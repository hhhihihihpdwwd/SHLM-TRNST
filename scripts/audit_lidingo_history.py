#!/usr/bin/env python3
"""Inspect complete archived Lidingöbanan 21 weekday departure windows.

Read-only. Distinguishes missing published trips from missing original GTFS
service; never manufactures historic departures.
"""
import collections
import datetime as dt
import statistics
import build_rail_keyless as gtfs

def main():
 days=[gtfs.SOURCE_START+dt.timedelta(days=n) for n in range(7)]
 with gtfs.fetch_archive() as z:
  calendar=gtfs.service_calendar(z,days)
  agencies={a.get("agency_id"):a.get("agency_name","") for a in gtfs.records(z,"agency.txt")}
  routes={r["route_id"]:r for r in gtfs.records(z,"routes.txt")
          if r.get("route_short_name","").strip()=="21" and
          gtfs.mode(r.get("route_type")," ".join((r.get("route_short_name",""),
                  r.get("route_long_name",""),agencies.get(r.get("agency_id"),""))),
                  r.get("route_short_name",""),agencies.get(r.get("agency_id"),""))=="tram"}
  print("LIDINGO SOURCE ROUTES",len(routes),[(r["route_id"],r.get("route_long_name"),r.get("route_type")) for r in routes.values()],flush=True)
  stops={r["stop_id"]:r.get("stop_name","") for r in gtfs.records(z,"stops.txt") if r.get("stop_id")}
  trips={t["trip_id"]:t for t in gtfs.records(z,"trips.txt") if t.get("route_id") in routes}
  print("LIDINGO ARCHIVED TRIP DEFINITIONS",len(trips),flush=True)
  timetable=collections.defaultdict(list)
  for x in gtfs.records(z,"stop_times.txt"):
   tid=x.get("trip_id")
   if tid not in trips:continue
   departure=gtfs.clock(x.get("departure_time"))
   arrival=gtfs.clock(x.get("arrival_time"))
   try:sequence=int(x.get("stop_sequence","0"))
   except ValueError:continue
   name=stops.get(x.get("stop_id"),"")
   if not name:continue
   timetable[tid].append((sequence,name,arrival,departure))
  for day in days:
   counted=collections.Counter()
   around=[]
   pattern=collections.Counter()
   for tid,t in trips.items():
    if t.get("service_id") not in calendar[day]:continue
    samples=sorted(timetable.get(tid,[]))
    if len(samples)<2:continue
    first,last=samples[0],samples[-1]
    origin,endpoint=first[1].casefold(),last[1].casefold()
    if not ((origin.startswith("ropsten") and endpoint.startswith("gåshaga"))
         or (origin.startswith("gåshaga") and endpoint.startswith("ropsten"))):continue
    d=first[3] if first[3] is not None else first[2]
    e=last[2] if last[2] is not None else last[3]
    if d is None or e is None or e<=d:continue
    counted[(d//3600)%24]+=1
    pattern["out" if origin.startswith("ropsten") else "back"]+=1
    if 6*3600<=d<10*3600:
     around.append((str(dt.timedelta(seconds=d)),str(dt.timedelta(seconds=e)),first[1],last[1],tid))
   print("LIDINGO ARCHIVE DAY",day,day.strftime("%A"),"full_runs",sum(counted.values()),
        "by_hour",dict(sorted(counted.items())),"directions",dict(pattern),flush=True)
   print("LIDINGO MORNING SAMPLE",day,sorted(around)[:40],flush=True)
if __name__=="__main__":main()
