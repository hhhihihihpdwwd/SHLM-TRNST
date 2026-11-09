#!/usr/bin/env python3
"""Append only VR trains whose original GTFS stops fit existing verified SJ OSM rails.

No new track is fabricated; reuse immutable Stockholm-Göteborg physical OSM
geometry that already passed the successful SJ rollout. All 11 old systems,
their stops, all times, route lines and photos remain byte-for-byte equivalent.
"""
from __future__ import annotations
import collections
import copy
import json
import sys
from pathlib import Path
from refine_osm_routes import project_stops

BASE_SCOPE="pendeltag-tunnelbana-tvarbanan-localtram-city7-roslags-saltsjo-arlanda-sj-malartag"
OPERATOR="VR Snabbtåg"
MAX_STOP_ERROR_METRES=500
REAL_OSM_RELATIONS=("21493221","21493220")
DIRECTIONS=("to-goteborg","to-stockholm")

def eligible_shapes(original):
 result=[]
 for sid,shape in original.get("shapes",{}).items():
  if not sid.startswith("sj-osm:") or not any(sid.startswith("sj-osm:"+rid) for rid in REAL_OSM_RELATIONS):
   continue
  if isinstance(shape,list) and len(shape)>25:
   result.append((sid,shape))
 if not result:raise ValueError("Pinned STABLE07 has no real SJ Stockholm–Göteborg OSM tracks")
 return result

