// Package03: physically moving genuine source trains + complete STABLE17 regression gate.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {activeRailTrips,railAt} from '../src/rail-data.js';
const base=JSON.parse(readFileSync(process.argv[2],'utf8'));
const d=JSON.parse(readFileSync(process.argv[3],'utf8'));
assert.equal(base.trips.length,10787);
assert.equal(d.trips.length,10789);
assert.deepEqual(d.trips.slice(0,10787),base.trips);
assert.deepEqual(d.shapes,base.shapes);
assert.deepEqual(Object.keys(d).filter(k=>!['trips','counts','package03Audit'].includes(k)).map(k=>[k,d[k]]),
 Object.keys(base).filter(k=>!['trips','counts'].includes(k)).map(k=>[k,base[k]]));
const add=d.trips.slice(10787);
assert.deepEqual(add.map(x=>x.agency),['SJ','VR Snabbtåg']);
const originEpoch=Date.parse('2026-11-09T00:00:00+01:00')/1000;
for(const t of add){
 assert(t.package03Verified&&t.isLiveGPS===false);
 assert(t.shapeId in d.shapes);
 assert.equal(t.start-originEpoch,t.stops[0][4]);
 assert.equal(t.end-originEpoch,t.stops.at(-1)[3]);
 for(let i=1;i<t.stops.length;i++){
  const start=t.stops[i-1][4],end=t.stops[i][3];
  assert(end-start>90);
  const now=t.start-t.stops[0][4]+Math.floor((start+end)/2);
  const v=activeRailTrips(d,now,20000).find(x=>x.id===t.id+':DAILY:2026-11-09');
  assert(v,'new source trip missing on map halfway between stations '+t.id);
  const p=railAt(v,now);
  assert(p.pos.every(Number.isFinite));
  assert(p.kmh>0 && p.kmh<210,t.id+' invalid speed '+p.kmh);
  assert.equal(p.next,i,t.id+' incorrect next stop');
  assert(p.meters>v._anchors[0]);
 }
}
let samples=0;
for(const day of ['2026-11-09','2026-11-10','2026-11-11','2026-11-12','2026-11-13','2026-11-14','2026-11-15']){
 for(let hour=0;hour<24;hour++){
  const now=Date.parse(day+'T'+String(hour).padStart(2,'0')+':27:00+01:00')/1000;
  const before=activeRailTrips(base,now,20000);
  const after=activeRailTrips(d,now,20000);
  const oldIds=new Set(before.map(t=>t.id));
  assert.deepEqual(after.filter(t=>oldIds.has(t.id)).map(t=>t.id).sort(),before.map(t=>t.id).sort());
  assert.equal(after.length,new Set(after.map(x=>x.id)).size);
  for(const t of after.filter(x=>x.package03Verified)){
   const p=railAt(t,now);
   assert(p.pos.every(Number.isFinite));
   assert(p.next>=0&&p.next<t.stops.length);
  }
  samples++;
 }
}
console.log('PACKAGE03 COMPLETE GREEN',samples,'HOURS SEVEN DAYS',add.map(x=>x.id),'10787 LEGACY TRAINS PRESERVED');
