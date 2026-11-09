// Check an actual renderable historic train schedule over all 24 hours.
// Never invent overnight trains: report zero where the real template has none.
import fs from 'node:fs';
import {activeRailTrips,railAt} from '../src/rail-data.js';
import {matchesRailFilter} from '../src/rail-filter.js';

const d=JSON.parse(fs.readFileSync('data/rail.json','utf8'));
if(d.type!=='historical-daily-repeating-simulation')throw Error('No daily timetable simulation');
if(d.scope!=='pendeltag-tunnelbana-tvarbanan-localtram-city7-roslags-saltsjo-arlanda')
 throw Error('Not the nine-system, Mälartåg-free rail release');
if(d.trips.some(t=>t.mode==='regional'||t.corridor))throw Error('Unexpected regional trains');
const filters=['commuter','metro','tram','nockeby','lidingo','city7','roslags','saltsjo','arlanda'];
const days=['2026-11-09','2026-11-15','2027-07-13'];
let total=0;
for(const day of days){
 const summer=day.includes('-07-'),tz=summer?'+02:00':'+01:00';
 const result=Object.fromEntries(filters.map(f=>[f,Array(24).fill(0)]));
 for(let hour=0;hour<24;hour++){
  const hr=String(hour).padStart(2,'0');
  for(const minute of [0,15,30,45]){
   const epoch=Date.parse(day+'T'+hr+':'+String(minute).padStart(2,'0')+':00'+tz)/1000;
   const trains=activeRailTrips(d,epoch,20000);
   for(const t of trains){
    const at=railAt(t,epoch);
    if(!at.pos.every(Number.isFinite)||!Number.isFinite(at.kmh))
     throw Error('Invalid vehicle coordinate/speed '+t.id);
   }
   for(const filter of filters){
    result[filter][hour]+=trains.filter(t=>matchesRailFilter(t,filter)).length;
   }
   total++;
  }
 }
 for(const filter of filters){
  // A reduced overnight service is fine, but no entire system may be
  // absent from the daytime timetable (including at 07:00–22:00).
  const daytime=result[filter].slice(7,23).reduce((a,n)=>a+n,0);
  if(daytime<1)throw Error('No trains during daytime for '+filter+' '+day);
 }
 if(!result.metro[7]||!result.metro[20])
  throw Error('Tunnelbana absent at 07:00 or 20:00 on '+day);
 // Explicit regression for the screenshot taken at 07:01 Stockholm time.
 const morning=Date.parse(day+'T07:01:00'+tz)/1000;
 const morningTrains=activeRailTrips(d,morning,20000);
 const morningModes=filters.filter(filter=>
  morningTrains.some(t=>matchesRailFilter(t,filter)));
 if(!morningModes.includes('metro')||!morningModes.includes('commuter')||
    morningModes.length<4)
  throw Error('07:01 still has a nearly empty network: '+morningModes.join(', '));
 console.log('SCREENSHOT 07:01 ACTIVE SYSTEMS',day,morningModes.join(', '));
 console.log('24-HOUR VERIFIED MAP-RENDERABLE TRAINS',day,JSON.stringify(result));
}
console.log('STABLE 06 NINE-SYSTEM 24-HOUR AUDIT PASSED',total,'quarter-hour samples');
