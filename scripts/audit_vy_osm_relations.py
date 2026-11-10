#!/usr/bin/env python3
"""Read-only rapid OSM route-relation audit. Never accept disconnected members."""
import json,urllib.parse,urllib.request
from refine_osm_routes import project_stops
BASE='https://openstreetmap.tools/public_transport_geojson/api/'
STOPS=[
 [59.330140,18.058154,'Stockholm Centralstation'],
 [59.568759,17.532813,'Bålsta station'],
 [59.607704,16.551707,'Västerås Centralstation'],
 [59.397107,15.841060,'Arboga station'],
 [59.278942,15.211344,'Örebro Centralstation'],
 [59.066699,15.110387,'Hallsberg station'],
 [59.316501,14.108292,'Kristinehamn station'],
 [59.377798,13.499047,'Karlstad Centralstation'],
 [59.505032,13.316341,'Kil station'],
 [59.653592,12.591148,'Arvika station'],
 [59.883973,12.297647,'Charlottenberg station'],
 [60.187716,12.003855,'Kongsvinger'],
 [59.953214,11.044680,'Lillestrøm'],
 [59.910990,10.753488,'Oslo S']
]
def load(path):
 req=urllib.request.Request(BASE+path,headers={'User-Agent':'StockholmRail/1.0 (OSM regional railway relation research)'})
 with urllib.request.urlopen(req,timeout=48) as r:return json.loads(r.read(19000001))
def main():
 ids={4078008}
 for q in ('Oslo','Karlstad','Vy Tåg'):
  try:
   url='search?'+urllib.parse.urlencode({'q':q,'mode':'train','south':58.8,'west':10.5,'north':60.4,'east':18.9})
   d=load(url)
   for r in d.get('routes',[]):
    print('OSM ROUTE SEARCH',q,r.get('id'),r.get('name'),r.get('from'),r.get('to'),r.get('operator'),flush=True)
    title=' '.join(str(r.get(k,'')) for k in ('name','from','to')).casefold()
    if ('oslo' in title or 'karlstad' in title) and ('stockholm' in title or 'oslo' in title):
     if isinstance(r.get('id'),int):ids.add(r['id'])
  except Exception as ex:print('OSM SEARCH UNAVAILABLE',q,str(ex)[:140],flush=True)
 from append_malartag import geometry_large,geometry_components
 for rid in sorted(ids):
  try:
   data=load('route/'+str(rid))
   geo=data.get('geojson',{})
   parts=geometry_components(geo)
   full=geometry_large(geo)
   print('OSM RELATION',rid,'name',data.get('name'),'FRAGMENTS',len(parts),'CONNECTED',len(full) if full else 0,flush=True)
   if full:
    for direction,g in [('as-is',full),('reverse',list(reversed(full)))]:
     if project_stops(STOPS,g,800) is not None:
      print('OSM FULL STOCKHOLM-OSLO ROUTE VERIFIED',rid,direction,'VERTICES',len(g),flush=True)
  except Exception as ex:print('OSM RELATION UNAVAILABLE',rid,str(ex)[:180],flush=True)
if __name__=='__main__':main()
