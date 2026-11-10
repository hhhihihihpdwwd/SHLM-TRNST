#!/usr/bin/env python3
"""Read-only historic GTFS investigation of Vy Tåg Stockholm–Oslo.
Never invent operator IDs, times, service days, stations or lines.
No production write/deploy.
"""
from __future__ import annotations
import collections, datetime as dt, json
import build_rail_keyless as gtfs

DATES=[dt.date(2026,11,d) for d in (6,7,8,13,14,15)]
TRAIN_TYPES={'2','100','101','102','103','106','109'}
def norm(s):return (s or '').casefold().strip()
def main():
 with gtfs.fetch_archive() as zipfile:
  valid=gtfs.service_calendar(zipfile,DATES)
  agencies={x.get('agency_id'):x.get('agency_name','') for x in gtfs.records(zipfile,'agency.txt')}
  selected={k:v for k,v in agencies.items() if 'vy' in norm(v) or 'tågkompaniet' in norm(v)}
  print('GTFS VY AGENCIES',json.dumps(selected,ensure_ascii=False),flush=True)
  routes={r['route_id']:r for r in gtfs.records(zipfile,'routes.txt')
    if r.get('agency_id') in selected and r.get('route_type') in TRAIN_TYPES}
  print('VY TRAIN ROUTES',len(routes),flush=True)
  for rid,r in list(routes.items())[:50]:
   print('VY ROUTE',rid,'TYPE',r.get('route_type'),'AGENCY',agencies.get(r.get('agency_id')),
    'SHORT',r.get('route_short_name'),'LONG',r.get('route_long_name'),flush=True)
  services=set().union(*valid.values())
  trips={r['trip_id']:r for r in gtfs.records(zipfile,'trips.txt')
   if r.get('route_id') in routes and r.get('service_id') in services}
  stops={}
  for r in gtfs.records(zipfile,'stops.txt'):
   if not r.get('stop_id'):continue
   try:lat,lon=float(r['stop_lat']),float(r['stop_lon'])
   except (KeyError,ValueError):continue
   if 58.0<lat<63.0 and 9.0<lon<21.0:stops[r['stop_id']]=[lat,lon,r.get('stop_name','')]
  bytrip=collections.defaultdict(list)
  for row in gtfs.records(zipfile,'stop_times.txt'):
   tid=row.get('trip_id')
   if tid not in trips or row.get('stop_id') not in stops:continue
   try:idx=int(row.get('stop_sequence','-1'))
   except ValueError:continue
   first=gtfs.clock(row.get('arrival_time'));last=gtfs.clock(row.get('departure_time'))
   if first is None or last is None:continue
   bytrip[tid].append((idx,stops[row['stop_id']],first,last))
  report=[]
  for tid,seq in bytrip.items():
   seq.sort(key=lambda r:r[0]);names=[norm(x[1][2]) for x in seq]
   if len(seq)<3:continue
   if not any('stockholm central' in n for n in names):continue
   if not any('oslo' in n or 'karlstad' in n or 'charlottenberg' in n for n in names):continue
   t=trips[tid];active=[str(d) for d in DATES if t['service_id'] in valid[d]]
   if not active:continue
   r=routes[t['route_id']]
   item={'id':tid,'route':r.get('route_short_name'),'agency':agencies.get(r.get('agency_id')),
    'days':active,'headsign':t.get('trip_headsign'),'stops':[[q[1][2],q[1][0],q[1][1],q[2],q[3]] for q in seq]}
   report.append(item)
   print('AUTHENTIC VY STOCKHOLM JOURNEY',json.dumps(item,ensure_ascii=False),flush=True)
  report.sort(key=lambda x:x['id'])
  print('VY STOCKHOLM–KARLSTAD/OSLO DAY-VALID TRIPS',len(report),flush=True)
  if not report:raise RuntimeError('No verified Vy Stockholm trains in archive; do not fabricate data')
if __name__=='__main__':main()
