#!/usr/bin/env python3
"""Build a bounded Stockholm rail timetable dataset from licensed GTFS feeds.

Requires GTFS_SL_KEY (Trafiklab GTFS Regional SL); optionally GTFS_SWEDEN_KEY
for national/intercity operators. Never publishes keys. Does not invent geometry:
trips without usable shapes are omitted. Output is a compact static JSON manifest.
"""
import csv
import datetime as dt
import io
import json
import os
from pathlib import Path
import urllib.request
import urllib.parse
import zipfile
from zoneinfo import ZoneInfo
from collections import defaultdict, Counter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "rail.json"
ZONE = ZoneInfo("Europe/Stockholm")
BOX = (59.0, 59.75, 17.55, 18.55)  # core Greater Stockholm
VALID = {"metro", "commuter", "tram", "rail"}
MAX_TRIPS = 16000
MAX_POINTS_PER_SHAPE = 700
MAX_OUTPUT_BYTES = 22_000_000

def mode(route_type, label):
    try: r = int(route_type)
    except (ValueError, TypeError): r = -1
    text = label.lower()
    if r in (1,) or 400 <= r < 500 or "tunnelbana" in text:
        return "metro"
    if r in (0,) or 900 <= r < 1000 or "spårväg" in text or "roslagsbanan" in text or "saltsjöbanan" in text:
        return "tram"
    if "pendeltåg" in text or "pendeltag" in text or "commuter" in text or r in (109,):
        return "commuter"
    if r in (2,) or 100 <= r < 200 or 100 <= r < 110:
        return "rail"
    return None

def read_rows(z, name):
    try:
        with z.open(name) as file:
            return list(csv.DictReader(io.TextIOWrapper(file, encoding="utf-8-sig")))
    except KeyError:
        return []

def active_services(z, days):
    active = {d: set() for d in days}
    for row in read_rows(z, "calendar.txt"):
        try:
            begin=dt.datetime.strptime(row["start_date"], "%Y%m%d").date()
            end=dt.datetime.strptime(row["end_date"], "%Y%m%d").date()
        except (ValueError, KeyError): continue
        for d in days:
            if begin <= d <= end and row.get(d.strftime("%A").lower()) == "1":
                active[d].add(row["service_id"])
    for row in read_rows(z, "calendar_dates.txt"):
        try: d=dt.datetime.strptime(row["date"], "%Y%m%d").date()
        except (ValueError, KeyError): continue
        if d not in active: continue
        if row.get("exception_type") == "1": active[d].add(row["service_id"])
        if row.get("exception_type") == "2": active[d].discard(row["service_id"])
    return active

def parse_seconds(value):
    try:
        parts = [int(x) for x in value.split(":")]
        if len(parts)!=3 or any(p<0 for p in parts) or parts[1]>59 or parts[2]>59: return None
        return parts[0]*3600+parts[1]*60+parts[2]
    except (TypeError, ValueError, AttributeError): return None

def in_box(lat, lon):
    return BOX[0] <= lat <= BOX[1] and BOX[2] <= lon <= BOX[3]

def simplified_shape(pts):
    """Bound the frontend payload without inventing new shape points."""
    if len(pts) <= MAX_POINTS_PER_SHAPE: return pts
    step = (len(pts)-1)/(MAX_POINTS_PER_SHAPE-1)
    return [pts[round(i*step)] for i in range(MAX_POINTS_PER_SHAPE)]

def fetch(url, api_key):
    url += ("&" if "?" in url else "?") + urllib.parse.urlencode({"key":api_key})
    request = urllib.request.Request(url, headers={"User-Agent":"StockholmRail/0.2 (timetable static importer)","Accept-Encoding":"identity"})
    with urllib.request.urlopen(request,timeout=150) as resp:
        blob=resp.read(110_000_000)
    if not zipfile.is_zipfile(io.BytesIO(blob)):
        raise RuntimeError("Not a GTFS zip feed")
    return zipfile.ZipFile(io.BytesIO(blob))

