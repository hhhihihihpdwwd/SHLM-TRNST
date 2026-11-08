#!/usr/bin/env python3
"""Append only real OSM verified Arlanda Express rails (route_master 1966855).

No city-to-airport straight connectors, no commuter Arlanda Central platforms.
Each 3-station archived trip must match the specific actual rail geometry
in travel order, for both Stockholm C -> Södra -> Norra and the return.
STABLE 05 data is preserved byte-for-byte in existing records/shapes/counts.
"""
import collections
import copy
import json
from pathlib import Path
from refine_osm_routes import BASE,read_json,geometry_from_geojson,project_stops
from build_arlanda_candidates import exact_terminal

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"/"rail.json"
CANDIDATES=ROOT/"data"/"arlanda_candidates.json"
OSM_MASTER=1966855
MAX_ERROR=420
MAX_ADDED=1500
MAX_BYTES=80_000_000

def osm_shapes(reader=read_json):
    obj=reader(BASE+"route_master/"+str(OSM_MASTER))
    result=[]
    for r in obj.get("routes",[]):
        rid=str(r.get("id",""))
        geo=geometry_from_geojson(r.get("geojson"))
        if rid and geo and len(geo)>2:
            result.append((rid,geo))
    if not result:
        raise ValueError("Arlanda Express OSM relation 1966855 has no usable actual rails")
    return result

def integrate(base,archive,provider=osm_shapes):
    if base.get("scope")!="pendeltag-tunnelbana-tvarbanan-localtram-city7-roslags-saltsjo":
        raise ValueError("Expected exactly complete STABLE 05 8-system base")
    frozen=copy.deepcopy(base)
    candidates=provider()
    options=[]
    for rid,geometry in candidates:
        options.append((rid,geometry))
        options.append((rid+":reverse",list(reversed(geometry))))
    by_pattern=collections.defaultdict(list)
    for t in archive["trips"]:
        if t.get("agency")!="Arlanda Express" or t.get("mode")!="rail":continue
        if exact_terminal(t.get("stops",[])) is None:continue
        by_pattern[tuple(s[2] for s in t["stops"])].append(t)
    accepted=[];shapes={};report=collections.Counter();rejected=collections.Counter()
    for pattern,trips in sorted(by_pattern.items(),key=lambda pair:-len(pair[1])):
        direction=exact_terminal(trips[0]["stops"])
        choice=next(((rid,shape) for rid,shape in options
                   if project_stops(trips[0]["stops"],shape,MAX_ERROR)),None)
        if choice is None:
            rejected[direction]+=len(trips)
            print("ARLANDA NO VERIFIED OSM",direction,pattern,"trips",len(trips),flush=True)
            continue
        rid,shape=choice
        sid="arlanda-express-osm:"+rid
        for t in trips:
            if project_stops(t["stops"],shape,MAX_ERROR) is None:
                rejected[direction]+=1
                continue
            accepted.append({**t,"mode":"express","line":"Arlanda Express","shapeId":sid,
                "geometryQuality":"verified-osm-relation",
                "osmRelation":rid,"vehicleModel":"X3","vehiclePhotoStatus":"approved-X3-photo",
                "source":t.get("source","GTFS Sverige 2 archived timetable")})
            shapes[sid]=shape
            report[direction]+=1
        print("ARLANDA VERIFIED",direction,pattern,"OSM",rid,"N",len(trips),flush=True)
    if report["to-airport"]<1 or report["to-city"]<1:
        raise ValueError("Arlanda Express lacks verified full 3-stop OSM geometry in both directions: "+str(dict(report)))
    if len(accepted)>MAX_ADDED:raise ValueError("Arlanda Express candidate cap exceeded")
    base["trips"].extend(accepted)
    base["shapes"].update(shapes)
    base["counts"]["express"]=len(accepted)
    base["arlandaDirections"]={"to-airport":report["to-airport"],"to-city":report["to-city"]}
    base["scope"]="pendeltag-tunnelbana-tvarbanan-localtram-city7-roslags-saltsjo-arlanda"
    assert base["trips"][:len(frozen["trips"])]==frozen["trips"]
    assert all(base["shapes"][k]==v for k,v in frozen["shapes"].items())
    assert all(base["counts"][k]==v for k,v in frozen["counts"].items())
    assert base["metroLines"]==frozen["metroLines"]
    assert base["tramLines"]==frozen["tramLines"]
    assert base["roslagsLines"]==frozen["roslagsLines"]
    assert base["saltsjoLines"]==frozen["saltsjoLines"]
    print("ARLANDA VERIFIED DIRECTIONS",dict(report),"REJECTED",dict(rejected),flush=True)
    return base

def main():
    previous=json.loads(DATA.read_text(encoding="utf8"))
    candidates=json.loads(CANDIDATES.read_text(encoding="utf8"))
    output=integrate(previous,candidates)
    payload=json.dumps(output,ensure_ascii=False,separators=(",",":"))
    if len(payload.encode())>MAX_BYTES:raise ValueError("Exceeds rail file size budget")
    DATA.write_text(payload,encoding="utf8")
    print("ARLANDA INTEGRATED",output["counts"]["express"],"TOTAL",output["counts"],flush=True)
if __name__=="__main__":main()
