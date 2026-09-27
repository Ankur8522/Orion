from __future__ import annotations
from dataclasses import dataclass
from urllib.parse import urlencode
from datetime import datetime, timezone
from .discovery import DiscoveryResult

NSE_HOST = 'www.nseindia.com'
NSE_RESULTS = 'https://www.nseindia.com/companies-listing/corporate-filings-financial-results'
NSE_ANNOUNCEMENTS = 'https://www.nseindia.com/companies-listing/corporate-filings-announcements'


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')

@dataclass(frozen=True)
class NSEPublicDiscoveryAdapter:
    """Official NSE public filing-page resolver.

    It resolves a symbol to an official NSE query page; it does not invent a
    filing attachment URL. A downstream filing-link extractor must promote a
    concrete attachment after validating its host and metadata.
    """
    source_id: str = 'nse-public'
    dataset: str = 'financial_results'
    min_confidence: float = 0.98

    def discover(self, security_id: str, job_id: str, decision_time: str) -> DiscoveryResult:
        if not security_id or any(c.isspace() for c in security_id):
            return DiscoveryResult(job_id,None,self.source_id,_now(),0.0,'BLOCKED','INVALID_NSE_SYMBOL')
        base = NSE_RESULTS if self.dataset == 'financial_results' else NSE_ANNOUNCEMENTS
        url = base + '?' + urlencode({'symbol': security_id.upper(), 'tabIndex': 'equity'})
        return DiscoveryResult(job_id,url,self.source_id,_now(),self.min_confidence,'DISCOVERED','OFFICIAL_NSE_FILING_PAGE')

@dataclass(frozen=True)
class NSEAnnouncementDiscoveryAdapter(NSEPublicDiscoveryAdapter):
    dataset: str = 'corporate_disclosures'

@dataclass(frozen=True)
class LicensedBSEDiscoveryAdapter:
    """BSE corporate-data boundary.

    BSE exposes corporate data through subscription/API products. ORION does
    not guess undocumented endpoints. Supply an approved endpoint template
    through deployment configuration when licensed access exists.
    """
    endpoint_template: str | None = None
    source_id: str = 'bse-licensed'
    dataset: str = 'financial_results'

    def discover(self, security_id: str, job_id: str, decision_time: str) -> DiscoveryResult:
        if not self.endpoint_template:
            return DiscoveryResult(job_id,None,self.source_id,_now(),0.0,'BLOCKED','BSE_LICENSED_ENDPOINT_REQUIRED')
        url = self.endpoint_template.format(security_id=security_id)
        return DiscoveryResult(job_id,url,self.source_id,_now(),0.99,'DISCOVERED','CONFIGURED_LICENSED_ENDPOINT')
