#!/usr/bin/env python3
"""Repair one proven Mälartåg 332-km false detour using ACTUAL connected OSM rail ways.
No straight lines. Every prior journey on the shared shape must pass the new rail
geometry with plausible station-to-station speed; fail without publishing otherwise.
"""
import json,math,sys
from pathlib import Path
from route_tagab_geofabrik import load_graph,route_one
from refine_osm_routes import project_stops,distance
BAD='malartag-osm:4755734:f+4755735:f+3177328:r'

def main(old,pbf,output):
 base=json.loads(Path(old).read_text())
 orig=base['shapes'][BAD]
 users=[x for x in base['trips'] if x.get('shapeId')==BAD]
 assert len(users)>=9
 master=max(users,key=lambda x:len(x['stops']))
 print('MÄLARTÅG REAL CORRIDOR ROUTING',len(users),'HISTORICAL JOURNEYS SHARING PATH',flush=True)
 print('ORIGINAL TRACK',len(orig),'vertices',int(sum(distance(a,b) for a,b in zip(orig,orig[1:]))/1000),'km',flush=True)
 print('ACTUAL ALL STOPS',[t[2] for t in master['stops']],flush=True)
 points,edges=load_graph([Path(pbf)],master['stops'])
 info=route_one('Eskilstuna–Kvicksund–Kolbäck–Västerås–Sala–Uppsala',master['stops'],points,edges)
 shape=info['shape']
 for u in users:
  stops=u['stops']
  match=project_stops(stops,shape,650)
  if match is None:raise ValueError('Historic Mälartåg calling points not matched to new OSM line '+u['id'])
  for i in range(1,len(stops)):
   depart=stops[i-1][4];arrival=stops[i][3]
   if arrival<=depart:raise ValueError('Bad historical stop times '+u['id'])
   kmh=(match[i]-match[i-1])/(arrival-depart)*3.6
   if kmh>210:raise ValueError('Still implausible actual OSM travel speed '+str(kmh)+' '+stops[i-1][2]+' to '+stops[i][2])
   if kmh<1 and distance(stops[i-1],stops[i])>500:raise ValueError('Missing Mälartåg progress '+u['id'])
 print('ALL HISTORICAL MÄLARTÅG DEPARTURES REAL OSM SPEEDS <210 km/h',len(users),flush=True)
 report={'affectedShapeId':BAD,'affectedHistoricTrains':len(users),
  'previousLengthKm':round(sum(distance(a,b) for a,b in zip(orig,orig[1:]))/1000,2),
  'actualVerifiedLengthKm':info['lengthKm'],'newRealOsmShape':shape,
  'proof':'Every consecutive point comes from physically connected original Geofabrik railway=rail way node IDs',
  'originalTrainDataUnchanged':True}
 path=Path(output);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(report,ensure_ascii=False,separators=(',',':')))
 print('REPAIRED TRACK PROOF READY',path,'points',len(shape),flush=True)
if __name__=='__main__':
 if len(sys.argv)!=4:raise SystemExit('Usage: repair_malartag_rail.py ORIGINAL_RAIL.json SWEDEN_RAIL.pbf PROOF.json')
 main(*sys.argv[1:])