def integrate(original,candidates,verified_bridge=None):
 if original.get("scope")!=BASE_SCOPE:
  raise ValueError("Refuse to modify any baseline other than pinned eleven-system STABLE 07")
 if original.get("type")!="historical-daily-repeating-simulation":
  raise ValueError("VR integration requires the existing historic daily replay")
 template=original.get("simulationTemplateDay")
 if not template or candidates.get("templateDay")!=template:
  raise ValueError("VR candidate date does not match frozen eleven-system archive")
 if candidates.get("referenceDay")!="2026-11-06" or candidates.get("operator")!=OPERATOR:
  raise ValueError("VR trains must originate from genuine reference Friday and verified operator")
 if original.get("counts",{}).get("intercity")!=56:
  raise ValueError("Unexpected change to the existing SJ service")
 if set(original.get("malartagDirections",{}))!={"orebro-uppsala","nykoping","uven"}:
  raise ValueError("Unexpected Mälartåg STABLE07 corridors")
 original_sha_copy=copy.deepcopy(original)
 shapes=eligible_shapes(original)
 extra_shapes={}
 if verified_bridge is not None:
  # The companion builder has routed ONLY OSM railway=rail node IDs between
  # two real SJ OSM track vertices. Check the signed source geometry endpoints
  # and refuse any invented station-to-station connector.
  if not verified_bridge.get("osmWayNetwork") or verified_bridge.get("source")!=(
      "Real OSM railway=rail way node IDs + existing verified SJ route relations"):
   raise ValueError("VR bridge is not verified physical OSM rail")
  physical=verified_bridge.get("shape")
  if not isinstance(physical,list) or len(physical)<100:
   raise ValueError("VR physical OSM bridge incomplete")
  left=original["shapes"].get("sj-osm:8860632:reverse")
  right=original["shapes"].get("sj-osm:21493221:reverse")
  if not left or not right or physical[0]!=left[0] or physical[-1]!=right[-1]:
   raise ValueError("VR OSM rail bridge does not meet original SJ real railway endpoints")
  if verified_bridge.get("bridgeNodeCount",0)<10 or verified_bridge.get("maxRealSegmentMetres",9999)>1500:
   raise ValueError("VR OSM railway-way bridge has insufficient connected source nodes")
  for suffix,geometry in (("forward",physical),("reverse",list(reversed(physical)))):
   sid="vr-osm-rail-ways:katrineholm-hallsberg:"+suffix
   if sid in original["shapes"]:raise ValueError("VR would overwrite existing rail shape")
   shapes.insert(0,(sid,geometry))
   extra_shapes[sid]=geometry
 verified=[];counts=collections.Counter()
 rejected=collections.Counter()
 matched_patterns={}
 for t in candidates.get("trips",[]):
  if t.get("agency")!=OPERATOR or t.get("mode")!="rail":continue
  if t.get("serviceDay")!=template:continue
  d=t.get("direction")
  if d not in DIRECTIONS:continue
  matched=None
  for sid,shape in shapes:
   # An OSM relation with the wrong coordinate direction or a skipped stop
   # is NOT sufficient; strict chronological stop projections are required.
   key=(sid,tuple((s[0],s[1],s[2]) for s in t["stops"]))
   if key not in matched_patterns:
    matched_patterns[key]=(project_stops(t["stops"],shape,MAX_STOP_ERROR_METRES) is not None)
   if matched_patterns[key]:
    matched=(sid,shape)
    break
  if matched is None:
   rejected[d]+=1
   print("VR REJECT UNVERIFIED PHYSICAL TRACK",d,t["id"],
         [s[2] for s in t["stops"]],flush=True)
   continue
  sid,_=matched
  from_way_graph=sid.startswith("vr-osm-rail-ways:")
  accepted={**t,
   "mode":"intercity","agency":OPERATOR,"line":"VR",
   "shapeId":sid,
   "geometryQuality":"verified-osm-rail-ways" if from_way_graph else "verified-osm-relation",
   "osmRelation":None if from_way_graph else sid.split(":")[1],
   "osmWayNetwork":from_way_graph,
   "isLiveGPS":False
  }
  verified.append(accepted)
  counts[d]+=1
  print("VR VERIFIED TRAIN",d,accepted["id"],"TRACK",sid,
        "STOPS",len(t["stops"]),flush=True)
 if any(counts[d]<1 for d in DIRECTIONS):
  raise ValueError("VR physical OSM rail verification failed in both directions: "+
                   repr(dict(counts))+" rejected "+repr(dict(rejected)))
 if len({t["id"] for t in verified})!=len(verified):
  raise ValueError("Duplicate real VR journey IDs")
 result=copy.deepcopy(original)
 result["trips"].extend(verified)
 for sid,geo in extra_shapes.items():
  if any(t["shapeId"]==sid for t in verified):result["shapes"][sid]=geo
 result["counts"]["intercity"]+=len(verified)
 result["vrDirections"]={d:counts[d] for d in DIRECTIONS}
 result["scope"]=BASE_SCOPE+"-vr"
 # These checks are necessary before users can trust the previous eleven systems.
 if result["trips"][:len(original["trips"])]!=original_sha_copy["trips"]:
  raise AssertionError("Original eleven-system vehicle timetable mutated")
 if not all(result["shapes"].get(k)==v for k,v in original_sha_copy["shapes"].items()):
  raise AssertionError("Original eleven-system OSM geometries mutated")
 if not all(k in extra_shapes for k in result["shapes"] if k not in original_sha_copy["shapes"]):
  raise AssertionError("Unproven extra rail geometry included")
 for k,v in original_sha_copy.items():
  if k in ("trips","shapes","counts","scope"):continue
  if result.get(k)!=v:raise AssertionError("Original timetable metadata mutated: "+k)
 for key,val in original_sha_copy["counts"].items():
  if key!="intercity" and result["counts"].get(key)!=val:
   raise AssertionError("Original mode count mutated: "+key)
 if result["counts"]["intercity"]!=56+len(verified):
  raise AssertionError("VR count corrupted original SJ trains")
 print("VR BOTH DIRECTIONS VERIFIED",dict(counts),"TEMPLATE DAY",template,
       "REJECTED IMPROPER OSM ROUTES",dict(rejected),flush=True)
 print("PROTECTED OLD SYSTEMS",len(original["trips"]),
       "UNMODIFIED TRACKS",len(original["shapes"]),
       "NEW VR TRAINS",len(verified),flush=True)
 return result

def main():
 if len(sys.argv) not in (4,5):
  raise SystemExit("Usage: append_vr_rail.py ORIGINAL_11.json VR_CANDIDATES.json OUT_12.json [VERIFIED_OSM_BRIDGE.json]")
 source=json.loads(Path(sys.argv[1]).read_text(encoding="utf8"))
 vr=json.loads(Path(sys.argv[2]).read_text(encoding="utf8"))
 bridge=(json.loads(Path(sys.argv[4]).read_text(encoding="utf8")) if len(sys.argv)==5 else None)
 output=integrate(source,vr,bridge)
 destination=Path(sys.argv[3])
 destination.parent.mkdir(parents=True,exist_ok=True)
 destination.write_text(json.dumps(output,ensure_ascii=False,separators=(",",":")),encoding="utf8")
if __name__=="__main__":main()
