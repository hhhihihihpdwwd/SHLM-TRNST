"""Snälltåget genuine domestic GTFS sections and immutable twelve-system OSM tests."""
import copy
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import build_snalltaget_candidates as snall
import append_snalltaget as append

def timetable(names):
 return [(i,(58+i*.01,16+i*.005,name),i*1000,i*1000)
   for i,name in enumerate(names)]
def fixture():
 shape=[[59.0-i*.001,18.0-i*.002] for i in range(240)]
 reverse=list(reversed(shape))
 base={"scope":append.BASE_SCOPE,"type":"historical-daily-repeating-simulation",
       "simulationTemplateDay":"2026-11-09",
       "trips":[{"id":"prior-"+str(i),"mode":"commuter"} for i in range(10402)],
       "shapes":{"sj-osm:8860632:forward":shape,
                 "sj-osm:8860632:reverse":reverse,
                 "protected-original-shape":[[59.1,18],[59.2,18.1]]},
       "counts":{"intercity":69,"commuter":300,"metro":800,"regional":432},
       "vrDirections":{"to-goteborg":7,"to-stockholm":6},
       "malartagDirections":{"orebro-uppsala":{},"nykoping":{},"uven":{}},
       "sjDirections":{"to-malmo":20},
       "tramLines":{"21":391}}
 source=[]
 for direction,coord in (("to-malmo",shape),("to-stockholm",reverse)):
  for date in ("2026-11-08","2026-11-09","2026-11-10"):
   stops=[[p[0],p[1],name,n*1200,n*1200] for n,(p,name) in
          enumerate(zip((coord[0],coord[119],coord[239]),
           ("Stockholm Centralstation","Linköping Centralstation","Malmö Centralstation")
           if direction=="to-malmo" else
           ("Malmö Centralstation","Linköping Centralstation","Stockholm Centralstation")))]
   source.append({"id":direction+date,"mode":"rail","agency":"Snälltåget",
                  "serviceDay":date,"archiveDay":"2026-11-06",
                  "start":1000,"end":36000,"direction":direction,"stops":stops,
                  "throughOrigin":stops[0][2],"throughDestination":stops[-1][2]})
 return base,{"referenceDay":"2026-11-06","templateDay":"2026-11-09",
              "operator":"Snälltåget","trips":source}

class SnalltagetTests(unittest.TestCase):
 def test_real_gtfs_domestic_section_cuts_foreign_origin(self):
  names=["Berlin Hbf","Köpenhamn H","Malmö Centralstation","Lund Centralstation",
         "Linköping Centralstation","Stockholm Centralstation"]
  direction,segment=snall.corridor_segment(timetable(names))
  self.assertEqual(direction,"to-stockholm")
  self.assertEqual(segment[0][1][2],"Malmö Centralstation")
  self.assertEqual(segment[-1][1][2],"Stockholm Centralstation")
 def test_stockholm_to_foreign_destination_is_domestic_section_only(self):
  names=["Stockholm Centralstation","Linköping Centralstation",
         "Malmö Centralstation","Köpenhamn H","Dresden Hbf"]
  direction,segment=snall.corridor_segment(timetable(names))
  self.assertEqual(direction,"to-malmo")
  self.assertEqual([x[1][2] for x in segment],
    ["Stockholm Centralstation","Linköping Centralstation","Malmö Centralstation"])
 def test_wrong_corridor_not_invented(self):
  self.assertIsNone(snall.corridor_segment(timetable(
   ["Malmö Centralstation","Lund Centralstation","Oslo S"])))
 def test_all_existing_train_data_immutable(self):
  before,candidates=fixture()
  copy_before=copy.deepcopy(before)
  result=append.integrate(before,candidates)
  self.assertEqual(result["trips"][:10402],copy_before["trips"])
  self.assertEqual(result["shapes"],copy_before["shapes"])
  self.assertEqual(result["vrDirections"],copy_before["vrDirections"])
  self.assertEqual(result["sjDirections"],copy_before["sjDirections"])
  self.assertEqual(result["malartagDirections"],copy_before["malartagDirections"])
  self.assertEqual(result["counts"]["regional"],432)
  self.assertEqual(result["snalltagetDirections"],{"to-malmo":1,"to-stockholm":1})
  self.assertEqual(result["counts"]["intercity"],71)
 def test_one_direction_blocks_release(self):
  base,candidates=fixture()
  candidates["trips"]=[t for t in candidates["trips"] if t["direction"]=="to-malmo"]
  with self.assertRaisesRegex(ValueError,"both directions"):
   append.integrate(base,candidates)
 def test_no_fake_base(self):
  base,candidates=fixture()
  base["scope"]="not-the-actual-12-systems"
  with self.assertRaises(ValueError):append.integrate(base,candidates)
if __name__=="__main__":unittest.main()
