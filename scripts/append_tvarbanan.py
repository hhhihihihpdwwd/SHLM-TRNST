#!/usr/bin/env python3
"""Add only verified Tvärbanan 30/31 to the already-tested Pendeltåg+Metro.

Historical GTFS stop times are read from the SAME source snapshot used by
the foundation. OSM route_master relations provide actual tramway geometry.
A tram trip is accepted only when stops project monotonically onto one
continuous, directional OSM rail relation. No synthetic straight connectors.
"""
import collections
import copy
import json
from pathlib import Path
from refine_osm_routes import BASE, read_json, geometry_from_geojson, project_stops

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"data"/"metro_candidates.json"
OUTPUT=ROOT/"data"/"rail.json"
TVARBANAN={"30":241384,"31":11997852}
STOP_LIMIT_METERS=280
MAX_TRAM_TRIPS=1800
MAX_DATA_BYTES=54_000_000

def route_shapes(line,reader=read_json):
    """OSM Wiki lists the documented route_master ID of both Tvärbanan lines."""
    rid=TVARBANAN[line]
    output=[]
    try:
        data=reader(BASE+"route_master/"+str(rid))
        for route in data.get("routes",[]):
            shape=geometry_from_geojson(route.get("geojson"))
            if shape and len(shape)>=3:
                output.append((str(route.get("id",rid)),shape))
    except Exception as exc:
        print("TRAM OSM MASTER",line,type(exc).__name__,flush=True)
    if output:return output
    # Some mapping deployments expose the OSM relation as a direct route.
    try:
        data=reader(BASE+"route/"+str(rid))
        shape=geometry_from_geojson(data.get("geojson"))
        if shape:return [(str(rid),shape)]
    except Exception as exc:
        print("TRAM OSM ROUTE",line,type(exc).__name__,flush=True)
    return []

