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
    # Replay incomplete Sunday service independently per local-tram line.
    # The original Tvärbanan candidate builder only checks all trams together,
    # which could leave line 12 empty while line 21 is available (or vice versa).
    if current.weekday()==6:
        sunday=current.isoformat()
        saturday=current-dt.timedelta(days=1)
        previous=saturday.isoformat()
        epoch=int(dt.datetime.combine(current,dt.time(12,47),archive.ZONE).timestamp())
        saturday_start=dt.datetime.combine(saturday,dt.time(),archive.ZONE)
        sunday_start=dt.datetime.combine(current,dt.time(),archive.ZONE)
        shift=int((sunday_start-saturday_start).total_seconds())
        for line in sorted(LOCAL):
            visible=[t for t in result["trips"] if t["line"]==line and
                     t["start"]<=epoch<=t["end"]]
            if len(visible)>=1:continue
            earlier=[t for t in result["trips"] if t["line"]==line and
                     t["serviceDay"]==previous]
            if not earlier:
                raise RuntimeError(f"No historical Saturday line {line} service to repeat")
            result["trips"]=[t for t in result["trips"]
                             if not (t["line"]==line and t["serviceDay"]==sunday)]
            result["trips"].extend({**t,"id":"LOCAL-SUNDAY-PROXY:"+t["id"],
                 "serviceDay":sunday,"start":t["start"]+shift,"end":t["end"]+shift,
                 "timetableProxy":"Saturday pattern repeated for Sunday",
                 "source":"Historical Saturday timetable repeated on Sunday (simulation)"}
                 for t in earlier)
            print("LOCAL SUNDAY REPLAY",line,len(earlier),"historic Saturday trips",flush=True)
    result["counts"]={"tram":len(result["trips"])}
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
