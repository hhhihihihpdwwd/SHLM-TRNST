#!/usr/bin/env python3
"""Audits exact SJ GTFS stop sequences against REAL OSM train route relations.

Read only; never publish a line that fails full stop projection.
"""
import collections
import json
import urllib.request
import urllib.error
import build_rail_keyless as gtfs
from refine_osm_routes import project_stops

RELATIONS={21493221:"Stockholm to Göteborg",21493220:"Göteborg to Stockholm",
           8860632:"Stockholm to Malmö",8858855:"Malmö to Stockholm"}
OSM_BASE="https://openstreetmap.tools/public_transport_geojson/api/route/"
def name(s):return (s or "").casefold()
def get_route(rid):
 url=OSM_BASE+str(rid)
 req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"StockholmRail SJ verified routing/1.0"})
 with urllib.request.urlopen(req,timeout=55) as response:
  raw=response.read(18_000_001)
 if len(raw)>18_000_000:raise ValueError("OSM route too large "+str(rid))
 obj=json.loads(raw)
 lines=[]
 for feat in (obj.get("geojson") or {}).get("features",[]):
  geom=feat.get("geometry") or {}
  if geom.get("type")=="LineString":lines.append(geom["coordinates"])
  if geom.get("type")=="MultiLineString":lines.extend(geom["coordinates"])
 shapes=[]
 for line in lines:
  if len(line)>=2:shapes.append([[round(float(p[1]),6),round(float(p[0]),6)] for p in line])
 print("SJ OSM RELATION",rid,"NAME",obj.get("name"),"SEQUENCES",list(map(len,shapes)),
       "ROUTE_STOPS",len(obj.get("stops",[])),flush=True)
 return shapes
def main():
 with gtfs.fetch_archive() as z:
  valid=gtfs.service_calendar(z,[gtfs.REFERENCE_DAY])[gtfs.REFERENCE_DAY]
  ag={x.get("agency_id"):x.get("agency_name","") for x in gtfs.records(z,"agency.txt")}
  routes={x["route_id"]:x for x in gtfs.records(z,"routes.txt")
          if name(ag.get(x.get("agency_id")))=="sj" and x.get("route_type") in ("2","100","101","102","103","106","109")}
  trips={x["trip_id"]:x for x in gtfs.records(z,"trips.txt")
         if x.get("route_id") in routes and x.get("service_id") in valid}
  stops={x["stop_id"]:[float(x.get("stop_lat","0") or 0),float(x.get("stop_lon","0") or 0),x.get("stop_name","")]
         for x in gtfs.records(z,"stops.txt") if x.get("stop_id") }
  times=collections.defaultdict(list)
  for x in gtfs.records(z,"stop_times.txt"):
   if x.get("trip_id") not in trips or x.get("stop_id") not in stops:continue
   try:i=int(x.get("stop_sequence","0"))
   except ValueError:continue
   p=stops[x["stop_id"]]
   times[x["trip_id"]].append((i,p))
  patterns=collections.defaultdict(list)
  for tid,rows in times.items():
   rows.sort()
   values=[p for _,p in rows]
   if len(values)<3:continue
   a,b=name(values[0][2]),name(values[-1][2])
   if ("stockholm central" in a and ("göteborg central" in b or "malmö central" in b)
       or "stockholm central" in b and ("göteborg central" in a or "malmö central" in a)):
    key="to-goteborg" if "stockholm" in a and "göteborg" in b else (
        "from-goteborg" if "göteborg" in a else (
        "to-malmo" if "stockholm" in a else "from-malmo"))
    patterns[key].append((tid,values))
  print("SJ DIRECT EXPRESS GTFS",dict((k,len(v)) for k,v in patterns.items()),flush=True)
  for key,all_trips in patterns.items():
   for tid,stops in all_trips[:3]:
    print("SJ GTFS PATTERN",key,tid," | ".join(s[2] for s in stops),flush=True)
  relation_keys={21493221:"to-goteborg",21493220:"from-goteborg",
                 8860632:"to-malmo",8858855:"from-malmo"}
  for rid,key in relation_keys.items():
   try:shapes=get_route(rid)
   except Exception as ex:
    print("SJ OSM DOWNLOAD ERROR",rid,repr(ex)[:240],flush=True)
    continue
   candidates=patterns.get(key,[])
   matches=0
   for tid,stops in candidates:
    for g in shapes:
     if project_stops(stops,g,850):
      matches+=1
      break
   print("SJ OSM GEOMETRY VALIDATION",rid,key,"valid_gtfs",matches,
         "total_candidates",len(candidates),flush=True)
if __name__=="__main__":main()
