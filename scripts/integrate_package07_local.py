#!/usr/bin/env python3
"""Package07: add only independently authentic missing historical return services,
and only if their original complete stopping pattern follows a verified OSM track.

Source evidence: the exact historical SL GTFS source-trip IDs and audited missing
endpoint pairs; no train, waypoint or station is synthesized. Historical source
weekdays are preserved even though existing site repeats illustrative timetable
daily. Every one of the 10,799 previous records and all OSM geometry stay intact.
"""
import collections,copy,datetime as dt,json,sys
from pathlib import Path
from zoneinfo import ZoneInfo
import build_rail_keyless as gtfs
from refine_osm_routes import project_stops
TEMPLATE='2026-11-09'
REFDAYS=[dt.date(2026,11,4)+dt.timedelta(days=i) for i in range(7)]
ZERO=dt.datetime.combine(dt.date.fromisoformat(TEMPLATE),dt.time(),ZoneInfo('Europe/Stockholm'))
def norm(s):return (s or '').casefold().strip()
def fingerprint(stops):
 return (tuple(s[2] for s in stops),stops[0][4],stops[-1][3])
def main(baseline,source_audit,out_path,report_path):
 data=json.loads(Path(baseline).read_text())
 evidence=json.loads(Path(source_audit).read_text())
 assert data['type']=='historical-daily-repeating-simulation'
 assert data['simulationTemplateDay']==TEMPLATE and len(data['trips'])==10799 and len(data['shapes'])==107
 missed=[x for x in evidence['reverseChecks'] if x['classification']=='real_historic_reverse_missing_from_published_snapshot']
 assert len(missed)==6,'Historic archived source gap census changed'
 targets={(x['line'],*x['unpublishedReverse'].split(' → ')):x for x in missed}
 targetlines={x[0] for x in targets}
 assert targetlines=={'40','41','43','13','17','19'}
 with gtfs.fetch_archive() as z:
  calendar=gtfs.service_calendar(z,REFDAYS);valid=set().union(*calendar.values())
  agencies={x.get('agency_id'):x.get('agency_name','') for x in gtfs.records(z,'agency.txt')}
  routes={x['route_id']:x for x in gtfs.records(z,'routes.txt')
          if x.get('route_short_name','').strip() in targetlines and
             ('sl' in norm(agencies.get(x.get('agency_id'),'')) or
              'stockholms' in norm(agencies.get(x.get('agency_id'),'')))}
  trips={x['trip_id']:x for x in gtfs.records(z,'trips.txt')
         if x.get('route_id') in routes and x.get('service_id') in valid}
  stations={}
  for x in gtfs.records(z,'stops.txt'):
   try:lat,lon=float(x['stop_lat']),float(x['stop_lon'])
   except (KeyError,TypeError,ValueError):continue
   if 57<lat<62 and 16<lon<20:
    stations[x['stop_id']]=[round(lat,6),round(lon,6),x.get('stop_name','')]
  times=collections.defaultdict(list)
  for x in gtfs.records(z,'stop_times.txt'):
   tid=x.get('trip_id')
   if tid not in trips:continue
   p=stations.get(x.get('stop_id'))
   if not p or not p[2]:continue
   a=gtfs.clock(x.get('arrival_time'));d=gtfs.clock(x.get('departure_time'))
   if a is None and d is None:continue
   try:i=int(x['stop_sequence'])
   except (ValueError,KeyError):continue
   times[tid].append((i,p,a if a is not None else d,d if d is not None else a))
  candidates=collections.defaultdict(list)
  for tid,raw in times.items():
   raw.sort(key=lambda r:r[0])
   if len(raw)<2:continue
   stops=[[x[1][0],x[1][1],x[1][2],x[2],x[3]] for x in raw]
   line=routes[trips[tid]['route_id']].get('route_short_name','').strip()
   key=(line,stops[0][2],stops[-1][2])
   if key not in targets or stops[-1][3]<=stops[0][4]:continue
   sourceDays=[str(day) for day in REFDAYS if trips[tid]['service_id'] in calendar[day]]
   if not sourceDays:continue
   candidates[key].append({'sourceId':tid,'line':line,'stops':stops,'sourceDays':sourceDays,
    'departure':stops[0][4],'arrival':stops[-1][3]})
 assert set(candidates)==set(targets),'Some authenticated return direction entirely missing source'
 report={'sourceArchive':gtfs.URL,'referenceDates':list(map(str,REFDAYS)),
  'baselineTemplates':10799,'baselineOsmShapes':107,
  'authenticMissingReturnDirections':6,
  'newVerifiedTrips':[],'deferredTrips':[],
  'directionResults':{},'method':'Direct original GTFS source trip with original clock and stop sequence, verifiable immutable connected OSM path, no source-free reverse train'}
 result=copy.deepcopy(data)
 originalPatterns=collections.defaultdict(set)
 originalByline=collections.defaultdict(list)
 for t in data['trips']:
  originalPatterns[str(t.get('line'))].add(fingerprint(t['stops']))
  originalByline[str(t.get('line'))].append(t)
 for key,rows in sorted(candidates.items()):
  line,origin,dest=key
  # Preserve one historic reference day per specific return pattern: the actual
  # available original day with the most source trips, preferring reference Friday.
  days=collections.Counter(d for row in rows for d in row['sourceDays'])
  ref=sorted(days,key=lambda d:(-days[d],0 if d=='2026-11-06' else 1,d))[0]
  group=[r for r in rows if ref in r['sourceDays']]
  by_pattern={}
  for row in sorted(group,key=lambda r:(r['departure'],r['sourceId'])):
   by_pattern.setdefault(fingerprint(row['stops']),row)
  accepted=[];deferred=[]
  existing=originalByline[line]
  for fp,row in by_pattern.items():
   if fp in originalPatterns[line]:continue
   overlap=[t for t in existing if t['stops'][0][2]==origin and
      t['stops'][-1][2]==dest and abs(t['stops'][0][4]-row['departure'])<90]
   if overlap:
    deferred.append((row,'almost-identical prior physical departure'));continue
   matched=[]
   for sid in {t['shapeId'] for t in existing if t['geometryQuality']=='verified-osm-relation'}:
    shape=result['shapes'][sid]
    if not isinstance(shape,list) or len(shape)<20:continue
    positions=project_stops(row['stops'],shape,650)
    if positions is None:continue
    speeds=[]
    for i in range(1,len(positions)):
     sec=row['stops'][i][3]-row['stops'][i-1][4]
     speeds.append((positions[i]-positions[i-1])/sec*3.6 if sec>0 else -1)
    if speeds and all(0<k<('200'=='commuter' and 200 or 160) for k in speeds):
     matched.append((sid,max(speeds)))
   if not matched:
    deferred.append((row,'full ordered source stops do not fit original proven OSM shape'));continue
   matched.sort(key=lambda z:z[1]);sid,mx=matched[0]
   sample=next(t for t in existing if t['shapeId']==sid)
   new=copy.deepcopy(sample)
   new.update({'id':'SL-PACKAGE07:'+row['sourceId']+':'+TEMPLATE,
    'sourceTripId':row['sourceId'],'sourceAgency':sample['agency'],
    'line':line,'stops':row['stops'],'shapeId':sid,
    'destination':dest,'serviceDay':TEMPLATE,
    'start':int((ZERO+dt.timedelta(seconds=row['departure'])).timestamp()),
    'end':int((ZERO+dt.timedelta(seconds=row['arrival'])).timestamp()),
    'geometryQuality':'verified-osm-relation','isLiveGPS':False,
    'archiveDay':ref,'sourceDays':row['sourceDays'],
    'source':'GTFS Sverige 2 Sweden 2026-11-04 original SL source train',
    'historicPattern':'Source original SL historical journey, daily repeated for illustrative simulation',
    'package07Verified':True})
   new['direction']='from-stockholm' if origin.startswith('Stockholm') else 'to-stockholm' if dest.startswith('Stockholm') else sample.get('direction')
   assert not any(t['id']==new['id'] for t in result['trips'])
   result['trips'].append(new)
   result['counts'][new['mode']]+=1
   originalPatterns[line].add(fp)
   existing.append(new)
   accepted.append((row,sid,round(mx)))
  report['directionResults'][' | '.join(key)]={'originalSourceDay':ref,
    'originalSourceTripCandidates':len(rows),'uniqueReferenceDayPatterns':len(by_pattern),
    'addedVerifiedJourneys':len(accepted),'deferred':len(deferred)}
  for row,sid,mx in accepted:
   report['newVerifiedTrips'].append({'line':line,'id':row['sourceId'],
     'from':origin,'to':dest,'sourceDay':ref,'departureSeconds':row['departure'],
     'arrivalSeconds':row['arrival'],'stopNames':[s[2] for s in row['stops']],
     'verifiedExistingOsmShape':sid,'maxKmh':mx})
  for row,reason in deferred:
   report['deferredTrips'].append({'line':line,'sourceId':row['sourceId'],
      'from':origin,'to':dest,'reason':reason})
  print('PACKAGE07 ORIGINAL SOURCE REVERSE',line,origin,'→',dest,
   'ARCHIVE SERVICE DAY',ref,'VERIFIED NEW JOURNEYS',len(accepted),
   'OSM-DEFERRED',len(deferred),flush=True)
 total=len(report['newVerifiedTrips'])
 result['package07Audit']={'referenceArchive':'GTFS Sverige 2 sweden-20261104.zip',
   'verifiedAdditionalShortTurnReturnJourneys':total,
   'missingReversePairsSeenInSource':6,
   'originalTrainTemplates':10799,
   'originalOsmShapes':107,
   'deferredJourneysWithoutConnectedOsm':len(report['deferredTrips']),
   'historicalNotLive':True}
 assert result['trips'][:10799]==data['trips'] and result['shapes']==data['shapes']
 assert len(result['trips'])==10799+total and total>0
 for k,v in data.items():
  if k in ('trips','counts'):continue
  assert result[k]==v,k
 assert len({t['id'] for t in result['trips']})==len(result['trips'])
 for k,v in data['counts'].items():
  delta=sum(t['mode']==k for t in result['trips'][10799:])
  assert result['counts'][k]==v+delta,(k,v,delta,result['counts'][k])
 for p,v in [(out_path,result),(report_path,report)]:
  f=Path(p);f.parent.mkdir(parents=True,exist_ok=True)
  f.write_text(json.dumps(v,ensure_ascii=False,separators=(',',':') if p==out_path else None,indent=None if p==out_path else 2))
 print('PACKAGE07 IMPORT RESULTS',total,'VERIFIED NEW HISTORIC SL RETURN JOURNEYS',
   'DEFERRED',len(report['deferredTrips']),'TOTAL',len(result['trips']),'OSM SHAPES',len(result['shapes']),flush=True)
if __name__=='__main__':
 if len(sys.argv)!=5:raise SystemExit('Usage: integrate_package07_local.py BASE.json SOURCE_AUDIT.json OUTPUT.json REPORT.json')
 main(*sys.argv[1:])
