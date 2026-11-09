#!/usr/bin/env python3
"""Append only SJ services whose entire scheduled stop sequence fits authentic OSM tracks.

No guessed tracks, no missing stop interpolation, no live GPS claims.
Existing nine-system rail records and shapes are copied unchanged.
"""
import collections
import copy
import json
import urllib.request
from pathlib import Path
from refine_osm_routes import project_stops

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"data"/"rail.json"
CANDIDATES=ROOT/"data"/"sj_candidates.json"
BASE_SCOPE="pendeltag-tunnelbana-tvarbanan-localtram-city7-roslags-saltsjo-arlanda"
RELATIONS={"to-goteborg":21493221,"to-stockholm":21493220}
MAX_ERROR_METRES=850
MAX_BYTES=110_000_000
OSM_URL="https://openstreetmap.tools/public_transport_geojson/api/route/"

def fetch_osm(direction):
 rid=RELATIONS[direction]
 req=urllib.request.Request(OSM_URL+str(rid),headers={
  "User-Agent":"StockholmRail SJ track verification/1.0","Accept":"application/json"})
 with urllib.request.urlopen(req,timeout=65) as response:
  raw=response.read(18_000_001)
 if len(raw)>18_000_000:raise ValueError("OSM SJ geometry exceeds safe limit")
 data=json.loads(raw)
 shapes=[]
 for feature in (data.get("geojson") or {}).get("features",[]):
  geo=feature.get("geometry") or {}
  if geo.get("type")!="LineString":continue
  coords=geo.get("coordinates") or []
  if len(coords)<4:continue
  shape=[[round(float(p[1]),6),round(float(p[0]),6)] for p in coords]
  if not all(55<lat<61.5 and 11<lon<19.9 for lat,lon in shape):
   continue
  shapes.append((str(rid),shape))
 if not shapes:raise ValueError("No valid SJ OSM LineStrings on "+str(rid))
 return shapes

def integrate(baseline,archive,provider=fetch_osm):
 if baseline.get("scope")!=BASE_SCOPE:
  raise ValueError("SJ integration must start from the proven nine-system baseline")
 frozen=copy.deepcopy(baseline)
 template=baseline.get("simulationTemplateDay")
 if not template:raise ValueError("Missing template date for daily repeating SJ")
 accepted=[];shapes={};directions=collections.Counter()
 for direction,rid in RELATIONS.items():
  options=provider(direction)
  trips=[t for t in archive.get("trips",[])
         if t.get("direction")==direction and t.get("agency")=="SJ"
         and t.get("mode")=="rail" and t.get("serviceDay")==template]
  print("SJ ROUTE",direction,"OSM",rid,"candidate_trips",len(trips),
        "OSM_SHAPES",len(options),flush=True)
  for t in trips:
   for ref,geometry in options:
    if project_stops(t["stops"],geometry,MAX_ERROR_METRES) is None:continue
    sid="sj-osm:"+ref
    accepted.append({**t,"mode":"intercity","line":"SJ",
      "shapeId":sid,"geometryQuality":"verified-osm-relation",
      "osmRelation":ref,"isLiveGPS":False})
    shapes[sid]=geometry
    directions[direction]+=1
    break
 if any(directions[d]<1 for d in RELATIONS):
  raise ValueError("SJ real OSM/GTFS full track matching failed, both directions required: "+str(dict(directions)))
 baseline["trips"].extend(accepted)
 baseline["shapes"].update(shapes)
 baseline["counts"]["intercity"]=len(accepted)
 baseline["sjDirections"]=dict(directions)
 baseline["scope"]=BASE_SCOPE+"-sj"
 assert baseline["trips"][:len(frozen["trips"])]==frozen["trips"]
 assert all(baseline["shapes"][k]==v for k,v in frozen["shapes"].items())
 assert all(baseline["counts"][k]==v for k,v in frozen["counts"].items())
 for k in ("metroLines","tramLines","roslagsLines","saltsjoLines","arlandaDirections"):
  assert baseline[k]==frozen[k],k
 print("SJ VERIFIED HISTORICAL TRAINS",dict(directions),flush=True)
 return baseline

def main():
 base=json.loads(SOURCE.read_text(encoding="utf8"))
 archive=json.loads(CANDIDATES.read_text(encoding="utf8"))
 result=integrate(base,archive)
 serialized=json.dumps(result,ensure_ascii=False,separators=(",",":"))
 if len(serialized.encode("utf8"))>MAX_BYTES:raise ValueError("SJ merged rail dataset exceeds safe limit")
 SOURCE.write_text(serialized,encoding="utf8")
if __name__=="__main__":main()
