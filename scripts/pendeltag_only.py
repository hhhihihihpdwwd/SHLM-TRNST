#!/usr/bin/env python3
"""Publish only verified Pendeltåg rail geometry. No synthetic line fallback."""
import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"data/rail.json"
d=json.loads(p.read_text(encoding="utf-8"))
trips=[t for t in d["trips"] if t.get("mode")=="commuter" and t.get("geometryQuality")=="verified-osm-relation"]
if not trips:
    report=d.get("routeRefinement",{})
    print("OSM diagnostic:",json.dumps(report,ensure_ascii=False),flush=True)
    raise SystemExit("FAIL CLOSED: no verified Pendeltåg tracks. Check OSM PINNED ROUTES and OSM diagnostic logs; no fake tracks will be published.")
# Prevent a train headed for Uppsala from silently stopping at the old
# 59.80° archive cutoff. A verified service must actually contain its
# advertised endpoint at the correct northern latitude.
def ends_at_uppsala(trip):
    last=trip["stops"][-1]
    return "uppsala" in last[2].casefold() and last[0]>=59.80

source_uppsala=[t for t in d["trips"] if t.get("mode")=="commuter"
                and "uppsala" in t.get("destination","").casefold()]
verified_uppsala=[t for t in trips if "uppsala" in t.get("destination","").casefold()
                  and ends_at_uppsala(t)]
invalid_uppsala=[t for t in trips if "uppsala" in t.get("destination","").casefold()
                 and not ends_at_uppsala(t)]
if source_uppsala and (not verified_uppsala or invalid_uppsala):
    print("UPPSALA TERMINAL QUALITY GATE:",len(source_uppsala),
          "source trips,",len(verified_uppsala),"verified complete,",
          len(invalid_uppsala),"invalid",flush=True)
    raise SystemExit("FAIL CLOSED: Uppsala-bound trains lack a complete verified path to Uppsala Centralstation.")
print("TERMINAL AUDIT: Uppsala verified through final station:",len(verified_uppsala),flush=True)

used={t["shapeId"] for t in trips}
d["trips"]=trips
d["shapes"]={k:v for k,v in d["shapes"].items() if k in used}
d["counts"]={"commuter":len(trips)}
d["geometryQuality"]="verified-osm-relation"
d["routeRefinement"]={"verifiedTrips":{"commuter":len(trips)},"estimatedTrips":0}
d["scope"]="pendeltag-only"
d["positionSource"]="historical-timetable-interpolation-not-live-gps"
p.write_text(json.dumps(d,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
print("PENDELTÅG VERIFIED ONLY:",len(trips),"trips",len(used),"shapes")
