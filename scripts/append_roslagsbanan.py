#!/usr/bin/env python3
"""Append only full-length, direction-verified Roslagsbanan 27/28/29 to STABLE 03.
No changes to existing six-system trips, geometry, counts, UI or engine.
OSM route masters from the documented SL OSM inventory; each GTFS station
must project monotonically onto real rail vertices in a single direction.
"""
import collections
import copy
import json
from pathlib import Path
from refine_osm_routes import BASE,read_json,geometry_from_geojson,project_stops

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"/"rail.json"
ARCHIVE=ROOT/"data"/"roslags_candidates.json"
RELATIONS={"27":11151437,"28":11151439,"29":11151441}
ENDS={"27":("kårsta","ormsta","lindholmen"),"28":("österskär","åkersberga"),"29":("näsbypark",)}
MAX_STOP_ERROR=420
MAX_TOTAL=65_000_000
MAX_ADDED=2000

def name(s):
    return s.casefold().strip().removeprefix("stockholm ").replace(" station","").strip()

def direction(line,first,last):
    a,b=name(first),name(last)
    def is_central(x):return x.startswith("stockholms östra") or x=="östra" or x.startswith("östra station")
    def is_outer(x):return any(x.startswith(c) for c in ENDS[line])
    if is_central(a) and is_outer(b):return "out"
    if is_outer(a) and is_central(b):return "back"
    return None

def verified_match(stops,shape):
    """Validate whole original OSM rail shape, with one documented exception.

    GTFS Enebyberg station point and OSM 27/28 route relation differ by
    roughly 690m. This exception does NOT add/shift a railway vertex:
    the published train stays on the untouched OSM polyline. We still require
    every other stop to be <=420m away, correct stop ordering, and the
    original full-stop sequence to pass at <=750m overall.
    """
    if project_stops(stops,shape,MAX_STOP_ERROR):
        return True
    eneby=[s for s in stops if "enebyberg" in s[2].casefold()]
    if len(eneby)!=1:return False
    return (project_stops(stops,shape,750) is not None
            and project_stops([s for s in stops if s not in eneby],
                              shape,MAX_STOP_ERROR) is not None)

def osm_shapes(line,reader=read_json):
    rid=RELATIONS[line]
    found=[]
    try:
        master=reader(BASE+"route_master/"+str(rid))
        for r in master.get("routes",[]):
            geom=geometry_from_geojson(r.get("geojson"))
            if geom and len(geom)>2:found.append((str(r.get("id",rid)),geom))
    except Exception as ex:
        print("ROSLAG OSM MASTER UNAVAILABLE",line,type(ex).__name__,flush=True)
    if found:return found
    try:
        route=reader(BASE+"route/"+str(rid))
        geom=geometry_from_geojson(route.get("geojson"))
        if geom and len(geom)>2:found.append((str(rid),geom))
    except Exception as ex:
        print("ROSLAG OSM ROUTE UNAVAILABLE",line,type(ex).__name__,flush=True)
    return found

