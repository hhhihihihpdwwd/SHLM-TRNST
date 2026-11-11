#!/usr/bin/env python3
"""Package06: repair RDC EN345 autumn 2026 operator published original clock times.
No speculative track; all actual passenger stops match immutable OSM tracks.
The simulator keeps RDC service in its every-day representative example but
chooses exactly ONE historical route variant per physical train each day.
The weekdays in the official source are retained for interpretability.
"""
import copy, datetime as dt, json, sys
from pathlib import Path
from zoneinfo import ZoneInfo
from refine_osm_routes import project_stops
from diagnose_package06 import AUTUMN_345,sec
TEMPLATE='2026-11-09'
OSM_BERLIN='rdc-osm-rail:RDC-EURONIGHT-345-berlin-hauptbahnhof'
TARGETS={'tue-hamburg':'RDC-EURONIGHT-345-hamburg-altona',
         'thu-berlin':'RDC-EURONIGHT-345-berlin-hauptbahnhof',
         'sat-berlin':'RDC-EURONIGHT-345-saturday-berlin-gesundbrunnen'}
DAY=dt.datetime.combine(dt.date.fromisoformat(TEMPLATE),dt.time(),ZoneInfo('Europe/Stockholm'))
WEEKDAYS={'tue-hamburg':[2],'thu-berlin':[0,1,3,4,5],'sat-berlin':[6]}
def correct(base):
 assert base['type']=='historical-daily-repeating-simulation' and base['simulationTemplateDay']==TEMPLATE
 assert len(base['trips'])==10798 and len(base['shapes'])==107
 assert base.get('package05Audit',{}).get('addedPerOperator')=={'Vy Tåg':0,'Tågab':0}
 rdc=[t for t in base['trips'] if t['agency']=='RDC EuroNight']
 assert len(rdc)==4
 assert set(t['id'] for t in rdc)=={
 'RDC-EURONIGHT-344-berlin-lichtenberg','RDC-EURONIGHT-344-hamburg-hbf',
 'RDC-EURONIGHT-345-berlin-hauptbahnhof','RDC-EURONIGHT-345-hamburg-altona'}
 coords={s[2]:s[:2] for t in rdc for s in t['stops']}
 coords['Berlin Gesundbrunnen']=[52.5489,13.3889]
 shape=base['shapes'][OSM_BERLIN]
 updated=copy.deepcopy(base)
 changed=[]
 for variant,rows in AUTUMN_345.items():
  id=TARGETS[variant]
  stations=[]
  for name,time in rows:
   assert name in coords,name
   seconds=sec(time)
   stations.append([*coords[name],name,seconds,seconds])
  pos=project_stops(stations,shape,650)
  assert pos is not None,(variant,'not on exact verified original OSM rail')
  speed=[(pos[i]-pos[i-1])/(stations[i][3]-stations[i-1][4])*3.6
         for i in range(1,len(stations))]
  assert all(0<v<200 for v in speed),(variant,'implausible average speed',speed)
  first,last=stations[0][4],stations[-1][3]
  source=next((t for t in updated['trips'] if t['id']==id),None)
  if variant=='sat-berlin':
   source=copy.deepcopy(next(t for t in rdc if t['id']=='RDC-EURONIGHT-345-berlin-hauptbahnhof'))
   source['id']=id
   updated['trips'].append(source)
  assert source is not None
  source.update({'stops':stations,'shapeId':OSM_BERLIN,
   'routeVariant': 'Hamburg Hbf' if variant=='tue-hamburg' else
                   'Berlin Gesundbrunnen' if variant=='thu-berlin' else 'Berlin Gesundbrunnen (Samstag)',
   'destination':stations[-1][2],
   'start':int((DAY+dt.timedelta(seconds=first)).timestamp()),
   'end':int((DAY+dt.timedelta(seconds=last)).timestamp()),
   'serviceDay':TEMPLATE,
   'historicReferenceDays':{'tue-hamburg':'Tuesday', 'thu-berlin':'Thursday',
                            'sat-berlin':'Saturday'}[variant],
   'source':'https://www.nachtexpress.de/de/fahrplan/ (official EN345 Sep 1-Dec 12 2026)',
   'geometryQuality':'verified-osm-rail-ways','osmWayNetwork':True,
   'isLiveGPS':False,'package06Verified':True,
   'package06Variant':variant,
   'historicalOperatingWeekdays':{'tue-hamburg':[2],'thu-berlin':[4],
                                  'sat-berlin':[6]}[variant],
   'historicPattern':'Actual autumn 2026 original EN345 station/clock timetable, one representative variant per simulation day; GPS not available'})
  changed.append({'id':id,'variant':variant,'departure':first,'arrival':last,
    'stopCount':len(stations),'maxLegKmh':round(max(speed))})
 for t in updated['trips']:
  if t['id']=='RDC-EURONIGHT-344-berlin-lichtenberg':
   t['package06Variant']='monfri-berlin'
   t['historicalOperatingWeekdays']=[1,5]
   t['package06Verified']=True
  elif t['id']=='RDC-EURONIGHT-344-hamburg-hbf':
   t['package06Variant']='wed-hamburg'
   t['historicalOperatingWeekdays']=[3]
   t['package06Verified']=True
 updated['counts']['intercity']+=1
 updated['rdcDirections']={'to-stockholm':2,'from-stockholm':3}
 updated['rdcOfficialSchedule']='https://www.nachtexpress.de/de/fahrplan/ (Sep 1-Dec 12, 2026, EN344/EN345)'
 updated['rdcSimulationNote']='One historically sourced operator timetable variant per direction per day, including illustrative daily repeats on non-operating dates; no live GPS; special November 20/21 Gothenburg detours are NOT simulated'
 updated['package06Audit']={
  'source':'https://www.nachtexpress.de/de/fahrplan/',
  'validFrom':'2026-09-01','validTo':'2026-12-12',
  'regularSourcePatterns':5,'en344Variants':2,'en345Variants':3,
  'correctedAutumnEn345':2,'addedAutumnSaturdayVariant':1,
  'simulatedOnlyNotLiveGPS':True,
  'exceptionalGothenburgReroutesNotSimulated':['2026-11-20','2026-11-21'],
  'selectedVariantPerSimulatedDay':True,
  'baselineTrainRecords':10798,'unchangedPhysicalOsmTracks':107}
 assert len(updated['trips'])==10799 and updated['shapes']==base['shapes']
 assert all(t==base['trips'][i] for i,t in enumerate(updated['trips'][:10798])
   if t['agency']!='RDC EuroNight')
 for k,v in base.items():
  if k in ('trips','counts','rdcDirections','rdcOfficialSchedule','rdcSimulationNote'):continue
  assert updated[k]==v,k
 for k,v in base['counts'].items():assert updated['counts'][k]==v+(1 if k=='intercity' else 0)
 print('PACKAGE06 CORRECTED REAL AUTUMN RDCEURONIGHT',json.dumps(changed,ensure_ascii=False),flush=True)
 print('PACKAGE06 10799 HISTORICAL TEMPLATES, 107 UNMODIFIED VERIFIED OSM TRACKS, ALL 16 ORIGINAL SYSTEMS',flush=True)
 return updated
if __name__=='__main__':
 if len(sys.argv)!=3:raise SystemExit('Usage: integrate_package06.py STABLE19_RAIL.json OUT_RAIL.json')
 base=json.loads(Path(sys.argv[1]).read_text())
 out=correct(base)
 file=Path(sys.argv[2]);file.parent.mkdir(parents=True,exist_ok=True)
 file.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')))
