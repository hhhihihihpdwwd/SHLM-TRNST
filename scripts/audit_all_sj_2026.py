#!/usr/bin/env python3
"""Audit ALL authentically identified SJ AB Stockholm-relevant rail journeys
for seven historical weekdays in the same November 2026 GTFS reference archive.
Read-only. No train or station is invented, no operator reassignment, and
nothing is published until fully connected OSM tracks are independently proven.
"""
from __future__ import annotations
import collections,datetime as dt,json,sys
from pathlib import Path
import build_rail_keyless as gtfs

SOURCE_DATES=[dt.date(2026,11,4)+dt.timedelta(days=i) for i in range(7)]
RAIL_TYPES={'2','100','101','102','103','106','109'}
def norm(s):return (s or '').strip().casefold()
def valid_sj(name):
    name=norm(name)
    return name=='sj' or name=='sj ab' or name.startswith('sj ab ') or name.startswith('sj ')
def stockholm(s):
    return 'stockholm central' in norm(s) or norm(s)=='stockholm c'
def main():
 with gtfs.fetch_archive() as archive:
  services=gtfs.service_calendar(archive,SOURCE_DATES)
  agencies={row.get('agency_id'):row.get('agency_name','') for row in gtfs.records(archive,'agency.txt')}
  owners={k:v for k,v in agencies.items() if valid_sj(v)}
  print('AUTHENTIC SJ OPERATOR IDS',json.dumps(owners,ensure_ascii=False),flush=True)
  routes={r['route_id']:r for r in gtfs.records(archive,'routes.txt')
    if r.get('agency_id') in owners and r.get('route_type') in RAIL_TYPES}
  print('AUTHENTIC SJ RAIL ROUTES',len(routes),flush=True)
  service_ids=set().union(*services.values())
  trips={r['trip_id']:r for r in gtfs.records(archive,'trips.txt')
    if r.get('route_id') in routes and r.get('service_id') in service_ids}
  print('ACTIVE AUTHENTIC SJ GTFS TRIP IDS IN SEVEN DAYS',len(trips),flush=True)
  stops={}
  for r in gtfs.records(archive,'stops.txt'):
    try:lat,lon=float(r['stop_lat']),float(r['stop_lon'])
    except (ValueError,KeyError,TypeError):continue
    if 55.0<lat<70.0 and 10.0<lon<25.0:
      stops[r['stop_id']]=[round(lat,6),round(lon,6),r.get('stop_name','')]
  times=collections.defaultdict(list)
  for row in gtfs.records(archive,'stop_times.txt'):
    tid=row.get('trip_id');point=stops.get(row.get('stop_id'))
    if tid not in trips or not point:continue
    a=gtfs.clock(row.get('arrival_time'));d=gtfs.clock(row.get('departure_time'))
    if a is None and d is None:continue
    try:idx=int(row['stop_sequence'])
    except (ValueError,KeyError):continue
    times[tid].append((idx,point,a if a is not None else d,d if d is not None else a))
  rows=[];endpoints=collections.Counter();days=collections.Counter()
  for tid,seq in times.items():
    seq.sort(key=lambda x:x[0])
    if len(seq)<2:continue
    if not any(stockholm(s[1][2]) for s in seq):continue
    r=trips[tid];route=routes[r['route_id']]
    active=[str(day) for day in SOURCE_DATES if r['service_id'] in services[day]]
    if not active:continue
    # Preserve only physical train journeys with exact full original stop orders.
    stations=[[x[1][0],x[1][1],x[1][2],x[2],x[3]] for x in seq]
    record={
      'id':tid,'agency':owners[route['agency_id']],
      'routeId':r['route_id'],'routeShortName':route.get('route_short_name',''),
      'routeLongName':route.get('route_long_name',''),
      'headsign':r.get('trip_headsign',''),'sourceDays':active,
      'origin':stations[0][2],'destination':stations[-1][2],
      'stopCount':len(stations),'firstDeparture':stations[0][4],
      'lastArrival':stations[-1][3],'stops':stations}
    if record['lastArrival']<=record['firstDeparture']:continue
    rows.append(record)
    endpoints[(record['origin'],record['destination'])]+=1
    for day in active:days[day]+=1
  rows.sort(key=lambda x:(x['origin'],x['destination'],x['firstDeparture'],x['id']))
  print('SJ EXACT STOCKHOLM-CALLING HISTORICAL GTFS JOURNEYS',len(rows),flush=True)
  print('SJ SOURCE-DAY COUNTS',json.dumps(days,ensure_ascii=False),flush=True)
  for (a,b),count in endpoints.most_common():
    example=next(x for x in rows if x['origin']==a and x['destination']==b)
    print('SJ ENDPOINT PAIR',count,repr(a),'→',repr(b),
          'stops',example['stopCount'],'first',example['firstDeparture'],'route',example['routeShortName'],flush=True)
  data={'sourceArchive':gtfs.URL,'referenceDates':list(map(str,SOURCE_DATES)),
        'operatorIds':owners,'trips':rows,'endpointCounts':[
        {'origin':a,'destination':b,'uniqueTripIds':count} for (a,b),count in endpoints.most_common()]}
  out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True)
  out.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')))
  if not rows:raise RuntimeError('No real SJ Stockholm GTFS trips found: do not fabricate')
  print('STORED VERIFIED OPERATOR-ASSIGNED SJ AUDIT',out,out.stat().st_size,'BYTES',flush=True)
if __name__=='__main__':
 if len(sys.argv)!=2:raise SystemExit('Usage: audit_all_sj_2026.py OUT.json')
 main()
