#!/usr/bin/env python3
"""Read-only audit: actual 2026-11-06 VR/MTRX GTFS operators and routes.

Train operators may still have historical legal agency name MTR Express even
though passenger brand is VR Snabbtåg. Never infer services from a brand alone.
"""
import collections
import datetime as dt
import re
import build_rail_keyless as gtfs

TRAIN_TYPES={"2","100","101","102","103","106","109"}
def vr_operator(s):
 return bool(re.search(r'\b(?:mtrx|mtr express|vr snabb|vr express|vr snabbtåg)\b',
                       (s or "").casefold()))

def main():
 with gtfs.fetch_archive() as z:
  day=gtfs.REFERENCE_DAY
  services=gtfs.service_calendar(z,[day])[day]
  agencies={a.get("agency_id"):a.get("agency_name","") for a in gtfs.records(z,"agency.txt")}
  matches={k:v for k,v in agencies.items() if vr_operator(v)}
  print("VR DISCOVERY MATCHED AGENCIES",sorted(matches.items()),flush=True)
  routes={}
  for route in gtfs.records(z,"routes.txt"):
   rid=route.get("route_id")
   label=" ".join([route.get("route_short_name",""),route.get("route_long_name","")])
   agency=agencies.get(route.get("agency_id"),"")
   if route.get("route_type") not in TRAIN_TYPES:continue
   if agency not in matches.values() and not vr_operator(label):continue
   routes[rid]=route
   print("VR GTFS ROUTE",rid,repr(agency),repr(label),route.get("route_type"),flush=True)
  timetable={}
  trips={}
  for t in gtfs.records(z,"trips.txt"):
   if t.get("route_id") in routes and t.get("service_id") in services:
    trips[t["trip_id"]]=t
  print("VR FRIDAY VALID TRAIN TRIPS",len(trips),flush=True)
  stations={x["stop_id"]:x.get("stop_name","") for x in gtfs.records(z,"stops.txt")
            if x.get("stop_id")}
  records=collections.defaultdict(list)
  for row in gtfs.records(z,"stop_times.txt"):
   tid=row.get("trip_id")
   if tid not in trips:continue
   try:seq=int(row.get("stop_sequence","-1"))
   except ValueError:continue
   name=stations.get(row.get("stop_id"))
   if not name:continue
   records[tid].append((seq,name,row.get("departure_time"),row.get("arrival_time")))
  patterns=collections.Counter()
  for tid,stops in records.items():
   stops.sort()
   names=[r[1] for r in stops]
   if len(names)<2:continue
   ends=(names[0],names[-1])
   patterns[(ends,len(names))]+=1
   if "stockholm central" in names[0].lower() or "stockholm central" in names[-1].lower():
    print("VR REAL TRAIN",tid,"HEADSIGN",trips[tid].get("trip_headsign"),
          "DEPART",stops[0][2],"ARRIVE",stops[-1][3],
          "STOPS"," | ".join(names[:20]),flush=True)
  print("VR DISTINCT ROUTE PATTERNS",len(patterns),flush=True)
  for k,v in patterns.most_common(25):print("VR PATTERN",v,k,flush=True)
  if not trips:raise SystemExit("No VR/MTRX trains found in pinned Friday archive; cannot integrate unverified trains")
if __name__=="__main__":main()
