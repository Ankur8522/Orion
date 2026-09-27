from __future__ import annotations
from dataclasses import dataclass
import time
from typing import Callable, TypeVar

T=TypeVar('T')

@dataclass(frozen=True)
class RetryPolicy:
    max_attempts:int=3
    base_delay_seconds:float=0.25
    max_delay_seconds:float=4.0
    retryable_statuses:tuple[int,...]=(408,425,429,500,502,503,504)

class RateLimiter:
    def __init__(self, min_interval_seconds:float=0.5):
        if min_interval_seconds < 0: raise ValueError('INVALID_RATE_LIMIT')
        self.min_interval_seconds=min_interval_seconds
        self._last:float|None=None
    def wait(self, clock:Callable[[],float]=time.monotonic, sleeper:Callable[[float],None]=time.sleep):
        now=clock()
        if self._last is not None:
            remaining=self.min_interval_seconds-(now-self._last)
            if remaining>0: sleeper(remaining)
        self._last=clock()

def with_retry(fn:Callable[[],T], policy:RetryPolicy, is_retryable:Callable[[Exception],bool]|None=None, sleeper=time.sleep)->T:
    if policy.max_attempts<1: raise ValueError('INVALID_RETRY_POLICY')
    last=None
    for attempt in range(1,policy.max_attempts+1):
        try: return fn()
        except Exception as exc:
            last=exc
            if attempt>=policy.max_attempts or (is_retryable and not is_retryable(exc)): raise
            delay=min(policy.max_delay_seconds, policy.base_delay_seconds*(2**(attempt-1)))
            sleeper(delay)
    raise last
