#!/usr/bin/env python3
"""VR Package 04: full source-authorised seven-day train pattern census.
Never confuse distinct service calendar variants with additional simultaneous
physical trains. Only publish genuinely new station/time paths fitting immutable
verified physical OSM rails and physically plausible speeds.
"""
import collections,copy,datetime as dt,json,sys
from pathlib import Path
from zoneinfo import ZoneInfo
import build_rail_keyless as gtfs
from refine_osm_routes import project_stops
OP='VR Snabbtåg'
DATES=[dt.date(2026,11,4)+dt.timedelta(days=i) for i in range(7)]
RAIL={'2','100','101','102','103','106','109'}
ZERO=dt.datetime.combine(dt.date(2026,11,9),dt.time(),ZoneInfo('Europe/Stockholm'))
def canonical(s):return (s or '').strip().casefold()
def station_ok(s):return 'stockholm central' in canonical(s) or 'göteborg central' in canonical(s)
def source():
 with gtfs.fetch_archive() as z:
  calendar=gtfs.service_calendar(z,DATES)
  agency={r.get('agency_id'):r.get('agency_name','') for r in gtfs.records(z,'agency.txt')}
  agency_ids={i for i,n in agency.items() if canonical(n)==canonical(OP)}
  assert agency_ids,'GTFS archive contains no explicit VR agency'
  routes={r['route_id']:r for r in gtfs.records(z,'routes.txt')
          if r.get('agency_id') in agency_ids and r.get('route_type') in RAIL}
  active_ids=set().union(*calendar.values())
  trips={r['trip_id']:r for r in gtfs.records(z,'trips.txt')
         if r.get('route_id') in routes and r.get('service_id') in active_ids}
  stations={}
  for r in gtfs.records(z,'stops.txt'):
   try:lat,lon=float(r['stop_lat']),float(r['stop_lon'])
   except (ValueError,KeyError,TypeError):continue
   if 55<lat<65 and 10<lon<25:stations[r['stop_id']]=[round(lat,6),round(lon,6),r.get('stop_name','')]
  times=collections.defaultdict(list)
  for r in gtfs.records(z,'stop_times.txt'):
   tid=r.get('trip_id')
   if tid not in trips:continue
   stop=stations.get(r.get('stop_id'))
   if not stop or not stop[2]:continue
   a=gtfs.clock(r.get('arrival_time'));d=gtfs.clock(r.get('departure_time'))
   if a is None and d is None:continue
   try:index=int(r['stop_sequence'])
   except (ValueError,KeyError):continue
   times[tid].append((index,stop,a if a is not None else d,d if d is not None else a))
  result=[]
  for tid,seq in times.items():
   seq.sort(key=lambda s:s[0])
   if len(seq)<2:continue
   stops=[[x[1][0],x[1][1],x[1][2],x[2],x[3]] for x in seq]
   if not station_ok(stops[0][2]) and not station_ok(stops[-1][2]):continue
   if stops[-1][3]<=stops[0][4]:continue
   day=[str(d) for d in DATES if trips[tid]['service_id'] in calendar[d]]
   if not day:continue
   result.append({'id':tid,'days':day,'stops':stops,
      'origin':stops[0][2],'destination':stops[-1][2],
      'route':routes[trips[tid]['route_id']].get('route_short_name',''),
      'first':stops[0][4],'last':stops[-1][3]})
  assert result,'No original VR journeys from GTFS'
  return result
def fingerprint(stops):
 return (tuple(s[2] for s in stops),stops[0][4],stops[-1][3])
