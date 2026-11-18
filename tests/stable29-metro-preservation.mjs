// Strict weekday-aware Metro-only regression versus the immutable STABLE22
// and STABLE28 source baselines. No altered operator or photo/track source.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {activeRailTrips as oldActive,railAt as oldAt} from '../_stable28/website/src/rail-data.js';
import {activeRailTrips as refActive,railAt as refAt} from '../_historicweek/website/src/rail-data.js';
import {activeRailTrips as newActive,railAt as newAt} from '../_release/website/src/rail-data.js';

const oldData=JSON.parse(fs.readFileSync('_stable28/website/data/rail.json','utf8'));
const reference=JSON.parse(fs.readFileSync('_historicweek/website/data/rail.json','utf8'));
const latest=JSON.parse(fs.readFileSync('_release/website/data/rail.json','utf8'));
const lines=['10','11','13','14','17','18','19'];
assert.equal(latest.counts.metro,13372);
assert.equal(latest.trips.length,21402);
assert.equal(latest.metroWeekdaySimulation,true);
const nonmetro=ds=>ds.trips.filter(x=>x.mode!=='metro');
assert.deepEqual(nonmetro(latest),nonmetro(oldData));
assert.deepEqual(latest.metroWeeklyCoverage,reference.metroWeeklyCoverage);
for(const [key,oldshape] of Object.entries(oldData.shapes))
 assert.deepEqual(latest.shapes[key],oldshape,'Existing track points changed '+key);
for(const key of Object.keys(oldData.counts).filter(k=>k!=='metro'))
 assert.equal(latest.counts[key],oldData.counts[key],'Other system record count changed '+key);
const expectedDay={day:'2026-11-18',time:'09:47:00',total:67,byLine:[6,6,11,11,10,11,12]};
let old09=0,cur09=0;
for(const day of ['2026-11-16','2026-11-17','2026-11-18','2026-11-19','2026-11-20','2026-11-21','2026-11-22']){
 for(const h of ['00:30:00','02:15:00','05:30:00','07:30:00','08:30:00','09:47:00',
                  '12:30:00','16:30:00','19:30:00','23:30:00']){
  const epoch=Date.parse(day+'T'+h+'+01:00')/1000;
  const actual=newActive(latest,epoch,25000);
  const referenceTrains=refActive(reference,epoch,25000);
  const previous=oldActive(oldData,epoch,25000);
  const metro=actual.filter(t=>t.mode==='metro');
  const referenceMetro=referenceTrains.filter(t=>t.mode==='metro');
  assert.equal(metro.length,referenceMetro.length,'Metro completeness: '+day+' '+h);
  const key=t=>[t.sourceTripId,t.serviceDay,t.line,t.start,t.end,t.shapeId].join('|');
  assert.deepEqual(metro.map(key).sort(),referenceMetro.map(key).sort(),
    'Metro actual source trips differ from all historic GTFS trips: '+day+' '+h);
  for(const line of lines)assert.equal(
    metro.filter(t=>String(t.line)===line).length,
    referenceMetro.filter(t=>String(t.line)===line).length,
    'Incomplete line '+line+' '+day+' '+h);
  const other=xs=>xs.filter(x=>x.mode!=='metro');
  assert.deepEqual(other(actual).map(t=>t.id).sort(),other(previous).map(t=>t.id).sort(),
    'Changed source operator outside Metro '+day+' '+h);
  // Geometry equality extends to every active old non-Metro train position.
  const oldMap=new Map(other(previous).map(t=>[t.id,oldAt(t,epoch).pos]));
  for(const train of other(actual))
   assert.deepEqual(newAt(train,epoch).pos,oldMap.get(train.id),'Moved nonmetro train '+train.id);
  assert.equal(new Set(actual.map(t=>t.id)).size,actual.length,'Duplicated running vehicle');
  for(const train of metro){
   const pos=newAt(train,epoch).pos;
   assert.equal(pos.length,2);
   assert(pos.every(Number.isFinite),'Invalid OSM geometry coordinate '+train.id);
   assert(pos[0]>=58.7&&pos[0]<=60.1&&pos[1]>=17.1&&pos[1]<=19.4,
      'Metro off Stockholm rail region '+train.id+' '+JSON.stringify(pos));
  }
  if(day==='2026-11-18'&&h==='09:47:00'){
   cur09=metro.length;old09=previous.filter(t=>t.mode==='metro').length;
   assert.equal(cur09,expectedDay.total);
   assert.deepEqual(lines.map(line=>metro.filter(t=>String(t.line)===line).length),expectedDay.byLine);
   assert.equal(old09,16);
  }
  console.log('SEVEN-DAY LIVE-SIMULATION AUDIT',day,h,'Metro',metro.length,'Other systems',other(actual).length,'ALL ORIGINAL OTHER SYSTEMS UNCHANGED');
 }
}
assert.equal(cur09,67);assert.equal(old09,16);
console.log('SEVEN-DAY AUDIT COMPLETE: Wed 09:47 now 67/67 vs previously 16/67; 15 other systems identical');
