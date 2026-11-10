#!/usr/bin/env python3
"""Extract authentic 2026 Tågåkeriet i Bergslagen Stockholm GTFS journeys.
Archive times are used as DAILY historical simulation templates as requested.
No fabricated trains, stops, train IDs or timestamps.
"""
from __future__ import annotations
import collections,datetime as dt,json,sys
from pathlib import Path
import build_rail_keyless as gtfs
from zoneinfo import ZoneInfo

DAYS=[dt.date(2026,11,d) for d in range(4,16)]
BASE_DAY=dt.date(2026,11,6)
ZONE=ZoneInfo('Europe/Stockholm')
TRAIN_TYPES={'2','100','101','102','103','106','109'}
def norm(s):return (s or '').casefold().strip()
def stockholm(name):return 'stockholm central' in norm(name) or norm(name)=='stockholm c'

def build():
 with gtfs.fetch_archive() as archive:
  valid=gtfs.service_calendar(archive,DAYS)
  agencies={x.get('agency_id'):x.get('agency_name','') for x in gtfs.records(archive,'agency.txt')}
  owners={k:v for k,v in agencies.items() if 'tågåkeriet i bergslagen' in norm(v) or 'tagakeriet i bergslagen' in norm(v)}
  if not owners:raise ValueError('Cannot authenticate Tågab operator in historic GTFS')
  routes={x['route_id']:x for x in gtfs.records(archive,'routes.txt')
   if x.get('agency_id') in owners and x.get('route_type') in TRAIN_TYPES}
  services=set().union(*valid.values())
  trips={x['trip_id']:x for x in gtfs.records(archive,'trips.txt')
   if x.get('route_id') in routes and x.get('service_id') in services}
  stations={}
  for x in gtfs.records(archive,'stops.txt'):
   try:lat,lon=float(x['stop_lat']),float(x['stop_lon'])
   except (ValueError,KeyError):continue
   if 56.8<lat<61.2 and 11.2<lon<19.1:
    stations[x['stop_id']]=[round(lat,6),round(lon,6),x.get('stop_name','')]
  sequences=collections.defaultdict(list)
  for x in gtfs.records(archive,'stop_times.txt'):
   tid=x.get('trip_id')
   if tid not in trips or x.get('stop_id') not in stations:continue
   a,d=gtfs.clock(x.get('arrival_time')),gtfs.clock(x.get('departure_time'))
   if a is None or d is None:continue
   try:order=int(x['stop_sequence'])
   except (ValueError,KeyError):continue
   sequences[tid].append((order,stations[x['stop_id']],a,d))
  results=[]
  midnight=dt.datetime.combine(BASE_DAY,dt.time(),ZONE)
  for tid,rows in sequences.items():
   rows.sort(key=lambda z:z[0]);places=[r[1][2] for r in rows]
   if len(rows)<3 or not any(stockholm(n) for n in places):continue
   if not(stockholm(places[0]) or stockholm(places[-1])):continue
   if not any(any(k in norm(n) for k in ['karlstad','kristinehamn','göteborg']) for n in places):continue
   source=trips[tid];service_dates=[day for day in DAYS if source['service_id'] in valid[day]]
   if not service_dates:continue
   if rows[-1][2]<=rows[0][3]:raise ValueError('Nonincreasing real GTFS train time '+tid)
   via='vasteras' if any('västerås' in norm(n) for n in places) else 'katrineholm' if any('katrineholm' in norm(n) for n in places) else None
   if via is None:raise ValueError('Unknown historic Tågab Stockholm railway corridor for '+tid)
   direction='from-stockholm' if stockholm(places[0]) else 'to-stockholm'
   train=routes[source['route_id']].get('route_short_name') or tid
   row={
    'id':'TAGAB-GTFS:'+tid,'mode':'intercity','agency':'Tågab',
    'sourceAgency':owners[routes[source['route_id']]['agency_id']],
    'train':train,'line':'Tågab','direction':direction,'destination':places[-1],
    'serviceDay':BASE_DAY.isoformat(),'historicWeekdays':sorted({d.weekday() for d in service_dates}),
    'archiveDays':[d.isoformat() for d in service_dates],
    'historicPattern':'authentic GTFS departure repeated DAILY in Stockholm Rail simulation',
    'corridor':via,
    'start':int((midnight+dt.timedelta(seconds=rows[0][3])).timestamp()),
    'end':int((midnight+dt.timedelta(seconds=rows[-1][2])).timestamp()),
    'stops':[[r[1][0],r[1][1],r[1][2],r[2],r[3]] for r in rows],
    'source':'GTFS Sverige 2 sweden-20261104.zip; Tågåkeriet i Bergslagen',
    'isLiveGPS':False,'geometryQuality':'awaiting-verified-OSM','shapeId':None,
    'vehicleModel':'Tågab (exact locomotive assignment not confirmed)',
    'vehiclePhotoStatus':'illustrative-only'
   }
   results.append(row)
  results.sort(key=lambda t:(t['train'],t['start'],t['id']))
  if len(results)<8:raise ValueError('Insufficient real Tågab Stockholm trains in archive')
  if not {t['direction'] for t in results}=={'from-stockholm','to-stockholm'}:
   raise ValueError('Authentic GTFS did not cover both directions')
  if not {t['corridor'] for t in results}=={'katrineholm','vasteras'}:
   raise ValueError('Historic GTFS lacks both real track corridors')
  if not any('göteborg' in norm(t['destination']) for t in results):
   raise ValueError('No verified Stockholm–Göteborg historic train')
  print('AUTHENTIC TAGAB STOCKHOLM CANDIDATES',len(results),flush=True)
  for row in results:
   print('GTFS TRAIN',row['train'],row['direction'],row['corridor'],row['destination'],
    'SOURCE DAYS',row['archiveDays'],'STOPS',[x[2] for x in row['stops']],flush=True)
  return {'operator':'Tågab','sourceAgency':'Tågåkeriet i Bergslagen',
   'sourceArchive':gtfs.URL,'referenceDay':BASE_DAY.isoformat(),
   'historicSimulation':'daily repetition of existing real GTFS trips, not actual daily service',
   'trips':results}

if __name__=='__main__':
 if len(sys.argv)!=2:raise SystemExit('Usage: build_tagab_candidates.py OUT.json')
 obj=build()
 out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':')))
 print('SAVED AUTHENTIC TAGAB HISTORIC TRAIN TEMPLATES',out,len(obj['trips']),flush=True)
