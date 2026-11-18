#!/usr/bin/env python3
"""Build STABLE29 from exact STABLE28 + already GTFS/OSM-audited STABLE22 Metro week.

No new tracks inferred or straight segments drawn. Failure is fatal; never
silently drop trips. Zero changes to the non-Metro STABLE28 records, images,
symbols, filters, timetable engine or physical geometry.
"""
import argparse
import collections
import datetime as dt
import hashlib
import json
import math
from pathlib import Path

LINES={"10","11","13","14","17","18","19"}
def hash_records(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()

def checked_merge(original,previous_week):
    assert original.get("type")=="historical-daily-repeating-simulation"
    assert not original.get("metroWeekdaySimulation"),"Expected STABLE28 source, not already merged Metro"
    assert previous_week.get("metroWeekdaySimulation") is True
    assert original["counts"]["metro"]==2797
    assert previous_week["counts"]["metro"]==13372
    assert len(original["trips"])==10827 and len(previous_week["trips"])==21402
    assert original["scope"]==previous_week["scope"]
    original_nonmetro=[v for v in original["trips"] if v["mode"]!="metro"]
    historical_nonmetro=[v for v in previous_week["trips"] if v["mode"]!="metro"]
    assert original_nonmetro==historical_nonmetro,"STABLE22 non-Metro source differs from the preserved production baseline"
    assert len(original_nonmetro)==8030
    assert all(previous_week["shapes"].get(k)==v for k,v in original["shapes"].items()),"Existing routes/coordinates changed"
    assert all(previous_week["counts"].get(k)==v for k,v in original["counts"].items() if k!="metro")
    metro=[t for t in previous_week["trips"] if t["mode"]=="metro"]
    assert len(metro)==13372
    assert len({r["id"] for r in metro})==len(metro)
    assert all(t.get("geometryQuality")=="verified-osm-relation" for t in metro)
    assert all(t.get("sourceTripId") for t in metro)
    assert all(t.get("shapeId") in previous_week["shapes"] for t in metro)
    assert all(len(t["stops"])>=2 and t["start"]<t["end"] for t in metro)
    counts=collections.Counter((t["serviceDay"],str(t["line"])) for t in metro)
    days=previous_week["metroWeeklyCoverage"]
    assert len(days)==7 and set(counts)=={(day,line) for day in days for line in LINES}
    for day,perline in days.items():
        assert set(perline)==LINES
        for line in LINES:
            assert perline[line]==counts[(day,line)]>0
    assert sum(sum(x.values()) for x in days.values())==len(metro)
    assert set(t["line"] for t in metro)==LINES
    # Shape sanity: no kilometers-long artificial straight connectors.
    # Use warnings separately for longer real OSM segments; do not mutate geometry.
    unique_shapes={t["shapeId"] for t in metro}
    for key in unique_shapes:
        path=previous_week["shapes"][key]
        assert len(path)>=2,(key,"empty OSM shape")
        assert all(len(point)==2 and all(math.isfinite(float(x)) for x in point)
                   for point in path),(key,"invalid shape coordinate")
    result={**original}
    result["trips"]=original_nonmetro+metro
    result["shapes"]={**original["shapes"],
        **{key:previous_week["shapes"][key] for key in unique_shapes}}
    result["counts"]={**original["counts"],"metro":len(metro)}
    result["metroLines"]=dict(collections.Counter(str(t["line"]) for t in metro))
    for name in ("metroWeekdaySimulation","metroWeekdaySourceDays",
                 "metroWeeklyCoverage","metroSourceDisclaimer"):
        result[name]=previous_week[name]
    assert len(result["trips"])==21402
    assert [t for t in result["trips"] if t["mode"]!="metro"]==original_nonmetro
    assert all(result["shapes"][k]==v for k,v in original["shapes"].items())
    assert result["scope"]==original["scope"]
    assert all(result["counts"][k]==v for k,v in original["counts"].items() if k!="metro")
    print("STABLE29 EXACT PRESERVED 15 SYSTEMS",len(original_nonmetro),"TRIPS SHA256",hash_records(original_nonmetro),flush=True)
    print("STABLE29 EXISTING OSM COORDINATES PRESERVED",len(original["shapes"]),
          "COMPLETE WEEK VERIFIED SHAPES",len(unique_shapes),flush=True)
    print("STABLE29 EXACT METRO GTFS 7-DAY JOURNEYS",len(metro),
          "METRO LINES",json.dumps(result["metroLines"],sort_keys=True),flush=True)
    for day,lines in days.items():
        print("STABLE29 GTFS DAY",day,json.dumps(lines,sort_keys=True),flush=True)
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--base",type=Path,required=True)
    p.add_argument("--reference",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    prior=json.loads(a.base.read_text(encoding="utf-8"))
    seven=json.loads(a.reference.read_text(encoding="utf-8"))
    updated=checked_merge(prior,seven)
    payload=json.dumps(updated,ensure_ascii=False,separators=(",",":"))
    assert len(payload.encode("utf-8"))<95_000_000,"Too large for safe Pages deployment"
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(payload,encoding="utf-8")
    assert json.loads(a.output.read_text(encoding="utf-8"))["counts"]["metro"]==13372
    print("STABLE29 DATA VALIDATED",len(payload.encode("utf-8")),"bytes",flush=True)
if __name__=="__main__":main()
