#!/usr/bin/env python3
"""Reconstruct an actual connected OSM *railway-way* path via ordered GTFS stops.

Never snap/connect disconnected rails or infer a straight line between stations.
Only explicit adjacent OSM way nodes are routable. Coordinates returned are
actual OSM track vertices; timetable positions are STILL simulated, not GPS.

Uses bounded Overpass searches around consecutive original GTFS stops, keeping
the source OSM node IDs so crossings without junctions cannot be joined.
"""
from __future__ import annotations
import collections
import datetime as dt
import hashlib
import heapq
import json
import math
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/"data"/"malartag_osm_ways"
OVERPASS=("https://overpass.kumi.systems/api/interpreter",
          "https://overpass-api.de/api/interpreter")
MAX_BYTES=55_000_000
MAX_NODE_VISITS=600_000
STOP_MAX_METRES=650
NEAR_NODES=10

def dist(a,b):
 lat1,lon1=a;lat2,lon2=b
 p=math.pi/180
 dp=(lat2-lat1)*p;dl=(lon2-lon1)*p
 v=math.sin(dp/2)**2+math.cos(lat1*p)*math.cos(lat2*p)*math.sin(dl/2)**2
 return 6371000*2*math.atan2(math.sqrt(v),math.sqrt(max(0,1-v)))

def bbox(a,b,extra=0.18):
 # 0.18 latitude + ~0.25 longitude buffer, leaving room for real curves.
 return (round(max(55.0,min(a[0],b[0])-extra),3),
         round(max(10.0,min(a[1],b[1])-extra*1.35),3),
         round(min(62.0,max(a[0],b[0])+extra),3),
         round(min(20.0,max(a[1],b[1])+extra*1.35),3))

