import datetime as dt
import io
import sys
import unittest
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import build_rail_keyless as keyless

class PublicHistoricRailTests(unittest.TestCase):
    def test_sample_archive_without_api_key(self):
        days=[keyless.SOURCE_START+dt.timedelta(days=i) for i in range(7)]
        service=keyless.REFERENCE_DAY
        rows={
          "agency.txt":"agency_id,agency_name\nsl,SL\n",
          "routes.txt":"route_id,agency_id,route_short_name,route_long_name,route_type\nM,sl,13,Tunnelbana,1\nB,sl,4,Bus,3\n",
          "calendar_dates.txt":f"service_id,date,exception_type\nW,{service:%Y%m%d},1\n",
          "trips.txt":"route_id,service_id,trip_id,trip_headsign\nM,W,M1,Ropsten\nB,W,B1,Bus terminal\n",
          "stops.txt":"stop_id,stop_name,stop_lat,stop_lon\nA,Slussen,59.3199,18.0721\nB,T-Centralen,59.3311,18.0603\n",
          "stop_times.txt":"trip_id,arrival_time,departure_time,stop_id,stop_sequence\nM1,12:00:00,12:00:00,A,1\nM1,12:03:00,12:03:00,B,2\nB1,12:00:00,12:00:00,A,1\nB1,12:03:00,12:03:00,B,2\n"
        }
        blob=io.BytesIO()
        with zipfile.ZipFile(blob,'w') as archive:
            for name,data in rows.items():archive.writestr(name,data)
        blob.seek(0)
        with zipfile.ZipFile(blob) as archive:
            data=keyless.build(archive,now=service)
        self.assertEqual(data["counts"]["metro"],3)
        self.assertEqual(len(data["trips"]),3)
        self.assertEqual({t["serviceDay"] for t in data["trips"]},
                         {(service+dt.timedelta(days=offset)).isoformat() for offset in (-1,0,1)})
        self.assertEqual(data["type"],"historical-daily-repeating-simulation")
        self.assertEqual(data["referenceDay"],keyless.REFERENCE_DAY.isoformat())
        self.assertEqual(data["simulationTemplateDay"],service.isoformat())
        self.assertEqual(data["trips"][0]["geometryQuality"],"approximate-stop-connectors")
        self.assertTrue(data["shapes"][data["trips"][0]["shapeId"]])
        self.assertEqual(data["trips"][0]["stops"][0][2],"Slussen")
        self.assertEqual(data["trips"][0]["stops"][1][2],"T-Centralen")
    def test_pendeltag_keeps_uppsala_and_southern_terminals(self):
        """Regression: historic bbox 59.00..59.80 dropped both endpoints."""
        self.assertTrue(keyless.in_box([59.85853,17.64609]))  # Uppsala C
        self.assertTrue(keyless.in_box([58.901,17.949]))     # Nynäshamn
        day=keyless.REFERENCE_DAY
        rows={
          "agency.txt":"agency_id,agency_name\nSL,SL\n",
          "routes.txt":"route_id,agency_id,route_short_name,route_long_name,route_type\n"
            "R40,SL,40,Pendeltåg Uppsala,109\n"
            "R42,SL,42,Pendeltåg Nynäshamn,109\n",
          "calendar_dates.txt":f"service_id,date,exception_type\nW,{day:%Y%m%d},1\n",
          "trips.txt":"route_id,service_id,trip_id,trip_headsign\n"
            "R40,W,UP,Uppsala Centralstation\n"
            "R42,W,NY,Nynäshamn\n",
          "stops.txt":"stop_id,stop_name,stop_lat,stop_lon\n"
            "S,Stockholm City,59.3311,18.0603\n"
            "M,Märsta station,59.6268,17.8617\n"
            "U,Uppsala Centralstation,59.85853,17.64609\n"
            "N,Nynäshamn station,58.901,17.949\n",
          "stop_times.txt":"trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
            "UP,10:00:00,10:00:00,S,1\n"
            "UP,10:30:00,10:30:00,M,2\n"
            "UP,11:00:00,11:00:00,U,3\n"
            "NY,12:00:00,12:00:00,S,1\n"
            "NY,13:00:00,13:00:00,N,2\n"
        }
        archive=io.BytesIO()
        with zipfile.ZipFile(archive,"w") as z:
            for name,value in rows.items():z.writestr(name,value)
        archive.seek(0)
        with zipfile.ZipFile(archive) as z:
            data=keyless.build(z,now=day)
        self.assertEqual(data["referenceDay"],keyless.REFERENCE_DAY.isoformat())
        trip_by_destination={t["destination"]:t for t in data["trips"]}
        self.assertEqual(trip_by_destination["Uppsala Centralstation"]["stops"][-1][2],"Uppsala Centralstation")
        self.assertEqual(len(trip_by_destination["Uppsala Centralstation"]["stops"]),3)
        self.assertEqual(trip_by_destination["Nynäshamn"]["stops"][-1][2],"Nynäshamn station")

    def test_gtfs_25_hour_clock(self):
        self.assertEqual(keyless.clock("25:15:00"),90900)
        self.assertIsNone(keyless.clock("25:99:00"))
        self.assertIsNone(keyless.clock("not a time"))

if __name__=="__main__":unittest.main()
