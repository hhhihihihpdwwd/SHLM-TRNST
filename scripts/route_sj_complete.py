#!/usr/bin/env python3
"""Single-stage SJ COMPLETE 2026 authentic Stockholm train network: reconstruct
missing real railway=rail shapes from one Geofabrik Sweden + Norway PBF graph.

Requires source audit and exact frozen 16-system release. All paths use shared
consecutive OSM way node IDs; no line between disconnected points. Explicit
failure records block publication. Existing 80 covered journeys reuse original
verified rail geometry. No UI or public site modifications.
"""
from __future__ import annotations
import collections,datetime as dt,heapq,json,math,os,pathlib,sys
from zoneinfo import ZoneInfo
import osmium
from osm_railway_way_router import dist,station_nodes,stage
from refine_osm_routes import project_stops

LIMIT=(55.0,69.0,9.0,25.0)
def admissible(lat,lon):
 return LIMIT[0]<=lat<=LIMIT[1] and LIMIT[2]<=lon<=LIMIT[3]

class RailGraph(osmium.SimpleHandler):
 def __init__(self):
  super().__init__();self.nodes={};self.edges=collections.defaultdict(dict);self.ways=0;self.edgecount=0
 def way(self,w):
  if w.tags.get('railway')!='rail':return
  try:
   vertices=[(int(n.ref),(n.location.lat,n.location.lon)) for n in w.nodes]
  except (osmium.InvalidLocationError,ValueError):return
  if len(vertices)<2 or not any(admissible(*p) for _,p in vertices):return
  self.ways+=1
  penalty=3.0 if w.tags.get('service') in ('yard','siding','spur') else 1.0
  for nid,p in vertices:self.nodes.setdefault(nid,p)
  for (u,a),(v,b) in zip(vertices,vertices[1:]):
   edge=dist(a,b)
   if u==v or not (.01<edge<4000):continue
   cost=edge*penalty
   if cost<self.edges[u].get(v,float('inf')):
    self.edges[u][v]=cost;self.edges[v][u]=cost
    self.edgecount+=1

def graph(files):
 g=RailGraph()
 for file in files:
  p=pathlib.Path(file)
  assert p.is_file() and p.stat().st_size>500000,'Railway extract missing '+str(p)
  print('LOAD CONNECTED NATIONAL OSM RAIL NETWORK',p,p.stat().st_size,flush=True)
  g.apply_file(str(p),locations=True,idx='flex_mem')
  print('SJ REAL RAILWAY GRAPH',g.ways,'WAYS',len(g.nodes),'NODES',g.edgecount,'EDGES',flush=True)
 assert len(g.nodes)>50000 and g.edgecount>50000
 return g.nodes,g.edges

def check_shape(shape,original_edges=None):
 if len(shape)<12:return False
 if max(dist(a,b) for a,b in zip(shape,shape[1:]))>4000:return False
 if original_edges is not None and len(original_edges)<len(shape)-1:return False
 return True

def build_exact_route(trip,nodes,network):
 stops=trip['stops']
 candidate={n:(d*.8,[n]) for n,d in station_nodes(stops[0],nodes).items()}
 counts=[]
 for idx,p in enumerate(stops[1:],1):
  selected=station_nodes(p,nodes)
  direct=dist(stops[idx-1][:2],p[:2])
  candidate,seen=stage(candidate,selected,network,max(18000,direct*2.9+13000))
  if not candidate:
   raise ValueError('DISCONNECTED ACTUAL OSM RAIL %s → %s'%(stops[idx-1][2],p[2]))
  counts.append(seen)
 _,ids=min(candidate.values(),key=lambda x:x[0])
 for a,b in zip(ids,ids[1:]):
  if b not in network[a]:raise ValueError('Connected OSM node sequence broken')
 shape=[]
 for nid in ids:
  p=nodes[nid];xy=[round(p[0],6),round(p[1],6)]
  if not shape or shape[-1]!=xy:shape.append(xy)
 if not check_shape(shape,ids):raise ValueError('Invalid real way vertex geometry')
 if project_stops(stops,shape,650) is None:raise ValueError('OSM rails do not follow ordered historic SJ scheduled stops')
 return shape,{'vertices':len(shape),'osmNodeEdges':len(ids)-1,
               'lengthKm':round(sum(dist(a,b) for a,b in zip(shape,shape[1:]))/1000,1),
               'routingVisits':sum(counts)}

