# Saltsjöbanan 25/26 — verification notes

- Reference: 8 November 2026, verified SL public service notice.
- Line 25: Saltsjö-Järla ↔ Saltsjöbaden.
- Line 26: Igelboda ↔ Solsidan.
- SL replacement buses and historic Slussen railway service are excluded.
- Both GTFS stop directions must match the unchanged OSM relation geometry:
  - Line 25 route_master 2705957
  - Line 26 route_master 2705952
- Sunday reference replays historical Saturday departures where Sunday is incomplete; all positions estimated.
- Photos are illustrative, not linked to actual service deployment.
- STABLE 04 is frozen as a separate branch and data snapshot.
- CI checks visibility at 08:47, 12:47, 16:47 for both lines, 20:47 for line 25 only (line 26 has no scheduled run at 20:47).
- No publication until all tests succeed.
