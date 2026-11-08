#!/usr/bin/env python3
"""Append shape-validated Spårväg City 7 to a frozen five-system rail dataset.

Only geometry from OSM route_master 2860817 is accepted, with monotonic
projection of every GTFS stop. All existing journeys, tracks, counts remain
identical. If either terminus direction is missing the build fails closed.
"""
import collections
import copy
import json
from pathlib import Path
from refine_osm_routes import BASE, read_json, geometry_from_geojson, project_stops

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"/"rail.json"
SOURCE=ROOT/"data"/"sparvag_city_candidates.json"
RELATION=2860817
MAX_STOP_ERROR=260
MAX_SIZE=65_000_000
MAX_ADDED=1200

def route_geometries(reader=read_json):
    shapes=[]
    try:
        data=reader(BASE+"route_master/"+str(RELATION))
        for route in data.get("routes",[]):
            g=geometry_from_geojson(route.get("geojson"))
            if g and len(g)>2:shapes.append((str(route.get("id",RELATION)),g))
    except Exception as e:
        print("CITY7 OSM MASTER FAILURE",type(e).__name__,flush=True)
    if shapes:return shapes
    try:
        data=reader(BASE+"route/"+str(RELATION))
        g=geometry_from_geojson(data.get("geojson"))
        if g and len(g)>2:shapes.append((str(RELATION),g))
    except Exception as e:
        print("CITY7 OSM ROUTE FAILURE",type(e).__name__,flush=True)
    return shapes

def terminus(first,last):
    first=first.casefold().strip()
    last=last.casefold().strip()
    west=("t-centralen","sergels torg")
    east=("waldemarsudde",)
    a=any(first.startswith(t) for t in west)
    b=any(last.startswith(t) for t in east)
    c=any(first.startswith(t) for t in east)
    d=any(last.startswith(t) for t in west)
    if a and b:return "out"
    if c and d:return "back"
    return None

def integrate(base,archive,provider=route_geometries):
    if base.get("scope")!="pendeltag-tunnelbana-tvarbanan-localtram":
        raise ValueError("STABLE 02 five-system dataset required")
    frozen=copy.deepcopy(base)
    by_pattern=collections.defaultdict(list)
    for t in archive["trips"]:
        if t.get("mode")!="tram" or str(t.get("line","")).strip()!="7":continue
        stops=t.get("stops") or []
        if len(stops)<2:continue
        by_pattern[tuple(s[2] for s in stops)].append(t)
    directions=[]
    for relation,shape in provider():
        directions.append((relation,shape))
        directions.append((relation+":reverse",list(reversed(shape))))
    added=[]
    shapes={}
    counts=collections.Counter()
    rejected=collections.Counter()
    for stops,trips in sorted(by_pattern.items(),key=lambda x:-len(x[1])):
        d=terminus(stops[0],stops[-1])
        if not d:
            rejected["missing_terminal"]+=len(trips)
            print("CITY7 UNEXPECTED TERMINI",stops[0],"→",stops[-1],len(trips),flush=True)
            continue
        matched=next(((name,geometry) for name,geometry in directions
                     if project_stops(trips[0]["stops"],geometry,MAX_STOP_ERROR)),None)
        if matched is None:
            rejected["geometry_mismatch"]+=len(trips)
            print("CITY7 MISSING TRACK",stops[0],"→",stops[-1],len(trips),flush=True)
            continue
        relation,geometry=matched
        key="sparvag-city-osm:7:"+relation
        for t in trips:
            if not project_stops(t["stops"],geometry,MAX_STOP_ERROR):
                rejected["individual_mismatch"]+=1
                continue
            added.append({**t,"mode":"tram","shapeId":key,
                          "geometryQuality":"verified-osm-relation",
                          "osmRelation":relation,
                          "source":t.get("source","Historical GTFS Sverige 2 + OSM 2860817")})
            shapes[key]=geometry
            counts[d]+=1
        print("CITY7 VERIFIED",d,stops[0],"→",stops[-1],"OSM",relation,flush=True)
    print("CITY7 DIRECTION AUDIT",dict(counts),"REJECTED",dict(rejected),flush=True)
    if counts["out"]<1 or counts["back"]<1:
        raise ValueError("Line 7 lacks complete T-Centralen / Waldemarsudde service in BOTH directions")
    if len(added)>MAX_ADDED:
        raise ValueError("Line 7 exceeds trip budget; refusing silent truncation")
    base["trips"].extend(added)
    base["shapes"].update(shapes)
    base["counts"]["tram"]=frozen["counts"]["tram"]+len(added)
    base["tramLines"]={**frozen["tramLines"],"7":len(added)}
    base["scope"]="pendeltag-tunnelbana-tvarbanan-localtram-city7"
    base["city7Directions"]={"out":counts["out"],"back":counts["back"]}
    assert base["trips"][:len(frozen["trips"])]==frozen["trips"]
    assert all(base["shapes"][k]==v for k,v in frozen["shapes"].items())
    assert base["counts"]["commuter"]==frozen["counts"]["commuter"]
    assert base["counts"]["metro"]==frozen["counts"]["metro"]
    assert base["counts"]["tram"]-len(added)==frozen["counts"]["tram"]
    assert all(base["tramLines"][k]==v for k,v in frozen["tramLines"].items())
    return base

def main():
    base=json.loads(DATA.read_text(encoding="utf8"))
    archive=json.loads(SOURCE.read_text(encoding="utf8"))
    result=integrate(base,archive)
    output=json.dumps(result,ensure_ascii=False,separators=(",",":"))
    if len(output.encode())>MAX_SIZE:raise ValueError("City7 rail dataset exceeds size budget")
    DATA.write_text(output,encoding="utf8")
    print("CITY7 INTEGRATED VERIFIED",result["city7Directions"],"TOTAL",result["counts"],flush=True)

if __name__=="__main__":main()
