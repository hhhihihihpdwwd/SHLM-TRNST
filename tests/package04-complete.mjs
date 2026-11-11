import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {activeRailTrips,railAt} from '../src/rail-data.js';
const base=JSON.parse(readFileSync(process.argv[2],'utf8'));
const d=JSON.parse(readFileSync(process.argv[3],'utf8'));
const report=JSON.parse(readFileSync(process.argv[4],'utf8'));
assert.equal(base.trips.length,10789);
assert.equal(base.shapes&&Object.keys(base.shapes).length,107);
assert.equal(report.newValidSourcePatterns,9);
assert.equal(report.shortOrUnmatched,12);
assert.equal(report.possiblePhysicalDuplicates,11);
assert.equal(d.trips.length,10798);
assert.deepEqual(d.trips.slice(0,10789),base.trips);
assert.deepEqual(d.shapes,base.shapes);
for(const [key,value] of Object.entries(base)){
 if(!['trips','counts'].includes(key))assert.deepEqual(d[key],value,'original metadata regression '+key);
}
for(const [key,value] of Object.entries(base.counts)){
 assert.equal(d.counts[key],value+(key==='intercity'?9:0),'count regression '+key);
}
const added=d.trips.filter(t=>t.package04Verified);
assert.equal(added.length,9);
assert.equal(new Set(added.map(t=>t.id)).size,9);
assert(added.every(t=>t.agency==='VR Snabbtåg'&&t.osmWayNetwork===true&&t.isLiveGPS===false));
const epochZero=Date.parse('2026-11-09T00:00:00+01:00')/1000;
for(const t of added){
 assert.equal(t.start-epochZero,t.stops[0][4]);
 assert.equal(t.end-epochZero,t.stops.at(-1)[3]);
 assert(t.shapeId in d.shapes);
 assert(t.stops.length>=3);
 for(let i=1;i<t.stops.length;i++){
  const a=t.stops[i-1][4],b=t.stops[i][3];assert(b>a,'source clock');
  const now=epochZero+Math.round((a+b)/2);
  const active=activeRailTrips(d,now,20000);
  const v=active.find(x=>x.id===t.id+':DAILY:2026-11-09');
  assert(v,'Package04 sourced VR train is not rendered halfway through its genuine track '+t.id);
  const p=railAt(v,now);
  assert(Array.isArray(p.pos)&&p.pos.every(Number.isFinite),'bad map coordinates');
  assert(p.next===i,'wrong displayed next station '+t.id);
  assert(p.kmh>0&&p.kmh<210,'unphysical train speed '+t.id+' '+p.kmh);
 }
}
let samples=0;
for(const day of ['2026-11-09','2026-11-10','2026-11-11','2026-11-12','2026-11-13','2026-11-14','2026-11-15']){
 for(let hour=0;hour<24;hour++){
  const epoch=Date.parse(day+'T'+String(hour).padStart(2,'0')+':19:00+01:00')/1000;
  const before=activeRailTrips(base,epoch,20000),after=activeRailTrips(d,epoch,20000);
  const originalIds=new Set(before.map(x=>x.id));
  assert.deepEqual(after.filter(x=>originalIds.has(x.id)).map(x=>x.id).sort(),
   before.map(x=>x.id).sort(),'previously published 16-system trains changed');
  assert.equal(new Set(after.map(x=>x.id)).size,after.length,'duplicate moving train');
  for(const t of after.filter(x=>x.package04Verified)){
   let p=railAt(t,epoch);
   assert(p.pos.every(Number.isFinite));assert(p.next>=0&&p.next<t.stops.length);
  }
  samples++;
 }
}
console.log('PACKAGE04 7-DAY MOVING VR AND 16-SYSTEM IMMUTABILITY GREEN',added.length,'NEW REAL GTFS TRAIN VARIANTS',samples,'HOURLY CHECKPOINTS');
