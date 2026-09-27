from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import ast, json

@dataclass(frozen=True)
class DerivedMetric:
    security_id: str; metric: str; value: Decimal; unit: str; source_ids: tuple[str,...]; formula: str; lineage_hash: str

def _dec(x): return Decimal(str(x))

def _safe_eval(formula, inputs):
    tree=ast.parse(formula, mode='eval')
    allowed=(ast.Expression,ast.BinOp,ast.UnaryOp,ast.Name,ast.Constant,ast.Add,ast.Sub,ast.Mult,ast.Div,ast.Pow,ast.USub,ast.UAdd,ast.Load)
    for n in ast.walk(tree):
        if not isinstance(n, allowed): raise ValueError('INVALID_FORMULA')
        if isinstance(n, ast.Name) and n.id not in inputs: raise ValueError('UNKNOWN_INPUT')
        if isinstance(n, ast.Constant) and not isinstance(n.value,(int,float,str)): raise ValueError('INVALID_CONSTANT')
    return eval(compile(tree,'<formula>','eval'), {'__builtins__':{}}, inputs)

def derive(security_id, metric, formula, inputs: dict[str, Decimal], unit='ratio', source_ids=None):
    if not inputs: raise ValueError('NO_INPUTS')
    vals={k:_dec(v) for k,v in inputs.items()}
    try: value=_safe_eval(formula, vals)
    except Exception as e: raise ValueError('INVALID_FORMULA') from e
    if not isinstance(value, Decimal): value=_dec(value)
    ids=tuple(sorted(source_ids or inputs.keys()))
    payload={'security_id':security_id,'metric':metric,'formula':formula,'inputs':{k:str(v) for k,v in sorted(vals.items())},'unit':unit,'source_ids':ids}
    h=sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return DerivedMetric(security_id,metric,value.quantize(Decimal('0.000001'),rounding=ROUND_HALF_UP),unit,ids,formula,h)
