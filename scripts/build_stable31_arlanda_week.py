#!/usr/bin/env python3
"""Complete historic Arlanda Express week, not a fabricated daily Friday replay.

Only accept real GTFS Sverige 2 archived service-days with three actual stops
and already-published verified Arlanda Express OSM relation geometries.
A missing train, unrecognized terminus or missing track is a fatal audit error.
"""
import argparse,collections,datetime as dt,json,sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0,'scripts')
from build_rail_keyless import SOURCE_START,fetch_archive,service_calendar,records,clock
from build_arlanda_candidates import exact_terminal
from refine_osm_routes import project_stops
DAYLIST=[SOURCE_START+dt.timedelta(days=i) for i in range(7)]
ZONE=ZoneInfo('Europe/Stockholm')

def build(base):
 assert base['metroWeekdaySimulation'] is True
 assert base['commuterWeekdaySimulation'] is True
 assert base['localWeekdaySimulation'] is True
 assert base['counts']['express']==540
 originals=[t for t in base['trips'] if t.get('agency')=='Arlanda Express']
 assert len(originals)==540
 verified_by_direction=collections.defaultdict(dict)
 for t in originals:
  assert t['mode']=='express' and t['geometryQuality']=='verified-osm-relation'
  direction=exact_terminal(t['stops'])
  assert direction is not None,'Original Arlanda trip missing known three stations'
  sid=t['shapeId']
  assert sid in base['shapes']
  verified_by_direction[direction][sid]=t
 assert set(verified_by_direction)=={'to-city','to-airport'}
 with fetch_archive() as z:
  calendar=service_calendar(z,DAYLIST)
  agencies={row.get('agency_id'):row.get('agency_name','') for row in records(z,'agency.txt')}
  routes={}
  for r in records(z,'routes.txt'):
   agency=agencies.get(r.get('agency_id'),'')
   if agency.casefold().strip()=='arlanda express' and r.get('route_type') in ('2','100','101'):
    routes[r['route_id']]=(agency,r.get('route_short_name'))
  assert routes,'Missing source Arlanda Express rail routes'
  tid={}
  for row in records(z,'trips.txt'):
   if row.get('route_id') not in routes:continue
   days=[day for day in DAYLIST if row.get('service_id') in calendar[day]]
   if days:tid[row['trip_id']]=(routes[row['route_id']],row.get('trip_headsign',''),days)
  stop={}
  for r in records(z,'stops.txt'):
   name=r.get('stop_name','').casefold()
   if not any(key in name for key in ('stockholm centralstation','arlanda södra','arlanda norra')):continue
   try:lat,lon=float(r['stop_lat']),float(r['stop_lon'])
   except (ValueError,KeyError):continue
   if 59.2<lat<59.9 and 17.7<lon<18.3:
    stop[r['stop_id']]=[round(lat,6),round(lon,6),r['stop_name']]
  times=collections.defaultdict(list)
  for r in records(z,'stop_times.txt'):
   ticket=r.get('trip_id')
   if ticket not in tid:continue
   p=stop.get(r.get('stop_id'))
   if p is None:raise RuntimeError('Unmatched GTFS source stop '+str(r.get('stop_id'))+' for '+ticket)
   a,d=clock(r.get('arrival_time')),clock(r.get('departure_time'))
   if a is None:a=d
   if d is None:d=a
   if a is None or d is None:raise RuntimeError('Bad exact GTFS source clock '+ticket)
   times[ticket].append((int(r['stop_sequence']),p,a,d))
  assert set(times)==set(tid),'Missing GTFS stop-times for source Arlanda journey'
  accepted=[];counts=collections.Counter();all_source=collections.Counter()
  for ticket,(route,head,days) in tid.items():
   stations=sorted(times[ticket],key=lambda p:p[0])
   points=[[p[1][0],p[1][1],p[1][2],p[2],p[3]] for p in stations]
   direction=exact_terminal(points)
   if direction is None:
    raise RuntimeError('Reject incomplete/unsupported GTFS Arlanda trip '+ticket+str([p[2] for p in points]))
   sid=next((key for key in verified_by_direction[direction] if project_stops(points,base['shapes'][key],420) is not None),None)
   if not sid:raise RuntimeError('No existing real Arlanda OSM track for '+ticket)
   exemplar=verified_by_direction[direction][sid]
   departure=points[0][4];arrival=points[-1][3]
   assert 0<=departure<arrival<=48*3600
   for day in days:
    base_time=dt.datetime.combine(day,dt.time(),ZONE)
    accepted.append({
      'id':'ARLANDA-GTFS-WEEK:'+day.isoformat()+':'+ticket,
      'mode':'express','line':'AX','agency':'Arlanda Express',
      'routeNumber':'46','train':route[1] or '',
      'destination':head or points[-1][2],
      'serviceDay':day.isoformat(),
      'start':int((base_time+dt.timedelta(seconds=departure)).timestamp()),
      'end':int((base_time+dt.timedelta(seconds=arrival)).timestamp()),
      'stops':points,'sourceTripId':ticket,
      'shapeId':sid,'osmRelation':exemplar.get('osmRelation'),
      'geometryQuality':'verified-osm-relation',
      'vehicleModel':exemplar.get('vehicleModel','X3'),
      'vehiclePhotoStatus':exemplar.get('vehiclePhotoStatus','approved-X3-photo'),
      'source':'GTFS Sverige 2 authentic 2026-11-04 historical seven-day service calendar',
      'archiveDay':day.isoformat(),'isLiveGPS':False
    })
    counts[(day.isoformat(),direction)]+=1
    all_source[day.isoformat()]+=1
  # Strict completeness: no dropped authentic historical train on either track.
  assert len(accepted)==sum(len(v[2]) for v in tid.values())
  assert len({t['id'] for t in accepted})==len(accepted)
  expected={'2026-11-04':180,'2026-11-05':180,'2026-11-06':180,
   '2026-11-07':160,'2026-11-08':180,'2026-11-09':180,'2026-11-10':180}
  assert all_source==expected,('Archive changed or partial source',dict(all_source))
  assert len(accepted)==1240
  for day in expected:
   assert counts[(day,'to-airport')]>0 and counts[(day,'to-city')]>0
  result={**base,'trips':[t for t in base['trips'] if t.get('agency')!='Arlanda Express']+accepted,
   'counts':{**base['counts'],'express':len(accepted)},
   'arlandaDirections':dict(collections.Counter('to-airport' if exact_terminal(t['stops'])=='to-airport'
     else 'to-city' for t in accepted)),
   'arlandaWeekdaySimulation':True,
   'arlandaWeekdaySourceDays':{str(day.weekday()):day.isoformat() for day in DAYLIST},
   'arlandaWeeklyCoverage':{day.isoformat():{
     'to-airport':counts[(day.isoformat(),'to-airport')],
     'to-city':counts[(day.isoformat(),'to-city')]} for day in DAYLIST},
   'arlandaSourceDisclaimer':'Historic GTFS Sverige 2 weekdays from Nov 2026, not current live GPS or guaranteed special timetable'}
  assert result['shapes']==base['shapes'],'Never touch any existing OSM railway'
  assert [t for t in result['trips'] if t.get('agency')!='Arlanda Express']==[
    t for t in base['trips'] if t.get('agency')!='Arlanda Express']
  assert all(result['counts'][mode]==value for mode,value in base['counts'].items() if mode!='express')
  assert len(result['trips'])==len(base['trips'])-540+1240
  print('REAL ARLANDA EXPRESS COMPLETE WEEK',len(accepted),'GTFS source journeys',flush=True)
  print('SOURCE DAY/ROUTE COUNTS',dict(all_source),dict(counts),flush=True)
  return result

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--source',required=True,type=Path)
 p.add_argument('--output',required=True,type=Path)
 a=p.parse_args()
 base=json.loads(a.source.read_text(encoding='utf8'))
 changed=build(base)
 output=json.dumps(changed,ensure_ascii=False,separators=(',',':'))
 assert len(output.encode())<100_000_000,'Asset size cap'
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(output,encoding='utf8')
 print('ARLANDA GTFS STRICT SOURCE OUT',len(output.encode()),flush=True)
if __name__=='__main__':main()
