#!/usr/bin/env python3
"""Build commuter route geometry from actual OpenStreetMap railway ways.

This does not claim to know which of multiple parallel tracks a real train uses.
It refuses routes when stops cannot be snapped to a connected railway graph.
Public Overpass source, no API key; output follows actual OSM rail way nodes,
never draws invented lines between stations.
"""
import collections
import gzip
import heapq
import io
import json
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path

OVERPASS="https://overpass.kumi.systems/api/interpreter"
BACKUP="https://overpass-api.de/api/interpreter"
# Overlapping bands cover the Stockholm commuter corridors, including
# Nynäshamn, Södertälje, Bålsta and Märsta.
BANDS=((58.82,17.25,59.23,18.75),(59.20,17.25,59.50,18.75),
       (59.47,17.25,59.84,18.75))
MAX_RAW=70_000_000
NEAR_M=240
MIN_SEGMENT_M=50
MAX_SEGMENT_SPEED=175
MAX_JOURNEYS=1900

def meters(a,b):
    dy=(b[0]-a[0])*111100
    dx=(b[1]-a[1])*111100*math.cos(math.radians((a[0]+b[0])/2))
    return math.hypot(dx,dy)

def osm_request(bbox):
    south,west,north,east=bbox
    query=f'[out:json][timeout:105];way["railway"="rail"]({south},{west},{north},{east});(._;>;);out body;'
    data=urllib.parse.urlencode({"data":query}).encode()
    for endpoint in (OVERPASS,BACKUP):
        try:
            req=urllib.request.Request(endpoint,data=data,headers={
                "User-Agent":"StockholmPendeltag/1.0 (personal railway modelling; OSM attribution)",
                "Accept-Encoding":"gzip, deflate"})
            with urllib.request.urlopen(req,timeout=135) as response:
                raw=response.read(MAX_RAW+1)
                encoding=response.headers.get("Content-Encoding","").lower()
            if len(raw)>MAX_RAW:raise ValueError("Overpass region too large")
            if encoding=="gzip":raw=gzip.decompress(raw)
            elif encoding=="deflate":
                import zlib
                raw=zlib.decompress(raw)
            result=json.loads(raw)
            if not isinstance(result.get("elements"),list):raise ValueError("OSM elements missing")
            return result["elements"]
        except (OSError,ValueError,TimeoutError) as exc:
            print("OSM region unavailable",endpoint,type(exc).__name__,flush=True)
    raise RuntimeError("Overpass unavailable; not publishing invented rail paths")

def graph_from_elements(elements):
    coordinates={}
    ways=[]
    for element in elements:
        if element.get("type")=="node":
            coordinates[element["id"]]=[float(element["lat"]),float(element["lon"])]
        if element.get("type")=="way":
            tags=element.get("tags") or {}
            if tags.get("railway")!="rail" or tags.get("service") in ("yard","siding","spur"):
                continue
            if tags.get("construction") or tags.get("disused") or tags.get("abandoned"):
                continue
            ways.append(element.get("nodes",[]))
    adjacency=collections.defaultdict(list)
    for way in ways:
        for a,b in zip(way,way[1:]):
            if a not in coordinates or b not in coordinates:continue
            d=meters(coordinates[a],coordinates[b])
            if not .2<=d<=4500:continue
            adjacency[a].append((b,d))
            adjacency[b].append((a,d))
    return coordinates,adjacency

def nearest(point,coords,buckets):
    lat,lon=point[:2]
    latbin,lonbin=round(lat*100),round(lon*100)
    options=[]
    for a in range(latbin-1,latbin+2):
        for b in range(lonbin-2,lonbin+3):
            options.extend(buckets.get((a,b),[]))
    if not options:return None
    closest=min(options,key=lambda n:meters(point,coords[n]))
    return closest if meters(point,coords[closest])<=NEAR_M else None

