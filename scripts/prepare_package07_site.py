#!/usr/bin/env python3
"""Prepare precise STABLE20 -> Package07 local-rail final release overlay.

All prior website photos, source files, markers and rail shapes stay unchanged.
Only add the independently authenticated 28 historical GTFS local return trains,
plus documented evidence and browser cache bust to make them visible on public site.
"""
import json,sys
from pathlib import Path
def once(t,old,new,kind):
 assert t.count(old)==1,(kind,t.count(old))
 return t.replace(old,new)
def prepare(site,new_data,source_report):
 root=Path(site)
 existing=json.loads((root/'data/rail.json').read_text())
 updated=json.loads(Path(new_data).read_text())
 report=json.loads(Path(source_report).read_text())
 assert len(existing['trips'])==10799 and len(updated['trips'])==10827
 assert len(existing['shapes'])==len(updated['shapes'])==107
 assert existing['trips']==updated['trips'][:10799]
 assert existing['shapes']==updated['shapes']
 assert updated['package07Audit']['verifiedAdditionalShortTurnReturnJourneys']==28
 assert updated['package07Audit']['deferredJourneysWithoutConnectedOsm']==0
 assert len(report['newVerifiedTrips'])==28 and not report['deferredTrips']
 for k,v in existing.items():
  if k in ('trips','counts'):continue
  assert updated[k]==v,k
 for k,v in existing['counts'].items():
  assert updated['counts'][k]==v+sum(t['mode']==k for t in updated['trips'][10799:]),k
 (root/'data/rail.json').write_text(json.dumps(updated,ensure_ascii=False,separators=(',',':')))
 html=root/'index.html'
 html.write_text(once(html.read_text(),'app.js?v=package06-01',
                      'app.js?v=package07-01','HTML entry point'))
 app=root/'src/app.js'
 app.write_text(once(app.read_text(),"from './rail-data.js?v=package06-01'",
                    "from './rail-data.js?v=package07-01'",'JS dataset parser import'))
 parser=root/'src/rail-data.js'
 parser.write_text(once(parser.read_text(),"TIMETABLE_URL='./data/rail.json?v=package06-01'",
                    "TIMETABLE_URL='./data/rail.json?v=package07-01'",'timetable JSON browser cache'))
 print('STABLE21 WEBSITE CANDIDATE PREPARED',len(updated['trips']),
       'AUTHENTIC TRAIN TEMPLATES',len(updated['shapes']),
       'UNCHANGED REAL OSM TRACKS, 28 GENUINE MISSING SL RETURN JOURNEYS',flush=True)
if __name__=='__main__':
 if len(sys.argv)!=4:raise SystemExit('Usage: prepare_package07_site.py SITE_ROOT AUTHENTIC_NEW_DATA.json SOURCE_REPORT.json')
 prepare(*sys.argv[1:])
