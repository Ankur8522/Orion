# ORION Cockpit UI

Static, responsive investment-intelligence cockpit for ORION v154.

- Demo data is explicitly labelled `DEMO DATA`.
- Core ORION calculations remain in the backend.
- `runtime_adapter.py` defines the JSON bridge shape for an authenticated HTTP gateway.
- No order placement is implemented by this UI.

## v159 runtime-connected cockpit
Run `python -m orion.app.server` from the source root to serve the cockpit on `http://127.0.0.1:8787`. The UI polls `/api/state` and `/api/health`; if the runtime is unavailable it explicitly falls back to OFFLINE mode rather than presenting live-looking data.
