#!/usr/bin/env python3
"""Saltsjöbanan 25/26 historic candidate source, isolated from STABLE 03.
Uses archived GTFS-Sverige-2 line-specific Saturday service for Sunday when
original public archive does not contain enough representative daytime trains.
Substitutions are explicitly labelled simulations, never live SL departures.
"""
import datetime as dt
import json
from pathlib import Path
import build_rail_keyless as archive

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"data"/"saltsjo_candidates.json"
REF_START=dt.date(2026,11,4)
LINES={"25","26"}

def clock_at(date,hour,minute=47):
    return int(dt.datetime.combine(date,dt.time(hour,minute),archive.ZONE).timestamp())

def build_candidates(gtfs,now):
    original=archive.SOURCE_START
    try:
        archive.SOURCE_START=REF_START
        dataset=archive.build(gtfs,now=now,tram_lines=LINES)
    finally:
        archive.SOURCE_START=original
    selected=[t for t in dataset["trips"] if str(t.get("line","")).strip() in LINES
              and t.get("mode")=="tram"]
    dataset["trips"]=selected
    dataset["shapes"]={k:v for k,v in dataset["shapes"].items()
                       if k in {t["shapeId"] for t in selected}}
    dataset["counts"]={"localrail":len(selected)}
    print("SALTSJO CANDIDATES", {l:sum(t["line"]==l for t in selected) for l in LINES},flush=True)
    if not all(any(t["line"]==line for t in selected) for line in LINES):
        raise ValueError("Archive missing Saltsjöbanan line 25 or 26")
    return dataset

def main():
    now=dt.datetime.now(archive.ZONE).date()
    with archive.fetch_archive() as z:
        data=build_candidates(z,now)
    OUTPUT.write_text(json.dumps(data,ensure_ascii=False,separators=(",",":")),encoding="utf8")

if __name__=="__main__":main()
