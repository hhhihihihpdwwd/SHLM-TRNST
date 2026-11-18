import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {activeRailTrips as newActive,railAt as newAt} from '../_release/website/src/rail-data.js';
import {activeRailTrips as oldActive,railAt as oldAt} from '../_original/website/src/rail-data.js';
import {activeRailTrips as refActive,railAt as refAt} from '../_week/website/src/rail-data.js';
import {matchesRailFilter} from '../_release/website/src/rail-filter.js';

const current=JSON.parse(await readFile('_release/website/data/rail.json'));
const original=JSON.parse(await readFile('_original/website/data/rail.json'));
const reference=JSON.parse(await readFile('_week/website/data/rail.json'));
const filters=['metro','commuter','tram','nockeby','lidingo','city7','roslags','saltsjo',
 'arlanda','sj','vr','snalltaget','vy','tagab','rdc','malartag'];
const protectedModes=['metro','express','intercity','regional'];
const patchedModes=['commuter','tram','localrail','saltsjo'];
for(const key of ['metroWeekdaySimulation','commuterWeekdaySimulation','localWeekdaySimulation'])
 assert.equal(current[key],true,'Seven-day SL coverage not enabled '+key);
assert.equal(current.trips.length,reference.trips.length);
for(const mode of patchedModes){
 const A=current.trips.filter(x=>x.mode===mode);
 const B=reference.trips.filter(x=>x.mode===mode);
 assert.deepEqual(A,B,'GTFS source trip count, stop patterns and original OSM relation must be byte-equivalent for '+mode);
}
for(const mode of protectedModes){
 assert.deepEqual(current.trips.filter(x=>x.mode===mode),original.trips.filter(x=>x.mode===mode),
 'Existing Metro/national operator was modified: '+mode);
}
for(const [key,shape] of Object.entries(original.shapes))
 assert.deepEqual(current.shapes[key],shape,'Original route vertices changed: '+key);
assert.deepEqual(current.shapes,reference.shapes,'Seven-day OSM route set differs from independently audited week');
for(const mode of ['metro','express','intercity','regional'])
 assert.equal(current.counts[mode],original.counts[mode]);
const rows=[];
function normalize(t){
 return [t.sourceTripId||t.id,t.serviceDay,t.line,t.start,t.end,t.shapeId,
  t.stops.map(s=>[s[0],s[1],s[2],s[3],s[4]])].join('|');
}
for(const day of ['2026-11-16','2026-11-17','2026-11-18','2026-11-19',
 '2026-11-20','2026-11-21','2026-11-22']){
 for(const clock of ['00:30:00','02:15:00','05:30:00','07:30:00','08:30:00',
  '10:53:22','12:30:00','16:30:00','19:30:00','23:30:00']){
  const t=Date.parse(day+'T'+clock+'+01:00')/1000;
  const now=newActive(current,t,30000);
  const previous=oldActive(original,t,30000);
  const archive=refActive(reference,t,30000);
  const out={day,clock,all:now.length,systems:{}};
  assert.equal(new Set(now.map(x=>x.id)).size,now.length,'Duplicate active train id '+day+clock);
  for(const filter of filters){
   const a=now.filter(v=>matchesRailFilter(v,filter));
   const expected=(['metro','commuter','tram','nockeby','lidingo','city7','roslags','saltsjo'].includes(filter)?
      archive:previous).filter(v=>matchesRailFilter(v,filter));
   assert.deepEqual(a.map(normalize).sort(),expected.map(normalize).sort(),
      'ACTUAL RIDES MISSING OR GHOST TRAINS '+filter+' '+day+' '+clock);
   out.systems[filter]=a.length;
   // Exact non-Metro train coordinates cannot be invented.
   if(!['commuter','tram','nockeby','lidingo','city7','roslags','saltsjo'].includes(filter)){
    const prevMap=new Map(expected.map(v=>[v.id,oldAt(v,t).pos]));
    for(const x of a)assert.deepEqual(newAt(x,t).pos,prevMap.get(x.id),
      'Changed original non-SL train position '+x.id);
   }else{
    const archiveMap=new Map(expected.map(v=>[v.id,refAt(v,t).pos]));
    for(const x of a)assert.deepEqual(newAt(x,t).pos,archiveMap.get(x.id),
      'Not on reference genuine OSM tracks '+x.id);
   }
  }
  if(day==='2026-11-18'&&clock==='10:53:22'){
   assert.equal(out.systems.commuter,33);
   assert.equal(out.systems.lidingo,4);
   assert.equal(out.systems.metro,56);
  }
  if(day==='2026-11-18'&&clock==='07:30:00')assert.equal(out.systems.lidingo,4,'Wednesday morning Lidingöbanan must be restored');
  rows.push(out);
  console.log('PROTECTED 16-SYSTEM GTFS PARITY',day,clock,'METRO',out.systems.metro,
   'PENDELTAG',out.systems.commuter,'LOCAL',
   ['tram','nockeby','lidingo','city7','roslags','saltsjo'].map(k=>k+':'+out.systems[k]).join(','),
   'NATIONAL', ['arlanda','sj','vr','snalltaget','vy','tagab','rdc','malartag'].map(k=>k+':'+out.systems[k]).join(','));
 }
}
await mkdir('_release/qa',{recursive:true});
await writeFile('_release/qa/all-16-source-parity.json',JSON.stringify({rows,dayCount:7,timeCount:10,systems:16},null,2));
console.log('SUCCESS: 1,120 SYSTEM/TIME CHECKS AND ALL 7 SL COMPLETE GTFS MODES EXACT MATCH, EIGHT NATIONAL SYSTEMS AND METRO BYTE-UNCHANGED');
