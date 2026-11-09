"""A single real-GTFS Mälartåg pilot cannot modify the known-good ten-system baseline."""
import copy
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import build_malartag_candidates as candidates
import append_malartag as pilot

STATIONS=("Uppsala Centralstation","Tierp station","Gävle Centralstation")
TRACK=[[59.858,17.650],[60.345,17.519],[60.675,17.150]]

def fixture():
 base={
  "scope":pilot.STABLE_SCOPE,
  "trips":[{"id":"existing-sj-train","mode":"intercity","agency":"SJ"}],
  "shapes":{"existing-verified-rail":[[59.33,18.05],[59.34,18.06]]},
  "counts":{"commuter":10,"metro":10,"tram":10,"localrail":10,
            "saltsjo":10,"express":10,"intercity":56},
  "metroLines":{"13":2},"tramLines":{"21":5},
  "roslagsLines":{"27":2},"saltsjoLines":{"25":2},
  "arlandaDirections":{"to-airport":3,"to-city":3},
  "sjDirections":{"to-goteborg":8,"from-goteborg":11,
                  "to-malmo":20,"from-malmo":17},
  "localTramDirections":{"21":{"out":2,"back":2}}
 }
 trains=[]
 for reverse in (False,True):
  points=list(reversed(TRACK)) if reverse else TRACK
  names=list(reversed(STATIONS)) if reverse else STATIONS
  trains.append({"id":"mtest-"+str(reverse),"mode":"rail","agency":"Mälartåg",
   "corridor":"gavle","line":"gavle","serviceDay":"2026-11-09",
   "stops":[[point[0],point[1],name,i*2400,i*2400]
            for i,(point,name) in enumerate(zip(points,names))]})
 return base,{"trips":trains},lambda corridor,first,last:[("genuine-osm-relation",TRACK)]

class PilotTests(unittest.TestCase):
 def test_only_one_selected_corridor(self):
  self.assertEqual(set(candidates.CORRIDORS),{"gavle"})
  self.assertEqual(set(candidates.SIGNATURES),{"gavle"})
  self.assertEqual(candidates.corridor_for(list(STATIONS)),"gavle")
  self.assertIsNone(candidates.corridor_for(["Stockholm Centralstation","Örebro Centralstation"]))
 def test_two_directions_append_without_mutating_old_train_records(self):
  base,archive,provider=fixture()
  frozen=copy.deepcopy(base)
  result=pilot.integrate(base,archive,provider)
  self.assertEqual(result["scope"],frozen["scope"]+"-malartag")
  self.assertEqual(result["trips"][:len(frozen["trips"])],frozen["trips"])
  self.assertEqual(result["sjDirections"],frozen["sjDirections"])
  self.assertEqual(result["localTramDirections"],frozen["localTramDirections"])
  self.assertEqual(result["shapes"]["existing-verified-rail"],frozen["shapes"]["existing-verified-rail"])
  self.assertEqual(result["malartagDirections"]["gavle"],{"forward":1,"reverse":1})
  self.assertEqual(result["counts"]["regional"],2)
  for key,value in frozen["counts"].items():
   self.assertEqual(result["counts"][key],value)
  self.assertTrue(all(t["geometryQuality"]=="verified-osm-relation"
     for t in result["trips"][len(frozen["trips"]):]))
 def test_missing_direction_and_nonexistent_tracks_cannot_pass(self):
  base,archive,provider=fixture()
  with self.assertRaisesRegex(ValueError,"gavle"):
   pilot.integrate(copy.deepcopy(base),{"trips":archive["trips"][:1]},provider)
  def wrong(corridor,first,last):
   return [("wrong",[[57.5,15.0],[57.6,15.1]])]
  with self.assertRaisesRegex(ValueError,"gavle"):
   pilot.integrate(copy.deepcopy(base),archive,wrong)

if __name__=="__main__":unittest.main()
