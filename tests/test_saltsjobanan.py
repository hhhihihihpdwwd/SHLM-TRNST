import copy,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from append_saltsjobanan import integrate,direction,RELATIONS

class SaltsjoTests(unittest.TestCase):
    def fixture(self):
        g=[[59.30,18.20],[59.29,18.24],[59.28,18.29]]
        names={"25":["Saltsjö-Järla","Igelboda","Saltsjöbaden"],
               "26":["Igelboda","Tippen","Solsidan"]}
        trips=[]
        for line,labels in names.items():
            for reverse in (False,True):
                coords=list(reversed(g)) if reverse else g
                stations=list(reversed(labels)) if reverse else labels
                stops=[[p[0],p[1],stations[i],i*120,i*120] for i,p in enumerate(coords)]
                trips.append({"id":line+str(reverse),"mode":"tram","line":line,
                    "stops":stops,"shapeId":"approx"})
        base={"scope":"pendeltag-tunnelbana-tvarbanan-localtram-city7-roslags",
              "trips":[{"id":"existing","mode":"commuter"}],
              "shapes":{"stable":g},"counts":{"commuter":1,"metro":2,"tram":3,"localrail":4},
              "tramLines":{"7":1},"roslagsLines":{"27":1,"28":1,"29":1},
              "metroLines":{"13":1}}
        return base,{"trips":trips},g
    def test_full_termini_two_lines_both_directions_and_stable_unchanged(self):
        base,source,geometry=self.fixture()
        old=copy.deepcopy(base)
        result=integrate(base,source,lambda line:[("relation-"+line,geometry)])
        self.assertEqual(result["saltsjoDirections"]["25"],{"out":1,"back":1})
        self.assertEqual(result["saltsjoDirections"]["26"],{"out":1,"back":1})
        self.assertEqual(result["counts"]["saltsjo"],4)
        self.assertEqual(result["trips"][:len(old["trips"])],old["trips"])
        for key,v in old["shapes"].items():self.assertEqual(result["shapes"][key],v)
        for key,v in old["counts"].items():self.assertEqual(result["counts"][key],v)
        self.assertTrue(all(x["geometryQuality"]=="verified-osm-relation" for x in result["trips"][1:]))
    def test_refuses_missing_return_direction(self):
        base,source,g=self.fixture()
        source["trips"]=[t for t in source["trips"] if t["line"]!="26" or t["id"]=="26False"]
        with self.assertRaisesRegex(ValueError,"Missing complete verified"):
            integrate(base,source,lambda line:[("rel",g)])
    def test_refuses_offrail_geometry(self):
        base,source,g=self.fixture()
        displaced=[[p[0]+.3,p[1]+.3] for p in g]
        with self.assertRaisesRegex(ValueError,"Missing complete verified"):
            integrate(base,source,lambda line:[("wrong",displaced)])
    def test_rejects_old_slussen_service_and_bus_substitutes(self):
        self.assertIsNone(direction("25","Slussen","Saltsjöbaden"))
        self.assertIsNone(direction("26","Slussen","Solsidan"))
        self.assertEqual(direction("25","Saltsjö-Järla station","Saltsjöbaden station"),"out")
        self.assertEqual(direction("26","Solsidan station","Igelboda station"),"back")
        self.assertEqual(RELATIONS,{"25":2705957,"26":2705952})
if __name__=="__main__":unittest.main()