def fetch_osm_ways(bounds):
 query='[out:json][timeout:130];way["railway"="rail"](%s);out geom;'%(
     ",".join(map(str,bounds)))
 CACHE.mkdir(parents=True,exist_ok=True)
 key=hashlib.sha256(query.encode("utf8")).hexdigest()[:20]
 target=CACHE/(key+".json")
 if target.is_file():
  result=json.loads(target.read_text(encoding="utf8"))
  if isinstance(result.get("elements"),list):return result["elements"]
 last=None
 for endpoint in OVERPASS:
  for attempt in range(2):
   try:
    form=urllib.parse.urlencode({"data":query}).encode("utf8")
    req=urllib.request.Request(endpoint,data=form,headers={
      "User-Agent":"StockholmRail/1.0 (legitimate OSM railway routing audit)",
      "Content-Type":"application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req,timeout=150) as response:
     raw=response.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:raise ValueError("OSM railway response exceeds safe size")
    obj=json.loads(raw)
    if not isinstance(obj.get("elements"),list):raise ValueError("No Overpass elements")
    count=sum(e.get("type")=="way" for e in obj["elements"])
    if count<1:raise ValueError("No rail ways returned for "+str(bounds))
    target.write_bytes(raw)
    print("OSM RAIL WAY BBOX",bounds,"WAYS",count,"BYTES",len(raw),flush=True)
    return obj["elements"]
   except (urllib.error.URLError,TimeoutError,OSError,ValueError) as exc:
    last=exc
    print("OSM RAIL REQUEST ERROR",endpoint,bounds,repr(exc)[:150],flush=True)
    if attempt==0:time.sleep(2)
 raise RuntimeError("OSM rail network query failed after both servers: "+repr(last))

def collect_graph(stops, downloader=fetch_osm_ways):
 nodes={}
 edges=collections.defaultdict(dict)
 seen_ways=set()
 unique_segments=[]
 for a,b in zip(stops,stops[1:]):
  area=bbox(a,b)
  if area not in unique_segments:unique_segments.append(area)
 for index,area in enumerate(unique_segments):
  elements=downloader(area)
  print("OSM RAIL GRAPH IMPORT",index+1,"/",len(unique_segments),area,flush=True)
  for item in elements:
   if item.get("type")!="way" or (item.get("tags") or {}).get("railway")!="rail":continue
   wid=item.get("id")
   if wid in seen_ways:continue
   ids=item.get("nodes") or []
   geo=item.get("geometry") or []
   if len(ids)!=len(geo) or len(ids)<2:continue
   seen_ways.add(wid)
   tag=item.get("tags") or {}
   penalty=3.0 if tag.get("service") in ("yard","siding","spur") else 1.0
   coords=[]
   try:
    for node in geo:coords.append((float(node["lat"]),float(node["lon"])))
   except (TypeError,KeyError,ValueError):continue
   for node_id,point in zip(ids,coords):
    nodes.setdefault(node_id,point)
   for i in range(1,len(ids)):
    u,v=ids[i-1],ids[i]
    if u==v:continue
    length=dist(coords[i-1],coords[i])
    if length<0.01 or length>4000:continue
    weight=length*penalty
    if weight<edges[u].get(v,float("inf")):
     edges[u][v]=weight
     edges[v][u]=weight
 print("OSM RAIL CONNECTIVITY GRAPH",len(nodes),"TRACK NODES",len(seen_ways),"PHYSICAL WAYS",
       sum(len(x) for x in edges.values())//2,"EDGES",flush=True)
 if len(nodes)<100 or not edges:raise ValueError("Insufficient actual OSM railway graph")
 return nodes,edges

def station_nodes(p,coords):
 lat,lon=p[:2]
 # Candidate nodes are actual mapped rail vertices; never attach platforms with
 # invented polylines. Every rail point must be close to scheduled GTFS station.
 nearby=[]
 for nid,c in coords.items():
  if abs(c[0]-lat)>0.010 or abs(c[1]-lon)>0.018:continue
  gap=dist((lat,lon),c)
  if gap<=STOP_MAX_METRES:nearby.append((gap,nid))
 nearby.sort()
 if not nearby:
  raise ValueError("No OSM rail nodes within %dm of GTFS stop %s"%(STOP_MAX_METRES,p[2]))
 # Avoid selecting many points from the same few metres of one track.
 selected=[]
 for gap,nid in nearby:
  if len(selected)>=NEAR_NODES:break
  if any(dist(coords[nid],coords[old_id])<17 for old_id in selected):continue
  selected.append(nid)
 return {nid:dist((lat,lon),coords[nid]) for nid in selected}

def stage(previous,targets,graph,maximum_length):
 heap=[(cost,source) for source,(cost,_) in previous.items()]
 heapq.heapify(heap)
 scores={node:cost for cost,node in heap}
 parent={node:None for _,node in heap}
 origin={node:node for _,node in heap}
 finished=set()
 obtained={}
 best_seed=min(scores.values())
 visits=0
 while heap and len(obtained)<len(targets):
  value,node=heapq.heappop(heap)
  if value!=scores[node] or node in finished:continue
  if value-best_seed>maximum_length:break
  finished.add(node)
  visits+=1
  if visits>MAX_NODE_VISITS:raise RuntimeError("Railway graph exceeded traversal cap")
  if node in targets:
   route=[]
   cur=node
   while cur is not None:
    route.append(cur)
    cur=parent[cur]
   route.reverse()
   src=origin[node]
   prefix=previous[src][1]
   obtained[node]=(value+targets[node]*0.8,
      prefix+route[1:] if prefix[-1]==route[0] else prefix+route)
  for neighbor,weight in graph.get(node,{}).items():
   score=value+weight
   if score<scores.get(neighbor,float("inf")):
    scores[neighbor]=score
    parent[neighbor]=node
    origin[neighbor]=origin[node]
    heapq.heappush(heap,(score,neighbor))
 return obtained,visits

def route_osm_ways(stops,downloader=fetch_osm_ways):
 if len(stops)<2:raise ValueError("Need two or more real GTFS stations")
 points,network=collect_graph(stops,downloader)
 previous={node:(gap*.8,[node]) for node,gap in station_nodes(stops[0],points).items()}
 print("OSM RAIL ROUTING STOPS",len(stops),[(s[2],round(s[0],4),round(s[1],4)) for s in stops],flush=True)
 for i,stop in enumerate(stops[1:],1):
  candidate=station_nodes(stop,points)
  direct=dist(stops[i-1][:2],stop[:2])
  max_leg=max(18000,direct*2.9+13000)
  follow,visited=stage(previous,candidate,network,max_leg)
  if not follow:
   raise ValueError("No connected OSM rails %s -> %s; candidates %s"%(stops[i-1][2],stop[2],len(candidate)))
  previous=follow
  print("OSM RAIL WAYPOINT",i,"/",len(stops)-1,stop[2],
        "rail_targets",len(follow),"visited",visited,flush=True)
 best=min(previous.values(),key=lambda x:x[0])
 ordered=[]
 for nid in best[1]:
  p=points[nid]
  if not ordered or ordered[-1]!=p:ordered.append([round(p[0],6),round(p[1],6)])
 if len(ordered)<10:raise ValueError("Railway geometry too short")
 from refine_osm_routes import project_stops
 if project_stops(stops,ordered,STOP_MAX_METRES) is None:
  raise ValueError("OSM rail graph path failed complete monotonic GTFS stop projection")
 print("OSM REAL RAILWAY-WAY PATH VERIFIED",len(ordered),"track points",
       "TOTAL METRES",round(sum(dist(a,b) for a,b in zip(ordered,ordered[1:]))),flush=True)
 return ordered

def build_full_corridor(corridor,trips):
 qualified=[t for t in trips if t.get("corridor")==corridor and len(t.get("stops",[]))>=3]
 if not qualified:raise ValueError("No real GTFS route for "+corridor)
 primary=max(qualified,key=lambda t:len(t["stops"]))
 geometry=route_osm_ways(primary["stops"])
 return [("osm-railway-ways:"+corridor,geometry)]
