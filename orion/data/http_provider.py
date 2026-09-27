from __future__ import annotations
import json, time
from dataclasses import dataclass
from urllib.request import Request, urlopen, HTTPRedirectHandler, build_opener
from urllib.parse import urlencode, urlparse
from .providers import hash_payload

class _SafeRedirect(HTTPRedirectHandler):
    def __init__(self, allowed): self.allowed=allowed
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        p=urlparse(newurl)
        if p.scheme!='https' or p.hostname not in self.allowed: raise ValueError('REDIRECT_NOT_ALLOWLISTED')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

@dataclass(frozen=True)
class FetchResult:
    url: str; status: int; content_type: str; payload: bytes; sha256: str; fetched_at: str

class PublicHTTPProvider:
    def __init__(self, allowed_hosts: set[str], user_agent='ORION/130 research-client', max_bytes=10_000_000):
        self.allowed_hosts=set(allowed_hosts); self.user_agent=user_agent; self.max_bytes=max_bytes
        self.opener=build_opener(_SafeRedirect(self.allowed_hosts))
    def fetch(self,url:str,params:dict[str,str]|None=None,timeout=20):
        p=urlparse(url)
        if p.scheme!='https' or p.hostname not in self.allowed_hosts: raise ValueError('URL_NOT_ALLOWLISTED')
        if params: url += ('&' if '?' in url else '?') + urlencode(params)
        req=Request(url,headers={'User-Agent':self.user_agent,'Accept':'application/json,text/html,*/*'})
        with self.opener.open(req,timeout=timeout) as r:
            length=r.headers.get('Content-Length')
            if length and int(length)>self.max_bytes: raise ValueError('RESPONSE_TOO_LARGE')
            payload=r.read(self.max_bytes+1)
            if len(payload)>self.max_bytes: raise ValueError('RESPONSE_TOO_LARGE')
            return FetchResult(r.geturl(),r.status,r.headers.get_content_type(),payload,hash_payload(payload),time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    @staticmethod
    def json(result:FetchResult): return json.loads(result.payload.decode('utf-8'))
