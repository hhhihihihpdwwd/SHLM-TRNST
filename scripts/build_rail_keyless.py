#!/usr/bin/env python3
"""No-key Stockholm Rail historical timetable importer.

GTFS Sverige 2 public archive has real timetables but NO shapes.txt.
Therefore the built geometry is an explicitly APPROXIMATE stop-to-stop schematic,
never claimed to be a verified track. Archive weekday service patterns are
mapped onto the current weekday for a private representative simulation.
"""
from __future__ import annotations
import collections
import csv
import datetime as dt
import hashlib
import io
import json
import os
import pathlib
import re
import urllib.request
import zipfile
from zoneinfo import ZoneInfo

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"rail.json"
ZONE=ZoneInfo("Europe/Stockholm")
URL="https://data.samtrafiken.se/trafiklab/gtfs-sverige-2/2026/11/sweden-20261104.zip"
SOURCE_START=dt.date(2026,11,4) # actual archived window; do not request unsupported Nov 15 Sunday
# Geographic stop retention must cover ALL Pendeltåg termini, not just central
# Stockholm. In particular Uppsala C (59.86 N) and Nynäshamn (58.90 N)
# were previously truncated by the 59.00..59.80 bounds.
BOX=(58.70,60.10,17.20,19.10)
LIMIT=9000
LIMIT_PER_MODE={"metro":2800,"commuter":2300,"rail":2400,"tram":1500}
MAX_OUTPUT=32_000_000

def records(z,name):
    try:
        with z.open(name) as handle:
            yield from csv.DictReader(io.TextIOWrapper(handle,encoding="utf-8-sig"))
    except KeyError:
        return

def clock(s):
    try:
        h,m,sec=map(int,s.split(":"))
        return h*3600+m*60+sec if 0<=h<=47 and 0<=m<60 and 0<=sec<60 else None
    except (ValueError,AttributeError):
        return None

def in_box(p):
    return BOX[0]<=p[0]<=BOX[1] and BOX[2]<=p[1]<=BOX[3]

TRAM_NAMES=("tvärbanan","tvarbanan","nockebybanan","lidingöbanan","lidingobanan",
            "spårväg city","sparvag city","spårvagn","spårväg","tram","spårvägen")
LOCAL_NAMES=("roslagsbanan","saltsjöbanan","saltsjobanan")
def mode(route_type,label,short="",agency=""):
    try:r=int(route_type)
    except (ValueError,TypeError):r=-1
    t=label.casefold()
    num=short.strip()
    sl=("sl" in agency.casefold() or "stockholms lokaltrafik" in agency.casefold())
    # Prioritise the explicitly named SL tram/light-rail systems: GTFS Sverige 2
    # can encode some urban lines as general railway instead of tram.
    if any(k in t for k in TRAM_NAMES):
        return "tram"
    if any(k in t for k in LOCAL_NAMES):
        return "tram" # grouped as local light rail in the existing tram filter
    if sl and num in {"7","12","21","22","30","31"} and r in (0,2,100,109,900,901):
        return "tram"
    # SL's seven current metro line numbers are unambiguous in rail-only GTFS.
    # Archive variants may encode metro under generic rail type 2.
    if sl and num in {"10","11","13","14","17","18","19"} and (r in (1,2,100) or 400<=r<500):
        return "metro"
    if r==1 or 400<=r<500 or "tunnelbana" in t:return "metro"
    if "pendel" in t or "x60" in t or "commuter" in t or r==109:return "commuter"
    if r==0 or 900<=r<1000:return "tram"
    if r==2 or 100<=r<400:return "rail"
    return None

def service_calendar(z,dates):
    valid={d:set() for d in dates}
    for r in records(z,"calendar.txt"):
        try:
            a=dt.datetime.strptime(r["start_date"],"%Y%m%d").date()
            b=dt.datetime.strptime(r["end_date"],"%Y%m%d").date()
        except (ValueError,KeyError):continue
        for day in dates:
            if a<=day<=b and r.get(day.strftime("%A").lower())=="1":
                valid[day].add(r["service_id"])
    for r in records(z,"calendar_dates.txt"):
        try:day=dt.datetime.strptime(r["date"],"%Y%m%d").date()
        except (ValueError,KeyError):continue
        if day not in valid:continue
        if r.get("exception_type")=="1":valid[day].add(r["service_id"])
        if r.get("exception_type")=="2":valid[day].discard(r["service_id"])
    return valid

