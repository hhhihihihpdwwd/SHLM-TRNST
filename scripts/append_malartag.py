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
import urllib.request
import urllib.error
import time
from pathlib import Path
from build_malartag_candidates import CORRIDORS,norm,contains_station
from refine_osm_routes import BASE,read_json,project_stops,choose_directional_shape

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"/"rail.json"
CANDIDATES=ROOT/"data"/"malartag_candidates.json"
STABLE_SCOPE="pendeltag-tunnelbana-tvarbanan-localtram-city7-roslags-saltsjo-arlanda"
MAX_ERROR=650
MAX_OSM_LOOKUPS=120
OSM_RESPONSE_BYTES=18_000_000
OSM_TIMEOUT_SECONDS=40
OSM_HTTP_CACHE={}
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

def geometry_components(geojson, join_metres=15):
 """Recover individual real track chains from a branching OSM relation.

 The previous geometry_large rejected an entire relation if ANY one member
 way was disconnected. Instead preserve original members, joining only
 endpoints that actually touch. Every resulting route still requires complete
 GTFS stop projection in chronological order before it is accepted.
 """
 from refine_osm_routes import distance
 if not isinstance(geojson,dict):return []
 fragments=[]
 features=geojson.get("features",[]) if geojson.get("type")=="FeatureCollection" else [{"geometry":geojson}]
 for feature in features:
  g=feature.get("geometry") or {}
  kind=g.get("type")
  groups=([g.get("coordinates",[])] if kind=="LineString" else
          g.get("coordinates",[]) if kind=="MultiLineString" else [])
  for coords in groups:
   try:shape=[[round(float(p[1]),6),round(float(p[0]),6)] for p in coords]
   except (IndexError,ValueError,TypeError):continue
   if len(shape)>=2 and all(57.3<x[0]<61.5 and 14.0<x[1]<19.8 for x in shape):
    fragments.append(shape)
 if not fragments:return []
 # Preserve branching segments instead of demanding that all relation members
 # can be forced into one chain. Each original OSM LineString stays intact.
 if len(fragments)>120:return fragments[:120]
 changed=True
 while changed:
  changed=False
  for i in range(len(fragments)):
   if changed:break
   for j in range(i+1,len(fragments)):
    a,b=fragments[i],fragments[j]
    options=[
      (distance(a[-1],b[0]),a,b),
      (distance(a[-1],b[-1]),a,list(reversed(b))),
      (distance(a[0],b[-1]),b,a),
      (distance(a[0],b[0]),list(reversed(b)),a)
    ]
    d,first,second=min(options,key=lambda x:x[0])
    if d>join_metres:continue
    joined=first+second[1:] if first[-1]==second[0] else first+second
    fragments[i]=joined
    fragments.pop(j)
    changed=True
    break
 return [f for f in fragments if len(f)>=2]

def read_regional_osm(url):
 """Separate large-route HTTP fetch; local lines retain their original limits.

 A failed request is reported, never treated as an empty valid rail route.
 """
 if url in OSM_HTTP_CACHE:return OSM_HTTP_CACHE[url]
 last=None
 for attempt in range(2):
  try:
   req=urllib.request.Request(url,headers={
    "User-Agent":"StockholmRail/0.6 (regional rail geometry verification)",
    "Accept":"application/json","Accept-Encoding":"identity"})
   with urllib.request.urlopen(req,timeout=OSM_TIMEOUT_SECONDS) as response:
    raw=response.read(OSM_RESPONSE_BYTES+1)
   if len(raw)>OSM_RESPONSE_BYTES:raise ValueError("regional OSM relation exceeds 18MB limit")
   decoded=json.loads(raw)
   OSM_HTTP_CACHE[url]=decoded
   return decoded
  except (urllib.error.URLError,TimeoutError,OSError,ValueError) as exc:
   last=exc
   if attempt==0:time.sleep(1)
 raise RuntimeError("OSM regional request failed: "+url+" : "+repr(last))

OVERPASS_ENDPOINTS=(
 "https://overpass.kumi.systems/api/interpreter",
 "https://overpass-api.de/api/interpreter"
)
OVERPASS_RELATION_CACHE=None

