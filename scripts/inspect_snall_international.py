#!/usr/bin/env python3
"""Diagnostic for genuine original Snälltåget German/Danish/Swedish train
patterns and overlap with existing live domestic Stockholm–Malmö segments.
No release or changes; strictly source-bound stop and time patterns.
"""
from pathlib import Path
import collections,json,sys
def main(sourcefile,coveragefile):
 a=json.loads(Path(sourcefile).read_text())['operatorData']['Snälltåget']
 comparisons={x['sourceId']:x for x in json.loads(Path(coveragefile).read_text())['Snälltåget']['matches']}
 grouping=collections.defaultdict(list)
 for t in a:
  stops=t['stops'];clock=t['firstDeparture'];first=stops[0][2]
  st=next((s for s in stops if s[2]=='Stockholm Centralstation'),None)
  ct=st[4] if st is not None and st is stops[0] else st[3] if st is not None else None
  south=st is stops[0]
  sig=('from-stockholm' if south else 'to-stockholm',ct)
  grouping[sig].append(t)
  print('AUTHENTIC SNÄLLTÅGET SOURCE',t['id'],'DAYS',t['sourceDays'],
     'EXISTING',comparisons[t['id']]['existing'],
     'ORIGIN',first,'DESTINATION',stops[-1][2],
     'STOP-TIME-DETAIL',json.dumps([[s[2],s[3],s[4]] for s in stops],ensure_ascii=False),flush=True)
 for sig,values in grouping.items():
  print('ONE PHYSICAL DEPARTURE GROUP',sig,'SOURCE RECORDS',len(values),
   'ROUTE TYPES',json.dumps([(x['id'],x['destination'],x['sourceDays']) for x in values],ensure_ascii=False),flush=True)
if __name__=='__main__':
 if len(sys.argv)!=3:raise SystemExit('Usage: inspect_snall_international.py ARCHIVE.json COVERAGE.json')
 main(*sys.argv[1:])
