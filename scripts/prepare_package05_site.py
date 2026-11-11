#!/usr/bin/env python3
"""Package05: publish independently audited source coverage without inventing duplicates.
Protect exact STABLE18 data, map markers, photographs and tracks; append evidence
metadata only and update three browser cache URLs to release the checked version.
"""
import json,sys
from pathlib import Path
def once(s,a,b,label):
 assert s.count(a)==1,(label,'unexpected old-cache marker',s.count(a))
 return s.replace(a,b)
def prepare(site,provenance,reportfile):
 root=Path(site)
 old=json.loads((root/'data/rail.json').read_text())
 cand=json.loads(Path(provenance).read_text())
 report=json.loads(Path(reportfile).read_text())
 assert len(old['trips'])==10798 and len(old['shapes'])==107
 assert cand['trips']==old['trips'] and cand['shapes']==old['shapes']
 assert cand['counts']==old['counts'] and cand['scope']==old['scope']
 assert len(cand['trips'])==10798 and not report['added'] and not report['deferred']
 assert cand['package05Audit']['addedPerOperator']=={'Vy Tåg':0,'Tågab':0}
 ops=report['operatorResults']
 assert ops['Vy Tåg']['uniqueStopClockPatterns']==10
 assert ops['Vy Tåg']['coveredSourcePatterns']==10
 assert ops['Tågab']['uniqueStopClockPatterns']==15
 assert ops['Tågab']['coveredSourcePatterns']==15
 assert ops['Vy Tåg']['publishedTemplatesBefore']==10
 assert ops['Tågab']['publishedTemplatesBefore']==16
 assert cand['package05Audit']['deferredCount']==0
 for k,v in old.items():assert cand[k]==v,k
 assert set(cand)==set(old)|{'package05Audit'}
 (root/'data/rail.json').write_text(json.dumps(cand,ensure_ascii=False,separators=(',',':')))
 html=root/'index.html';html.write_text(once(html.read_text(),
     'app.js?v=package04-01','app.js?v=package05-01','HTML browser cache'))
 app=root/'src/app.js';app.write_text(once(app.read_text(),
     "from './rail-data.js?v=package04-01'","from './rail-data.js?v=package05-01'",'JS timetable import'))
 parser=root/'src/rail-data.js';parser.write_text(once(parser.read_text(),
     "TIMETABLE_URL='./data/rail.json?v=package04-01'",
     "TIMETABLE_URL='./data/rail.json?v=package05-01'",'dataset version'))
 print('PACKAGE05 COMPLETE COVERAGE ON NEW SITE',
       '10/10 VY UNIQUE SOURCE PATTERNS',
       '15/15 TÅGAB UNIQUE SOURCE PATTERNS',
       'NO UNKNOWN TRAIN ADDED',
       '10798 TRAIN RECORDS AND ALL 107 OSM GEOMETRIES PRESERVED',
       flush=True)
if __name__=='__main__':
 if len(sys.argv)!=4:raise SystemExit('Usage: prepare_package05_site.py SITE_DIR AUDITED_CANDIDATE.json REPORT.json')
 prepare(*sys.argv[1:])
