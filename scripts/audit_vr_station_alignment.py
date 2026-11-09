#!/usr/bin/env python3
"""Investigate every rejected VR stop without guessing alternate railway tracks."""
import collections
import json
import math
import sys
from pathlib import Path
from refine_osm_routes import project_stops
from append_vr_rail import eligible_shapes
ROOT=Path(__file__).resolve().parents[1]

def nearest_meters(p,shape):
 best=float("inf")
 for a,b in zip(shape,shape[1:]):
  scale=111100*math.cos(math.radians(p[0]))
  dx=(b[1]-a[1])*scale;dy=(b[0]-a[0])*111100
  x=(p[1]-a[1])*scale;y=(p[0]-a[0])*111100
  f=max(0,min(1,(x*dx+y*dy)/(dx*dx+dy*dy or 1)))
  best=min(best,math.hypot(x-f*dx,y-f*dy))
 return best

def main():
 original=json.loads(Path(sys.argv[1]).read_text())
 candidates=json.loads(Path(sys.argv[2]).read_text())
 shapes=eligible_shapes(original)
 tday=original["simulationTemplateDay"]
 originals=[t for t in candidates["trips"] if t["serviceDay"]==tday]
 report=collections.Counter()
 for t in originals:
  best=None
  for sid,shape in shapes:
   dists=[round(nearest_meters(s[:2],shape)) for s in t["stops"]]
   maxima=max(dists)
   successes=[m for m in (500,650,750,800,850) if project_stops(t["stops"],shape,m) is not None]
   quality=(min(successes) if successes else 9999,maxima,sid,dists)
   if best is None or quality[:2]<best[:2]:best=quality
  if best is None:continue
  threshold,maxgap,sid,dists=best
  k="SUCCESS@" + str(threshold) if threshold<9000 else "FAILED"
  report[(t["direction"],k)]+=1
  print("VR TRACK STATION AUDIT",t["direction"],t["id"],
     "BEST_TRUSTWORTHY_OSM",sid,"MIN_VERIFIED_THRESHOLD",threshold,
     "MAX_STOP_GAP_METRES",maxgap,
     "STOPS_AND_GAPS",[(s[2],d) for s,d in zip(t["stops"],dists)],flush=True)
 print("VR STATION-SNAP THRESHOLD SUMMARY",dict((str(k),v) for k,v in report.items()),flush=True)
if __name__=="__main__":main()
