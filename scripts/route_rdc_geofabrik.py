#!/usr/bin/env python3
"""Reconstruct Vy Stockholm–Oslo from Geofabrik OSM rail-only PBF extracts.

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
LATMIN,LATMAX,LONMIN,LONMAX=52.0,60.4,8.4,18.6
CANDIDATE_BUFFER_METRES=39000

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

from refine_osm_routes import project_stops
# Routing-only waypoints are not claimed passenger stops; real published passenger
# calling points are separately checked in order against the final original OSM rails.
WAYPOINTS={
 'Berlin Gesundbrunnen':[52.5489,13.3889,'Berlin Gesundbrunnen (track corridor waypoint)'],
 'Wittenberge':[53.0019,11.7538,'Wittenberge (track waypoint)'],
 'Ludwigslust':[53.328,11.499,'Ludwigslust (track waypoint)'],
 'Büchen':[53.475,10.622,'Büchen (track waypoint)'],
 'Neumünster':[54.0726,9.986,'Neumünster (track waypoint)'],
 'Flensburg':[54.7732,9.437,'Flensburg (track waypoint)'],
 'Kolding':[55.4898,9.476,'Kolding (track waypoint)'],
 'Fredericia':[55.567,9.757,'Fredericia (track waypoint)'],
 'Odense':[55.401,10.386,'Odense (track waypoint)'],
 'Nyborg':[55.312,10.788,'Nyborg (track waypoint)'],
 'Korsør':[55.35691,11.13535,'Korsør (track waypoint)'],
 'Ringsted':[55.443,11.787,'Ringsted (track waypoint)'],
 'København H':[55.6728,12.565,'København H (track waypoint)'],
 'Malmö Hyllie':[55.5639,12.975,'Malmö Hyllie (track waypoint)'],
 'Malmö C':[55.6085,13.000,'Malmö Central (track waypoint)']
}
def official_stop(t,name):
 items=[x for x in t['stops'] if x[2]==name]
 if not items:raise ValueError('Missing official stop '+name+' for '+t['id'])
 return items[0][:3]
def stop(t,name):
 return official_stop(t,name) if any(s[2]==name for s in t['stops']) else WAYPOINTS[name]
def waypoints(trip):
 # Select a real geographic railroad corridor; none of these are added as
 # passengers' stops if they are not listed by the operator.
 if trip['direction']=='to-stockholm':
  first=trip['stops'][0][:3]
  german=(['Berlin Gesundbrunnen','Wittenberge','Ludwigslust','Büchen'] if trip['routeVariant']=='Berlin-Lichtenberg' else [])
  pre=[stop(trip,k) for k in german]
  # Hamburg Hbf is the northern endpoint of Germany's section.
  german2=[stop(trip,'Hamburg Hbf'),*(WAYPOINTS[x] for x in ('Neumünster','Flensburg'))]
  danish=[stop(trip,'Padborg'),*(WAYPOINTS[x] for x in ('Kolding','Fredericia','Odense','Nyborg','Korsør','Ringsted','Malmö Hyllie','Malmö C'))]
  # The Copenhagen Airport sits between København H and Malmö Hyllie;
  # include it at the correct location in ordered geography.
  idx=next(i for i,x in enumerate(danish) if x[2].startswith('Malmö Hyllie'))
  danish.insert(idx,stop(trip,'København Lufthavn'))
  danish.insert(idx,[55.649,12.512,'København Syd (route only)'])
  swedish=[stop(trip,x) for x in ('Lund C','Hässleholm C','Alvesta','Nässjö C','Linköping C','Norrköping C','Stockholm C')]
  return [first]+pre+german2+danish+swedish
 # Southbound, the exact physical route is the reverse main corridor.
 # Southbound EN345 calls at København Syd before Copenhagen airport? Chronology
 # says Airport 23:02, Syd 23:16: reverse must go via Airport then Syd, then Padborg.
 first=trip['stops'][0][:3]
 swedish=[stop(trip,x) for x in ('Norrköping C','Linköping C','Nässjö C','Alvesta','Hässleholm C','Lund C')]
 danish=[*(WAYPOINTS[x] for x in ('Malmö C','Malmö Hyllie')),
         stop(trip,'København Lufthavn'),stop(trip,'København Syd'),
         *(WAYPOINTS[x] for x in ('Ringsted','Korsør','Nyborg','Odense','Fredericia','Kolding'))]
 germany=[stop(trip,'Padborg'),WAYPOINTS['Flensburg'],WAYPOINTS['Neumünster'],stop(trip,'Hamburg Hbf') if trip['routeVariant']=='Berlin Hauptbahnhof' else WAYPOINTS['Büchen']]
 if trip['routeVariant']=='Hamburg-Altona':
  # The train to Altona does not necessarily call at Hauptbahnhof; its route
  # may pass through Hamburg's main junction without an operational stop.
  germany=[stop(trip,'Padborg'),WAYPOINTS['Flensburg'],WAYPOINTS['Neumünster'],stop(trip,'Hamburg-Altona')]
 else:
  germany += [WAYPOINTS['Büchen'],WAYPOINTS['Ludwigslust'],WAYPOINTS['Wittenberge'],
              WAYPOINTS['Berlin Gesundbrunnen'],stop(trip,'Berlin Hauptbahnhof')]
 return [first]+swedish+danish+germany

def audit_real(geo,trip):
 if len(geo)<500:raise ValueError('Not enough real railway geometry for cross-border EuroNight')
 maximum=max(dist(a,b) for a,b in zip(geo,geo[1:]))
 if maximum>4000:raise ValueError('Rail line contains a gap between original OSM way vertices')
 if project_stops(trip['stops'],geo,650) is None:
  raise ValueError('Official RDC call points are not in order on verifiable original rail geometry: '+trip['id'])
 return round(maximum,2)
def route_one(trip,points,network):
 ordered=waypoints(trip)
 print('AUTHENTIC RDC ROUTE',trip['id'],'STEPS',len(ordered),'TRACK VIA', [x[2] for x in ordered],flush=True)
 prev={nid:(distance*.8,[nid]) for nid,distance in station_nodes(ordered[0],points).items()}
 for i,p in enumerate(ordered[1:],1):
  targets=station_nodes(p,points)
  direct=dist(ordered[i-1][:2],p[:2])
  nxt,visited=stage(prev,targets,network,max(18000,direct*3.1+15000))
  if not nxt:raise ValueError('No physically connected OSM rails: '+ordered[i-1][2]+' -> '+p[2]+' on '+trip['id'])
  prev=nxt
  print('RDC REAL OSM WAYPOINT',trip['id'],i,'/',len(ordered)-1,p[2],len(prev),'nodes',visited,'visited',flush=True)
 cost,ids=min(prev.values(),key=lambda x:x[0])
 if any(b not in network[a] for a,b in zip(ids,ids[1:])):raise ValueError('Original OSM way-node adjacency broken')
 shape=[]
 for nid in ids:
  xy=[round(points[nid][0],6),round(points[nid][1],6)]
  if not shape or xy!=shape[-1]:shape.append(xy)
 gap=audit_real(shape,trip)
 length=sum(dist(a,b) for a,b in zip(shape,shape[1:]))/1000
 print('AUTHENTIC RDC OSM RAILWAY VERIFIED',trip['id'],len(ids),'ORIGINAL NODES',round(length,1),'KM MAXSTEP',gap,flush=True)
 return {'shape':shape,'maxSegmentMetres':gap,'lengthKm':round(length,2),
   'nodesOnPath':len(ids),'verifiedConsecutiveOsmWayEdges':len(ids)-1}
def main():
 if len(sys.argv)<4:raise SystemExit('Usage: route_rdc_geofabrik.py RDC.json OUT.json [rail-pbf...]')
 cand=json.loads(pathlib.Path(sys.argv[1]).read_text())
 trips=cand['trips']
 if len(trips)!=4 or cand['operator']!='RDC EuroNight':raise ValueError('Authentic operator timetable missing')
 route_stops=[]
 for t in trips:route_stops+=waypoints(t)
 points,network=load_graph([pathlib.Path(x) for x in sys.argv[3:]],route_stops)
 output={'source':'Original connected OSM railway=rail way nodes from Geofabrik Sweden+Denmark+Germany regional PBF extracts',
   'officialTimetable':cand['officialTimetable'],'isLiveGPS':False,'routes':{}}
 for trip in trips:
  output['routes'][trip['id']]=route_one(trip,points,network)
 dest=pathlib.Path(sys.argv[2]);dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(output,separators=(',',':')))
 print('COMPLETE CROSS-BORDER RDC EURONIGHT FOUR HISTORICAL ROUTES OSM VERIFIED',len(output['routes']),flush=True)
if __name__=='__main__':main()