def integrate(base,archive,provider=osm_shapes):
    if base.get("scope")!="pendeltag-tunnelbana-tvarbanan-localtram-city7":
        raise ValueError("Expected unchanged STABLE 03 six-system dataset")
    original=copy.deepcopy(base)
    patterns=collections.defaultdict(list)
    for trip in archive["trips"]:
        line=str(trip.get("line","")).strip()
        if line not in RELATIONS or trip.get("mode")!="tram":continue
        stops=trip.get("stops") or []
        if len(stops)<2:continue
        patterns[(line,tuple(stop[2] for stop in stops))].append(trip)
    candidates={}
    for line in RELATIONS:
        candidates[line]=[]
        for relation,shape in provider(line):
            candidates[line].append((relation,shape))
            candidates[line].append((relation+":reverse",list(reversed(shape))))
        print("ROSLAG OSM LINE",line,"directional tracks",len(candidates[line]),flush=True)
    additions=[]
    new_shapes={}
    full_kårsta=collections.Counter()
    full_österskär=collections.Counter()
    report=collections.defaultdict(collections.Counter)
    rejected=collections.Counter()
    for (line,stops),trips in sorted(patterns.items(),key=lambda x:-len(x[1])):
        d=direction(line,stops[0],stops[-1])
        if not d:
            rejected["wrong_terminals:"+line]+=len(trips)
            print("ROSLAG TERMINALS NOT FULL",line,stops[0],"→",stops[-1],len(trips),flush=True)
            continue
        winner=next(((rel,shape) for rel,shape in candidates[line]
                   if verified_match(trips[0]["stops"],shape)),None)
        if winner is None:
            rejected["no_verified_track:"+line]+=len(trips)
            print("ROSLAG NO MATCH",line,stops[0],"→",stops[-1],len(trips),flush=True)
            continue
        rel,shape=winner
        sid="roslags-osm:"+line+":"+rel
        for trip in trips:
            if not verified_match(trip["stops"],shape):
                rejected["individual_stop_mismatch:"+line]+=1
                continue
            additions.append({**trip,"mode":"localrail","shapeId":sid,
                   "geometryQuality":"verified-osm-relation",
                   "osmRelation":rel,
                   "vehiclePhotoStatus":"illustrative-X10p-or-X15p-unconfirmed",
                   "stopAlignmentCaveat":"GTFS Enebyberg ~690m from OSM route geometry"
                     if any("enebyberg" in stop[2].casefold() for stop in trip["stops"]) else None,
                   "source":trip.get("source","Historical GTFS + real OSM Roslagsbanan tracks")})
            new_shapes[sid]=shape
            report[line][d]+=1
            if line=="27" and any("kårsta" in name(n) for n in (stops[0],stops[-1])):
                full_kårsta[d]+=1
            if line=="28" and any("österskär" in name(n) for n in (stops[0],stops[-1])):
                full_österskär[d]+=1
        print("ROSLAG VERIFIED",line,d,stops[0],"→",stops[-1],"N",len(trips),flush=True)
    counts={line:{"out":report[line]["out"],"back":report[line]["back"]}
            for line in RELATIONS}
    print("ROSLAG BIDIRECTIONAL FULL TERMINALS",counts,"rejected",dict(rejected),flush=True)
    if any(counts[l][d]<1 for l in RELATIONS for d in ("out","back")):
        raise ValueError("Missing full verified Roslagsbanan 27/28/29 line direction/endpoint: "+str(counts))
    print("ROSLAG KÅRSTA FULL-TERMINAL",dict(full_kårsta),flush=True)
    if full_kårsta["out"]<1 or full_kårsta["back"]<1:
        raise ValueError("Roslagsbanan 27 missing the full Kårsta terminus in one direction")
    print("ROSLAG ÖSTERSKÄR FULL-TERMINAL",dict(full_österskär),flush=True)
    if full_österskär["out"]<1 or full_österskär["back"]<1:
        raise ValueError("Roslagsbanan 28 missing full Österskär terminus in one direction")
    if len(additions)>MAX_ADDED:raise ValueError("Roslagsbanan over trip size budget; no silent truncation")
    base["trips"].extend(additions)
    base["shapes"].update(new_shapes)
    base["counts"]["localrail"]=len(additions)
    base["roslagsLines"]={line:counts[line]["out"]+counts[line]["back"] for line in RELATIONS}
    base["roslagsDirections"]=counts
    base["scope"]="pendeltag-tunnelbana-tvarbanan-localtram-city7-roslags"
    assert base["trips"][:len(original["trips"])]==original["trips"]
    assert all(base["shapes"][k]==v for k,v in original["shapes"].items())
    assert all(base["counts"][k]==v for k,v in original["counts"].items())
    assert base["tramLines"]==original["tramLines"]
    assert base["metroLines"]==original["metroLines"]
    return base

def main():
    previous=json.loads(DATA.read_text(encoding="utf8"))
    candidate=json.loads(ARCHIVE.read_text(encoding="utf8"))
    result=integrate(previous,candidate)
    payload=json.dumps(result,ensure_ascii=False,separators=(",",":"))
    if len(payload.encode("utf8"))>MAX_TOTAL:
        raise ValueError("Rail data size limit exceeded; abort safely")
    DATA.write_text(payload,encoding="utf8")
    print("ROSLAG ADDED",result["roslagsLines"],"TOTAL",result["counts"],flush=True)

if __name__=="__main__":main()
