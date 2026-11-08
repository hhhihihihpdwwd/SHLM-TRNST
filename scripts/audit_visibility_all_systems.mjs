import fs from 'node:fs';
import {activeRailTrips,railAt} from '../src/rail-data.js';
import {matchesRailFilter} from '../src/rail-filter.js';

const data=JSON.parse(fs.readFileSync('data/rail.json','utf8'));
const filters=['commuter','metro','tram','nockeby','lidingo','city7','roslags','saltsjo','arlanda'];
if(data.counts.regional)filters.push('malartag');
const dates=[...new Set(data.trips.map(t=>t.serviceDay).filter(Boolean))].sort();
if(!dates.length)throw Error('No dated historical timetable services');
const today=new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Stockholm',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
if(!dates.includes(today))throw Error('Published data does not contain Stockholm today '+today+' (available '+dates.join(', ')+')');
const stamps=['08:47','12:47','16:47','20:06','20:47'];
const results={};
for(const hm of stamps){
 const epoch=Date.parse(today+'T'+hm+':00+01:00')/1000;
 const trains=activeRailTrips(data,epoch,15000);
 results[hm]={};
 for(const filter of filters){
  const active=trains.filter(v=>matchesRailFilter(v,filter));
  results[hm][filter]=active.length;
  for(const trip of active){
   const position=railAt(trip,epoch);
   if(!position.pos.every(Number.isFinite))throw Error(filter+' invalid vehicle coordinate');
   if(!Number.isFinite(position.kmh))throw Error(filter+' invalid speed');
  }
 }
}
console.log('STOCKHOLM RAIL ALL-SYSTEM VISIBILITY',JSON.stringify({today,results},null,2));
for(const filter of filters){
 const total=stamps.reduce((n,hm)=>n+results[hm][filter],0);
 if(!total)throw Error('EMPTY VEHICLE LIST throughout sampled day for '+filter);
}
if(!results['20:06'].metro)throw Error('TUNNELBANA EMPTY at 20:06 — screenshot regression');
