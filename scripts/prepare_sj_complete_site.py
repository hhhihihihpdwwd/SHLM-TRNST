#!/usr/bin/env python3
"""Atomic SJ ALL NETWORK overlay. No filter, color, marker, CSS, photo, map,
or original timetable changed. Only appended verified trains, a strict parser
scope check, and cache-busted JS imports inside exact STABLE13 release.
"""
from pathlib import Path
import json,sys
import append_sj_complete

def prepare(source,site,coverage,verified):
 source,site=Path(source),Path(site)
 base=json.loads((site/'data/rail.json').read_text())
 assert len(base['trips'])==10437 and len(base['shapes'])==71
 assert base['scope'].endswith('-vr-snalltaget-vy-tagab-rdc')
 report=json.loads(Path(coverage).read_text())
 osm=json.loads(Path(verified).read_text())
 new=append_sj_complete.integrate(base,report,osm)
 (site/'data/rail.json').write_text(json.dumps(new,ensure_ascii=False,separators=(',',':')))
 # The exact released HTML and JS stay intact except for the versioned URL
 # needed to force browsers to load the verified newly added SJ timetable.
 html=site/'index.html';h=html.read_text()
 assert h.count('app.js?v=rdc-01')==1
 html.write_text(h.replace('app.js?v=rdc-01','app.js?v=sj-complete-01'))
 app=site/'src/app.js';a=app.read_text()
 assert a.count("from './rail-data.js?v=rdc-01'")==1
 app.write_text(a.replace("from './rail-data.js?v=rdc-01'","from './rail-data.js?v=sj-complete-01'"))
 parser=source/'src/rail-data.js';p=parser.read_text()
 assert "TIMETABLE_URL='./data/rail.json?v=vy-01'" in p
 p=p.replace("TIMETABLE_URL='./data/rail.json?v=vy-01'",
             "TIMETABLE_URL='./data/rail.json?v=sj-complete-01'")
 (site/'src/rail-data.js').write_text(p)
 print('SJ COMPLETE ATOMIC SITE OVERLAY: 16 EXISTING OPERATORS PLUS SJ NETWORK DEPTH,',
       len(new['trips']),'HISTORIC TRAINS',len(new['shapes']),'REAL GEOMETRIES',flush=True)

if __name__=='__main__':
 if len(sys.argv)!=5:raise SystemExit('Usage: prepare_sj_complete_site.py SOURCE_DIR RELEASE_DIR COVERAGE.json OSM.json')
 prepare(*sys.argv[1:])
