#!/usr/bin/env python3
"""Independent historical source cross-check for all published local route branches.

Only source operator lines from 2026-11-04 public GTFS, seven consecutive archive
dates, matched by exact station names and both directions. Not a license to
invent opposite return trains. Returns evidence for every suspected missing
short-turn reverse, including whether the source itself operated that return.
"""
import collections,datetime as dt,json,sys
from pathlib import Path
import build_rail_keyless as gtfs
LOCAL={'40','41','43','48','10','11','13','14','17','18','19','30','31',
       '12','21','7','27','28','29','25','26'}
DATES=[dt.date(2026,11,4)+dt.timedelta(days=i) for i in range(7)]
RAILTYPES={'0','1','2','100','101','102','103','106','109','400','401','402','403','404','405','900','901'}
def main(report_path,out):
 report=json.loads(Path(report_path).read_text())
 with gtfs.fetch_archive() as z:
  calendar=gtfs.service_calendar(z,DATES)
  active=set().union(*calendar.values())
  agencies={r.get('agency_id'):r.get('agency_name','') for r in gtfs.records(z,'agency.txt')}
  routes={}
  for r in gtfs.records(z,'routes.txt'):
   line=(r.get('route_short_name') or '').strip()
   if line not in LOCAL:continue
   agency=agencies.get(r.get('agency_id'),'')
   if not any(w in agency.casefold() for w in ('sl','stockholms','trafikförvaltningen','ab storstockholms lokaltrafik')):
    continue
   if r.get('route_type') not in RAILTYPES:continue
   routes[r['route_id']]=(line,agency)
  assert routes,'Cannot authenticate SL local rail routes in original archive'
  trips={r['trip_id']:r for r in gtfs.records(z,'trips.txt')
         if r.get('route_id') in routes and r.get('service_id') in active}
  station={r.get('stop_id'):r.get('stop_name','') for r in gtfs.records(z,'stops.txt')}
  ends=collections.defaultdict(list)
  for r in gtfs.records(z,'stop_times.txt'):
   tid=r.get('trip_id')
   if tid not in trips:continue
   name=station.get(r.get('stop_id'))
   if not name:continue
   try:seq=int(r.get('stop_sequence',''))
   except ValueError:continue
   t=gtfs.clock(r.get('departure_time')) or gtfs.clock(r.get('arrival_time'))
   if t is None:continue
   ends[tid].append((seq,name,t))
  published=report['systems']
  source_pairs=collections.Counter()
  day_pairs=collections.defaultdict(set)
  source_samples={}
  for tid,rows in ends.items():
   rows.sort()
   if len(rows)<2:continue
   a,b=rows[0][1],rows[-1][1]
   line=routes[trips[tid]['route_id']][0]
   pair=(line,a,b)
   source_pairs[pair]+=1
   days=[str(day) for day in DATES if trips[tid]['service_id'] in calendar[day]]
   day_pairs[pair].update(days)
   source_samples.setdefault(pair,{'tripId':tid,'sourceDays':days,'departureSeconds':rows[0][2]})
  checks=[]
  warnings=report['coverageWarnings']
  for w in warnings:
   if w[0]!='missing_reverse_physical_origin_destination':continue
   _,system,line,missing=w
   for a,b,templates in missing:
    rev=(line,b,a)
    found=source_pairs.get(rev,0)
    same=source_pairs.get((line,a,b),0)
    checks.append({'system':system,'line':line,'publishedOriginal':a+' → '+b,
     'unpublishedReverse':b+' → '+a,'originalPublishedTemplates':templates,
     'originalSourceTripIds':same,'reverseSourceTripIds':found,
     'reverseDays':sorted(day_pairs.get(rev,set())),
     'reverseSourceExample':source_samples.get(rev),
     'classification':('real_historic_reverse_missing_from_published_snapshot' if found else
                        'source_did_not_run_reverse_in_seven_day_reference')})
  output={'archive':gtfs.URL,'referenceDays':list(map(str,DATES)),
   'authenticatedSLRailRoutes':len(routes),'authenticatedSLRailTripIds':len(trips),
   'lineSourceTripCounts':dict(collections.Counter(routes[t['route_id']][0] for t in trips.values())),
   'reverseChecks':checks,
   'missingReverseInPublishedButPresentSource':sum(x['reverseSourceTripIds']>0 for x in checks),
   'sourceItselfHasNoReverse':sum(x['reverseSourceTripIds']==0 for x in checks),
   'warnings':['SL archived timetable source is a historical reference sample, not all future dates',
    'Source route numbers do not always map cleanly to a present-day SL line number']}
  Path(out).parent.mkdir(parents=True,exist_ok=True)
  Path(out).write_text(json.dumps(output,ensure_ascii=False,indent=2))
  print('PACKAGE07 AUTHENTIC HISTORIC SL RAIL ROUTES',len(routes),'TRIPS',len(trips),flush=True)
  for e in checks:print('PACKAGE07 REVERSE SOURCE CHECK',json.dumps(e,ensure_ascii=False),flush=True)
  print('PACKAGE07 REVERSE AUDIT RESULT',output['missingReverseInPublishedButPresentSource'],
   'SOURCE RETURNS NOT IN WEBSITE,',output['sourceItselfHasNoReverse'],
   'WITHOUT REFERENCE RETURN',flush=True)
if __name__=='__main__':
 if len(sys.argv)!=3:raise SystemExit('Usage: audit_package07_gtfs.py INVENTORY.json OUT.json')
 main(*sys.argv[1:])
