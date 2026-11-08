import copy
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from append_local_trams import integrate,LINE_RELATIONS,terminus_direction

class LocalTramsTests(unittest.TestCase):
    def fixture(self):
        geometry=[[59.30,18.00],[59.31,18.01],[59.32,18.02]]
        names={"12":["Alvik","Alléparken","Nockeby"],
               "21":["Ropsten","Baggeby","Gåshaga brygga"]}
        trips=[]
        for line in ("12","21"):
            for backward in (False,True):
                g=list(reversed(geometry)) if backward else geometry
                labels=list(reversed(names[line])) if backward else names[line]
                stops=[[p[0],p[1],labels[i],i*120,i*120] for i,p in enumerate(g)]
                trips.append({"id":line+("B" if backward else "A"),"mode":"tram",
                              "line":line,"stops":stops,"shapeId":"old:"+line})
        base={"schema":1,"scope":"pendeltag-tunnelbana-tvarbanan",
              "trips":[{"id":"old41","mode":"commuter"},{"id":"old13","mode":"metro"},
                       {"id":"old30","mode":"tram","line":"30"}],
              "shapes":{"old-rail":geometry},
              "counts":{"commuter":1,"metro":1,"tram":1},
              "tramLines":{"30":1,"31":1},"metroLines":{"13":1}}
        return base,{"trips":trips},geometry

    def test_preserves_entire_old_dataset_and_adds_both_lines_both_directions(self):
        base,archive,geom=self.fixture()
        old=copy.deepcopy(base)
        result=integrate(base,archive,lambda line:[("relation-"+line,geom)])
        self.assertEqual(result["scope"],"pendeltag-tunnelbana-tvarbanan-localtram")
        self.assertEqual(result["counts"],{"commuter":1,"metro":1,"tram":5})
        self.assertEqual(result["tramLines"],{"30":1,"31":1,"12":2,"21":2})
        self.assertEqual(result["trips"][:len(old["trips"])],old["trips"])
        self.assertEqual(result["shapes"]["old-rail"],old["shapes"]["old-rail"])
        self.assertEqual(result["localTramDirections"]["12"],{"out":1,"back":1})
        self.assertEqual(result["localTramDirections"]["21"],{"out":1,"back":1})
        self.assertTrue(all(t["geometryQuality"]=="verified-osm-relation"
                            for t in result["trips"][len(old["trips"]):]))

    def test_missing_return_direction_refuses_publish(self):
        base,archive,geom=self.fixture()
        archive["trips"]=[t for t in archive["trips"] if not t["id"].endswith("B")]
        with self.assertRaisesRegex(ValueError,"both directions"):
            integrate(base,archive,lambda line:[("relation-"+line,geom)])

    def test_wrong_track_does_not_pass(self):
        base,archive,geom=self.fixture()
        other=[[p[0]+0.25,p[1]+0.25] for p in geom]
        with self.assertRaisesRegex(ValueError,"both directions"):
            integrate(base,archive,lambda line:[("wrong",other)])

    def test_terminal_patterns_strict(self):
        self.assertEqual(terminus_direction("12","Alvik","Nockeby"),"out")
        self.assertEqual(terminus_direction("21","Gåshaga brygga","Ropsten"),"back")
        self.assertIsNone(terminus_direction("12","Alvik","Alléparken"))

    def test_osm_relations_verified_by_wiki(self):
        self.assertEqual(LINE_RELATIONS,{"12":241383,"21":7779520})

if __name__=="__main__":
    unittest.main()
