#!/usr/bin/env python3
"""Add only Snälltåget Friday GTFS journeys verified on original STABLE08 SJ OSM.

Every prior trip, original shape, existing metadata, photo and mode count
remain identical. No fabricated straight connectors, no new OSM relation.
If one direction has no physical track match, fail without altering the site.
"""
from __future__ import annotations
import collections
import copy
import json
import sys
from pathlib import Path
from refine_osm_routes import project_stops

BASE_SCOPE="pendeltag-tunnelbana-tvarbanan-localtram-city7-roslags-saltsjo-arlanda-sj-malartag-vr"
OPERATOR="Snälltåget"
DIRECTIONS=("to-malmo","to-stockholm")
MAX_STOP_ERROR=600

def eligible_shapes(source):
 return [(sid,shape) for sid,shape in source["shapes"].items()
   if sid.startswith("sj-osm:") and isinstance(shape,list) and len(shape)>150]

def integrate(base,candidates):
 if base.get("scope")!=BASE_SCOPE or base.get("type")!="historical-daily-repeating-simulation":
  raise ValueError("Only immutable verified twelve-system STABLE08 accepted")
 if len(base["trips"])!=10402 or base["counts"].get("intercity")!=69:
  raise ValueError("STABLE08 train count does not match exact published site")
 if base.get("vrDirections")!={"to-goteborg":7,"to-stockholm":6}:
  raise ValueError("Existing VR directions changed")
 if set(base.get("malartagDirections",{}))!={"orebro-uppsala","nykoping","uven"}:
  raise ValueError("Existing Mälartåg coverage changed")
 if candidates.get("referenceDay")!="2026-11-06" or candidates.get("operator")!=OPERATOR:
  raise ValueError("Snälltåget journeys not from verified Friday GTFS")
 template=base["simulationTemplateDay"]
 if candidates.get("templateDay")!=template:raise ValueError("Wrong template day")
 shapes=eligible_shapes(base)
 if not shapes:raise ValueError("No verified SJ Stockholm–Malmö original OSM rail tracks")
 patterns={}
 result=[];count=collections.Counter();failed=collections.Counter()
 used_gtfs=set()
 for train in candidates.get("trips",[]):
  if train.get("serviceDay")!=template:continue
  if train.get("mode")!="rail" or train.get("agency")!=OPERATOR:continue
  direction=train.get("direction")
  if direction not in DIRECTIONS:continue
  sid=None
  for key,shape in shapes:
   pattern=(key,tuple((s[0],s[1],s[2]) for s in train["stops"]))
   if pattern not in patterns:
    patterns[pattern]=project_stops(train["stops"],shape,MAX_STOP_ERROR) is not None
   if patterns[pattern]:sid=key;break
  if sid is None:
   failed[direction]+=1
   print("SNALL REJECT NO REAL OSM RAIL",direction,train["id"],
         [s[2] for s in train["stops"]],flush=True)
   continue
  if train["id"] in used_gtfs:raise ValueError("Duplicate historic train ID")
  used_gtfs.add(train["id"])
  result.append({**train,
   "mode":"intercity","agency":OPERATOR,"line":"Snälltåget",
   "shapeId":sid,"geometryQuality":"verified-osm-relation",
   "osmRelation":sid.split(":")[1],
   "isLiveGPS":False
  })
  count[direction]+=1
  print("SNALL VERIFIED GTFS TRAIN",direction,train["id"],"OSM TRACK",sid,
        "ORIGINAL",train["throughOrigin"],"→",train["throughDestination"],flush=True)
 if any(count[k]<1 for k in DIRECTIONS):
  raise ValueError("Snälltåget no real OSM-verified journeys in both directions: "+
    str(dict(count))+" rejected "+str(dict(failed)))
 release=copy.deepcopy(base)
 release["scope"]=BASE_SCOPE+"-snalltaget"
 release["trips"].extend(result)
 release["counts"]["intercity"]+=len(result)
 release["snalltagetDirections"]={k:count[k] for k in DIRECTIONS}
 assert release["trips"][:len(base["trips"])]==base["trips"]
 assert release["shapes"]==base["shapes"]
 assert len(release["trips"])==len(base["trips"])+len(result)
 assert all(release["counts"][k]==v for k,v in base["counts"].items() if k!="intercity")
 for k,v in base.items():
  if k in ("trips","scope","counts"):continue
  assert release[k]==v,"Existing mode data changed: "+k
 print("SNALL VERIFIED NEW TRAINS",len(result),"PER SIMULATED DAY",dict(count),
       "REJECTED",dict(failed),"UNMODIFIED STABLE08",len(base["trips"]),flush=True)
 return release

def main():
 if len(sys.argv)!=4:
  raise SystemExit("Usage: append_snalltaget.py STABLE08.json CANDIDATES.json RELEASE.json")
 orig=json.loads(Path(sys.argv[1]).read_text(encoding="utf8"))
 candidate=json.loads(Path(sys.argv[2]).read_text(encoding="utf8"))
 d=integrate(orig,candidate)
 Path(sys.argv[3]).parent.mkdir(parents=True,exist_ok=True)
 Path(sys.argv[3]).write_text(json.dumps(d,ensure_ascii=False,separators=(",",":")),encoding="utf8")
if __name__=="__main__":main()
