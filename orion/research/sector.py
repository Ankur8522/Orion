from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class MetricSnapshot:
    security_id: str
    metrics: dict[str, Decimal]
    warnings: tuple[str, ...]

def _d(v):
    return Decimal(str(v))

def derive_metrics(security_id: str, facts: dict[str, object]) -> MetricSnapshot:
    """Generic cross-sector financial quality metrics; missing inputs remain explicit."""
    m={k:_d(v) for k,v in facts.items()}
    warnings=[]
    if 'revenue' in m and m['revenue'] == 0: warnings.append('ZERO_REVENUE')
    if 'pat' in m and 'revenue' in m and m['revenue'] != 0: m['net_margin']=m['pat']/m['revenue']
    if 'ebitda' in m and 'revenue' in m and m['revenue'] != 0: m['ebitda_margin']=m['ebitda']/m['revenue']
    if 'cfo' in m and 'pat' in m and m['pat'] != 0: m['cfo_pat']=m['cfo']/m['pat']
    if 'receivables' in m and 'revenue' in m and m['revenue'] != 0: m['receivables_to_revenue']=m['receivables']/m['revenue']
    if 'debt' in m and 'ebitda' in m and m['ebitda'] != 0: m['debt_ebitda']=m['debt']/m['ebitda']
    if 'cash' in m and 'debt' in m: m['net_debt']=m['debt']-m['cash']
    return MetricSnapshot(security_id,m,tuple(warnings))

class SectorMetricEngine:
    """Routes sector-specific metric derivation without pretending absent data exists."""
    def run(self, security_id: str, sector: str, facts: dict[str, object]) -> MetricSnapshot:
        s=(sector or 'generic').lower()
        snap=derive_metrics(security_id,facts)
        extra=[]
        required={
            'banking':('nim','gnpa','nnpa','pcr','casa','credit_cost','loan_growth'),
            'it':('tcv','utilisation','attrition','revenue','ebitda'),
            'capital_goods':('order_book','revenue','receivables','capex'),
            'pharma':('revenue','us_growth','anda_pipeline'),
            'metals':('realised_price','ebitda_per_tonne','spread'),
            'auto':('volume','asp','revenue','ebitda'),
            'consumer':('volume_growth','revenue','ebitda'),
            'real_estate':('bookings','collections','net_debt'),
        }.get(s,())
        for key in required:
            if key not in facts: extra.append('MISSING_'+key.upper())
        return MetricSnapshot(security_id,snap.metrics,tuple(sorted(set(snap.warnings+tuple(extra)))))
