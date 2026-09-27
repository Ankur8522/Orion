from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import sqlite3
from datetime import datetime, timezone

class ModelLifecycle(str, Enum):
    DEVELOPMENT='DEVELOPMENT'
    VALIDATION='VALIDATION'
    SHADOW='SHADOW'
    CHALLENGER='CHALLENGER'
    CHAMPION='CHAMPION'
    RETIRED='RETIRED'
    ROLLED_BACK='ROLLED_BACK'

@dataclass(frozen=True)
class ModelLifecycleRecord:
    model_id: str
    state: ModelLifecycle
    changed_at: str
    reason: str

@dataclass(frozen=True)
class ModelScore:
    model_id: str
    resolved: int
    brier: float | None
    log_loss: float | None
    calibration_error: float | None
    horizon_coverage: float = 1.0
    confidence: float = 1.0
    stability: float = 1.0
    evidence_sufficient: bool = True
    regime_coverage: int = 1

@dataclass(frozen=True)
class ModelDecision:
    champion: str
    challenger_scores: tuple[ModelScore, ...]
    rationale: str
    changed: bool = False

class ChampionChallengerRegistry:
    """Bounded, auditable model selection from observed outcomes only."""
    def __init__(self, champion: str = 'orion', path=':memory:'):
        if not champion: raise ValueError('INVALID_CHAMPION')
        self.path=str(path); self._db=sqlite3.connect(self.path, check_same_thread=False)
        self._ensure_schema(); self._champion=champion; self._scores={}; self._hydrate()
    def _ensure_schema(self):
        self._db.execute('CREATE TABLE IF NOT EXISTS model_registry (model_id TEXT PRIMARY KEY, resolved INTEGER, brier REAL, log_loss REAL, calibration_error REAL, horizon_coverage REAL DEFAULT 1.0, confidence REAL DEFAULT 1.0, stability REAL DEFAULT 1.0, evidence_sufficient INTEGER DEFAULT 1, regime_coverage INTEGER DEFAULT 1)')
        cols={r[1] for r in self._db.execute('PRAGMA table_info(model_registry)')}
        for name,sql in [('horizon_coverage','ALTER TABLE model_registry ADD COLUMN horizon_coverage REAL DEFAULT 1.0'),('confidence','ALTER TABLE model_registry ADD COLUMN confidence REAL DEFAULT 1.0'),('stability','ALTER TABLE model_registry ADD COLUMN stability REAL DEFAULT 1.0'),('evidence_sufficient','ALTER TABLE model_registry ADD COLUMN evidence_sufficient INTEGER DEFAULT 1'),('regime_coverage','ALTER TABLE model_registry ADD COLUMN regime_coverage INTEGER DEFAULT 1')]:
            if name not in cols: self._db.execute(sql)
        self._db.execute('CREATE TABLE IF NOT EXISTS model_meta (key TEXT PRIMARY KEY, value TEXT)')
        self._db.execute('CREATE TABLE IF NOT EXISTS model_lifecycle (model_id TEXT PRIMARY KEY, state TEXT NOT NULL, changed_at TEXT NOT NULL, reason TEXT NOT NULL)')
        self._db.commit()
    def _hydrate(self):
        row=self._db.execute("SELECT value FROM model_meta WHERE key='champion'").fetchone()
        if row: self._champion=row[0]
        for r in self._db.execute('SELECT model_id,resolved,brier,log_loss,calibration_error,horizon_coverage,confidence,stability,evidence_sufficient,regime_coverage FROM model_registry'):
            self._scores[r[0]]=ModelScore(r[0],r[1],r[2],r[3],r[4],r[5],r[6],r[7],bool(r[8]),r[9])
    @staticmethod
    def _rank(score): return (score.brier is None, score.brier if score.brier is not None else 1e9, score.calibration_error if score.calibration_error is not None else 1e9, score.log_loss if score.log_loss is not None else 1e9, -score.resolved)
    def register(self, model_id: str, state: ModelLifecycle = ModelLifecycle.DEVELOPMENT, *, reason: str = 'REGISTERED'):
        if not model_id: raise ValueError('INVALID_MODEL_ID')
        now=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
        self._db.execute('INSERT OR REPLACE INTO model_lifecycle VALUES(?,?,?,?)',(model_id,state.value,now,reason)); self._db.commit()
        return ModelLifecycleRecord(model_id,state,now,reason)

    def transition(self, model_id: str, state: ModelLifecycle, *, reason: str):
        if not model_id or not reason: raise ValueError('INVALID_MODEL_TRANSITION')
        current=self.lifecycle(model_id)
        allowed={
            ModelLifecycle.DEVELOPMENT:{ModelLifecycle.VALIDATION,ModelLifecycle.RETIRED},
            ModelLifecycle.VALIDATION:{ModelLifecycle.SHADOW,ModelLifecycle.CHALLENGER,ModelLifecycle.RETIRED},
            ModelLifecycle.SHADOW:{ModelLifecycle.CHALLENGER,ModelLifecycle.RETIRED},
            ModelLifecycle.CHALLENGER:{ModelLifecycle.CHAMPION,ModelLifecycle.RETIRED},
            ModelLifecycle.CHAMPION:{ModelLifecycle.RETIRED,ModelLifecycle.ROLLED_BACK},
            ModelLifecycle.RETIRED:set(),
            ModelLifecycle.ROLLED_BACK:{ModelLifecycle.DEVELOPMENT,ModelLifecycle.RETIRED},
        }
        if current is None: raise KeyError('MODEL_NOT_REGISTERED')
        if state not in allowed[current.state]: raise ValueError('INVALID_MODEL_TRANSITION')
        return self.register(model_id,state,reason=reason)

    def lifecycle(self, model_id: str):
        row=self._db.execute('SELECT model_id,state,changed_at,reason FROM model_lifecycle WHERE model_id=?',(model_id,)).fetchone()
        return None if row is None else ModelLifecycleRecord(row[0],ModelLifecycle(row[1]),row[2],row[3])

    def lifecycles(self):
        return tuple(ModelLifecycleRecord(r[0],ModelLifecycle(r[1]),r[2],r[3]) for r in self._db.execute('SELECT model_id,state,changed_at,reason FROM model_lifecycle ORDER BY model_id'))

    def update(self, scores, *, min_resolved=5, min_horizon_coverage=0.75, min_confidence=0.6, min_stability=0.75, min_regimes=1, min_performance_delta=0.02):
        if min_resolved<1 or not 0<=min_horizon_coverage<=1 or not 0<=min_confidence<=1 or not 0<=min_stability<=1: raise ValueError('INVALID_SELECTION_GATES')
        for s in scores:
            if not s.model_id or s.resolved<0: raise ValueError('INVALID_MODEL_SCORE')
            self._scores[s.model_id]=s
            self._db.execute('INSERT OR REPLACE INTO model_registry VALUES(?,?,?,?,?,?,?,?,?,?)',(s.model_id,s.resolved,s.brier,s.log_loss,s.calibration_error,s.horizon_coverage,s.confidence,s.stability,int(s.evidence_sufficient),s.regime_coverage))
        eligible=[s for s in self._scores.values() if s.resolved>=min_resolved and s.brier is not None and s.horizon_coverage>=min_horizon_coverage and s.confidence>=min_confidence and s.stability>=min_stability and s.regime_coverage>=min_regimes and s.evidence_sufficient]
        rationale='INSUFFICIENT_OBSERVED_OUTCOMES_OR_EVIDENCE'
        old=self._champion; changed=False
        if eligible:
            winner=min(eligible,key=self._rank); current=self._scores.get(self._champion)
            if current is None or current.brier is None:
                self._champion=winner.model_id; rationale='CHAMPION_UPDATED_AFTER_SELECTION_GATES'; changed=True
                if self.lifecycle(winner.model_id) is None: self.register(winner.model_id, ModelLifecycle.CHALLENGER, reason=rationale)
                if self.lifecycle(winner.model_id) and self.lifecycle(winner.model_id).state == ModelLifecycle.CHALLENGER: self.transition(winner.model_id, ModelLifecycle.CHAMPION, reason=rationale)
            elif winner.model_id != current.model_id and winner.brier <= current.brier-min_performance_delta and winner.horizon_coverage>=min_horizon_coverage and winner.confidence>=min_confidence and winner.stability>=min_stability:
                self._champion=winner.model_id; rationale='CHAMPION_UPDATED_AFTER_STABLE_PERFORMANCE_DELTA'; changed=True
                if self.lifecycle(winner.model_id) is None: self.register(winner.model_id, ModelLifecycle.CHALLENGER, reason=rationale)
                if self.lifecycle(winner.model_id).state == ModelLifecycle.CHALLENGER: self.transition(winner.model_id, ModelLifecycle.CHAMPION, reason=rationale)
            else: rationale='CHAMPION_RETAINED_SELECTION_GATES'
        self._db.execute("INSERT OR REPLACE INTO model_meta VALUES('champion',?)",(self._champion,)); self._db.commit()
        return ModelDecision(self._champion,tuple(sorted(self._scores.values(),key=lambda x:x.model_id)),rationale,changed)
    @property
    def champion(self): return self._champion
    def scores(self): return tuple(sorted(self._scores.values(),key=lambda x:x.model_id))
    def close(self): self._db.close()
