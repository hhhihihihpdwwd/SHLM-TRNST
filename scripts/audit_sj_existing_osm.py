#!/usr/bin/env python3
"""Analyze true SJ November 2026 inventory against EXACT immutable STABLE13
real OSM geometries; no assumed rail connections or fictional services.

Select every authentic Friday SJ Stockholm-calling journey, then include only
the endpoint families not represented that Friday from other 2026 archival days.
This avoids falsely stacking the whole week's alternate-day trains simultaneously.
"""
import collections,datetime as dt,json,sys
from pathlib import Path
from refine_osm_routes import project_stops, distance

REFERENCE_DAY='2026-11-06'
MAX_ERROR=650
def key(t):return (t['origin'].casefold(),t['destination'].casefold())
def bounds(points):
 lats=[x[0] for x in points];lons=[x[1] for x in points]
 return min(lats),max(lats),min(lons),max(lons)
def near_bounding_box(stops,box):
 latmin,latmax,lonmin,lonmax=box
 for point in (stops[0],stops[-1]):
  if not (latmin-.025<point[0]<latmax+.025 and lonmin-.045<point[1]<lonmax+.045):return False
 return True

def build(existing,source):
 assert len(existing['trips'])==10437 and len(existing['shapes'])==71
 assert existing['scope'].endswith('-vr-snalltaget-vy-tagab-rdc')
 if source['operatorIds']!={'74':'SJ'}:
  raise ValueError('Unexpected historical SJ operator attribution: '+repr(source['operatorIds']))
 allrows=source['trips']
 friday=[t for t in allrows if REFERENCE_DAY in t['sourceDays']]
 present={key(t) for t in friday}
 fallback=[t for t in allrows if key(t) not in present]
 # In fallback endpoint families, pick the day with most trips, not the whole
 # week's mutually exclusive timetable variants.
 byfamily=collections.defaultdict(list)
 for t in fallback:byfamily[key(t)].append(t)
 selected=list(friday)
 for fam,records in byfamily.items():
  day_counts=collections.Counter(d for t in records for d in t['sourceDays'])
  best=sorted(day_counts,key=lambda d:(-day_counts[d],d))[0]
  selected.extend(t for t in records if best in t['sourceDays'])
 selected.sort(key=lambda x:(x['origin'],x['destination'],x['firstDeparture'],x['id']))
 shapes=[]
 for sid,geom in existing['shapes'].items():
  if isinstance(geom,list) and len(geom)>3 and all(isinstance(p,list) and len(p)>=2 for p in geom):
   shapes.append((sid,geom,bounds(geom)))
 existing_sj=[t for t in existing['trips'] if t.get('agency')=='SJ']
 matches=[];unmatched=[];dupes=[]
 for n,t in enumerate(selected,1):
  stops=t['stops']
  # Already published SJ journeys must never be counted as new.
  orig=(t['origin'].casefold(),t['destination'].casefold())
  dup=False
  for prev in existing_sj:
   ps=prev.get('stops') or []
   if len(ps)<2:continue
   if (ps[0][2].casefold(),ps[-1][2].casefold())!=orig:continue
   if abs((ps[0][4] if len(ps[0])>4 else 0)-t['firstDeparture'])<=90:
    dup=True;break
  if dup:
   dupes.append(t['id']);continue
  chosen=None
  for sid,shape,box in shapes:
   if not near_bounding_box(stops,box):continue
   match=project_stops(stops,shape,MAX_ERROR)
   if match is not None:
    chosen={'tripId':t['id'],'shapeId':sid,'startMetres':round(match[0]),'endMetres':round(match[-1])}
    break
   match=project_stops(stops,list(reversed(shape)),MAX_ERROR)
   if match is not None:
    chosen={'tripId':t['id'],'shapeId':sid,'reverse':True,'startMetres':round(match[0]),'endMetres':round(match[-1])}
    break
  if chosen:matches.append(chosen)
  else:unmatched.append({'id':t['id'],'origin':t['origin'],'destination':t['destination'],
    'stops':[s[2] for s in stops],'sourceDays':t['sourceDays']})
  if n%40==0:print('PROGRESS CHECKED',n,'/',len(selected),'SUITABLE VERIFIED SHAPES',len(matches),flush=True)
 stats={'allAuthenticStockholmSJTrainIds':len(allrows),
  'fridayServiceTrainIds':len(friday),
  'selectedDailyReferenceTemplates':len(selected),
  'alreadyPublishedSJDuplicates':len(dupes),
  'readyOnExistingVerifiedOSMShapes':len(matches),
  'missingVerifiedRailShapes':len(unmatched),
  'unmatchedEndpointPairs':dict(collections.Counter(x['origin']+' → '+x['destination'] for x in unmatched))}
 report={'summary':stats,'selected':selected,'alreadyPresentIds':dupes,'matched':matches,'needsRailway':unmatched}
 print('SJ FULL-NETWORK COVERAGE',json.dumps(stats,ensure_ascii=False),flush=True)
 return report

if __name__=='__main__':
 if len(sys.argv)!=4:raise SystemExit('Usage: audit_sj_existing_osm.py STABLE13.json SJ_AUDIT.json REPORT.json')
 a=json.loads(Path(sys.argv[1]).read_text());b=json.loads(Path(sys.argv[2]).read_text())
 out=build(a,b)
 path=Path(sys.argv[3]);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')))
 print('REPORT SAVED',path,path.stat().st_size,flush=True)
