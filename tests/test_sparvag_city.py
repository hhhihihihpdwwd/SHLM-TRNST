import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from append_sparvag_city import integrate,route_geometries,terminus,RELATION
from build_sparvag_city_candidates import build_candidates

class City7Tests(unittest.TestCase):
    def fixture(self):
        geom=[[59.33,18.05],[59.32,18.08],[59.31,18.12]]
        base={"scope":"pendeltag-tunnelbana-tvarbanan-localtram",
              "trips":[{"id":"existing-pendeltag","mode":"commuter"},
                       {"id":"existing-metro","mode":"metro"},
                       {"id":"existing-tram","mode":"tram","line":"12"}],
              "shapes":{"existing-rails":geom},
              "counts":{"commuter":1,"metro":1,"tram":1},
              "metroLines":{"13":1},
              "tramLines":{"12":1,"21":1,"30":1,"31":1}}
        trips=[]
        for d in (False,True):
            points=list(reversed(geom)) if d else geom
            names=["Waldemarsudde","Djurgårdsbron","T-Centralen"] if d else ["T-Centralen","Djurgårdsbron","Waldemarsudde"]
            stops=[[p[0],p[1],names[i],i*120,i*120] for i,p in enumerate(points)]
            trips.append({"id":"7-back" if d else "7-out","mode":"tram",
                          "line":"7","stops":stops,"shapeId":"approx-7"})
        return base,{"trips":trips},geom

    def test_both_directions_preserve_stable02_identically(self):
        base,archive,geom=self.fixture()
        old=copy.deepcopy(base)
        result=integrate(base,archive,lambda:[("validated",geom)])
        self.assertEqual(result["city7Directions"],{"out":1,"back":1})
        self.assertEqual(result["tramLines"]["7"],2)
        self.assertEqual(result["trips"][:len(old["trips"])],old["trips"])
        for key in old["shapes"]:self.assertEqual(result["shapes"][key],old["shapes"][key])
        self.assertTrue(all(x["geometryQuality"]=="verified-osm-relation" for x in result["trips"][3:]))
    def test_no_partial_terminal_release(self):
        base,archive,geom=self.fixture()
        archive["trips"]=archive["trips"][:1]
        with self.assertRaisesRegex(ValueError,"BOTH directions"):
            integrate(base,archive,lambda:[("validated",geom)])
    def test_no_distant_osm_route_release(self):
        base,archive,geom=self.fixture()
        wrong=[[p[0]+.3,p[1]+.3] for p in geom]
        with self.assertRaisesRegex(ValueError,"BOTH directions"):
            integrate(base,archive,lambda:[("wrong",wrong)])
    def test_terminal_aliases(self):
        self.assertEqual(terminus("T-Centralen Spårv","Waldemarsudde"),"out")
        self.assertEqual(terminus("Waldemarsudde","Sergels torg"),"back")
        self.assertEqual(terminus("Stockholm Waldemarsudde","T-Centralen Spårv"),"back")
        self.assertEqual(terminus("T-Centralen Spårv","Stockholm Waldemarsudde"),"out")
        self.assertIsNone(terminus("Skansen","T-Centralen"))
    def test_route_master_id(self):
        self.assertEqual(RELATION,2860817)
    def test_master_directional_shapes(self):
        geo={"type":"FeatureCollection","features":[{"geometry":{"type":"LineString",
             "coordinates":[[18.05,59.33],[18.08,59.32],[18.12,59.31]]}}]}
        with patch('append_sparvag_city.read_json',return_value={"routes":[{"id":17,"geojson":geo}]}):
            result=route_geometries(reader=__import__('append_sparvag_city').read_json)
            self.assertEqual(len(result),1)

if __name__=="__main__":unittest.main()
