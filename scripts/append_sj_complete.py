#!/usr/bin/env python3
"""Single approved SJ release: append genuine historical Stockholm SJ journeys
for South/West/North/Night in one atomic data-only change to frozen STABLE13.
Requires 100% verified original shared-node OSM track matches; fail closed.
"""
from __future__ import annotations
import collections,copy,datetime as dt,json,sys
from pathlib import Path
from zoneinfo import ZoneInfo
from refine_osm_routes import project_stops

BASE_SCOPE='pendeltag-tunnelbana-tvarbanan-localtram-city7-roslags-saltsjo-arlanda-sj-malartag-vr-snalltaget-vy-tagab-rdc'
ZONE=ZoneInfo('Europe/Stockholm')
def integrate(base,report,routes):
 if base.get('scope')!=BASE_SCOPE or len(base.get('trips',[]))!=10437 or len(base.get('shapes',{}))!=71:
  raise ValueError('Requires exactly publicly verified STABLE13 16-system website')
 stats=report['summary']
 assert stats['selectedDailyReferenceTemplates']==231
 assert stats['alreadyPublishedSJDuplicates']==57
 assert stats['readyOnExistingVerifiedOSMShapes']==80
 assert stats['missingVerifiedRailShapes']==94
 if routes.get('failures') or len(routes.get('assignments',{}))!=94:
  raise ValueError('Cannot release incomplete SJ network; unverified route coverage')
 if routes.get('stats',{}).get('failed')!=0:
  raise ValueError('No SJ route failure allowed')
 selected=report['selected']
 oldids=set(report['alreadyPresentIds'])
 matched={m['tripId']:m for m in report['matched']}
 unmatched=routes['assignments']
 newrecords=[t for t in selected if t['id'] not in oldids]
 assert len(newrecords)==174
 result=copy.deepcopy(base)
 result['scope']=BASE_SCOPE+'-sj-complete'
 existing_shapes=result['shapes']
 for k,v in routes['newShapes'].items():
  assert k not in existing_shapes and len(v)>10
  existing_shapes[k]=v
 reverseids={}
 additions=[]
 template=dt.date.fromisoformat(base['simulationTemplateDay'])
 midnight=dt.datetime.combine(template,dt.time(),ZONE)
 for t in newrecords:
  ref=matched.get(t['id']) or unmatched.get(t['id'])
  if not ref:raise ValueError('No physical OSM geometry for '+t['id'])
  sid=ref['shapeId']
  if sid not in existing_shapes:raise ValueError('Missing true physical rail shape '+sid)
  shape=existing_shapes[sid]
  if ref.get('reverse'):
   if sid not in reverseids:
    reverseids[sid]='sj-complete-reverse:'+sid
    assert reverseids[sid] not in existing_shapes
    existing_shapes[reverseids[sid]]=list(reversed(shape))
   sid=reverseids[sid];shape=existing_shapes[sid]
  if project_stops(t['stops'],shape,650) is None:
   raise ValueError('Authentic ordered SJ stations mismatch OSM track '+t['id'])
  first,last=t['firstDeparture'],t['lastArrival']
  if first<0 or last<=first or last>48*3600:raise ValueError('Invalid original GTFS hours '+t['id'])
  duration=last-first
  night=duration>=8*3600 or first//86400!=last//86400 or last>86400
  item={
    'id':'SJ-FULL-20261106:'+t['id'],'mode':'intercity','agency':'SJ',
    'line':'SJ','train':t['routeShortName'] or t['id'],
    'destination':t['destination'],'direction':'from-stockholm' if t['origin'].casefold().startswith('stockholm central') else 'to-stockholm',
    'sourceAgency':'SJ','sourceTripId':t['id'],
    'serviceDay':template.isoformat(),
    'start':int((midnight+dt.timedelta(seconds=first)).timestamp()),
    'end':int((midnight+dt.timedelta(seconds=last)).timestamp()),
    'stops':t['stops'],'shapeId':sid,
    'geometryQuality':'verified-osm-rail-ways','osmWayNetwork':True,'sjCompleteVerified':True,
    'source':'GTFS Sverige 2 historic 2026-11-04 archive, authenticated SJ operator',
    'sourceDays':t['sourceDays'],
    'historicPattern':'Original historical GTFS journey repeated daily as illustrative simulation',
    'isLiveGPS':False,'serviceCategory':'night' if night else 'day',
    'vehicleModel':'SJ train (actual rolling-stock type not confirmed)',
    'vehiclePhotoStatus':'illustrative-only'
  }
  additions.append(item)
 result['trips'].extend(additions)
 result['counts']['intercity']+=len(additions)
 result['sjCompleteSource']='GTFS Sverige 2 historical 2026-11-04, all verified 2026-11-06 Stockholm trains plus representative unique terminal families'
 result['sjCompleteAdded']=len(additions)
 result['sjCompleteNight']=sum(x['serviceCategory']=='night' for x in additions)
 result['sjCompleteBaselinePreserved']=True
 assert result['trips'][:10437]==base['trips']
 assert all(result['shapes'][k]==v for k,v in base['shapes'].items())
 for key,val in base.items():
  if key not in ('scope','shapes','trips','counts'):assert result[key]==val,key
 for key,val in base['counts'].items():
  assert result['counts'][key]==val+(len(additions) if key=='intercity' else 0)
 print('ONE ATOMIC SJ HISTORIC NETWORK RELEASE',len(additions),
       'NEW AUTHENTIC SJ TRAIN TEMPLATES',
       'INCLUDING',result['sjCompleteNight'],'LONG/NIGHT TRIPS',
       'TOTAL',len(result['trips']),'TRAIN TEMPLATES',
       'TRACKS',len(result['shapes']),
       'ALL 10437 ORIGINAL TRAINS UNCHANGED',flush=True)
 return result

if __name__=='__main__':
 if len(sys.argv)!=5:raise SystemExit('Usage: append_sj_complete.py STABLE13.json SJ_COVER.json REAL_OSM.json OUTPUT.json')
 base,cover,osm=[json.loads(Path(p).read_text()) for p in sys.argv[1:4]]
 out=integrate(base,cover,osm)
 path=Path(sys.argv[4]);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')))
