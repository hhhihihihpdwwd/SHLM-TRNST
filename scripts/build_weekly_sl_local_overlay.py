#!/usr/bin/env python3
"""Source-complete Mon-Sun historic timetables for ten existing SL local rail lines.

Only touch tram (7/12/21/30/31), Roslagsbanan (27/28/29), and
Saltsjöbanan (25/26); preserve all other 16-system train records and OSM
geometries exactly. An unmatchable genuine GTFS journey is a hard failure.
"""
from __future__ import annotations
import collections
import datetime as dt
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from build_rail_keyless import SOURCE_START, clock, fetch_archive, in_box, records, service_calendar
from refine_osm_routes import choose_directional_shape
from append_roslagsbanan import verified_match as verified_roslags_match
from stitch_saltsjo_shortturns import stitch_saltsjo_25_26

INPUT=Path(__file__).resolve().parents[1]/"website/data/rail.json"
ZONE=ZoneInfo("Europe/Stockholm")
DAYS=[SOURCE_START+dt.timedelta(days=i) for i in range(7)]
MODE={**dict.fromkeys(("7","12","21","30","31"),"tram"),
      **dict.fromkeys(("27","28","29"),"localrail"),
      **dict.fromkeys(("25","26"),"saltsjo")}
MAX_STOP_ERROR=350

def load_week(z):
    calendar=service_calendar(z,DAYS)
    dates_by_service=collections.defaultdict(list)
    for day,services in calendar.items():
        for service in services:dates_by_service[service].append(day)
    agencies={r.get("agency_id"):r.get("agency_name","") for r in records(z,"agency.txt")}
    routes={}
    for r in records(z,"routes.txt"):
        line=str(r.get("route_short_name","")).strip()
        agency=agencies.get(r.get("agency_id"),"")
        if line not in MODE:continue
        if "sl" not in agency.casefold() and "stockholms lokaltrafik" not in agency.casefold():continue
        routes[r["route_id"]]=(line,agency)
    if {x[0] for x in routes.values()}!=set(MODE):
        raise RuntimeError("Missing SL lines in source: "+str(set(MODE)-{x[0] for x in routes.values()}))
    trips={}
    for r in records(z,"trips.txt"):
        route=routes.get(r.get("route_id"));days=dates_by_service.get(r.get("service_id"),[])
        if route and days:trips[r["trip_id"]]=(route,r.get("trip_headsign",""),r.get("trip_short_name",""),days)
    stations={}
    for r in records(z,"stops.txt"):
        try:coords=[round(float(r["stop_lat"]),6),round(float(r["stop_lon"]),6)]
        except (ValueError,KeyError):continue
        if in_box(coords):stations[r["stop_id"]]=[*coords,r.get("stop_name","")]
    stop_times=collections.defaultdict(list)
    for r in records(z,"stop_times.txt"):
        tid=r.get("trip_id")
        if tid not in trips:continue
        stop=stations.get(r.get("stop_id"))
        if stop is None:raise RuntimeError("SL local stop beyond Stockholm bbox "+str(r.get("stop_id")))
        a,d=clock(r.get("arrival_time","")),clock(r.get("departure_time",""))
        if a is None:a=d
        if d is None:d=a
        if a is None or d is None:raise RuntimeError("Bad SL local stop time "+tid)
        stop_times[tid].append((int(r["stop_sequence"]),[*stop,a,d]))
    out=[]
    for tid,(route,head,train,days) in trips.items():
        stops=[x for _,x in sorted(stop_times[tid],key=lambda x:x[0])]
        if len(stops)<2:raise RuntimeError("SL local short/missing trip "+tid)
        if any(stops[i][3]>stops[i+1][3] or stops[i][4]>stops[i+1][4] for i in range(len(stops)-1)):
            raise RuntimeError("SL local nonmonotonic stop times "+tid)
        first,last=stops[0][4],stops[-1][3]
        if last<=first:raise RuntimeError("SL local invalid trip duration "+tid)
        for day in days:
            base=dt.datetime.combine(day,dt.time(0),ZONE)
            out.append({
                "id":"LOCAL-SL-WEEK:"+day.isoformat()+":"+tid,
                "mode":MODE[route[0]],"line":route[0],"agency":route[1],
                "destination":head or stops[-1][2],"train":train,
                "serviceDay":day.isoformat(),
                "start":int((base+dt.timedelta(seconds=first)).timestamp()),
                "end":int((base+dt.timedelta(seconds=last)).timestamp()),
                "stops":stops,"sourceTripId":tid,
                "source":"GTFS Sverige 2 historical 2026-11-04 week",
                "archiveDay":day.isoformat()
            })
    print("GTFS SL LOCAL WEEK CANDIDATES",len(out),dict(collections.Counter(r["line"] for r in out)),flush=True)
    return out

