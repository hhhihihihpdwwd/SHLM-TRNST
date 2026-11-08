import copy
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from append_roslagsbanan import integrate,direction,RELATIONS,verified_match

class RoslagsbananTests(unittest.TestCase):
    def fixture(self):
        shape=[[59.34,18.07],[59.42,18.12],[59.53,18.16]]
        ends={"27":"Kårsta","28":"Österskär","29":"Näsbypark"}
        trips=[]
        for line,end in ends.items():
            for back in (False,True):
                points=list(reversed(shape)) if back else shape
                names=[end,"Roslags Näsby","Stockholms östra"] if back else ["Stockholms östra","Roslags Näsby",end]
                stops=[[p[0],p[1],names[i],i*300,i*300] for i,p in enumerate(points)]
                trips.append({"id":line+("back" if back else "out"),"line":line,
                    "mode":"tram","stops":stops,"shapeId":"stops-approx"})
        base={"scope":"pendeltag-tunnelbana-tvarbanan-localtram-city7",
              "trips":[{"id":"stable-commuter","mode":"commuter"}],
              "shapes":{"previous-track":shape},
              "counts":{"commuter":1,"metro":2,"tram":3},
              "metroLines":{"13":2},"tramLines":{"7":1,"12":1,"21":1,"30":1,"31":1}}
        return base,{"trips":trips},shape

    def test_three_line_endpoints_both_directions_and_immutable_stable(self):
        base,source,shape=self.fixture()
        original=copy.deepcopy(base)
        result=integrate(base,source,lambda line:[("real-osm-"+line,shape)])
        self.assertEqual(result["roslagsLines"],{"27":2,"28":2,"29":2})
        self.assertEqual(result["counts"]["localrail"],6)
        self.assertEqual(result["trips"][:1],original["trips"])
        self.assertEqual(result["shapes"]["previous-track"],shape)
        self.assertEqual(result["tramLines"],original["tramLines"])
        for line in ("27","28","29"):
            self.assertEqual(result["roslagsDirections"][line],{"out":1,"back":1})
        self.assertTrue(all(t["geometryQuality"]=="verified-osm-relation" for t in result["trips"][1:]))

    def test_reject_missing_return_and_missing_complete_branch(self):
        base,source,shape=self.fixture()
        source["trips"]=[t for t in source["trips"] if t["id"]!="28back"]
        with self.assertRaisesRegex(ValueError,"Missing full verified"):
            integrate(base,source,lambda line:[("original",shape)])
        base,source,shape=self.fixture()
        source["trips"][0]["stops"][-1][2]="Unknown middle station"
        with self.assertRaisesRegex(ValueError,"Missing full verified"):
            integrate(base,source,lambda line:[("original",shape)])

    def test_reject_fake_offtrack_route(self):
        base,source,shape=self.fixture()
        displaced=[[p[0]+.2,p[1]+.2] for p in shape]
        with self.assertRaisesRegex(ValueError,"Missing full verified"):
            integrate(base,source,lambda line:[("bad",displaced)])

    def test_only_enebyberg_may_be_roughly_690m_from_osm_route(self):
        shape=[[59.30,18.00],[59.34,18.04],[59.40,18.08]]
        stops=[[59.30,18.00,"Stockholm Östra station",0,0],
               [59.34,18.051,"Enebyberg station",120,120],
               [59.40,18.08,"Roslags Näsby",240,240]]
        self.assertTrue(verified_match(stops,shape))
        wrong=[x.copy() for x in stops]
        wrong[1][2]="Unrelated station"
        self.assertFalse(verified_match(wrong,shape))
        distant=[x.copy() for x in stops]
        distant[1][1]=18.07
        self.assertFalse(verified_match(distant,shape))

    def test_osm_relation_ids_and_terminals(self):
        self.assertEqual(RELATIONS,{"27":11151437,"28":11151439,"29":11151441})
        self.assertEqual(direction("27","Stockholms östra","Kårsta station"),"out")
        self.assertEqual(direction("27","Stockholm Östra station","Kårsta station"),"out")
        self.assertEqual(direction("29","Näsbypark station","Stockholm Östra station"),"back")
        self.assertEqual(direction("27","Ormsta","Stockholms östra"),"back")
        self.assertEqual(direction("27","Lindholmen station","Stockholm Östra station"),"back")
        self.assertEqual(direction("28","Stockholm Östra station","Åkersberga station"),"out")
        self.assertEqual(direction("28","Österskär","Stockholms östra"),"back")
        self.assertEqual(direction("29","Stockholms östra","Näsbypark"),"out")
        self.assertIsNone(direction("29","Roslags Näsby","Näsbypark"))

if __name__=="__main__":unittest.main()
