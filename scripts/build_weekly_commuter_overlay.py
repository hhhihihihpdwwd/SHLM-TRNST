#!/usr/bin/env python3
"""Rebuild the COMPLETE historical Pendeltåg GTFS week without dropping trips.

This replaces commuter only on the frozen STABLE22 website. Metro's 13,372
already-validated weekly journeys and every other operator stay unmodified.
Do not publish unless every GTFS journey matches verified existing OSM rails.
"""
from __future__ import annotations
import argparse
import collections
import datetime as dt
import json
import hashlib
from pathlib import Path
from zoneinfo import ZoneInfo

from build_rail_keyless import SOURCE_START, clock, fetch_archive, in_box, mode, records, service_calendar
from refine_osm_routes import choose_directional_shape

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/"website/data/rail.json"
ZONE=ZoneInfo("Europe/Stockholm")
DAYS=[SOURCE_START+dt.timedelta(days=n) for n in range(7)]
ERROR_METRES=350

def gtfs_week(archive):
    valid=service_calendar(archive,DAYS)
    by_service=collections.defaultdict(list)
    for day,ids in valid.items():
        for id in ids:by_service[id].append(day)
    agencies={r.get("agency_id"):r.get("agency_name","") for r in records(archive,"agency.txt")}
    route_info={}
    for r in records(archive,"routes.txt"):
        short=r.get("route_short_name","").strip()
        agency=agencies.get(r.get("agency_id"),"")
        m=mode(r.get("route_type")," ".join((short,r.get("route_long_name",""),agency)),short,agency)
        # Limit to SL-numbered Pendeltåg, not all national heavy rail.
        if m!="commuter" or not short.isdecimal() or not 40<=int(short)<=49:continue
        if "sl" not in agency.casefold() and "stockholms lokaltrafik" not in agency.casefold():continue
        route_info[r["route_id"]]=(short,agency)
    if not route_info:raise RuntimeError("GTFS archive does not contain numbered SL Pendeltåg")
    trips={}
    for r in records(archive,"trips.txt"):
        route=route_info.get(r.get("route_id"))
        days=by_service.get(r.get("service_id"),[])
        if route and days:trips[r["trip_id"]]=(route,r.get("trip_headsign",""),r.get("trip_short_name",""),days)
    stations={}
    for r in records(archive,"stops.txt"):
        try:p=[round(float(r["stop_lat"]),6),round(float(r["stop_lon"]),6)]
        except (KeyError,ValueError):continue
        if in_box(p):stations[r["stop_id"]]=[*p,r.get("stop_name","")]
    stop_times=collections.defaultdict(list)
    for r in records(archive,"stop_times.txt"):
        tid=r.get("trip_id")
        if tid not in trips:continue
        stop=stations.get(r.get("stop_id"))
        if not stop:raise RuntimeError("Pendeltåg GTFS stop outside retained geography "+str(r.get("stop_id")))
        arr,dep=clock(r.get("arrival_time","")),clock(r.get("departure_time",""))
        if arr is None:arr=dep
        if dep is None:dep=arr
        if arr is None or dep is None:raise RuntimeError("Bad Pendeltåg stop time "+tid)
        stop_times[tid].append((int(r["stop_sequence"]),[*stop,arr,dep]))
    rows=[]
    for tid,(route,head,train,days) in trips.items():
        stops=[s for _,s in sorted(stop_times[tid],key=lambda x:x[0])]
        if len(stops)<2:raise RuntimeError("Pendeltåg has <2 GTFS stops "+tid)
        if any(stops[i][3]>stops[i+1][3] or stops[i][4]>stops[i+1][4] for i in range(len(stops)-1)):
            raise RuntimeError("Nonmonotonic Pendeltåg stop times "+tid)
        for day in days:
            startday=dt.datetime.combine(day,dt.time(0),ZONE)
            first,last=stops[0][4],stops[-1][3]
            if first>=last:raise RuntimeError("Invalid Pendeltåg time interval "+tid)
            rows.append({
                "id":"COMMUTER-WEEK:"+day.isoformat()+":"+tid,
                "mode":"commuter","line":route[0],"agency":route[1],
                "destination":head or stops[-1][2],"train":train,
                "serviceDay":day.isoformat(),
                "start":int((startday+dt.timedelta(seconds=first)).timestamp()),
                "end":int((startday+dt.timedelta(seconds=last)).timestamp()),
                "stops":stops,"sourceTripId":tid,
                "source":"GTFS Sverige 2 historical timetable, 2026-11-04 archive",
                "archiveDay":day.isoformat()
            })
    if not rows:raise RuntimeError("No GTFS commuter journeys")
    print("GTFS PENDLETÅG ARCHIVE",len(rows),"journeys",flush=True)
    print("GTFS PENDLETÅG LINES",dict(collections.Counter(r["line"] for r in rows)),flush=True)
    return rows

