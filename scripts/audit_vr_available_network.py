#!/usr/bin/env python3
"""Check whether STABLE07 already has genuine OSM track near missing VR GTFS stops."""
import json,math,sys
from pathlib import Path
from refine_osm_routes import distance
KEYS=("Stockholm Centralstation","Flemingsberg station",
 "Katrineholm Centralstation","Hallsberg station","Skövde Centralstation",
 "Herrljunga station","Alingsås station","Göteborg Centralstation")
# Source point coordinates are literal real GTFS stops from the pinned archive.
# The caller supplies an authentic VR timetable JSON.
def nearest(p,shape):
 scale=111100*math.cos(math.radians(p[0]))
 best=float("inf")
 for a,b in zip(shape,shape[1:]):
  dx=(b[1]-a[1])*scale;dy=(b[0]-a[0])*111100
  px=(p[1]-a[1])*scale;py=(p[0]-a[0])*111100
  f=max(0,min(1,(px*dx+py*dy)/(dx*dx+dy*dy or 1)))
  best=min(best,math.hypot(px-f*dx,py-f*dy))
 return round(best)
def main():
 d=json.loads(Path(sys.argv[1]).read_text())
 c=json.loads(Path(sys.argv[2]).read_text())
 samples={k:None for k in KEYS}
 for train in c["trips"]:
  for point in train["stops"]:
   if point[2] in samples:samples[point[2]]=point
 summary={}
 for key,point in samples.items():
  if point is None:continue
  found=[]
  for sid,shape in d["shapes"].items():
   if not isinstance(shape,list) or len(shape)<2:continue
   gap=nearest(point[:2],shape)
   if gap<2500:
    found.append((gap,sid,len(shape),shape[0],shape[-1]))
  found.sort()
  summary[key]=found
  print("VR MISSING-STATION EXISTING TRACK",key,"NEARBY",len(found),
        "REAL TRACKS",found[:26],flush=True)
 for sid,shape in d["shapes"].items():
  if not (sid.startswith("sj-osm:") or "malartag" in sid.lower()):continue
  gap={key:nearest(point[:2],shape) for key,point in samples.items() if point}
  if min(gap.values())<2500:
   print("VR POTENTIAL EXISTING REGIONAL TRACK",sid,len(shape),
         "METRES PER STOP",gap,flush=True)
if __name__=="__main__":main()
