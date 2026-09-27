from __future__ import annotations
import json
from hashlib import sha256

def canonical_hash(obj):
    return sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def verify_chain(events):
    previous='GENESIS'
    for e in events:
        body={'previous_hash':previous,'event':e}
        current=canonical_hash(body)
        previous=current
    return previous
