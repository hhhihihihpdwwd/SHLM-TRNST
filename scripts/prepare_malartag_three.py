#!/usr/bin/env python3
"""Publish only the three fully verified Mälartåg corridors from audit 42624208878.

Input: immutable ten-system live snapshot, immutable read-only five-route audit.
Output: exactly three corridor train records and no changes to old services.

Never download OSM, make geometry, edit GTFS times, or publish data for Gävle/Hallsberg.
"""
from __future__ import annotations
import collections
import copy
import json
import sys
from pathlib import Path
from build_malartag_candidates import contains_station
from refine_osm_routes import project_stops
from append_malartag import direction_of

BASE_SCOPE="pendeltag-tunnelbana-tvarbanan-localtram-city7-roslags-saltsjo-arlanda-sj"
CORRIDORS={
 "orebro-uppsala":("örebro","eskilstuna","stockholm","uppsala"),
 "nykoping":("norrköping","nyköping","stockholm"),
 "uven":("linköping","norrköping","katrineholm","eskilstuna","västerås","sala","uppsala"),
}
EXPECTED_DAILY={"orebro-uppsala":35,"nykoping":40,"uven":69}
EXPECTED_DAYS={"2026-11-08","2026-11-09","2026-11-10"}
VERIFIED={"verified-osm-relation","verified-osm-rail-ways"}

def prepare(live,audit):
 assert live["scope"]==BASE_SCOPE, "wrong production base"
 assert live["type"]=="historical-daily-repeating-simulation"
 assert len(live["trips"])==9957,"wrong snapshot; do not overwrite newer production"
 assert live["counts"]["intercity"]==56 and live["tramLines"]["21"]>350
 assert audit["scope"]==BASE_SCOPE+"-malartag", "incorrect source audit"
 assert audit["trips"][:len(live["trips"])]==live["trips"],"source audit altered old rides"
 assert all(audit["shapes"].get(k)==v for k,v in live["shapes"].items()),"old shape changed"
 assert all(audit["counts"].get(k)==v for k,v in live["counts"].items()),"old count changed"
 for key in ("metroLines","tramLines","roslagsLines","saltsjoLines",
             "arlandaDirections","sjDirections","localTramDirections"):
  assert audit[key]==live[key],"audited baseline altered: "+key
 source=audit["trips"][len(live["trips"]):]
 # Pinned 42624208878 audit predates a later direction-field addition.
 # Infer exactly as its original import did, from authentic ordered GTFS stops.
 extra=[{**t,"direction":t.get("direction") or direction_of(t)} for t in source]
 assert all(t["corridor"] in CORRIDORS for t in extra),"unverified corridor sneaked into audit"
 assert len(extra)==3*sum(EXPECTED_DAILY.values())==432,"expected 432 actual verifications"
 assert len({t["id"] for t in extra})==len(extra),"duplicate regional trip IDs"
 new=copy.deepcopy(live)
 tally=collections.Counter()
 directions=collections.defaultdict(lambda:collections.Counter())
 used_shapes=set()
 previous_timetables=set(t["id"] for t in live["trips"])
 for t in extra:
  k=t["corridor"];day=t["serviceDay"];dr=t.get("direction")
  assert day in EXPECTED_DAYS,(k,day)
  assert dr in ("forward","reverse"),(k,dr)
  assert t["mode"]=="regional" and t["agency"]=="Mälartåg"
  assert t["geometryQuality"] in VERIFIED
  assert t["archiveDay"]=="2026-11-06"
  assert t["id"] not in previous_timetables
  assert t["end"]>t["start"] and len(t["stops"])>=2
  sid=t["shapeId"];shape=audit["shapes"].get(sid)
  assert shape and len(shape)>=5,(k,"geometry unavailable",sid)
  if t["geometryQuality"]=="verified-osm-rail-ways":
   assert t.get("osmWayNetwork") is True and t.get("osmRelation") is None
  else:
   assert t.get("osmRelation"),(k,"missing relation provenance")
  used_shapes.add(sid)
  tally[(k,day)]+=1
  directions[k][dr]+=1
 for k in CORRIDORS:
  for day in EXPECTED_DAYS:
   assert tally[(k,day)]==EXPECTED_DAILY[k],(k,day,tally[(k,day)])
  assert directions[k]["forward"]>0 and directions[k]["reverse"]>0,(k,directions[k])
  assert audit["malartagDirections"].get(k)==dict(directions[k]),(k,"directions mismatch")
  assert audit["malartagCorridors"].get(k)==3*EXPECTED_DAILY[k],(k,"counts mismatch")
  names=[s[2] for t in extra if t["corridor"]==k for s in t["stops"]]
  missing=[a for a in CORRIDORS[k] if not any(contains_station(n,a) for n in names)]
  assert not missing,(k,"advertised stations missing",missing)
  assert audit["malartagCoverage"][k]["requiredStops"]==len(CORRIDORS[k])
 checked=set()
 for t in extra:
  signature=(t["shapeId"],tuple((x[0],x[1],x[2]) for x in t["stops"]))
  if signature in checked:continue
  checked.add(signature)
  assert project_stops(t["stops"],audit["shapes"][t["shapeId"]],650) is not None,(
    t["corridor"],t["id"],"GTFS stop order does not follow verified OSM track")
 for sid in used_shapes:
  assert sid not in live["shapes"],("unexpected old shape overwrite",sid)
  new["shapes"][sid]=audit["shapes"][sid]
 new["trips"].extend(extra)
 new["scope"]=BASE_SCOPE+"-malartag"
 new["counts"]["regional"]=len(extra)
 new["malartagCorridors"]={k:3*EXPECTED_DAILY[k] for k in CORRIDORS}
 new["malartagDirections"]={k:dict(directions[k]) for k in CORRIDORS}
 new["malartagCoverage"]={k:audit["malartagCoverage"][k] for k in CORRIDORS}
 assert set(new["malartagCorridors"])==set(CORRIDORS)
 assert new["trips"][:len(live["trips"])]==live["trips"]
 assert all(new["shapes"][k]==v for k,v in live["shapes"].items())
 assert all(new["counts"][k]==v for k,v in live["counts"].items())
 for k in ("metroLines","tramLines","roslagsLines","saltsjoLines",
           "arlandaDirections","sjDirections","localTramDirections"):
  assert new[k]==live[k]
 assert len(new["trips"])==10389
 print("SAFE MÄLARTÅG THREE-CORRIDOR RELEASE VERIFIED")
 print("NEW",len(extra),"3-DAY TRAIN RECORDS; 144 REPRESENTATIVE RIDES/DAY",
       "GEOMETRIES",len(used_shapes),"STOP PATTERNS",len(checked),flush=True)
 for k in CORRIDORS:
  print("VERIFIED",k,"DAILY",EXPECTED_DAILY[k],
        "DIRECTIONS",dict(directions[k]),flush=True)
 print("OLD 10 SYSTEMS IMMUTABLE",len(live["trips"]),"INCLUDING SJ 56 AND LIDINGÖBANAN",flush=True)
 return new

def main():
 if len(sys.argv)!=4:
  raise SystemExit("Usage: prepare_malartag_three.py old.json audited.json output.json")
 a=json.loads(Path(sys.argv[1]).read_text(encoding="utf8"))
 b=json.loads(Path(sys.argv[2]).read_text(encoding="utf8"))
 result=prepare(a,b)
 Path(sys.argv[3]).write_text(json.dumps(result,ensure_ascii=False,separators=(",",":")),encoding="utf8")

if __name__=="__main__":
 main()
