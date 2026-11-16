#!/usr/bin/env python3
"""Rebuild *all* scheduled Tunnelbana trains for a complete historical week.

Only replaces metro records in the archived STABLE21 website. Non-metro
trips, OSM paths, photos, controls and their order are kept byte-equivalent.
A missing train/OSM alignment is fatal: never silently publish partial metro.
This remains a WEEKLY HISTORICAL simulation, not current SL GPS or holiday data.
"""
from __future__ import annotations
import argparse
import collections
import datetime as dt
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from build_rail_keyless import (
    SOURCE_START, BOX, clock, fetch_archive, in_box, mode, records,
    service_calendar,
)
from refine_osm_routes import choose_directional_shape

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "website/data/rail.json"
LINES = {"10","11","13","14","17","18","19"}
DAYS = [SOURCE_START + dt.timedelta(days=i) for i in range(7)]
ZONE = ZoneInfo("Europe/Stockholm")
MAX_STOP_ERROR_METRES = 350

def gtfs_metro_week(archive):
    available = service_calendar(archive, DAYS)
    agencies = {r.get("agency_id"): r.get("agency_name","") for r in records(archive,"agency.txt")}
    routes = {}
    for r in records(archive,"routes.txt"):
        short = r.get("route_short_name","").strip()
        agency = agencies.get(r.get("agency_id"),"")
        if short not in LINES: continue
        if mode(r.get("route_type")," ".join((short,r.get("route_long_name",""),agency)),short,agency)!="metro": continue
        routes[r["route_id"]] = (short,agency)
    if {line for line,_ in routes.values()} != LINES:
        raise RuntimeError("GTFS source missing Tunnelbana line(s): "+repr(LINES-{line for line,_ in routes.values()}))
    service_days = collections.defaultdict(list)
    for day,ids in available.items():
        for service_id in ids: service_days[service_id].append(day)
    trips = {}
    for row in records(archive,"trips.txt"):
        route = routes.get(row.get("route_id"))
        if route is None: continue
        days = service_days.get(row.get("service_id"))
        if not days: continue
        trips[row["trip_id"]] = (route, row.get("trip_headsign",""),row.get("trip_short_name",""),days)
    stops = {}
    for row in records(archive,"stops.txt"):
        try: coord = [round(float(row["stop_lat"]),6), round(float(row["stop_lon"]),6)]
        except (KeyError,ValueError): continue
        if in_box(coord):
            stops[row["stop_id"]] = [*coord,row.get("stop_name","")]
    stop_times = collections.defaultdict(list)
    for row in records(archive,"stop_times.txt"):
        tid = row.get("trip_id")
        if tid not in trips: continue
        point = stops.get(row.get("stop_id"))
        if point is None: raise RuntimeError("Metro stop outside retained Stockholm geometry: "+str(row.get("stop_id")))
        ar, dep = clock(row.get("arrival_time","")),clock(row.get("departure_time",""))
        if ar is None: ar = dep
        if dep is None: dep = ar
        if ar is None or dep is None: raise RuntimeError("Metro GTFS invalid stop time for "+tid)
        stop_times[tid].append((int(row["stop_sequence"]),[*point,ar,dep]))
    rows=[]
    for tid,(route,head,train,days) in trips.items():
        stops = [s for _,s in sorted(stop_times[tid],key=lambda x:x[0])]
        if len(stops)<2: raise RuntimeError("Metro GTFS missing stops "+tid)
        if any(stops[i][3]>stops[i+1][3] or stops[i][4]>stops[i+1][4] for i in range(len(stops)-1)):
            raise RuntimeError("Metro GTFS nonmonotonic times "+tid)
        for day in days:
            begin = dt.datetime.combine(day,dt.time(0),ZONE)
            first,last = stops[0][4],stops[-1][3]
            if last<=first: raise RuntimeError("Metro GTFS bad trip duration "+tid)
            rows.append({
                "id":"METRO-WEEK:"+day.isoformat()+":"+tid,
                "mode":"metro","line":route[0],"agency":route[1],
                "destination":head or stops[-1][2],"train":train,
                "serviceDay":day.isoformat(),
                "start":int((begin+dt.timedelta(seconds=first)).timestamp()),
                "end":int((begin+dt.timedelta(seconds=last)).timestamp()),
                "stops":stops,
                "sourceTripId":tid,
                "source":"GTFS Sverige 2 historical timetable, 2026-11-04 archive",
                "archiveDay":day.isoformat()
            })
    if not rows: raise RuntimeError("Zero historical metro trips")
    return rows

