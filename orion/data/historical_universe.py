from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Iterable, Mapping
from .time import parse_utc
from .universe_contract import InstitutionalUniverseContract, UniverseMembership

@dataclass(frozen=True)
class HistoricalUniverseSnapshot:
    snapshot_id: str
    as_of: str
    memberships: tuple[UniverseMembership, ...]
    coverage: object
    lineage_hash: str
    provenance: tuple[dict, ...] = ()

class HistoricalUniverseRegistry:
    """Persistent, PIT-safe historical membership registry.

    It stores supplied membership facts only. It never reconstructs missing index
    constituents or assumes today's membership was valid historically.
    """
    def __init__(self, store, contract: InstitutionalUniverseContract | None = None):
        self.store = store
        self.contract = contract or InstitutionalUniverseContract()
        self._ensure_schema()

    def _ensure_schema(self):
        self.store.db.execute('''CREATE TABLE IF NOT EXISTS historical_memberships(
            security_id TEXT NOT NULL,index_name TEXT NOT NULL,effective_from TEXT NOT NULL,
            effective_to TEXT,available_time TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,
            source_id TEXT NOT NULL,content_hash TEXT NOT NULL,metadata_json TEXT NOT NULL,
            PRIMARY KEY(security_id,index_name,effective_from,source_id,content_hash))''')
        self.store.db.execute('CREATE INDEX IF NOT EXISTS ix_hist_membership_pit ON historical_memberships(index_name,effective_from,available_time)')
        self.store.db.commit()

    def upsert(self, membership: UniverseMembership, *, source_id: str, content_hash: str, metadata: Mapping[str, object] | None = None):
        if not membership.security_id or not membership.index or not source_id or len(content_hash) != 64:
            raise ValueError('INVALID_HISTORICAL_MEMBERSHIP')
        parse_utc(membership.effective_from or membership.available_time or '1970-01-01T00:00:00Z')
        if membership.effective_to: parse_utc(membership.effective_to)
        if membership.available_time: parse_utc(membership.available_time)
        if membership.effective_from and membership.effective_to and parse_utc(membership.effective_to) <= parse_utc(membership.effective_from):
            raise ValueError('INVALID_MEMBERSHIP_INTERVAL')
        self.store.db.execute('''INSERT OR REPLACE INTO historical_memberships
            VALUES(?,?,?,?,?,?,?,?,?)''',(
            membership.security_id,membership.index,membership.effective_from or '1970-01-01T00:00:00Z',
            membership.effective_to,membership.available_time or membership.effective_from or '1970-01-01T00:00:00Z',
            int(membership.active),source_id,content_hash,json.dumps(dict(metadata or {}),sort_keys=True)))
        self.store.db.commit()

    def memberships_as_of(self, as_of: str, *, index_name: str | None = None) -> tuple[UniverseMembership, ...]:
        parse_utc(as_of)
        params=[as_of]
        sql='SELECT * FROM historical_memberships WHERE active=1 AND available_time<=? AND effective_from<=? AND (effective_to IS NULL OR effective_to>?)'
        params.extend([as_of,as_of])
        if index_name:
            sql += ' AND index_name=?'; params.append(index_name)
        sql += ' ORDER BY index_name,security_id,effective_from,available_time'
        rows=self.store.db.execute(sql,params).fetchall()
        # A security can have overlapping source records. Preserve provenance but
        # expose one effective membership per index/security, choosing latest effective record.
        chosen={}
        for r in rows:
            key=(r['index_name'],r['security_id'])
            old=chosen.get(key)
            if old is None or (r['effective_from'],r['available_time'],r['content_hash']) > (old['effective_from'],old['available_time'],old['content_hash']):
                chosen[key]=r
        return tuple(UniverseMembership(r['security_id'],r['index_name'],bool(r['active']),r['effective_from'],r['effective_to'],r['available_time']) for r in chosen.values())

    def snapshot(self, as_of: str) -> HistoricalUniverseSnapshot:
        rows=self.memberships_as_of(as_of)
        coverage=self.contract.coverage(rows,as_of=as_of)
        # Bind the snapshot to the exact source/content provenance selected by the PIT query.
        db_rows=self.store.db.execute('''SELECT index_name,security_id,effective_from,effective_to,available_time,source_id,content_hash
            FROM historical_memberships WHERE active=1 AND available_time<=? AND effective_from<=?
            AND (effective_to IS NULL OR effective_to>?) ORDER BY index_name,security_id,effective_from,available_time,source_id,content_hash''',(as_of,as_of,as_of)).fetchall()
        provenance=[]; seen=set()
        for r in db_rows:
            key=(r['index_name'],r['security_id'])
            if key in seen: continue
            seen.add(key)
            provenance.append({'index':r['index_name'],'security_id':r['security_id'],'effective_from':r['effective_from'],'effective_to':r['effective_to'],'available_time':r['available_time'],'source_id':r['source_id'],'content_hash':r['content_hash']})
        payload={'as_of':as_of,'memberships':[m.__dict__ for m in rows],'provenance':provenance,'coverage':coverage.__dict__}
        sid=sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:24]
        lineage=sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        return HistoricalUniverseSnapshot(sid,as_of,rows,coverage,lineage,tuple(provenance))
