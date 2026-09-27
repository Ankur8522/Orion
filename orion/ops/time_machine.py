from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from datetime import datetime, timezone
from ..data.time import parse_utc

@dataclass(frozen=True)
class StateSnapshot:
    cycle_id: str; decision_time: str; state: dict; state_hash: str; previous_hash: str = ''; chain_hash: str = ''

@dataclass(frozen=True)
class ReplayResult:
    cycle_ids: tuple[str,...]; final_state: dict; deterministic: bool; lineage_hash: str

class TimeMachine:
    """Append-only persistent state snapshots with timestamp and hash-chain validation."""
    def __init__(self, path=':memory:'):
        self.path=str(path); self._snapshots=[]
        if self.path!=':memory:' and Path(self.path).exists(): self._load()
    @staticmethod
    def _hash(state): return sha256(json.dumps(state,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
    @staticmethod
    def _chain(cycle_id, decision_time, state_hash, previous_hash):
        return sha256(json.dumps({'cycle_id':cycle_id,'decision_time':decision_time,'state_hash':state_hash,'previous_hash':previous_hash},sort_keys=True,separators=(',',':')).encode()).hexdigest()
    @staticmethod
    def _time_key(value):
        try:
            return ('dt', parse_utc(value))
        except (ValueError, TypeError):
            try:
                dt=datetime.fromisoformat(str(value))
                if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
                return ('dt', dt.astimezone(timezone.utc))
            except (ValueError, TypeError):
                return ('opaque', str(value))
    def _validate_order(self, decision_time):
        current=self._time_key(decision_time)
        if self._snapshots:
            previous=self._time_key(self._snapshots[-1].decision_time)
            if current[0] == previous[0] == 'dt' and current[1] < previous[1]: raise ValueError('NON_MONOTONIC_DECISION_TIME')
    def record(self, cycle_id, decision_time, state):
        if not cycle_id: raise ValueError('INVALID_CYCLE_ID')
        if any(x.cycle_id == cycle_id for x in self._snapshots): raise ValueError('DUPLICATE_CYCLE_ID')
        self._validate_order(decision_time)
        clean=json.loads(json.dumps(state,sort_keys=True,default=str)); state_hash=self._hash(clean)
        previous=self._snapshots[-1].chain_hash if self._snapshots else ''
        chain=self._chain(cycle_id,decision_time,state_hash,previous)
        snap=StateSnapshot(cycle_id,decision_time,clean,state_hash,previous,chain); self._snapshots.append(snap); self._persist(); return snap
    def _persist(self):
        if self.path == ':memory:': return
        p=Path(self.path); p.parent.mkdir(parents=True,exist_ok=True); p.write_text('\n'.join(json.dumps(x.__dict__,sort_keys=True) for x in self._snapshots)+'\n',encoding='utf-8')
    def _load(self):
        for line in Path(self.path).read_text(encoding='utf-8').splitlines():
            if line.strip():
                x=json.loads(line); self._snapshots.append(StateSnapshot(x['cycle_id'],x['decision_time'],x['state'],x['state_hash'],x.get('previous_hash',''),x.get('chain_hash','')))
        prev=''; last=None
        for x in self._snapshots:
            if last is not None:
                current=self._time_key(x.decision_time); previous=self._time_key(last)
                if current[0] == previous[0] == 'dt' and current[1] < previous[1]: raise ValueError('NON_MONOTONIC_DECISION_TIME')
            if self._hash(x.state)!=x.state_hash: raise ValueError('SNAPSHOT_INTEGRITY_FAILURE')
            if x.chain_hash:
                if x.previous_hash != prev: raise ValueError('SNAPSHOT_CHAIN_FAILURE')
                expected=self._chain(x.cycle_id,x.decision_time,x.state_hash,x.previous_hash)
                if x.chain_hash != expected: raise ValueError('SNAPSHOT_CHAIN_FAILURE')
                prev=x.chain_hash
            else:
                # v1 snapshots had no chain fields; state hashes are still checked.
                prev=''
            last=x.decision_time
    def snapshots(self): return tuple(self._snapshots)
    def replay(self, *, start_cycle=None, end_cycle=None):
        rows=self._snapshots
        if start_cycle: rows=tuple(x for x in rows if x.cycle_id>=start_cycle)
        if end_cycle: rows=tuple(x for x in rows if x.cycle_id<=end_cycle)
        if not rows: return ReplayResult((),{},True,self._hash({}))
        state={}; ids=[]; hashes=[]; prev=''
        for x in rows:
            if self._hash(x.state)!=x.state_hash: raise ValueError('SNAPSHOT_INTEGRITY_FAILURE')
            state=dict(x.state); ids.append(x.cycle_id); hashes.append(x.chain_hash)
            if x.previous_hash != prev and prev: raise ValueError('SNAPSHOT_CHAIN_FAILURE')
            prev=x.chain_hash
        return ReplayResult(tuple(ids),state,True,self._hash({'cycles':ids,'hashes':hashes,'final':state}))
