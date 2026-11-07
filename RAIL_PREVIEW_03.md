# Stockholm Rail — Rail Preview 03

This release is intentionally isolated from the working Preview 02.

## What's implemented
- Read actual SL GTFS Regional static schedules and only draw rail services that have source-provided `shapes.txt`.
- Monotonic station-to-shape projection to avoid jumping backwards along a line.
- Colour travelled selected route blue and untravelled part grey, both following published geometries.
- Smooth camera following and viewport culling to reduce marker work.
- 20 previously approved rail photo references; download optimised local WebP assets and include attribution.
- Timetable stops, deterministic illustrative occupancy, Stockholm time zone.
- Existing station schematic is still demo-only and not a real platform allocation.
- Existing Preview 02 remains intact until the new deployment passes.

## Required, one-time GitHub setup
1. Create/reuse a key for **GTFS Regional SL (Static)** at https://developer.trafiklab.se/.
2. Open this repository's **Settings → Secrets and variables → Actions → New repository secret**.
3. Secret name: `GTFS_SL_KEY`. Paste the API key as the secret's value. Never add a key to the repository or chat.
4. Run the Actions workflow **Deploy Stockholm Rail - Real Rail Preview** on branch `main`.
5. This build will download the current SL feed, validate actual shape-backed rail trips, build verified local photos and only then update GitHub Pages.

## Current limits
- This is *scheduled* data, not GPS or realtime tracking.
- It uses the SL regional data feed. National intercity rail in GTFS Sweden 3 is not included, because Trafiklab reports that these trains often lack actual shapes/platforms as of spring 2026. A separate verified operator feed / Trafikverket integration is required.
- No inference of platform allocation for Stockholm Central yet.
- Stops with a poor shape match are omitted, never joined by invented straight tracks.
- Local photo import may omit an image if Wikimedia is unavailable; a truthful placeholder appears instead.
- The published output is intentionally a static rail snapshot and needs a new build for refreshed timetables.

Sources:
- https://www.trafiklab.se/api/gtfs-datasets/gtfs-regional
- https://www.trafiklab.se/docs/using-trafiklab-data/frequently-asked-questions/
