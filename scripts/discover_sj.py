#!/usr/bin/env python3
"""Discover genuine SJ services in Stockholm Rail's pinned GTFS reference.

Read-only diagnostics, no fictional services, no publication.
"""
import collections
import datetime as dt
import build_rail_keyless as gtfs

def main():
 with gtfs.fetch_archive() as z:
  day=gtfs.REFERENCE_DAY
  valid=gtfs.service_calendar(z,[day])[day]
  agencies={a.get("agency_id"):a.get("agency_name","") for a in gtfs.records(z,"agency.txt")}
  sj_routes={}
  for rt in gtfs.records(z,"routes.txt"):
   a=agencies.get(rt.get("agency_id"),"")
   label=" ".join((rt.get("route_short_name",""),rt.get("route_long_name","")))
   if "sj" not in a.casefold().split() and not a.casefold().startswith("sj ") and a.casefold()!="sj":
    continue
   if rt.get("route_type") not in ("2","100","101","102","103","106","109"):
    continue
   sj_routes[rt["route_id"]]=(a,label)
  print("SJ AGENCIES",sorted({a for a,_ in sj_routes.values()}),flush=True)
  print("SJ ROUTES",len(sj_routes),flush=True)
  services={}
  for tr in gtfs.records(z,"trips.txt"):
   if tr.get("route_id") in sj_routes and tr.get("service_id") in valid:
    services[tr["trip_id"]]=(tr["route_id"],tr.get("trip_headsign",""),tr.get("trip_short_name",""))
  print("SJ REFERENCE FRIDAY TRIPS",len(services),"DAY",day,flush=True)
  stops={r["stop_id"]:(r.get("stop_name",""),float(r.get("stop_lat","0") or 0),float(r.get("stop_lon","0") or 0))
         for r in gtfs.records(z,"stops.txt") if r.get("stop_id")}
  times=collections.defaultdict(list)
  for st in gtfs.records(z,"stop_times.txt"):
   tid=st.get("trip_id")
   if tid not in services:continue
   name,lat,lon=stops.get(st.get("stop_id"),("",0,0))
   if not name:continue
   try:n=int(st["stop_sequence"])
   except (KeyError,ValueError):continue
   times[tid].append((n,name,lat,lon,st.get("departure_time","")))
  patterns=collections.Counter()
  samples={}
  for tid,ordered in times.items():
   ordered.sort()
   names=[x[1] for x in ordered]
   if len(names)<2:continue
   rid,head,number=services[tid]
   a,label=sj_routes[rid]
   is_stockholm=any("stockholm central" in name.casefold() for name in names)
   if not is_stockholm:continue
   key=(names[0],names[-1],len(names),a,label)
   patterns[key]+=1
   samples[key]=[names,tid,ordered[0][4],head,number]
  print("SJ STOCKHOLM TERMINAL PATTERNS",len(patterns),flush=True)
  for (first,last,n,a,label),count in patterns.most_common(45):
   names,tid,depart,head,number=samples[(first,last,n,a,label)]
   print("SJ SERVICE",count,"AGENCY",repr(a),"ROUTE",repr(label),
         "FROM",repr(first),"TO",repr(last),"N",n,
         "STOPS"," | ".join(names[:18]),"SAMPLE",tid,depart,head,number,flush=True)
if __name__=="__main__":main()
