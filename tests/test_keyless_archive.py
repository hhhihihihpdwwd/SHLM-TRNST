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
        service=days[0]
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
        self.assertEqual(data["counts"]["metro"],1)
        self.assertEqual(len(data["trips"]),1)
        self.assertEqual(data["type"],"historical-weekday-simulation")
        self.assertEqual(data["trips"][0]["geometryQuality"],"approximate-stop-connectors")
        self.assertTrue(data["shapes"][data["trips"][0]["shapeId"]])
        self.assertEqual(data["trips"][0]["stops"][0][2],"Slussen")
        self.assertEqual(data["trips"][0]["stops"][1][2],"T-Centralen")
    def test_gtfs_25_hour_clock(self):
        self.assertEqual(keyless.clock("25:15:00"),90900)
        self.assertIsNone(keyless.clock("25:99:00"))
        self.assertIsNone(keyless.clock("not a time"))

if __name__=="__main__":unittest.main()
