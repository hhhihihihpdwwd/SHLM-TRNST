#!/usr/bin/env python3
"""Produce isolated historical SL line 7 timetable without altering STABLE 02.

The reference archive's Sunday service may be incomplete. Reuse the complete
Saturday pattern solely for this privately simulated service when necessary.
Mark every substituted trip as estimated, not actual Sunday departures.
"""
import datetime as dt
import json
from pathlib import Path
import build_rail_keyless as archive
import build_tvarbanan_candidates as shared

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"data"/"sparvag_city_candidates.json"
SOURCE_START=dt.date(2026,11,4)
LINE="7"

def visible_at(trips,date,hour=12,minute=47):
    epoch=int(dt.datetime.combine(date,dt.time(hour,minute),archive.ZONE).timestamp())
    return sum(t["start"]<=epoch<=t["end"] for t in trips)

def build_candidates(gtfs,current):
    previous=shared.LINES
    try:
        shared.LINES={LINE}
        result=shared.build_tram_candidates(gtfs,current)
    finally:
        shared.LINES=previous
    trips=[t for t in result["trips"] if t.get("mode")=="tram" and str(t.get("line",""))==LINE]
    if current.weekday()==6:
        date=current.isoformat()
        saturday=current-dt.timedelta(days=1)
        prev=saturday.isoformat()
        today=[t for t in trips if t.get("serviceDay")==date]
        if visible_at(today,current)<2:
            source=[t for t in trips if t.get("serviceDay")==prev]
            if visible_at(source,saturday)<2:
                raise RuntimeError("No sufficient historical Saturday line 7 service for Sunday simulation")
            diff=int((dt.datetime.combine(current,dt.time(),archive.ZONE)-
                      dt.datetime.combine(saturday,dt.time(),archive.ZONE)).total_seconds())
            replay=[{**t,"id":"CITY7-SUNDAY-PROXY:"+t["id"],
                     "serviceDay":date,"start":t["start"]+diff,"end":t["end"]+diff,
                     "timetableProxy":"Historical Saturday pattern repeated on Sunday",
                     "source":"Private Sunday simulation, NOT current live SL timetable"}
                    for t in source]
            trips=[t for t in trips if t.get("serviceDay")!=date]+replay
            print("SPÅRVÄG CITY SUNDAY HISTORICAL PROXY",len(replay),flush=True)
    result["trips"]=trips
    result["counts"]={"tram":len(trips)}
    result["shapes"]={k:v for k,v in result["shapes"].items()
                      if k in {t["shapeId"] for t in trips}}
    return result

def main():
    current=dt.datetime.now(archive.ZONE).date()
    with archive.fetch_archive() as z:
        result=build_candidates(z,current)
    from collections import Counter
    by_day=Counter(t["serviceDay"] for t in result["trips"])
    print("CITY7 HISTORIC GTFS DAYS",dict(by_day),flush=True)
    if not result["trips"]:raise RuntimeError("No line 7 timetable candidates")
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,separators=(",",":")),encoding="utf8")

if __name__=="__main__":main()
