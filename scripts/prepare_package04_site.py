#!/usr/bin/env python3
"""Package 04 exact public Package03-site overlay; no UI/marker/photo edits."""
import json,sys
from pathlib import Path
from audit_package04_vr import source,reconcile,integrate
def swap(text,a,b,label):
 if text.count(a)!=1:raise ValueError('Unexpected Package03 '+label+' anchor: '+str(text.count(a)))
 return text.replace(a,b)
def main(site,report_path):
 root=Path(site)
 original=json.loads((root/'data/rail.json').read_text())
 verified,report=reconcile(original,source())
 updated=integrate(original,verified,report)
 out=root/'data/rail.json'
 out.write_text(json.dumps(updated,ensure_ascii=False,separators=(',',':')))
 html=root/'index.html'
 html.write_text(swap(html.read_text(),'app.js?v=package03-01',
                      'app.js?v=package04-01','HTML app cache'))
 app=root/'src/app.js'
 app.write_text(swap(app.read_text(),"from './rail-data.js?v=package03-01'",
                     "from './rail-data.js?v=package04-01'",'JS parser cache'))
 parser=root/'src/rail-data.js'
 parser.write_text(swap(parser.read_text(),"TIMETABLE_URL='./data/rail.json?v=package03-01'",
                    "TIMETABLE_URL='./data/rail.json?v=package04-01'",'timetable cache'))
 # Do not claim the full seven-day pattern as active in every actual weekday.
 Path(report_path).parent.mkdir(parents=True,exist_ok=True)
 Path(report_path).write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print('PACKAGE04 WEBSITE CANDIDATE',len(updated['trips']),'VERIFIED TRAINS',
  'ADDED',len(verified),'VR',flush=True)
if __name__=='__main__':
 if len(sys.argv)!=3:raise SystemExit('Usage: prepare_package04_site.py _site report.json')
 main(*sys.argv[1:])