def rebuild(data,rows):
    assert data.get("metroWeekdaySimulation") and data.get("commuterWeekdaySimulation")
    assert data["counts"]["metro"]==13372 and data["counts"]["commuter"]==3528
    old=data["trips"]
    unchanged=[r for r in old if r["mode"] not in {"tram","localrail","saltsjo"}]
    assert len(unchanged)>=13372+3528
    original_sha=hashlib.sha256(json.dumps(unchanged,sort_keys=True).encode()).hexdigest()
    inventory=collections.defaultdict(dict)
    allshapes={}
    for row in old:
        if row["mode"] not in {"tram","localrail","saltsjo"}:continue
        line=str(row.get("line",""));sid=row.get("shapeId");shape=data["shapes"].get(sid)
        if line in MODE and sid and shape and len(shape)>=2 and row.get("geometryQuality")=="verified-osm-relation":
            inventory[line][sid]=shape;allshapes[sid]=shape
    if set(inventory)!=set(MODE):
        raise RuntimeError("Existing verified OSM geometry missing SL local "+str(set(MODE)-set(inventory)))
    patterns=collections.defaultdict(list);sourcecount=collections.Counter()
    for r in rows:
        patterns[(r["line"],tuple((s[0],s[1],s[2]) for s in r["stops"]))].append(r)
        sourcecount[(r["serviceDay"],r["line"])]+=1
    valid=[];newshape={};unmatched=[]
    for (line,station_pattern),group in patterns.items():
        stops=group[0]["stops"]
        chosen=choose_directional_shape(stops,list(inventory[line].items()),MAX_STOP_ERROR)
        if chosen is None and line in ("27","28","29"):
            # The verified Roslagsbanan parser explicitly documents the ~690 m
            # Enebyberg GTFS vs OSM station offset. Never move any rail vertex.
            for sid,source_shape in inventory[line].items():
                for suffix,geometry in (("",source_shape),(":reverse",list(reversed(source_shape)))):
                    if verified_roslags_match(stops,geometry):
                        chosen=(sid+suffix,geometry)
                        break
                if chosen:break
        if chosen is None:
            chosen=choose_directional_shape(stops,list(allshapes.items()),MAX_STOP_ERROR)
        crossing=None
        if chosen is None and line=="26":
            crossing=stitch_saltsjo_25_26(stops,inventory)
            if crossing:
                chosen=(crossing[0],crossing[1])
                print("VERIFIED SALTSJO AUTHENTIC RAIL JUNCTION",line,len(group),
                      "trips; old OSM parents",crossing[2],"junction gap metres",round(crossing[3],3),flush=True)
        if chosen is None:
            unmatched.append((line,len(group),group[0]["id"],stops[0][2],stops[-1][2]))
            continue
        sid,shape=chosen
        newshape[sid]=shape
        for r in group:
            clone={**r,"shapeId":sid,"osmRelation":sid,
                    "geometryQuality":"verified-osm-relation"}
            if crossing:clone["verifiedJoinedOsmRelations"]=crossing[2]
            valid.append(clone)
    if unmatched:
        print("SL LOCAL UNVERIFIED PATTERNS",len(unmatched),"UNMATCHED TRAINS",sum(x[1] for x in unmatched),flush=True)
        for t in sorted(unmatched,key=lambda x:-x[1])[:100]:print("UNMATCHED",t,flush=True)
        raise RuntimeError("Refusing incomplete historical SL local week; missing verified OSM relation(s)")
    assert len(valid)==len(rows)
    assert len({r["id"] for r in valid})==len(valid)
    coverage=collections.Counter((r["serviceDay"],r["line"]) for r in valid)
    assert coverage==sourcecount
    assert set(r["line"] for r in valid)==set(MODE)
    for line in MODE:
        for day in DAYS:
            if coverage[(day.isoformat(),line)]==0:
                raise RuntimeError("Empty day for SL local line "+line+" "+day.isoformat())
    valid.sort(key=lambda r:(r["serviceDay"],r["start"],r["line"],r["id"]))
    newtrips=unchanged+valid
    result={**data,"trips":newtrips,"shapes":{**data["shapes"],**newshape},
      "counts":{**data["counts"],
        "tram":sum(r["mode"]=="tram" for r in valid),
        "localrail":sum(r["mode"]=="localrail" for r in valid),
        "saltsjo":sum(r["mode"]=="saltsjo" for r in valid)},
      "tramLines":{line:sum(r["line"]==line for r in valid) for line in ("7","12","21","30","31")},
      "roslagsLines":{line:sum(r["line"]==line for r in valid) for line in ("27","28","29")},
      "saltsjoLines":{line:sum(r["line"]==line for r in valid) for line in ("25","26")},
      "localWeekdaySimulation":True,
      "localWeekdaySourceDays":{str(d.weekday()):d.isoformat() for d in DAYS},
      "localWeeklyCoverage":{d.isoformat():{line:coverage[(d.isoformat(),line)] for line in sorted(MODE,key=int)} for d in DAYS},
      "localSourceDisclaimer":"Historically dated SL Nov 2026 representative week; not actual live GPS or guaranteed holiday timetable"}
    assert original_sha==hashlib.sha256(json.dumps([r for r in result["trips"] if r["mode"] not in {"tram","localrail","saltsjo"}],sort_keys=True).encode()).hexdigest()
    assert all(result["shapes"][k]==v for k,v in data["shapes"].items())
    assert len(result["trips"])==len(unchanged)+len(rows)
    for key in data["counts"]:
        if key not in ("tram","localrail","saltsjo"):
            assert result["counts"][key]==data["counts"][key]
    print("SL LOCAL ALL LINES AND ALL WEEKDAYS VERIFIED",json.dumps(result["localWeeklyCoverage"],ensure_ascii=False),flush=True)
    print("SL LOCAL WEEK TOTAL",len(valid),"OLD",len(old)-len(unchanged),flush=True)
    return result

def main():
    data=json.loads(INPUT.read_text(encoding="utf8"))
    with fetch_archive() as z:rows=load_week(z)
    new=rebuild(data,rows)
    output=json.dumps(new,ensure_ascii=False,separators=(",",":"))
    if len(output.encode())>100_000_000:raise RuntimeError("GTFS website JSON exceeds size cap")
    INPUT.write_text(output,encoding="utf8")
    print("SL LOCAL WEEK BUILD COMPLETE",len(output),"bytes",flush=True)

if __name__=="__main__":main()