def discover_regional_osm_relations():
 """Fallback to OSM relation metadata instead of relying on route-name search.

 Fetches only relation IDs and tags (no enormous rail way download).
 The geometry is still fetched from OSM and must pass every stop check.
 """
 global OVERPASS_RELATION_CACHE
 if OVERPASS_RELATION_CACHE is not None:return OVERPASS_RELATION_CACHE
 query='[out:json][timeout:90];relation["route"="train"](57.3,14.0,61.5,19.8);out tags;'
 last=None
 for base_url in OVERPASS_ENDPOINTS:
  try:
   payload=urllib.parse.urlencode({"data":query}).encode("utf8")
   req=urllib.request.Request(base_url,data=payload,headers={
      "User-Agent":"StockholmRail/0.7 (OSM train route relation audit)",
      "Content-Type":"application/x-www-form-urlencoded"})
   with urllib.request.urlopen(req,timeout=105) as response:
    raw=response.read(OSM_RESPONSE_BYTES+1)
   if len(raw)>OSM_RESPONSE_BYTES:raise ValueError("Overpass relation list too large")
   obj=json.loads(raw)
   elements=obj.get("elements",[])
   if not isinstance(elements,list):raise ValueError("Invalid Overpass result")
   selected={}
   for e in elements:
    tags=e.get("tags") or {}
    if e.get("type")!="relation" or tags.get("route")!="train":continue
    rid=e.get("id")
    if not isinstance(rid,int):continue
    selected[rid]={"id":rid,"name":tags.get("name",""),
      "from":tags.get("from",""),"to":tags.get("to",""),
      "operator":tags.get("operator",""),"network":tags.get("network","")}
   OVERPASS_RELATION_CACHE=selected
   print("MÄLARTÅG OVERPASS RELATION INVENTORY",len(selected),flush=True)
   return selected
  except (urllib.error.URLError,TimeoutError,OSError,ValueError) as exc:
   last=exc
   print("MÄLARTÅG OVERPASS RELATION REQUEST FAILED",base_url,repr(exc)[:160],flush=True)
 raise RuntimeError("OSM Overpass relation discovery unavailable: "+repr(last))

def corridor_relation_match(corridor,item):
 """Selection for later strict geometrical check; never marks a relation valid."""
 names=" ".join(str(item.get(k,"")) for k in ("name","from","to","operator","network"))
 names=norm(names)
 # A generic operator label is NOT evidence for a particular corridor.
 # Require at least two identifiable corridor waypoints in the OSM relation
 # name/from/to. Geometry and ALL GTFS stops must still validate separately.
 anchors=CORRIDORS[corridor]
 hits=sum(a in names for a in anchors)
 if hits>=2:return True

 return False

