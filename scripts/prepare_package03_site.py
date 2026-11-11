#!/usr/bin/env python3
"""Materialize a fully reversible package-03 release from the exact archived site."""
import json,sys
from pathlib import Path
from integrate_package03 import integrate
def once(value,a,b,kind):
 assert value.count(a)==1,(kind,'unexpected source cache marker',value.count(a))
 return value.replace(a,b)
def run(site,sj,vr):
 root=Path(site)
 original=json.loads((root/'data/rail.json').read_text())
 updated=integrate(original,json.loads(Path(sj).read_text()),json.loads(Path(vr).read_text()))
 (root/'data/rail.json').write_text(json.dumps(updated,ensure_ascii=False,separators=(',',':')))
 html=root/'index.html'
 html.write_text(once(html.read_text(),'app.js?v=intl-four-01','app.js?v=package03-01','HTML'))
 app=root/'src/app.js'
 app.write_text(once(app.read_text(),"from './rail-data.js?v=intl-four-01'",
                  "from './rail-data.js?v=package03-01'",'app'))
 adapter=root/'src/rail-data.js'
 adapter.write_text(once(adapter.read_text(),"TIMETABLE_URL='./data/rail.json?v=intl-four-01'",
                  "TIMETABLE_URL='./data/rail.json?v=package03-01'",'adapter'))
 print('PACKAGE 03 PUBLIC CANDIDATE READY',len(updated['trips']),'TRIPS',len(updated['shapes']),'SHAPES')
if __name__=='__main__':
 if len(sys.argv)!=4:raise SystemExit('Usage: prepare_package03_site.py SITE_DIR SJ_SOURCE.json VR_SOURCE.json')
 run(*sys.argv[1:])
