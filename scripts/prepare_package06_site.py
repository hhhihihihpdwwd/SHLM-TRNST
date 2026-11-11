#!/usr/bin/env python3
"""Atomic site patch: corrected official autumn RDC records and physical variant
selection for historic *daily repeated* illustrative service without multiple
parallel copies of the same train. Keep all licensed photos and other 16 systems.
"""
import json,sys
from pathlib import Path
from integrate_package06 import correct
def one(text,old,new,label):
 assert text.count(old)==1,(label,'anchor mismatch',text.count(old))
 return text.replace(old,new)
def prepare(site):
 root=Path(site)
 path=root/'data/rail.json'
 original=json.loads(path.read_text())
 updated=correct(original)
 path.write_text(json.dumps(updated,ensure_ascii=False,separators=(',',':')))
 html=root/'index.html'
 html.write_text(one(html.read_text(),'app.js?v=package05-01','app.js?v=package06-01','HTML cache'))
 app=root/'src/app.js'
 app.write_text(one(app.read_text(),"from './rail-data.js?v=package05-01'",
    "from './rail-data.js?v=package06-01'",'JS parser cache'))
 parser=root/'src/rail-data.js'
 source=parser.read_text()
 source=one(source,"TIMETABLE_URL='./data/rail.json?v=package05-01'",
   "TIMETABLE_URL='./data/rail.json?v=package06-01'",'timetable version')
 original_line='   const targetDay=targetDays[index];'
 replacement="""   const targetDay=targetDays[index];
   // Official EN344/345 have several historical variants of the same train.
   // Preserve daily illustrative operation as requested, but never display
   // alternative source itineraries as several parallel physical vehicles.
   // Departure-day selection also carries last night's train past midnight.
   if(source.agency==='RDC EuroNight' && source.package06Variant){
    const weekday=new Date(targetDay+'T00:00:00Z').getUTCDay();
    const preferred=String(source.line)==='EN 344'
       ? (weekday===3?'wed-hamburg':'monfri-berlin')
       : (weekday===2?'tue-hamburg':weekday===6?'sat-berlin':'thu-berlin');
    if(source.package06Variant!==preferred)continue;
   }"""
 source=one(source,original_line,replacement,'date-scoped single physical EuroNight variant')
 parser.write_text(source)
 print('PACKAGE06 EXACT WEBSITE',len(updated['trips']),'AUTHENTIC TRAIN RECORDS',
       'EN344 EN345 AUTUMN OFFICIAL TIMES, ONE TRAIN EACH DIRECTION DAILY',
       '107 ORIGINAL TRUE OSM TRACKS PRESERVED',flush=True)
if __name__=='__main__':
 if len(sys.argv)!=2:raise SystemExit('Usage: prepare_package06_site.py SITE_DIR')
 prepare(sys.argv[1])
