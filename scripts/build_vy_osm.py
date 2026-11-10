#!/usr/bin/env python3
"""Route authentic Vy Stockholm–Oslo GTFS trains over connected OSM railway=rail WAY NODE IDs.
Fail closed if any critical railway link is absent; NO straight-line interpolation.
"""
from __future__ import annotations
import json,sys
from pathlib import Path
from osm_railway_way_router import route_osm_ways,dist
from refine_osm_routes import project_stops

def build(candidates):
 original=[t for t in candidates['trips'] if t['stops'][0][2]=='Stockholm Centralstation'
           and t['stops'][-1][2]=='Oslo S']
 if not original:raise ValueError('No full authentic Stockholm–Oslo Vy service')
 # Choose complete GTFS stops, not imaginary routing stations.
 selected=max(original,key=lambda t:len(t['stops']))
 print('VY OSM BASE SOURCE',selected['id'],'STOPS',len(selected['stops']),flush=True)
 shape=route_osm_ways(selected['stops'])
 assert len(shape)>=100
 # Railway vertices must actually connect; no jumps.
 maxstep=max(dist(a,b) for a,b in zip(shape,shape[1:]))
 assert maxstep<1500,('Railway geometry gap',maxstep)
 assert project_stops(selected['stops'],shape,650) is not None
 cover={'from-stockholm':0,'to-stockholm':0}
 for t in candidates['trips']:
  for key,g in (('east-west',shape),('west-east',list(reversed(shape)))):
   if project_stops(t['stops'],g,650) is not None:
    cover[t['direction']]+=1
    print('VY OSM VERIFIED TRAIN',t['train'],t['archiveDay'],t['direction'],key,flush=True)
    break
  else:print('VY REJECTED NOT ON FULL PHYSICAL OSM RAIL',t['id'],t['stops'][-1][2],flush=True)
 if not all(cover.values()):raise ValueError('Verified OSM shape does not support Vy both directions: '+str(cover))
 print('VY OSM VERIFIED PATH',len(shape),'VERTICES','MAX REAL WAY STEP',round(maxstep),'METRES', 'COVERAGE',cover,flush=True)
 return {'shape':shape,'source':'connected OSM railway=rail ways with shared OSM node IDs, no synthetic jumps',
  'maxSegmentMetres':round(maxstep,2),'sourceTrip':selected['id'],'matched':cover}
def main():
 if len(sys.argv)!=3:raise SystemExit('Usage: build_vy_osm.py CANDIDATES.json OUT.json')
 d=json.loads(Path(sys.argv[1]).read_text())
 route=build(d)
 p=Path(sys.argv[2]);p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(route,separators=(',',':')));print('VY VERIFIED OSM ROUTE WRITTEN',p,p.stat().st_size,flush=True)
if __name__=='__main__':main()
