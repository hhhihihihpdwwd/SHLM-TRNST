import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import pendeltag_graph as rail

class ActualRailGraphTests(unittest.TestCase):
    def setUp(self):
        self.elements=[
            {"type":"node","id":1,"lat":59.30,"lon":18.000},
            {"type":"node","id":2,"lat":59.301,"lon":18.001},
            {"type":"node","id":3,"lat":59.302,"lon":18.002},
            {"type":"node","id":4,"lat":59.303,"lon":18.003},
            {"type":"way","id":50,"nodes":[1,2,3,4],"tags":{"railway":"rail"}},
        ]
        self.coords,self.graph=rail.graph_from_elements(self.elements)
    def test_path_follows_actual_railway_nodes(self):
        path=rail.shortest_path(1,4,self.graph)
        self.assertEqual(path,[1,2,3,4])
    def test_route_rejects_disconnected_rails(self):
        self.assertIsNone(rail.shortest_path(1,999,self.graph))
    def test_station_times_and_rail_coordinates_required(self):
        t={"id":"pendel","mode":"commuter","start":0,
           "stops":[[59.3,18,"A",0,0],[59.303,18.003,"B",200,200]]}
        good,shapes,errors=rail.reconstruct([t],self.coords,self.graph)
        self.assertEqual(len(good),1)
        self.assertEqual(good[0]["geometryQuality"],"verified-osm-rail-graph")
        points=shapes[good[0]["shapeId"]]
        self.assertEqual(len(points),4)
        self.assertEqual(points[1],[59.301,18.001])
        impossible={"id":"disconnected","mode":"commuter","stops":[[59.3,18,"A",0,0],[59.45,18.5,"Far",100,100]]}
        rejected,_,failures=rail.reconstruct([impossible],self.coords,self.graph)
        self.assertEqual(rejected,[])
        self.assertGreater(failures["stop_far_from_track"],0)
if __name__=="__main__":unittest.main()
