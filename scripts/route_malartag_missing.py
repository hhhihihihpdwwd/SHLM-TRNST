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
 for t in gaps:
  assert len(t['stops'])==2 and t['origin']!=t['destination']
 representative=next(t for t in gaps if t['origin']=='Stockholm Centralstation')
 points,network=load_graph([pathlib.Path(pbf)],representative['stops'])
 info=route_one('Stockholm C–Uppsala C original railway track',representative['stops'],points,network)
 shape=info['shape']
 assert 30<info['lengthKm']<110,('Unrealistic direct Stockholm Uppsala rail length',info)
 matched={}
 for t in gaps:
  oriented=shape if t['origin']=='Stockholm Centralstation' else shape[::-1]
  projected=project_stops(t['stops'],oriented,650)
  if projected is None:
   raise ValueError('Actual GTFS stops not on ordered real original railway: '+t['id'])
  span=projected[-1]-projected[0]
  elapsed=t['lastArrival']-t['firstDeparture']
  if elapsed<=0:raise ValueError('No real journey time '+t['id'])
  speed=span/elapsed*3.6
  if not 15<speed<220:raise ValueError('Unrealistic scheduled speed on true OSM rails '+str(speed)+' '+t['id'])
  matched[t['id']]={'shapeId':'malartag-new-osm:stockholm-uppsala:'+
    ('forward' if t['origin']=='Stockholm Centralstation' else 'reverse'),'scheduledKmH':round(speed,1)}
 print('ALL 40 MÄLARTÅG STOCKHOLM–UPPSALA TRAINS MATCH AUTHENTIC SHARED OSM RAILWAY NODE EDGES',
 len(matched),'KM',info['lengthKm'],flush=True)
 result={'originalPhysicalOSM':info,'shapes':{
 'malartag-new-osm:stockholm-uppsala:forward':shape,
 'malartag-new-osm:stockholm-uppsala:reverse':shape[::-1]},
 'assignments':matched,
 'routeDisclaimer':'Physical OSM route verified; no GPS or individual GTFS shape ID for express trains asserted'}
 path=pathlib.Path(out);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')))
 print('VERIFIED ORIGINAL REAL RAIL MÄLARTÅG CORRIDOR',len(shape),'NODES',info['lengthKm'],'KM',flush=True)
if __name__=='__main__':
 if len(sys.argv)!=4:raise SystemExit('Usage: route_malartag_missing.py COVERAGE.json SWEDEN_RAIL.osm.pbf OUT.json')
 main(*sys.argv[1:])
