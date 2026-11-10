// Exhaustive independent audit of all historical train templates in deployed STABLE14.
// No writes, no invented trains and no deploy. Report every train and operator failure.
import {readFileSync,writeFileSync} from 'node:fs';
import {activeRailTrips,railAt} from '../src/rail-data.js';

const file=process.argv[2]||process.env.SITE_ROOT+'/data/rail.json';
const data=JSON.parse(readFileSync(file,'utf8'));
const eps=1e-6;
const errs=[],findings=[],operator=new Map();
const baseTime=Date.parse(data.simulationTemplateDay+'T00:00:00+01:00')/1000;
function add(category,t,details={}) {
 const entry={category,id:t?.id,agency:t?.agency,mode:t?.mode,shapeId:t?.shapeId,...details};
 findings.push(entry);
 let row=operator.get(t?.agency)||{total:0,findings:{}};
 row.findings[category]=(row.findings[category]||0)+1;operator.set(t?.agency,row);
}
function verified(t){
 return t.geometryQuality==='verified-osm-relation'||
 (t.mode==='regional'&&t.geometryQuality==='verified-osm-rail-ways')||
 (t.mode==='intercity'&&(['VR Snabbtåg','Vy Tåg','Tågab','RDC EuroNight'].includes(t.agency)||
 (t.agency==='SJ'&&String(data.scope||'').endsWith('-sj-complete')&&t.sjCompleteVerified===true&&
 String(t.id).startsWith('SJ-FULL-20261106:')&&!!t.sourceTripId))&&
 t.osmWayNetwork===true&&t.geometryQuality==='verified-osm-rail-ways');
}
const eligible=[];
for(const t of data.trips){
 let row=operator.get(t.agency)||{total:0,findings:{}};row.total++;operator.set(t.agency,row);
 if(!verified(t)||!['commuter','metro','tram','localrail','saltsjo','express','intercity','regional'].includes(t.mode)){
  add('excluded_by_runtime_filter',t,{geometryQuality:t.geometryQuality,serviceDay:t.serviceDay});
  continue;
 }
 if(t.serviceDay!==data.simulationTemplateDay){
  add('excluded_by_template_day',t,{serviceDay:t.serviceDay});
  continue;
 }
 if(!Array.isArray(t.stops)||t.stops.length<2){add('invalid_stops',t);continue}
 if(!data.shapes[t.shapeId]){add('missing_shape',t);continue}
 const first=t.stops[0],last=t.stops.at(-1);
 if(!Number.isFinite(t.start)||!Number.isFinite(t.end)||t.end<=t.start){
  add('invalid_epoch_times',t);continue;
 }
 const startClock=t.start-baseTime;
 const endClock=t.end-baseTime;
 const diffStart=Math.round(startClock-first[4]),diffEnd=Math.round(endClock-last[3]);
 if(Math.abs(diffStart)>90)add('start_time_mismatch',t,{diffSeconds:diffStart,startClock,departure:first[4],firstArrival:first[3]});
 if(Math.abs(diffEnd)>90)add('end_time_mismatch',t,{diffSeconds:diffEnd,endClock,arrival:last[3]});
 const departPause=first[4]-first[3];
 if(departPause!==0)add('origin_departure_vs_arrival',t,{originStop: first[2],arrival:first[3],departure:first[4],pauseSeconds:departPause});
 for(let i=1;i<t.stops.length;i++){
  const prev=t.stops[i-1],cur=t.stops[i];
  if(cur[3]<prev[4])add('nonmonotonic_stop_clocks',t,{index:i,previousDeparture:prev[4],arrival:cur[3]});
 }
 eligible.push(t);
}
// Inspect each genuine scheduled departure at a fixed reference time, never mix in assumed GPS data.
const times=[];
for(let i=0;i<48*4;i++)times.push(baseTime+i*900);
const activeAt=new Map(),activeSizes=[];const originals=new Map(eligible.map(t=>[t.id,t]));
for(const epoch of times){
 const active=activeRailTrips(data,epoch,20000);
 activeSizes.push(active.length);
 for(const t of active){
  const id=t.id.replace(/:DAILY:.*/,''),original=originals.get(id);
  if(original&&t.start===original.start)activeAt.set(id,t);
 }
}
const ignored=eligible.filter(t=>t.start < baseTime+172800 && t.end>baseTime && !activeAt.has(t.id));
for(const t of ignored)add('never_visible_during_15_min_samples',t,{first:t.start-baseTime,last:t.end-baseTime});
const timing=[];
for(const t of eligible){
 const live=activeAt.get(t.id);
 if(!live)continue;
 // Compute midpoint of every actual GTFS leg. This distinguishes a real
 // zero-speed station dwell from a train stuck at its origin while in motion.
 for(let i=1;i<t.stops.length;i++){
  const a=t.stops[i-1][4],b=t.stops[i][3];
  if(b-a<120)continue;
  const epoch=(t.start-t.stops[0][4])+Math.floor((a+b)/2);
  const p=railAt(live,epoch);
  if(p.next!==i)add('wrong_next_station_mid_leg',t,{leg:i,predictedNext:p.next});
  if(p.kmh<=0)add('stopped_between_stations',t,{leg:i,depart:a,arrive:b,epoch,position:p.pos});
  if(p.kmh>330)add('implausible_segment_speed',t,{leg:i,kmh:p.kmh});
  if(i===1 && p.meters<=live._anchors[0]+1)add('stuck_at_origin_mid_leg',t,{leg:i,kmh:p.kmh,origin:t.stops[0][2]});
 }
 const tStart=t.start,after=Math.min(t.end-1,tStart+Math.min(60,Math.max(1,Math.floor((t.stops[1][3]-t.stops[0][4])/4))));
 const first=railAt(live,after);
 if(first.next===0)add('not_departed_after_start',t,{elapsed:after-tStart,origin:t.stops[0][2]});
}
const counts={};
for(const [k,v] of operator)counts[k]=v;
const categories={};for(const x of findings)categories[x.category]=(categories[x.category]||0)+1;
const output={source:data.scope,templates:data.trips.length,shapes:Object.keys(data.shapes).length,
 eligible:eligible.length,foundDuringQuarterHourScan:activeAt.size,
 maxActive15min:Math.max(...activeSizes),minActive15min:Math.min(...activeSizes),
 categories,operators:counts,findings:findings.slice(0,1500)};
writeFileSync(process.argv[3]||'/tmp/rail-network-audit.json',JSON.stringify(output,null,2));
console.log('FULL NETWORK AUDIT',JSON.stringify({...output,findings:undefined},null,2));
for(const category of Object.keys(categories))console.log('CATEGORY SAMPLES',category,JSON.stringify(findings.filter(x=>x.category===category).slice(0,4)));
console.log('SNALL SPECIFIC',JSON.stringify(findings.filter(x=>x.agency==='Snälltåget'),null,2));
console.log('SAMPLE TRIP ANCHORS',JSON.stringify([...activeAt.values()].filter(x=>['Snälltåget','Storstockholms Lokaltrafik','SJ'].includes(x.agency)).slice(0,5).map(x=>({id:x.id,agency:x.agency,start:x.start,stop0:x.stops[0],stop1:x.stops[1],anchors:x._anchors.slice(0,5),serviceDay:x.serviceDay})),null,2));
