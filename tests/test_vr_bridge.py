"""No bridge to VR west rail is legal unless real OSM node IDs connect exactly."""
import copy
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import build_vr_real_osm_bridge as bridge

PREFIX=[[59+i*.001,17+i*.001] for i in range(51)]
TRACK=[[59.05+i*.001,17.05+i*.001] for i in range(51)]
SUFFIX=[[59.10+i*.001,17.10+i*.001] for i in range(51)]

def sample(disconnect=False):
 rail_nodes={1000+i:p for i,p in enumerate(TRACK)}
 edges={nid:{} for nid in rail_nodes}
 for i in range(50):
  if disconnect and i==25:continue
  a,b=1000+i,1001+i
  edges[a][b]=160
  edges[b][a]=160
 data={"scope":"pendeltag-tunnelbana-tvarbanan-localtram-city7-roslags-saltsjo-arlanda-sj-malartag",
       "simulationTemplateDay":"2026-11-09",
       "shapes":{bridge.STOCKHOLM_MALMO:copy.deepcopy(PREFIX),
                 bridge.STOCKHOLM_GOTEBORG:copy.deepcopy(SUFFIX)}}
 trains=[]
 for direction in ("to-goteborg","to-stockholm"):
  stop_points=([PREFIX[0],PREFIX[-1],SUFFIX[0],SUFFIX[-1]]
          if direction=="to-goteborg" else
          [SUFFIX[-1],SUFFIX[0],PREFIX[-1],PREFIX[0]])
  stops=(["Stockholm Centralstation","Katrineholm Centralstation",
          "Hallsberg station","Göteborg Centralstation"]
         if direction=="to-goteborg" else
         ["Göteborg Centralstation","Hallsberg station",
          "Katrineholm Centralstation","Stockholm Centralstation"])
  for i in range(3):
   trains.append({"id":direction+str(i),"direction":direction,
      "serviceDay":"2026-11-09",
      "stops":[[p[0],p[1],name,n*3600,n*3600]
               for n,(p,name) in enumerate(zip(stop_points,stops))]})
 return data,{"trips":trains},lambda coords:(rail_nodes,edges)

class VrBridgeTests(unittest.TestCase):
 def test_real_osm_node_bridge_joins_only_at_identical_existing_vertices(self):
  original,candidates,graph=sample()
  result=bridge.build(original,candidates,network_builder=graph)
  self.assertTrue(result["osmWayNetwork"])
  self.assertEqual(result["sourceNodeId"],1000)
  self.assertEqual(result["targetNodeId"],1050)
  self.assertEqual(result["shape"][0],PREFIX[0])
  self.assertEqual(result["shape"][-1],SUFFIX[-1])
  self.assertGreater(len(result["shape"]),100)
  self.assertEqual(result["bridgeNodeCount"],51)
 def test_unconnected_osm_rail_nodes_must_never_be_joined_by_a_line(self):
  original,candidates,graph=sample(disconnect=True)
  with self.assertRaisesRegex(ValueError,"No physical OSM railway"):
   bridge.build(original,candidates,network_builder=graph)
 def test_missing_genuine_shared_station_nodes_rejected(self):
  original,candidates,graph=sample()
  original["shapes"][bridge.STOCKHOLM_MALMO][-1]=[58.0,15.0]
  # The still-existing prior vertex means first junction may be found. Remove
  # every shape vertex near the real station to force fail-closed.
  original["shapes"][bridge.STOCKHOLM_MALMO]=[[58+i*.001,15+i*.001] for i in range(51)]
  with self.assertRaisesRegex(ValueError,"No original real OSM track nodes"):
   bridge.build(original,candidates,network_builder=graph)

if __name__=="__main__":unittest.main()
