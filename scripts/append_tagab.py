#!/usr/bin/env python3
"""Add ONLY actual GTFS Tågab Stockholm services with complete connected OSM rail shapes to STABLE11.
No fabrication, no geometry interpolation, no alteration of any original 14 systems.
All real source departures are replayed daily by Stockholm Rail's shared simulator.
"""
import copy,json,sys
from pathlib import Path
from refine_osm_routes import project_stops
BASE_SCOPE='pendeltag-tunnelbana-tvarbanan-localtram-city7-roslags-saltsjo-arlanda-sj-malartag-vr-snalltaget-vy'
def integrate(base,candidates,osm):
 if base.get('scope')!=BASE_SCOPE or len(base.get('trips',[]))!=10417 or len(base.get('shapes',{}))!=63:
  raise ValueError('Only exact frozen 14-system STABLE11 release accepted')
 if candidates.get('operator')!='Tågab' or len(candidates.get('trips',[]))<8:
  raise ValueError('Historic authentic Tågab operator/GTFS trips required')
 if not osm.get('corridors') or len(osm.get('tripsMatched',{}))!=len(candidates['trips']):
  raise ValueError('Every authenticated train must be proven on real OSM railway')
 result=copy.deepcopy(base)
 added={}
 for corridor in ('katrineholm','vasteras'):
  info=osm['corridors'][corridor]
  shape=info['shape']
  if not isinstance(shape,list) or len(shape)<100 or info['maxSegmentMetres']>4000 or info['verifiedConsecutiveOsmWayEdges']<99:
   raise ValueError('Invalid physically connected original railway '+corridor)
  for direction in ('from-stockholm','to-stockholm'):
   sid='tagab-osm:'+corridor+':'+direction
   result['shapes'][sid]=shape if direction=='from-stockholm' else list(reversed(shape))
   added[(corridor,direction)]=sid
 for t in candidates['trips']:
  assert t['agency']=='Tågab' and t['mode']=='intercity'
  assert t['serviceDay']==base['simulationTemplateDay']
  if t.get('isLiveGPS') is not False:raise ValueError('GTFS must not claim GPS data')
  key=(t['corridor'],t['direction']);sid=added.get(key)
  if not sid or t['id'] not in osm['tripsMatched']:raise ValueError('Unverified GTFS train '+t['id'])
  if project_stops(t['stops'],result['shapes'][sid],650) is None:
   raise ValueError('Real GTFS stations not ordered along physical OSM rails '+t['id'])
  result['trips'].append({**t,'shapeId':sid,'geometryQuality':'verified-osm-rail-ways',
    'osmWayNetwork':True,'isLiveGPS':False})
 result['scope']=BASE_SCOPE+'-tagab'
 result['counts']['intercity']+=len(candidates['trips'])
 result['tagabSource']='Tågåkeriet i Bergslagen 2026-11-04 GTFS, daily repeating historical templates'
 result['tagabDirections']={
   'from-stockholm':sum(t['direction']=='from-stockholm' for t in candidates['trips']),
   'to-stockholm':sum(t['direction']=='to-stockholm' for t in candidates['trips'])
 }
 # Only the four new original-OSM shapes and the extra real train records may change.
 assert result['trips'][:10417]==base['trips']
 assert all(result['shapes'][key]==value for key,value in base['shapes'].items())
 for key,value in base.items():
  if key not in ('scope','trips','shapes','counts'):assert result[key]==value,key
 for key,value in base['counts'].items():
  assert result['counts'][key]==value+(len(candidates['trips']) if key=='intercity' else 0)
 print('NEW AUTHENTIC TAGAB TRAINS',len(candidates['trips']),'NEW VERIFIED OSM TRACKS',len(added),
       'ORIGINAL 10417 TRAINS UNTOUCHED',flush=True)
 return result
if __name__=='__main__':
 if len(sys.argv)!=5:raise SystemExit('Usage: append_tagab.py STABLE11.json GTFS.json OSM.json OUT.json')
 base,gtfs,osm=[json.loads(Path(p).read_text()) for p in sys.argv[1:4]]
 out=integrate(base,gtfs,osm)
 dest=Path(sys.argv[4]);dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')))
 print('15-SYSTEM RAIL RELEASE CANDIDATE',dest,len(out['trips']),'services',len(out['shapes']),'rail shapes')
