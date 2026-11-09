#!/usr/bin/env python3
"""Join two verified existing SJ OSM corridors with a physical OSM rail-way bridge.

Stockholm→Katrineholm is already verified in the SJ Malmö relation.
Hallsberg→Göteborg is already verified in the SJ Göteborg relation.
Route ONLY Katrineholm→Hallsberg through explicitly connected OSM railway
way node IDs, never via a straight line or an approximate station connector.
All joins occur at identical real OSM vertices on existing relations.

Inputs: exact STABLE07 rail.json and genuine VR GTFS candidate train record file.
Output: independently auditable geometry + source OSM node IDs in JSON.
"""
from __future__ import annotations
import collections
import json
import math
import sys
from pathlib import Path

import osm_railway_way_router as graph
from refine_osm_routes import project_stops

STOCKHOLM_MALMO="sj-osm:8860632:reverse"
STOCKHOLM_GOTEBORG="sj-osm:21493221:reverse"
KATRINEHOLM="Katrineholm Centralstation"
HALLSBERG="Hallsberg station"
JOIN_DISTANCE_METRES=450
EXACT_JOIN_ERROR_METRES=0.25

def find_station(trips,name):
 for t in trips:
  for x in t["stops"]:
   if x[2]==name:return x
 raise ValueError("Real VR GTFS station missing "+name)

def near_station_indices(shape,station):
 return {tuple(round(float(x),6) for x in p):i for i,p in enumerate(shape)
         if graph.dist(p,station[:2])<=JOIN_DISTANCE_METRES}

def matching_osm_nodes(rail_shape,station,nodes):
 allowed=near_station_indices(rail_shape,station)
 match={}
 for nid,p in nodes.items():
  xy=tuple(round(x,6) for x in p)
  if xy in allowed:
   match[nid]=allowed[xy]
 print("VR EXACT PHYSICAL OSM JUNCTION",station[2],"JOIN_POINTS",len(match),flush=True)
 if not match:
  raise ValueError("No original real OSM track nodes shared at "+station[2])
 return match

def build(data,candidates,network_builder=graph.collect_graph):
 assert data["scope"]=="pendeltag-tunnelbana-tvarbanan-localtram-city7-roslags-saltsjo-arlanda-sj-malartag"
 stockholm_to_katrineholm=data["shapes"].get(STOCKHOLM_MALMO)
 hallsberg_to_goteborg=data["shapes"].get(STOCKHOLM_GOTEBORG)
 if not stockholm_to_katrineholm or not hallsberg_to_goteborg:
  raise ValueError("STABLE07 lacks original verified southern/western OSM tracks")
 vr=[t for t in candidates["trips"] if t["serviceDay"]==data["simulationTemplateDay"]]
 katrineholm=find_station(vr,KATRINEHOLM)
 hallsberg=find_station(vr,HALLSBERG)
 if graph.dist(katrineholm[:2],hallsberg[:2])>100000:
  raise ValueError("Unexpected far distance Katrineholm–Hallsberg")
 node_points,connections=network_builder([katrineholm,hallsberg])
 joins_start=matching_osm_nodes(stockholm_to_katrineholm,katrineholm,node_points)
 joins_end=matching_osm_nodes(hallsberg_to_goteborg,hallsberg,node_points)
 # Only actual rail nodes shared by original OSM relations are eligible.
 previous={nid:(graph.dist(node_points[nid],katrineholm[:2]),[nid])
           for nid in joins_start}
 targets={nid:graph.dist(node_points[nid],hallsberg[:2]) for nid in joins_end}
 path_results,visited=graph.stage(previous,targets,connections,175000)
 if not path_results:
  raise ValueError("No physical OSM railway=rail node path between Katrineholm and Hallsberg")
 selected_node,(cost,ids)=min(path_results.items(),key=lambda item:item[1][0])
 first,last=ids[0],ids[-1]
 if first not in joins_start or last not in joins_end:
  raise ValueError("Connected graph path did not end at existing real OSM track junction")
 prefix=stockholm_to_katrineholm[:joins_start[first]+1]
 gap=[[round(node_points[node][0],6),round(node_points[node][1],6)] for node in ids]
 suffix=hallsberg_to_goteborg[joins_end[last]:]
 if not prefix or not suffix or len(gap)<10:raise ValueError("Short/incomplete OSM bridge")
 if graph.dist(prefix[-1],gap[0])>EXACT_JOIN_ERROR_METRES:
  raise ValueError("Synthetic Katrineholm connection refused")
 if graph.dist(gap[-1],suffix[0])>EXACT_JOIN_ERROR_METRES:
  raise ValueError("Synthetic Hallsberg connection refused")
 shape=prefix+gap[1:]+suffix[1:]
 if len(shape)<100:raise ValueError("Composite railway insufficient")
 max_step=max(graph.dist(x,y) for x,y in zip(shape,shape[1:]))
 if max_step>1500:raise ValueError("Hidden non-rail geometric jump of "+str(max_step))
 print("VR PHYSICAL RAILWAY PATH VERIFIED",len(shape),"points",
       "KATRINEHOLM LINK NODES",first,"HALLSBERG LINK NODES",last,
       "OSM BRIDGE NODES",len(ids),"GRAPH SEARCH",visited,
       "GRAPH COST",round(cost),"MAX SEGMENT",round(max_step),flush=True)
 check=collections.Counter()
 for t in vr:
  for d,geom in (("forward",shape),("reverse",list(reversed(shape)))):
   if project_stops(t["stops"],geom,500) is not None:
    check[t["direction"]]+=1
    print("VR FULL OSM ROUTE MATCH",t["id"],"GEOMETRY",d,flush=True)
    break
 print("VR REAL ROUTE COVERAGE",dict(check),"ALL GTFS CANDIDATES",len(vr),flush=True)
 if any(check[direction]<3 for direction in ("to-goteborg","to-stockholm")):
  raise ValueError("VR real OSM bridge did not verify at least three trains per direction")
 return {
  "source":"Real OSM railway=rail way node IDs + existing verified SJ route relations",
  "sourceRelations":[STOCKHOLM_MALMO,STOCKHOLM_GOTEBORG],
  "osmWayNetwork":True,
  "sourceNodeId":first,"targetNodeId":last,
  "sourceStation":KATRINEHOLM,"targetStation":HALLSBERG,
  "bridgeNodeCount":len(ids),"maxRealSegmentMetres":round(max_step,1),
  "shape":shape
 }

def main():
 if len(sys.argv)!=4:
  raise SystemExit("Usage: build_vr_real_osm_bridge.py STABLE07.json CANDIDATES.json OUT.json")
 source=json.loads(Path(sys.argv[1]).read_text())
 vr=json.loads(Path(sys.argv[2]).read_text())
 output=build(source,vr)
 target=Path(sys.argv[3])
 target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(json.dumps(output,ensure_ascii=False,separators=(",",":")),encoding="utf8")
 print("VR OSM GRAPH BRIDGE SAVED",target,target.stat().st_size,flush=True)
if __name__=="__main__":main()
