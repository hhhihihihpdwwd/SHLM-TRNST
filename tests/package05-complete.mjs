import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {activeRailTrips,railAt} from '../src/rail-data.js';
import {matchesRailFilter} from '../src/rail-filter.js';
const base=JSON.parse(readFileSync(process.argv[2],'utf8'));
const d=JSON.parse(readFileSync(process.argv[3],'utf8'));
const report=JSON.parse(readFileSync(process.argv[4],'utf8'));
assert.equal(base.trips.length,10798);
assert.equal(d.trips.length,10798);
assert.equal(Object.keys(d.shapes).length,107);
assert.deepEqual(d.trips,base.trips);
assert.deepEqual(d.shapes,base.shapes);
assert.deepEqual(d.counts,base.counts);
assert.deepEqual(Object.keys(base).sort(),Object.keys(d).filter(k=>k!=='package05Audit').sort());
for(const [k,v] of Object.entries(base))assert.deepEqual(d[k],v,k);
assert.deepEqual(d.package05Audit.addedPerOperator,{'Vy Tåg':0,'Tågab':0});
assert.equal(d.package05Audit.deferredCount,0);
assert.equal(report.operatorResults['Vy Tåg'].coveredSourcePatterns,10);
assert.equal(report.operatorResults['Vy Tåg'].uniqueStopClockPatterns,10);
assert.equal(report.operatorResults['Tågab'].coveredSourcePatterns,15);
assert.equal(report.operatorResults['Tågab'].uniqueStopClockPatterns,15);
assert.deepEqual(report.added,[]);
assert.deepEqual(report.deferred,[]);
for(const [agency,expected] of [['Vy Tåg',10],['Tågab',16]]){
 const trains=d.trips.filter(t=>t.agency===agency);
 assert.equal(trains.length,expected);
 const directions=new Set(trains.map(t=>t.direction));
 assert(directions.has('to-stockholm')&&directions.has('from-stockholm'));
 for(const t of trains){
  assert.equal(t.isLiveGPS,false);
  assert(t.geometryQuality==='verified-osm-rail-ways'||t.geometryQuality==='verified-osm-relation');
  assert(t.stops.length>=3);
  assert(d.shapes[t.shapeId]?.length>=30);
  for(let i=1;i<t.stops.length;i++)assert(t.stops[i][3]>t.stops[i-1][4]);
  for(let i=1;i<t.stops.length;i++){
   const a=t.stops[i-1][4],b=t.stops[i][3];
   const now=Date.parse('2026-11-09T00:00:00+01:00')/1000+Math.floor((a+b)/2);
   const v=activeRailTrips(d,now,20000).find(x=>x.id===t.id+':DAILY:2026-11-09');
   assert(v,'Authentic published train invisible mid-leg: '+t.id);
   const p=railAt(v,now);
   assert(p.pos.every(Number.isFinite));
   assert(p.next===i,'Incorrect next stop '+t.id);
   assert(p.kmh>0&&p.kmh<240,'Train not moving with plausible speed '+t.id+' '+p.kmh);
  }
 }
}
let checkpoints=0;
for(const day of ['2026-11-09','2026-11-10','2026-11-11','2026-11-12','2026-11-13','2026-11-14','2026-11-15']){
 for(let hour=0;hour<24;hour++){
  const now=Date.parse(day+'T'+String(hour).padStart(2,'0')+':37:00+01:00')/1000;
  const a=activeRailTrips(base,now,20000),b=activeRailTrips(d,now,20000);
  assert.deepEqual(b.map(t=>t.id),a.map(t=>t.id));
  assert.equal(new Set(b.map(t=>t.id)).size,b.length);
  for(const op of ['Vy Tåg','Tågab']){
   const current=b.filter(v=>v.agency===op);
   for(const t of current){
    assert(matchesRailFilter(t,op==='Vy Tåg'?'vy':'tagab'));
    const p=railAt(t,now);
    assert(p.pos.every(Number.isFinite));assert(p.next>=0&&p.next<t.stops.length);
   }
  }
  checkpoints++;
 }
}
console.log('PACKAGE05 FULL HISTORIC COVERAGE VERIFIED: VY 10 OF 10, TÅGAB 15 OF 15 PATTERNS, 26 PUBLISHED TRAIN TEMPLATES, 16 SYSTEMS UNCHANGED,',checkpoints,'NETWORK CHECKPOINTS');
