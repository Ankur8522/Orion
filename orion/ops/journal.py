from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path


@dataclass(frozen=True)
class JournalEvent:
    sequence: int
    event_type: str
    payload: dict
    previous_hash: str
    event_hash: str


class RunJournal:
    """Append-only hash-chained runtime journal for replay and audit."""
    GENESIS = "GENESIS"

    def __init__(self, path: str | Path = ":memory:"):
        self.path = Path(path) if str(path) != ":memory:" else None
        self._events: list[JournalEvent] = []
        if self.path and self.path.exists():
            self._load()

    @staticmethod
    def _hash(previous_hash: str, event_type: str, payload: dict) -> str:
        body = {"previous_hash": previous_hash, "event_type": event_type, "payload": payload}
        return sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()

    def append(self, event_type: str, payload: dict) -> JournalEvent:
        if not event_type:
            raise ValueError("INVALID_EVENT_TYPE")
        previous = self._events[-1].event_hash if self._events else self.GENESIS
        event = JournalEvent(len(self._events) + 1, event_type, dict(payload), previous,
                             self._hash(previous, event_type, dict(payload)))
        self._events.append(event)
        self._persist()
        return event

    def events(self) -> tuple[JournalEvent, ...]:
        return tuple(self._events)

    def verify(self) -> bool:
        previous = self.GENESIS
        for e in self._events:
            if e.previous_hash != previous or e.event_hash != self._hash(previous, e.event_type, e.payload):
                return False
            previous = e.event_hash
        return True

    def _persist(self):
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            for e in self._events:
                f.write(json.dumps({"sequence": e.sequence, "event_type": e.event_type,
                                    "payload": e.payload, "previous_hash": e.previous_hash,
                                    "event_hash": e.event_hash}, sort_keys=True, default=str) + "\n")

    def close(self):
        return None

    def _load(self):
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                obj = json.loads(line)
                self._events.append(JournalEvent(obj["sequence"], obj["event_type"], obj["payload"],
                                                 obj["previous_hash"], obj["event_hash"]))
        if not self.verify():
            raise ValueError("JOURNAL_INTEGRITY_FAILURE")
