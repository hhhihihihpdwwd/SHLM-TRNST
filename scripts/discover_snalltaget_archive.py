#!/usr/bin/env python3
"""Read-only authentic Snälltåget operator and Friday 2026-11-06 GTFS audit."""
import collections
import json
import re
import build_rail_keyless as gtfs

def main():
 with gtfs.fetch_archive() as archive:
  valid=gtfs.service_calendar(archive,[gtfs.REFERENCE_DAY])[gtfs.REFERENCE_DAY]
  agencies={a["agency_id"]:a.get("agency_name","") for a in gtfs.records(archive,"agency.txt")}
  matched={k:v for k,v in agencies.items() if ("snäll" in v.casefold() or "snall" in v.casefold())}
  print("SNALL OPERATOR IDS",json.dumps(matched,ensure_ascii=False),flush=True)
  routes={}
  for route in gtfs.records(archive,"routes.txt"):
   label=" ".join([route.get("route_short_name",""),route.get("route_long_name","")])
   agency=agencies.get(route.get("agency_id"),"")
   if route.get("agency_id") in matched or "snälltåget" in label.casefold():
    routes[route["route_id"]]=route
    print("SNALL ROUTE",route["route_id"],"TYPE",route.get("route_type"),
          "AGENCY",agency,"SHORT",route.get("route_short_name"),
          "LONG",route.get("route_long_name"),flush=True)
  trips={t["trip_id"]:t for t in gtfs.records(archive,"trips.txt")
         if t.get("route_id") in routes and t.get("service_id") in valid}
  print("SNALL FRIDAY ACTIVE TRAIN IDS",len(trips),flush=True)
  stops={s["stop_id"]:s.get("stop_name","") for s in gtfs.records(archive,"stops.txt") if s.get("stop_id")}
  stop_times=collections.defaultdict(list)
  for s in gtfs.records(archive,"stop_times.txt"):
   tid=s.get("trip_id")
   if tid not in trips:continue
   try:n=int(s.get("stop_sequence","-1"))
   except ValueError:continue
   name=stops.get(s.get("stop_id"),"")
   if name:stop_times[tid].append((n,name,s.get("departure_time"),s.get("arrival_time")))
  patterns=collections.Counter()
  for tid,arr in stop_times.items():
   arr.sort()
   if len(arr)<2:continue
   names=[x[1] for x in arr]
   first,last=names[0],names[-1]
   patterns[(first,last)]+=1
   print("SNALL HISTORIC TRAIN",tid,"FROM",first,"TO",last,
         "DEPART",arr[0][2],"ARRIVE",arr[-1][3],
         "HEADSIGN",trips[tid].get("trip_headsign"),
         "STOPS",json.dumps(names,ensure_ascii=False),flush=True)
  print("SNALL ROUTE PATTERNS",dict((str(k),v) for k,v in patterns.items()),flush=True)
  if not matched or not trips:
   raise ValueError("No authentic Snälltåget Friday services found in public archive; cannot invent departures")
if __name__=="__main__":main()
