#!/usr/bin/env python3
"""Package03: append only two GTFS-authenticated service journeys onto exact STABLE17.
Source operator, station order, OSM geometry and speeds independently validated.
Other 10,787 original services, 107 shapes, photos and map UI are immutable.
"""
import copy,datetime as dt,json,sys
from pathlib import Path
from zoneinfo import ZoneInfo
from refine_osm_routes import project_stops
BASE=10787
EXPECTED={'SJ':'740427004688000001','VR Snabbtåg':'680130054745000001'}
SHAPES={'SJ':'sj-complete-osm:011','VR Snabbtåg':'sj-complete-osm:010'}
DAY='2026-11-09'
def integrate(base,sj,vr):
 assert base['simulationTemplateDay']==DAY and base['type']=='historical-daily-repeating-simulation'
 assert len(base['trips'])==BASE and len(base['shapes'])==107 and base['scope'].endswith('-intl-four')
 assert len({t['id'] for t in base['trips']})==BASE
 published_sj={str(t.get('sourceTripId')) for t in base['trips'] if t['agency']=='SJ'}
 legacy={(tuple(s[2] for s in t['stops']),t['stops'][0][4],t['stops'][-1][3])
         for t in base['trips'] if t['agency']=='SJ' and not t.get('sourceTripId')}
 sj_candidates=[t for t in sj['trips'] if '2026-11-06' in t['sourceDays'] and
  t['id'] not in published_sj and
  (tuple(s[2] for s in t['stops']),t['firstDeparture'],t['lastArrival']) not in legacy]
 vr_published={str(t['id']).split(':')[1] for t in base['trips']
               if t['agency']=='VR Snabbtåg' and str(t['id']).startswith('VR-ARCHIVE:')}
 vr_candidates=[t for t in vr['trips'] if t['serviceDay']=='2026-11-06' and
                t['id'].split(':')[1] not in vr_published]
 assert len(sj_candidates)==len(vr_candidates)==1,'Source gaps changed; do not deploy'
 assert sj_candidates[0]['id']==EXPECTED['SJ']
 assert vr_candidates[0]['id'].split(':')[1]==EXPECTED['VR Snabbtåg']
 mid=dt.datetime.combine(dt.date.fromisoformat(DAY),dt.time(),ZoneInfo('Europe/Stockholm'))
 result=copy.deepcopy(base);additions=[]
 for agency,t in [('SJ',sj_candidates[0]),('VR Snabbtåg',vr_candidates[0])]:
  stops=t['stops'];sid=SHAPES[agency]
  positions=project_stops(stops,result['shapes'][sid],650)
  assert positions is not None,(agency,'source stations do not match connected existing OSM rail')
  assert all(stops[i][3]>stops[i-1][4] for i in range(1,len(stops)))
  speeds=[(positions[i]-positions[i-1])/(stops[i][3]-stops[i-1][4])*3.6
          for i in range(1,len(stops))]
  assert all(0<v<210 for v in speeds),(agency,speeds)
  first,last=stops[0][4],stops[-1][3]
  assert first>=0 and last>first and last<48*3600
  identifier=('SJ-FULL-20261106:'+t['id'] if agency=='SJ' else
              'VR-ARCHIVE:'+EXPECTED[agency]+':'+DAY)
  assert not any(x['id']==identifier for x in result['trips'])
  # Do not introduce another vehicle simultaneously departing the same source
  # station with the same operator and published departure time.
  same=[x['id'] for x in result['trips'] if x['agency']==agency and
        x['stops'][0][2]==stops[0][2] and x['stops'][0][4]==first and
        x['stops'][-1][2]==stops[-1][2]]
  assert not same,(agency,'possible parallel physical service',same)
  entry={
   'id':identifier,'mode':'intercity','agency':agency,
   'line':'SJ' if agency=='SJ' else 'VR',
   'train':t.get('routeShortName') or t['id'],
   'destination':stops[-1][2],
   'direction':'from-stockholm' if stops[0][2]=='Stockholm Centralstation' else 'to-stockholm',
   'sourceAgency':agency,'sourceTripId':EXPECTED[agency],
   'serviceDay':DAY,
   'start':int((mid+dt.timedelta(seconds=first)).timestamp()),
   'end':int((mid+dt.timedelta(seconds=last)).timestamp()),
   'stops':stops,'shapeId':sid,'geometryQuality':'verified-osm-rail-ways',
   'osmWayNetwork':True,'isLiveGPS':False,
   'source':'Authentic GTFS Sverige 2 2026-11-04 source, reference Friday 2026-11-06',
   'sourceDays':t.get('sourceDays',['2026-11-06']),
   'historicPattern':'Original verified historical reference Friday journey repeated daily as an illustrative simulation',
   'vehicleModel':agency+' train (actual consist not confirmed)',
   'vehiclePhotoStatus':'illustrative-only',
   'package03Verified':True
  }
  if agency=='SJ':entry['sjCompleteVerified']=True
  additions.append(entry)
  print('PACKAGE03 AUTHENTIC RAIL',agency,identifier,'STATIONS',len(stops),
        'REAL OSM',sid,'AVERAGE LEG SPEEDS',list(map(lambda x:round(x),speeds)),flush=True)
 result['trips']+=additions
 result['counts']['intercity']+=2
 result['package03Audit']={'newAuthenticJourneys':2,'sjAdded':1,'vrAdded':1,
                           'baseTemplates':BASE,'baseShapes':107,
                           'simulatedNotLive':True,'sourceFriday':'2026-11-06'}
 assert result['trips'][:BASE]==base['trips']
 assert result['shapes']==base['shapes']
 for key,value in base.items():
  if key in ('trips','counts'):continue
  assert result[key]==value,key
 for key,value in base['counts'].items():
  assert result['counts'][key]==value+(2 if key=='intercity' else 0)
 assert len(result['trips'])==10789
 return result
if __name__=='__main__':
 if len(sys.argv)!=5:raise SystemExit('Usage: integrate_package03.py STABLE17.json SJ.json VR.json OUTPUT.json')
 b,s,v=[json.loads(Path(p).read_text()) for p in sys.argv[1:4]]
 d=integrate(b,s,v)
 p=Path(sys.argv[4]);p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(d,ensure_ascii=False,separators=(',',':')))
 print('PACKAGE03 OUTPUT',len(d['trips']),len(d['shapes']),p,flush=True)
