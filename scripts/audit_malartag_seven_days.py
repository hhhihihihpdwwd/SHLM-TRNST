#!/usr/bin/env python3
"""Complete Mälartåg November 2026 audit across seven archive service days.
Produce historical unmodified GTFS trips and classify all five real corridors.
Read-only, no fabricated departure, no new public site.
"""
import collections,datetime as dt,json,sys
from pathlib import Path
import build_rail_keyless as gtfs
from build_malartag_candidates import CORRIDORS,corridor_for,agency_ok,norm
DAYS=[dt.date(2026,11,4)+dt.timedelta(days=i) for i in range(7)]
TRAINTYPES={'2','100','101','102','103','106','109'}
def main(path):
 with gtfs.fetch_archive() as z:
  agency={r.get('agency_id'):r.get('agency_name','') for r in gtfs.records(z,'agency.txt')}
  routes={r['route_id']:r for r in gtfs.records(z,'routes.txt')
    if r.get('route_type') in TRAINTYPES and agency_ok(agency.get(r.get('agency_id')))}
  print('REAL MÄLARTÅG AGENCIES',json.dumps({k:v for k,v in agency.items() if agency_ok(v)},ensure_ascii=False),flush=True)
  print('REAL MÄLARTÅG ROUTES',len(routes),flush=True)
  services=gtfs.service_calendar(z,DAYS)
  eligible_services=set().union(*services.values())
  trips={r['trip_id']:r for r in gtfs.records(z,'trips.txt')
   if r.get('route_id') in routes and r.get('service_id') in eligible_services}
  pts={}
  for r in gtfs.records(z,'stops.txt'):
   try:lat,lon=float(r['stop_lat']),float(r['stop_lon'])
   except (ValueError,KeyError):continue
   if 56.5<lat<61.8 and 13.1<lon<20:
    pts[r['stop_id']]=[round(lat,6),round(lon,6),r.get('stop_name','')]
  times=collections.defaultdict(list)
  for r in gtfs.records(z,'stop_times.txt'):
   tid=r.get('trip_id')
   if tid not in trips or r.get('stop_id') not in pts:continue
   a=gtfs.clock(r.get('arrival_time'));d=gtfs.clock(r.get('departure_time'))
   if a is None and d is None:continue
   try:seq=int(r['stop_sequence'])
   except (KeyError,ValueError):continue
   times[tid].append([seq,pts[r['stop_id']],a if a is not None else d,d if d is not None else a])
  groups=collections.defaultdict(list);unknown=[];invalid=[]
  for tid,records in times.items():
   records.sort(key=lambda x:x[0])
   if len(records)<2:continue
   t=trips[tid];route=routes[t['route_id']]
   text=' '.join([route.get('route_short_name',''),route.get('route_long_name',''),t.get('trip_headsign','')])
   stations=[r[1][2] for r in records]
   corridor=corridor_for(stations,text)
   daylist=[str(day) for day in DAYS if t['service_id'] in services[day]]
   item={'id':tid,'corridor':corridor,'sourceDays':daylist,
    'routeId':t['route_id'],'routeName':text,'origin':stations[0],'destination':stations[-1],
    'stops':[[*r[1],r[2],r[3]] for r in records],
    'train':t.get('trip_short_name') or route.get('route_short_name') or tid,
    'firstDeparture':records[0][3],'lastArrival':records[-1][2]}
   if records[-1][2]<=records[0][3]:
    invalid.append(item);continue
   if corridor not in CORRIDORS:unknown.append(item);continue
   groups[corridor].append(item)
  out={'archive':gtfs.URL,'referenceDays':list(map(str,DAYS)),'corridors':dict(groups),
   'unclassified':unknown,'invalidClock':invalid}
  Path(path).parent.mkdir(parents=True,exist_ok=True)
  Path(path).write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')))
  for k in CORRIDORS:
   values=groups[k];byday=collections.Counter(d for t in values for d in t['sourceDays'])
   print('MÄLARTÅG SEVEN-DAY CORRIDOR',k,'UNIQUE',len(values),'DAYS',json.dumps(byday,ensure_ascii=False),
    'ENDPOINTS',json.dumps(collections.Counter((x['origin'],x['destination']) for x in values).most_common(20),ensure_ascii=False),flush=True)
  print('MÄLARTÅG UNCLASSIFIED',len(unknown),'INVALID',len(invalid),flush=True)
  if unknown:
   print('UNCLASSIFIED ROUTES',json.dumps(collections.Counter((x['origin'],x['destination'],x['routeName']) for x in unknown).most_common(20),ensure_ascii=False),flush=True)
  if any(not groups[k] for k in CORRIDORS):raise ValueError('Missing authentic timetable for some of five Mälartåg corridors')
if __name__=='__main__':
 if len(sys.argv)!=2:raise SystemExit('Usage: audit_malartag_seven_days.py OUTPUT.json')
 main(sys.argv[1])
