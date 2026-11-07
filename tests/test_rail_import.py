import datetime as dt
import io
import json
import sys
import unittest
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import build_rail as rail

class RailGTFSIntegrationTests(unittest.TestCase):
    def test_filters_buses_and_keeps_real_rail_geometry(self):
        day=dt.datetime.now(rail.ZONE).date()
        calendar=day.strftime("%Y%m%d")
        rows={
            "agency.txt":"agency_id,agency_name\nSL,SL\n",
            "routes.txt":"route_id,agency_id,route_short_name,route_long_name,route_type\nM,SL,13,Tunnelbana 13,1\nB,SL,4,Bus 4,3\n",
            "calendar_dates.txt":f"service_id,date,exception_type\nW,{calendar},1\n",
            "trips.txt":"route_id,service_id,trip_id,trip_headsign,shape_id\nM,W,M1,Ropsten,metroshape\nB,W,B1,Bus terminal,busshape\n",
            "stops.txt":"stop_id,stop_name,stop_lat,stop_lon\nA,Slussen,59.3199,18.0721\nB,T-Centralen,59.3311,18.0603\n",
            "stop_times.txt":"trip_id,arrival_time,departure_time,stop_id,stop_sequence\nM1,12:00:00,12:00:00,A,1\nM1,12:03:00,12:03:00,B,2\nB1,12:00:00,12:00:00,A,1\nB1,12:03:00,12:03:00,B,2\n",
            "shapes.txt":"shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\nmetroshape,59.3199,18.0721,1\nmetroshape,59.325,18.067,2\nmetroshape,59.3311,18.0603,3\n",
        }
        blob=io.BytesIO()
        with zipfile.ZipFile(blob,"w") as z:
            for name,body in rows.items():z.writestr(name,body)
        blob.seek(0)
        outputs=[]
        with zipfile.ZipFile(blob) as z:
            count=rail.import_feed(z,"TEST",[day],outputs)
        self.assertEqual(count,1)
        self.assertEqual(outputs[0]["mode"],"metro")
        self.assertEqual(outputs[0]["shapeId"],"TEST:metroshape")
        self.assertEqual(len(rail.SHARED_SHAPES["TEST:metroshape"]),3)
        self.assertLess(outputs[0]["start"],outputs[0]["end"])
    def test_gtfs_times_after_midnight(self):
        self.assertEqual(rail.parse_seconds("25:03:10"),25*3600+3*60+10)
        self.assertIsNone(rail.parse_seconds("27:90:00"))
        self.assertIsNone(rail.parse_seconds("not-time"))
if __name__=="__main__":unittest.main()
