#!/usr/bin/env python3
"""Tunnelbana extension to a previously verified Pendeltåg dataset.

Reads the unmodified historical candidate snapshot saved before Pendeltåg
route refinement. Uses only OSM metro *route relations*, verified against all
stops of each GTFS trip. Never converts source stop connectors into "tracks".
Appends to the verified Pendeltåg JSON and does not change its rows or shapes.
"""
import collections
import json
from pathlib import Path
from refine_osm_routes import read_json, BASE, project_stops, geometry_from_geojson, choose_directional_shape

ROOT=Path(__file__).resolve().parents[1]
PENDELTAG=ROOT/"data"/"rail.json"
METRO_SOURCE=ROOT/"data"/"metro_candidates.json"
METRO_LINES={"10","11","13","14","17","18","19"}
METRO_MASTERS={"10":6286483,"11":6286484,"13":6286488,"14":6286489,
               "17":6286485,"18":6286486,"19":6286487}
# OSM metro tunnels and station entrances can be offset: tolerate 350 m
# only if stops project in sequence onto the *same* full directional shape.
MAX_STOP_ERROR_METERS=350
MAX_METRO_TRIPS=5500
MAX_OUTPUT_BYTES=48_000_000

def shape_candidates(line,reader=read_json):
    rid=METRO_MASTERS[line]
    try:
        result=reader(BASE+"route_master/"+str(rid))
    except Exception as exc:
        print("METRO OSM MASTER ERROR",line,type(exc).__name__,flush=True)
        return []
    routes=result.get("routes",[])
    shapes=[]
    for route in routes:
        try:
            shape=geometry_from_geojson(route.get("geojson"))
            if shape:
                shapes.append((str(route.get("id",rid)),shape))
        except (ValueError,TypeError,KeyError):
            continue
    return shapes

def append_metro(base,candidates,provider=shape_candidates):
    if base.get("scope")!="pendeltag-only":
        raise ValueError("Only the untouched Pendeltåg foundation may be extended")
    before=json.dumps({"trips":base["trips"],"shapes":base["shapes"]},sort_keys=True)
    metro=[t for t in candidates["trips"] if t.get("mode")=="metro"
           and str(t.get("line","")).strip() in METRO_LINES]
    groups=collections.defaultdict(list)
    for t in metro:
        line=str(t["line"]).strip()
        key=(line,tuple(s[2] for s in t["stops"]))
        groups[key].append(t)
    available={line:provider(line) for line in sorted(METRO_LINES)}
    for line,shapes in available.items():
        print("METRO OSM ROUTE",line,"candidate directional geometries",len(shapes),flush=True)
    appended=[]
    shapes_to_add={}
    verified=collections.Counter()
    directions=collections.Counter()
    for (line,stations),trips in groups.items():
        chosen=choose_directional_shape(trips[0]["stops"],available[line],MAX_STOP_ERROR_METERS)
        if chosen is None:continue
        relation,shape=chosen
        key="metro-osm:"+line+":"+relation
        shapes_to_add[key]=shape
        for t in trips:
            if not project_stops(t["stops"],shape,MAX_STOP_ERROR_METERS):continue
            cloned={**t,"shapeId":key,"geometryQuality":"verified-osm-relation",
                    "osmRelation":relation,"source":"GTFS Sverige 2 historical metro"}
            appended.append(cloned)
            verified[line]+=1
            directions['reversed' if relation.endswith(':reverse') else 'original']+=1
    missing=sorted(METRO_LINES-set(verified))
    print("METRO COVERAGE",dict(verified),"directions",dict(directions),"missing",missing,flush=True)
    if missing:
        raise ValueError("Missing verified Tunnelbana routes for "+",".join(missing)+
                         "; refusing partial or fabricated metro deployment")
    if len(appended)>MAX_METRO_TRIPS:
        # Deterministic cap retains all seven lines by round-robin.
        per_line=collections.defaultdict(list)
        for t in appended:per_line[t["line"]].append(t)
        kept=[]
        while len(kept)<MAX_METRO_TRIPS:
            more=False
            for line in sorted(METRO_LINES):
                if per_line[line]:
                    kept.append(per_line[line].pop(0))
                    more=True
                if len(kept)==MAX_METRO_TRIPS:break
            if not more:break
        appended=kept
    base["trips"].extend(appended)
    base["shapes"].update({key:shapes_to_add[key] for key in {t["shapeId"] for t in appended}})
    base["counts"]["metro"]=len(appended)
    base["scope"]="pendeltag-and-tunnelbana"
    base["metroLines"]=dict(verified)
    base["metroDirections"]=dict(directions)
    base["positionSource"]="historical-timetable-interpolation-not-live-gps"
    original={"trips":base["trips"][:-len(appended)],
              "shapes":{k:v for k,v in base["shapes"].items() if not k.startswith("metro-osm:")}}
    if json.dumps(original,sort_keys=True)!=before:
        raise AssertionError("Pendeltåg foundation changed while merging Metro")
    return base

def main():
    base=json.loads(PENDELTAG.read_text(encoding="utf8"))
    candidates=json.loads(METRO_SOURCE.read_text(encoding="utf8"))
    updated=append_metro(base,candidates)
    output=json.dumps(updated,ensure_ascii=False,separators=(",",":"))
    if len(output.encode())>MAX_OUTPUT_BYTES:
        raise ValueError("Combined dataset exceeds size budget")
    PENDELTAG.write_text(output,encoding="utf8")
    print("VALIDATED INTEGRATION:",updated["counts"],"original Pendeltåg unchanged",flush=True)

if __name__=="__main__":main()