def shortest_path(start,end,adjacency):
    if start==end:return [start]
    q=[(0.,start)]
    dist={start:0.}
    previous={}
    while q:
        cost,node=heapq.heappop(q)
        if cost>dist.get(node,float('inf')):continue
        if node==end:
            path=[end]
            while path[-1]!=start:path.append(previous[path[-1]])
            path.reverse();return path
        for neighbor,weight in adjacency.get(node,()):
            next_cost=cost+weight
            if next_cost<dist.get(neighbor,float('inf')):
                dist[neighbor]=next_cost
                previous[neighbor]=node
                heapq.heappush(q,(next_cost,neighbor))
    return None

def reconstruct(trips,coordinates,adjacency):
    buckets=collections.defaultdict(list)
    for node in adjacency:
        p=coordinates[node]
        buckets[(round(p[0]*100),round(p[1]*100))].append(node)
    route_cache={}
    journeys=[]
    shapes={}
    failures=collections.Counter()
    for t in trips:
        stations=t["stops"]
        stations_nodes=[nearest(point,coordinates,buckets) for point in stations]
        if None in stations_nodes:
            failures["stop_far_from_track"]+=1;continue
        node_sequence=[stations_nodes[0]]
        valid=True
        for i,(start,end) in enumerate(zip(stations_nodes,stations_nodes[1:])):
            key=(start,end)
            if key not in route_cache:
                path=shortest_path(start,end,adjacency)
                route_cache[key]=path
                if path:route_cache[end,start]=list(reversed(path))
            part=route_cache.get(key)
            if not part:
                failures["railway_disconnected"]+=1;valid=False;break
            length=sum(meters(coordinates[a],coordinates[b]) for a,b in zip(part,part[1:]))
            travel=stations[i+1][3]-stations[i][4]
            if travel<=0 or length<MIN_SEGMENT_M or length/travel*3.6*1.5>MAX_SEGMENT_SPEED:
                failures["speed_or_geometry"]+=1;valid=False;break
            node_sequence.extend(part[1:])
        if not valid:continue
        # Retain every OSM railway node (no line smoothing that leaves tracks).
        shape=[[round(coordinates[n][0],6),round(coordinates[n][1],6)] for n in node_sequence]
        if len(shape)<2:continue
        import hashlib
        shape_id="osmrail:"+hashlib.sha1(json.dumps(node_sequence).encode()).hexdigest()[:16]
        shapes.setdefault(shape_id,shape)
        new={**t,"shapeId":shape_id,"geometryQuality":"verified-osm-rail-graph",
             "source":"GTFS Sverige 2 archive + OSM rail graph"}
        journeys.append(new)
        if len(journeys)>=MAX_JOURNEYS:break
    return journeys,shapes,failures

def build(dataset,fetch=osm_request):
    elements={}
    for region in BANDS:
        for elem in fetch(region):elements[elem.get("type"),elem.get("id")]=elem
    coords,graph=graph_from_elements(elements.values())
    print("OSM RAIL NETWORK",len(coords),"nodes",len(graph),"connected nodes",flush=True)
    if len(graph)<2000:raise RuntimeError("Insufficient OSM railways")
    pends=[t for t in dataset["trips"] if t["mode"]=="commuter"]
    matched,shapes,failures=reconstruct(pends,coords,graph)
    print("PENDELTAG GRAPH MATCH",len(matched),"/",len(pends),"failures",dict(failures),flush=True)
    if len(matched)<12:
        raise RuntimeError("Too few Pendeltag journeys could be matched to continuous OSM railway geometry; no publish")
    dataset.update({
        "trips":matched,"shapes":shapes,"counts":{"commuter":len(matched)},
        "type":"historical-pendeltag-verified-rail","strictGeometry":True,
        "description":"Historische Fahrplanzeit auf echter OSM-Schienenlinie. Position, km/h und Auslastung modelliert, kein GPS.",
        "qualityReport":{"inputTrips":len(pends),"verifiedTrips":len(matched),
          "verifiedShare":round(len(matched)/len(pends)*100,1),
          "unverifiedTripsHidden":len(pends)-len(matched),
          "trackSource":"OpenStreetMap railway=rail ways, connected shortest path",
          "snapToleranceMetres":NEAR_M,"failures":dict(failures)}
    })
    return dataset
