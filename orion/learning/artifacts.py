from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class ModelArtifact:
    model_id: str
    model_type: str
    version: str
    payload: dict[str, Any]
    metrics: dict[str, Any]
    dataset_hash: str
    feature_hash: str
    code_hash: str
    lineage_hash: str

class ModelArtifactStore:
    """Content-addressed model artifact persistence with deterministic lineage."""
    def save(self, path: str | Path, artifact: ModelArtifact) -> str:
        p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
        obj={'model_id':artifact.model_id,'model_type':artifact.model_type,'version':artifact.version,'payload':artifact.payload,'metrics':artifact.metrics,'dataset_hash':artifact.dataset_hash,'feature_hash':artifact.feature_hash,'code_hash':artifact.code_hash,'lineage_hash':artifact.lineage_hash}
        p.write_text(json.dumps(obj,sort_keys=True,indent=2),encoding='utf-8')
        return str(p)
    def load(self, path: str | Path) -> ModelArtifact:
        obj=json.loads(Path(path).read_text(encoding='utf-8'))
        required=('model_id','model_type','version','payload','metrics','dataset_hash','feature_hash','code_hash','lineage_hash')
        if any(k not in obj for k in required): raise ValueError('INVALID_MODEL_ARTIFACT')
        return ModelArtifact(**{k:obj[k] for k in required})

def artifact_lineage(model_id, model_type, version, payload, metrics, dataset_hash, feature_hash, code_hash):
    raw={'model_id':model_id,'model_type':model_type,'version':version,'payload':payload,'metrics':metrics,'dataset_hash':dataset_hash,'feature_hash':feature_hash,'code_hash':code_hash}
    return sha256(json.dumps(raw,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
