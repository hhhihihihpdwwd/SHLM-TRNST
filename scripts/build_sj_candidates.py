#!/usr/bin/env python3
"""Historical SJ Stockholm–Västerås services: authentic Friday GTFS, daily replay.

No guessed schedule, no geometry. Track matching happens in append_sj_rail.py.
Only full Stockholm C <> Västerås C train services are currently in scope.
"""
import collections
import datetime as dt
import json
from pathlib import Path
import build_rail_keyless as gtfs

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"sj_candidates.json"
REF_DAY=gtfs.REFERENCE_DAY
ENDS=("stockholm centralstation","västerås centralstation")
ALLOWED_TYPES={"2","100","101","102","103","106","109"}

def normalize(s):
 return (s or "").casefold().strip()

def direction(names):
 names=[normalize(x) for x in names]
 if names[0]==ENDS[0] and names[-1]==ENDS[1]:return "to-vasteras"
 if names[0]==ENDS[1] and names[-1]==ENDS[0]:return "to-stockholm"
 return None

def build(z,now):
 valid=gtfs.service_calendar(z,[REF_DAY])[REF_DAY]
 agencies={row.get("agency_id"):row.get("agency_name","") for row in gtfs.records(z,"agency.txt")}
 routes={}
 for r in gtfs.records(z,"routes.txt"):
  agency=agencies.get(r.get("agency_id"),"")
  if normalize(agency)=="sj" and r.get("route_type") in ALLOWED_TYPES:
   routes[r["route_id"]]=(agency,r.get("route_short_name",""),r.get("route_long_name",""))
 if not routes:raise ValueError("No authentic SJ train agency in archive")
 stops={}
 for st in gtfs.records(z,"stops.txt"):
  try:lat,lon=float(st["stop_lat"]),float(st["stop_lon"])
  except (KeyError,ValueError):continue
  if 59.1<=lat<=60.1 and 16.2<=lon<=18.3:
   stops[st["stop_id"]]=(round(lat,6),round(lon,6),st.get("stop_name",""))
 relevant={}
 for trip in gtfs.records(z,"trips.txt"):
  if trip.get("route_id") in routes and trip.get("service_id") in valid:
   relevant[trip["trip_id"]]=(routes[trip["route_id"]],trip.get("trip_headsign",""),trip.get("trip_short_name",""))
 times=collections.defaultdict(list)
 for r in gtfs.records(z,"stop_times.txt"):
  tid=r.get("trip_id")
  if tid not in relevant:continue
  p=stops.get(r.get("stop_id"))
  if not p:continue
  arr=gtfs.clock(r.get("arrival_time",""))
  dep=gtfs.clock(r.get("departure_time",""))
  if arr is None and dep is None:continue
  try:order=int(r["stop_sequence"])
  except (KeyError,ValueError):continue
  times[tid].append((order,p,arr if arr is not None else dep,dep if dep is not None else arr))
 candidates=[]
 stats=collections.Counter()
 for tid,values in times.items():
  values.sort(key=lambda x:x[0])
  names=[v[1][2] for v in values]
  if len(names)<3:continue
  d=direction(names)
  if not d:continue
  if values[-1][3]<=values[0][2]:continue
  agency,route_short,route_long=relevant[tid][0]
  head=relevant[tid][1]
  for target in (now-dt.timedelta(days=1),now,now+dt.timedelta(days=1)):
   begin=dt.datetime.combine(target,dt.time(),gtfs.ZONE)
   origin=values[0][2];finish=values[-1][3]
   candidates.append({
    "id":"SJ-ARCHIVE:"+tid+":"+target.isoformat(),
    "mode":"rail","agency":"SJ","line":"SJ","train":route_short,
    "destination":head or names[-1], "serviceDay":target.isoformat(),
    "start":int((begin+dt.timedelta(seconds=origin)).timestamp()),
    "end":int((begin+dt.timedelta(seconds=finish)).timestamp()),
    "stops":[[v[1][0],v[1][1],v[1][2],v[2],v[3]] for v in values],
    "direction":d, "archiveDay":REF_DAY.isoformat(),
    "source":"GTFS Sverige 2 historic SJ weekday, replayed every day",
    "geometryQuality":"awaiting-verified-OSM","shapeId":None,
    "vehicleModel":"SJ Regional (specific rolling stock not established)",
    "vehiclePhotoStatus":"no-trip-confirmed-photo",
    "isLiveGPS":False})
   stats[d]+=1
 if not candidates or not stats["to-vasteras"] or not stats["to-stockholm"]:
  raise ValueError("Authentic SJ Stockholm–Västerås historical service missing in both directions")
 return {"trips":candidates,"counts":dict(stats),"referenceDay":REF_DAY.isoformat()}

def main():
 with gtfs.fetch_archive() as z:
  candidates=build(z,dt.datetime.now(gtfs.ZONE).date())
 OUT.parent.mkdir(parents=True,exist_ok=True)
 OUT.write_text(json.dumps(candidates,ensure_ascii=False,separators=(",",":")),encoding="utf8")
 print("SJ HISTORIC STOCKHOLM–VÄSTERÅS",candidates["counts"],"TRIPS",len(candidates["trips"]),flush=True)
if __name__=="__main__":main()
