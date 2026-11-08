import unittest
from unittest.mock import patch
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from build_rail_keyless import mode
from refine_osm_routes import project_stops, pinned_pendeltag_shapes, PENDELTAG_OSM_RELATIONS, choose_directional_shape

class RailPolishTests(unittest.TestCase):
    def test_tvarbanan_light_rail_is_tram(self):
        self.assertEqual(mode("2","Tvärbanan", "30","SL"),"tram")
        self.assertEqual(mode("2","Spårväg City", "7","SL"),"tram")
        self.assertEqual(mode("2","Nockebybanan", "12","SL"),"tram")
        self.assertEqual(mode("2","Lidingöbanan", "21","SL"),"tram")
        self.assertEqual(mode("3","City bus 7", "7","SL"),None)
        self.assertEqual(mode("1","Tunnelbana 13", "13","SL"),"metro")
    def test_pinned_pendeltag_relation_inventory(self):
        self.assertEqual(PENDELTAG_OSM_RELATIONS["41"],241413)
        self.assertEqual(PENDELTAG_OSM_RELATIONS["43"],241411)
        self.assertEqual(PENDELTAG_OSM_RELATIONS["48"],241414)

    def test_route_master_geometry_and_direct_route_fallback(self):
        poly={"type":"FeatureCollection","features":[{"type":"Feature","geometry":{
            "type":"LineString","coordinates":[[18.01,59.32],[18.02,59.33],[18.03,59.34]]}}]}
        master={"routes":[{"id":212,"geojson":poly},{"id":213,"geojson":poly}]}
        with patch("refine_osm_routes.read_json",return_value=master) as fetch:
            results=pinned_pendeltag_shapes("41")
        self.assertEqual(len(results),2)
        self.assertEqual(results[0][1][0],[59.32,18.01])
        self.assertIn("route_master/241413",fetch.call_args.args[0])
        with patch("refine_osm_routes.read_json",side_effect=[
            ValueError("master absent"),{"geojson":poly}
        ]):
            direct=pinned_pendeltag_shapes("43")
        self.assertEqual(len(direct),1)

    def test_osm_reverse_direction_uses_original_track_vertices(self):
        shape=[[59.30,18.00],[59.31,18.01],[59.32,18.02]]
        returning=[[59.32,18.02,"C",0,0],[59.31,18.01,"B",100,100],[59.30,18.00,"A",200,200]]
        original=[[59.30,18.00,"A",0,0],[59.31,18.01,"B",100,100],[59.32,18.02,"C",200,200]]
        self.assertEqual(choose_directional_shape(original,[("123",shape)],80)[0],"123")
        backwards=choose_directional_shape(returning,[("123",shape)],80)
        self.assertEqual(backwards[0],"123:reverse")
        self.assertEqual(backwards[1],list(reversed(shape)))
        self.assertIsNotNone(project_stops(returning,backwards[1],80))

    def test_osm_route_accepts_correct_stop_alignment(self):
        shape=[[59.30,18.00],[59.31,18.01],[59.32,18.02]]
        stops=[[59.30,18.00,"A",0,0],[59.31,18.01,"B",10,10],[59.32,18.02,"C",20,20]]
        self.assertIsNotNone(project_stops(stops,shape,80))
    def test_osm_route_rejects_distant_or_reverse_stops(self):
        shape=[[59.30,18.00],[59.31,18.01],[59.32,18.02]]
        far=[[59.30,18.00],[59.31,19.01],[59.32,18.02]]
        reversed_stops=[[59.32,18.02],[59.31,18.01],[59.30,18.00]]
        self.assertIsNone(project_stops(far,shape,150))
        self.assertIsNone(project_stops(reversed_stops,shape,150))

if __name__=="__main__":unittest.main()
