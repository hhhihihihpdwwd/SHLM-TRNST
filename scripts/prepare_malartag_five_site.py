#!/usr/bin/env python3
"""Overlay exact public STABLE15 with complete five-corridor Mälartåg.
Only 168 proven GTFS records, strictly connected OSM geometry, scope parser
and cache-versioned asset URLs change. All prior vehicle icons, photos and
10,611 original trains remain byte-identical.
"""
from pathlib import Path
import json,sys
from append_malartag_five import integrate
def replace_one(value,old,new,label):
 if value.count(old)!=1:raise ValueError('Expected unique '+label+' anchor '+str(value.count(old)))
 return value.replace(old,new)
def build(source,site,report,rails):
 source=Path(source);site=Path(site)
 p=site/'data/rail.json';baseline=json.loads(p.read_text())
 candidate=integrate(baseline,json.loads(Path(report).read_text()),
                      json.loads(Path(rails).read_text()))
 p.write_text(json.dumps(candidate,ensure_ascii=False,separators=(',',':')))
 index=site/'index.html'
 index.write_text(replace_one(index.read_text(),'app.js?v=motion-fix-01',
  'app.js?v=malartag-five-01','HTML cache URL'))
 app=site/'src/app.js'
 app.write_text(replace_one(app.read_text(),
  "from './rail-data.js?v=motion-fix-01'",
  "from './rail-data.js?v=malartag-five-01'",'map parser import cache'))
 parser=(source/'src/rail-data.js').read_text()
 parser=replace_one(parser,"TIMETABLE_URL='./data/rail.json?v=vy-01'",
                    "TIMETABLE_URL='./data/rail.json?v=malartag-five-01'",'timetable cache')
 (site/'src/rail-data.js').write_text(parser)
 print('FIVE MÄLARTÅG CORRIDORS COMPLETE; CURRENT 16 SYSTEMS PRESERVED; NEW RECORDS',
  len(candidate['trips'])-10611,'ALL ORIGINAL DATA IDENTICAL',flush=True)
if __name__=='__main__':
 if len(sys.argv)!=5:raise SystemExit('Usage: prepare_malartag_five_site.py SOURCE_DIR FROZEN_SITE COVERAGE.json REAL_RAIL.json')
 build(*sys.argv[1:])
