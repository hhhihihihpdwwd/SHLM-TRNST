import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dirname,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
const modulePath=resolve(dirname(process.argv[3]),'../src/rail-data.js');
const {activeRailTrips,railAt}=await import(pathToFileURL(modulePath).href);
const original=JSON.parse(readFileSync(process.argv[2],'utf8'));
const updated=JSON.parse(readFileSync(process.argv[3],'utf8'));
assert.equal(original.trips.length,10798);
assert.equal(updated.trips.length,10799);
assert.deepEqual(updated.shapes,original.shapes);
assert.equal(Object.keys(updated.shapes).length,107);
assert.equal(updated.package06Audit.regularSourcePatterns,5);
assert.equal(updated.package06Audit.correctedAutumnEn345,2);
assert.equal(updated.package06Audit.addedAutumnSaturdayVariant,1);
const before=original.trips.filter(t=>t.agency!=='RDC EuroNight');
const after=updated.trips.filter(t=>t.agency!=='RDC EuroNight');
assert.deepEqual(after,before,'Previous 16-system rail data must remain unchanged');
assert.deepEqual(
 Object.entries(updated.counts).map(([k,v])=>[k,v-(k==='intercity'?1:0)]),
 Object.entries(original.counts)
);
const rdc=updated.trips.filter(t=>t.agency==='RDC EuroNight');
assert.equal(rdc.length,5);
assert.equal(rdc.filter(t=>t.line==='EN 344').length,2);
assert.equal(rdc.filter(t=>t.line==='EN 345').length,3);
assert.equal(rdc.every(t=>t.package06Verified&&t.isLiveGPS===false),true);
const byVariant=Object.fromEntries(rdc.map(t=>[t.package06Variant,t]));
for(const name of ['monfri-berlin','wed-hamburg','tue-hamburg','thu-berlin','sat-berlin'])
 assert(byVariant[name],name);
function departure(t){return t.stops[0][4]}
function arrival(t){return t.stops.at(-1)[3]}
assert.equal(departure(byVariant['tue-hamburg']),17*3600+29*60);
assert.equal(departure(byVariant['thu-berlin']),17*3600+29*60);
assert.equal(departure(byVariant['sat-berlin']),17*3600+29*60);
assert.equal(arrival(byVariant['tue-hamburg']),29*3600+53*60);
assert.equal(arrival(byVariant['thu-berlin']),32*3600+56*60);
assert.equal(arrival(byVariant['sat-berlin']),35*3600+10*60);
assert.equal(byVariant['thu-berlin'].destination,'Berlin Gesundbrunnen');
assert.equal(byVariant['sat-berlin'].destination,'Berlin Gesundbrunnen');
assert.equal(byVariant['tue-hamburg'].destination,'Hamburg Hbf');
assert(rdc.every(t=>!t.stops.some(s=>s[2]==='København Syd')),'Winter-only Copenhagen south stop leaked into autumn');
for(const t of rdc){
 assert(t.shapeId in updated.shapes);
 assert(t.stops.length>=10);
 for(let i=1;i<t.stops.length;i++){
  const a=t.stops[i-1][4],b=t.stops[i][3];
  assert(b>a,'non-monotonic official RDC clock');
 }
}
const expected={
 '2026-11-09':['monfri-berlin','thu-berlin'],
 '2026-11-10':['monfri-berlin','tue-hamburg'],
 '2026-11-11':['wed-hamburg','thu-berlin'],
 '2026-11-12':['monfri-berlin','thu-berlin'],
 '2026-11-13':['monfri-berlin','thu-berlin'],
 '2026-11-14':['monfri-berlin','sat-berlin'],
 '2026-11-15':['monfri-berlin','thu-berlin']
};
let checkpoints=0;
for(const [date,variants] of Object.entries(expected)){
 const epochStart=Date.parse(date+'T00:00:00+01:00')/1000;
 for(const variant of variants){
  const t=byVariant[variant],e=epochStart+departure(t)+60;
  const actual=activeRailTrips(updated,e,20000).filter(t=>t.agency==='RDC EuroNight');
  const thisLine=actual.filter(x=>x.line===t.line&&x.serviceDay===date);
  assert.equal(thisLine.length,1,'must display only one physical daily RDC train '+date+' '+t.line);
  assert.equal(thisLine[0].package06Variant,variant,'wrong original timetable selected '+date);
 }
 for(let hour=0;hour<24;hour++){
  const e=epochStart+hour*3600+37*60;
  const previous=activeRailTrips(original,e,20000).filter(t=>t.agency!=='RDC EuroNight');
  const actual=activeRailTrips(updated,e,20000);
  assert.deepEqual(actual.filter(t=>t.agency!=='RDC EuroNight').map(t=>t.id),
    previous.map(t=>t.id),'Other original rail vehicles changed '+date);
  assert.equal(actual.length,new Set(actual.map(t=>t.id)).size,'duplicate vehicle');
  for(const train of actual.filter(t=>t.agency==='RDC EuroNight')){
   const pos=railAt(train,e);
   assert(pos.pos.every(Number.isFinite));
   assert(pos.next>=0&&pos.next<train.stops.length);
   assert(pos.kmh>=0&&pos.kmh<240);
  }
  checkpoints++;
 }
}
for(const [variant,date] of [['tue-hamburg','2026-11-10'],['thu-berlin','2026-11-12'],
                            ['sat-berlin','2026-11-14'],['monfri-berlin','2026-11-09'],
                            ['wed-hamburg','2026-11-11']]){
 const t=byVariant[variant],zero=Date.parse(date+'T00:00:00+01:00')/1000;
 for(let i=1;i<t.stops.length;i++){
  const e=zero+Math.floor((t.stops[i-1][4]+t.stops[i][3])/2);
  const train=activeRailTrips(updated,e,20000).find(t=>t.agency==='RDC EuroNight'&&t.package06Variant===variant&&t.serviceDay===date);
  assert(train,'Official RDC train not visible on railway '+variant+' leg '+i);
  const p=railAt(train,e);
  assert(p.pos.every(Number.isFinite));
  assert.equal(p.next,i);
  assert(p.kmh>0&&p.kmh<240,'Unphysical historic rail speed '+variant+' '+p.kmh);
 }
}
console.log('PACKAGE06 GREEN: ALL 5 OPERATOR EN344/345 HISTORICAL ROUTE PATTERNS VERIFIED',checkpoints,'SEVEN-DAY NETWORK CHECKPOINTS, 10798 ORIGINAL VEHICLE RECORDS PROTECTED, ONE RDC VARIANT PER PHYSICAL TRAIN');
