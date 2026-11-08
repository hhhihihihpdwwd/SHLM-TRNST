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
