#!/usr/bin/env python3
"""Append ONLY proven complete OSM route-relation Mälartåg trips to STABLE 06.

No straight-line fallback, no guessed OSM track, no STABLE 06 mutation.
Requires every GTFS intermediate stopping point in monotonic order on a genuine
OSM railway route relation. Fail closed if any official corridor/direction lacks service.
"""
import collections
import copy
import json
import urllib.parse
from pathlib import Path
from build_malartag_candidates import CORRIDORS,norm,contains_station
from refine_osm_routes import BASE,read_json,project_stops,choose_directional_shape

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"/"rail.json"
CANDIDATES=ROOT/"data"/"malartag_candidates.json"
STABLE_SCOPE="pendeltag-tunnelbana-tvarbanan-localtram-city7-roslags-saltsjo-arlanda"
MAX_ERROR=650
MAX_OSM_LOOKUPS=120
MAX_FILE=105_000_000

def geometry_large(geojson):
 """Accept continuous OSM LineStrings, never connect unrelated track segments.

 OSM railway relations often contain multiple way geometries. Stitch ONLY
 endpoints that genuinely meet (max 25 metres); reject gaps/branches rather
 than drawing invented rail links.
 """
 from refine_osm_routes import distance
 if not isinstance(geojson,dict):return None
 chunks=[]
 for feature in geojson.get("features",[]):
  g=feature.get("geometry") or {}
  if g.get("type")=="LineString": sequences=[g.get("coordinates",[])]
  elif g.get("type")=="MultiLineString":sequences=g.get("coordinates",[])
  else:continue
  for coords in sequences:
   try:
    segment=[[round(float(x[1]),6),round(float(x[0]),6)] for x in coords]
   except (IndexError,TypeError,ValueError):return None
   if len(segment)>1:chunks.append(segment)
 if not chunks:return None
 result=chunks.pop(0)
 while chunks:
  choices=[]
  for i,s in enumerate(chunks):
   for reverse in (False,True):
    oriented=list(reversed(s)) if reverse else s
    d=distance(result[-1],oriented[0])
    if d<=25:choices.append((d,i,reverse,False))
    d=distance(result[0],oriented[-1])
    if d<=25:choices.append((d,i,reverse,True))
  if not choices:return None
  _,i,reverse,prepend=min(choices)
  segment=chunks.pop(i)
  if reverse:segment.reverse()
  result=segment[:-1]+result if prepend else result+segment[1:]
 if len(result)>9000:
  step=(len(result)-1)/8999
  result=[result[round(i*step)] for i in range(9000)]
 return result if all(57.3<p[0]<61.5 and 14.0<p[1]<19.8 for p in result) else None

def relation_shapes(corridor,first,last,reader=read_json):
 """Search public OSM train relations. Validate every result geometrically.

 A route relation must include all rails; rejected short/truncated relations
 cannot be silently supplemented with straight-line connectors.
 """
 found={};queries=[first,last,*CORRIDORS[corridor]]
 for term in dict.fromkeys(queries):
  if len(term.strip())<4:continue
  q=urllib.parse.urlencode({"q":term,"mode":"train",
     "south":57.4,"west":14.0,"north":61.2,"east":19.6})
  try:
   obj=reader(BASE+"search?"+q)
  except (OSError,ValueError,TimeoutError) as ex:
   print("MÄLARTÅG OSM SEARCH",corridor,term,type(ex).__name__,flush=True)
   continue
  for item in obj.get("routes",[]):
   if item.get("type")=="route_master":
    continue
   rid=item.get("id")
   if isinstance(rid,int):found[rid]=item
  if len(found)>=60:break
 geometries=[]
 for rid in list(found)[:MAX_OSM_LOOKUPS]:
  try:
   obj=reader(BASE+"route/"+str(rid))
   shape=geometry_large(obj.get("geojson"))
   if shape and len(shape)>5:geometries.append((str(rid),shape))
  except (OSError,ValueError,TimeoutError,KeyError):continue
 print("MÄLARTÅG OSM CANDIDATES",corridor,len(geometries),flush=True)
 return geometries

