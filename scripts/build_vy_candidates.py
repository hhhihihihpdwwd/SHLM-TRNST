#!/usr/bin/env python3
"""Import actual Vy Tåg Stockholm–Oslo GTFS weekend services (Fri 6, Sat 7, Sun 8 Nov 2026).
A single representative Fri/Sat/Sun is replayed on corresponding historic weekdays,
not as invented daily service. Read-only until an independently verified OSM path exists.
"""
from __future__ import annotations
import collections,datetime as dt,json,sys
from pathlib import Path
import build_rail_keyless as gtfs

ROOT=Path(__file__).resolve().parents[1]
OPERATOR='Vy Tåg'
REFERENCE=[dt.date(2026,11,x) for x in (6,7,8)]
TRAIN_TYPES={'2','100','101','102','103','106','109'}
def n(x):return (x or '').casefold().strip()
def choose(seq):
 names=[n(s[1][2]) for s in seq]
 indices=[i for i,name in enumerate(names) if name=='stockholm centralstation']
 if not indices:return None
 idx=indices[0]
 if idx not in (0,len(seq)-1):return None
 if len(seq)<3 or not any(('karlstad centralstation'==k or 'oslo s'==k or 'charlottenberg station'==k) for k in names):return None
 if seq[-1][2]<=seq[0][3]:return None
 return 'from-stockholm' if idx==0 else 'to-stockholm'
def build(archive,template_day):
 valid=gtfs.service_calendar(archive,REFERENCE)
 agencies={r.get('agency_id'):r.get('agency_name','') for r in gtfs.records(archive,'agency.txt')}
 owner={k for k,v in agencies.items() if n(v)==n(OPERATOR)}
 if not owner:raise ValueError('Historical GTFS missing exact Vy Tåg operator')
 routes={r['route_id']:r for r in gtfs.records(archive,'routes.txt')
         if r.get('agency_id') in owner and r.get('route_type') in TRAIN_TYPES}
 service_ids=set().union(*valid.values())
 trips={r['trip_id']:r for r in gtfs.records(archive,'trips.txt')
        if r.get('route_id') in routes and r.get('service_id') in service_ids}
 stops={}
 for s in gtfs.records(archive,'stops.txt'):
  try:lat,lon=float(s['stop_lat']),float(s['stop_lon'])
  except (ValueError,KeyError):continue
  if 58.5<lat<61 and 10<lon<19.5:
   stops[s['stop_id']]=[round(lat,6),round(lon,6),s.get('stop_name','')]
 times=collections.defaultdict(list)
 for row in gtfs.records(archive,'stop_times.txt'):
  tid=row.get('trip_id')
  if tid not in trips or row.get('stop_id') not in stops:continue
  try:seq=int(row['stop_sequence'])
  except (ValueError,KeyError):continue
  arrive=gtfs.clock(row.get('arrival_time'));depart=gtfs.clock(row.get('departure_time'))
  if arrive is None or depart is None:continue
  times[tid].append((seq,stops[row['stop_id']],arrive,depart))
 result=[];counts=collections.Counter()
 for tid,seq in times.items():
  seq.sort(key=lambda x:x[0]);direction=choose(seq)
  if direction is None:continue
  source=trips[tid]
  days=[day for day in REFERENCE if source['service_id'] in valid[day]]
  if not days:continue
  for day in days:
   local_midnight=dt.datetime.combine(template_day,dt.time(),tzinfo=gtfs.ZONE)
   row={'id':'VY-GTFS:'+tid+':'+str(day),'mode':'intercity','agency':OPERATOR,
     'sourceAgency':OPERATOR,'line':'Vy Tåg','train':routes[source['route_id']].get('route_short_name') or tid,
     'direction':direction,'destination':seq[-1][1][2],'serviceDay':str(template_day),
     'archiveDay':str(day),'historicWeekday':day.weekday(),
     'start':int((local_midnight+dt.timedelta(seconds=seq[0][3])).timestamp()),
     'end':int((local_midnight+dt.timedelta(seconds=seq[-1][2])).timestamp()),
     'stops':[[s[1][0],s[1][1],s[1][2],s[2],s[3]] for s in seq],
     'source':'GTFS Sverige 2 historical Vy Tåg 2026-11-04 ZIP; weekday '+day.isoformat(),
     'geometryQuality':'awaiting-verified-OSM','shapeId':None,'isLiveGPS':False,
     'vehicleModel':'Vy Tåg (exact rolling stock not confirmed)',
     'vehiclePhotoStatus':'illustrative-only'}
   assert row['end']>row['start']
   result.append(row);counts[(day.weekday(),direction)]+=1
 if not result or not any(t['direction']=='to-stockholm' for t in result) or not any(t['direction']=='from-stockholm' for t in result):
  raise ValueError('Authentic Vy weekend Stockholm route does not cover both directions')
 print('VY AUTHENTIC GTFS CANDIDATES',len(result),'BY WEEKDAY/DIRECTION',dict((str(k),v) for k,v in counts.items()),flush=True)
 for t in result:print('VY CANDIDATE',t['train'],t['archiveDay'],t['direction'],t['stops'][0][2],'→',t['stops'][-1][2],len(t['stops']),'STOPS',flush=True)
 return {'operator':OPERATOR,'sourceArchive':gtfs.URL,'referenceDays':list(map(str,REFERENCE)),
  'templateDay':str(template_day),'weekdayService':True,'trips':result}
def main():
 if len(sys.argv)!=3:raise SystemExit('Usage: build_vy_candidates.py YYYY-MM-DD OUT.json')
 day=dt.date.fromisoformat(sys.argv[1])
 with gtfs.fetch_archive() as archive:r=build(archive,day)
 out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(r,ensure_ascii=False,separators=(',',':')));print('VY GTFS CANDIDATES WRITTEN',out,flush=True)
if __name__=='__main__':main()
