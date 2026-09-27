from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class Role(str,Enum): VIEWER='VIEWER'; RESEARCHER='RESEARCHER'; OPERATOR='OPERATOR'; ADMIN='ADMIN'
@dataclass(frozen=True)
class Principal:
    subject: str
    role: Role
class AccessPolicy:
    """Local authorization policy. Live trading permission is intentionally absent."""
    def allowed(self, principal: Principal, action: str) -> bool:
        if action.startswith('read:'): return True
        if action.startswith('research:'): return principal.role in {Role.RESEARCHER,Role.OPERATOR,Role.ADMIN}
        if action.startswith('ops:'): return principal.role in {Role.OPERATOR,Role.ADMIN}
        if action.startswith('admin:'): return principal.role is Role.ADMIN
        if action.startswith('trade:live:'): return False
        if action.startswith('trade:paper:'): return principal.role in {Role.OPERATOR,Role.ADMIN}
        return False
