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

def enrich(dataset):
    trips=dataset["trips"]
    # Prioritise tram, where accurate rails make the largest visual difference.
    mode_priority={"commuter":0,"tram":1,"metro":2,"rail":3}
    patterns=collections.defaultdict(list)
    for trip in trips:
        if trip.get('mode')!='commuter':continue
        line=str(trip.get("line","")).strip()
        if not line or len(line)>6:continue
        key=(trip["mode"],line,trip["stops"][0][2],trip["stops"][-1][2])
        patterns[key].append(trip)
    ordered=sorted(patterns.items(),key=lambda item:(mode_priority.get(item[0][0],9),-len(item[1])))
    lookup_cache={}
    shape_cache={}
    successful=collections.Counter()
    fetches=0
    for (mode,line,first,last),group in ordered[:MAX_LOOKUPS]:
        cache_key=(mode,line,first,last)
        if cache_key not in lookup_cache:lookup_cache[cache_key]=osm_candidates(line,mode,first,last)
        if not lookup_cache[cache_key]:continue
        representative=group[0]
        chosen=None
        for candidate in lookup_cache[cache_key]:
            rid=candidate.get("id")
            if rid not in shape_cache and fetches<MAX_FETCHES:
                fetches+=1
                try:shape_cache[rid]=get_shape(candidate)
                except (urllib.error.URLError,ValueError,TimeoutError,KeyError,TypeError):
                    shape_cache[rid]=None
            shape=shape_cache.get(rid)
            if shape and project_stops(representative["stops"],shape,MATCH_LIMIT.get(mode,350)):
                chosen=(rid,shape);break
        if not chosen:continue
        rid,shape=chosen
        sid="osm:"+str(rid)
        dataset["shapes"][sid]=shape
        for trip in group:
            if project_stops(trip["stops"],shape,MATCH_LIMIT.get(mode,350)):
                trip["shapeId"]=sid
                trip["geometryQuality"]="verified-osm-relation"
                trip["osmRelation"]=rid
                successful[mode]+=1
    dataset["routeRefinement"]={"method":"OSM directional public-transport relation, stop-projection guarded",
        "verifiedTrips":dict(successful),"attemptedPatterns":min(MAX_LOOKUPS,len(patterns)),
        "estimatedTrips":len(trips)-sum(successful.values())}
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
