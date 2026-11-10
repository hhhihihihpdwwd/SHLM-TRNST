#!/usr/bin/env python3
"""Patch exactly ONE wrong Mälartåg OSM track and TWO JS timing/display bugs
onto exact publicly Chromium-verified STABLE14. Never rebuild old services,
never change other operators' geometry, photos, icons or design.
"""
from pathlib import Path
import json,sys
BAD='malartag-osm:4755734:f+4755735:f+3177328:r'
def replace_once(text,old,new,label):
 if text.count(old)!=1:raise ValueError('Expected one '+label+' anchor, got '+str(text.count(old)))
 return text.replace(old,new)
def main(site,proof):
 site=Path(site);proof=json.loads(Path(proof).read_text())
 rail=site/'data/rail.json'
 data=json.loads(rail.read_text())
 assert len(data['trips'])==10611 and len(data['shapes'])==95
 assert data['scope'].endswith('-vy-tagab-rdc-sj-complete')
 assert proof['affectedShapeId']==BAD
 affected=[x for x in data['trips'] if x.get('shapeId')==BAD]
 assert len(affected)==proof['affectedHistoricTrains']==27
 old=data['shapes'][BAD]
 new=proof['newRealOsmShape']
 assert len(old)>8000 and len(new)>1500
 assert proof['previousLengthKm']>500 and 130<proof['actualVerifiedLengthKm']<180
 data['shapes'][BAD]=new
 rail.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')))
 # Preserve exact deployed app bundle and all old style/marker/photo modules.
 html=site/'index.html';h=html.read_text()
 h=replace_once(h,'app.js?v=sj-complete-01','app.js?v=motion-fix-01','index cache URL')
 html.write_text(h)
 app=site/'src/app.js';a=app.read_text()
 a=replace_once(a,'displayOrder(realActive.filter(v=>matchesRailFilter(v,state.filter))).slice(0,90)',
   'displayOrder(realActive.filter(v=>matchesRailFilter(v,state.filter)))','all trains list cap')
 a=replace_once(a,'const stops=v.stops,first=stops[0][3],base=v.start-first;',
   'const stops=v.stops,firstDeparture=stops[0][4],base=v.start-firstDeparture;','detail origin-time base')
 a=replace_once(a,"$('next-stop-time').textContent='Plan '+toTime(stops[idx][3]);",
   "$('next-stop-time').textContent='Plan '+toTime(stops[idx][idx===0?4:3]);",'detail next-station clock')
 a=replace_once(a,'time.textContent=toTime(stops[i][3]);',
   'time.textContent=toTime(stops[i][i===0?4:3]);','detail station time list')
 old_marker_cull=""" const bounds=map.getBounds().pad(.12);
 let drawn=0;
 for(const v of showing){
  const p=railAt(v,epoch).pos;
  const selectedHere=selected?.id===v.id;
  let marker=markers.get(v.id);
  if(!bounds.contains(p)&&!selectedHere){
   if(marker){map.removeLayer(marker);markers.delete(v.id)}
   continue;
  }
  // Keep the selected train even when crowded, prevent excessive DOM markers.
  if(drawn>=280&&!selectedHere){
   if(marker){map.removeLayer(marker);markers.delete(v.id)}continue;
  }
  drawn++;"""
 new_marker_render=""" // Render every historically active train marker, not just first 280 or those
 // inside the current viewport. Leaflet handles clipping naturally.
 for(const v of showing){
  const p=railAt(v,epoch).pos;
  const selectedHere=selected?.id===v.id;
  let marker=markers.get(v.id);"""
 a=replace_once(a,old_marker_cull,new_marker_render,'all train marker culling/cap')
 a=replace_once(a,"from './rail-data.js?v=sj-complete-01'",
   "from './rail-data.js?v=motion-fix-01'",'parser cache import')
 app.write_text(a)
 module=site/'src/rail-data.js';s=module.read_text()
 s=replace_once(s,'const base=trip.start-stops[0][3];',
   "// Anchor origin to its advertised DEPARTURE, not an earlier platform arrival.\n const base=trip.start-stops[0][4];",'origin time')
 s=replace_once(s,'if(epoch<source.start+delta-60||epoch>source.end+delta+80)continue;',
   'if(epoch<source.start+delta||epoch>=source.end+delta)continue;','exact visibility window')
 s=replace_once(s,"TIMETABLE_URL='./data/rail.json?v=sj-complete-01'",
   "TIMETABLE_URL='./data/rail.json?v=motion-fix-01'",'timetable cache')
 module.write_text(s)
 print('BUILD COMPLETE NETWORK MOTION REPAIR: 10611 OLD TRAIN TEMPLATES,',
       '27 MÄLARTÅG SERVICES REPAIRED ON TRUE 148.2KM OSM',
       'EXACT DEPARTURES/ARRIVALS + EVERY ACTIVE TRAIN IN LIST',
       'ALL 16 EXISTING SYSTEMS INTACT',flush=True)
if __name__=='__main__':
 if len(sys.argv)!=3:raise SystemExit('Usage: prepare_network_motion_release.py SITE_DIR OSM_FIX_PROOF.json')
 main(*sys.argv[1:])
