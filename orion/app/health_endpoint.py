from __future__ import annotations
from .gateway import RuntimeGateway

def health_payload():
    g=RuntimeGateway(); return g.health()
