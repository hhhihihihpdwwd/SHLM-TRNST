#!/usr/bin/env python3
"""Readonly factual inventory of national railway timetable sources.

Use the same pinned public GTFS Sverige 2 historic archive. Count available
service days and actual sourceTripIds per agency. Do not fabricate any train,
do not deploy, and never mistake broad national GTFS for Stockholm map scope.
"""
import collections,datetime as dt,json,unicodedata,sys
from pathlib import Path
sys.path.insert(0,'scripts')
from build_rail_keyless import fetch_archive,records,service_calendar,SOURCE_START

def norm(s):
 return unicodedata.normalize('NFKC',str(s or '')).casefold().strip()
def group(agency,line):
 a=norm(agency);r=norm(line)
 if a=='sj':return 'SJ'
 if 'arlanda express' in a:return 'Arlanda Express'
 if 'mälartåg' in a or 'mälardalstrafik' in a:return 'Mälartåg'
 if 'snälltåget' in a:return 'Snälltåget'
 if 'tågab' in a or 'tågaktiebolaget' in a:return 'Tågab'
 if 'vy tåg' in a or a in ('vy','vy tåg ab'):return 'Vy Tåg'
 if 'rdc' in a and 'euro' in a:return 'RDC EuroNight'
 if 'vr snabb' in a or 'mtrx' in a or a=='vr':return 'VR Snabbtåg'
 return None

def main():
 ds=[SOURCE_START+dt.timedelta(days=i) for i in range(7)]
 current=json.loads(Path('website/data/rail.json').read_text(encoding='utf8'))
 groups=['Arlanda Express','SJ','Mälartåg','VR Snabbtåg','Snälltåget','Vy Tåg','Tågab','RDC EuroNight']
 currentBy=collections.defaultdict(list)
 for t in current['trips']:
  if t.get('agency') in groups:currentBy[t['agency']].append(t)
 print('CURRENT STABLE29 NATIONAL TEMPLATES',dict((k,len(v)) for k,v in currentBy.items()),flush=True)
 with fetch_archive() as z:
  valid=service_calendar(z,ds)
  agencyMap={r.get('agency_id'):r.get('agency_name','') for r in records(z,'agency.txt')}
  routes={}
  for route in records(z,'routes.txt'):
   agency=agencyMap.get(route.get('agency_id'),'')
   name=group(agency,route.get('route_short_name'))
   if name is not None and route.get('route_type','') in {'2','100','101','102','103','106','109'}:
    routes[route['route_id']]=(name,agency,route.get('route_short_name'),route.get('route_long_name'))
  counts=collections.Counter();routeNames=collections.defaultdict(collections.Counter)
  sourceIds=collections.defaultdict(set)
  daysByGroup=collections.defaultdict(lambda:collections.defaultdict(set))
  validByService=collections.defaultdict(set)
  for d,services in valid.items():
   for service in services:validByService[service].add(d.isoformat())
  for row in records(z,'trips.txt'):
   route=routes.get(row.get('route_id'))
   if not route:continue
   name=route[0];sid=row.get('service_id')
   for day in validByService.get(sid,[]):
    counts[(name,day)]+=1
    daysByGroup[name][day].add(row.get('trip_id'))
   sourceIds[name].add(row.get('trip_id'))
   routeNames[name][(route[1],route[2],route[3])]+=1
  report={}
  for name in groups:
   templates=currentBy.get(name,[])
   covered={t.get('sourceTripId') for t in templates if t.get('sourceTripId')}
   historic=sourceIds[name]
   sourceWeek={day.isoformat():counts[(name,day.isoformat())] for day in ds}
   report[name]={
    'sourceGTFSWeekCounts':sourceWeek,
    'sourceUniqueIds':len(historic),
    'existingUniqueTripIdsMatched':len(covered&historic),
    'existingTemplates':len(templates),
    'currentlyMatchedSourceCoveragePercent':round(100*len(covered&historic)/len(historic),1) if historic else None,
    'unmatchedTemplateTripIds':sorted(covered-historic)[:20],
    'sourceRouteExamples':[{'agency':k[0],'shortName':k[1],'longName':k[2],'tripCount':v}
      for k,v in routeNames[name].most_common(15)],
    'independentCompleteGTFSAvailable':len(historic)>0,
    'scopeNote':'National agency totals; only trips with verified OSM and map scope can be added.'
   }
   print('NATIONAL REAL GTFS',name,'day totals',sourceWeek,
    'existing source IDs',len(covered&historic),'of',len(historic),
    'source routes',len(routeNames[name]),flush=True)
  Path('_national_audit').mkdir(exist_ok=True)
  Path('_national_audit/agency_gtfs_week_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
  print('NATIONAL GTFS SOURCE READONLY AUDIT COMPLETE – NO NEW SERVICES OR TRACKS CREATED',flush=True)
if __name__=='__main__':main()
