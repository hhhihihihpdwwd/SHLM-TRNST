#!/usr/bin/env python3
"""Source historical line 12/21 timetable from same public November archive.

Do not modify Pendeltåg, Tunnelbana or Tvärbanan candidate data.
Weekend replay (historical Saturday pattern) is explicitly marked simulated.
"""
import datetime as dt
import json
from pathlib import Path
import build_rail_keyless as archive
import build_tvarbanan_candidates as existing

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"local_tram_candidates.json"
LOCAL={"12","21"}

def build_candidates(gtfs,current):
    prior=existing.LINES
    try:
        existing.LINES=LOCAL
        result=existing.build_tram_candidates(gtfs,current)
    finally:
        existing.LINES=prior
    return result

def main():
    now=dt.datetime.now(archive.ZONE).date()
    with archive.fetch_archive() as gtfs:
        dataset=build_candidates(gtfs,now)
    from collections import Counter
    by_line=Counter(t["line"] for t in dataset["trips"])
    by_day=Counter(t["serviceDay"] for t in dataset["trips"])
    print("LOCAL RAIL GTFS CANDIDATES",dict(by_line),"DAYS",dict(by_day),flush=True)
    if not all(by_line[line]>0 for line in LOCAL):
        raise RuntimeError("Missing historical trips for Nockebybanan or Lidingöbanan")
    OUT.write_text(json.dumps(dataset,ensure_ascii=False,separators=(",",":")),encoding="utf8")

if __name__=="__main__":main()
