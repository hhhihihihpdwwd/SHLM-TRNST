#!/usr/bin/env python3
"""One uniquely physical historic Snälltåget departure per 2026 reference pattern.
Never duplicate same Norrköping (southbound) or Malmö (northbound) scheduled
train merely because Sunday/weekday GTFS has alternate through destinations.
On five already published domestic trains, import only the genuine foreign
extension BEFORE Malmö departure or AFTER Malmö arrival, never overlap trains.
Preserve original source variants as metadata, do not invent services.
"""
from __future__ import annotations
import collections,json,sys
from pathlib import Path
from refine_osm_routes import project_stops

def key(t):
 stops=t['stops'];names=[x[2].casefold() for x in stops]
 outbound=names[0]=='stockholm centralstation'
 if outbound:
  idx=next((i for i,s in enumerate(names) if 'norrköping central' in s),None)
  if idx is not None:return ('out-norrkoping',stops[idx][4])
  return ('out-stockholm',stops[0][4])
 idx=next((i for i,s in enumerate(names) if 'malmö central' in s),None)
 if idx is not None:return ('in-malmo',stops[idx][4])
 return ('in-stockholm',stops[-1][3])

def source_match(canonical,existing):
 a=canonical['stops'];b=existing['stops']
 labels=[s[2].casefold() for s in a];oldlabels=[s[2].casefold() for s in b]
 for i in range(len(a)-len(b)+1):
  if labels[i:i+len(b)]!=oldlabels:continue
  if all(abs(a[i+j][4]-x[4])<120 and abs(a[i+j][3]-x[3])<120 for j,x in enumerate(b)):
   return (i,i+len(b)-1)
 return None

def main(basefile,archivefile,output):
 data=json.loads(Path(basefile).read_text())
 assert len(data['trips'])==10779 and len(data['shapes'])==101
 source=json.loads(Path(archivefile).read_text())['operatorData']['Snälltåget']
 old=[x for x in data['trips'] if x['agency']=='Snälltåget']
 assert len(old)==5
 groups=collections.defaultdict(list)
 for t in source:groups[key(t)].append(t)
 requests=[];deduplicated=[]
 for k,arr in sorted(groups.items()):
  # Longest actual international route, then freshest GTFS source dates.
  # Each alternative is preserved in metadata, not a second simultaneous marker.
  ordered=sorted(arr,key=lambda t:(len(t['stops']),max(t['sourceDays']),t['id']),reverse=True)
  selected=ordered[0]
  candidates=[]
  for x in old:
   matched=source_match(selected,x)
   if matched:candidates.append((x,matched))
  if not candidates:
   # Find any historic alternative in group with identical physical Swedish
   # portion. This prevents the selected longer Berlin/Dresden variant from
   # looking like a new physical train due to a platform-time variation.
   for t in ordered[1:]:
    for x in old:
     if source_match(t,x):
      # Require selected and old to share timed Malmö or Norrköping stops
      if k==key(t):
       related=source_match(selected,x)
       if related:candidates.append((x,related))
       break
  if candidates:
   x,(begin,end)=max(candidates,key=lambda p:len(p[0]['stops']))
   if begin==0 and end<len(selected['stops'])-1:
    portion=selected['stops'][end:]
    kind='foreign-suffix'
   elif begin>0 and end==len(selected['stops'])-1:
    portion=selected['stops'][:begin+1]
    kind='foreign-prefix'
   elif begin==0 and end==len(selected['stops'])-1:
    deduplicated.append({'key':k,'already':x['id'],'variants':len(arr)})
    print('SNÄLL EXISTING FULL TRAIN PRESERVED',k,x['id'],'variants',len(arr),flush=True)
    continue
   else:raise ValueError('Ambiguous real international GTFS segmentation at '+repr(k))
   if len(portion)<2:
    deduplicated.append({'key':k,'already':x['id']});continue
   assert 'malmö' in portion[0][2].casefold() or 'malmö' in portion[-1][2].casefold()
   existing=x['id']
  else:
   portion=selected['stops'];kind='new-physical-train';existing=None
  row={'physicalKey':list(k),'id':'SNALL-INTL-20261109:'+selected['id']+':'+kind,
   'sourceTripId':selected['id'],'kind':kind,'existingDomesticId':existing,
   'sourceDays':sorted({d for t in arr for d in t['sourceDays']}),
   'variantSources':[{'id':t['id'],'origin':t['origin'],'destination':t['destination'],
      'days':t['sourceDays']} for t in arr],
   'originalThroughOrigin':selected['origin'],'originalThroughDestination':selected['destination'],
   'origin':portion[0][2],'destination':portion[-1][2],
   'stops':portion,'firstDeparture':portion[0][4],'lastArrival':portion[-1][3]}
  assert row['lastArrival']>row['firstDeparture']
  requests.append(row)
  print('SNÄLLTÅGET REAL SIMULATED MISSING PIECE',k,kind,
   row['origin'],'→',row['destination'],'REAL STOPS',len(portion),
   'HISTORIC ALTERNATIVE GTFS VARIANTS',len(arr),'PREVIOUS',existing,flush=True)
 print('SNÄLL SOURCE-DEDUPLICATED PHYSICAL GROUPS',len(groups),
       'NEEDED ADDITIVE TRAIN PARTS',len(requests),'EXISTING DOMESTIC ONLY',len(deduplicated),flush=True)
 out={'source':'GTFS Sverige 2 historical 2026-11-04 ZIP, authenticated Snälltåget',
  'physicalServiceGroups':len(groups),'new':requests,'preserved':deduplicated}
 Path(output).write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')))
 assert len(groups)>=8
 assert any(x['kind']=='foreign-prefix' for x in requests)
 assert any(x['kind']=='foreign-suffix' for x in requests)
if __name__=='__main__':
 if len(sys.argv)!=4:raise SystemExit('Usage: plan_snall_international.py STABLE16.json SOURCE.json PLAN.json')
 main(*sys.argv[1:])
