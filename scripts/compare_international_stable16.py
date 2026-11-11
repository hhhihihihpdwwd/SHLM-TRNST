#!/usr/bin/env python3
"""Compare each real authenticated operator GTFS service to precise old STABLE16.
No arbitrary owner relabels or rounded matching that can double a real train.
Retain exhaustive reports for through services, same train domestic sections,
and any unmatched historical weekday/route pattern.
"""
from pathlib import Path
import collections,json,sys
def norm(s):return str(s or '').strip().casefold()
def matches_real(gt,old):
 a=[s[2] for s in gt['stops']];b=[s[2] for s in old['stops']]
 # a common domestic subset may be a segment of a real international train.
 choices=[]
 for start in range(len(a)-len(b)+1):
  if [norm(x) for x in a[start:start+len(b)]]!=[norm(x) for x in b]:continue
  zipped=list(zip(gt['stops'][start:start+len(b)],old['stops']))
  departure=max(abs(x[4]-y[4]) for x,y in zipped)
  arrival=max(abs(x[3]-y[3]) for x,y in zipped)
  if departure<=120 and arrival<=120:
   choices.append((max(departure,arrival),start,start+len(b)-1))
 return min(choices) if choices else None
def main(oldfile,sourcefile,rdcfile,output):
 d=json.loads(Path(oldfile).read_text());source=json.loads(Path(sourcefile).read_text());rdc=json.loads(Path(rdcfile).read_text())
 assert len(d['trips'])==10779 and len(d['shapes'])==101
 operators=['Snälltåget','Vy Tåg','Tågab','RDC EuroNight']
 old={a:[x for x in d['trips'] if x.get('agency')==a] for a in operators}
 new={**source['operatorData'],'RDC EuroNight':rdc['trips']}
 report={}
 for agency in operators:
  comparison=[];unmatched=[]
  for t in new[agency]:
   candidates=[]
   for x in old[agency]:
    m=matches_real(t,x)
    if m is None:continue
    # Some old trains intentionally encode the original archive trip ID.
    marker=norm(t['id']) in norm(x['id']) or norm(t['id']) in norm(x.get('sourceTripId',''))
    candidates.append({'id':x['id'],'match':m,'exactOriginalId':marker,
                       'oldLength':len(x['stops']),'sourceLength':len(t['stops'])})
   candidates.sort(key=lambda x:(not x['exactOriginalId'],x['match'][0],-x['oldLength']))
   best=candidates[0] if candidates else None
   if best is None:unmatched.append(t)
   comparison.append({'sourceId':t['id'],'origin':t['origin'] if 'origin' in t else t['stops'][0][2],
    'destination':t['destination'],'firstDeparture':t.get('firstDeparture',t['stops'][0][4]),
    'sourceDays':t.get('sourceDays') or t.get('historicReferenceDays'),
    'existing':best,'extraBeyondExisting':(len(t['stops'])-best['oldLength']) if best else None})
  stats=collections.Counter(('present' if x['existing'] else 'missing') for x in comparison)
  stat={'existingRecords':len(old[agency]),'sourcePatterns':len(new[agency]),
        'matched':stats['present'],'unmatched':stats['missing']}
  report[agency]={'statistics':stat,'matches':comparison,'unmatchedTrips':unmatched}
  print('INTERNATIONAL 4 OPERATOR SOURCE-COMPARED',agency,json.dumps(stat,ensure_ascii=False),flush=True)
  print('MISSING GENUINE ROUTES',agency,json.dumps(collections.Counter(
   (t.get('origin',t['stops'][0][2]),t['destination']) for t in unmatched).most_common(25),ensure_ascii=False),flush=True)
  if agency=='Snälltåget':
   print('SNÄLL AUTHENTIC WHOLE-SERVICE COMPARISONS',json.dumps(comparison,ensure_ascii=False),flush=True)
 Path(output).write_text(json.dumps(report,ensure_ascii=False,separators=(',',':')))
if __name__=='__main__':
 if len(sys.argv)!=5:raise SystemExit('Usage: compare_international_stable16.py LIVE.json ARCHIVE.json RDC.json OUT.json')
 main(*sys.argv[1:])
