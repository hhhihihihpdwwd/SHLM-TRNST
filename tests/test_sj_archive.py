"""SJ test fixtures: authentic timetable shape, both directions, no invented trains."""
import datetime as dt
import io
import sys
import unittest
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import build_sj_candidates as sj

def archive():
 buffer=io.BytesIO()
 with zipfile.ZipFile(buffer,"w") as z:
  z.writestr("agency.txt","agency_id,agency_name\nsj,SJ\n")
  z.writestr("routes.txt","route_id,agency_id,route_short_name,route_long_name,route_type\nr,sj,400,Stockholm Göteborg,2\n")
  z.writestr("calendar.txt","service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\ns,0,0,0,0,1,0,0,20261104,20261110\n")
  z.writestr("stops.txt","stop_id,stop_name,stop_lat,stop_lon\na,Stockholm Centralstation,59.33,18.05\nb,Södertälje Syd station,59.20,17.65\nc,Göteborg Centralstation,57.71,11.97\n")
  z.writestr("trips.txt","trip_id,route_id,service_id,trip_headsign\nout,r,s,Göteborg Centralstation\nback,r,s,Stockholm Centralstation\n")
  z.writestr("stop_times.txt","trip_id,arrival_time,departure_time,stop_id,stop_sequence\nout,10:00:00,10:00:00,a,1\nout,10:20:00,10:21:00,b,2\nout,12:50:00,12:50:00,c,3\nback,13:00:00,13:00:00,c,1\nback,15:10:00,15:11:00,b,2\nback,15:40:00,15:40:00,a,3\n")
 buffer.seek(0)
 return zipfile.ZipFile(buffer)

class SjTests(unittest.TestCase):
 def test_goteborg_full_route_both_directions(self):
  self.assertEqual(sj.direction(["Stockholm Centralstation","Södertälje Syd station","Göteborg Centralstation"]),"to-goteborg")
  self.assertEqual(sj.direction(["Göteborg Centralstation","Södertälje Syd station","Stockholm Centralstation"]),"to-stockholm")
  self.assertIsNone(sj.direction(["Stockholm Centralstation","Sundbyberg station","Västerås Centralstation"]))
 def test_reference_friday_repeats_with_all_original_stops(self):
  with archive() as z:data=sj.build(z,dt.date(2026,11,9))
  self.assertEqual(data["counts"],{"to-goteborg":3,"to-stockholm":3})
  self.assertEqual(len(data["trips"]),6)
  for t in data["trips"]:
   self.assertEqual(t["archiveDay"],"2026-11-06")
   self.assertEqual(len(t["stops"]),3)
   self.assertEqual(t["agency"],"SJ")
   self.assertEqual(t["geometryQuality"],"awaiting-verified-OSM")
   self.assertNotIn("verified",str(t["vehiclePhotoStatus"]).replace("unverified",""))
  self.assertEqual({t["serviceDay"] for t in data["trips"]},{"2026-11-08","2026-11-09","2026-11-10"})

if __name__=="__main__":unittest.main()