def direction_of(trip):
 # Determine direction from every scheduled station, not only named termini.
 # A short-turn service may begin/end at a stop missing from corridor anchors.
 anchors=CORRIDORS[trip["corridor"]]
 found=[]
 for stop in trip["stops"]:
  positions=[i for i,name in enumerate(anchors) if contains_station(stop[2],name)]
  if len(positions)==1:found.append(positions[0])
 if len(found)<2 or found[0]==found[-1]:return None
 return "forward" if found[0]<found[-1] else "reverse"

def integrate(base,archive,provider=relation_shapes):
 if base.get("scope")!=STABLE_SCOPE:
  raise ValueError("Mälartåg requires untouched full STABLE 06 nine-system baseline")
 frozen=copy.deepcopy(base)
 records=collections.defaultdict(list)
 for t in archive["trips"]:
  c=t.get("corridor")
  if c not in CORRIDORS or t.get("agency")!="Mälartåg" or t.get("mode")!="rail":
   continue
  key=(c,tuple(s[2] for s in t["stops"]))
  records[key].append(t)
 added=[];shape_map={};counts=collections.Counter();directions=collections.defaultdict(lambda:collections.Counter())
 cache={}
 for (corridor,stopnames),group in sorted(records.items(),key=lambda row:-len(row[1])):
  first,last=stopnames[0],stopnames[-1]
  direction=direction_of(group[0])
  if direction is None:continue
  key=(corridor,norm(first),norm(last))
  if key not in cache:
   cache[key]=provider(corridor,first,last)
  winner=choose_directional_shape(group[0]["stops"],cache[key],MAX_ERROR)
  if not winner:
   print("MÄLARTÅG REJECT incomplete OSM",corridor,first,last,len(group),flush=True)
   continue
  rid,geom=winner
  sid="malartag-osm:"+rid
  for t in group:
   if project_stops(t["stops"],geom,MAX_ERROR) is None:continue
   # Explicitly do NOT assert model if historical GTFS has no vehicle assignment.
   added.append({**t,"mode":"regional","vehicleModel":"ER1 (typical; not trip-confirmed)",
     "vehiclePhotoStatus":"approved-model-reference",
     "shapeId":sid,"osmRelation":rid,"geometryQuality":"verified-osm-relation"})
   shape_map[sid]=geom
   counts[corridor]+=1
   directions[corridor][direction]+=1
 missing=[c for c in CORRIDORS if directions[c]["forward"]<1 or directions[c]["reverse"]<1]
 if missing:raise ValueError("Mälartåg incomplete verified bidirectional OSM/GTFS corridors: "+", ".join(missing))
 # Require every officially advertised corridor waypoint to occur in an
 # actually accepted train's scheduled stops. A few accepted partial
 # services must not be misrepresented as five complete corridors.
 coverage={}
 for corridor,anchors in CORRIDORS.items():
  names=[stop[2] for t in added if t["corridor"]==corridor for stop in t["stops"]]
  absent=[a for a in anchors if not any(contains_station(name,a) for name in names)]
  if absent:raise ValueError("Mälartåg incomplete corridor "+corridor+"; stations missing: "+", ".join(absent))
  coverage[corridor]={"requiredStops":len(anchors),"scheduledStops":len(set(names))}
 base["malartagCoverage"]=coverage
 base["trips"].extend(added)
 base["shapes"].update(shape_map)
 base["counts"]["regional"]=len(added)
 base["malartagCorridors"]=dict(counts)
 base["malartagDirections"]={k:dict(v) for k,v in directions.items()}
 base["scope"]=STABLE_SCOPE+"-malartag"
 assert base["trips"][:len(frozen["trips"])]==frozen["trips"]
 assert all(base["shapes"][k]==v for k,v in frozen["shapes"].items())
 assert all(base["counts"][k]==v for k,v in frozen["counts"].items())
 for key in ("metroLines","tramLines","roslagsLines","saltsjoLines","arlandaDirections"):
  assert base[key]==frozen[key],key
 return base

def main():
 base=json.loads(DATA.read_text(encoding="utf8"))
 candidates=json.loads(CANDIDATES.read_text(encoding="utf8"))
 out=integrate(base,candidates)
 payload=json.dumps(out,ensure_ascii=False,separators=(",",":"))
 if len(payload.encode())>MAX_FILE:raise ValueError("Mälartåg total railway payload exceeds size limit")
 DATA.write_text(payload,encoding="utf8")
 print("MÄLARTÅG VERIFIED ALL FIVE CORRIDORS",out["malartagDirections"],flush=True)
if __name__=="__main__":main()
