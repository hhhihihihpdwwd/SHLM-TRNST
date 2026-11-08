#!/usr/bin/env python3
"""Append only current truncated Saltsjöbanan 25/26 rail services.

Official November 2026 SL: 25 Saltsjö-Järla ↔ Saltsjöbaden;
26 Igelboda ↔ Solsidan. Exclude replacement buses, obsolete rail routes
toward Slussen, and non-rail geometry. All previous trips/shapes unchanged.
"""
import collections
import copy
import json
from pathlib import Path
from refine_osm_routes import BASE,read_json,geometry_from_geojson,project_stops

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"/"rail.json"
ARCHIVE=ROOT/"data"/"saltsjo_candidates.json"
RELATIONS={"25":2705957,"26":2705952}
ENDS={"25":("saltsjö-järla","saltsjöbaden"),
      "26":("igelboda","solsidan")}
MAX_ERROR=320
MAX_TRIPS=1600
MAX_BYTES=75_000_000

def normalize(value):
    s=value.casefold().strip()
    for prefix in ("stockholm ","nacka "):
        if s.startswith(prefix):s=s[len(prefix):]
    return s.replace(" station","").strip()

def direction(line,first,last):
    a,b=ENDS[line]
    x,y=normalize(first),normalize(last)
    if x.startswith(a) and y.startswith(b):return "out"
    if x.startswith(b) and y.startswith(a):return "back"
    return None

def osm_shapes(line,reader=read_json):
    relation=RELATIONS[line]
    result=[]
    try:
        data=reader(BASE+"route_master/"+str(relation))
        for route in data.get("routes",[]):
            geom=geometry_from_geojson(route.get("geojson"))
            if geom and len(geom)>=3:
                result.append((str(route.get("id",relation)),geom))
    except Exception as e:
        print("SALTSJO MASTER UNAVAILABLE",line,type(e).__name__,flush=True)
    if result:return result
    try:
        data=reader(BASE+"route/"+str(relation))
        geom=geometry_from_geojson(data.get("geojson"))
        if geom and len(geom)>=3:result.append((str(relation),geom))
    except Exception as e:
        print("SALTSJO ROUTE UNAVAILABLE",line,type(e).__name__,flush=True)
    return result

def integrate(base,archive,provider=osm_shapes):
    if base.get("scope")!="pendeltag-tunnelbana-tvarbanan-localtram-city7-roslags":
        raise ValueError("Must be built on a complete STABLE 04 dataset")
    frozen=copy.deepcopy(base)
    pattern=collections.defaultdict(list)
    for t in archive["trips"]:
        line=str(t.get("line","")).strip()
        if line not in RELATIONS or t.get("mode")!="tram":continue
        stops=t.get("stops",[])
        if len(stops)<2:continue
        pattern[(line,tuple(s[2] for s in stops))].append(t)
    routes={}
    for line in RELATIONS:
        routes[line]=[]
        for rid,shape in provider(line):
            routes[line].append((rid,shape))
            routes[line].append((rid+":reverse",list(reversed(shape))))
        print("SALTSJO RAIL GEOMETRIES",line,len(routes[line]),flush=True)
    accepted=[];new_shapes={};counts=collections.defaultdict(collections.Counter)
    excluded=collections.Counter()
    for (line,stations),trips in sorted(pattern.items(),key=lambda pair:-len(pair[1])):
        d=direction(line,stations[0],stations[-1])
        if not d:
            excluded["not-current-train-service:"+line]+=len(trips)
            print("SALTSJO EXCLUDE",line,stations[0],"→",stations[-1],len(trips),flush=True)
            continue
        choice=next(((rid,shape) for rid,shape in routes[line]
                     if project_stops(trips[0]["stops"],shape,MAX_ERROR)),None)
        if choice is None:
            excluded["missing-verified-OSM:"+line]+=len(trips)
            print("SALTSJO UNMATCHED",line,stations[0],"→",stations[-1],len(trips),flush=True)
            continue
        rid,shape=choice
        sid="saltsjo-osm:"+line+":"+rid
        for trip in trips:
            if not project_stops(trip["stops"],shape,MAX_ERROR):
                excluded["individual-unmatched:"+line]+=1
                continue
            accepted.append({**trip,"mode":"saltsjo",
                "shapeId":sid,"geometryQuality":"verified-osm-relation",
                "osmRelation":rid,
                "source":trip.get("source","Archived GTFS Sverige 2 + OSM rails"),
                "vehiclePhotoStatus":"illustrative-historic-Saltsjöbanan-train"})
            new_shapes[sid]=shape
            counts[line][d]+=1
        print("SALTSJO VERIFIED",line,d,stations[0],"→",stations[-1],flush=True)
    report={line:{"out":counts[line]["out"],"back":counts[line]["back"]}
            for line in RELATIONS}
    print("SALTSJO DIRECTION REPORT",report,"excluded",dict(excluded),flush=True)
    if any(report[line][d]<=0 for line in RELATIONS for d in ("out","back")):
        raise ValueError("Missing complete verified current Saltsjöbanan direction: "+str(report))
    if len(accepted)>MAX_TRIPS:raise ValueError("Saltsjöbanan count unusually high")
    base["trips"].extend(accepted)
    base["shapes"].update(new_shapes)
    base["counts"]["saltsjo"]=len(accepted)
    base["saltsjoLines"]={line:report[line]["out"]+report[line]["back"] for line in RELATIONS}
    base["saltsjoDirections"]=report
    base["scope"]="pendeltag-tunnelbana-tvarbanan-localtram-city7-roslags-saltsjo"
    assert base["trips"][:len(frozen["trips"])]==frozen["trips"]
    assert all(base["shapes"][k]==v for k,v in frozen["shapes"].items())
    assert all(base["counts"][k]==v for k,v in frozen["counts"].items())
    assert base["tramLines"]==frozen["tramLines"]
    assert base["roslagsLines"]==frozen["roslagsLines"]
    assert base["metroLines"]==frozen["metroLines"]
    return base

def main():
    base=json.loads(DATA.read_text(encoding="utf8"))
    archived=json.loads(ARCHIVE.read_text(encoding="utf8"))
    output=integrate(base,archived)
    payload=json.dumps(output,ensure_ascii=False,separators=(",",":"))
    if len(payload.encode("utf8"))>MAX_BYTES:raise ValueError("Dataset too large")
    DATA.write_text(payload,encoding="utf8")
    print("SALTSJO INTEGRATED",output["saltsjoLines"],flush=True)

if __name__=="__main__":main()