def relation_shapes(corridor,first,last,reader=None):
 """Search public OSM train relations. Validate every result geometrically.

 A route relation must include all rails; rejected short/truncated relations
 cannot be silently supplemented with straight-line connectors.
 """
 if reader is None:reader=read_regional_osm
 found={}
 diagnostics=collections.Counter()
 # Operator/network search is much more precise than generic station names.
 queries=["Mälartåg","Mälardalstrafik",first,last,*CORRIDORS[corridor]]
 for term in dict.fromkeys(queries):
  if len(term.strip())<4:continue
  q=urllib.parse.urlencode({"q":term,"mode":"train",
     "south":57.4,"west":14.0,"north":61.2,"east":19.6})
  try:
   obj=reader(BASE+"search?"+q)
   diagnostics["search_success"]+=1
  except (OSError,ValueError,TimeoutError,RuntimeError) as ex:
   diagnostics["search_error"]+=1
   print("MÄLARTÅG OSM SEARCH FAILED",corridor,term,str(ex)[:160],flush=True)
   continue
  for item in obj.get("routes",[]):
   rid=item.get("id")
   if isinstance(rid,int):
    if item.get("type")=="route_master":
     try:
      master=reader(BASE+"route_master/"+str(rid))
      diagnostics["master_success"]+=1
      for sub in master.get("routes",[]):
       subid=sub.get("id")
       if isinstance(subid,int):found[subid]=sub
     except (OSError,ValueError,TimeoutError,RuntimeError) as ex:
      diagnostics["master_error"]+=1
      print("MÄLARTÅG OSM MASTER FAILED",rid,str(ex)[:120],flush=True)
    else:
     found[rid]=item
  if len(found)>=MAX_OSM_LOOKUPS:break
 if not found and reader is read_regional_osm:
  # The OSM route-search endpoint can return zero relations for regional
  # rail services even if OSM has relevant train relations.
  try:
   inventory=discover_regional_osm_relations()
   matched={rid:item for rid,item in inventory.items()
            if corridor_relation_match(corridor,item)}
   print("MÄLARTÅG OVERPASS CORRIDOR",corridor,
         "candidate_relations",len(matched),flush=True)
   found.update(dict(list(matched.items())[:MAX_OSM_LOOKUPS]))
   diagnostics["overpass_matches"]=len(matched)
  except RuntimeError as exc:
   diagnostics["overpass_error"]+=1
   print("MÄLARTÅG OVERPASS FALLBACK FAILED",corridor,str(exc),flush=True)
 geometries=[]
 for rid,item in list(found.items())[:MAX_OSM_LOOKUPS]:
  try:
   obj={}
   if item.get("geojson"):
    shape=geometry_large(item["geojson"])
   else:
    obj=reader(BASE+"route/"+str(rid))
    shape=geometry_large(obj.get("geojson"))
   if shape and len(shape)>5:
    geometries.append((str(rid),shape))
   else:
    diagnostics["invalid_or_disconnected_geometry"]+=1
    # Missing/branching relations still contain real OSM track members.
    # Expose separate actual fragments to the strict directional validator,
    # rather than throwing away the entire railway.
    source_geojson=item.get("geojson") or obj.get("geojson")
    parts=geometry_components(source_geojson)
    diagnostics["recovered_osm_track_fragments"]+=len(parts)
    for n,part in enumerate(parts):
     if len(part)>5:geometries.append((str(rid)+":part"+str(n),part))
  except (OSError,ValueError,TimeoutError,RuntimeError,KeyError) as ex:
   diagnostics["route_download_error"]+=1
   print("MÄLARTÅG OSM ROUTE FAILED",rid,str(ex)[:140],flush=True)
 print("MÄLARTÅG OSM REPORT",corridor,"relations",len(found),"usable_shapes",
       len(geometries),"diagnostics",dict(diagnostics),flush=True)
 return geometries

def connected_route_combinations(sources,max_segments=3,join_metres=25):
 """Join actual OSM relation track only where endpoints touch physically.

 No line is drawn between disconnected tracks. Each direction is examined
 later against every GTFS stopping point. Some regional services span more
 than one mapped OSM route relation.
 """
 from refine_osm_routes import distance
 if not sources:return []
 output=[]
 seen=set()
 def walk(used,shape,labels):
  if len(used)>1:
   signature=tuple(labels)
   if signature not in seen:
    seen.add(signature)
    output.append(("+".join(labels),shape))
  if len(used)>=max_segments:return
  for i,(rid,segment) in enumerate(sources):
   if i in used or len(segment)<2:continue
   # Reverse only existing OSM vertices, never synthesize connectors.
   for direction,way in (("f",segment),("r",list(reversed(segment)))):
    if distance(shape[-1],way[0])<=join_metres:
     # Drop common endpoint only when points are identical; otherwise keep
     # both actual measured OSM points (gap <=25 m).
     joined=shape+way[1:] if shape[-1]==way[0] else shape+way
     walk(used|{i},joined,labels+[str(rid)+":"+direction])
 for i,(rid,shape) in enumerate(sources):
  if len(shape)<2:continue
  walk({i},shape,[str(rid)+":f"])
  walk({i},list(reversed(shape)),[str(rid)+":r"])
 return output

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
  key=corridor
  if key not in cache:
   cache[key]=provider(corridor,first,last)
  winner=choose_directional_shape(group[0]["stops"],cache[key],MAX_ERROR)
  if not winner and len(cache[key])>1:
   # A full train may use multiple separately mapped, contiguous OSM
   # rail relations. Never use station-to-station straight lines.
   composites=connected_route_combinations(cache[key])
   winner=choose_directional_shape(group[0]["stops"],composites,MAX_ERROR)
   if winner:
    print("MÄLARTÅG VERIFIED CONNECTED OSM ROUTES",corridor,
          first,last,winner[0],flush=True)
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
 # services must not be misrepresented as four complete selected corridors.
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
 print("MÄLARTÅG VERIFIED FOUR SELECTED CORRIDORS",out["malartagDirections"],flush=True)
if __name__=="__main__":main()
