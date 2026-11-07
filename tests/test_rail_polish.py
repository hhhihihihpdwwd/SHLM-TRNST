import unittest
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from build_rail_keyless import mode
from refine_osm_routes import project_stops

class RailPolishTests(unittest.TestCase):
    def test_tvarbanan_light_rail_is_tram(self):
        self.assertEqual(mode("2","Tvärbanan", "30","SL"),"tram")
        self.assertEqual(mode("2","Spårväg City", "7","SL"),"tram")
        self.assertEqual(mode("2","Nockebybanan", "12","SL"),"tram")
        self.assertEqual(mode("2","Lidingöbanan", "21","SL"),"tram")
        self.assertEqual(mode("3","City bus 7", "7","SL"),None)
        self.assertEqual(mode("1","Tunnelbana 13", "13","SL"),"metro")
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
