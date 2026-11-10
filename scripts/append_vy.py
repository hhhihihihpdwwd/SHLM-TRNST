#!/usr/bin/env python3
"""Append only independently GTFS-verified and physically OSM-verified Vy Tåg journeys.
Never touch or silently repair any of STABLE09's 10407 original services.
"""
import copy,collections,json,sys
from pathlib import Path
from refine_osm_routes import project_stops
BASE_SCOPE='pendeltag-tunnelbana-tvarbanan-localtram-city7-roslags-saltsjo-arlanda-sj-malartag-vr-snalltaget'
def integrate(base,candidates,osm):
 if base.get('scope')!=BASE_SCOPE or len(base.get('trips',[]))!=10407 or len(base.get('shapes',{}))!=61:
  raise ValueError('Only exact 13-system STABLE09 site accepted')
 if candidates.get('operator')!='Vy Tåg' or not candidates.get('weekdayService'):
  raise ValueError('No authenticated Vy historical weekday GTFS')
 shape=osm.get('shape')
 if not isinstance(shape,list) or len(shape)<100 or osm.get('maxSegmentMetres',1e9)>4000:
  raise ValueError('Missing fully connected original physical OSM railway graph')
 accepted=[];counts=collections.Counter();skipped=collections.Counter()
 geometries=(('to-oslo',shape),('to-stockholm',list(reversed(shape))))
 for t in candidates['trips']:
  if t['agency']!='Vy Tåg' or t['mode']!='intercity' or t['serviceDay']!=base['simulationTemplateDay']:continue
  if t.get('historicWeekday') not in (4,5,6):continue
  if t.get('isLiveGPS') is not False:raise ValueError('False live/GPS claim')
  matches=[key for key,g in geometries if project_stops(t['stops'],g,650) is not None]
  if not matches:
   skipped[(t['direction'],t['archiveDay'])]+=1
   print('VY REJECTED UNVERIFIED RAIL PATH',t['train'],t['archiveDay'],flush=True)
   continue
  sid='vy-osm-rail:'+matches[0]
  accepted.append({**t,'shapeId':sid,'geometryQuality':'verified-osm-rail-ways',
   'osmWayNetwork':True,'isLiveGPS':False})
  counts[(t['historicWeekday'],t['direction'])]+=1
 if not any(t['direction']=='to-stockholm' for t in accepted) or not any(t['direction']=='from-stockholm' for t in accepted):
  raise ValueError('Both authentic Vy directions must be OSM-verified: '+str(dict(counts)))
 if len(accepted)<4:raise ValueError('Too few genuine connected Vy trains')
 out=copy.deepcopy(base)
 out['scope']=BASE_SCOPE+'-vy'
 out['shapes']['vy-osm-rail:to-oslo']=shape
 out['shapes']['vy-osm-rail:to-stockholm']=list(reversed(shape))
 out['trips'].extend(accepted);out['counts']['intercity']+=len(accepted)
 out['vyWeekdayDirections']={str(k):v for k,v in counts.items()}
 out['vyWeekdaySource']='2026-11-06/07/08 GTFS actual Friday/Saturday/Sunday; repeated only same weekday'
 assert out['trips'][:10407]==base['trips']
 assert all(out['shapes'][k]==v for k,v in base['shapes'].items())
 for k,v in base.items():
  if k in ('scope','trips','shapes','counts'):continue
  assert out[k]==v,k
 for k,v in base['counts'].items():
  assert out['counts'][k]==v+(len(accepted) if k=='intercity' else 0)
 print('VY ISOLATED INTEGRATION',len(accepted),'NEW HISTORIC SERVICES',dict(counts),'REJECTED',dict(skipped),flush=True)
 return out
def main():
 if len(sys.argv)!=5:raise SystemExit('Usage: append_vy.py STABLE09.json VY_GTFS.json VY_OSM.json RELEASE.json')
 base,candidates,osm=[json.loads(Path(p).read_text()) for p in sys.argv[1:4]]
 result=integrate(base,candidates,osm);out=Path(sys.argv[4]);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')))
 print('14-SYSTEM CANDIDATE DATA',out,out.stat().st_size,flush=True)
if __name__=='__main__':main()
