from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re, zipfile

@dataclass(frozen=True)
class ReleaseAudit:
    version: str
    source_files: int
    test_files: int
    forbidden_patterns: tuple[str,...]
    generated_files: tuple[str,...]
    live_trade_markers: tuple[str,...]
    passed: bool

class ReleaseAuditEngine:
    """Static release audit. It reports suspicious content; it never declares data readiness."""
    def audit(self, root: str|Path, version: str) -> ReleaseAudit:
        p=Path(root); files=[x for x in p.rglob('*') if x.is_file() and '.git' not in x.parts]
        source=[x for x in files if x.suffix=='.py']; tests=[x for x in files if x.parts and x.parts[-2:] and 'tests' in x.parts]
        forbidden=[]; generated=[]; live=[]
        for f in files:
            rel=str(f.relative_to(p))
            if any(part in {'__pycache__','.pytest_cache','.orion_runtime'} for part in f.parts) or f.suffix in {'.pyc','.sqlite','.db'}:
                generated.append(rel)
            if f.suffix in {'.py','.md','.json','.html','.yml','.yaml'}:
                try: txt=f.read_text(errors='ignore')
                except Exception: continue
                if re.search(r'AKIA[0-9A-Z]{16}|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY',txt): forbidden.append(rel+':SECRET_MARKER')
                if re.search(r'live[_ -]?trading\s*=\s*True',txt,re.I): live.append(rel)
        passed=not forbidden and not live
        return ReleaseAudit(version,len(source),len(tests),tuple(sorted(forbidden)),tuple(sorted(generated)),tuple(sorted(live)),passed)
