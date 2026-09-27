# ORION v186.0.0 — Institutional Data/Brain Architecture Boundary

## Purpose

v186 addresses structural gaps identified in the v185 audit. It does not claim real-data coverage or empirical trading performance.

## Implemented
- Canonical dataset/domain catalog covering market, fundamentals, valuation, ownership, business, estimates, macro/sector, evidence and universe domains.
- PIT `WorldSnapshot` boundary that assembles a security's information set at one decision timestamp and rejects future observations.
- Read-only Zerodha/Kite provider adapter for instruments, quotes and historical candles. No order endpoints exist.
- Specialist-model ensemble boundary that refuses to publish an empirical probability until the required number of trained specialists is present and tracks model disagreement.
- Regression tests for the new architecture and live-trading safety boundary.

## Explicit non-claims
- No Zerodha credentials are embedded or assumed.
- No fundamental/news/estimate provider is claimed to be connected.
- No empirical accuracy or profitability is claimed.
- The ensemble's static weights are not a substitute for trained meta-learning.
- Live trading remains disabled.
