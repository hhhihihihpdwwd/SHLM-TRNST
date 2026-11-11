#!/usr/bin/env python3
"""Resolve only the 40 historic Mälartåg Stockholm–Uppsala direct trains
using original physically connected Geofabrik OSM railway=rail way nodes.
No invented trains, no straight-line joins and no rewriting previous tracks.
"""
import json,pathlib,sys
from route_tagab_geofabrik import load_graph,route_one
from refine_osm_routes import project_stops,distance

def main(report,pbf,out):
 data=json.loads(pathlib.Path(report).read_text())
 gaps=data['missing']
 assert len(gaps)==40,('Unexpected gap inventory',len(gaps))
 assert {t['corridor'] for t in gaps}=={'orebro-uppsala'}
 assert {t['origin'] for t in gaps}=={'Stockholm Centralstation','Uppsala Centralstation'}
 assert {t['destination'] for t in gaps}=={'Stockholm Centralstation','Uppsala Centralstation'}
 from collections import Counter
 patterns=Counter(tuple(s[2] for s in t['stops']) for t in gaps)
 print('MÄLARTÅG MISSING UNIQUE OFFICIAL STOP PATTERNS',len(patterns),list(patterns.items()),flush=True)
 for t in gaps:
  assert len(t['stops'])>=2 and t['origin']!=t['destination']
 all_stops=[s for t in gaps for s in t['stops']]
 points,network=load_graph([pathlib.Path(pbf)],all_stops)
 shapes={}
 matched={}
 for t in sorted(gaps,key=lambda x:-len(x['stops'])):
  candidate=None
  for sid,shape in shapes.items():
   if project_stops(t['stops'],shape,650) is not None:
    candidate=(sid,shape);break
  if candidate is None:
   sid='malartag-new-osm:stockholm-uppsala:'+str(len(shapes)+1).zfill(2)
   info=route_one(sid,t['stops'],points,network)
   shape=info['shape']
   assert 30<info['lengthKm']<120,('Unrealistic Stockholm Uppsala actual rail length',info)
   shapes[sid]=shape
   candidate=(sid,shape)
   # Also save reverse of each connected physical railway way route.
   shapes[sid+':reverse']=shape[::-1]
   print('MÄLARTÅG VERIFIED DISTINCT OSM RAIL BRANCH',sid,info['lengthKm'],'km',flush=True)
  sid,shape=candidate
  projections=project_stops(t['stops'],shape,650)
  assert projections is not None
  span=projections[-1]-projections[0]
  elapsed=t['lastArrival']-t['firstDeparture']
  if elapsed<=0:raise ValueError('No real journey duration '+t['id'])
  speed=span/elapsed*3.6
  if not 15<speed<220:
   raise ValueError('Unrealistic scheduled speed on actual OSM railway '+str(speed)+' '+t['id'])
  matched[t['id']]={'shapeId':sid,'scheduledKmH':round(speed,1)}
 result={'shapes':shapes,'assignments':matched,
  'originalPhysicalOSM':'All consecutively linked original OSM railway way node IDs; no drawn straight lines',
  'uniqueOriginalStationPatterns':len(patterns),
  'routeDisclaimer':'Verified physical OSM rail corridors; historical train positions are simulated, not GPS'}
 assert len(matched)==len(gaps)==40
 print('ALL 40 REAL MÄLARTÅG DIRECT TRAINS VERIFIED',len(shapes),'connected oriented OSM rail shapes',flush=True)
 path=pathlib.Path(out);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')))
 print('ALL AUTHENTIC STOCKHOLM UPPSALA TRAIN STOP SEQUENCES VALIDATED ON REAL OSM RAILWAY',len(matched),flush=True)
if __name__=='__main__':
 if len(sys.argv)!=4:raise SystemExit('Usage: route_malartag_missing.py COVERAGE.json SWEDEN_RAIL.osm.pbf OUT.json')
 main(*sys.argv[1:])
