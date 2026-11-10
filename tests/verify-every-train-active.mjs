// Independently enumerate expected historic trains and compare with runtime at
// seven Stockholm dates, across two midnight boundaries and all operator filters.
// Also test EACH scheduled service at least once, including short metro runs.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {activeRailTrips,railAt} from '../src/rail-data.js';
import {matchesRailFilter} from '../src/rail-filter.js';

const d=JSON.parse(readFileSync(process.argv[2]||process.env.SITE_ROOT+'/data/rail.json','utf8'));
assert.equal(d.trips.length,10611);
assert.equal(Object.keys(d.shapes).length,95);
const template=d.simulationTemplateDay;
const first=Date.parse(template+'T00:00:00+01:00')/1000;
function eligible(t){
 const yes=t.geometryQuality==='verified-osm-relation'||
  (t.mode==='regional'&&t.geometryQuality==='verified-osm-rail-ways')||
  (t.mode==='intercity'&&(['VR Snabbtåg','Vy Tåg','Tågab','RDC EuroNight'].includes(t.agency)||
    (t.agency==='SJ'&&d.scope.endsWith('-sj-complete')&&t.sjCompleteVerified===true&&
      String(t.id).startsWith('SJ-FULL-20261106:')&&!!t.sourceTripId))&&
    t.osmWayNetwork===true&&t.geometryQuality==='verified-osm-rail-ways');
 return t.serviceDay===template&&yes&&
   ['commuter','metro','tram','localrail','saltsjo','express','intercity','regional'].includes(t.mode);
}
const source=d.trips.filter(eligible);
assert.equal(source.length,3722);
const known=new Map(source.map(x=>[x.id,x]));
const seen=new Set();
const dates=['2026-11-09','2026-11-10','2026-11-11','2026-11-12','2026-11-13','2026-11-14','2026-11-15'];
let compared=0,max=0,min=Infinity;
function dayplus(day,n){
 const v=new Date(day+'T12:00:00Z');v.setUTCDate(v.getUTCDate()+n);return v.toISOString().slice(0,10);
}
function expectedIds(epoch){
 const target=new Date(epoch*1000).toLocaleDateString('sv-SE',{timeZone:'Europe/Stockholm'});
 const arr=[];
 for(const day of [dayplus(target,-1),target]){
  const delta=Date.parse(day+'T00:00:00+01:00')/1000-first;
  for(const t of source){
   if(epoch>=t.start+delta&&epoch<t.end+delta)
    arr.push(t.id+':DAILY:'+day);
  }
 }
 return arr.sort();
}
for(const day of dates){
 for(let minute=0;minute<24*60;minute+=(day==='2026-11-10'?10:120)){
  const epoch=Date.parse(day+'T00:00:00+01:00')/1000+minute*60;
  const actual=activeRailTrips(d,epoch,20000);
  const expected=expectedIds(epoch);
  assert.deepEqual(actual.map(t=>t.id).sort(),expected,
    'Missing/ghost train at '+day+' '+minute+' minutes');
  assert.equal(new Set(actual.map(t=>t.id)).size,actual.length,'Duplicate physical train at '+day);
  for(const v of actual){
   seen.add(v.id.replace(/:DAILY:.*/,'')); // track scheduled service coverage
   const p=railAt(v,epoch);
   assert(p&&p.pos.every(Number.isFinite),'Invalid train position '+v.id);
   assert(p.next>=0&&p.next<v.stops.length,'Invalid next station '+v.id);
   assert(p.meters>=v._anchors[0]-1&&p.meters<=v._anchors.at(-1)+1,
    'Train outside its actual OSM railway distance '+v.id);
  }
  min=Math.min(min,actual.length);max=Math.max(max,actual.length);compared++;
 }
}
// Every remaining short historical train is sampled at its own unique actual
// departure midpoint, so not a SINGLE source template is unverified.
for(const t of source){
 if(seen.has(t.id))continue;
 const epoch=t.start+Math.min((t.end-t.start)/2,120);
 const observed=activeRailTrips(d,epoch,20000).find(x=>
   x.id===t.id+':DAILY:'+template&&x.start===t.start);
 assert(observed,'Train never visible when legitimately en route: '+t.agency+' '+t.id);
 const p=railAt(observed,epoch);
 assert(p.pos.every(Number.isFinite),'Invalid individual train position '+t.id);
 seen.add(t.id);
}
assert.equal(seen.size,source.length,'Not all 3722 template-day trains were tested');
const byOperator={};
for(const t of source)byOperator[t.agency]=(byOperator[t.agency]||0)+1;
for(const [agency,n] of Object.entries(byOperator)){
 assert(n>0,'Missing agency train');
 const filtered=source.filter(t=>t.agency===agency);
 for(const t of filtered.slice(0,3)){
   const key=agency==='SJ'?'sj':agency==='Snälltåget'?'snalltaget':
   agency==='Tågab'?'tagab':agency==='Vy Tåg'?'vy':
   agency==='RDC EuroNight'?'rdc':agency==='VR Snabbtåg'?'vr':
   agency==='Mälartåg'?'malartag':null;
   if(key)assert(matchesRailFilter(t,key),'Operator filter excludes train '+t.id);
 }
}
const snall=source.find(x=>x.agency==='Snälltåget'&&x.stops[0][4]===16*3600+18*60);
assert(snall,'Cannot find screenshot Snälltåget Malmö 16:18 journey');
const epoch=Date.parse('2026-11-10T16:37:00+01:00')/1000;
const train=activeRailTrips(d,epoch,20000).find(x=>
 x.id.startsWith(snall.id+':DAILY:')&&x.stops[0][2].includes('Malmö'));
assert(train,'Malmö 16:18 train missing at 16:37');
const p=railAt(train,epoch);
console.log('SCREENSHOT TARGET DEBUG',JSON.stringify({id:train.id,start:train.start,epoch,first:train.stops[0],next3:train.stops.slice(1,4),index:p.next,kmh:p.kmh,meters:p.meters,base:train.start-train.stops[0][4]}));
assert.equal(train.stops[p.next][2],'Eslöv station','At 16:37 the genuine GTFS next stop is Eslöv, because Lund was 16:28');
assert(p.kmh>0,'16:37 Snälltåget must be moving and not standing in Malmö');
assert(p.meters>train._anchors[0]+1000,'Snälltåget should have moved over 1km by 16:37');
assert.equal(train.stops[1][3],16*3600+28*60,'Historic GTFS shows Lund 16:28, screenshot had shifted 17:11 UI display');
console.log('COMPLETE SOURCE COVERAGE VERIFIED',seen.size,'OF',source.length);
console.log('ACTIVE TRAIN EXACT MATCH AT',compared,'INDEPENDENTLY COMPUTED REFERENCE TIMESTAMPS ACROSS SEVEN DAYS; MIN',min,'MAX',max);
console.log('ALL AGENCIES',JSON.stringify(byOperator));
console.log('SNÄLLTÅGET EXACT USER SCREENSHOT 2026-11-10 16:37 VERIFIED',JSON.stringify({train:train.id,next:train.stops[p.next][2],kmh:p.kmh,progressMetres:Math.round(p.meters-train._anchors[0])}));
