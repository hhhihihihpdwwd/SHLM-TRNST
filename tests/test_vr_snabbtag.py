"""Tests VR 2026-11-06 real-operator timetable, OSM matching and 11-system immutability."""
import copy
import datetime as dt
import io
import sys
import unittest
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import build_vr_candidates as vr
import append_vr_rail as append

def fixture_archive():
 memory=io.BytesIO()
 with zipfile.ZipFile(memory,"w") as z:
  z.writestr("agency.txt","agency_id,agency_name\n812,VR Snabbtåg\n99,SJ\n")
  z.writestr("routes.txt","route_id,agency_id,route_short_name,route_long_name,route_type\nVR,812,2021,VR Snabbtåg,101\nSJ,99,100,SJ 100,101\n")
  z.writestr("calendar.txt","service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\nF,0,0,0,0,1,0,0,20261104,20261110\n")
  z.writestr("stops.txt","stop_id,stop_name,stop_lat,stop_lon\nA,Stockholm Centralstation,59.33,18.05\nB,Katrineholm Centralstation,58.997,16.208\nC,Göteborg Centralstation,57.71,11.97\nD,Solna station,59.36,18.01\n")
  z.writestr("trips.txt","trip_id,route_id,service_id,trip_headsign\nv-out,VR,F,Göteborg Centralstation\nv-back,VR,F,Stockholm Centralstation\nv-solna,VR,F,Göteborg Centralstation\ns-not-vr,SJ,F,Göteborg Centralstation\n")
  z.writestr("stop_times.txt","trip_id,arrival_time,departure_time,stop_id,stop_sequence\nv-out,06:51:00,06:51:00,A,1\nv-out,08:00:00,08:02:00,B,2\nv-out,10:35:00,10:35:00,C,3\nv-back,10:50:00,10:50:00,C,1\nv-back,12:55:00,12:57:00,B,2\nv-back,14:24:00,14:24:00,A,3\nv-solna,07:00:00,07:00:00,D,1\nv-solna,08:00:00,08:02:00,B,2\nv-solna,10:30:00,10:30:00,C,3\ns-not-vr,07:00:00,07:00:00,A,1\ns-not-vr,08:00:00,08:02:00,B,2\ns-not-vr,10:30:00,10:30:00,C,3\n")
 memory.seek(0)
 return zipfile.ZipFile(memory)

def sample_integrate():
 forward=[[59+i*.01,17+i*.003] for i in range(40)]
 reverse=list(reversed(forward))
 first,middle,last=forward[0],forward[20],forward[-1]
 base={
  "scope":append.BASE_SCOPE,
  "type":"historical-daily-repeating-simulation",
  "simulationTemplateDay":"2026-11-09",
  "trips":[{"id":"protected-existing-SJ","mode":"intercity","agency":"SJ"}],
  "shapes":{"sj-osm:21493221:reverse":forward,"sj-osm:21493220:reverse":reverse,
            "protected-other-rail":[[59.3,18.0],[59.4,18.1]]},
  "counts":{"intercity":56,"commuter":200,"metro":500,"regional":432,"tram":400},
  "sjDirections":{"to-goteborg":8,"from-goteborg":11,"to-malmo":20,"from-malmo":17},
  "malartagDirections":{"orebro-uppsala":{"forward":54,"reverse":51},
    "nykoping":{"forward":63,"reverse":57},"uven":{"forward":105,"reverse":102}},
  "tramLines":{"21":390},
 }
 source=[]
 for day in ("2026-11-08","2026-11-09","2026-11-10"):
  for direction,points in (("to-goteborg",[first,middle,last]),
                            ("to-stockholm",[last,middle,first])):
   source.append({"id":direction+":"+day,"agency":"VR Snabbtåg",
       "direction":direction,"mode":"rail","serviceDay":day,"archiveDay":"2026-11-06",
       "start":1000,"end":36000,"stops":[[p[0],p[1],name,i*2000,i*2000]
           for i,(p,name) in enumerate(zip(points,("Start","Middle","End")))]})
 return base,{"operator":"VR Snabbtåg","referenceDay":"2026-11-06",
               "templateDay":"2026-11-09","trips":source}

class VrSourceTests(unittest.TestCase):
 def test_only_genuine_vr_agency_and_two_terminal_directions(self):
  with fixture_archive() as z:d=vr.build(z,dt.date(2026,11,9))
  self.assertEqual(d["counts"],{"to-goteborg":3,"to-stockholm":3})
  self.assertEqual(len(d["trips"]),6)
  self.assertEqual({x["serviceDay"] for x in d["trips"]},
     {"2026-11-08","2026-11-09","2026-11-10"})
  self.assertEqual({x["archiveDay"] for x in d["trips"]},{"2026-11-06"})
  self.assertTrue(all(x["agency"]=="VR Snabbtåg" and
                      len(x["stops"])==3 and x["geometryQuality"]=="awaiting-verified-OSM"
                      for x in d["trips"]))
  self.assertNotIn("v-solna",str([x["id"] for x in d["trips"]]))
  self.assertNotIn("s-not-vr",str([x["id"] for x in d["trips"]]))

 def test_verified_osm_both_directions_preserves_every_old_trip_and_shape(self):
  baseline,candidates=sample_integrate()
  frozen=copy.deepcopy(baseline)
  result=append.integrate(baseline,candidates)
  self.assertEqual(result["scope"],append.BASE_SCOPE+"-vr")
  self.assertEqual(result["trips"][:len(frozen["trips"])],frozen["trips"])
  self.assertEqual(result["shapes"],frozen["shapes"])
  self.assertEqual(result["malartagDirections"],frozen["malartagDirections"])
  self.assertEqual(result["sjDirections"],frozen["sjDirections"])
  self.assertEqual(result["counts"]["intercity"],58)
  self.assertEqual(result["counts"]["regional"],432)
  self.assertEqual(result["vrDirections"],{"to-goteborg":1,"to-stockholm":1})
  for t in result["trips"][len(frozen["trips"]):]:
   self.assertEqual(t["geometryQuality"],"verified-osm-relation")
   self.assertIn(t["shapeId"],frozen["shapes"])

 def test_unmatched_vr_rail_direction_cannot_publish(self):
  baseline,candidates=sample_integrate()
  candidates["trips"]=[x for x in candidates["trips"] if x["direction"]=="to-goteborg"]
  with self.assertRaisesRegex(ValueError,"both directions"):
   append.integrate(baseline,candidates)

 def test_no_unverified_source_or_wrong_baseline(self):
  baseline,candidates=sample_integrate()
  baseline["scope"]="old-ten-systems"
  with self.assertRaises(ValueError):append.integrate(baseline,candidates)
  baseline,candidates=sample_integrate()
  candidates["referenceDay"]="2026-11-07"
  with self.assertRaises(ValueError):append.integrate(baseline,candidates)

if __name__=="__main__":unittest.main()
