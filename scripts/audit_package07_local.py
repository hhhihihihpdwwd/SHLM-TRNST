#!/usr/bin/env python3
"""Package07 immutable full local-rail census.  This is an audit, not an import.

All published historical timetable templates are checked across the existing
Stockholm metropolitan rail network. Every published train's original stops,
termini, directional counterpart, short-turn patterns and OSM geometry are
inventoried. A Friday reference archive is not mistaken for GPS or today's
actual operating schedule. No new journeys or false OSM connectors are created.
"""
import collections,json,sys,math
from pathlib import Path

LINES={
 'commuter':{'40','41','42','43','44','48'},
 'metro':{'10','11','13','14','17','18','19'},
 'tvarbanan':{'30','31'},
 'nockeby':{'12'},
 'lidingo':{'21'},
 'city7':{'7'},
 'roslags':{'27','28','29'},
 'saltsjo':{'25','26'},
 'arlanda':set()
}
def group(t):
 mode=t.get('mode','');line=str(t.get('line') or '').strip()
 agency=str(t.get('agency') or '')
 if mode=='commuter':return 'commuter'
 if mode=='metro':return 'metro'
 if line in ('30','31') or 'tvärban' in agency.casefold():return 'tvarbanan'
 if line=='12':return 'nockeby'
 if line=='21':return 'lidingo'
 if line=='7':return 'city7'
 if line in ('27','28','29') or mode=='localrail':return 'roslags'
 if line in ('25','26') or mode=='saltsjo':return 'saltsjo'
 if mode=='express' or 'arlanda express' in agency.casefold():return 'arlanda'
 return None
def key(t):
 s=t['stops'];return (str(t.get('line')),s[0][2],s[-1][2])
def local(t):
 return group(t) is not None
def main(path,out):
 data=json.loads(Path(path).read_text())
 assert data['type']=='historical-daily-repeating-simulation'
 assert data['simulationTemplateDay']=='2026-11-09'
 assert len(data['trips'])==10799 and len(data['shapes'])==107
 assert len({t['id'] for t in data['trips']})==len(data['trips'])
 assert all(t['shapeId'] in data['shapes'] for t in data['trips'])
 groups=collections.defaultdict(list)
 for t in data['trips']:
  g=group(t)
  if g:groups[g].append(t)
 errors=[];warnings=[];summary={}
 for g in LINES:
  rows=groups[g]
  byline=collections.defaultdict(list)
  for t in rows:byline[str(t.get('line') or '')].append(t)
  expected=LINES[g]
  if not rows:errors.append(('empty_system',g))
  if expected:
   missing=expected-set(byline)
   if missing:warnings.append(('no_published_template_for_line',g,sorted(missing)))
  stats={}
  for line,trips in sorted(byline.items()):
   pairs=collections.Counter((t['stops'][0][2],t['stops'][-1][2]) for t in trips)
   terminals=sorted(set(s for a,b in pairs for s in (a,b)))
   missing_reverse=sorted([(a,b,n) for (a,b),n in pairs.items() if (b,a) not in pairs])
   if missing_reverse:warnings.append(('missing_reverse_physical_origin_destination',g,line,missing_reverse))
   endpoints=collections.Counter()
   for a,b in pairs:endpoints[a]+=1;endpoints[b]+=1
   stats[line]={'tripTemplates':len(trips),'terminalNames':terminals,
     'endpointFamilies':[{'from':a,'to':b,'templates':n} for (a,b),n in pairs.most_common()],
     'missingReverseDirections':[{'from':a,'to':b,'templates':n} for a,b,n in missing_reverse],
     'shortTurnTerminalCount':len(terminals),
     'stopNameCount':len(set(s[2] for t in trips for s in t['stops'])),
     'sourceRealOsmShapes':len(set(t['shapeId'] for t in trips))}
   for t in trips:
    st=t['stops'];id=t['id']
    if len(st)<2:errors.append(('too_few_stops',id));continue
    if t['end']<=t['start']:errors.append(('nonpositive_duration',id))
    if t.get('isLiveGPS') is not False:errors.append(('false_gps_label',id))
    if t.get('geometryQuality') not in ('verified-osm-rail-ways','verified-osm-relation'):
     errors.append(('unverified_track',id,t.get('geometryQuality')))
    if len(data['shapes'].get(t['shapeId'],[]))<2:errors.append(('empty_track',id))
    for i in range(1,len(st)):
     if st[i][3]<st[i-1][4]:errors.append(('station_times_reverse',id,i))
     if st[i][4]<st[i][3]:errors.append(('negative_dwell',id,i))
   # Endpoints not guaranteed to be symmetric in archive, flag not fabricate.
  summary[g]={'trips':len(rows),'lines':stats,'operatorNames':dict(collections.Counter(t['agency'] for t in rows))}
 report={'sourceScope':data['scope'],'referenceDay':'2026-11-09',
   'historicSimulationNotLive':True,'allTrainTemplates':len(data['trips']),
   'physicalTrackShapes':len(data['shapes']),
   'localTrainTemplates':sum(len(x) for x in groups.values()),
   'systems':summary,'structuralErrors':errors,'coverageWarnings':warnings,
   'method':'Source-anchored published local rail timetable templates: exact original stops, termini, reverse pairs, short-turns, source-labelled track geometry; do not fabricate unpublished rides',
   'limitations':['Historical repeating simulation rather than real-time train positioning',
    'Archived local train routes can differ from current construction-day operations',
    'One source sample cannot establish every calendar date or exceptional short-run service']}
 Path(out).parent.mkdir(parents=True,exist_ok=True)
 Path(out).write_text(json.dumps(report,ensure_ascii=False,indent=2))
 for name,info in summary.items():
  print('PACKAGE07 SYSTEM',name,'TEMPLATES',info['trips'],'LINES',
    {k:len(v['endpointFamilies']) for k,v in info['lines'].items()},
    'TERMINI',{k:v['terminalNames'] for k,v in info['lines'].items()},flush=True)
 print('PACKAGE07 STRUCTURAL ERRORS',json.dumps(errors[:20],ensure_ascii=False),'COUNT',len(errors),flush=True)
 print('PACKAGE07 COVERAGE WARNINGS',json.dumps(warnings[:50],ensure_ascii=False),'COUNT',len(warnings),flush=True)
 print('PACKAGE07 SUMMARY',len(data['trips']),len(data['shapes']),
       'local trains',report['localTrainTemplates'],flush=True)
 if errors:raise SystemExit('Fail closed: structural errors in audited local rail')
if __name__=='__main__':
 if len(sys.argv)!=3:raise SystemExit('Usage: audit_package07_local.py PUBLISHED_RAIL.json REPORT.json')
 main(*sys.argv[1:])
