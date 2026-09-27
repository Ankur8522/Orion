from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class PortfolioImpact:
    security_id: str
    exposure_weight: float
    thesis_status: str
    priority_score: float
    action: str

def assess(security_id, exposure_weight, thesis_status, priority_score):
    if not 0 <= exposure_weight <= 1: raise ValueError('INVALID_EXPOSURE')
    if not 0 <= priority_score <= 100: raise ValueError('INVALID_PRIORITY')
    if thesis_status == 'RED': action='REVIEW_NOW'
    elif priority_score >= 70: action='RESEARCH_PRIORITY'
    elif priority_score >= 40: action='WATCH'
    else: action='ROUTINE'
    return PortfolioImpact(security_id,float(exposure_weight),thesis_status,float(priority_score),action)