def rebuild(data,rows):
    if not data.get("metroWeekdaySimulation") or data["counts"].get("metro")!=13372:
        raise RuntimeError("Refusing to modify source without verified STABLE22 weekly Tunnelbana")
    original=data["trips"]
    untouched=[r for r in original if r["mode"]!="commuter"]
    fingerprint=hashlib.sha256(json.dumps(untouched,sort_keys=True).encode()).hexdigest()
    old=[r for r in original if r["mode"]=="commuter"]
    by_line=collections.defaultdict(dict)
    all_shapes={}
    for t in old:
        key=t["shapeId"];shape=data["shapes"].get(key)
        if not shape or len(shape)<2 or t.get("geometryQuality")!="verified-osm-relation":continue
        by_line[str(t["line"])][key]=shape
        all_shapes[key]=shape
    missing_lines=set(str(r["line"]) for r in rows)-set(by_line)
    if missing_lines:
        print("MISSING COMMUTER LINE TRACKS",missing_lines,flush=True)
        raise RuntimeError("Historical commuter routes absent from original OSM inventory")
    by_pattern=collections.defaultdict(list)
    expected=collections.Counter()
    for r in rows:
        by_pattern[(r["line"],tuple((s[0],s[1],s[2]) for s in r["stops"]))].append(r)
        expected[(r["serviceDay"],r["line"])]+=1
    converted=[];new_shapes={};fail=[]
    for (line,points),group in by_pattern.items():
        candidates=list(by_line[line].items())
        # A shared SL commuter track may be registered under another line.
        chosen=choose_directional_shape(group[0]["stops"],candidates,ERROR_METRES)
        if chosen is None:
            chosen=choose_directional_shape(group[0]["stops"],list(all_shapes.items()),ERROR_METRES)
        if chosen is None:
            fail.append((line,len(group),group[0]["id"],group[0]["stops"][0][2],group[0]["stops"][-1][2]))
            continue
        sid,shape=chosen
        new_shapes[sid]=shape
        for r in group:
            converted.append({**r,"shapeId":sid,"geometryQuality":"verified-osm-relation",
                              "osmRelation":sid})
    if fail:
        print("UNMATCHED COMMUTER ROUTE PATTERNS",len(fail),"DROPPED TRIPS",sum(x[1] for x in fail),flush=True)
        for row in sorted(fail,key=lambda x:-x[1])[:80]:print("UNMATCHED",row,flush=True)
        raise RuntimeError("Full commuter GTFS archive cannot be represented by verified old OSM tracks")
    actual=collections.Counter((r["serviceDay"],r["line"]) for r in converted)
    if actual!=expected:raise RuntimeError("Historical commuter source trips lost in reconstruction")
    lines=set(r["line"] for r in converted)
    for day in DAYS:
        for line in lines:
            if not actual[(day.isoformat(),line)]:
                # Some SL branches may be weekday-only: do NOT fabricate trains.
                print("ZERO REAL HISTORICAL SCHEDULED",day,line,flush=True)
    converted.sort(key=lambda r:(r["serviceDay"],r["start"],r["line"],r["id"]))
    out={**data,"trips":untouched+converted,
         "shapes":{**data["shapes"],**new_shapes},
         "counts":{**data["counts"],"commuter":len(converted)},
         "commuterWeekdaySimulation":True,
         "commuterWeekdaySourceDays":{str(d.weekday()):d.isoformat() for d in DAYS},
         "commuterWeeklyCoverage":{d.isoformat():{line:actual[(d.isoformat(),line)] for line in sorted(lines)} for d in DAYS},
         "commuterSourceDisclaimer":"Historic weekday-specific GTFS, not realtime GPS or a guaranteed holiday timetable"}
    assert fingerprint==hashlib.sha256(json.dumps([r for r in out["trips"] if r["mode"]!="commuter"],sort_keys=True).encode()).hexdigest()
    assert all(out["shapes"][k]==v for k,v in data["shapes"].items())
    assert len(converted)==len(rows)
    print("PENDLETÅG WEEK SUCCESS",len(converted),"old",len(old),flush=True)
    print("WEEK COUNTS",json.dumps(out["commuterWeeklyCoverage"],ensure_ascii=False),flush=True)
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,default=INPUT)
    p.add_argument("--output",type=Path,default=INPUT)
    a=p.parse_args()
    d=json.loads(a.input.read_text(encoding="utf8"))
    with fetch_archive() as z:trips=gtfs_week(z)
    upgraded=rebuild(d,trips)
    result=json.dumps(upgraded,ensure_ascii=False,separators=(",",":"))
    if len(result.encode("utf8"))>95_000_000:raise RuntimeError("Website data exceeds safe 95 MB limit")
    a.output.write_text(result,encoding="utf8")
    print("PENDLETÅG BUILD COMPLETE",len(result),"bytes",flush=True)

if __name__=="__main__":main()
