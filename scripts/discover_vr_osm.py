#!/usr/bin/env python3
"""Read-only OSM route audit for VR Snabbtåg / MTRX, 2026-11-06 GTFS stops.

Search public OpenStreetMap train route relations by VR operator/name and
check EVERY archived stop in both physical directions. Never synthesize rails.
The audited geometries are a separate artifact, never committed to live site.
"""
import collections
import datetime as dt
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import build_rail_keyless as gtfs
from build_vr_candidates import build
from refine_osm_routes import project_stops

ROOT=Path(__file__).resolve().parents[1]
BASE="https://openstreetmap.tools/public_transport_geojson/api/"
SEARCHES=("VR Snabbtåg","MTRX","MTR Express","X74","VR","Stockholm Göteborg")
MAX_SHAPE_BYTES=18_000_000

def get(url,size=1_500_000):
 req=urllib.request.Request(url,headers={
  "User-Agent":"StockholmRail VR Snabbtag OSM audit/1.0",
  "Accept":"application/json"})
 with urllib.request.urlopen(req,timeout=55) as result:
  data=result.read(size+1)
 if len(data)>size:raise ValueError("OSM API response unexpectedly large")
 return json.loads(data)

def search():
 relations={}
 for name in SEARCHES:
  try:
   url=BASE+"search?"+urllib.parse.urlencode({"q":name,"mode":"train"})
   result=get(url)
   found=result.get("routes",[])
   print("VR OSM SEARCH",repr(name),"COUNT",len(found),"TRUNCATED",
         result.get("truncated",False),flush=True)
   for x in found:
    if x.get("route")!="train" or not isinstance(x.get("id"),int):continue
    name_text=" ".join(str(x.get(k,"")) for k in ("name","from","to","operator","network","ref")).casefold()
    if any(w in name_text for w in ("göteborg","stockholm","mtrx","mtr express","vr snabbtåg")):
     relations[x["id"]]=x
     print("VR OSM POSSIBLE RELATION",x["id"],json.dumps(x,ensure_ascii=False),flush=True)
  except (urllib.error.URLError,TimeoutError,OSError,ValueError,KeyError) as exc:
   print("VR OSM SEARCH ERROR",repr(name),repr(exc)[:270],flush=True)
 return relations

def get_shapes(rid):
 obj=get(BASE+"route/"+str(rid),MAX_SHAPE_BYTES)
 raw=obj.get("geojson") or {}
 shapes=[]
 for item in raw.get("features",[]):
  geom=item.get("geometry") or {}
  if geom.get("type")!="LineString":continue
  pts=geom.get("coordinates",[])
  if not 20<len(pts)<150000:continue
  coords=[[round(float(p[1]),6),round(float(p[0]),6)] for p in pts]
  if all(55<=p[0]<=62 and 11<=p[1]<=20 for p in coords):
   shapes.append(coords)
 print("VR OSM FETCH",rid,"ROUTE",obj.get("name"),"SHAPES",list(map(len,shapes)),flush=True)
 return shapes

def main():
 with gtfs.fetch_archive() as z:
  candidates=build(z,dt.date(2026,11,9))
 trips=[t for t in candidates["trips"] if t["serviceDay"]=="2026-11-09"]
 if len(trips)<10:raise ValueError("Reference VR sample incomplete")
 relations=search()
 print("VR OSM RELATION CANDIDATES",len(relations),flush=True)
 result=[]
 for rid,info in list(relations.items())[:32]:
  try:shapes=get_shapes(rid)
  except (urllib.error.URLError,TimeoutError,OSError,ValueError) as e:
   print("VR OSM ROUTE ERROR",rid,repr(e)[:250],flush=True)
   continue
  for i,orig in enumerate(shapes):
   for suffix,shape in (("f",orig),("r",list(reversed(orig)))):
    matched=[t["id"] for t in trips
             if project_stops(t["stops"],shape,500) is not None]
    if matched:
     item={"id":"vr-osm:"+str(rid)+":"+str(i)+":"+suffix,
           "osmRelation":str(rid),"shape":shape,"matchedIds":matched,
           "operatorTag":info.get("operator"),"name":info.get("name")}
     result.append(item)
     print("VR VERIFIED OSM RELATION",rid,"DIRECTION",suffix,
           "TRAIN_COUNT",len(matched),"TRIPS",matched,flush=True)
 accepted=set(k for x in result for k in x["matchedIds"])
 print("VR OSM RESULTS",len(accepted),"OF",len(trips),"CANDIDATE GTFS TRIPS",
       "VALID OSM ROUTES",len(result),flush=True)
 if result:
  out=ROOT/"data"/"vr_osm_audit.json"
  out.parent.mkdir(parents=True,exist_ok=True)
  out.write_text(json.dumps({"referenceDay":"2026-11-06","routes":result},
                            ensure_ascii=False,separators=(",",":")),encoding="utf8")
  print("VR OSM AUDIT FILE",out,out.stat().st_size,flush=True)

if __name__=="__main__":main()
