import copy
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from build_malartag_candidates import CORRIDORS,corridor_for
from append_malartag import integrate,direction_of,STABLE_SCOPE

class MalartagTests(unittest.TestCase):
 def make_fixture(self):
  data={"scope":STABLE_SCOPE,"trips":[{"id":"stable06-original"}],
    "shapes":{"old":[[59.3,18.0],[59.4,18.1]]},
    "counts":{"commuter":1,"metro":1,"tram":1,"localrail":1,"saltsjo":1,"express":1},
    "metroLines":{"13":1},"tramLines":{"7":1},
    "roslagsLines":{"27":1},"saltsjoLines":{"25":1},
    "arlandaDirections":{"to-airport":1,"to-city":1}}
  entries=[]
  shape={}
  for j,(key,names) in enumerate(CORRIDORS.items()):
   forward=[[58.1+j*.22+i*.012,16.0+j*.1+i*.008] for i in range(len(names))]
   shape[key]=forward
   for reverse in (False,True):
    coords=list(reversed(forward)) if reverse else forward
    labels=list(reversed(names)) if reverse else list(names)
    entries.append({"id":key+str(reverse),"corridor":key,"agency":"Mälartåg",
      "mode":"rail","stops":[[p[0],p[1],label,i*600,i*600] for i,(p,label) in enumerate(zip(coords,labels))]})
  def provider(corridor,first,last):return [(corridor,shape[corridor])]
  return data,{"trips":entries},provider
 def test_immutable_nine_systems_and_all_five_directions(self):
  base,archive,provider=self.make_fixture()
  old=copy.deepcopy(base)
  result=integrate(base,archive,provider)
  self.assertEqual(result["trips"][:1],old["trips"])
  self.assertEqual(result["shapes"]["old"],old["shapes"]["old"])
  for key in old["counts"]:self.assertEqual(result["counts"][key],old["counts"][key])
  for corridor in CORRIDORS:
   self.assertEqual(result["malartagDirections"][corridor],{"forward":1,"reverse":1})
  self.assertEqual(result["counts"]["regional"],10)
 def test_absent_direction_blocks_release(self):
  base,archive,provider=self.make_fixture()
  archive["trips"]=[v for v in archive["trips"] if v["id"]!="gavleTrue"]
  with self.assertRaisesRegex(ValueError,"gavle"):
   integrate(base,archive,provider)
 def test_unrelated_track_blocks_release(self):
  base,archive,provider=self.make_fixture()
  def wrong(corridor,first,last):
   if corridor=="uven":return [("unrelated",[[61.1,19.1],[61.2,19.2]])]
   return provider(corridor,first,last)
  with self.assertRaisesRegex(ValueError,"uven"):
   integrate(base,archive,wrong)
 def test_direction(self):
  base,archive,provider=self.make_fixture()
  self.assertEqual(direction_of(archive["trips"][0]),"forward")
  self.assertEqual(direction_of(archive["trips"][1]),"reverse")
if __name__=="__main__":unittest.main()