def fetch_archive(url=URL):
    if not url.startswith("https://data.samtrafiken.se/trafiklab/gtfs-sverige-2/"):
        raise ValueError("Only the public verified GTFS Sverige 2 historical archive is supported")
    req=urllib.request.Request(url,headers={"User-Agent":"StockholmRail/0.4 personal historic timetable simulator","Accept-Encoding":"identity"})
    with urllib.request.urlopen(req,timeout=240) as response:
        raw=response.read(140_000_001)
    if len(raw)>140_000_000 or not zipfile.is_zipfile(io.BytesIO(raw)):
        raise RuntimeError("Historical archive unavailable or too large")
    return zipfile.ZipFile(io.BytesIO(raw))

def round_robin_service_days(candidates):
    """Preserve each service day, daytime hour and line under per-mode caps.

    The previous sequential cap picked mainly early departures. Even if a day
    had hundreds of valid Metro trains, late evening could show zero vehicles.
    Stratify by day + departure hour + line; interleave each time window before
    the existing mode caps are applied. This does not fabricate GTFS trips.
    """
    buckets=collections.defaultdict(list)
    for row in candidates:
        mode,tid,stops,route,head,short,target,source_day=row
        hour=(stops[0][2]//3600)%24
        line=str(route.get("line",""))
        buckets[(mode,target.isoformat(),hour,line)].append(row)
    for bucket in buckets.values():
        bucket.sort(key=lambda row:(row[2][0][2],row[1]))
    ordered=[]
    from itertools import zip_longest
    for mode in sorted({key[0] for key in buckets}):
        keys=sorted((key for key in buckets if key[0]==mode),
                    key=lambda k:(k[2],k[1],k[3]))
        for layer in zip_longest(*(buckets[key] for key in keys),fillvalue=None):
            ordered.extend(item for item in layer if item is not None)
    return ordered

def build(z,now=None,tram_lines=None):
    now=now or dt.datetime.now(ZONE).date()
    dates=[SOURCE_START+dt.timedelta(days=i) for i in range(7)]
    wanted_days=service_calendar(z,dates)
    agencies={r.get("agency_id"):r.get("agency_name","") for r in records(z,"agency.txt")}
    routes={}
    for r in records(z,"routes.txt"):
        agency=agencies.get(r.get("agency_id"),"")
        short=r.get("route_short_name","")
        long=r.get("route_long_name","")
        m=mode(r.get("route_type")," ".join((short,long,agency)),short,agency)
        # The tram builders must not first consume the global 1,500-trip
        # allowance with unrelated tram lines and yesterday's schedules.
        if tram_lines is not None and not (m=="tram" and short.strip() in tram_lines):
            continue
        if m:routes[r["route_id"]]={"line":short,"agency":agency,"mode":m,"name":long}
    stops={}
    for r in records(z,"stops.txt"):
        try:lat,lon=float(r["stop_lat"]),float(r["stop_lon"])
        except (ValueError,KeyError):continue
        if in_box([lat,lon]):
            stops[r["stop_id"]]=[round(lat,6),round(lon,6),r.get("stop_name","")]
    trips={}
    for r in records(z,"trips.txt"):
        route=routes.get(r.get("route_id"))
        if not route:continue
        valid=[day for day in dates if r.get("service_id") in wanted_days[day]]
        if valid:trips[r["trip_id"]]=(route,r.get("trip_headsign",""),r.get("trip_short_name",""),valid)
    times=collections.defaultdict(list)
    for r in records(z,"stop_times.txt"):
        tid=r.get("trip_id")
        if tid not in trips:continue
        point=stops.get(r.get("stop_id"))
        if not point:continue
        arrive=clock(r.get("arrival_time",""))
        depart=clock(r.get("departure_time",""))
        if arrive is None and depart is None:continue
        try:order=int(r.get("stop_sequence",0))
        except ValueError:order=0
        times[tid].append((order,point,arrive if arrive is not None else depart,depart if depart is not None else arrive))
    # Repeat the historic reference weekday for each of yesterday/today/tomorrow.
    target_dates=[now-dt.timedelta(days=1),now,now+dt.timedelta(days=1)]
    targets=collections.defaultdict(list)
    for day in target_dates:targets[day.weekday()].append(day)
    entries=[]
    shape_library={}
    counts=collections.Counter()
    candidates=[]
    for tid,stop_list in times.items():
        stop_list.sort(key=lambda x:x[0])
        if len(stop_list)<2:continue
        route,head,short,valid=trips[tid]
        if all(stop_list[i][2]<=stop_list[i+1][2] for i in range(len(stop_list)-1)):
            for service_day in valid:
                for target in targets.get(service_day.weekday(),[]):
                    candidates.append((route["mode"],tid,stop_list,route,head,short,target,service_day))
    # Prevent the three-day cap from consuming all trains from yesterday.
    # The old mode->date ordering could create thousands of archived trains
    # but ZERO active trains today, including a blank Tunnelbana at 20:06.
    candidates=round_robin_service_days(candidates)
    for category,tid,stop_list,route,head,short,target,source_day in candidates:
        if counts[category]>=LIMIT_PER_MODE[category] or len(entries)>=LIMIT:continue
        # Consecutive stops connected only schematically; no actual tracks inferred.
        pts=[[st[1][0],st[1][1]] for st in stop_list]
        compact=[pts[0]]
        for point in pts[1:]:
            if point!=compact[-1]:compact.append(point)
        if len(compact)<2:continue
        key=hashlib.sha1(json.dumps(compact,separators=(",",":")).encode()).hexdigest()[:16]
        sid="approx:"+key
        shape_library.setdefault(sid,compact)
        begin=dt.datetime.combine(target,dt.time(0),ZONE)
        arr0,depN=stop_list[0][2],stop_list[-1][3]
        if depN<=arr0:continue
        entries.append({
            "id":f"ARCHIVE:{tid}:{target.isoformat()}",
            "mode":category,"line":route["line"],"agency":route["agency"],
            "destination":head or stop_list[-1][1][2],
            "train":short,"serviceDay":target.isoformat(),
            "start":int((begin+dt.timedelta(seconds=arr0)).timestamp()),
            "end":int((begin+dt.timedelta(seconds=depN)).timestamp()),
            "stops":[[p[0],p[1],p[2],arrival,departure] for _,p,arrival,departure in stop_list],
            "shapeId":sid,"geometryQuality":"approximate-stop-connectors",
            "source":"GTFS Sverige 2 public archive","archiveDay":source_day.isoformat()
        })
        counts[category]+=1
    if not entries:raise RuntimeError("No historic rail trips. Do not publish an empty timetable.")
    data={
        "schema":1,
        "generated":dt.datetime.now(dt.timezone.utc).isoformat(),
        "timezone":"Europe/Stockholm",
        "type":"historical-weekday-simulation",
        "geometryQuality":"approximate-stop-connectors",
        "archiveSource":"2026-11-04",
        "description":"Historischer Wochenfahrplan; gefahrene Strecken sind schematische Verbindungen zwischen Haltestellen, keine Schienen-Trassen",
        "sources":["GTFS Sverige 2 public historical archive"],
        "counts":dict(counts),"shapes":shape_library,"trips":entries
    }
    return data

def main():
    with fetch_archive() as z:
        data=build(z)
    serialized=json.dumps(data,ensure_ascii=False,separators=(",",":"))
    if len(serialized.encode("utf8"))>MAX_OUTPUT:
        raise RuntimeError("Archive representation too large; reduce limit")
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(serialized,encoding="utf8")
    print("KEYLESS HISTORICAL TRAIN BUILD:",len(data["trips"]),"trips",data["counts"],"geometry: approximate")
if __name__=="__main__":main()
