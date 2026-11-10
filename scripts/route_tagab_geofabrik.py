#!/usr/bin/env python3
"""Reconstruct both authentic Tågab Stockholm–Göteborg corridors from Geofabrik OSM rail-only PBF extracts.

No Overpass dependency. Uses ONLY consecutive OSM railway=rail way node IDs,
no synthetic connections or station-to-station straight lines. OSM extracts
from Sweden and Norway are combined in a shared node-ID graph. Generates an
independent geojson/Leaflet PREVIEW but never modifies the public website.
"""
from __future__ import annotations
import collections, json, math, pathlib, sys, heapq
import osmium
from osm_railway_way_router import dist,station_nodes,stage
from refine_osm_routes import project_stops

ROOT=pathlib.Path(__file__).resolve().parents[1]
LATMIN,LATMAX,LONMIN,LONMAX=57.5,60.55,11.55,18.35
CANDIDATE_BUFFER_METRES=38000

def corridor_near(lat,lon,stops):
    if not (LATMIN<=lat<=LATMAX and LONMIN<=lon<=LONMAX):return False
    # Distance to segment between adjacent real GTFS station pairs:
    # used only to limit storage; routing remains on actual OSM shared nodes.
    y=lat*111100; x=lon*111100*math.cos(math.radians(lat))
    for p,q in zip(stops,stops[1:]):
        scale=111100*math.cos(math.radians((p[0]+q[0])/2))
        ax,ay=p[1]*scale,p[0]*111100
        bx,by=q[1]*scale,q[0]*111100
        xx=lon*scale
        dx,dy=bx-ax,by-ay
        fraction=max(0,min(1,((xx-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy or 1)))
        if math.hypot(xx-(ax+fraction*dx),y-(ay+fraction*dy))<CANDIDATE_BUFFER_METRES:
            return True
    return False

class TrackGraph(osmium.SimpleHandler):
    def __init__(self,stops):
        super().__init__();self.stops=stops
        self.nodes={};self.edges=collections.defaultdict(dict)
        self.ways=0;self.edges_seen=0;self.rejected=0
    def way(self,way):
        if way.tags.get('railway')!='rail':return
        ns=list(way.nodes)
        if len(ns)<2:return
        pairs=[]
        try:
            for n in ns:
                lat,lon=n.location.lat,n.location.lon
                pairs.append((int(n.ref),(lat,lon)))
        except (osmium.InvalidLocationError,ValueError):
            self.rejected+=1;return
        # Whole OSM way qualifies if ANY rail vertex is close to the actual
        # train corridor. Store entire original way with all original nodes.
        if not any(corridor_near(*p,self.stops) for _,p in pairs):return
        self.ways+=1
        penalty=3.0 if way.tags.get('service') in ('yard','siding','spur') else 1.0
        for nid,xy in pairs:self.nodes.setdefault(nid,xy)
        for (a,aa),(b,bb) in zip(pairs,pairs[1:]):
            distance=dist(aa,bb)
            if a==b or not (0.01<distance<4000):continue
            cost=distance*penalty
            if cost<self.edges[a].get(b,float('inf')):
                self.edges[a][b]=cost;self.edges[b][a]=cost
                self.edges_seen+=1

def load_graph(files,stops):
    graph=TrackGraph(stops)
    for file in files:
        assert file.is_file() and file.stat().st_size>100000,'PBF input missing or truncated: '+str(file)
        print('READ GEOfabrik RAIL EXTRACT',file,file.stat().st_size,flush=True)
        graph.apply_file(str(file),locations=True,idx='flex_mem')
        print('OSM GRAPH PROGRESS',graph.ways,'ways',len(graph.nodes),'nodes',graph.edges_seen,'edges',flush=True)
    if len(graph.nodes)<1000:raise ValueError('No OSM railway nodes loaded')
    return graph.nodes,graph.edges

def validate(shape,trips):
    if len(shape)<100:raise ValueError('OSM geometry too short')
    lengths=[dist(a,b) for a,b in zip(shape,shape[1:])]
    if max(lengths)>4000:raise ValueError('Unexpected length between actual OSM way vertices: '+str(max(lengths)))
    checked=collections.Counter()
    for t in trips:
        for orientation,coords in [('stockholm-oslo',shape),('oslo-stockholm',list(reversed(shape)))]:
            if project_stops(t['stops'],coords,650) is not None:
                checked[(t['direction'],t['historicWeekday'])]+=1
                print('GEOfabrik VERIFIED VY',t['train'],t['archiveDay'],orientation,flush=True)
                break
        else:print('GEOfabrik NOT COVERED',t['train'],t['archiveDay'],t['stops'][0][2],t['stops'][-1][2],flush=True)
    if not any(k[0]=='from-stockholm' for k in checked) or not any(k[0]=='to-stockholm' for k in checked):
        raise ValueError('Both directions not verified on shared real OSM nodes '+str(checked))
    return checked

def render_geojson(shape,source,meta,dest):
    dest.parent.mkdir(parents=True,exist_ok=True)
    geo={'type':'FeatureCollection','features':[
      {'type':'Feature','properties':{'name':'Vy Tåg – physically connected OSM rails',
        'source':'© OpenStreetMap contributors · Geofabrik extracts',
        'verification':'OSM way node ID path; historic GTFS every stop verified',
        'note':'Technical preview, not a live GPS train position'},
       'geometry':{'type':'LineString','coordinates':[[lon,lat] for lat,lon in shape]}}
    ],'metadata':meta}
    dest.write_text(json.dumps(geo,ensure_ascii=False,separators=(',',':')))
    html=dest.with_suffix('.html')
    page="""<!doctype html><html lang="de"><meta charset="utf-8"><title>Vy Tåg – Verified OSM track preview</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>body{margin:0;font-family:system-ui;background:#f4f6f5}header{padding:12px 20px;background:white;border-bottom:1px solid #ddd}
#map{height:calc(100dvh - 82px)}small{color:#64748b}</style>
<header><b>STOCKHOLM RAIL – VY TÅG · TECHNICAL PREVIEW</b><div><small>Real connected OSM railway=rail nodes; historic timetable, no GPS. Public website unchanged.</small></div></header>
<div id="map"></div><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script><script>
const data=__GEOJSON__;
const map=L.map('map');L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap contributors'}).addTo(map);
const track=L.geoJSON(data,{style:{color:'#147d79',weight:5,opacity:.9}}).addTo(map);
map.fitBounds(track.getBounds(),{padding:[25,25]});
</script></html>""".replace('__GEOJSON__',json.dumps(geo,ensure_ascii=False))
    html.write_text(page)
    print('PREVIEW GEOJSON AND LEAFLET HTML',dest,html,flush=True)

def route_one(title,stops,points,network):
 current={nid:(gap*.8,[nid]) for nid,gap in station_nodes(stops[0],points).items()}
 for i,stop in enumerate(stops[1:],1):
  target=station_nodes(stop,points)
  direct=dist(stops[i-1][:2],stop[:2])
  next_nodes,visited=stage(current,target,network,max(18000,direct*2.9+13000))
  if not next_nodes:raise ValueError('DISCONNECTED ACTUAL OSM TRACK '+title+' '+stops[i-1][2]+' -> '+stop[2])
  current=next_nodes
  print('TAGAB PHYSICAL OSM TRACK',title,i,'/',len(stops)-1,stop[2],'NODES',len(current),'VISITED',visited,flush=True)
 cost,ids=min(current.values(),key=lambda v:v[0])
 if any(b not in network[a] for a,b in zip(ids,ids[1:])):raise ValueError('Unexpected nonconnected OSM railway way nodes')
 shape=[]
 for nid in ids:
  lat,lon=points[nid]
  xy=[round(lat,6),round(lon,6)]
  if not shape or shape[-1]!=xy:shape.append(xy)
 longest=max(dist(a,b) for a,b in zip(shape,shape[1:]))
 if longest>4000:raise ValueError('Unexpected physical OSM way vertex gap '+str(longest))
 if project_stops(stops,shape,650) is None:raise ValueError('Ordered GTFS stations are not on the verified OSM railway path '+title)
 length=sum(dist(a,b) for a,b in zip(shape,shape[1:]))/1000
 print('TAGAB VERIFIED OSM ROUTE',title,'KM',round(length,1),'NODES',len(ids),'MAXSEGMENT',round(longest,1),flush=True)
 return {'shape':shape,'lengthKm':round(length,1),'maxSegmentMetres':round(longest,2),
         'nodesOnPath':len(ids),'verifiedConsecutiveOsmWayEdges':len(ids)-1}

def build(candidates,source_pbf):
 trips=candidates['trips']
 if candidates['operator']!='Tågab' or len(trips)<8:raise ValueError('Missing authentic historical Tågab GTFS')
 patterns={}
 for corridor in ['katrineholm','vasteras']:
  choices=[t for t in trips if t['corridor']==corridor
     and t['direction']=='from-stockholm' and 'göteborg' in t['destination'].casefold()]
  if not choices:raise ValueError('No authentic through Stockholm–Göteborg GTFS trip via '+corridor)
  selected=max(choices,key=lambda t:len(t['stops']))
  patterns[corridor]=selected
  print('TAGAB AUTHENTIC MASTER',corridor,selected['train'],[z[2] for z in selected['stops']],flush=True)
 # The graph covers BOTH real historical corridor options; the train paths
 # are built entirely on consecutive OSM railway=rail shared node IDs.
 all_stops=[]
 for trip in patterns.values():all_stops.extend(trip['stops'])
 points,graph=load_graph([source_pbf],all_stops)
 result={'source':'Geofabrik Sweden PBF, actual OSM railway=rail shared node graph',
  'historicGTFS':candidates['sourceArchive'],'corridors':{},'tripsMatched':{},'isLiveGPS':False}
 for name,trip in patterns.items():
  result['corridors'][name]=route_one(name,trip['stops'],points,graph)
 for trip in trips:
  corridor=trip['corridor']
  shape=result['corridors'][corridor]['shape']
  oriented=shape if trip['direction']=='from-stockholm' else list(reversed(shape))
  if project_stops(trip['stops'],oriented,650) is None:
   raise ValueError('Authentic Tågab train not mapped to real OSM track '+trip['id']+' corridor '+corridor)
  result['tripsMatched'][trip['id']]={'corridor':corridor,'direction':trip['direction']}
  print('TAGAB ACTUAL GTFS STOPS VERIFIED',trip['train'],corridor,trip['direction'],flush=True)
 assert len(result['tripsMatched'])==len(trips)
 return result

def main():
 if len(sys.argv)!=4:raise SystemExit('Usage: route_tagab_geofabrik.py TAGAB_CANDIDATES.json RAIL_SWEDEN.pbf OUT.json')
 candidates=json.loads(pathlib.Path(sys.argv[1]).read_text())
 data=build(candidates,pathlib.Path(sys.argv[2]))
 path=pathlib.Path(sys.argv[3]);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(data,separators=(',',':')))
 print('ALL TAGAB STOCKHOLM TRAINS VERIFIED ON ACTUAL OSM TRACKS',len(data['tripsMatched']),'TWO ROUTES',flush=True)

if __name__=='__main__':main()
