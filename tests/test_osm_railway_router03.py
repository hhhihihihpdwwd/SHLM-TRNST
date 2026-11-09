"""Railway-way graph must never join unrelated tracks or invent rail connections."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import osm_railway_way_router as router

def make_rail(nodes,base_id=9000):
 coords=[{"lat":p[0],"lon":p[1]} for p in nodes]
 return {"type":"way","id":base_id,"nodes":[base_id*1000+i for i in range(len(nodes))],
         "geometry":coords,"tags":{"railway":"rail","usage":"main"}}

def route_data():
 points=[[59+i*.001,17+i*.0003] for i in range(121)]
 stops=[
  [*points[0],"A",0,0],
  [*points[60],"B",4800,4800],
  [*points[120],"C",9600,9600],
 ]
 return points,stops

class OsmRailGraphTests(unittest.TestCase):
 def test_true_osm_nodes_only_and_all_gtfs_stations_in_order(self):
  points,stops=route_data()
  way=make_rail(points)
  shape=router.route_osm_ways(stops,downloader=lambda area:[way])
  self.assertGreater(len(shape),90)
  self.assertEqual(shape[0],points[0])
  self.assertEqual(shape[-1],points[-1])
  self.assertTrue(all(p in points for p in shape))
  self.assertTrue(all(p[0]<=q[0] for p,q in zip(shape,shape[1:])))
 def test_disconnected_crossing_rail_segments_must_not_join(self):
  points,stops=route_data()
  one=make_rail(points[:61],100)
  two=make_rail(points[60:],200)
  # Both ways touch exactly at B in space but have distinct OSM node IDs,
  # so there is NO legal railway junction.
  with self.assertRaisesRegex(ValueError,"No connected OSM rails"):
   router.route_osm_ways(stops,downloader=lambda area:[one,two])
 def test_station_not_on_real_rail_is_rejected(self):
  points,stops=route_data()
  stops[1][0]=60.0
  with self.assertRaisesRegex(ValueError,"No OSM rail nodes"):
   router.route_osm_ways(stops,downloader=lambda area:[make_rail(points)])

if __name__=="__main__":unittest.main()
