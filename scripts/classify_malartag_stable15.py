#!/usr/bin/env python3
"""Audit actual Tuesday Mälartåg timetable vs exact publicly proven STABLE15.
Do not invent classifications. Prove existing OSM route alignment; report gaps.
"""
import collections,json,sys
from pathlib import Path
from refine_osm_routes import project_stops
from build_malartag_candidates import CORRIDORS,contains_station

DAY='2026-11-10'
def normalize(s):return (s or '').strip().casefold()
def cls(t):
 names=[normalize(x[2]) for x in t['stops']]
 if len(names)<2:return None
 a,b=names[0],names[-1]
 if {a,b}=={'stockholm centralstation','uppsala centralstation'}:
  return 'orebro-uppsala'
 if {a,b}=={'eskilstuna centralstation','uppsala centralstation'}:
  return 'uven'
 if {a,b}=={'eskilstuna centralstation','stockholm centralstation'}:
  return 'orebro-uppsala'
 return None
def endpoints(shape):
 lats=[x[0] for x in shape];lons=[x[1] for x in shape]
 return min(lats),max(lats),min(lons),max(lons)
def accepts(stops,box):
 a,b,c,d=box
 return all(a-.05<=s[0]<=b+.05 and c-.08<=s[1]<=d+.08 for s in (stops[0],stops[-1]))
def main(baseline,source,outpath):
 base=json.loads(Path(baseline).read_text())
 data=json.loads(Path(source).read_text())
 assert len(base['trips'])==10611 and len(base['shapes'])==95
 old=[t for t in base['trips'] if t.get('agency')=='Mälartåg']
 print('CURRENT DEPLOYED MALARTAG RECORDS',len(old),'per corridor',
  json.dumps(collections.Counter(t.get('corridor') for t in old)),flush=True)
 shapes=[(sid,shape,endpoints(shape)) for sid,shape in base['shapes'].items()
         if isinstance(shape,list) and len(shape)>4]
 candidates=[]
 for corridor,rows in data['corridors'].items():
  candidates += [dict(t,corridor=corridor) for t in rows if DAY in t['sourceDays']]
 others=[t for t in data['unclassified'] if DAY in t['sourceDays']]
 accepted=[];unclassified=[]
 for t in others:
  key=cls(t)
  if key:accepted.append(dict(t,corridor=key,originalUnclassified=True))
  else:unclassified.append(t)
 candidates.extend(accepted)
 print('UNCLASSIFIED TUESDAY TRAINS',len(others),'SAFE RECLASSIFIED',len(accepted),
  'REMAINING',len(unclassified),flush=True)
 print('REMAINING STATION PAIRS',json.dumps(collections.Counter(
  (r['origin'],r['destination'],r['routeName']) for r in unclassified).most_common(100),
  ensure_ascii=False),flush=True)
 oldday=[t for t in old if t.get('serviceDay')==DAY]
 def duplicate(t):
  for prior in oldday:
   if prior['stops'][0][2]!=t['origin'] or prior['stops'][-1][2]!=t['destination']:continue
   if (abs(prior['stops'][0][4]-t['firstDeparture'])<=60 and
      abs(prior['stops'][-1][3]-t['lastArrival'])<=90):
    return prior['id']
  return None
 stats=collections.Counter();missing=[];reused=[];already=[]
 matched={}
 for t in candidates:
  current=duplicate(t)
  if current:
   already.append({'id':t['id'],'matchedExistingId':current,'corridor':t['corridor']})
   stats['already']+=1;continue
  found=None
  for sid,shape,box in shapes:
   if not accepts(t['stops'],box):continue
   for reverse in (False,True):
    rail=shape[::-1] if reverse else shape
    projection=project_stops(t['stops'],rail,650)
    if projection is not None:
     found={'tripId':t['id'],'shapeId':sid,'reverse':reverse};break
   if found:break
  if found:
   reused.append(found);matched[t['id']]=found;stats['reused']+=1
  else:
   missing.append({'id':t['id'],'corridor':t['corridor'],'origin':t['origin'],
      'destination':t['destination'],'stops':t['stops'],'firstDeparture':t['firstDeparture'],
      'lastArrival':t['lastArrival']})
   stats['missing']+=1
  stats[t['corridor']]+=1
 print('ALL FIVE CORRIDORS TUESDAY CANDIDATE COUNT',len(candidates),
       'OLD MATCHES',len(already),'REUSE REAL SHAPES',len(reused),
       'NEW OSM RAIL ROUTING NEEDED',len(missing),flush=True)
 print('NEW OSM RAIL CORRIDOR NEEDS',json.dumps(collections.Counter(
  (t['corridor'],t['origin'],t['destination']) for t in missing).most_common(60),ensure_ascii=False),flush=True)
 obj={'referenceDay':DAY,'verifiedBaseline':{'trips':10611,'shapes':95},
  'candidates':candidates,'already':already,'reused':reused,
  'missing':missing,'unclassified':unclassified,'stats':dict(stats)}
 Path(outpath).parent.mkdir(parents=True,exist_ok=True)
 Path(outpath).write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':')))
 if unclassified:raise RuntimeError('Could not safely identify ALL Mälartåg train patterns: '+str(len(unclassified)))
if __name__=='__main__':
 if len(sys.argv)!=4:raise SystemExit('Usage: classify_malartag_stable15.py BASE.json AUDIT.json OUT.json')
 main(*sys.argv[1:])
