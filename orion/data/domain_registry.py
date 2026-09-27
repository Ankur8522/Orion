from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

class DatasetDomain(str, Enum):
    MARKET = 'market'
    FUNDAMENTAL = 'fundamental'
    VALUATION = 'valuation'
    OWNERSHIP = 'ownership'
    BUSINESS = 'business'
    ESTIMATES = 'estimates'
    SECTOR_MACRO = 'sector_macro'
    EVIDENCE = 'evidence'
    UNIVERSE = 'universe'

@dataclass(frozen=True)
class DatasetSpec:
    name: str
    domain: DatasetDomain
    required_for_trade: bool = False
    pit_required: bool = True
    historical_required: bool = False

# This is a contract/catalog, not a claim that the datasets are currently available.
DATASET_CATALOG = (
    DatasetSpec('ohlcv', DatasetDomain.MARKET, True, True, True),
    DatasetSpec('volume', DatasetDomain.MARKET, True, True, True),
    DatasetSpec('corporate_actions', DatasetDomain.MARKET, True, True, True),
    DatasetSpec('financial_statements', DatasetDomain.FUNDAMENTAL, True, True, True),
    DatasetSpec('quarterly_results', DatasetDomain.FUNDAMENTAL, True, True, True),
    DatasetSpec('cash_flow', DatasetDomain.FUNDAMENTAL, True, True, True),
    DatasetSpec('balance_sheet', DatasetDomain.FUNDAMENTAL, True, True, True),
    DatasetSpec('valuation', DatasetDomain.VALUATION, True, True, True),
    DatasetSpec('promoter_shareholding', DatasetDomain.OWNERSHIP, True, True, True),
    DatasetSpec('institutional_flows', DatasetDomain.OWNERSHIP, False, True, True),
    DatasetSpec('order_book', DatasetDomain.BUSINESS, False, True, True),
    DatasetSpec('business_visibility', DatasetDomain.BUSINESS, False, True, True),
    DatasetSpec('earnings_estimates', DatasetDomain.ESTIMATES, False, True, True),
    DatasetSpec('sector', DatasetDomain.SECTOR_MACRO, True, True, True),
    DatasetSpec('macro_sensitivity', DatasetDomain.SECTOR_MACRO, False, True, True),
    DatasetSpec('news_evidence', DatasetDomain.EVIDENCE, False, True, True),
    DatasetSpec('universe_membership', DatasetDomain.UNIVERSE, True, True, True),
)

class DatasetCatalog:
    def __init__(self, specs: Iterable[DatasetSpec] = DATASET_CATALOG):
        self._specs = {s.name: s for s in specs}
    def get(self, name: str) -> DatasetSpec | None: return self._specs.get(name)
    def names(self) -> tuple[str, ...]: return tuple(sorted(self._specs))
    def required(self) -> tuple[DatasetSpec, ...]: return tuple(s for s in self._specs.values() if s.required_for_trade)
    def domain(self, name: str) -> DatasetDomain:
        spec = self.get(name)
        if spec is None: raise KeyError(f'UNKNOWN_DATASET:{name}')
        return spec.domain