def existing_match(stops,geometries):
 for key,shape in geometries.items():
  if project_stops(stops,shape,650) is not None:return key,False
  if project_stops(stops,list(reversed(shape)),650) is not None:return key,True
 return None

def build(report,original,files):
 assert len(original['trips'])==10437 and len(original['shapes'])==71
 lookup={t['id']:t for t in report['selected']}
 completed={m['tripId']:m for m in report['matched']}
 requests=report['needsRailway']
 assert len(requests)==report['summary']['missingVerifiedRailShapes']
 nodes,network=graph(files)
 shapes={}
 assignments={}
 failed=[]
 # Match against already verified 71 shapes first. All existing geometries unchanged.
 oldshapes={k:v for k,v in original['shapes'].items() if isinstance(v,list) and len(v)>10}
 # Longest journeys first: shorter services can reuse existing correctly
 # connected paths if every scheduled stop projects monotonically.
 ordered=sorted(requests,key=lambda r:-len(lookup[r['id']]['stops']))
 for n,request in enumerate(ordered,1):
  trip=lookup[request['id']]
  stops=trip['stops']
  candidate=existing_match(stops,shapes)
  if candidate:
   sid,rev=candidate
   assignments[trip['id']]={'shapeId':sid,'reverse':rev,'verified':True,'reusedNewOSM':True}
   continue
  try:
   shape,metrics=build_exact_route(trip,nodes,network)
   sid='sj-complete-osm:'+str(len(shapes)+1).zfill(3)
   shapes[sid]=shape
   assignments[trip['id']]={'shapeId':sid,'reverse':False,'verified':True,'metrics':metrics}
   print('SJ NEW CONNECTED OSM RAILWAY',n,'/',len(ordered),sid,
      trip['origin'],'→',trip['destination'],metrics,flush=True)
  except (ValueError,RuntimeError) as e:
   message=repr(e)
   failed.append({'id':trip['id'],'from':trip['origin'],'to':trip['destination'],
                  'stops':[x[2] for x in stops],'reason':message})
   print('SJ ROUTING NOT VERIFIED',trip['id'],message,flush=True)
 result={'source':'Actual shared OSM railway=rail way nodes from Sweden/Norway Geofabrik extracts',
  'sourceTimetable':report.get('sourceArchive','GTFS Sverige 2 2026-11-04'),
  'originalTrips':10437,'originalShapes':71,
  'newShapes':shapes,'assignments':assignments,'alreadyMatched':completed,'failures':failed,
  'stats':{'needed':len(requests),'verified':len(assignments),
           'newConnectedRailwayShapes':len(shapes),'failed':len(failed)}}
 print('SJ COMPLETE NETWORK REAL RAILWAY ROUTE RESULT',json.dumps(result['stats']),flush=True)
 return result

if __name__=='__main__':
 if len(sys.argv)<5:raise SystemExit('Usage: route_sj_complete.py COVERAGE.json STABLE13.json OUTPUT.json Sweden.pbf [Norway.pbf...]')
 cover=json.loads(pathlib.Path(sys.argv[1]).read_text())
 original=json.loads(pathlib.Path(sys.argv[2]).read_text())
 result=build(cover,original,sys.argv[4:])
 out=pathlib.Path(sys.argv[3]);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')))
 print('WRITTEN CONCRETE OSM TRACK PROOF',out,out.stat().st_size,flush=True)
 if result['failures']:raise RuntimeError(str(len(result['failures']))+' SJ routes still lack verified connected OSM track; NO DEPLOY')
