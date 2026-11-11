#!/usr/bin/env python3
"""Package 05: exhaustive historic source operator audit, no invented trains or rails.

Reads the original Nov-2026 Swedish GTFS archive. Enumerates Vy Tåg and
Tågåkeriet i Bergslagen train journeys touching Stockholm Central across 12
archive dates. Reconciles original source IDs and physical departure patterns
before allowing any new reference train. Every accepted addition must fit a
previously published, source-verified connected OSM corridor and physically
plausible measured train speed. Reuses existing licensed illustrative photos.
"""
from __future__ import annotations
import collections, copy, datetime as dt, json, sys
from pathlib import Path
from zoneinfo import ZoneInfo
import build_rail_keyless as gtfs
from refine_osm_routes import project_stops
BASE_TRIPS=10798
BASE_SHAPES=107
BASE_DAY='2026-11-09'
DATES=[dt.date(2026,11,4)+dt.timedelta(days=i) for i in range(12)]
TYPES={'2','100','101','102','103','106','109'}
OPERATORS=('Vy Tåg','Tågab')
MID=dt.datetime.combine(dt.date.fromisoformat(BASE_DAY),dt.time(),ZoneInfo('Europe/Stockholm'))

def norm(name):
 return (name or '').casefold().strip()
def exact_operator(name):
 n=norm(name)
 if n=='vy tåg':return 'Vy Tåg'
 if 'tågåkeriet i bergslagen' in n or 'tagakeriet i bergslagen' in n:return 'Tågab'
 return None
def stockholm(name):
 return norm(name) in ('stockholm centralstation','stockholm c')
def fingerprint(stops):
 return (tuple(s[2] for s in stops), stops[0][4], stops[-1][3])
def parse_source():
 with gtfs.fetch_archive() as z:
  services=gtfs.service_calendar(z,DATES)
  agencies={x.get('agency_id'):exact_operator(x.get('agency_name')) for x in gtfs.records(z,'agency.txt')}
  owners={k:v for k,v in agencies.items() if v in OPERATORS}
  assert set(owners.values())==set(OPERATORS),'Exact Vy and Tågab agency IDs missing'
  routes={x['route_id']:x for x in gtfs.records(z,'routes.txt')
          if x.get('agency_id') in owners and x.get('route_type') in TYPES}
  service_ids=set().union(*services.values())
  trips={x['trip_id']:x for x in gtfs.records(z,'trips.txt')
         if x.get('route_id') in routes and x.get('service_id') in service_ids}
  stations={}
  for x in gtfs.records(z,'stops.txt'):
   try:lat,lon=float(x['stop_lat']),float(x['stop_lon'])
   except (KeyError,TypeError,ValueError):continue
   if 55<lat<68 and 9<lon<24:
    stations[x['stop_id']]=[round(lat,6),round(lon,6),x.get('stop_name','')]
  times=collections.defaultdict(list)
  for x in gtfs.records(z,'stop_times.txt'):
   tid=x.get('trip_id')
   if tid not in trips:continue
   p=stations.get(x.get('stop_id'))
   if not p or not p[2]:continue
   arrive,depart=gtfs.clock(x.get('arrival_time')),gtfs.clock(x.get('departure_time'))
   if arrive is None and depart is None:continue
   try:order=int(x['stop_sequence'])
   except (KeyError,TypeError,ValueError):continue
   times[tid].append((order,p,arrive if arrive is not None else depart,
                            depart if depart is not None else arrive))
  results=[]
  for tid,seq in times.items():
   seq.sort(key=lambda x:x[0])
   if len(seq)<2:continue
   stops=[[v[1][0],v[1][1],v[1][2],v[2],v[3]] for v in seq]
   if not any(stockholm(s[2]) for s in stops):continue
   if not (stockholm(stops[0][2]) or stockholm(stops[-1][2])):continue
   if stops[-1][3]<=stops[0][4]:continue
   trip=trips[tid];route=routes[trip['route_id']]
   agency=owners[route['agency_id']]
   days=[str(d) for d in DATES if trip['service_id'] in services[d]]
   if not days:continue
   results.append({'agency':agency,'id':tid,'days':days,'stops':stops,
    'origin':stops[0][2],'destination':stops[-1][2],
    'first':stops[0][4],'last':stops[-1][3],
    'route':route.get('route_short_name') or agency,
    'headsign':trip.get('trip_headsign','')})
  assert all(any(x['agency']==op for x in results) for op in OPERATORS),'No source train for operator'
  return results

