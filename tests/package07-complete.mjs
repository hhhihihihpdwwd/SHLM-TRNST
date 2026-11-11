import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dirname,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
const base=JSON.parse(readFileSync(process.argv[2],'utf8'));
const d=JSON.parse(readFileSync(process.argv[3],'utf8'));
const proof=JSON.parse(readFileSync(process.argv[4],'utf8'));
const {activeRailTrips,railAt}=await import(pathToFileURL(resolve(dirname(process.argv[3]),'../src/rail-data.js')).href);
const {matchesRailFilter}=await import(pathToFileURL(resolve(dirname(process.argv[3]),'../src/rail-filter.js')).href);
assert.equal(base.trips.length,10799);
assert.equal(d.trips.length,10827);
assert.equal(Object.keys(base.shapes).length,107);
assert.deepEqual(d.shapes,base.shapes);
assert.deepEqual(d.trips.slice(0,10799),base.trips);
assert.equal(d.package07Audit.verifiedAdditionalShortTurnReturnJourneys,28);
assert.equal(d.package07Audit.deferredJourneysWithoutConnectedOsm,0);
assert.equal(proof.newVerifiedTrips.length,28);
assert.deepEqual(proof.deferredTrips,[]);
for(const [k,v] of Object.entries(base)){
 if(!['trips','counts'].includes(k))assert.deepEqual(d[k],v,'prior 16 system metadata '+k);
}
for(const [k,v] of Object.entries(base.counts)){
 assert.equal(d.counts[k],v+d.trips.slice(10799).filter(t=>t.mode===k).length,k);
}
const added=d.trips.slice(10799);
assert.equal(new Set(added.map(t=>t.id)).size,28);
const lines=Object.fromEntries([...new Set(added.map(t=>t.line))].map(x=>[x,added.filter(t=>t.line===x).length]));
assert.deepEqual(lines,{'13':2,'17':3,'19':1,'40':20,'41':1,'43':1});
assert(added.every(t=>t.package07Verified&&t.isLiveGPS===false&&t.geometryQuality==='verified-osm-relation'));
const zero=Date.parse('2026-11-09T00:00:00+01:00')/1000;
for(const t of added){
 assert(t.shapeId in d.shapes);
 assert(t.stops.length>=2);
 assert.equal(t.start-zero,t.stops[0][4]);
 assert.equal(t.end-zero,t.stops.at(-1)[3]);
 for(let i=1;i<t.stops.length;i++){
  const departure=t.stops[i-1][4],arrival=t.stops[i][3];
  assert(arrival>departure,'nonmonotonic published historical stop times');
  const epoch=zero+Math.floor((departure+arrival)/2);
  const t2=activeRailTrips(d,epoch,20000).find(x=>x.id===t.id+':DAILY:2026-11-09');
  assert(t2,'Authenticated missing reverse train is not shown halfway along real rail '+t.id+' leg '+i);
  const state=railAt(t2,epoch);
  assert(state.pos.every(Number.isFinite),'train marker invalid '+t.id);
  assert(state.next===i,'next station corrupted '+t.id);
  assert(state.kmh>0&&state.kmh<220,'unphysical mean track speed '+t.id+' '+state.kmh);
 }
}
const checks=['commuter','metro','tram','nockeby','lidingo','city7','roslags','saltsjo','arlanda'];
let samples=0;
for(const date of ['2026-11-09','2026-11-10','2026-11-11','2026-11-12','2026-11-13','2026-11-14','2026-11-15']){
 for(let hour=0;hour<24;hour++){
  const epoch=Date.parse(date+'T'+String(hour).padStart(2,'0')+':27:00+01:00')/1000;
  const prior=activeRailTrips(base,epoch,20000);
  const after=activeRailTrips(d,epoch,20000);
  const priorId=new Set(prior.map(t=>t.id));
  assert.deepEqual(after.filter(t=>priorId.has(t.id)).map(t=>t.id).sort(),
   prior.map(t=>t.id).sort(),'legacy active vehicles changed '+date+' '+hour);
  assert.equal(new Set(after.map(t=>t.id)).size,after.length,'duplicate moving vehicle');
  for(const t of after.filter(t=>t.package07Verified)){
   assert(railAt(t,epoch).pos.every(Number.isFinite));
  }
  if(hour>=7&&hour<=22){
   for(const f of checks)if(after.some(t=>matchesRailFilter(t,f)))daySeen.add(f);
  }
  samples++;
 }
 for(const f of checks)assert(daySeen.has(f),'No daytime sample for '+f+' on historical repeat '+date);
}
const group=new Map();
for(const t of d.trips.filter(t=>['commuter','metro','tram','localrail','saltsjo','express'].includes(t.mode))){
 const key=(t.mode==='commuter'?'commuter':t.mode==='metro'?'metro':String(t.line));
 const entry=group.get(key)||{count:0,terminals:new Set(),trips:[]};
 entry.count++;entry.terminals.add(t.stops[0][2]);entry.terminals.add(t.stops.at(-1)[2]);
 entry.trips.push(t);group.set(key,entry);
}
for(const [key,e] of group){
 if(e.count<2)continue;
 if(e.trips.length>=5){
  const first= new Set(e.trips.map(t=>t.stops[0][2]));
  const last= new Set(e.trips.map(t=>t.stops.at(-1)[2]));
  assert([...first].some(x=>last.has(x)),'no opposite direction at all in '+key);
 }
}
console.log('PACKAGE07 ALL GREEN: 28 GENUINE HISTORICAL SL RETURNS',Object.fromEntries(Object.entries(lines).sort()),
 'ALL 10799 LEGACY TRAINS UNCHANGED',samples,'HOURLY SNAPSHOTS SEVEN DAYS ALL NINE STOCKHOLM LOCAL FILTERS');
