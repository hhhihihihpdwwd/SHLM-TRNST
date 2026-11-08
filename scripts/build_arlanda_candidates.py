#!/usr/bin/env python3
"""Isolated Arlanda Express GTFS-Sverige-2 reference timetable importer.

Filter by real Arlanda Express agency BEFORE selecting trips, so the 2400
generic rail cap cannot silently drop Arlanda trains. Preserve direct archive
stop times and all three stations, including express-only Arlanda Södra/Norra.
These are historical weekday-mapped services, not real-time GPS.
"""
import collections
import datetime as dt
import json
from pathlib import Path
import build_rail_keyless as gtfs

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"arlanda_candidates.json"
REF_START=gtfs.REFERENCE_DAY

def name(s):
    return s.casefold().strip()

def exact_terminal(stops):
    if len(stops)!=3:return None
    names=[name(s[2]) for s in stops]
    city=lambda x:x=="stockholm centralstation"
    south=lambda x:"arlanda södra" in x and "arlanda express" in x
    north=lambda x:"arlanda norra" in x and "arlanda express" in x
    if city(names[0]) and south(names[1]) and north(names[2]):return "to-airport"
    if north(names[0]) and south(names[1]) and city(names[2]):return "to-city"
    return None

def build(z,now):
    dates=[REF_START]
    valid=gtfs.service_calendar(z,dates)
    ag={r["agency_id"]:r.get("agency_name","") for r in gtfs.records(z,"agency.txt")}
    routes={}
    for r in gtfs.records(z,"routes.txt"):
        agency=ag.get(r.get("agency_id"),"")
        if agency.casefold().strip()=="arlanda express" and r.get("route_type") in ("2","100","101"):
            routes[r["route_id"]]={"agency":agency,"train":r.get("route_short_name","")}
    if not routes:raise ValueError("No authentic Arlanda Express rail agency in GTFS")
    stop={}
    for r in gtfs.records(z,"stops.txt"):
        if r.get("stop_name") and any(k in name(r["stop_name"]) for k in ("stockholm centralstation","arlanda södra","arlanda norra")):
            try:lat,lon=float(r["stop_lat"]),float(r["stop_lon"])
            except (ValueError,KeyError):continue
            if 59.2<lat<59.9 and 17.7<lon<18.3:
                stop[r["stop_id"]]=[round(lat,6),round(lon,6),r["stop_name"]]
    tids={}
    for r in gtfs.records(z,"trips.txt"):
        route=routes.get(r.get("route_id"))
        if not route:continue
        days=[d for d in dates if r.get("service_id") in valid[d]]
        if days:tids[r["trip_id"]]=(route,days,r.get("trip_headsign",""))
    times=collections.defaultdict(list)
    for r in gtfs.records(z,"stop_times.txt"):
        tid=r.get("trip_id")
        if tid not in tids:continue
        p=stop.get(r.get("stop_id"))
        if p is None:continue
        a=gtfs.clock(r.get("arrival_time",""))
        d=gtfs.clock(r.get("departure_time",""))
        if a is None and d is None:continue
        try:seq=int(r.get("stop_sequence","0"))
        except ValueError:continue
        times[tid].append((seq,p,a if a is not None else d,d if d is not None else a))
    targets=[now-dt.timedelta(days=1),now,now+dt.timedelta(days=1)]
    trips=[]
    directions=collections.Counter()
    excluded=collections.Counter()
    for tid,stops in times.items():
        stops.sort(key=lambda t:t[0])
        station=[x[1] for x in stops]
        d=exact_terminal(station)
        if d is None:
            excluded[tuple(s[2] for s in station)]+=1
            continue
        train_info,days,head=tids[tid]
        for day in days:
            for target in targets:
                # Repeat the same archived Friday departure every calendar day.
                begin=dt.datetime.combine(target,dt.time(),gtfs.ZONE)
                first=stops[0][2];last=stops[-1][3]
                if last<=first:continue
                trips.append({
                    "id":"ARLANDA-ARCHIVE:"+tid+":"+target.isoformat(),
                    "mode":"rail","line":"Arlanda Express",
                    "agency":"Arlanda Express",
                    "train":train_info["train"],
                    "destination":head or station[-1][2],
                    "serviceDay":target.isoformat(),
                    "start":int((begin+dt.timedelta(seconds=first)).timestamp()),
                    "end":int((begin+dt.timedelta(seconds=last)).timestamp()),
                    "stops":[[s[1][0],s[1][1],s[1][2],s[2],s[3]] for s in stops],
                    "geometryQuality":"awaiting-verified-OSM","shapeId":None,
                    "source":"Historical GTFS Sverige 2, reference "+day.isoformat(),
                    "archiveDay":day.isoformat(),
                    "isLiveGPS":False,
                })
                directions[(target.isoformat(),d)]+=1
    print("ARLANDA ARCHIVED DIRECTIONS",dict(directions),"EXCLUDED",dict(excluded),flush=True)
    if not trips or not any(k[1]=="to-airport" for k in directions) or not any(k[1]=="to-city" for k in directions):
        raise ValueError("Missing correct full three-station Arlanda Express timetable both directions")
    return {"trips":trips,"counts":{"rail":len(trips)},"directions":dict((str(k),v) for k,v in directions.items())}

def main():
    now=dt.datetime.now(gtfs.ZONE).date()
    with gtfs.fetch_archive() as z:data=build(z,now)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(data,ensure_ascii=False,separators=(",",":")),encoding="utf8")
    print("ARLANDA EXPRESS CANDIDATE TRIPS",len(data["trips"]),flush=True)
if __name__=="__main__":main()
