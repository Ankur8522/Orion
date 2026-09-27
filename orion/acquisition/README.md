# Acquisition layer

v137 adds deterministic source planning and safe execution contracts.

**Important:** the planner never invents URLs or live data. Provider-specific discovery must resolve a real URL before execution. Public HTTP fetching remains HTTPS + host allowlisted and bounded.
