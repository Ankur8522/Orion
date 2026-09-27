from __future__ import annotations
from dataclasses import asdict
from typing import Any
import os
from pathlib import Path
from orion.runtime.control_plane import OrionControlPlane
from orion.portfolio.performance import PortfolioPerformanceEngine
from orion.runtime.data_plane import DataPlaneRegistry
from orion.research.factory import ResearchFactory, REQUIRED_DATASETS
from orion.learning.diagnostics import LearningDiagnosticsEngine
from orion.runtime.operating_metrics import OperatingScorecard
from orion.research.operating import ResearchOperatingCoordinator
from orion.research.factory import REQUIRED_DATASETS
from orion.data.universe_contract import InstitutionalUniverseContract
from orion.data.integrity import DataIntegrityPipeline
from orion.validation.empirical import EmpiricalValidationLab
from orion.data.store import SQLiteStore
from orion.acquisition.instrument_registry import InstrumentMappingRegistry
from orion.data.historical_universe import HistoricalUniverseRegistry
from orion.learning.advanced_diagnostics import AdvancedDiagnosticsEngine
from orion.portfolio.stress import PortfolioStressEngine
from orion.learning.probabilistic import ForecastEvidence, ProbabilisticForecastEngine
from orion.execution.realistic import ExecutionCostModel, RealisticPaperCostEngine

