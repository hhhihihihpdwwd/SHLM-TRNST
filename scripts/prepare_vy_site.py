#!/usr/bin/env python3
"""Apply ONLY Vy additions onto exact STABLE09 deployed Pages files.
Never replace legacy CSS, track geometry or original train photo metadata.
"""
from pathlib import Path
import json, shutil, sys

def create(source,website,gtfs,route):
 source,website=[Path(p) for p in (source,website)]
 if not (website/'index.html').exists():raise ValueError('Not a verified deployed website')
 html=(website/'index.html').read_text()
 old_button='<button data-filter="snalltaget">Snälltåget</button>'
 if html.count(old_button)!=1:raise ValueError('STABLE09 filter anchor missing')
 html=html.replace(old_button,old_button+'<button data-filter="vy">Vy Tåg</button>')
 if 'app.js?v=train-icons-02' not in html or 'style.css?v=train-icons-02' not in html:
  raise ValueError('Unexpected STABLE09 source or CSS version')
 html=html.replace('app.js?v=train-icons-02','app.js?v=vy-01')
 html=html.replace('Snälltåget · 13 system','Vy Tåg · 14 system')
 html=html.replace('STOCKHOLM RAIL · 13 SYSTEM · SJ · MÄLARTÅG · VR · SNÄLLTÅGET',
                   'STOCKHOLM RAIL · 14 SYSTEM · SJ · MÄLARTÅG · VR · SNÄLLTÅGET · VY')
 (website/'index.html').write_text(html)
 for filename in ('app.js','rail-data.js','rail-filter.js','photos.js','vy-marker-sprite.js'):
  out=website/'src'/filename
  text=(source/'src'/filename).read_text()
  if filename=='app.js':
   for module in ('rail-data','rail-filter','photos'):
    before=f"from './{module}.js?v=snalltaget-01'"
    assert before in text,(filename,module)
    text=text.replace(before,f"from './{module}.js?v=vy-01'")
  if filename=='rail-data.js':
   assert "TIMETABLE_URL='./data/rail.json?v=snalltaget-01'" in text
   text=text.replace("TIMETABLE_URL='./data/rail.json?v=snalltaget-01'",
                     "TIMETABLE_URL='./data/rail.json?v=vy-01'")
  if filename=='photos.js':
   assert 'photos/catalog.json?v=snalltaget-01' in text
   text=text.replace('photos/catalog.json?v=snalltaget-01','photos/catalog.json?v=vy-01')
  out.write_text(text)
 import append_vy
 old=json.loads((website/'data/rail.json').read_text())
 cand=json.loads(Path(gtfs).read_text())
 osm=json.loads(Path(route).read_text())
 new=append_vy.integrate(old,cand,osm)
 (website/'data/rail.json').write_text(json.dumps(new,ensure_ascii=False,separators=(',',':')))
 print('EXACT 14-SYSTEM CANDIDATE PREPARED',len(new['trips']),'trips',len(new['shapes']),'shapes')
def main():
 if len(sys.argv)!=5:raise SystemExit('Usage: prepare_vy_site.py SOURCE_DIR WEBSITE_DIR VY_GTFS.json VY_OSM.json')
 create(*sys.argv[1:])
if __name__=='__main__':main()
