"""Five-corridor Mälartåg geometry regression; cannot alter 10-system production baseline."""
import copy
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import build_malartag_candidates as candidates
import append_malartag as mal

def sample():
 base={"scope":mal.STABLE_SCOPE,
       "trips":[{"id":"protected-sj","mode":"intercity","agency":"SJ"}],
       "shapes":{"protected-track":[[59.34,18.0],[59.35,18.01]]},
       "counts":{"metro":100,"commuter":100,"tram":100,"localrail":100,
                 "saltsjo":100,"express":100,"intercity":56},
       "metroLines":{"13":40},"tramLines":{"21":80},
       "roslagsLines":{"27":40},"saltsjoLines":{"25":40},
       "arlandaDirections":{"to-airport":20,"to-city":20},
       "sjDirections":{"to-goteborg":8,"from-goteborg":11,"to-malmo":20,"from-malmo":17},
       "localTramDirections":{"21":{"out":20,"back":20}}}
 archive=[]
 geometry={}
 for index,(key,names) in enumerate(candidates.CORRIDORS.items()):
  points=[[58+index*.4+i*.05,16+index*.25+i*.03] for i in range(len(names))]
  geometry[key]=points
  for reversed_dir in (False,True):
   line=list(reversed(points)) if reversed_dir else points
   stops=list(reversed(names)) if reversed_dir else names
   archive.append({"id":key+str(reversed_dir),"corridor":key,"agency":"Mälartåg",
    "mode":"rail","stops":[[p[0],p[1],name,i*600,i*600]
        for i,(p,name) in enumerate(zip(line,stops))]})
 def reader(corridor,first,last):return [(corridor,geometry[corridor])]
 return base,{"trips":archive},reader

class MalartagFullRegression(unittest.TestCase):
 def test_all_five_distinct_historical_corridors(self):
  self.assertEqual(set(candidates.CORRIDORS),{"orebro-uppsala","nykoping","hallsberg","uven","gavle"})
  self.assertEqual(set(candidates.SIGNATURES),set(candidates.CORRIDORS))
  self.assertEqual(candidates.corridor_for(["Uppsala Centralstation","Tierp station","Gävle Centralstation"]),"gavle")
  self.assertEqual(candidates.corridor_for(["Stockholm Centralstation","Katrineholm Centralstation","Hallsberg station"]),"hallsberg")
 def test_all_corridors_both_directions_no_mutation(self):
  base,archive,reader=sample()
  old=copy.deepcopy(base)
  result=mal.integrate(base,archive,reader)
  self.assertEqual(result["trips"][:len(old["trips"])],old["trips"])
  self.assertEqual(result["shapes"]["protected-track"],old["shapes"]["protected-track"])
  self.assertEqual(result["sjDirections"],old["sjDirections"])
  self.assertEqual(result["localTramDirections"],old["localTramDirections"])
  for k,v in old["counts"].items():self.assertEqual(result["counts"][k],v)
  self.assertEqual(result["counts"]["regional"],10)
  for corridor in candidates.CORRIDORS:
   self.assertEqual(result["malartagDirections"][corridor],{"forward":1,"reverse":1})
  for t in result["trips"][len(old["trips"]):]:
   self.assertEqual(t["geometryQuality"],"verified-osm-relation")
 def test_missing_hallsberg_reverse_blocks_publication(self):
  base,archive,reader=sample()
  archive["trips"]=[t for t in archive["trips"] if t["id"]!="hallsbergTrue"]
  with self.assertRaisesRegex(ValueError,"hallsberg"):
   mal.integrate(base,archive,reader)
 def test_incorrect_nykoping_track_blocks_publication(self):
  base,archive,reader=sample()
  def wrong(corridor,first,last):
   if corridor=="nykoping":return [("wrong",[[60.7,19.2],[60.8,19.3]])]
   return reader(corridor,first,last)
  with self.assertRaisesRegex(ValueError,"nykoping"):
   mal.integrate(base,archive,wrong)
 def test_whole_place_name_not_substring(self):
  self.assertFalse(mal.corridor_relation_match("orebro-uppsala",{"name":"Nyköping - Norrköping"}))
  self.assertTrue(mal.corridor_relation_match("orebro-uppsala",{"name":"Örebro - Arboga"}))
  self.assertFalse(mal.corridor_relation_match("hallsberg",{"name":"Göteborg - Skövde"}))

if __name__=="__main__":unittest.main()
