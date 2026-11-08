import datetime as dt
import sys
import unittest
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from build_rail_keyless import SOURCE_START, round_robin_service_days, LIMIT_PER_MODE

class DayCoverageTests(unittest.TestCase):
 def test_source_week_contains_actual_archived_november_8_sunday(self):
  self.assertLessEqual(SOURCE_START,dt.date(2026,11,8))
  self.assertGreaterEqual(SOURCE_START+dt.timedelta(days=6),dt.date(2026,11,8))
 def test_mode_cap_cannot_starve_last_day(self):
  yesterday,today,tomorrow=[dt.date(2026,11,7)+dt.timedelta(days=i) for i in range(3)]
  modes=("metro","commuter","rail","tram")
  candidates=[]
  for mode in modes:
   for day in (yesterday,today,tomorrow):
    for n in range(3500):
     hour=n%24
     line=str(n%7)
     candidates.append((mode,str(n),[(0,0,hour*3600)],{"line":line},mode,str(n),day,day))
  ordered=round_robin_service_days(candidates)
  capped=Counter()
  seen=Counter()
  evening=Counter()
  for row in ordered:
   mode=row[0]
   if capped[mode]>=LIMIT_PER_MODE[mode]:continue
   capped[mode]+=1
   seen[(mode,row[6])]+=1
   if (row[2][0][2]//3600)>=19:evening[(mode,row[6])]+=1
  for mode in modes:
   for day in (yesterday,today,tomorrow):
    self.assertGreater(seen[(mode,day)],0,(mode,day))
    self.assertGreater(evening[(mode,day)],0,("evening starvation",mode,day))
if __name__=="__main__":unittest.main()