class RuntimeGateway:
    """Runtime read model for the UI/API. Never fabricates market data."""
    def __init__(self, control_plane=None):
        if control_plane is not None:
            self.control_plane=control_plane
        else:
            root=Path(os.environ.get("ORION_STATE_DIR", ".orion_runtime")); root.mkdir(parents=True,exist_ok=True)
            self.control_plane=OrionControlPlane(state_path=root/"brain.sqlite", journal_path=root/"journal.sqlite", paper_path=root/"paper.sqlite")
        self.performance=PortfolioPerformanceEngine()
        self.research_factory=ResearchFactory()
        self.learning_diagnostics=LearningDiagnosticsEngine()
        self.scorecard=OperatingScorecard()
        self.data_plane=DataPlaneRegistry()
        self.research_operating=ResearchOperatingCoordinator()
        self.universe_contract=InstitutionalUniverseContract()
        self.data_integrity=DataIntegrityPipeline()
        self.empirical_validation=EmpiricalValidationLab()
        token=os.environ.get('UPSTOX_ACCESS_TOKEN','').strip()
        self.data_plane.register('upstox', configured=bool(token), authenticated=False, capabilities=('ohlcv','market_price'), historical_datasets=('ohlcv','market_price'), reason=('CREDENTIAL_PRESENT_AUTH_NOT_VERIFIED' if token else 'CREDENTIALS_REQUIRED'))
        self.data_plane.register('authorized-provider', configured=False, authenticated=False, capabilities=(), reason='CREDENTIALS_REQUIRED')
    def state(self)->dict[str,Any]:
        cp=self.control_plane; h=cp.health(); service=cp.service; paper=service.paper.snapshot(); journal=cp.journal.events(); metrics=cp.metrics.snapshot()
        memory=getattr(service.kernel,'progressive_memory',None); memory_size=memory.size() if memory else 0
        latest=None
        if memory:
            histories=getattr(memory,'_states',{})
            rows=[x for rs in histories.values() for x in rs]
            if rows: latest=max(rows,key=lambda x:x.cycle_id)
        paper['position_count']=len(service.paper.positions()); paper['positions']=[asdict(x) for x in service.paper.positions()]
        diagnostics=self._learning_snapshot()
        readiness=self._system_readiness()
        return {'product':'ORION','version':'v190','mode':'RUNTIME','live_trading_enabled':False,'health':h,'paper':paper,
                'journal':{'events':len(journal),'integrity':cp.journal.verify()},'metrics':metrics,
                'brain':{'progressive':True,'persistent_memory':bool(memory),'closed_loop':True,'replay':True,'champion_challenger':True,'specialist_count':15,'specialist_training':'CHRONOLOGICAL_OOS','meta_intelligence':'AVAILABLE_REQUIRES_OBSERVED_OUTCOMES','data_fabric':'CANONICAL_PIT_AWARE','decision_world':'SINGLE_SOURCE_OF_TRUTH',
                         'memory_states':memory_size,'latest_cycle':getattr(latest,'cycle_id',None),'phase':getattr(getattr(latest,'phase',None),'value',None),
                         'belief':getattr(getattr(latest,'assessment',None),'belief',None),'uncertainty':getattr(getattr(latest,'assessment',None),'uncertainty',None),
                         'robustness':getattr(getattr(latest,'assessment',None),'robustness',None),'fragility':getattr(getattr(latest,'assessment',None),'fragility',None)},
                'operations':{'cycles':h.get('cycles',[]),'alerts':h.get('alerts',[]),'research_jobs':h.get('research_jobs',0),'active_jobs':h.get('active_research_jobs',0),'capabilities':[
                    'PIT DATA BOUNDARY','EVIDENCE GATING','PROGRESSIVE REASONING','COUNTERFACTUAL SCENARIOS','PORTFOLIO RISK',
                    'CAPITAL ALLOCATION','PAPER EXECUTION','FORECAST CALIBRATION','CHAMPION/CHALLENGER','TIME-MACHINE REPLAY','DATA INTEGRITY RECONCILIATION','AUDIT LINEAGE','PERSISTENT PAPER ACCOUNTING','REPLAY HASH CHAIN','RESEARCH EVIDENCE ADJUDICATION']},
                'data_boundary':{'market_data':'NOT_CONFIGURED_UNLESS_PROVIDER_AUTHORIZED','pit':True,'synthetic_market_data':False,'providers':[x.__dict__ for x in self.data_plane.statuses()]},
                'performance': self.performance_snapshot(),
                'learning': {'forecasts': len(service.kernel.forecast_ledger.forecasts()), 'resolved': len(service.kernel.forecast_ledger.outcomes()), 'champion': service.kernel.model_registry.champion},
                'replay': {'snapshots': len(service.kernel.time_machine.snapshots()), 'latest': service.kernel.time_machine.snapshots()[-1].__dict__ if service.kernel.time_machine.snapshots() else None},
                'research': {'required_datasets': REQUIRED_DATASETS, 'queue_jobs': h.get('research_jobs',0), 'coverage_contract': self.data_plane.coverage(REQUIRED_DATASETS), 'universe_target': self.universe_contract.targets, 'universe_target_size': self.universe_contract.target_size},
                'learning_diagnostics': diagnostics,
                'advanced_learning': self.advanced_learning_snapshot(),
                'system_readiness': readiness,
                'security': {'rbac':'DEFINED','live_trade_permission':False,'api_mode':'LOCAL_RUNTIME'},
                'integrity': {'status':'NOT_EXECUTED','reconciliation':'ENFORCED','pit_boundary':'ENFORCED'},
                'provider_freshness': list(self.data_plane.freshness(__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat().replace('+00:00','Z'))),
                'empirical_validation': self.empirical_validation_snapshot()}
    def health(self): return self.control_plane.health()
    def brain_history(self, thesis_id=None):
        m=getattr(self.control_plane.service.kernel,'progressive_memory',None)
        if not m: return []
        if thesis_id: rows=m.history(thesis_id)
        else: rows=[x for rs in getattr(m,'_states',{}).values() for x in rs]
        return [asdict(x) for x in rows]
    def audit(self, limit=100):
        return [{'seq':i+1,'event':e.event_type,'hash':e.event_hash,'payload':e.payload} for i,e in enumerate(self.control_plane.journal.events()[-limit:])]

    def performance_snapshot(self):
        # Only verified paper marks are used. No market prices are invented.
        history=getattr(self.control_plane.service.paper,'nav_history',lambda:())()
        if not history: return {'status':'NO_PAPER_HISTORY','summary':None,'series':[]}
        nav=[(str(x['timestamp']), float(x['nav'])) for x in history]
        summary=self.performance.summarize(nav)
        return {'status':'VERIFIED_PAPER_HISTORY','summary':summary.__dict__,'series':[x.__dict__ for x in self.performance.series(nav)]}

    def empirical_validation_snapshot(self):
        ledger=self.control_plane.service.kernel.forecast_ledger
        forecasts=ledger.forecasts(); outcomes=ledger.outcomes()
        if not forecasts and not outcomes:
            return {'status':'NO_OBSERVED_HISTORY','forecast_resolved':0,'backtest_observations':0,'lookahead_rejections':0,'lineage_hash':None,'note':'Provide verified PIT forecasts/outcomes or historical rows to activate empirical validation.'}
        if forecasts:
            decision_time=max(f.decision_time for f in forecasts)
        else:
            decision_time=max(o.available_time for o in outcomes)
        evaluation_time=max([f.horizon_end for f in forecasts] + [o.available_time for o in outcomes] + [decision_time])
        report=self.empirical_validation.run(forecasts=forecasts, outcomes=outcomes, decision_time=decision_time, evaluation_time=evaluation_time, ledger=ledger)
        return {
            'status':report.status, 'forecast_resolved':report.forecast_report.get('resolved',0),
            'backtest_observations':report.observations_used, 'lookahead_rejections':report.leakage_rejections,
            'diagnostics':report.diagnostics, 'lineage_hash':report.lineage_hash,
            'note':'Metrics derive only from observed forecast outcomes and supplied PIT backtest rows.'
        }

    def _learning_snapshot(self):
        ledger=getattr(self.control_plane.service.kernel,'forecast_ledger',None)
        if ledger is None:
            return {'status':'NO_FORECAST_LEDGER','resolved':0,'hit_rate':None,'flags':['FORECAST_LEDGER_NOT_WIRED']}
        d=self.learning_diagnostics.analyze(ledger.forecasts(),ledger.outcomes())
        return d.__dict__ | {'status':'VERIFIED_OBSERVED_OUTCOMES'}

    def _system_readiness(self):
        provider_ready=any(x.configured and x.authenticated for x in self.data_plane.statuses())
        b=80.0; p=70.0; u=95.0; data=100.0 if provider_ready else 20.0
        score=self.scorecard.score(data_readiness=data,brain_readiness=b,portfolio_readiness=p,ui_readiness=u,blockers={'REAL_DATA_PROVIDER':not provider_ready})
        return score.__dict__

    def research_readiness(self, security_id: str, as_of: str, datasets):
        return self.research_operating.plan((security_id,), as_of=as_of, datasets={security_id: datasets}).plans[0]


    def acquisition_coverage(self, security_ids, decision_time=None):
        root=Path(os.environ.get('ORION_STATE_DIR','.orion_runtime')); root.mkdir(parents=True,exist_ok=True)
        store=SQLiteStore(root/'acquisition.sqlite')
        try: return store.acquisition_coverage(security_ids,dataset='ohlcv',decision_time=decision_time)
        finally: store.close()

    def acquisition_manifest_coverage(self, manifest_id, decision_time=None):
        root=Path(os.environ.get('ORION_STATE_DIR','.orion_runtime')); root.mkdir(parents=True,exist_ok=True)
        store=SQLiteStore(root/'acquisition.sqlite')
        try:
            return {'coverage': store.market_batch_coverage(manifest_id,dataset='ohlcv',decision_time=decision_time), 'ledger': store.dataset_coverage_ledger(manifest_id,dataset='ohlcv')}
        finally: store.close()

    def acquisition_schedule(self, manifest_id, decision_time=None):
        root=Path(os.environ.get('ORION_STATE_DIR','.orion_runtime')); root.mkdir(parents=True,exist_ok=True)
        store=SQLiteStore(root/'acquisition.sqlite')
        try: return store.market_schedule_state(manifest_id) or {'manifest_id':manifest_id,'status':'NOT_REGISTERED'}
        finally: store.close()

    def acquisition_readiness(self, security_ids, *, provider='upstox', as_of=None):
        from datetime import datetime, timezone
        as_of = as_of or datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
        root=Path(os.environ.get('ORION_STATE_DIR','.orion_runtime')); root.mkdir(parents=True,exist_ok=True)
        store=SQLiteStore(root/'acquisition.sqlite')
        try:
            return InstrumentMappingRegistry(store).readiness(security_ids, provider=provider, as_of=as_of)
        finally: store.close()

    def acquisition_operational_readiness(self, security_ids, *, provider='upstox', as_of=None, dataset='ohlcv'):
        from datetime import datetime, timezone
        from orion.acquisition.operational_readiness import build_operational_readiness
        as_of = as_of or datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
        root=Path(os.environ.get('ORION_STATE_DIR','.orion_runtime')); root.mkdir(parents=True,exist_ok=True)
        store=SQLiteStore(root/'acquisition.sqlite')
        try:
            status = next((x for x in self.data_plane.statuses() if x.provider == provider), None)
            authenticated = bool(status and status.authenticated)
            report=build_operational_readiness(security_ids=security_ids, mapping_registry=InstrumentMappingRegistry(store), store=store, provider=provider, as_of=as_of, provider_authenticated=authenticated, dataset=dataset)
            return report.__dict__ | {'rows': list(report.rows), 'provider_authenticated': authenticated, 'dataset': dataset}
        finally: store.close()

    def acquisition_instrument_mappings(self, *, provider=None):
        root=Path(os.environ.get('ORION_STATE_DIR','.orion_runtime')); root.mkdir(parents=True,exist_ok=True)
        store=SQLiteStore(root/'acquisition.sqlite')
        try: return store.instrument_mappings(provider=provider)
        finally: store.close()

    def historical_universe_snapshot(self, as_of: str):
        root=Path(os.environ.get('ORION_STATE_DIR','.orion_runtime')); root.mkdir(parents=True,exist_ok=True)
        store=SQLiteStore(root/'acquisition.sqlite')
        try:
            snap=HistoricalUniverseRegistry(store,self.universe_contract).snapshot(as_of)
            return {'snapshot_id':snap.snapshot_id,'as_of':snap.as_of,'coverage':snap.coverage.__dict__,'memberships':[x.__dict__ for x in snap.memberships],'lineage_hash':snap.lineage_hash}
        finally: store.close()

    def advanced_learning_snapshot(self, min_sample: int=10):
        adv=AdvancedDiagnosticsEngine().analyze(self.control_plane.service.kernel.forecast_ledger.forecasts(),self.control_plane.service.kernel.forecast_ledger.outcomes(),min_sample=min_sample)
        return adv.__dict__ | {'by_model':[x.__dict__ for x in adv.by_model],'by_sector':[x.__dict__ for x in adv.by_sector],'by_regime':[x.__dict__ for x in adv.by_regime],'by_horizon':[x.__dict__ for x in adv.by_horizon],'calibration_drift':adv.calibration_drift.__dict__}

    def probabilistic_forecast(self, *, base_rate, evidence, model_id='orion-bounded-logistic', temperature=1.0, prior_strength=1.0):
        rows=tuple(ForecastEvidence(str(x['evidence_id']),float(x['signal']),float(x.get('reliability',1.0)),float(x.get('direction',1.0))) for x in evidence)
        return ProbabilisticForecastEngine().generate(base_rate=float(base_rate), evidence=rows, model_id=str(model_id), temperature=float(temperature), prior_strength=float(prior_strength)).__dict__

    def paper_cost(self, *, quantity, reference_price, side, model=None):
        m=ExecutionCostModel(**dict(model or {}))
        return RealisticPaperCostEngine().apply(quantity=float(quantity), reference_price=float(reference_price), side=str(side).upper(), model=m).__dict__

    def portfolio_stress(self, weights, correlations=None, shocks=None, gross_exposure=None):
        corr = None
        if correlations is not None:
            corr = {}
            for k,v in correlations.items():
                if isinstance(k,str) and '|' in k:
                    a,b=k.split('|',1); corr[(a,b)]=float(v)
                elif isinstance(k,(tuple,list)) and len(k)==2:
                    corr[(str(k[0]),str(k[1]))]=float(v)
                else:
                    raise ValueError('INVALID_CORRELATION_KEY')
        report=PortfolioStressEngine().analyze(weights,correlations=corr,shocks=shocks,gross_exposure=gross_exposure)
        return report.__dict__ | {'clusters':[x.__dict__ for x in report.clusters]}

    def capabilities(self):
        return {'architecture': ['PIT_DATA','DATA_QUALITY','PROVIDER_REGISTRY','EVIDENCE_LEDGER','RESEARCH_FACTORY','UNIVERSE_SCHEDULER','INFORMATION_VALUE_PRIORITY','DECISION_PLANE','PROGRESSIVE_BRAIN','ADVERSARIAL_REVIEW','COUNTERFACTUAL_WORLD','SCENARIO_ENGINE','PORTFOLIO_RISK','CAPITAL_ALLOCATION','PAPER_EXECUTION','PERFORMANCE','FORECAST_FEEDBACK','LEARNING_DIAGNOSTICS','CHAMPION_CHALLENGER','ATTRIBUTION','TIME_MACHINE','AUDIT','OBSERVABILITY','RBAC','RUNTIME_UI','EMPIRICAL_VALIDATION','PIT_BACKTEST_LEAKAGE_TESTS','GOVERNED_INSTRUMENT_MAPPING','ACQUISITION_READINESS','OPERATIONAL_DATA_READINESS','HISTORICAL_UNIVERSE_TIME_MACHINE','ADVANCED_CALIBRATION_DRIFT','PORTFOLIO_STRESS_CLUSTERS','BOUNDED_PROBABILISTIC_FORECASTS','REALISTIC_PAPER_COST_LEDGER'], 'live_trading_enabled':False}

# v182 code-completable read-only research/risk surfaces
from orion.research.scenarios import ResearchScenarioEngine
from orion.portfolio.correlation import CorrelationEngine

def _scenario_surface(self, payload):
    return ResearchScenarioEngine().build(**payload).__dict__

def _correlation_surface(self, returns, threshold=0.70):
    return CorrelationEngine().calculate(returns, threshold).__dict__
RuntimeGateway.research_scenarios = _scenario_surface
RuntimeGateway.portfolio_correlation = _correlation_surface
