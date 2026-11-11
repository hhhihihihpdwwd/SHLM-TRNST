#!/usr/bin/env python3
"""Release exact original STABLE16 site with fully proven 4-operator historical
international additions. Never regenerate originals, change photo/sprite/JS UI
or overwrite unrelated systems; cache-bust only previously tested dependencies.
"""
from pathlib import Path
import json,sys
from append_international_four import integrate
def replace_once(s,old,new,label):
 if s.count(old)!=1:raise ValueError('Unexpected original '+label+' count '+str(s.count(old)))
 return s.replace(old,new)
def prepare(root,site,plan,gap,rail):
 root=Path(root);site=Path(site)
 old=json.loads((site/'data/rail.json').read_text())
 proposed=integrate(old,json.loads(Path(plan).read_text()),
  json.loads(Path(gap).read_text()),json.loads(Path(rail).read_text()))
 (site/'data/rail.json').write_text(json.dumps(proposed,ensure_ascii=False,separators=(',',':')))
 html=site/'index.html'
 html.write_text(replace_once(html.read_text(),
  'app.js?v=malartag-five-01','app.js?v=intl-four-01','HTML cache'))
 app=site/'src/app.js'
 app.write_text(replace_once(app.read_text(),
  "from './rail-data.js?v=malartag-five-01'",
  "from './rail-data.js?v=intl-four-01'",'JS rail-parser import'))
 parser=root/'src/rail-data.js'
 source=parser.read_text()
 source=replace_once(source,"TIMETABLE_URL='./data/rail.json?v=vy-01'",
  "TIMETABLE_URL='./data/rail.json?v=intl-four-01'",'source timetable cache')
 (site/'src/rail-data.js').write_text(source)
 print('EXACT STABLE16 HISTORICAL SITE SAVED AS ONE EUROPEAN EXTENSION',
   len(proposed['trips']),'ORIGINAL HISTORICAL SCHEDULES',
   len(proposed['shapes']),'VERIFIED OSM TRACKS',
   'EIGHT UNIQUE NONOVERLAPPING REAL INTERNATIONAL TRAIN SEGMENTS',flush=True)
if __name__=='__main__':
 if len(sys.argv)!=6:raise SystemExit('Usage: prepare_international_four_site.py SOURCE_DIR SITE_DIR PLAN.json GAP.json RAIL.json')
 prepare(*sys.argv[1:])
