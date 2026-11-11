#!/usr/bin/env python3
"""Find ALL authenticated historical Stockholm-connected intercity trains for four
operator brands over November 4–15, 2026, not only previously imported routes.
Read-only; preserves every real original GTFS route, station, train, service date,
travel time and operator name. RDC official operator reference audited separately.
"""
from __future__ import annotations
import collections,datetime as dt,json,sys
from pathlib import Path
import build_rail_keyless as g
DAYS=[dt.date(2026,11,4)+dt.timedelta(days=i) for i in range(12)]
RAIL={'2','100','101','102','103','106','109'}
def operator(s):
 n=(s or '').casefold().strip()
 if 'snälltåget' in n or 'snalltaget' in n:return 'Snälltåget'
 if n=='vy tåg' or n=='vy tag':return 'Vy Tåg'
 if 'tågåkeriet i bergslagen' in n or 'tagakeriet i bergslagen' in n or n=='tågab':return 'Tågab'
 return None
def main(path):
 with g.fetch_archive() as z:
  calendar=g.service_calendar(z,DAYS)
  agencies={r['agency_id']:r.get('agency_name','') for r in g.records(z,'agency.txt')}
  ids={k:operator(v) for k,v in agencies.items() if operator(v)}
  print('AUTHENTIC 2026 INTERCITY OPERATOR AGENCIES',json.dumps(ids,ensure_ascii=False),flush=True)
  routes={r['route_id']:r for r in g.records(z,'routes.txt')
   if r.get('agency_id') in ids and r.get('route_type') in RAIL}
  services=set().union(*calendar.values())
  trips={t['trip_id']:t for t in g.records(z,'trips.txt')
    if t.get('route_id') in routes and t.get('service_id') in services}
  stations={}
  for s in g.records(z,'stops.txt'):
   try:lat,lon=float(s['stop_lat']),float(s['stop_lon'])
   except (KeyError,TypeError,ValueError):continue
   if 50<lat<70 and 7<lon<26:stations[s['stop_id']]=[round(lat,6),round(lon,6),s.get('stop_name','')]
  seq=collections.defaultdict(list)
  for row in g.records(z,'stop_times.txt'):
   tid=row.get('trip_id');p=stations.get(row.get('stop_id'))
   if tid not in trips or p is None:continue
   a=g.clock(row.get('arrival_time'));d=g.clock(row.get('departure_time'))
   if a is None and d is None:continue
   try:n=int(row['stop_sequence'])
   except (ValueError,KeyError):continue
   seq[tid].append((n,[*p,a if a is not None else d,d if d is not None else a]))
  data={k:[] for k in ('Snälltåget','Vy Tåg','Tågab')}
  excluded=collections.Counter()
  for tid,rows in seq.items():
   rows.sort(key=lambda x:x[0]);stops=[x[1] for x in rows]
   if len(stops)<2:continue
   old=trips[tid];route=routes[old['route_id']];agency=ids[route['agency_id']]
   if stops[-1][3]<=stops[0][4]:continue
   names=[s[2].casefold() for s in stops]
   stockholm=any('stockholm central' in s or s=='stockholm c' for s in names)
   if not stockholm:
    excluded[agency]+=1;continue
   days=[str(day) for day in DAYS if old['service_id'] in calendar[day]]
   record={'id':tid,'agency':agency,'routeId':old['route_id'],
    'routeShortName':route.get('route_short_name',''),
    'routeLongName':route.get('route_long_name',''),
    'headsign':old.get('trip_headsign',''),'sourceDays':days,
    'origin':stops[0][2],'destination':stops[-1][2],
    'firstDeparture':stops[0][4],'lastArrival':stops[-1][3],
    'stops':stops}
   data[agency].append(record)
  for agency,rows in data.items():
   pairs=collections.Counter((x['origin'],x['destination']) for x in rows)
   active=collections.Counter(d for x in rows for d in x['sourceDays'])
   print('INTERNATIONAL OPERATOR',agency,'UNIQUE TRAIN IDS',len(rows),
    'ACTIVE DATES',json.dumps(active,ensure_ascii=False),
    'ROUTES',json.dumps(pairs.most_common(40),ensure_ascii=False),flush=True)
  print('OTHER REAL GTFS SERVICES NOT CALLING STOCKHOLM',dict(excluded),flush=True)
  assert all(data[x] for x in data),'Missing authenticated operator railway trips'
  output={'source':g.URL,'referenceDays':list(map(str,DAYS)),'operatorData':data,
          'nonStockholmServiceCounts':dict(excluded)}
  out=Path(path);out.parent.mkdir(parents=True,exist_ok=True)
  out.write_text(json.dumps(output,ensure_ascii=False,separators=(',',':')))
if __name__=='__main__':
 if len(sys.argv)!=2:raise SystemExit('Usage: audit_international_four.py OUT.json')
 main(sys.argv[1])
