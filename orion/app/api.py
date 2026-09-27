from dataclasses import dataclass
from time import monotonic

from orion.brain.progressive import Belief, Challenge, MarketState, ProgressiveDecisionBrain
from orion.portfolio.allocation import AllocationCandidate, DynamicCapitalAllocationBrain

@dataclass(frozen=True)
class RequestContext:
    user_id: str
    request_id: str
    role: str

class API:
    def __init__(self, max_ids=500, rate_limit=30, window_seconds=60):
        self._requests={}; self._seen={}; self.max_ids=max_ids; self.rate_limit=rate_limit; self.window_seconds=window_seconds; self._hits={}
        self._brain = ProgressiveDecisionBrain()
        self._allocator = DynamicCapitalAllocationBrain()
    def authorize(self, ctx: RequestContext, action: str):
        if ctx.role not in {'analyst','admin'}: raise PermissionError('FORBIDDEN')
        return True
    def _rate_check(self,user_id):
        now=monotonic(); hits=[t for t in self._hits.get(user_id,[]) if now-t < self.window_seconds]
        if len(hits)>=self.rate_limit: raise RuntimeError('RATE_LIMITED')
        hits.append(now); self._hits[user_id]=hits
    def research_request(self, ctx: RequestContext, security_ids):
        self.authorize(ctx,'research'); self._rate_check(ctx.user_id)
        ids=tuple(dict.fromkeys(security_ids))
        if not ids: raise ValueError('EMPTY_UNIVERSE')
        if len(ids)>self.max_ids: raise ValueError('REQUEST_TOO_LARGE')
        existing=self._seen.get(ctx.request_id)
        if existing is not None:
            if existing[0] != ctx.user_id or existing[1] != ids: raise PermissionError('REQUEST_ID_REUSE')
            return existing[2]
        result={'request_id':ctx.request_id,'count':len(ids),'status':'QUEUED'}
        self._requests[ctx.request_id]=(ctx.user_id,ids); self._seen[ctx.request_id]=(ctx.user_id,ids,result)
        return result
    def progressive_assessment(self, ctx, belief: Belief, challenges=(), scenario_score=0.5, calibration_score=0.5, market_state=None):
        self.authorize(ctx, 'research'); self._rate_check(ctx.user_id)
        return self._brain.assess(belief, tuple(challenges), scenario_score, calibration_score, market_state)

    def allocation_assessment(self, ctx, candidates, max_weight=0.25, cash_floor=0.0, min_weight=0.0):
        self.authorize(ctx, 'portfolio'); self._rate_check(ctx.user_id)
        return self._allocator.assess(tuple(candidates), max_weight=max_weight, cash_floor=cash_floor, min_weight=min_weight)

    def get_request(self, ctx, request_id):
        row=self._requests.get(request_id)
        if row is None: raise KeyError('NOT_FOUND')
        if row[0]!=ctx.user_id: raise PermissionError('REQUEST_ISOLATION')
        return row
