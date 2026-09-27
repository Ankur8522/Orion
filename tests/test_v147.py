from datetime import datetime, timezone, timedelta
from pathlib import Path
import tempfile
from orion.data.store import SQLiteStore
from orion.execution.vertical_slice import ResearchExecution
from orion.execution.vertical_runtime import RealDataVerticalRuntime


def iso(dt): return dt.replace(microsecond=0).isoformat().replace('+00:00','Z')

def payload():
    return {'data':{'candles':[['2026-09-25T09:15:00+05:30',100,110,95,105,10000],['2026-09-25T09:20:00+05:30',105,112,103,111,12000]]}}

def test_v147_upstox_vertical_pit_ready():
    with tempfile.TemporaryDirectory() as d:
        s=SQLiteStore(str(Path(d)/'o.db')); e=ResearchExecution(s); r=RealDataVerticalRuntime(s,e)
        now=datetime(2026,9,25,10,0,tzinfo=timezone.utc)
        x=r.ingest_upstox_candles(security_id='NSE_EQ|INE123A01016',instrument_key='NSE_EQ|INE123A01016',payload=payload(),event_time=iso(now-timedelta(minutes=45)),available_time=iso(now-timedelta(minutes=30)),captured_at=iso(now-timedelta(minutes=29)),decision_time=iso(now))
        assert x.state=='READY' and x.rows==2
        assert len(s.pit('NSE_EQ|INE123A01016','ohlcv',iso(now)))==2

def test_v147_future_information_blocked():
    with tempfile.TemporaryDirectory() as d:
        s=SQLiteStore(str(Path(d)/'o.db')); e=ResearchExecution(s); r=RealDataVerticalRuntime(s,e)
        now=datetime(2026,9,25,10,0,tzinfo=timezone.utc)
        x=r.ingest_upstox_candles(security_id='NSE_EQ|INE123A01016',instrument_key='NSE_EQ|INE123A01016',payload=payload(),event_time=iso(now),available_time=iso(now+timedelta(minutes=1)),captured_at=iso(now+timedelta(minutes=2)),decision_time=iso(now))
        assert x.state=='BLOCKED' and 'FUTURE_INFORMATION' in x.blockers

def test_v147_manifest_deterministic():
    with tempfile.TemporaryDirectory() as d:
        s=SQLiteStore(str(Path(d)/'o.db')); e=ResearchExecution(s); r=RealDataVerticalRuntime(s,e)
        now=datetime(2026,9,25,10,0,tzinfo=timezone.utc)
        kwargs=dict(security_id='NSE_EQ|INE123A01016',instrument_key='NSE_EQ|INE123A01016',payload=payload(),event_time=iso(now-timedelta(minutes=45)),available_time=iso(now-timedelta(minutes=30)),captured_at=iso(now-timedelta(minutes=29)),decision_time=iso(now))
        a=r.ingest_upstox_candles(**kwargs); b=r.ingest_upstox_candles(**kwargs)
        assert a.manifest_hash==b.manifest_hash
