# Stockholm Pendeltåg — isolated prototype

The currently published Stockholm Rail application remains untouched until the dedicated deployment succeeds.

## What is genuinely grounded
- **Timetable:** public, archived GTFS Sverige 2 historical timetable from Trafiklab/Samtrafiken. No API key. These were real *past* scheduled services; the archive's weekdays are repeated as a simulation of today, **not today's confirmed timetable**.
- **Track:** OpenStreetMap connected railway-node geometry, accepted only when all listed stops snap within 240 m to a connected OSM railway graph, whose node-by-node path passes a speed sanity check, and simulated peak speed is plausible.
- **Trains:** exclusively `mode=commuter`; no buses, metro, trams, long-distance services, or invented fallback trains.
- **Vehicle icons:** original photo-like Pendeltåg train-front sprite, small and rendered from a cached image.
- **Position:** inferred along track from station departure and arrival times, with dwell, acceleration and deceleration; not actual GPS.
- **Speed:** computed from the derivative of the same motion model; km/h estimated, zero when waiting at a station.
- **Route:** blue travelled track and grey remaining track are trimmed from the very same validated geometry.
- **Follow:** independently animated smooth camera.
- **Occupancy:** stable, explicitly modelled percentage, varying by station/time of day.
- **Satellite:** existing working layer switch.

## Important accuracy limit
**A keyless historical timetable + OSM tracks cannot show exactly where the real Pendeltåg is right now.** To achieve the user's requirement of actual train positions and today's exact service pattern, we will need an authorized current static feed and ideally GTFS-RT VehiclePositions, a comparable legitimate realtime provider, or a verified directly published open dataset. We do not call a position 'live' when it is predicted.

## Deploy
Open **Actions → Build Stockholm Pendeltåg - Isolated Preview**, choose `main`, then **Run workflow**. The workflow checks out `feature/pendeltag-only-v1`.

The build **will fail instead of deploying** if fewer than 12 historical Pendeltåg trips can be validated against OSM geometry. This is a quality gate, not a bug in GitHub Pages.

## Sources
- https://www.trafiklab.se/api/gtfs-datasets/gtfs-sverige-2/
- https://www.trafiklab.se/docs/using-trafiklab-data/frequently-asked-questions/
- https://openstreetmap.tools/public_transport_geojson/docs
- https://www.openstreetmap.org/copyright

## Next steps only after full OSM data checks
If the quality gate fails, investigate which relation matches failed. Do **not** relax the tests to pass by drawing invented lines; instead acquire a better directional rail shape feed or explicit geOps permission.