def import_feed(z, source, days, output):
    routes={}
    agency={row.get("agency_id"):row.get("agency_name","") for row in read_rows(z,"agency.txt")}
    for row in read_rows(z,"routes.txt"):
        agency_name=agency.get(row.get("agency_id"),"")
        label=" ".join([row.get("route_short_name",""),row.get("route_long_name",""),agency_name])
        category=mode(row.get("route_type"),label)
        # SL suburban service classification often arrives as rail mode 2.
        if category=="rail" and ("pendeltåg" in label.lower() or "pendel" in label.lower()):
            category="commuter"
        if category in VALID: routes[row.get("route_id")]={
            "mode":category,"line":row.get("route_short_name",""),"name":row.get("route_long_name",""),"agency":agency_name
        }
    stops={}
    for row in read_rows(z,"stops.txt"):
        try: lat,lon=float(row["stop_lat"]),float(row["stop_lon"])
        except (KeyError,ValueError): continue
        stops[row["stop_id"]]=[round(lat,6),round(lon,6),row.get("stop_name","")]
    services=active_services(z,days)
    trips={}
    for row in read_rows(z,"trips.txt"):
        route=routes.get(row.get("route_id"))
        if route is None: continue
        valid_days=[d for d in days if row.get("service_id") in services[d]]
        if valid_days:
            trips[row["trip_id"]]={"route":route,"days":valid_days,"head":row.get("trip_headsign",""),
            "shape":row.get("shape_id",""),"short":row.get("trip_short_name","")}
    stop_times=defaultdict(list)
    for row in read_rows(z,"stop_times.txt"):
        tid=row.get("trip_id")
        if tid not in trips or row.get("stop_id") not in stops:continue
        a=parse_seconds(row.get("arrival_time"))
        b=parse_seconds(row.get("departure_time"))
        if a is None and b is None:continue
        try: seq=int(row.get("stop_sequence",0))
        except ValueError:seq=0
        stop_times[tid].append((seq,row["stop_id"],a if a is not None else b,b if b is not None else a))
    relevant={}
    for tid,points in stop_times.items():
        points.sort()
        coords=[stops[p[1]] for p in points]
        if len(points)>=2 and any(in_box(p[0],p[1]) for p in coords):
            relevant[tid]=points
    wanted_shapes={trips[tid]["shape"] for tid in relevant if trips[tid]["shape"]}
    shape_points=defaultdict(list)
    for row in read_rows(z,"shapes.txt"):
        sid=row.get("shape_id")
        if sid not in wanted_shapes:continue
        try:
            lat,lon=float(row["shape_pt_lat"]),float(row["shape_pt_lon"])
            seq=int(row["shape_pt_sequence"])
        except (KeyError,ValueError):continue
        shape_points[sid].append((seq,[round(lat,6),round(lon,6)]))
    shapes={}
    for sid, pts in shape_points.items():
        pts.sort(key=lambda x:x[0])
        arr=simplified_shape([p[1] for p in pts])
        if len(arr)>1:shapes[sid]=arr
    created=0
    for tid,points in relevant.items():
        trip=trips[tid]
        shape=shapes.get(trip["shape"])
        if not shape:continue
        # No fake shape: project stops onto source polyline only at render.
        trip_stops=[[stops[sid][0],stops[sid][1],stops[sid][2],arr,dep] for _,sid,arr,dep in points]
        for day in trip["days"]:
            if created>=MAX_TRIPS:break
            service_day=dt.datetime.combine(day,dt.time(0),ZONE)
            output.append({
                "id":source+":"+tid+":"+day.isoformat(),
                "mode":trip["route"]["mode"],"line":trip["route"]["line"],
                "agency":trip["route"]["agency"],"destination":trip["head"],
                "train":trip["short"],"serviceDay":day.isoformat(),
                "start":int((service_day+dt.timedelta(seconds=points[0][2])).timestamp()),
                "end":int((service_day+dt.timedelta(seconds=points[-1][3])).timestamp()),
                "stops":trip_stops,
                "shape":shape,
                "source":source
            })
            created+=1
    return created

def main():
    key=os.getenv("GTFS_SL_KEY")
    if not key:raise SystemExit("GTFS_SL_KEY required. Add it as GitHub Actions secret, never commit it.")
    now=dt.datetime.now(ZONE).date()
    days=[now-dt.timedelta(days=1),now,now+dt.timedelta(days=1)]
    sources=[("SL","https://opendata.samtrafiken.se/gtfs/sl/sl.zip",key)]
    sweden=os.getenv("GTFS_SWEDEN_KEY")
    if sweden:sources.append(("SWEDEN","https://opendata.samtrafiken.se/gtfs-sweden/sweden.zip",sweden))
    output=[]
    for name,url,token in sources:
        archive=fetch(url,token)
        count=import_feed(archive,name,days,output)
        print(f"Imported {name}: {count} real scheduled rail trips with GTFS shapes")
    output.sort(key=lambda row:(row["start"],row["id"]))
    if not output:raise RuntimeError("No shape-backed rail trips; refusing to publish empty data.")
    counts=Counter(x["mode"] for x in output)
    if not counts.get("metro") or not (counts.get("commuter") or counts.get("rail")):
        raise RuntimeError(f"Rail mode quality gate failed: {dict(counts)}")
    result={"schema":1,"generated":dt.datetime.now(dt.timezone.utc).isoformat(),
        "timezone":"Europe/Stockholm","type":"scheduled","sources":[s[0] for s in sources],
        "trips":output,"counts":dict(counts)}
    text=json.dumps(result,ensure_ascii=False,separators=(",",":"))
    if len(text.encode())>MAX_OUTPUT_BYTES:raise RuntimeError("Data too large. Decrease output size before publishing.")
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(text,encoding="utf8")
    print("Validated",len(output),"trips and",dict(counts),"bytes",len(text))
if __name__=="__main__":main()
