from orion.acquisition.public_adapters import NSEPublicDiscoveryAdapter, NSEAnnouncementDiscoveryAdapter, LicensedBSEDiscoveryAdapter
from orion.acquisition.contracts import AcquisitionJob, AcquisitionState
from orion.acquisition.discovery import DiscoveryRegistry
from orion.acquisition.orchestrator import AcquisitionPreparer
from orion.acquisition.fetch_policy import RetryPolicy, with_retry, RateLimiter
from orion.acquisition.filing_links import extract_official_links


def make_job(source,dataset):
    return AcquisitionJob('j1','TCS',source,dataset,'https://placeholder.invalid','2026-09-26T00:00:00Z','2026-09-26T00:00:00Z','2026-09-26T00:00:00Z',metadata={'requires_discovery':'true'})

def test_nse_financial_discovery_is_official_and_executable():
    r=DiscoveryRegistry(); r.register(NSEPublicDiscoveryAdapter())
    out=AcquisitionPreparer(r).prepare(make_job('nse-public','financial_results'),'2026-09-26T00:00:00Z')
    assert out.state==AcquisitionState.PLANNED
    assert out.job.url.startswith('https://www.nseindia.com/companies-listing/corporate-filings-financial-results')
    assert 'requires_discovery' not in out.job.metadata

def test_nse_announcement_discovery():
    r=DiscoveryRegistry(); r.register(NSEAnnouncementDiscoveryAdapter())
    out=AcquisitionPreparer(r).prepare(make_job('nse-public','corporate_disclosures'),'2026-09-26T00:00:00Z')
    assert out.state==AcquisitionState.PLANNED and 'corporate-filings-announcements' in out.job.url

def test_bse_never_guesses_undocumented_endpoint():
    a=LicensedBSEDiscoveryAdapter(); result=a.discover('500325','j','2026-09-26T00:00:00Z')
    assert result.status=='BLOCKED' and result.reason=='BSE_LICENSED_ENDPOINT_REQUIRED'

def test_filing_link_extractor_allowlists_hosts():
    html='<a href="/x.pdf">Financial Results PDF</a><a href="https://evil.example/x.pdf">Result</a>'
    links=extract_official_links(html,'https://www.nseindia.com/page',{'www.nseindia.com'})
    assert len(links)==1 and links[0].url=='https://www.nseindia.com/x.pdf'

def test_retry_retries_transient_failure():
    state={'n':0}
    def fn():
        state['n']+=1
        if state['n']<3: raise RuntimeError('temporary')
        return 'ok'
    assert with_retry(fn,RetryPolicy(max_attempts=3,base_delay_seconds=0),sleeper=lambda _:None)=='ok'
    assert state['n']==3

def test_rate_limiter_deterministic():
    calls=[]
    clock_values=iter([0.0,0.0,0.0,0.0])
    limiter=RateLimiter(1.0)
    limiter.wait(clock=lambda:next(clock_values),sleeper=lambda x:calls.append(x))
    limiter.wait(clock=lambda:next(clock_values),sleeper=lambda x:calls.append(x))
    assert calls==[1.0]
