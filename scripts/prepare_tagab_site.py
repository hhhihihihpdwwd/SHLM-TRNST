#!/usr/bin/env python3
"""Make an ADDITIVE Tågab candidate from the EXACT deployed STABLE11 website.
Do not modify any original historical trips, geometries, original images or UI CSS.
"""
from __future__ import annotations
from pathlib import Path
import copy,datetime as dt,json,sys
from zoneinfo import ZoneInfo
import append_tagab

def overlay(source,site,gtfs_file,osm_file):
 source,site=Path(source),Path(site)
 current=json.loads((site/'data/rail.json').read_text())
 assert current['scope'].endswith('-vr-snalltaget-vy')
 assert len(current['trips'])==10417 and len(current['shapes'])==63
 h=(site/'index.html').read_text()
 anchor='<button data-filter="vy">Vy Tåg</button>'
 assert h.count(anchor)==1
 h=h.replace(anchor,anchor+'<button data-filter="tagab">Tågab</button>')
 assert 'app.js?v=vy-daily-01' in h
 h=h.replace('app.js?v=vy-daily-01','app.js?v=tagab-01')
 h=h.replace('Vy Tåg · 14 system','Tågab · 15 system')
 h=h.replace('STOCKHOLM RAIL · 14 SYSTEM · SJ · MÄLARTÅG · VR · SNÄLLTÅGET · VY',
             'STOCKHOLM RAIL · 15 SYSTEM · SJ · MÄLARTÅG · VR · SNÄLLTÅGET · VY · TÅGAB')
 (site/'index.html').write_text(h)
 for file in ('app.js','rail-data.js','rail-filter.js','photos.js','tagab-marker-sprite.js'):
  text=(source/'src'/file).read_text()
  if file=='app.js':
   for module,version in [('rail-data','snalltaget-01'),('rail-filter','vy-01'),('photos','vy-01')]:
    old=f"from './{module}.js?v={version}'"
    assert old in text,(file,module,version)
    text=text.replace(old,f"from './{module}.js?v=tagab-01'")
  if file=='rail-data.js':
   old="TIMETABLE_URL='./data/rail.json?v=vy-01'"
   assert old in text
   text=text.replace(old,"TIMETABLE_URL='./data/rail.json?v=tagab-01'")
  if file=='photos.js':
   old="'./photos/catalog.json?v=snalltaget-01'"
   assert old in text
   text=text.replace(old,"'./photos/catalog.json?v=tagab-01'")
  (site/'src'/file).write_text(text)
 cand=json.loads(Path(gtfs_file).read_text())
 osm=json.loads(Path(osm_file).read_text())
 template=current['simulationTemplateDay']
 if cand['referenceDay']!=template:
  local=ZoneInfo('Europe/Stockholm')
  def midnight(day):return dt.datetime.combine(dt.date.fromisoformat(day),dt.time(),local).timestamp()
  change=int(midnight(template)-midnight(cand['referenceDay']))
  cand=copy.deepcopy(cand)
  for t in cand['trips']:
   t['start']+=change;t['end']+=change;t['serviceDay']=template
  cand['referenceDay']=template
  print('TAGAB REAL ARCHIVED CLOCKS RETARGETED TO ORIGINAL SITE',template,flush=True)
 target=append_tagab.integrate(current,cand,osm)
 (site/'data/rail.json').write_text(json.dumps(target,ensure_ascii=False,separators=(',',':')))
 print('BUILT EXACT 15 SYSTEM CANDIDATE',len(target['trips']),'TRIPS',len(target['shapes']),'OSM SHAPES',flush=True)

if __name__=='__main__':
 if len(sys.argv)!=5:raise SystemExit('Usage: prepare_tagab_site.py SOURCE SITE GTFS.json OSM.json')
 overlay(*sys.argv[1:])
