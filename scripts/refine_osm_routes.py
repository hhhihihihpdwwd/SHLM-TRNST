#!/usr/bin/env python3
"""Best-effort high-confidence OSM route refinement.

Queries *public* OSM public-transport route relations (no API key), at build time.
Only accepts a full directional shape when every GTFS stop projects near it in
monotonic order; otherwise the existing dashed approximation remains unchanged.
An outage or low match rate is never treated as real geometry.
"""
import collections
import json
import math
import os
from pathlib import Path
import urllib.parse
import urllib.request
import urllib.error

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"/"rail.json"
BASE="https://openstreetmap.tools/public_transport_geojson/api/"
MAX_LOOKUPS=80
MAX_FETCHES=110
MODES={"tram":["tram","light_rail"],"metro":["subway"],"commuter":["train"],"rail":["train"]}
MATCH_LIMIT={"tram":220,"metro":300,"commuter":420,"rail":650}
MAX_OUTPUT_BYTES=36_000_000

def distance(a,b):
    dy=(b[0]-a[0])*111100
    dx=(b[1]-a[1])*111100*math.cos(math.radians(a[0]))
    return math.hypot(dx,dy)

def total_length(shape):
    return sum(distance(a,b) for a,b in zip(shape,shape[1:]))

def project_stops(stops,shape,limit):
    """Validate nearest projections and direction; reject zigzags and mismatches."""
    if len(shape)<2 or len(stops)<2:return None
    cumul=[0.0]
    for a,b in zip(shape,shape[1:]):cumul.append(cumul[-1]+distance(a,b))
    previous=-1.
    distances=[]
    for stop in stops:
        p=stop[:2];best=(float("inf"),0.)
        for i in range(1,len(shape)):
            a,b=shape[i-1:i+1]
            scale=111100*math.cos(math.radians(p[0]))
            dx=(b[1]-a[1])*scale;dy=(b[0]-a[0])*111100
            px=(p[1]-a[1])*scale;py=(p[0]-a[0])*111100
            f=max(0,min(1,(dx*px+dy*py)/(dx*dx+dy*dy or 1)))
            along=cumul[i-1]+f*(cumul[i]-cumul[i-1])
            if along+25<previous:continue
            err=math.hypot(px-dx*f,py-dy*f)
            if err<best[0]:best=(err,along)
        if best[0]>limit:return None
        if best[1]+25<previous:return None
        previous=max(previous,best[1]);distances.append(previous)
    if distances[-1]-distances[0]<150:return None
    # Do not accept a route many times longer than the sequence of stop links.
    direct=sum(distance(a[:2],b[:2]) for a,b in zip(stops,stops[1:]))
    if direct<100 or distances[-1]-distances[0]>direct*3.8:return None
    return distances

