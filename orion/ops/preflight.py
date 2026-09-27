from dataclasses import dataclass

@dataclass(frozen=True)
class Preflight:
    pit_enabled: bool
    audit_enabled: bool
    verifier_enabled: bool
    backup_enabled: bool
    provider_mode: str

    def validate(self):
        missing=[]
        for name in ('pit_enabled','audit_enabled','verifier_enabled','backup_enabled'):
            if not getattr(self,name): missing.append(name)
        if missing: raise RuntimeError('DEPLOYMENT_BLOCKED:' + ','.join(missing))
        if self.provider_mode not in {'public','licensed'}: raise RuntimeError('INVALID_PROVIDER_MODE')
        return True
