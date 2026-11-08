import copy
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from append_tunnelbana import append_metro, METRO_LINES, METRO_MASTERS
from build_rail_keyless import mode

class MetroIntegrationTest(unittest.TestCase):
    def setup_dataset(self):
        points=[[59.30,18.00],[59.31,18.01],[59.32,18.02]]
        times=[[p[0],p[1],str(i),i*120,i*120] for i,p in enumerate(points)]
        commuter={"id":"commuter-preserved","mode":"commuter","line":"41",
            "shapeId":"commuter-original","geometryQuality":"verified-osm-relation",
            "destination":"Märsta","stops":times}
        base={"scope":"pendeltag-only","trips":[commuter],
              "shapes":{"commuter-original":points},"counts":{"commuter":1}}
        metro={"trips":[{**commuter,"id":"metro-"+line,"mode":"metro",
            "line":line,"geometryQuality":"approximate-stop-connectors"}
            for line in sorted(METRO_LINES)]}
        return base,metro,points

    def test_seven_lines_merge_and_preserve_commuter_byte_equivalence(self):
        base,metro,points=self.setup_dataset()
        original=copy.deepcopy(base)
        def fake_shapes(line):return [("relation-"+line,points)]
        result=append_metro(base,metro,fake_shapes)
        self.assertEqual(result["counts"],{"commuter":1,"metro":7})
        self.assertEqual(result["trips"][0],original["trips"][0])
        self.assertEqual(result["shapes"]["commuter-original"],original["shapes"]["commuter-original"])
        self.assertEqual(set(result["metroLines"]),METRO_LINES)
        self.assertEqual(set(t["line"] for t in result["trips"][1:]),METRO_LINES)
        self.assertTrue(all(t["geometryQuality"]=="verified-osm-relation" for t in result["trips"]))

    def test_refuse_missing_one_line_without_rewriting_commuter_source(self):
        base,metro,points=self.setup_dataset()
        with self.assertRaisesRegex(ValueError,"Missing verified Tunnelbana"):
            append_metro(base,metro,lambda line:[] if line=="19" else [("r"+line,points)])

    def test_accept_reverse_travel_on_same_verified_rails(self):
        base,metro,points=self.setup_dataset()
        result=append_metro(base,metro,lambda line:[("opposite-osm",list(reversed(points)))])
        self.assertEqual(result["counts"]["metro"],7)
        self.assertEqual(result["metroDirections"]["reversed"],7)
        self.assertTrue(all(t["osmRelation"].endswith(":reverse") for t in result["trips"][1:]))

    def test_reject_off_track_geometry(self):
        base,metro,points=self.setup_dataset()
        distant=[[p[0]+0.2,p[1]+0.2] for p in points]
        with self.assertRaisesRegex(ValueError,"Missing verified Tunnelbana"):
            append_metro(base,metro,lambda line:[("wrong-tracks",distant)])

    def test_gtfs_sverige_metro_classification(self):
        for line in METRO_LINES:
            self.assertEqual(mode("1","SL metro "+line,line,"SL"),"metro")
            self.assertEqual(mode("2","SL regional "+line,line,"SL"),"metro")
        self.assertIsNone(mode("3","Bus 13","13","SL"))
        self.assertEqual(mode("109","Pendeltåg 41","41","SL"),"commuter")

    def test_pinned_real_osm_master_ids(self):
        self.assertEqual(METRO_MASTERS["10"],6286483)
        self.assertEqual(METRO_MASTERS["13"],6286488)
        self.assertEqual(METRO_MASTERS["19"],6286487)

if __name__=="__main__":unittest.main()
