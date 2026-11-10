#!/usr/bin/env python3
"""Read-only audit of authentic Tågab journeys in November 2026 GTFS Sverige 2.
Never relabel unrelated trains or synthesize departures.
"""
from __future__ import annotations
import collections,datetime as dt,json
import build_rail_keyless as gtfs
DAYS=[dt.date(2026,11,d) for d in range(4,16)]
def name(s):return (s or '').casefold()
def main():
 with gtfs.fetch_archive() as z:
  valid=gtfs.service_calendar(z,DAYS)
  agencies={x.get('agency_id'):x.get('agency_name','') for x in gtfs.records(z,'agency.txt')}
  matched={k:v for k,v in agencies.items() if any(q in name(v) for q in ('tågåkeriet','tagakeriet','tågab','tagab','bergslagen ab'))}
  print('TAGAB GTFS AGENCIES',json.dumps(matched,ensure_ascii=False),flush=True)
  for key,val in agencies.items():
   if any(q in name(val) for q in ('bergslagen','värmland','varmland')):
    print('RELATED BUT NOT ASSUMED TAGAB',key,val,flush=True)
  routes={r['route_id']:r for r in gtfs.records(z,'routes.txt') if r.get('agency_id') in matched}
  for r in list(routes.values())[:35]:
   print('TAGAB ROUTE',json.dumps(r,ensure_ascii=False),flush=True)
  services=set().union(*valid.values())
  journeys={r['trip_id']:r for r in gtfs.records(z,'trips.txt')
    if r.get('route_id') in routes and r.get('service_id') in services}
  print('TAGAB VALID TRIPS COUNT',len(journeys),flush=True)
  points={}
  for x in gtfs.records(z,'stops.txt'):
   try:lat,lon=float(x['stop_lat']),float(x['stop_lon'])
   except (KeyError,ValueError,TypeError):continue
   if 56.5<lat<61.8 and 10.5<lon<20.2:points[x['stop_id']]=[lat,lon,x.get('stop_name','')]
  sequences=collections.defaultdict(list)
  for x in gtfs.records(z,'stop_times.txt'):
   trip=x.get('trip_id');point=points.get(x.get('stop_id'))
   if trip not in journeys or point is None:continue
   arrival,departure=gtfs.clock(x.get('arrival_time')),gtfs.clock(x.get('departure_time'))
   if arrival is None or departure is None:continue
   try:order=int(x['stop_sequence'])
   except (ValueError,KeyError):continue
   sequences[trip].append((order,point,arrival,departure))
  found=[]
  for tid,stops in sequences.items():
   stops.sort(key=lambda x:x[0])
   places=[name(x[1][2]) for x in stops]
   if not any('stockholm central' in p or p=='stockholm c' for p in places):continue
   if len(stops)<3:continue
   source=journeys[tid]
   dates=[str(d) for d in DAYS if source['service_id'] in valid[d]]
   if not dates:continue
   data={'id':tid,'route':routes[source['route_id']].get('route_short_name'),
    'headsign':source.get('trip_headsign'),'dates':dates,
    'stopSequence':[[s[1][2],s[2],s[3]] for s in stops]}
   print('AUTHENTIC TAGAB STOCKHOLM TRIP',json.dumps(data,ensure_ascii=False),flush=True)
   found.append(data)
  print('AUTHENTIC TAGAB STOCKHOLM TRIPS',len(found),flush=True)
  if not found:
   raise RuntimeError('No Stockholm Tågab travel in archive under verified agency. Do not fabricate trains. Try operator timetable PDF for alternate archive.')
if __name__=='__main__':main()
