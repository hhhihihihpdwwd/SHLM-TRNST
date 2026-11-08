import copy,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from build_arlanda_candidates import exact_terminal
from append_arlanda_express import integrate,OSM_MASTER

class ExpressTests(unittest.TestCase):
    def fixture(self):
        shape=[[59.33,18.05],[59.62,17.94],[59.65,17.93]]
        terminals=["Stockholm Centralstation","Arlanda Södra/ Arlanda Express","Arlanda Norra/ Arlanda Express"]
        entries=[]
        for reverse in (False,True):
            pts=list(reversed(shape)) if reverse else shape
            names=list(reversed(terminals)) if reverse else terminals
            stops=[[p[0],p[1],names[i],i*300,i*300] for i,p in enumerate(pts)]
            entries.append({"id":"express-"+str(reverse),"agency":"Arlanda Express","mode":"rail","line":"7777",
                            "stops":stops,"shapeId":None})
        base={"scope":"pendeltag-tunnelbana-tvarbanan-localtram-city7-roslags-saltsjo",
            "trips":[{"id":"stable-other-system","mode":"commuter"}],
            "shapes":{"stable-track":shape},
            "counts":{"commuter":1,"metro":1,"tram":1,"localrail":1,"saltsjo":1},
            "metroLines":{"13":1},"tramLines":{"7":1},"roslagsLines":{"27":1},
            "saltsjoLines":{"25":1}}
        return base,{"trips":entries},shape
    def test_exact_three_station_termini_not_arlanda_central(self):
        first=["Stockholm Centralstation","Arlanda Södra/ Arlanda Express","Arlanda Norra/ Arlanda Express"]
        self.assertEqual(exact_terminal([[0,0,s] for s in first]),"to-airport")
        self.assertEqual(exact_terminal([[0,0,s] for s in reversed(first)]),"to-city")
        self.assertIsNone(exact_terminal([[0,0,s] for s in ("Stockholm Centralstation","Arlanda Central","Arlanda Norra/ Arlanda Express")]))
        self.assertIsNone(exact_terminal([[0,0,s] for s in ("Stockholm Centralstation","Arlanda Norra/ Arlanda Express")]))
        self.assertEqual(OSM_MASTER,1966855)
    def test_immutable_stable_and_100_percent_both_directions(self):
        base,archive,shape=self.fixture()
        old=copy.deepcopy(base)
        result=integrate(base,archive,lambda:[("original-OSM",shape)])
        self.assertEqual(result["arlandaDirections"],{"to-airport":1,"to-city":1})
        self.assertEqual(result["trips"][:1],old["trips"])
        self.assertEqual(result["shapes"]["stable-track"],shape)
        for key,value in old["counts"].items():self.assertEqual(result["counts"][key],value)
        self.assertTrue(all(x["vehicleModel"]=="X3" for x in result["trips"][1:]))
    def test_missing_real_rail_or_single_direction_blocks_release(self):
        base,archive,shape=self.fixture()
        far=[[p[0]+.25,p[1]+.25] for p in shape]
        with self.assertRaisesRegex(ValueError,"both directions"):
            integrate(base,archive,lambda:[("wrong",far)])
        base,archive,shape=self.fixture()
        archive["trips"]=archive["trips"][:1]
        with self.assertRaisesRegex(ValueError,"both directions"):
            integrate(base,archive,lambda:[("original",shape)])

if __name__=="__main__":unittest.main()
