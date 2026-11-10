#!/usr/bin/env python3
"""Append ONLY official 2026 RDC EuroNight 344/345 historical templates
to the exact frozen STABLE12 (15 systems). Never edit earlier train services,
photo records or the physical geometry of the original 67 rail shapes.
"""
from __future__ import annotations
import copy,json,sys
from pathlib import Path
from refine_osm_routes import project_stops
BASE_SCOPE='pendeltag-tunnelbana-tvarbanan-localtram-city7-roslags-saltsjo-arlanda-sj-malartag-vr-snalltaget-vy-tagab'
def integrate(base,candidates,rail):
 if base.get('scope')!=BASE_SCOPE or len(base.get('trips',[]))!=10433 or len(base.get('shapes',{}))!=67:
  raise ValueError('Requires EXACT stable 15-system STABLE12 public site')
 if candidates.get('operator')!='RDC EuroNight' or len(candidates.get('trips',[]))!=4:
  raise ValueError('Missing authentic operator-published RDC EuroNight 2026 timetable')
 if rail.get('officialTimetable')!=candidates.get('officialTimetable') or len(rail.get('routes',{}))!=4:
  raise ValueError('Four physically verified international EN344/345 railway routes required')
 out=copy.deepcopy(base)
 out['scope']=BASE_SCOPE+'-rdc'
 for t in candidates['trips']:
  assert t['agency']=='RDC EuroNight' and t['mode']=='intercity'
  assert t['serviceDay']==base['simulationTemplateDay'] and t['isLiveGPS'] is False
  info=rail['routes'].get(t['id'])
  if not info:raise ValueError('No actual OSM railway path for official RDC train '+t['id'])
  shape=info.get('shape')
  if not isinstance(shape,list) or len(shape)<500 or info.get('maxSegmentMetres',1e8)>4000:
   raise ValueError('Disconnected or unverified original OSM railway path '+t['id'])
  if info.get('verifiedConsecutiveOsmWayEdges',0)<499:
   raise ValueError('No adjacent original OSM railway node proof '+t['id'])
  if project_stops(t['stops'],shape,650) is None:
   raise ValueError('Operator station sequence does not match true connected OSM path '+t['id'])
  sid='rdc-osm-rail:'+t['id']
  out['shapes'][sid]=shape
  out['trips'].append({**t,'shapeId':sid,'geometryQuality':'verified-osm-rail-ways',
   'osmWayNetwork':True,'isLiveGPS':False})
 out['counts']['intercity']+=4
 out['rdcDirections']={'to-stockholm':2,'from-stockholm':2}
 out['rdcOfficialSchedule']=candidates['officialTimetable']
 out['rdcSimulationNote']='Original 2026 reference-day EuroNight patterns repeated every day in illustrative simulation; no live GPS'
 assert out['trips'][:10433]==base['trips']
 assert all(out['shapes'][key]==value for key,value in base['shapes'].items())
 for key,value in base.items():
  if key not in ('scope','trips','shapes','counts'):assert out[key]==value,key
 for key,value in base['counts'].items():
  assert out['counts'][key]==value+(4 if key=='intercity' else 0)
 print('EXACT RDC EURONIGHT IMPORT',len(out['trips']),'HISTORIC REFERENCE TRAINS',len(out['shapes']),
  'VERIFIED OSM SHAPES, ALL 10433 EXISTING TRIPS IMMUTABLE',flush=True)
 return out
if __name__=='__main__':
 if len(sys.argv)!=5:raise SystemExit('Usage: append_rdc.py STABLE12.json OFFICIAL.json OSM.json OUT.json')
 base,official,osm=[json.loads(Path(p).read_text()) for p in sys.argv[1:4]]
 out=integrate(base,official,osm);p=Path(sys.argv[4]);p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')))
