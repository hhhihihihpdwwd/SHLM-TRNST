# Stockholm Rail — Rail Preview 03 (keyless historical rail mode)

The existing working Preview 02 remains deployed until this build completes successfully.

## What Preview 03 contains
- A **public, free** GTFS Sverige 2 historical archive download with **no API key**.
- Timetabled trains and station calls from the historical archive, mapped by weekday to the current week for an immersive private simulator.
- No buses or ferries; metro, commuter, regional/long-distance rail and tram modes only.
- Vehicle positions between historical station stops are **estimated**.
- Because GTFS Sverige 2 does not include `shapes.txt`, routes are **dashed schematic stop-to-stop connectors**, not verified railway geometry. Never label them as mapped OSM/GTFS tracks.
- The map's standard/satellite switch, smooth following and modeled occupancy.
- Twenty previously approved rail photo sources, imported as local optimised WebP files where accessible. Unavailable photos get a neutral placeholder.
- Automated checks include synthetic keyless GTFS archive validation, JS simulation, timezone and route simulation tests.

## Deploy
1. Open GitHub → Actions → **Deploy Stockholm Rail - Real Rail Preview** (workflow name retained for continuity).
2. Run workflow on `main`; the script checks out the `feature/rail-gtfs-foundation` branch.
3. Wait for both build and deploy to succeed, then refresh GitHub Pages.

No `GTFS_SL_KEY` is needed. You may leave or remove the existing secret independently.

## Data provenance
Historical source: https://data.samtrafiken.se/trafiklab/gtfs-sverige-2/2026/11/sweden-20261104.zip
Official dataset description: https://www.trafiklab.se/api/trafiklab-apis/gtfs-sverige-2/
The archive is a **past timetable**, not a source for live departures or observed train locations. A weekday's 2026-11-09 to 2026-11-15 schedule is repeated for matching present weekdays; holidays and later changes will not be reflected.

## Remaining work
- Build an accurately routable rail geometry library from OSM / verified operator feeds.
- Integrate genuine photographed model matching for more operators and a richer station-level view.
- Stockholm Central platform allocations require separate verified Trafikverket data.
