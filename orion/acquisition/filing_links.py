from __future__ import annotations
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
import re

@dataclass(frozen=True)
class FilingLink:
    url:str
    label:str
    kind:str
    confidence:float

class _LinkParser(HTMLParser):
    def __init__(self): super().__init__(); self.items=[]; self._href=None; self._text=[]
    def handle_starttag(self,tag,attrs):
        if tag.lower()=='a':
            self._href=dict(attrs).get('href'); self._text=[]
    def handle_data(self,data):
        if self._href is not None: self._text.append(data)
    def handle_endtag(self,tag):
        if tag.lower()=='a' and self._href:
            self.items.append((self._href,' '.join(self._text).strip()))
            self._href=None; self._text=[]

def extract_official_links(html:str, base_url:str, allowed_hosts:set[str]) -> tuple[FilingLink,...]:
    p=_LinkParser(); p.feed(html)
    out=[]
    for href,label in p.items:
        url=urljoin(base_url,href)
        parsed=urlparse(url)
        if parsed.scheme!='https' or parsed.hostname not in allowed_hosts: continue
        blob=(label+' '+url).lower()
        if not re.search(r'(pdf|xbrl|result|financial|announcement|attachment|annual)',blob): continue
        kind='financial_result' if re.search(r'financial|result',blob) else 'corporate_filing'
        out.append(FilingLink(url,label,kind,0.9 if kind=='financial_result' else 0.75))
    # deterministic de-duplication
    seen=set(); dedup=[]
    for item in sorted(out,key=lambda x:(-x.confidence,x.url)):
        if item.url not in seen: seen.add(item.url); dedup.append(item)
    return tuple(dedup)
