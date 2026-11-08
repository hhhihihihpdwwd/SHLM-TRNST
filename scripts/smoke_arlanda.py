#!/usr/bin/env python3
"""Fast Arlanda-only end-to-end test: historic ZIP -> genuine OSM tracks -> map."""
import datetime as dt
import json
from pathlib import Path
import build_rail_keyless as gtfs
from build_arlanda_candidates import build
from append_arlanda_express import integrate
ROOT=Path(__file__).resolve().parents[1]
def main():
    now=dt.date(2026,11,8)
    with gtfs.fetch_archive() as z:archive=build(z,now)
    base={
      "schema":1,"scope":"pendeltag-tunnelbana-tvarbanan-localtram-city7-roslags-saltsjo",
      "trips":[],"shapes":{},"counts":{"commuter":1,"metro":1,"tram":1,"localrail":1,"saltsjo":1},
      "metroLines":{"13":1},"tramLines":{"7":1},"roslagsLines":{"27":1},
      "saltsjoLines":{"25":1}
    }
    result=integrate(base,archive)
    out=ROOT/"data"/"arlanda-smoke.json"
    out.parent.mkdir(exist_ok=True,parents=True)
    out.write_text(json.dumps(result,ensure_ascii=False,separators=(",",":")),encoding="utf8")
    print("ARLANDA FAST SMOKE DATA",result["arlandaDirections"],flush=True)
if __name__=="__main__":main()