def read_json(url):
    req=urllib.request.Request(url,headers={"User-Agent":"StockholmRail/0.4 (personal noncommercial rail route validation)","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=9) as resp:
        payload=resp.read(1_500_001)
    if len(payload)>1_500_000:raise ValueError("Remote route payload exceeds limit")
    return json.loads(payload)

def osm_candidates(line, mode, first="", last=""):
    """Retrieve directional route relations without assuming single-character
    line refs are valid search phrases (API requires q length >=2).
    We match ref after searching; returned unrelated lines are discarded.
    """
    found={}
    terms=[]
    if len(line.strip())>=2:
        terms.append(line.strip())
    # Stop names and endpoints are searchable in OSM route names/termini.
    for end in (first,last):
        end=end.strip().replace(" station","").replace(" centrum","")
        if len(end)>=4 and end.casefold() not in {x.casefold() for x in terms}:
            terms.append(end)
    if not terms:
        return []
    for osm_mode in MODES.get(mode,[]):
        for q in terms[:2]:
            url=BASE+"search?"+urllib.parse.urlencode({
                "q":q,"mode":osm_mode,
                "south":59.0,"west":17.45,"north":59.8,"east":18.65})
            try:
                result=read_json(url)
                for c in result.get("routes",[]):
                    if not isinstance(c,dict):continue
                    if c.get("type")=="route_master":continue
                    ref=str(c.get("ref","")).strip()
                    if ref.casefold()==line.casefold() and isinstance(c.get("id"),int):
                        found[c["id"]]=c
            except (urllib.error.URLError, ValueError,TimeoutError,KeyError) as exc:
                print("OSM relation search unavailable",mode,line,type(exc).__name__,flush=True)
            if len(found)>=6:break
    return list(found.values())[:6]

def get_shape(relation):
    rid=relation.get("id")
    if not isinstance(rid,int):return None
    obj=read_json(BASE+"route/"+str(rid))
    geometries=[f.get("geometry") or {} for f in (obj.get("geojson") or {}).get("features",[])]
    lines=[g.get("coordinates") for g in geometries if g.get("type")=="LineString"]
    if not lines:return None
    coords=lines[0]
    if len(coords)>1500:
        stride=(len(coords)-1)/1499
        coords=[coords[round(i*stride)] for i in range(1500)]
    shape=[[round(float(p[1]),6),round(float(p[0]),6)] for p in coords if len(p)>1]
    if len(shape)<2 or not all(58.0<p[0]<61.0 and 16.5<p[1]<20.0 for p in shape):return None
    return shape

# SL Pendeltåg route / route_master IDs from the OpenStreetMap Stockholm
# public transport mapping inventory. Pinning relations avoids ambiguous search.
# https://wiki.openstreetmap.org/wiki/Sweden/Public_transport/Storstockholms_lokaltrafik
PENDELTAG_OSM_RELATIONS={
    "40":2836163,"41":241413,"42X":8506177,"43":241411,
    "43X":8518405,"44":8518402,"48":241414,
}

def geometry_from_geojson(value):
    if not isinstance(value,dict):return None
    shapes=[]
    for feature in value.get("features",[]):
        geom=feature.get("geometry") or {}
        if geom.get("type")=="LineString":shapes.append(geom.get("coordinates",[]))
    if not shapes:return None
    coords=shapes[0]
    if len(coords)>1700:
        step=(len(coords)-1)/1699
        coords=[coords[round(i*step)] for i in range(1700)]
    try:
        shape=[[round(float(c[1]),6),round(float(c[0]),6)] for c in coords]
    except (IndexError,ValueError,TypeError):return None
    if len(shape)<2 or not all(58.0<p[0]<61.0 and 16.5<p[1]<20.0 for p in shape):
        return None
    return shape

def pinned_pendeltag_shapes(line):
    """A documented OSM id may be route_master OR a route. Support both."""
    rid=PENDELTAG_OSM_RELATIONS.get(line.upper())
    if not rid:return []
    # Query route_master first; master includes both directions and branches.
    try:
        data=read_json(BASE+"route_master/"+str(rid))
        result=[]
        for route in data.get("routes",[]):
            geom=geometry_from_geojson(route.get("geojson"))
            if geom:
                result.append((str(route.get("id",rid)),geom))
        if result:return result
    except (urllib.error.URLError,TimeoutError,ValueError,KeyError):
        pass
    try:
        data=read_json(BASE+"route/"+str(rid))
        geom=geometry_from_geojson(data.get("geojson"))
        return [(str(rid),geom)] if geom else []
    except (urllib.error.URLError,TimeoutError,ValueError,KeyError):
        return []

def enrich(dataset):
    trips=dataset["trips"]
    patterns=collections.defaultdict(list)
    for trip in trips:
        if trip.get("mode")!="commuter":continue
        line=str(trip.get("line","")).strip().upper()
        if not line:continue
        key=(line,trip["stops"][0][2],trip["stops"][-1][2])
        patterns[key].append(trip)
    ordered=sorted(patterns.items(),key=lambda item:-len(item[1]))
    shape_cache={}
    successful=collections.Counter()
    diagnostics=collections.Counter()
    # Fetch each documented OSM corridor once, not once per trip.
    for line in sorted({key[0] for key in patterns}):
        shape_cache[line]=pinned_pendeltag_shapes(line)
        diagnostics["pinned_candidates"]+=len(shape_cache[line])
        print("OSM PINNED ROUTES",line,"shapes",len(shape_cache[line]),flush=True)
    # Fallback to search only if a particular line has no pinned geometry.
    for (line,first,last),group in ordered:
        shapes=shape_cache.get(line,[])
        if not shapes:
            found=osm_candidates(line,"commuter",first,last)
            for candidate in found[:5]:
                try:
                    geom=get_shape(candidate)
                    if geom:shapes.append((str(candidate["id"]),geom))
                except (ValueError,TypeError,KeyError,urllib.error.URLError,TimeoutError):
                    continue
            shape_cache[line]=shapes
        if not shapes:
            diagnostics["no_osm_geometry"]+=len(group)
            continue
        winner=None
        best_error=float("inf")
        for relation_id,geom in shapes:
            matched=project_stops(group[0]["stops"],geom,MATCH_LIMIT["commuter"])
            if matched:
                # Prefer the route with the closest overall station alignment.
                err=abs(matched[-1]-matched[0]-sum(distance(a[:2],b[:2]) for a,b in zip(group[0]["stops"],group[0]["stops"][1:])))
                if err<best_error:
                    winner=(relation_id,geom);best_error=err
        if not winner:
            diagnostics["stop_alignment_failed"]+=len(group)
            continue
        rid,geom=winner
        sid="osm:"+rid
        dataset["shapes"][sid]=geom
        for trip in group:
            if project_stops(trip["stops"],geom,MATCH_LIMIT["commuter"]):
                trip["shapeId"]=sid
                trip["geometryQuality"]="verified-osm-relation"
                trip["osmRelation"]=rid
                successful["commuter"]+=1
            else:
                diagnostics["individual_stop_mismatch"]+=1
    dataset["routeRefinement"]={
        "method":"Pinned OSM Pendeltåg route relations with directional stop-matching",
        "verifiedTrips":dict(successful),
        "estimatedTrips":len(trips)-sum(successful.values()),
        "diagnostics":dict(diagnostics),
        "patterns":len(patterns),
    }
    return dataset

def main():
    data=json.loads(DATA.read_text(encoding="utf8"))
    try:
        enriched=enrich(data)
        text=json.dumps(enriched,ensure_ascii=False,separators=(",",":"))
        if len(text.encode())>MAX_OUTPUT_BYTES:raise ValueError("Route geometries exceed size budget")
        DATA.write_text(text,encoding="utf8")
        print("OSM ROUTE MATCH REPORT",enriched["routeRefinement"],flush=True)
    except Exception as exc:
        # Optional enrichment must not corrupt the already valid historical feed.
        print("OSM enrichment unavailable; preserving dashed historical geometry",type(exc).__name__,flush=True)

if __name__=="__main__":main()
