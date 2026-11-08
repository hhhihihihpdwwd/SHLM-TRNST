#!/usr/bin/env python3
"""Build Tvärbanan-specific historical service patterns without touching rail baseline.

The Nov 4 public archive contains complete Nov 7/8 services, whereas Nov 15
is outside dependable calendar coverage. The legacy rail baseline continues
using its existing reference window unchanged. This module ONLY writes tram
archive candidates for the Tvärbanan extension.
"""
import datetime as dt
import json
from pathlib import Path
import build_rail_keyless as archive

OUTPUT=Path(__file__).resolve().parents[1]/"data"/"tvarbanan_candidates.json"
TRAM_REFERENCE_START=dt.date(2026,11,4) # Wed, covers Sat Nov 7 / Sun Nov 8
LINES={"30","31"}

def build_tram_candidates(gtfs,current=None):
    old=archive.SOURCE_START
    try:
        archive.SOURCE_START=TRAM_REFERENCE_START
        result=archive.build(gtfs,now=current,tram_lines=LINES)
    finally:
        archive.SOURCE_START=old
    trips=[t for t in result["trips"] if t["mode"]=="tram" and str(t.get("line","")) in LINES]
    # Archived Sunday 2026-11-08 has early-morning services but no daytime
    # Tvärbanan runs. For this PRIVATE representative traffic simulation,
    # use the complete previous Saturday pattern for Sunday. Do not label it
    # a real Sunday timetable: each proxy trip carries an explicit provenance.
    sunday=current if current and current.weekday()==6 else None
    if sunday:
        sunday_date=sunday.isoformat()
        saturday=sunday-dt.timedelta(days=1)
        saturday_date=saturday.isoformat()
        def daytime_count(items,day):
            # deterministic local noon, independent of CI timezone
            noon=int(dt.datetime.combine(day,dt.time(12,47),archive.ZONE).timestamp())
            return sum(x["start"]<=noon<=x["end"] for x in items)
        sundays=[t for t in trips if t["serviceDay"]==sunday_date]
        if daytime_count(sundays,sunday)<2:
            saturday_trips=[t for t in trips if t["serviceDay"]==saturday_date]
            if daytime_count(saturday_trips,saturday)<2:
                from collections import Counter
                counts=Counter((str(t["line"]),t["serviceDay"]) for t in trips)
                raise RuntimeError(
                    "No complete prior-day tram pattern to simulate Sunday; "
                    "per-line GTFS reference counts="+str(dict(counts)))
            shift=int((dt.datetime.combine(sunday,dt.time(0),archive.ZONE)-
                       dt.datetime.combine(saturday,dt.time(0),archive.ZONE)).total_seconds())
            replay=[{**t,
                      "id":"SUNDAY-PROXY:"+t["id"],
                      "serviceDay":sunday_date,
                      "start":t["start"]+shift,
                      "end":t["end"]+shift,
                      "timetableProxy":"Saturday service pattern repeated on Sunday",
                      "source":"Historical Saturday GTFS timetable used for Sunday private simulation"}
                    for t in saturday_trips]
            trips=[t for t in trips if t["serviceDay"]!=sunday_date]+replay
            print("TVÄRBANAN SUNDAY PROXY",len(replay),"Saturday trips mapped to",
                  sunday_date,"to replace incomplete Sunday service",flush=True)
    result["trips"]=trips
    result["counts"]={"tram":len(trips)}
    used={t["shapeId"] for t in trips}
    result["shapes"]={k:v for k,v in result["shapes"].items() if k in used}
    result["tramArchiveReference"]="2026-11-04-through-2026-11-10"
    return result

def main():
    now=dt.datetime.now(archive.ZONE).date()
    with archive.fetch_archive() as z:
        result=build_tram_candidates(z,now)
    from collections import Counter
    days=Counter(t["serviceDay"] for t in result["trips"])
    print("TVÄRBANAN REFERENCE DAYS",dict(days),flush=True)
    if days.get(now.isoformat(),0)<20:
        raise RuntimeError("Tvärbanan historic service missing for today's weekday: refuse empty map")
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,separators=(",",":")),encoding="utf8")
    print("TVÄRBANAN PUBLIC ARCHIVE CANDIDATES:",len(result["trips"]),flush=True)

if __name__=="__main__":main()
