from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass
class Health:
    name:str; ok:bool; detail:str=''

def check_store(store):
    try:
        store.db.execute('SELECT 1').fetchone(); return Health('sqlite',True)
    except Exception as e: return Health('sqlite',False,str(e))

def readiness(checks):
    bad=[c.name for c in checks if not c.ok]
    return {'status':'READY' if not bad else 'NOT_READY','checks':[c.__dict__ for c in checks],'failed':bad}
