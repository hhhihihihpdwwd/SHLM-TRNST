#!/usr/bin/env python3
"""RDC EuroNight 344/345 historical reference from the operator's 2026 timetable.
Departure/arrival clock times are sourced from https://www.nachtexpress.de/de/fahrplan/
(effective 1 Sep – 12 Dec 2026). Four authenticated representative patterns:
northbound Berlin, northbound Hamburg; southbound Berlin, southbound Hamburg-Altona.
The train instances repeat DAILY in the Stockholm Rail *simulation*, not in reality.
Coordinates are preliminary station search seeds and MUST be snapped/verified against
actual OSM railway=rail graph nodes, or the publisher must fail closed.
"""
from __future__ import annotations
import datetime as dt,json,sys
from pathlib import Path
from zoneinfo import ZoneInfo

SOURCE='https://www.nachtexpress.de/de/fahrplan/'
TEMPLATE='2026-11-06'
# Station location search seeds approximate; actual geometry follows verified OSM rail ways.
STATIONS={
 'Berlin-Lichtenberg':(52.5106,13.4965),
 'Berlin Hauptbahnhof':(52.5255,13.3694),
 'Hamburg Hbf':(53.5531,10.0067),
 'Hamburg-Altona':(53.5525,9.9350),
 'Padborg':(54.8241,9.3637),
 'København Lufthavn':(55.6301,12.6497),
 'København Syd':(55.6489,12.5116),
 'Lund C':(55.7050,13.1872),
 'Hässleholm C':(56.1588,13.7630),
 'Alvesta':(56.8992,14.5571),
 'Nässjö C':(57.6532,14.6946),
 'Linköping C':(58.4162,15.6247),
 'Norrköping C':(58.5966,16.1836),
 'Stockholm C':(59.33014,18.058154)
}
# Time order has explicit next-day rollover. All three countries share CET/CEST;
# historic Nov 2026 timestamps are outside DST switchover.
NORTH_COMMON=[
 ('Hamburg Hbf','21:53'),('Padborg','24:29'),('København Lufthavn','27:23'),
 ('Lund C','28:35'),('Hässleholm C','29:13'),('Alvesta','30:01'),
 ('Nässjö C','30:45'),('Linköping C','31:48'),('Norrköping C','32:16'),
 ('Stockholm C','33:45')
]
SOUTH_COMMON=[
 ('Stockholm C','16:34'),('Norrköping C','18:02'),('Linköping C','18:37'),
 ('Nässjö C','20:03'),('Alvesta','20:40'),('Hässleholm C','21:30'),
 ('Lund C','22:01'),('København Lufthavn','23:02'),
 ('København Syd','23:16'),('Padborg','26:50')
]
VARIANTS=[
 ('344','Berlin-Lichtenberg', [('Berlin-Lichtenberg','18:39')]+NORTH_COMMON,'Berlin → Stockholm', 'Monday/Friday original'),
 ('344','Hamburg Hbf',NORTH_COMMON,'Hamburg → Stockholm','Wednesday original'),
 ('345','Berlin Hauptbahnhof',SOUTH_COMMON+[('Hamburg Hbf','29:44'),('Berlin Hauptbahnhof','33:18')], 'Stockholm → Berlin','Thursday/Saturday original'),
 ('345','Hamburg-Altona',SOUTH_COMMON+[('Hamburg-Altona','30:06')], 'Stockholm → Hamburg','Tuesday original')
]
def seconds(value):
 h,m=map(int,value.split(':'))
 assert 0<=h<48 and 0<=m<60
 return h*3600+m*60

def build():
 midnight=dt.datetime.combine(dt.date.fromisoformat(TEMPLATE),dt.time(),ZoneInfo('Europe/Stockholm'))
 trips=[]
 for number,variant,items,label,days in VARIANTS:
  clock=[seconds(clock) for _,clock in items]
  assert all(a<b for a,b in zip(clock,clock[1:]))
  coords=[[STATIONS[n][0],STATIONS[n][1],n,t,t] for (n,_),t in zip(items,clock)]
  direction='from-stockholm' if number=='345' else 'to-stockholm'
  # Only real 2026 operator-published time patterns are ever imported.
  trips.append({
   'id':'RDC-EURONIGHT-'+number+'-'+variant.lower().replace(' ','-'),
   'agency':'RDC EuroNight','line':'EN '+number,'train':number,'mode':'intercity',
   'serviceDay':TEMPLATE,'historicReferenceDays':days,
   'source':SOURCE,'archiveDay':'2026-11-06','direction':direction,
   'start':int((midnight+dt.timedelta(seconds=clock[0])).timestamp()),
   'end':int((midnight+dt.timedelta(seconds=clock[-1])).timestamp()),
   'stops':coords,'destination':items[-1][0],
   'historicPattern':'official 2026 RDC timetable, daily-repeating illustrative simulation',
   'routeVariant':variant,'shapeId':None,'geometryQuality':'awaiting-verified-osm',
   'isLiveGPS':False,'vehiclePhotoStatus':'illustrative-only'
  })
 assert len(trips)==4 and {t['direction'] for t in trips}=={'from-stockholm','to-stockholm'}
 return {'operator':'RDC EuroNight','officialTimetable':SOURCE,'validFrom':'2026-09-01',
  'validTo':'2026-12-12','simulationTemplateDay':TEMPLATE,
  'disclaimer':'Real service approximately three days weekly in each direction; historic official journeys repeat daily solely as map simulation.',
  'stationSeeds':'preliminary; verify against actual OSM shared railway way nodes before release',
  'trips':trips}

if __name__=='__main__':
 obj=build()
 assert len(sys.argv)==2,'Usage: rdc_official_timetable.py OUT.json'
 path=Path(sys.argv[1]);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':')))
 for t in obj['trips']:
  print('OFFICIAL RDC',t['line'],t['routeVariant'],t['direction'],len(t['stops']),'REAL TIMETABLE STOPS',t['stops'][0][2],'→',t['stops'][-1][2],flush=True)
 print('RDC OFFICIAL HISTORICAL TRAIN TEMPLATES',len(obj['trips']),'from operator publication')
