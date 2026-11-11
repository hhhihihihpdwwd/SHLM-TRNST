#!/usr/bin/env python3
"""Prove all missing Berlin/Dresden/Sjælland Snälltåget historical rail services
against FULL physically connected OSM railway=rail way node IDs, crossing
Germany, Denmark and Sweden. No invented straight links, no guessed rails.
Exact original GTFS station sequence and speeds required or NO RELEASE.
"""
from pathlib import Path
import json,sys,collections
import route_sj_complete as sj
from refine_osm_routes import project_stops
from osm_railway_way_router import dist

def reuse(stops,shapes):
 for sid,shape in shapes.items():
  for rev in (False,True):
   if project_stops(stops,shape[::-1] if rev else shape,650) is not None:
    return (sid,rev)
 return None
def check(stops,shape,title):
 matched=project_stops(stops,shape,650)
 if matched is None:raise ValueError('Real cross-border OSM rail does not actually pass all stops in order '+title)
 for i in range(1,len(stops)):
  duration=stops[i][3]-stops[i-1][4]
  if duration<30:raise ValueError('Nonpositive real international train running time '+title)
  speed=(matched[i]-matched[i-1])/duration*3.6
  if not 0<speed<230:raise ValueError('Unrealistic international rail average '+str(speed)+' '+title)
 return matched[-1]-matched[0]
def main(coverage,output,files):
 report=json.loads(Path(coverage).read_text())
 missed=report['missing']
 assert len(missed)==3,('Unverified crossborder gaps changed',len(missed))
 assert set(t['kind'] for t in missed)=={'foreign-prefix','foreign-suffix','new-physical-train'}
 for t in missed:
  assert any('berlin' in x[2].casefold() for x in t['stops'])
  assert t['firstDeparture']<t['lastArrival']
 # Use original country OSM way node IDs, extending graph south into Germany.
 sj.LIMIT=(50.0,70.0,7.0,25.0)
 graph=sj.RailGraph()
 for f in files:
  p=Path(f)
  assert p.is_file() and p.stat().st_size>100000,'Missing country/state railway=rail extract '+str(p)
  graph.apply_file(str(p),locations=True,idx='flex_mem')
  print('ORIGINAL CROSSBORDER GRAPH',p.name,'WAYS',graph.ways,
   'NODES',len(graph.nodes),'EDGES',graph.edgecount,flush=True)
 assert len(graph.nodes)>300000 and graph.edgecount>300000
 nodes,network=graph.nodes,graph.edges
 result={'source':'Geofabrik original OSM railway=rail way-node graph in DE/DK/SE',
  'verified':{},'newShapes':{},'failures':[],'originalSource':report['source']}
 for t in sorted(missed,key=lambda x:-len(x['stops'])):
  title=t['id']
  checkmatch=reuse(t['stops'],result['newShapes'])
  if checkmatch:
   sid,rev=checkmatch
   oriented=result['newShapes'][sid][::-1] if rev else result['newShapes'][sid]
   check(t['stops'],oriented,title)
   result['verified'][title]={'shapeId':sid,'reverse':rev,'reusedNewRail':True}
   continue
  try:
   shape,meta=sj.build_exact_route(t,nodes,network)
   check(t['stops'],shape,title)
   sid='snall-crossborder-osm:'+str(len(result['newShapes'])+1).zfill(2)
   result['newShapes'][sid]=shape
   result['verified'][title]={'shapeId':sid,'reverse':False,'metrics':meta}
   print('SNÄLLTÅGET ORIGINAL DE DK SE RAILWAY TRACK VERIFIED',
    t['origin'],'→',t['destination'],'REAL CONNECTED WAY NODES',meta['osmNodeEdges'],
    'KM',meta['lengthKm'],flush=True)
  except (RuntimeError,ValueError,KeyError) as exc:
   result['failures'].append({'id':title,'stops':[s[2] for s in t['stops']],
                              'reason':repr(exc)})
   print('SNÄLLTÅGET RAILWAY NOT VERIFIED; NOT DEPLOYABLE',title,repr(exc),flush=True)
 out=Path(output);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')))
 print('CROSS BORDER GENUINE OSM TRACK FINAL',
  len(result['verified']),'VERIFIED',len(result['failures']),'UNVERIFIED',
  len(result['newShapes']),'PHYSICAL GERMANY DENMARK SWEDEN RAIL ROUTES',flush=True)
 if result['failures']:raise RuntimeError('Refuse publishing until every international track is physically proven')
if __name__=='__main__':
 if len(sys.argv)<5:raise SystemExit('Usage: route_snall_foreign.py RAIL_GAPS.json OUT.json Sweden.pbf Denmark.pbf GermanyStates...pbf')
 main(sys.argv[1],sys.argv[2],sys.argv[3:])
