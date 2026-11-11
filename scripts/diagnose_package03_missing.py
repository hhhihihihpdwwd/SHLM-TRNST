#!/usr/bin/env python3
"""Read-only physical track gap diagnosis for the two authentic missing package-03 services."""
import json,sys,collections,math
from pathlib import Path
from refine_osm_routes import project_stops, distance
data=json.loads(Path(sys.argv[1]).read_text())
sj=json.loads(Path(sys.argv[2]).read_text())
vr=json.loads(Path(sys.argv[3]).read_text())
existing_sj={str(t.get('sourceTripId')) for t in data['trips'] if t['agency']=='SJ'}
legacy={(tuple(x[2] for x in t['stops']),t['stops'][0][4],t['stops'][-1][3])
        for t in data['trips'] if t['agency']=='SJ' and not t.get('sourceTripId')}
missing_sj=[t for t in sj['trips'] if '2026-11-06' in t['sourceDays'] and
 t['id'] not in existing_sj and
 (tuple(x[2] for x in t['stops']),t['firstDeparture'],t['lastArrival']) not in legacy]
existing_vr={str(t['id']).split(':')[1] for t in data['trips'] if t['agency']=='VR Snabbtåg' and str(t['id']).startswith('VR-ARCHIVE:')}
missing_vr=[t for t in vr['trips'] if t['serviceDay']=='2026-11-06' and str(t['id']).split(':')[1] not in existing_vr]
def nearest_point_distance(p,shape):
 best=1e20
 scale=111100*math.cos(math.radians(p[0]))
 for a,b in zip(shape,shape[1:]):
  dx=(b[1]-a[1])*scale;dy=(b[0]-a[0])*111100
  px=(p[1]-a[1])*scale;py=(p[0]-a[0])*111100
  f=max(0,min(1,(dx*px+dy*py)/(dx*dx+dy*dy or 1)))
  best=min(best,math.hypot(px-dx*f,py-dy*f))
 return round(best)
for agency,missing in [('SJ',missing_sj),('VR Snabbtåg',missing_vr)]:
 print('MISSING_SOURCE',agency,len(missing),flush=True)
 for t in missing:
  stops=t['stops']
  print('SERVICE',agency,t['id'],'CLOCK',stops[0][4],stops[-1][3],
        'STOPS',[(s[2],s[4]) for s in stops],flush=True)
  good=[];near=[]
  for sid,shape in data['shapes'].items():
   if not isinstance(shape,list) or len(shape)<3:continue
   max_gap=max(nearest_point_distance(s,shape) for s in stops)
   if max_gap<=2500:near.append((max_gap,sid))
   for reverse in (False,True):
    positions=project_stops(stops,shape[::-1] if reverse else shape,650)
    if positions is None:continue
    speeds=[round((positions[i]-positions[i-1])/max(1,stops[i][3]-stops[i-1][4])*3.6)
            for i in range(1,len(stops))]
    good.append({'shapeId':sid,'reverse':reverse,'legSpeedsKmh':speeds,'maxKmh':max(speeds),
                 'distanceKm':round((positions[-1]-positions[0])/1000,1)})
  print('VALID_REAL_OSM_MATCHES',json.dumps(good,ensure_ascii=False),flush=True)
  print('CLOSEST_WHOLE_ROUTE',sorted(near)[:12],flush=True)
