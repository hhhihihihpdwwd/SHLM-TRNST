import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {activeRailTrips as newActive,railAt as newAt} from '../_release/website/src/rail-data.js';
import {activeRailTrips as oldActive,railAt as oldAt} from '../_stable30/website/src/rail-data.js';
import {matchesRailFilter} from '../_release/website/src/rail-filter.js';

const old=JSON.parse(await readFile('_stable30/website/data/rail.json','utf8'));
const now=JSON.parse(await readFile('_release/website/data/rail.json','utf8'));
const isArlanda=t=>t.agency==='Arlanda Express'&&t.mode==='express';
const other=data=>data.trips.filter(t=>!isArlanda(t));
assert.equal(now.arlandaWeekdaySimulation,true);
assert.equal(now.counts.express,1240);
assert.equal(old.counts.express,540);
assert.equal(now.trips.length,old.trips.length-540+1240);
assert.deepEqual(other(now),other(old),'Any other rail service has changed');
assert.deepEqual(now.shapes,old.shapes,'OSM rail geometry must not change');
assert.deepEqual(Object.fromEntries(Object.entries(now.counts).filter(([k])=>k!=='express')),
 Object.fromEntries(Object.entries(old.counts).filter(([k])=>k!=='express')));
const AX=now.trips.filter(isArlanda);
assert.equal(AX.length,1240);
assert.equal(new Set(AX.map(v=>v.id)).size,1240);
const byday=Object.fromEntries([...new Set(AX.map(t=>t.serviceDay))].sort()
 .map(d=>[d,AX.filter(t=>t.serviceDay===d).length]));
assert.deepEqual(byday,{
 '2026-11-04':180,'2026-11-05':180,'2026-11-06':180,'2026-11-07':160,
 '2026-11-08':180,'2026-11-09':180,'2026-11-10':180,
});
assert(AX.every(t=>t.geometryQuality==='verified-osm-relation'
 &&t.sourceTripId&&t.stops.length===3&&t.shapeId in now.shapes));
const screens=[];
for(const d of ['2026-11-16','2026-11-17','2026-11-18','2026-11-19',
 '2026-11-20','2026-11-21','2026-11-22']){
 for(const clock of ['00:30:00','05:30:00','07:30:00','09:47:00','10:53:22','12:30:00','16:30:00','19:30:00','23:30:00']){
  const epoch=Date.parse(d+'T'+clock+'+01:00')/1000;
  const a=newActive(now,epoch,30000),b=oldActive(old,epoch,30000);
  const rest=xs=>xs.filter(t=>!isArlanda(t));
  assert.deepEqual(rest(a).map(t=>t.id).sort(),rest(b).map(t=>t.id).sort(),
      'Original non-Arlanda live train changed '+d+' '+clock);
  const oldPositions=new Map(rest(b).map(t=>[t.id,oldAt(t,epoch).pos]));
  for(const t of rest(a))
   assert.deepEqual(newAt(t,epoch).pos,oldPositions.get(t.id),'Original train moved '+t.id);
  const actual=a.filter(isArlanda);
  for(const t of actual){
   assert(t._geom && t._anchors && t.stops.length===3);
   assert(newAt(t,epoch).pos.every(Number.isFinite));
  }
  screens.push({day:d,time:clock,arlanda:actual.length,all:a.length});
  console.log('ARLANDA-WEEK DAY',d,'TIME',clock,'X3 LIVE',actual.length,
    'ALL OTHER MODES PRESERVED',rest(a).length);
 }
}
await mkdir('_release/qa',{recursive:true});
await writeFile('_release/qa/arlanda-real-week-checks.json',JSON.stringify({byday,liveSamples:screens},null,2));
console.log('ARLANDA EXPRESS ALL 7 GTFS DAYS CHECKED 1240/1240, 63 TIME SLICES, NO OTHER RAIL CHANGES');