def rebuild(dataset,gtfs_rows):
    if not dataset.get("scope","").endswith("-intl-four"):
        raise RuntimeError("Only verified STABLE21 16-system base is supported")
    original = dataset["trips"]
    before_nonmetro = [r for r in original if r.get("mode")!="metro"]
    before_hash = hashlib.sha256(json.dumps(before_nonmetro,sort_keys=True).encode()).hexdigest()
    shapes = {}
    for key,shape in dataset["shapes"].items():
        if key.startswith("metro-osm:") and len(shape)>=2:
            line=key.split(":")[1]
            if line in LINES: shapes.setdefault(line,[]).append((key,shape))
    if set(shapes)!=LINES: raise RuntimeError("Existing verified OSM shapes missing lines "+repr(LINES-set(shapes)))
    patterns = collections.defaultdict(list)
    expected = collections.Counter()
    for row in gtfs_rows:
        pattern=(row["line"],tuple((s[0],s[1],s[2]) for s in row["stops"]))
        patterns[pattern].append(row)
        expected[(row["serviceDay"],row["line"])] += 1
    validated=[]; extra_shapes={}; failures=[]
    for (line,points),rows in patterns.items():
        chosen=choose_directional_shape(rows[0]["stops"],shapes[line],MAX_STOP_ERROR_METRES)
        if chosen is None:
            failures.append((line,len(rows),rows[0]["id"],rows[0]["stops"][0][2],rows[0]["stops"][-1][2]))
            continue
        sid,shape=chosen
        # A reversed existing OSM relation is still real geometry, not an invented track.
        extra_shapes[sid]=shape
        for row in rows:
            validated.append({**row,"shapeId":sid,
                              "geometryQuality":"verified-osm-relation",
                              "osmRelation":sid.removeprefix("metro-osm:")})
    if failures:
        print("UNMATCHED METRO STOP PATTERNS",len(failures),"TRAINS",sum(x[1] for x in failures),flush=True)
        for row in sorted(failures,key=lambda x:-x[1])[:30]:print("UNMATCHED",row,flush=True)
        raise RuntimeError("Refusing incomplete Tunnelbana build: "+str(sum(x[1] for x in failures))+" train(s) lack verified OSM shape")
    actual=collections.Counter((row["serviceDay"],row["line"]) for row in validated)
    assert actual==expected,("Dropped historical metro journeys",expected-actual)
    assert len(set(row["id"] for row in validated))==len(validated)
    for day in DAYS:
        for line in LINES:
            if actual[(day.isoformat(),line)]==0:
                raise RuntimeError("No trains for "+line+" "+day.isoformat())
    validated.sort(key=lambda r:(r["serviceDay"],r["start"],r["line"],r["id"]))
    output={**dataset,"trips":before_nonmetro+validated}
    output["shapes"]={**dataset["shapes"],**extra_shapes}
    output["counts"]={**dataset["counts"],"metro":len(validated)}
    output["metroLines"]=dict(collections.Counter(r["line"] for r in validated))
    output["metroWeekdaySimulation"]=True
    output["metroWeekdaySourceDays"]={str(d.weekday()):d.isoformat() for d in DAYS}
    output["metroWeeklyCoverage"]={d.isoformat():{line:actual[(d.isoformat(),line)] for line in sorted(LINES)} for d in DAYS}
    output["metroSourceDisclaimer"]="Archived representative Mon-Sun service, not live GPS, future public-holiday or disruption timetable"
    after_hash=hashlib.sha256(json.dumps([r for r in output["trips"] if r["mode"]!="metro"],sort_keys=True).encode()).hexdigest()
    assert before_hash==after_hash
    assert all(output["shapes"][k]==v for k,v in dataset["shapes"].items())
    for mode_name in set(r["mode"] for r in before_nonmetro):
        assert output["counts"][mode_name]==dataset["counts"][mode_name]
    print("GTFS METRO ALL 7 DAYS COVERED",json.dumps(output["metroWeeklyCoverage"],ensure_ascii=False,sort_keys=True),flush=True)
    print("SOURCE TRIPS",len(gtfs_rows),"VERIFIED",len(validated),"OLD METRO",len(original)-len(before_nonmetro),flush=True)
    print("NON-METRO SHA256 UNCHANGED",after_hash,flush=True)
    return output

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",type=Path,default=SOURCE)
    parser.add_argument("--output",type=Path,default=SOURCE)
    args=parser.parse_args()
    data=json.loads(args.input.read_text(encoding="utf8"))
    with fetch_archive() as archive: rows=gtfs_metro_week(archive)
    new=rebuild(data,rows)
    payload=json.dumps(new,ensure_ascii=False,separators=(",",":"))
    if len(payload.encode("utf8"))>95_000_000:
        raise RuntimeError("GitHub Pages data budget exceeded; refuse to publish")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(payload,encoding="utf8")
    print("METRO WEEKLY BUILD SUCCESS",len(payload),"bytes",flush=True)

if __name__=="__main__":main()