def reconcile(base,source_rows):
 assert base['type']=='historical-daily-repeating-simulation'
 assert base['simulationTemplateDay']=='2026-11-09'
 assert len(base['trips'])==10789 and len(base['shapes'])==107
 known=[x for x in base['trips'] if x['agency']==OP]
 ids={str(t.get('sourceTripId')) for t in known}
 ids|={str(t['id']).split(':')[1] for t in known if str(t['id']).startswith('VR-ARCHIVE:')}
 fp={fingerprint(t['stops']) for t in known}
 # Source trip variants with exactly identical clock and station pattern refer
 # to the same physical train. Alternate station itineraries at the same clock
 # are not silently appended as duplicate simultaneous trains.
 groups=collections.defaultdict(list)
 for row in source_rows:groups[fingerprint(row['stops'])].append(row)
 verified=[];unmatched=[];already=[];conflicts=[]
 for key,variants in sorted(groups.items(),key=lambda kv:(kv[0][1],kv[0][2],str(kv[0][0]))):
  row=next((v for v in variants if '2026-11-06' in v['days']),variants[0])
  if key in fp or any(v['id'] in ids for v in variants):
   already.append(row);continue
  if not (station_ok(row['origin']) and station_ok(row['destination'])):
   unmatched.append((row,'short-run requires separate corridor assessment'));continue
  first,last=row['first'],row['last']
  overlap=[t for t in known if t['stops'][0][2]==row['origin'] and
    abs(t['stops'][0][4]-first)<8*60 and t['stops'][-1][2]==row['destination']]
  if overlap:
   conflicts.append((row,','.join(t['id'] for t in overlap[:2])));continue
  matches=[]
  for sid,shape in base['shapes'].items():
   if not isinstance(shape,list) or len(shape)<25:continue
   pos=project_stops(row['stops'],shape,650)
   if pos is None:continue
   speeds=[]
   for i in range(1,len(pos)):
    travel=row['stops'][i][3]-row['stops'][i-1][4]
    speeds.append((pos[i]-pos[i-1])/travel*3.6 if travel>0 else -1)
   if all(0<k<210 for k in speeds):
    matches.append((sid,pos,max(speeds)))
  if not matches:
   unmatched.append((row,'no verified OSM complete corridor with plausible speed'));continue
  matches.sort(key=lambda m:(0 if m[0].startswith('vr-osm-rail-ways') else 1,m[2]))
  sid=matches[0][0]
  verified.append((row,sid,variants))
 report={'sourceDates':list(map(str,DATES)),'sourceTripIds':len(source_rows),
 'uniqueSourceStopClockPatterns':len(groups),'publishedVRTripTemplates':len(known),
 'previouslyCoveredPatterns':len(already),'newValidSourcePatterns':len(verified),
 'shortOrUnmatched':len(unmatched),'possiblePhysicalDuplicates':len(conflicts),
 'publishedByDirection':dict(collections.Counter('from-stockholm' if x['stops'][0][2].startswith('Stockholm') else 'to-stockholm' for x in known)),
 'sourceDayCounts':{str(d):sum(str(d) in x['days'] for x in source_rows) for d in DATES},
 'newDetails':[{'sourceId':r['id'],'origin':r['origin'],'destination':r['destination'],
     'departure':r['first'],'arrival':r['last'],'stops':len(r['stops']),
     'verifiedOSM':sid,'sourceDays':r['days']} for r,sid,_ in verified],
 'unmatchedDetails':[{'sourceId':r['id'],'origin':r['origin'],'destination':r['destination'],
    'departure':r['first'],'reason':why} for r,why in unmatched],
 'conflictDetails':[{'sourceId':r['id'],'departure':r['first'],
    'reason':why} for r,why in conflicts],
 'limitations':['Historical November 2026 GTFS snapshot; not live GPS',
 'Distinct weekday patterns are not necessarily extra simultaneous trains',
 'Unmatched or short services are NOT represented as fabricated tracks']}
 return verified,report
def integrate(base,verified,report):
 out=copy.deepcopy(base)
 for row,sid,variants in verified:
  identifier='VR-PACKAGE04:'+row['id']+':2026-11-09'
  assert all(t['id']!=identifier for t in out['trips'])
  stops=row['stops']
  out['trips'].append({'id':identifier,'agency':OP,'sourceAgency':OP,'sourceTripId':row['id'],
   'mode':'intercity','line':'VR','train':row['route'] or 'VR',
   'destination':row['destination'],
   'direction':'from-stockholm' if station_ok(row['origin']) and row['origin'].startswith('Stockholm') else 'to-stockholm',
   'serviceDay':'2026-11-09','start':int((ZERO+dt.timedelta(seconds=row['first'])).timestamp()),
   'end':int((ZERO+dt.timedelta(seconds=row['last'])).timestamp()),
   'stops':stops,'shapeId':sid,
   'geometryQuality':'verified-osm-rail-ways' if not sid.startswith('sj-osm:') else 'verified-osm-relation',
   'isLiveGPS':False,'sourceDays':sorted(set(d for v in variants for d in v['days'])),
   'source':'GTFS Sverige 2, authentic VR Snabbtåg November 2026 service calendar',
   'vehicleModel':'VR Snabbtåg (specific consist unverified)',
   'vehiclePhotoStatus':'licensed-illustrative-example',
   'package04Verified':True,
   'historicPattern':'Source-verified November 2026 service variant, repeated daily for historical simulation'})
 out['counts']['intercity']+=len(verified)
 out['package04Audit']={k:v for k,v in report.items() if not k.endswith('Details')}
 assert out['trips'][:10789]==base['trips'] and out['shapes']==base['shapes']
 for k,v in base.items():
  if k in ('trips','counts'):continue
  assert out[k]==v,k
 for k,v in base['counts'].items():
  assert out['counts'][k]==v+(len(verified) if k=='intercity' else 0)
 return out
def main():
 base=json.loads(Path(sys.argv[1]).read_text())
 rows=source()
 verified,report=reconcile(base,rows)
 out=integrate(base,verified,report)
 Path(sys.argv[2]).parent.mkdir(parents=True,exist_ok=True)
 Path(sys.argv[2]).write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')))
 Path(sys.argv[3]).parent.mkdir(parents=True,exist_ok=True)
 Path(sys.argv[3]).write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print('PACKAGE04 VERIFIED VR CENSUS',json.dumps(report,ensure_ascii=False),flush=True)
 print('PACKAGE04 NEW DATA',len(verified),'TOTAL TRAIN TEMPLATES',len(out['trips']),flush=True)
if __name__=='__main__':
 if len(sys.argv)!=4:raise SystemExit('Usage audit_package04_vr.py ORIGINAL_RAIL OUTPUT_RAIL OUTPUT_REPORT')
 main()
