# Stockholm Rail — fresh start (foundation preview)

This is a **new** project, independent of Stockholm Transit V11/V12.

## Quick local browser preview
Run `python3 -m http.server 5173` in this folder, then open http://localhost:5173/.
No API keys, bundles or GTFS downloads required.

## Scope
- Rail only (metro, commuter, intercity), filtered on an interactive geographic map.
- Warm clean light visual design; the old proposed dark map mockup is not used.
- Stockholm clock correctly handles summer and winter time.
- Deterministic interpolation and station-by-station illustrative occupancy.
- Smooth follow mode with continuously eased camera.
- Switch between standard map and satellite imagery (third-party tile services).
- Separate Central Station schematic tab.
- Photographs are **deliberately not faked**: local licensed verified train photos will be imported in the next data/inventory milestone.

## Important
**All currently displayed trips and station platforms are demonstrative fixtures.**
Station connections are dashed straight-line overview segments, not verified rail shapes;
station platform names A–D are placeholders. No claim of live positions or accurate
trip times is made. The next milestone replaces demo fixtures with licensed GTFS and
verified rail geometry, plus a local photo manifest. Satellite and map tiles require internet.

## Checks
`npm test` (or `node --test tests/simulation.test.mjs`).

## Deployment auf GitHub Pages

Siehe [SETUP_GITHUB.md](SETUP_GITHUB.md). Der Workflow `.github/workflows/deploy.yml` prüft den Code und veröffentlicht die statische Vorschau per GitHub Pages. Bei Änderungen an der Vorschau sind keine großen Kartendownloads nötig.