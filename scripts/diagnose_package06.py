#!/usr/bin/env python3
"""Diagnose 2026 autumn EN344/345 against the actually published 19th stable site.

Times transcribed from operator's *Sep 1-Dec 12, 2026* primary timetable:
https://www.nachtexpress.de/de/fahrplan/
December 14's EN324/325 must NOT be labelled current in November.
Find physical OSM coverage before changing public timetable.
"""
import json,sys
from pathlib import Path
from refine_osm_routes import project_stops
def sec(clock):
 h,m=map(int,clock.split(':'));return h*3600+m*60
AUTUMN_345={
 'tue-hamburg':[('Stockholm C','17:29'),('Norrköping C','18:59'),
   ('Linköping C','19:29'),('Nässjö C','20:29'),('Alvesta','21:10'),
   ('Hässleholm C','21:57'),('Lund C','22:31'),
   ('København Lufthavn','23:52'),('Padborg','27:12'),
   ('Hamburg Hbf','29:53')],
 'thu-berlin':[('Stockholm C','17:29'),('Norrköping C','18:59'),
   ('Linköping C','19:29'),('Nässjö C','20:29'),('Alvesta','21:10'),
   ('Hässleholm C','21:57'),('Lund C','22:31'),
   ('København Lufthavn','23:52'),('Padborg','27:12'),
   ('Hamburg Hbf','29:53'),('Berlin Gesundbrunnen','32:56')],
 'sat-berlin':[('Stockholm C','17:29'),('Norrköping C','18:59'),
   ('Linköping C','19:29'),('Nässjö C','20:29'),('Alvesta','21:10'),
   ('Hässleholm C','21:57'),('Lund C','22:31'),
   ('København Lufthavn','25:37'),('Padborg','29:08'),
   ('Hamburg Hbf','32:10'),('Berlin Gesundbrunnen','35:10')],
}
OTHER_COORDS={'Berlin Gesundbrunnen':[52.5489,13.3889]}
def main(p):
 data=json.loads(Path(p).read_text())
 rdc=[t for t in data['trips'] if t['agency']=='RDC EuroNight']
 assert len(rdc)==4 and len(data['trips'])==10798 and len(data['shapes'])==107
 allstations={}
 for t in data['trips']:
  for s in t['stops']:
   allstations.setdefault(s[2],s[:2])
 print('ORIGINAL RDC:')
 for t in rdc:
  print(json.dumps({'id':t['id'],'variant':t.get('routeVariant'),
     'shapeId':t['shapeId'],'start':t['stops'][0][4],
     'end':t['stops'][-1][3],
     'stops':[(s[2],s[4]) for s in t['stops']]},ensure_ascii=False),flush=True)
 mapping={s[2]:s[:2] for t in rdc for s in t['stops']}
 mapping.update(OTHER_COORDS)
 for label,stations in AUTUMN_345.items():
  stops=[];missing=[]
  for name,time in stations:
   xy=mapping.get(name) or allstations.get(name)
   if not xy:missing.append(name);continue
   stops.append([*xy,name,sec(time),sec(time)])
  print('AUTUMN SOURCE',label,'missing_coords',missing,flush=True)
  if missing:continue
  matches=[]
  for sid,shape in data['shapes'].items():
   if not isinstance(shape,list) or len(shape)<20:continue
   dist=project_stops(stops,shape,650)
   if dist is None:continue
   speed=[]
   for i in range(1,len(dist)):
    dt=stops[i][3]-stops[i-1][4]
    speed.append(round((dist[i]-dist[i-1])/dt*3.6) if dt>0 else -1)
   matches.append({'shapeId':sid,'minKmh':min(speed),'maxKmh':max(speed),
     'legKmh':speed,'osmVerified':any(t['shapeId']==sid and t.get('osmWayNetwork') is True for t in data['trips'])})
  print('AUTUMN ROUTE MATCHES',label,json.dumps(matches,ensure_ascii=False),flush=True)
if __name__=='__main__':main(sys.argv[1])
