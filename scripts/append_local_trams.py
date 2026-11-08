#!/usr/bin/env python3
"""Append Nockebybanan 12 and Lidingöbanan 21 to a frozen three-mode rail build.

Only original OSM public-transport relation coordinates, with each GTFS
station monotonically projected within tolerance. Reverse traversal only
reverses the verified OSM points. Existing trips/shapes remain identical.
"""
import collections
import copy
import json
from pathlib import Path
from refine_osm_routes import BASE, read_json, geometry_from_geojson, project_stops

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"/"rail.json"
CANDIDATES=ROOT/"data"/"local_tram_candidates.json"
LINE_RELATIONS={"12":241383,"21":7779520}
TERMINALS={"12":("alvik","nockeby"),"21":("ropsten","gåshaga")}
MAX_STOP_ERROR=280
MAX_ADDED_TRIPS=1800
MAX_BYTES=58_000_000

def route_geometries(line,reader=read_json):
    rid=LINE_RELATIONS[line]
    result=[]
    try:
        master=reader(BASE+"route_master/"+str(rid))
        for route in master.get("routes",[]):
            geom=geometry_from_geojson(route.get("geojson"))
            if geom and len(geom)>=3:
                result.append((str(route.get("id",rid)),geom))
    except Exception as err:
        print("LOCAL TRAM ROUTE MASTER UNAVAILABLE",line,type(err).__name__,flush=True)
    if result:return result
    try:
        route=reader(BASE+"route/"+str(rid))
        geom=geometry_from_geojson(route.get("geojson"))
        if geom and len(geom)>=3:
            return [(str(rid),geom)]
    except Exception as err:
        print("LOCAL TRAM ROUTE UNAVAILABLE",line,type(err).__name__,flush=True)
    return []

def terminus_direction(line,first,last):
    a,b=TERMINALS[line]
    first=first.casefold().strip()
    last=last.casefold().strip()
    if first.startswith(a) and last.startswith(b):return "out"
    if first.startswith(b) and last.startswith(a):return "back"
    return None

def integrate(base,archive,provider=route_geometries):
    if base.get("scope")!="pendeltag-tunnelbana-tvarbanan":
        raise ValueError("The protected three-mode stable dataset is required")
    old=copy.deepcopy(base)
    grouped=collections.defaultdict(list)
    for trip in archive["trips"]:
        line=str(trip.get("line","")).strip()
        if line not in LINE_RELATIONS or trip.get("mode")!="tram":continue
        stops=trip.get("stops",[])
        if len(stops)<2:continue
        grouped[(line,tuple(s[2] for s in stops))].append(trip)
    shapes={}
    for line in LINE_RELATIONS:
        directional=[]
        for relation,geom in provider(line):
            directional.append((relation,geom))
            directional.append((relation+":reverse",list(reversed(geom))))
        shapes[line]=directional
    accepted=[]
    matched_shapes={}
    direction_counts=collections.Counter()
    discarded=collections.Counter()
    for (line,stations),trips in sorted(grouped.items(),key=lambda x:-len(x[1])):
        direction=terminus_direction(line,stations[0],stations[-1])
        if not direction:
            discarded["partial_or_unexpected_terminal:"+line]+=len(trips)
            continue
        chosen=next(((relation,geom) for relation,geom in shapes[line]
                     if project_stops(trips[0]["stops"],geom,MAX_STOP_ERROR)),None)
        if not chosen:
            discarded["osm_mismatch:"+line]+=len(trips)
            continue
        relation,geometry=chosen
        sid="local-tram-osm:"+line+":"+relation
        for trip in trips:
            if not project_stops(trip["stops"],geometry,MAX_STOP_ERROR):
                discarded["individual_mismatch:"+line]+=1
                continue
            clone={**trip,"mode":"tram","shapeId":sid,
                   "geometryQuality":"verified-osm-relation",
                   "osmRelation":relation,
                   "source":"historical GTFS Sverige 2 + verified OSM local tram"}
            accepted.append(clone)
            matched_shapes[sid]=geometry
            direction_counts[(line,direction)]+=1
    report={line:{"out":direction_counts[(line,"out")],"back":direction_counts[(line,"back")]}
            for line in LINE_RELATIONS}
    print("LOCAL TRAM VALIDATED DIRECTIONS",report,"rejected",dict(discarded),flush=True)
    if any(report[line][d]<=0 for line in LINE_RELATIONS for d in ("out","back")):
        raise ValueError("Nockebybanan/Lidingöbanan missing verified full terminal service in both directions")
    if len(accepted)>MAX_ADDED_TRIPS:
        raise ValueError("Local tram dataset too large; do not silently truncate departures")
    base["trips"].extend(accepted)
    base["shapes"].update(matched_shapes)
    base["counts"]["tram"]=old["counts"]["tram"]+len(accepted)
    base["tramLines"]={**old["tramLines"],
                       **{line:sum(t["line"]==line for t in accepted) for line in LINE_RELATIONS}}
    base["scope"]="pendeltag-tunnelbana-tvarbanan-localtram"
    base["localTramDirections"]=report
    # Strict immutability of ALL prior journeys, routes, lines and counts.
    assert base["trips"][:len(old["trips"])]==old["trips"]
    assert all(base["shapes"][k]==v for k,v in old["shapes"].items())
    assert base["counts"]["commuter"]==old["counts"]["commuter"]
    assert base["counts"]["metro"]==old["counts"]["metro"]
    assert base["counts"]["tram"]-len(accepted)==old["counts"]["tram"]
    assert all(base["tramLines"][k]==v for k,v in old["tramLines"].items())
    return base

def main():
    base=json.loads(DATA.read_text(encoding="utf8"))
    archive=json.loads(CANDIDATES.read_text(encoding="utf8"))
    result=integrate(base,archive)
    text=json.dumps(result,ensure_ascii=False,separators=(",",":"))
    if len(text.encode("utf8"))>MAX_BYTES:
        raise ValueError("Rail dataset exceeds 58 MB size limit")
    DATA.write_text(text,encoding="utf8")
    print("ADDED NÖCKEBY/LIDINGÖ",result["localTramDirections"],"total",result["counts"],flush=True)

if __name__=="__main__":main()
