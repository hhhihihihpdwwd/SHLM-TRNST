"""Regression: infrequent Roslagsbanan 29 survives unmodified weekday replay."""
import datetime as dt
import sys
import unittest
from unittest.mock import patch
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import build_roslags_candidates as roslags

SUNDAY=dt.date(2026,11,8)
SATURDAY=dt.date(2026,11,7)

def sample(line,day,hour,start_minute=0):
    start=roslags.clock_at(day,hour,start_minute)
    return {"id":f"{line}-{day}-{hour}","line":line,"mode":"tram",
            "serviceDay":day.isoformat(),"start":start,"end":start+1800,
            "shapeId":"example","stops":[[59.34,18.07,"Start",hour*3600,hour*3600],
                                         [59.5,18.2,"End",hour*3600+1800,hour*3600+1800]]}

class RoslagsScheduleTests(unittest.TestCase):
 def test_sparse_line29_is_preserved_without_noon_departure_requirement(self):
    # The source builder no longer replays Saturday on Sunday. The chosen
    # reference Friday is already mapped to both days by the shared importer.
    trips=[sample(line,SUNDAY,h,30) for line in ("27","28") for h in (12,13)]
    trips += [sample("29",SUNDAY,h) for h in (10,16)]
    data={"trips":trips,"shapes":{"example":[[59.34,18.07],[59.5,18.2]]}}
    with patch.object(roslags.archive,"build",return_value=data) as build:
        out=roslags.build_candidates(None,SUNDAY)
    self.assertEqual(build.call_args.kwargs["tram_lines"],{"27","28","29"})
    line29=[t for t in out["trips"] if t["line"]=="29" and t["serviceDay"]==SUNDAY.isoformat()]
    self.assertEqual(len(line29),2)
    self.assertTrue(all(not t.get("timetableProxy") for t in line29))
    noon=roslags.clock_at(SUNDAY,12)
    self.assertFalse(any(t["start"]<=noon<=t["end"] for t in line29))
 def test_missing_line29_is_still_rejected(self):
    data={"trips":[sample(line,SUNDAY,12,30) for line in ("27","28")],
          "shapes":{"example":[[59.34,18.07],[59.5,18.2]]}}
    with patch.object(roslags.archive,"build",return_value=data):
       with self.assertRaisesRegex(ValueError,"Roslagsbanan line 27, 28 or 29"):
          roslags.build_candidates(None,SUNDAY)

if __name__=="__main__":unittest.main()
