#!/usr/bin/env python3
"""Check each NEW true Snälltåget physical train or foreign extension against
STABLE16's existing 101 VERIFIED railway routes before downloading cross-border
OSM. No lines are guessed; missing sections demand original connected OSM nodes.
"""
from pathlib import Path
from refine_osm_routes import project_stops
import json,sys,collections
def bounds(shape):
 return (min(p[0] for p in shape),max(p[0] for p in shape),
         min(p[1] for p in shape),max(p[1] for p in shape))
def near(stops,box):
 a,b,c,d=box
 return all(a-.12<=s[0]<=b+.12 and c-.20<=s[1]<=d+.20 for s in (stops[0],stops[-1]))
def main(oldfile,planfile,out):
 d=json.loads(Path(oldfile).read_text())
 plan=json.loads(Path(planfile).read_text())
 shapes=[(sid,shape,bounds(shape)) for sid,shape in d['shapes'].items()
  if isinstance(shape,list) and len(shape)>=6]
 used=[];missing=[]
 for t in plan['new']:
  match=None
  for sid,shape,box in shapes:
   if not near(t['stops'],box):continue
   for rev in [False,True]:
    oriented=shape[::-1] if rev else shape
    dist=project_stops(t['stops'],oriented,650)
    if dist is not None:
     match={'tripId':t['id'],'shapeId':sid,'reverse':rev,'spanKm':round((dist[-1]-dist[0])/1000,1)}
     break
   if match:break
  if match:
   used.append(match)
   print('SNÄLLTÅGET VERIFIED EXISTING OSM SHAPE',t['id'],match['shapeId'],
    'reverse',match['reverse'],'km',match['spanKm'],flush=True)
  else:
   missing.append(t)
   print('SNÄLLTÅGET NEEDS ADDITIONAL CROSS-BORDER ORIGINAL OSM NODES',
    t['id'],t['origin'],'→',t['destination'],
    [s[2] for s in t['stops']],flush=True)
 summary={'new':len(plan['new']),'reusedOldRails':len(used),'missingActualRailShapes':len(missing)}
 print('SNÄLLTÅGET OFFICIAL PHYSICAL ROUTE SUMMARY',json.dumps(summary),flush=True)
 Path(out).write_text(json.dumps({'source':plan['source'],
  'summary':summary,'reused':used,'missing':missing},ensure_ascii=False,separators=(',',':')))
if __name__=='__main__':
 if len(sys.argv)!=4:raise SystemExit('Usage: match_snall_existing_rail.py OLD.json PLAN.json OUT.json')
 main(*sys.argv[1:])
