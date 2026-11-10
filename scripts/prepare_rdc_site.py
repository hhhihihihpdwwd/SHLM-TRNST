#!/usr/bin/env python3
"""Build RDC EN344/345 as strictly additive patch on exact publicly deployed STABLE12.
Only new filter, app modules, RDC image/marker, four authentic international trains
and their original connected OSM tracks are allowed to change.
"""
from pathlib import Path
import copy,datetime as dt,json,sys
from zoneinfo import ZoneInfo
import append_rdc

def build(source,site,timetable,osm):
 source,site=Path(source),Path(site)
 p=site/'data/rail.json'
 original=json.loads(p.read_text())
 assert original['scope'].endswith('-snalltaget-vy-tagab')
 assert len(original['trips'])==10433 and len(original['shapes'])==67
 html=(site/'index.html').read_text()
 tag='<button data-filter="tagab">Tågab</button>'
 assert html.count(tag)==1
 html=html.replace(tag,tag+'<button data-filter="rdc">RDC EuroNight</button>')
 assert 'app.js?v=tagab-01' in html
 html=html.replace('app.js?v=tagab-01','app.js?v=rdc-01')
 html=html.replace('Tågab · 15 system','RDC EuroNight · 16 system')
 html=html.replace('STOCKHOLM RAIL · 15 SYSTEM · SJ · MÄLARTÅG · VR · SNÄLLTÅGET · VY · TÅGAB',
                   'STOCKHOLM RAIL · 16 SYSTEM · SJ · MÄLARTÅG · VR · SNÄLLTÅGET · VY · TÅGAB · RDC')
 (site/'index.html').write_text(html)
 for filename in ('app.js','rail-data.js','rail-filter.js','photos.js','rdc-marker-sprite.js'):
  text=(source/'src'/filename).read_text()
  if filename=='app.js':
   for module,version in [('rail-data','snalltaget-01'),('rail-filter','vy-01'),('photos','vy-01')]:
    old=f"from './{module}.js?v={version}'"
    assert old in text,filename+module
    text=text.replace(old,f"from './{module}.js?v=rdc-01'")
  if filename=='rail-data.js':
   old="TIMETABLE_URL='./data/rail.json?v=vy-01'"
   assert old in text
   text=text.replace(old,"TIMETABLE_URL='./data/rail.json?v=rdc-01'")
  if filename=='photos.js':
   old="'./photos/catalog.json?v=snalltaget-01'"
   assert old in text
   text=text.replace(old,"'./photos/catalog.json?v=rdc-01'")
  (site/'src'/filename).write_text(text)
 timetable=json.loads(Path(timetable).read_text())
 shape=json.loads(Path(osm).read_text())
 template=original['simulationTemplateDay']
 if timetable['simulationTemplateDay']!=template:
  local=ZoneInfo('Europe/Stockholm')
  def midnight(day):return dt.datetime.combine(dt.date.fromisoformat(day),dt.time(),local).timestamp()
  change=int(midnight(template)-midnight(timetable['simulationTemplateDay']))
  timetable=copy.deepcopy(timetable)
  for t in timetable['trips']:
   t['start']+=change;t['end']+=change;t['serviceDay']=template
  timetable['simulationTemplateDay']=template
 result=append_rdc.integrate(original,timetable,shape)
 p.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')))
 print('RDC EU 16-SYSTEM CANDIDATE BUILT',len(result['trips']),'REAL TRAIN TEMPLATES',len(result['shapes']),'VERIFIED OSM TRACKS')

if __name__=='__main__':
 if len(sys.argv)!=5:raise SystemExit('Usage: prepare_rdc_site.py SOURCE_SITE SITE_ROOT OFFICIAL.json VERIFIED_OSM.json')
 build(*sys.argv[1:])
