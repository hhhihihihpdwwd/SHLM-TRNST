#!/usr/bin/env python3
"""Atomic completion of five Mälartåg historical corridors on exact STABLE15.
Imports only 168 confirmed new Tuesday services; preserves all prior 10611
timetable entries, track shapes, licensed photos and front-facing train icons.
"""
from __future__ import annotations
import collections,copy,datetime as dt,json,sys
from pathlib import Path
from zoneinfo import ZoneInfo
from build_malartag_candidates import CORRIDORS,contains_station
from append_malartag import direction_of
from refine_osm_routes import project_stops

SOURCE_DAY='2026-11-10'
NEW_SCOPE_SUFFIX='-malartag-five'
def integrate(base,coverage,verified):
 assert len(base['trips'])==10611 and len(base['shapes'])==95
 assert base['scope'].endswith('-snalltaget-vy-tagab-rdc-sj-complete')
 assert base['type']=='historical-daily-repeating-simulation'
 template=base['simulationTemplateDay']
 assert template=='2026-11-09',template
 assert coverage['referenceDay']==SOURCE_DAY
 assert len(coverage['candidates'])==308
 already={x['id'] for x in coverage['already']}
 assert len(already)==140
 assert len(coverage['reused'])==128
 assert len(coverage['missing'])==40
 assert len(coverage['unclassified'])==0
 newrows=[x for x in coverage['candidates'] if x['id'] not in already]
 assert len(newrows)==168
 real=dict((x['tripId'],x) for x in coverage['reused'])
 real.update(verified['assignments'])
 assert len(real)==168
 assert len(verified['assignments'])==40
 result=copy.deepcopy(base)
 result['scope']=base['scope']+NEW_SCOPE_SUFFIX
 newshape=verified['shapes']
 for sid,shape in newshape.items():
  assert sid not in result['shapes']
  assert len(shape)>40
  result['shapes'][sid]=shape
 observed={t['shapeId']:t for t in base['trips'] if t.get('shapeId') in base['shapes']}
 reverses={}
 included=[]
 epoch=dt.datetime.combine(dt.date.fromisoformat(template),dt.time(),ZoneInfo('Europe/Stockholm'))
 for r in newrows:
  ref=real[r['id']];sid=ref['shapeId']
  assert sid in result['shapes'],('Unproven existing railway shape',sid)
  shape=result['shapes'][sid]
  if ref.get('reverse'):
   rid='malartag-five-reverse:'+sid
   if rid not in result['shapes']:
    result['shapes'][rid]=shape[::-1]
   sid=rid;shape=result['shapes'][sid]
  match=project_stops(r['stops'],shape,650)
  if match is None:raise ValueError('Mälartåg stops not on real original OSM track '+r['id'])
  dr=direction_of(r)
  if dr not in ('forward','reverse'):
   raise ValueError('Cannot authenticate corridor train direction '+r['id'])
  if r['corridor'] not in CORRIDORS:raise ValueError('Unknown Mälartåg line')
  begin,end=r['firstDeparture'],r['lastArrival']
  if not (0<=begin<end<=48*3600):raise ValueError('Invalid authentic GTFS time '+r['id'])
  for i in range(1,len(r['stops'])):
   a,b=r['stops'][i-1],r['stops'][i]
   duration=b[3]-a[4]
   if duration<=0:raise ValueError('Non-increasing authentic train clock '+r['id'])
   velocity=(match[i]-match[i-1])/duration*3.6
   if velocity<0 or velocity>210:raise ValueError('Unrealistic railway timetable speed '+str(velocity)+' '+r['id'])
  original=ref['shapeId']
  exemplar=observed.get(original)
  if original in newshape or original.startswith(('sj-complete-osm:','rdc-osm-rail:','tagab-osm:')):
   quality='verified-osm-rail-ways';way_network=True;relation=None
  elif exemplar is not None and exemplar.get('geometryQuality') in ('verified-osm-relation','verified-osm-rail-ways'):
   quality=exemplar['geometryQuality']
   way_network=exemplar.get('osmWayNetwork') is True
   relation=exemplar.get('osmRelation') if quality=='verified-osm-relation' else None
  else:
   raise ValueError('No trustworthy OSM source provenance for reused train shape '+original)
  train={
   'id':'MALARTAG-FIVE-20261110:'+r['id'],'mode':'regional','agency':'Mälartåg',
   'line':r['corridor'],'corridor':r['corridor'],
   'routeName':r['routeName'],'destination':r['destination'],'train':r['train'],
   'serviceDay':template,'start':int((epoch+dt.timedelta(seconds=begin)).timestamp()),
   'end':int((epoch+dt.timedelta(seconds=end)).timestamp()),'stops':r['stops'],
   'shapeId':sid,'geometryQuality':quality,'osmWayNetwork':way_network,
   'direction':dr,'osmRelation':relation,'archiveDay':SOURCE_DAY,
   'sourceDays':r['sourceDays'],'source':'GTFS Sverige 2 historical November 2026 original Mälartåg 313',
   'isLiveGPS':False,'vehicleModel':'Mälartåg ER1 typical (actual rolling stock not trip-confirmed)',
   'vehiclePhotoStatus':'approved-model-reference',
   'historicPattern':'Authentic November 10 reference train repeated daily in illustrative simulation',
   'malartagFiveVerified':True,'sourceTripId':r['id']
  }
  included.append(train)
 result['trips'].extend(included)
 result['counts']['regional']+=len(included)
 allmal=[t for t in result['trips'] if t.get('agency')=='Mälartåg']
 result['malartagCorridors']=dict(collections.Counter(t.get('corridor') for t in allmal))
 drcount=collections.defaultdict(collections.Counter)
 for train in allmal:
  direction=train.get('direction') or direction_of(train)
  if direction in ('forward','reverse'):drcount[train['corridor']][direction]+=1
 result['malartagDirections']={k:dict(v) for k,v in drcount.items()}
 result['malartagCoverage']={}
 for corridor,stops in CORRIDORS.items():
  trains=[t for t in allmal if t.get('corridor')==corridor]
  if not trains:raise ValueError('Entire Mälartåg corridor missing '+corridor)
  names=[p[2] for t in trains for p in t['stops']]
  missing=[s for s in stops if not any(contains_station(n,s) for n in names)]
  if missing:raise ValueError('Missing whole corridor essential stations '+str((corridor,missing)))
  if any(drcount[corridor].get(d,0)<1 for d in ('forward','reverse')):
   raise ValueError('Missing direction for Mälartåg corridor '+corridor)
  result['malartagCoverage'][corridor]={'requiredStops':len(stops),'scheduledStops':len(set(names))}
 result['malartagFiveDailyNew']=len(included)
 result['malartagFiveSource']='Original Tuesday 10 Nov 2026 GTFS Sverige 2, Mälartåg agency 313'
 result['malartagFiveCompleteCorridors']=list(CORRIDORS)
 assert result['trips'][:10611]==base['trips']
 assert all(result['shapes'][k]==v for k,v in base['shapes'].items())
 for k,v in base.items():
  if k not in ('scope','trips','shapes','counts','malartagCorridors','malartagDirections','malartagCoverage'):
   assert result[k]==v,('Old field changed',k)
 for k,v in base['counts'].items():
  assert result['counts'][k]==v+(168 if k=='regional' else 0)
 print('ATOMIC COMPLETE FIVE-MÄLARTÅG CORRIDOR RELEASE',len(included),'NEW REAL TUESDAY REFERENCE TRAINS',
  len(result['trips']),'TOTAL RECORDS',len(result['shapes']),'PHYSICAL SHAPES')
 print('FULL FIVE-CORRIDOR HISTORIC COVERAGE',json.dumps(result['malartagCorridors'],ensure_ascii=False))
 return result

if __name__=='__main__':
 if len(sys.argv)!=5:raise SystemExit('Usage: append_malartag_five.py STABLE15.json COVERAGE.json VERIFIED_OSM.json OUT.json')
 a,b,c=[json.loads(Path(p).read_text()) for p in sys.argv[1:4]]
 out=integrate(a,b,c);path=Path(sys.argv[4]);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')))
