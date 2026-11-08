#!/usr/bin/env python3
"""Roslagsbanan 27/28/29 historic candidate source, isolated from STABLE 03.
Uses archived GTFS-Sverige-2 line-specific Saturday service for Sunday when
original public archive does not contain enough representative daytime trains.
Substitutions are explicitly labelled simulations, never live SL departures.
"""
import datetime as dt
import json
from pathlib import Path
import build_rail_keyless as archive

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"data"/"roslags_candidates.json"
REF_START=dt.date(2026,11,4)
LINES={"27","28","29"}

def clock_at(date,hour,minute=47):
    return int(dt.datetime.combine(date,dt.time(hour,minute),archive.ZONE).timestamp())

def build_candidates(gtfs,now):
    original=archive.SOURCE_START
    try:
        archive.SOURCE_START=REF_START
        dataset=archive.build(gtfs,now=now)
    finally:
        archive.SOURCE_START=original
    selected=[t for t in dataset["trips"] if str(t.get("line","")).strip() in LINES
              and t.get("mode")=="tram"]
    # Source archive can omit or undercount Sunday Roslagsbanan journeys.
    # The private simulation can instead mirror the actual historic Saturday
    # timetable for that one line while preserving all stop-time differences.
    if now.weekday()==6:
        saturday=now-dt.timedelta(days=1)
        shift=clock_at(now,0,0)-clock_at(saturday,0,0)
        for line in sorted(LINES):
            todays=[t for t in selected if t["line"]==line and t["serviceDay"]==now.isoformat()]
            noon=clock_at(now,12)
            if sum(t["start"]<=noon<=t["end"] for t in todays)>=2:continue
            earlier=[t for t in selected if t["line"]==line
                     and t["serviceDay"]==saturday.isoformat()]
            before=clock_at(saturday,12)
            if sum(t["start"]<=before<=t["end"] for t in earlier)<1:
                raise ValueError("No complete archived Saturday service for Roslagsbanan "+line)
            selected=[t for t in selected if not (t["line"]==line
                      and t["serviceDay"]==now.isoformat())]
            selected.extend({**t,"id":"ROSLAG-SUNDAY-PROXY:"+t["id"],
                "serviceDay":now.isoformat(),"start":t["start"]+shift,
                "end":t["end"]+shift,
                "timetableProxy":"Historical Saturday service repeated on Sunday",
                "source":"Historical Saturday GTFS used for private Sunday simulation"}
                for t in earlier)
            print("ROSLAG SUNDAY SIMULATION",line,len(earlier),"archived Saturday trips",flush=True)
    dataset["trips"]=selected
    dataset["shapes"]={k:v for k,v in dataset["shapes"].items()
                       if k in {t["shapeId"] for t in selected}}
    dataset["counts"]={"localrail":len(selected)}
    print("ROSLAG CANDIDATES", {l:sum(t["line"]==l for t in selected) for l in LINES},flush=True)
    if not all(any(t["line"]==line for t in selected) for line in LINES):
        raise ValueError("Archive missing Roslagsbanan line 27, 28 or 29")
    return dataset

def main():
    now=dt.datetime.now(archive.ZONE).date()
    with archive.fetch_archive() as z:
        data=build_candidates(z,now)
    OUTPUT.write_text(json.dumps(data,ensure_ascii=False,separators=(",",":")),encoding="utf8")

if __name__=="__main__":main()
