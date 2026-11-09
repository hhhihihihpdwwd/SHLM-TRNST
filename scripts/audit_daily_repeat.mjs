import fs from 'node:fs';
import {activeRailTrips,railAt} from '../src/rail-data.js';
import {matchesRailFilter} from '../src/rail-filter.js';

const d=JSON.parse(fs.readFileSync('data/rail.json','utf8'));
if(d.type!=='historical-daily-repeating-simulation')
 throw Error('Expected a true daily-repeating historical service');
if(!d.simulationTemplateDay||d.referenceDay!=='2026-11-06')
 throw Error('The validated fixed historic Friday timetable is absent');

const filters=['commuter','metro','tram','nockeby','lidingo','city7','roslags','saltsjo','arlanda'];
const samples=['03:47','08:47','12:47','16:47','20:06','20:47'];
const dates=[
 ['2026-11-09','+01:00'],['2026-11-10','+01:00'],['2026-11-11','+01:00'],
 ['2026-11-12','+01:00'],['2026-11-13','+01:00'],['2026-11-14','+01:00'],
 ['2026-11-15','+01:00'],['2027-07-13','+02:00']
];
function signature(trips,epoch){
 return trips.map(t=>{
  const p=railAt(t,epoch);
  if(!p.pos.every(Number.isFinite))throw Error('Off-rail position');
  return [t.id.split(':DAILY:')[0],p.pos.map(v=>Math.round(v*1e6)/1e6),p.kmh];
 }).sort((a,b)=>a[0].localeCompare(b[0]));
}
const counts={};
for(const sample of samples){
 let expected=null;
 for(const [day,offset] of dates){
  const epoch=Date.parse(day+'T'+sample+':00'+offset)/1000;
  const all=activeRailTrips(d,epoch,30000);
  const byMode=Object.fromEntries(filters.map(filter=>
   [filter,signature(all.filter(t=>matchesRailFilter(t,filter)),epoch)]));
  if(expected===null)expected=byMode;
  else for(const filter of filters){
   if(JSON.stringify(byMode[filter])!==JSON.stringify(expected[filter]))
    throw Error('Weekday/weekend train mismatch at '+sample+' '+day+' for '+filter);
  }
 }
 counts[sample]=Object.fromEntries(filters.map(f=>[f,expected[f].length]));
 console.log('DAILY TIME REPLAY VALIDATED',sample,counts[sample]);
}
const noon=Object.values(counts['12:47']).reduce((a,b)=>a+b,0);
const night=Object.values(counts['03:47']).reduce((a,b)=>a+b,0);
if(!noon||night>=noon)throw Error('No credible sparse night versus daytime traffic');
console.log('ONE HISTORICAL DAY REPEATS EVERY CALENDAR DAY, ALL SYSTEMS',JSON.stringify({night,noon}));
