import copy
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from append_tvarbanan import integrate, route_shapes, TVARBANAN
from unittest.mock import patch

class TvärbananIntegrationTests(unittest.TestCase):
    def fixture(self):
        coords=[[59.30,18.00],[59.31,18.01],[59.32,18.02]]
        stops=[[p[0],p[1],f'Station {i}',i*180,i*180] for i,p in enumerate(coords)]
        base={"scope":"pendeltag-and-tunnelbana","trips":[
           {"id":"pendeltag","mode":"commuter","line":"41","shapeId":"pendel-shape"},
           {"id":"tunnelbana","mode":"metro","line":"13","shapeId":"metro-shape"}],
           "shapes":{"pendel-shape":coords,"metro-shape":coords},
           "counts":{"commuter":1,"metro":1},"metroLines":{"13":1}}
        archive={"trips":[{"id":"tram-"+line,"mode":"tram","line":line,"stops":stops,
                  "shapeId":"approx:"+line} for line in sorted(TVARBANAN)]}
        return base,archive,coords

    def test_two_verified_lines_preserve_previous_services_unchanged(self):
        base,archive,coords=self.fixture()
        original=copy.deepcopy(base)
        output=integrate(base,archive,lambda line:[(line+"-route",coords)])
        self.assertEqual(output["scope"],"pendeltag-tunnelbana-tvarbanan")
        self.assertEqual(output["counts"]["tram"],2)
        self.assertEqual(output["tramLines"],{"30":1,"31":1})
        self.assertEqual(output["trips"][:2],original["trips"])
        for name in original["shapes"]:
            self.assertEqual(output["shapes"][name],original["shapes"][name])
        self.assertEqual(output["metroLines"],original["metroLines"])
        self.assertTrue(all(t["geometryQuality"]=="verified-osm-relation"
                            for t in output["trips"][2:]))

    def test_missing_line_31_refuses_incomplete_release(self):
        base,archive,coords=self.fixture()
        with self.assertRaisesRegex(ValueError,"31"):
            integrate(base,archive,lambda line:[] if line=="31" else [("good",coords)])

    def test_reverse_direction_is_rejected(self):
        base,archive,coords=self.fixture()
        with self.assertRaisesRegex(ValueError,"Missing verified"):
            integrate(base,archive,lambda line:[("reverse",list(reversed(coords)))])

    def test_other_trams_are_not_imported(self):
        base,archive,coords=self.fixture()
        archive["trips"].append({**archive["trips"][0],"id":"other","line":"12"})
        output=integrate(base,archive,lambda line:[("good",coords)])
        self.assertEqual(len(output["trips"]),4)

    def test_documented_osm_relation_ids(self):
        self.assertEqual(TVARBANAN,{"30":241384,"31":11997852})

    def test_osm_route_master_and_direct_fallback(self):
        coords=[[18.00,59.30],[18.01,59.31],[18.02,59.32]]
        geometry={"type":"FeatureCollection","features":[{
            "geometry":{"type":"LineString","coordinates":coords}}]}
        with patch('append_tvarbanan.read_json',return_value={
            "routes":[{"id":123,"geojson":geometry}]}):
            result=route_shapes("30",reader=__import__('append_tvarbanan').read_json)
            self.assertEqual(result[0][1][0],[59.30,18.00])

if __name__=="__main__":unittest.main()
