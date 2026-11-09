"""Regression tests for 08:28 missing Lidingöbanan and protected 10-system site."""
import copy
import datetime as dt
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import repair_lidingo_gaps as repair
import build_rail_keyless as gtfs

DAY="2026-11-09"
FORWARD=[[59.355,18.125],[59.356,18.165],[59.358,18.2]]
BACKWARD=list(reversed(FORWARD))
SHAPES={"local-tram-osm:21:out":FORWARD,"local-tram-osm:21:back":BACKWARD}

def time(hour,minute):
 return int(dt.datetime(2026,11,9,hour,minute,tzinfo=gtfs.ZONE).timestamp())
def trip(direction,hour,minute,archived="2026-11-07"):
 geom=FORWARD if direction=="out" else BACKWARD
 first="Ropsten T-bana" if direction=="out" else "Gåshaga brygga station"
 last="Gåshaga brygga station" if direction=="out" else "Ropsten T-bana"
 start=time(hour,minute)
 return {"id":f"{direction}-{hour:02}:{minute:02}",
         "mode":"tram","line":"21","agency":"SL","serviceDay":DAY,
         "archiveDay":archived,"shapeId":"local-tram-osm:21:"+direction,
         "geometryQuality":"verified-osm-relation",
         "start":start,"end":start+22*60,
         "stops":[[geom[0][0],geom[0][1],first,0,0],
                  [geom[-1][0],geom[-1][1],last,22*60,22*60]]}

def base():
 original=[trip("out",6,10,archived="2026-11-06"),
           trip("back",6,19,archived="2026-11-06"),
           trip("out",9,1,archived="2026-11-06"),
           trip("back",9,18,archived="2026-11-06")]
 return {"scope":repair.BASE_SCOPE,"type":"historical-daily-repeating-simulation",
         "simulationTemplateDay":DAY,"trips":original,"shapes":copy.deepcopy(SHAPES),
         "counts":{"tram":10,"intercity":56,"commuter":30},
         "tramLines":{"12":5,"21":4},"sjDirections":{"to-goteborg":8,
         "from-goteborg":11,"to-malmo":20,"from-malmo":17},
         "localTramDirections":{"12":{"out":2,"back":3},
         "21":{"out":2,"back":2}}}

class LidingoGapTests(unittest.TestCase):
 def test_saturday_gtfs_replay_preserves_all_existing_trains(self):
  old=base()
  saturday=[trip("out",7,13),trip("back",7,35),
            trip("out",8,28),trip("back",8,30)]
  amended=repair.integrate(copy.deepcopy(old),saturday)
  self.assertEqual(amended["trips"][:len(old["trips"])],old["trips"])
  self.assertEqual(amended["shapes"],old["shapes"])
  self.assertEqual(amended["sjDirections"],old["sjDirections"])
  self.assertEqual(amended["counts"]["intercity"],56)
  self.assertEqual(amended["tramLines"]["12"],old["tramLines"]["12"])
  self.assertEqual(amended["tramLines"]["21"],8)
  new=amended["trips"][len(old["trips"]):]
  self.assertEqual({t["archiveDay"] for t in new},{"2026-11-07"})
  self.assertTrue(all(t["timetableProxy"].startswith("Saturday") for t in new))
  self.assertEqual({repair.direction(t) for t in new},{"out","back"})
 def test_no_fabricated_weekday_gap_without_archival_evidence(self):
  with self.assertRaises(ValueError):
   repair.integrate(base(),[])
 def test_no_approximated_rail_geometry_ever_added(self):
  old=base()
  bad=trip("out",8,28)
  bad["stops"][0][:2]=[50.0,10.0]
  with self.assertRaises(ValueError):
   repair.integrate(old,[bad,trip("back",8,30)])
 if __name__=="__main__":unittest.main()
