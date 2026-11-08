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
import refine_osm_routes as osm

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
    candidates=[t for t in data["trips"] if t["mode"]=="commuter"]
    if not candidates:raise RuntimeError("No Pendeltag journeys identified in historical GTFS.")
    data["trips"]=candidates
    # Override the general-purpose matcher: focus only on Pendeltåg and
    # use conservative railway geometry tolerance.
    osm.MATCH_LIMIT["commuter"]=MAX_TRACK_ERROR_M
    osm.MAX_LOOKUPS=28
    osm.MAX_FETCHES=50
    verified=osm.enrich(data)
    accepted=[]
    for trip in verified["trips"]:
        if trip.get("geometryQuality")!="verified-osm-relation":continue
        shape=verified["shapes"].get(trip["shapeId"])
        if shape and validate(trip,shape):
            accepted.append(trip)
    if len(accepted)<MIN_TRACKED:
        raise RuntimeError(
            f"Verified Pendeltag route coverage too low: {len(accepted)} trips "
            f"from {len(candidates)} historical candidates. "
            "Refusing to replace the working website with approximations."
        )
    # Only include geometry for trips we actually display.
    verified["trips"]=sorted(accepted,key=lambda t:(t["start"],t["id"]))
    ids={t["shapeId"] for t in accepted}
    verified["shapes"]={key:shape for key,shape in verified["shapes"].items() if key in ids}
    verified["counts"]={"commuter":len(accepted)}
    verified["type"]="historical-pendeltag-verified-rail"
    verified["description"]="Historische Fahrplanzeiten + geprüfte OSM-Gleisführung; Position, Geschwindigkeit und Auslastung modelliert, keine Live-GPS-Daten."
    verified["strictGeometry"]=True
    verified["qualityReport"]={
        "inputTrips":len(candidates),
        "verifiedTrips":len(accepted),
        "verifiedShare":round(len(accepted)/len(candidates)*100,1),
        "maxStopProjectionErrorMetres":MAX_TRACK_ERROR_M,
        "maxPeakSimulatedSpeedKmh":MAX_SPEED_KMH,
        "unverifiedTripsHidden":len(candidates)-len(accepted),
    }
    return verified

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
