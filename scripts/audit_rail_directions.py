#!/usr/bin/env python3
"""Fail deployment when any vehicle system loses either travel direction.

For Stockholm most named routes are non-horizontal; north/south is a useful
network-wide sanity check, not a substitute for individual GTFS destination
validation. Also audit the named Uppsala–Stockholm corridor explicitly.
"""
import collections
import json
from pathlib import Path

DATA=Path(__file__).resolve().parents[1]/"data"/"rail.json"

def direction(trip):
    a,b=trip["stops"][0][:2],trip["stops"][-1][:2]
    lat=b[0]-a[0]
    lon=(b[1]-a[1])*0.50
    if abs(lat)>=abs(lon):
        return "north" if lat>0 else "south"
    return "east" if lon>0 else "west"

def audit(data):
    result=collections.defaultdict(collections.Counter)
    for trip in data["trips"]:
        if trip.get("geometryQuality")!="verified-osm-relation":
            raise AssertionError("Published trip has unverified tracks")
        result[trip["mode"]][direction(trip)]+=1
    print("VEHICLE DIRECTION COVERAGE",json.dumps({k:dict(v) for k,v in result.items()},sort_keys=True),flush=True)
    for mode in ("commuter","metro","tram"):
        counts=result[mode]
        if counts["north"]<1 or counts["south"]<1:
            raise AssertionError(f"{mode} lacks an entire north/south direction: {dict(counts)}")
    uppsala=[
        t for t in data["trips"]
        if t["mode"]=="commuter"
        and any("uppsala" in stop[2].casefold() for stop in (t["stops"][0],t["stops"][-1]))
    ]
    outbound=sum("uppsala" in t["stops"][-1][2].casefold() for t in uppsala)
    inbound=sum("uppsala" in t["stops"][0][2].casefold() for t in uppsala)
    print("UPPSALA CORRIDOR:",outbound,"towards Uppsala,",inbound,"from Uppsala",flush=True)
    if outbound<1 or inbound<1:
        raise AssertionError("Uppsala corridor is missing one direction")
    return result

if __name__=="__main__":
    audit(json.loads(DATA.read_text(encoding="utf8")))
