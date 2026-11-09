#!/usr/bin/env python3
"""Build only genuine Friday 2026-11-06 VR Snabbtåg trains Stockholm C–Göteborg C.

The source GTFS operator is explicitly VR Snabbtåg, not inferred from a
generic Swedish high-speed train route. Replays the SAME historic Friday
for templateDay-1/templateDay/templateDay+1. Does not invent stops or trains.
"""
from __future__ import annotations
import collections
import datetime as dt
import json
import sys
from pathlib import Path
import build_rail_keyless as gtfs

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"vr_candidates.json"
REFERENCE_DAY=gtfs.REFERENCE_DAY
TRAIN_TYPES={"2","100","101","102","103","106","109"}
STOCKHOLM="stockholm centralstation"
GOTEBORG="göteborg centralstation"
OPERATOR="VR Snabbtåg"

def route_direction(names):
 if len(names)<3:return None
 first,last=names[0].casefold().strip(),names[-1].casefold().strip()
 if first==STOCKHOLM and last==GOTEBORG:return "to-goteborg"
 if first==GOTEBORG and last==STOCKHOLM:return "to-stockholm"
 return None

def build(z,template_day):
 day=REFERENCE_DAY
 valid=gtfs.service_calendar(z,[day])[day]
 agencies={x.get("agency_id"):x.get("agency_name","").strip() for x in gtfs.records(z,"agency.txt")}
 ids={k for k,v in agencies.items() if v.casefold()==OPERATOR.casefold()}
 if not ids:raise ValueError("Verified VR Snabbtåg GTFS agency missing")
 routes={}
 for r in gtfs.records(z,"routes.txt"):
  if r.get("agency_id") not in ids or r.get("route_type") not in TRAIN_TYPES:continue
  routes[r["route_id"]]=r
 if not routes:raise ValueError("No VR Snabbtåg train routes")
 trips={}
 for t in gtfs.records(z,"trips.txt"):
  if t.get("route_id") in routes and t.get("service_id") in valid:
   trips[t["trip_id"]]=t
 stations={}
 for s in gtfs.records(z,"stops.txt"):
  if not s.get("stop_id"):continue
  try:lat,lon=float(s["stop_lat"]),float(s["stop_lon"])
  except (KeyError,ValueError):continue
  if 55.0<=lat<=62.0 and 11.0<=lon<=20.0:
   stations[s["stop_id"]]=(round(lat,6),round(lon,6),s.get("stop_name",""))
 sequences=collections.defaultdict(list)
 for item in gtfs.records(z,"stop_times.txt"):
  trip_id=item.get("trip_id")
  if trip_id not in trips:continue
  point=stations.get(item.get("stop_id"))
  if not point or not point[2]:continue
  arr=gtfs.clock(item.get("arrival_time"))
  dep=gtfs.clock(item.get("departure_time"))
  if arr is None and dep is None:continue
  try:seq=int(item["stop_sequence"])
  except (KeyError,ValueError):continue
  sequences[trip_id].append((seq,point,arr if arr is not None else dep,
                            dep if dep is not None else arr))
 accepted=[];counts=collections.Counter()
 for trip_id,seq in sequences.items():
  seq.sort(key=lambda x:x[0])
  if len(seq)<3:continue
  names=[s[1][2] for s in seq]
  direction=route_direction(names)
  if not direction:continue
  if seq[-1][3]<=seq[0][2]:continue
  original=trips[trip_id]
  line=routes[original["route_id"]].get("route_short_name") or "VR"
  for offset in (-1,0,1):
   target=template_day+dt.timedelta(days=offset)
   zero=dt.datetime.combine(target,dt.time(),gtfs.ZONE)
   accepted.append({
    "id":"VR-ARCHIVE:"+trip_id+":"+target.isoformat(),
    "mode":"rail","agency":OPERATOR,"sourceAgency":OPERATOR,
    "line":"VR","train":line,"destination":names[-1],
    "serviceDay":target.isoformat(),"archiveDay":day.isoformat(),
    "direction":direction,
    "start":int((zero+dt.timedelta(seconds=seq[0][2])).timestamp()),
    "end":int((zero+dt.timedelta(seconds=seq[-1][3])).timestamp()),
    "stops":[[s[1][0],s[1][1],s[1][2],s[2],s[3]] for s in seq],
    "source":"GTFS Sverige 2, VR Snabbtåg, 2026-11-06 reference Friday",
    "geometryQuality":"awaiting-verified-OSM","shapeId":None,
    "vehicleModel":"VR X74 (operator fleet example, not trip verified)",
    "vehiclePhotoStatus":"licensed-illustrative-example",
    "isLiveGPS":False
   })
   counts[direction]+=1
 if any(counts[k]<1 for k in ("to-goteborg","to-stockholm")):
  raise ValueError("Historical VR Snabbtåg direct Stockholm–Göteborg trips missing in one direction")
 print("VR VERIFIED FRIDAY GTFS",OPERATOR,"ROUTES",len(routes),
       "REAL TRAIN DEFINITIONS",len(trips),"DIRECT 3-DAY",len(accepted),
       "BY DIRECTION",dict(counts),flush=True)
 return {"trips":accepted,"counts":dict(counts),"referenceDay":str(day),
         "operator":OPERATOR,"templateDay":template_day.isoformat()}

def main():
 if len(sys.argv)!=2:raise SystemExit("Usage: build_vr_candidates.py YYYY-MM-DD")
 target=dt.date.fromisoformat(sys.argv[1])
 with gtfs.fetch_archive() as z:
  result=build(z,target)
 OUT.parent.mkdir(parents=True,exist_ok=True)
 OUT.write_text(json.dumps(result,ensure_ascii=False,separators=(",",":")),encoding="utf8")
 print("VR CANDIDATES SAVED",OUT,len(result["trips"]),flush=True)

if __name__=="__main__":main()