def integrate(base,archive,provider=route_shapes):
    if base.get("scope")!="pendeltag-and-tunnelbana":
        raise ValueError("Validated Pendeltåg+Tunnelbana foundation required")
    before=copy.deepcopy(base)
    by_pattern=collections.defaultdict(list)
    for trip in archive["trips"]:
        line=str(trip.get("line","")).strip()
        if line not in TVARBANAN or trip.get("mode")!="tram":continue
        if not trip.get("stops") or len(trip["stops"])<2:continue
        key=(line,tuple(stop[2] for stop in trip["stops"]))
        by_pattern[key].append(trip)
    # A route_master can expose only one oriented path for bidirectional tram
    # tracks. Test the reverse orientation of *the same verified OSM track*
    # against the entire ordered station list; never invent connecting segments.
    shape_map={}
    for line in TVARBANAN:
        base_shapes=provider(line)
        variants=[]
        for relation,shape in base_shapes:
            variants.append((relation,shape))
            variants.append((relation+":reverse",list(reversed(shape))))
        shape_map[line]=variants
    print("TVARBANAN SOURCE PATTERNS",len(by_pattern),
          "OSM ROUTES",{line:len(v) for line,v in shape_map.items()},flush=True)
    additions=[]
    new_shapes={}
    verified=collections.Counter()
    matched_patterns=collections.Counter()
    rejected=collections.Counter()
    for (line,stations),trips in sorted(by_pattern.items(),key=lambda item:-len(item[1])):
        winner=None
        for relation,shape in shape_map[line]:
            if project_stops(trips[0]["stops"],shape,STOP_LIMIT_METERS):
                winner=(relation,shape)
                break
        if not winner:
            print("TRAM PATTERN REJECTED",line,"FROM",stations[0],"TO",stations[-1],"N",len(trips),flush=True)
            rejected[line]+=len(trips)
            continue
        relation,shape=winner
        print("TRAM PATTERN VERIFIED",line,"FROM",stations[0],"TO",stations[-1],"N",len(trips),"OSM",relation,flush=True)
        matched_patterns[line]+=1
        shape_id="tvarbanan-osm:"+line+":"+relation
        for trip in trips:
            if not project_stops(trip["stops"],shape,STOP_LIMIT_METERS):
                rejected[line]+=1
                continue
            clone={**trip,"mode":"tram","shapeId":shape_id,
                   "geometryQuality":"verified-osm-relation",
                   "osmRelation":relation,"source":"historical GTFS Sverige 2 + OSM Tvärbanan"}
            additions.append(clone)
            new_shapes[shape_id]=shape
            verified[line]+=1
    print("TVARBANAN VERIFIED",dict(verified),"PATTERNS",dict(matched_patterns),
          "REJECTED",dict(rejected),flush=True)
    required_endpoints={
       "30":{("solna","sickla"),("sickla","solna")},
       "31":{("bromma flygplats","alvik"),("alvik","bromma flygplats")}
    }
    passed=collections.defaultdict(set)
    for trip in additions:
        first=trip["stops"][0][2].lower()
        last=trip["stops"][-1][2].lower()
        if trip["line"]=="30" and {"solna","sickla"} <= {p.split()[0] for p in (first,last)}:
            passed["30"].add(("solna","sickla") if first.startswith("solna") else ("sickla","solna"))
        if trip["line"]=="31" and (
            ("bromma flygplats" in first and "alvik" in last) or
            ("alvik" in first and "bromma flygplats" in last)):
            passed["31"].add(("bromma flygplats","alvik") if first.startswith("bromma") else ("alvik","bromma flygplats"))
    print("TVARBANAN TERMINAL DIRECTIONS",dict(passed),flush=True)
    if any(not required_endpoints[line].issubset(passed[line]) for line in TVARBANAN):
        raise ValueError("A complete verified terminus-to-terminus trip is missing in one or more directions")
    if not all(verified.get(line,0)>0 for line in TVARBANAN):
        raise ValueError("Missing verified Tvärbanan line(s): "+
                         ",".join(l for l in TVARBANAN if not verified[l]))
    if len(additions)>MAX_TRAM_TRIPS:
        # Preserve both lines: no accidental favouritism if archival service is dense.
        per_line=collections.defaultdict(list)
        for trip in additions:per_line[trip["line"]].append(trip)
        chosen=[]
        while len(chosen)<MAX_TRAM_TRIPS:
            progress=False
            for line in sorted(TVARBANAN):
                if per_line[line]:
                    chosen.append(per_line[line].pop(0));progress=True
                if len(chosen)>=MAX_TRAM_TRIPS:break
            if not progress:break
        additions=chosen
    base["trips"].extend(additions)
    base["shapes"].update({sid:new_shapes[sid] for sid in {t["shapeId"] for t in additions}})
    base["counts"]["tram"]=len(additions)
    base["tramLines"]=dict(collections.Counter(t["line"] for t in additions))
    base["scope"]="pendeltag-tunnelbana-tvarbanan"
    base["positionSource"]="historical-timetable-interpolation-not-live-gps"
    # Exact structural preservation of every existing commuter & metro trip.
    assert base["trips"][:len(before["trips"])]==before["trips"]
    assert all(base["shapes"].get(k)==v for k,v in before["shapes"].items())
    assert base["counts"]["commuter"]==before["counts"]["commuter"]
    assert base["counts"]["metro"]==before["counts"]["metro"]
    assert base["metroLines"]==before["metroLines"]
    return base

def main():
    base=json.loads(OUTPUT.read_text(encoding="utf8"))
    archive=json.loads(SOURCE.read_text(encoding="utf8"))
    data=integrate(base,archive)
    serialized=json.dumps(data,ensure_ascii=False,separators=(",",":"))
    if len(serialized.encode("utf8"))>MAX_DATA_BYTES:
        raise ValueError("Combined timetable exceeds configured size budget")
    OUTPUT.write_text(serialized,encoding="utf8")
    print("RAIL THREE-MODE BUILD VALID:",data["counts"],"TVÄRBANAN:",data["tramLines"],flush=True)

if __name__=="__main__":main()
