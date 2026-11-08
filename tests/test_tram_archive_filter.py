"""Regression: select lines 12/21 before global 1500-trip tram cap."""
import datetime as dt
import io
import sys
import unittest
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import build_rail_keyless as archive
import build_tvarbanan_candidates as tvar

def fixture():
    b=io.BytesIO()
    with zipfile.ZipFile(b,"w") as z:
        z.writestr("agency.txt","agency_id,agency_name\nsl,SL\n")
        z.writestr("routes.txt","route_id,agency_id,route_short_name,route_long_name,route_type\n"
                   +"r7,sl,7,Spårväg City,0\n"
                   +"r12,sl,12,Nockebybanan,0\n"
                   +"r21,sl,21,Lidingöbanan,0\n")
        z.writestr("stops.txt","stop_id,stop_name,stop_lat,stop_lon\n"
                   +"a,A,59.33,18.04\n"+"b,B,59.34,18.05\n")
        z.writestr("calendar.txt","service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"
                   +"s,0,0,0,0,0,1,0,20261104,20261110\n")
        rows=["trip_id,route_id,service_id,trip_headsign"]
        times=["trip_id,arrival_time,departure_time,stop_id,stop_sequence"]
        for line in ("7","12","21"):
            for n in range(800):
                tid=f"{line}-{n}"
                rows.append(f"{tid},r{line},s,B")
                hour=12 if n%2==0 else 16
                times.append(f"{tid},{hour:02}:30:00,{hour:02}:30:00,a,1")
                times.append(f"{tid},{hour:02}:55:00,{hour:02}:55:00,b,2")
        z.writestr("trips.txt","\n".join(rows)+"\n")
        z.writestr("stop_times.txt","\n".join(times)+"\n")
    b.seek(0)
    return zipfile.ZipFile(b)

class TramArchiveTests(unittest.TestCase):
    def test_selected_lines_do_not_get_starved_by_unrelated_tram_trips(self):
        saturday=dt.date(2026,11,7)
        with fixture() as z:
            raw=archive.build(z,now=saturday,tram_lines={"12","21"})
        self.assertEqual(set(t["line"] for t in raw["trips"]),{"12","21"})
        self.assertTrue(all(t["mode"]=="tram" for t in raw["trips"]))
        self.assertTrue(any(t["serviceDay"]==saturday.isoformat() for t in raw["trips"]))
        for line in ("12","21"):
            self.assertTrue(any(t["line"]==line and
                t["start"]<=int(dt.datetime(2026,11,7,12,47,tzinfo=archive.ZONE).timestamp())<=t["end"]
                for t in raw["trips"]))
    def test_sunday_proxy_keeps_prior_day_departures_for_local_lines(self):
        sunday=dt.date(2026,11,8)
        old=tvar.LINES
        try:
            tvar.LINES={"12","21"}
            with fixture() as z:
                result=tvar.build_tram_candidates(z,current=sunday)
        finally:
            tvar.LINES=old
        sunday_trips=[t for t in result["trips"] if t["serviceDay"]=="2026-11-08"]
        self.assertGreater(len(sunday_trips),0)
        self.assertEqual({t["line"] for t in sunday_trips},{"12","21"})
        self.assertTrue(all(t.get("timetableProxy") for t in sunday_trips))
if __name__=="__main__":unittest.main()
