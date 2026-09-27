from __future__ import annotations
import re
from .contracts import DocumentKind

_PATTERNS=(
    (DocumentKind.AUDITOR_REPORT, (r'\bindependent auditor', r'\bauditor.?s report', r'basis for opinion')),
    (DocumentKind.FINANCIAL_RESULTS, (r'audited financial results', r'unaudited financial results', r'statement of profit', r'cash flow statements')),
    (DocumentKind.INVESTOR_PRESENTATION, (r'analyst meet', r'investor presentation', r'analyst conference call', r'investor relations')),
    (DocumentKind.BOARD_DISCLOSURE, (r'outcome of board meeting', r'regulation 30', r'regulation 33', r'board of directors')),
    (DocumentKind.CORPORATE_ACTION, (r'buyback', r'dividend', r'bonus issue', r'split', r'rights issue', r'merger')),
    (DocumentKind.ANNUAL_REPORT, (r'annual report', r'board.s report', r'corporate governance report')),
)

def classify_document(text:str, media_type:str='') -> tuple[DocumentKind,float]:
    body=(text or '').lower()
    scores={k:0 for k,_ in _PATTERNS}
    for kind,pats in _PATTERNS:
        for pat in pats:
            if re.search(pat,body): scores[kind]+=1
    best=max(scores,key=scores.get) if scores else DocumentKind.OTHER
    hits=scores.get(best,0)
    if hits==0: return DocumentKind.OTHER,0.35
    confidence=min(0.55+0.12*hits,0.95)
    if media_type=='application/pdf': confidence=min(confidence+0.03,0.98)
    return best,confidence
