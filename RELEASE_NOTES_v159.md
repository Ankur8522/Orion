# ORION v159 — Full Runtime + UI/UX Completion

v159 closes the main remaining application gaps above v158 without claiming a live market feed.

## Architecture
- UniverseOperatingRuntime connects deterministic universe scheduling, production research and the decision control plane.
- Persistent paper execution survives restart and covers order → fill → position → mark-to-market P&L.
- RuntimeGateway exposes a read-oriented JSON state contract for the cockpit.
- Standard-library HTTP server serves the UI and `/api/health` + `/api/state`.
- Runtime health explicitly validates journal integrity and live-trading-off invariant.

## UI/UX
- Cockpit is runtime-connected instead of hard-coded as the primary state source.
- Runtime mode, health, paper P&L, journal integrity, brain capabilities and live-trading boundary are visible.
- Refresh pulls `/api/state`; if no runtime server is available the UI stays clearly in offline/demo mode.
- Added Operations view for runtime, queue, audit and paper lifecycle visibility.

## Boundaries
- No synthetic market facts are presented as live data.
- Live broker execution remains disabled.
- Missing company/evidence inputs remain BLOCKED.
