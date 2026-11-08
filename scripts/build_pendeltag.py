#!/usr/bin/env python3
"""Build a keyless, Pendeltåg-only, strictly shape-matched historical simulation.

Historical GTFS has scheduled times, not GPS, and no shapes. Public OSM railway
relations provide verified track geometry. Unmatched trips are EXCLUDED; no
straight-line fallbacks, no fabricated movement along roads.
"""
import collections
import datetime as dt
import json
import pathlib
from zoneinfo import ZoneInfo
import build_rail_keyless as historic

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"data"/"rail.json"
MIN_TRACKED=12
MAX_SPEED_KMH=185
MAX_TRACK_ERROR_M=130

def validate(trip,shape):
    anchors=osm.project_stops(trip["stops"],shape,MAX_TRACK_ERROR_M)
    if anchors is None or len(anchors)<2:return False
    for i in range(1,len(anchors)):
        length=anchors[i]-anchors[i-1]
        travel=trip["stops"][i][3]-trip["stops"][i-1][4]
        if travel<=0 or length<0:return False
        # 3*t*t-2*t*t*t has a peak speed 1.5x average.
        if length/travel*3.6*1.5>MAX_SPEED_KMH:return False
    return True

def create(data):
    import pendeltag_graph
    return pendeltag_graph.build(data)

def main():
    with historic.fetch_archive() as z:
        initial=historic.build(z)
    result=create(initial)
    raw=json.dumps(result,ensure_ascii=False,separators=(",",":"))
    if len(raw.encode())>24_000_000:raise RuntimeError("Dataset exceeds 24 MB safe payload")
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(raw,encoding="utf-8")
    print("PENDELTAG VERIFIED RAIL DATA:",result["qualityReport"],flush=True)

if __name__=="__main__":main()