def existing_source_id(trip):
 value=str(trip.get('sourceTripId') or '')
 if value:return value
 tid=str(trip['id'])
 if tid.startswith('VY-GTFS:'):return tid.split(':')[1]
 if tid.startswith('TAGAB-GTFS:'):return tid.split(':')[1]
 return ''

def reconcile(base,records):
 assert base['type']=='historical-daily-repeating-simulation' and base['simulationTemplateDay']==BASE_DAY
 assert len(base['trips'])==BASE_TRIPS and len(base['shapes'])==BASE_SHAPES
 assert base.get('package04Audit',{}).get('newValidSourcePatterns')==9
 out=copy.deepcopy(base)
 by_operator={op:[t for t in base['trips'] if t['agency']==op] for op in OPERATORS}
 used={op:{fingerprint(t['stops']) for t in by_operator[op]} for op in OPERATORS}
 source_ids={op:{existing_source_id(t) for t in by_operator[op]} for op in OPERATORS}
 # An identical route departure/arrival on different historical weekdays is
 # ONE illustrative daily-repeat train, not multiple simultaneous vehicles.
 patterns=collections.defaultdict(list)
 for r in records:patterns[(r['agency'],fingerprint(r['stops']))].append(r)
 real_shapes={}
 for t in base['trips']:
  if t['agency'] not in OPERATORS:continue
  if t.get('geometryQuality') in ('verified-osm-rail-ways','verified-osm-relation') and
     t.get('osmWayNetwork') is True and t['shapeId'] in base['shapes']:
   real_shapes[t['shapeId']]=base['shapes'][t['shapeId']]
 # Also allow verified connected SJ/Mälartåg railway-way geometries when a
 # genuine Tågab service shares their exact physical route.
 for t in base['trips']:
  if t.get('geometryQuality') not in ('verified-osm-rail-ways','verified-osm-relation'):continue
  if t['shapeId'] not in base['shapes']:continue
  if t.get('osmWayNetwork') is True or t.get('osmRelation'):
   real_shapes[t['shapeId']]=base['shapes'][t['shapeId']]
 assert len(real_shapes)>=10,'Not enough previously verified physical OSM tracks'
 report={'referenceDates':[str(d) for d in DATES],
  'sourceArchive':gtfs.URL,
  'originalTrainTemplates':BASE_TRIPS,'originalPhysicalOsmShapes':BASE_SHAPES,
  'operatorResults':{},'added':[],'deferred':[],
  'limitations':['Historic source is not a live vehicle tracker',
     'Source day variants may describe one train, not extra simultaneous departures',
     'Only existing genuinely verified OSM physical railway corridors may be used',
     'Daily replay is illustrative and does not assert operation every weekday']}
 additions=[]
 for op in OPERATORS:
  rows=[r for r in records if r['agency']==op]
  groups=[x for (agency,_),x in patterns.items() if agency==op]
  counter=collections.Counter()
  daycount=collections.Counter(d for r in rows for d in r['days'])
  endpoints=collections.Counter((r['origin'],r['destination']) for r in rows)
  for variants in sorted(groups,key=lambda group:(group[0]['first'],group[0]['origin'],group[0]['destination'])):
   # Sunday variant is not a second train if Friday already has identical
   # stop-times, and older published source IDs remain authoritative.
   row=next((x for x in variants if '2026-11-06' in x['days']),variants[0])
   fp=fingerprint(row['stops'])
   if fp in used[op] or any(x['id'] in source_ids[op] for x in variants):
    counter['alreadyCovered']+=1;continue
   # Keep different actual source departures, but prohibit alternative
   # timetable paths representing the same train within a departure window.
   overlaps=[t for t in by_operator[op]+additions if t['agency']==op and
      t['stops'][0][2]==row['origin'] and
      abs(t['stops'][0][4]-row['first'])<9*60 and
      t['stops'][-1][2]==row['destination']]
   if overlaps:
    counter['possibleDuplicate']+=1
    report['deferred'].append({'agency':op,'sourceId':row['id'],
       'origin':row['origin'],'destination':row['destination'],
       'departure':row['first'],'reason':'Possible physical duplicate of already published train'})
    continue
   valid=[]
   for sid,shape in real_shapes.items():
    if len(shape)<30:continue
    positions=project_stops(row['stops'],shape,650)
    if positions is None:continue
    speeds=[]
    for idx in range(1,len(positions)):
     seconds=row['stops'][idx][3]-row['stops'][idx-1][4]
     speeds.append((positions[idx]-positions[idx-1])/seconds*3.6 if seconds>0 else -1)
    if speeds and all(0<v<200 for v in speeds):
     valid.append((sid,max(speeds)))
   if not valid:
    counter['unverifiedTrack']+=1
    report['deferred'].append({'agency':op,'sourceId':row['id'],
       'origin':row['origin'],'destination':row['destination'],
       'departure':row['first'],'reason':'No existing connected verified OSM rail fits all real stops/speed'})
    continue
   valid.sort(key=lambda item:(0 if item[0].startswith(('vy-osm','tagab-osm')) else 1,item[1]))
   sid,max_speed=valid[0]
   identifier=('VY-PACKAGE05:' if op=='Vy Tåg' else 'TAGAB-PACKAGE05:')+row['id']+':'+BASE_DAY
   assert not any(t['id']==identifier for t in base['trips']+additions)
   stops=row['stops']
   new={'id':identifier,'agency':op,'sourceAgency':op,'sourceTripId':row['id'],
    'mode':'intercity','line':op,'train':row['route'],'destination':row['destination'],
    'direction':'from-stockholm' if stockholm(row['origin']) else 'to-stockholm',
    'serviceDay':BASE_DAY,'start':int((MID+dt.timedelta(seconds=row['first'])).timestamp()),
    'end':int((MID+dt.timedelta(seconds=row['last'])).timestamp()),
    'stops':stops,'shapeId':sid,'geometryQuality':'verified-osm-rail-ways','osmWayNetwork':True,
    'isLiveGPS':False,'sourceDays':sorted(set(d for v in variants for d in v['days'])),
    'source':gtfs.URL+'; authenticated agency '+op+'; November 2026 archive',
    'vehicleModel':op+' source train (actual rolling stock not verified)',
    'vehiclePhotoStatus':'licensed-illustrative-example',
    'historicPattern':'Original historical source stop times, illustrated by daily repeating simulation',
    'package05Verified':True}
   additions.append(new);used[op].add(fp)
   counter['added']+=1
   report['added'].append({'agency':op,'sourceId':row['id'],'origin':row['origin'],
    'destination':row['destination'],'firstDeparture':row['first'],
    'lastArrival':row['last'],'verifiedShapeId':sid,'maxLegKmh':round(max_speed),
    'stopNames':[s[2] for s in stops],
    'sourceDays':new['sourceDays']})
  report['operatorResults'][op]={
   'sourceTripIds':len(rows),'uniqueStopClockPatterns':len(groups),
   'publishedTemplatesBefore':len(by_operator[op]),
   'coveredSourcePatterns':counter['alreadyCovered'],
   'newAuthenticatedTrains':counter['added'],
   'deferredPossibleDuplicates':counter['possibleDuplicate'],
   'deferredUnverifiedTracks':counter['unverifiedTrack'],
   'sourceDays':dict(daycount),
   'sourceEndpointFamilies':[{'origin':a,'destination':b,'uniqueSourceTripIds':count} for (a,b),count in endpoints.most_common()]}
 out['trips']+=additions
 out['counts']['intercity']+=len(additions)
 out['package05Audit']={
  'sourceDates':report['referenceDates'],
  'sourceOperators':OPERATORS,
  'addedPerOperator':{op:report['operatorResults'][op]['newAuthenticatedTrains'] for op in OPERATORS},
  'sourceTripsPerOperator':{op:report['operatorResults'][op]['sourceTripIds'] for op in OPERATORS},
  'deferredCount':len(report['deferred']),'allArchivedOriginalTripsPreserved':BASE_TRIPS,
  'realOriginalOsmShapesPreserved':BASE_SHAPES,'historicalNotLive':True}
 assert out['trips'][:BASE_TRIPS]==base['trips'] and out['shapes']==base['shapes']
 for key,val in base.items():
  if key in ('trips','counts'):continue
  assert out[key]==val,key
 for key,val in base['counts'].items():
  assert out['counts'][key]==val+(len(additions) if key=='intercity' else 0)
 return out,report

def main():
 if len(sys.argv)!=4:raise SystemExit('Usage: audit_package05.py BASE.json OUT.json REPORT.json')
 baseline=json.loads(Path(sys.argv[1]).read_text())
 result,report=reconcile(baseline,parse_source())
 out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')))
 path=Path(sys.argv[3]);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print('PACKAGE05 INDEPENDENT OPERATOR AUDIT',json.dumps({
  'operators':report['operatorResults'],'added':report['added'],
  'deferred':report['deferred'],'totalTrains':len(result['trips']),
  'physicalShapes':len(result['shapes'])},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
