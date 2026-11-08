#!/usr/bin/env python3
"""Diagnostic only: historical Arlanda Express archive records and OSM search.
No changes to the published rail network or timetable.
"""
import collections
import json
import urllib.parse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import build_rail_keyless as gtfs
from refine_osm_routes import BASE,read_json,get_shape

def run():
 with gtfs.fetch_archive() as z:
  ag={r.get("agency_id"):r.get("agency_name","") for r in gtfs.records(z,"agency.txt")}
  candidates={}
  for r in gtfs.records(z,"routes.txt"):
   name=" ".join((r.get("route_short_name",""),r.get("route_long_name",""),ag.get(r.get("agency_id"),"")))
   if "arlanda" in name.lower() or "a-train" in name.lower():
    candidates[r["route_id"]]=r
    print("ARLANDA ROUTE",r["route_id"],"short",r.get("route_short_name"),"long",r.get("route_long_name"),"type",r.get("route_type"),"agency",ag.get(r.get("agency_id")),flush=True)
  trips={}
  for r in gtfs.records(z,"trips.txt"):
   if r.get("route_id") in candidates:trips[r["trip_id"]]=r
  print("ARLANDA GTFS TRIPS",len(trips),flush=True)
  stopnames={}
  for r in gtfs.records(z,"stops.txt"):
   stopnames[r["stop_id"]]=r.get("stop_name","")
  samples=collections.defaultdict(list)
  for r in gtfs.records(z,"stop_times.txt"):
   if r.get("trip_id") in trips:
    entry=(int(r.get("stop_sequence","0")),stopnames.get(r.get("stop_id")),r.get("arrival_time"))
    samples[r["trip_id"]].append(entry)
  counts=collections.Counter()
  shown=set()
  for tid,items in samples.items():
   items.sort()
   seq=tuple(x[1] for x in items)
   counts[seq]+=1
  for seq,n in counts.most_common(25):print("ARLANDA STOP SEQUENCE",n,seq,flush=True)
 for q in ("Arlanda Express","Arlanda norra","Arlanda södra"):
  url=BASE+"search?"+urllib.parse.urlencode({"q":q,"mode":"train","south":59.2,"west":17.7,"north":60.0,"east":18.4})
  try:
   data=read_json(url)
   for record in data.get("routes",[])[:20]:
    print("ARLANDA OSM RESULT",q,"id",record.get("id"),"type",record.get("type"),"ref",record.get("ref"),"name",record.get("name"),flush=True)
  except Exception as e:print("ARLANDA OSM SEARCH ERROR",q,str(e),flush=True)
 for rid in (1966855,):
  for kind in ("route_master","route"):
   try:
    response=read_json(BASE+kind+"/"+str(rid))
    print("ARLANDA PINNED OSM",kind,rid,"keys",list(response),"routes",len(response.get("routes",[])),flush=True)
    for record in response.get("routes",[])[:8]:
     geom=record.get("geojson") or {}
     features=geom.get("features",[])
     print("ARLANDA PINNED CHILD",record.get("id"),record.get("name"),"features",len(features),"first",str(features[:1])[:200],flush=True)
    geo=response.get("geojson") or {}
    print("ARLANDA PINNED MAIN GEOJSON",kind,len(geo.get("features",[])),flush=True)
   except Exception as ex:print("ARLANDA PINNED ERROR",kind,str(ex),flush=True)
if __name__=="__main__":run()
