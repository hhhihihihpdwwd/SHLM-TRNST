// Exhaustively check all eight original-authenticated cross-border physical
// train components and all original 16 systems against precise actual Swedish
// simulated time. Every train is a historical illustration, not live GPS.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {activeRailTrips,railAt} from '../src/rail-data.js';
import {matchesRailFilter} from '../src/rail-filter.js';
const file=process.argv[2]||process.env.SITE_ROOT+'/data/rail.json';
const data=JSON.parse(readFileSync(file,'utf8'));
assert.equal(data.trips.length,10787);
assert.equal(data.internationalFourAudited['Snälltåget'].addedNonOverlappingSegments,8);
for(const a of ['Vy Tåg','Tågab','RDC EuroNight'])
 assert.equal(data.internationalFourAudited[a].added,0,'Already fully represented source '+a);
const newtrips=data.trips.slice(10779);
assert.equal(newtrips.length,8);
assert(newtrips.every(t=>t.agency==='Snälltåget'&&t.snallCrossborderVerified&&
  t.isLiveGPS===false&&t.sourceTripId&&t.shapeId in data.shapes));
const oldids=new Set(data.trips.slice(0,10779).map(t=>t.id));
assert(newtrips.every(x=>!oldids.has(x.id)));
const physical=new Set(newtrips.map(t=>JSON.stringify(t.historicalPhysicalKey)));
assert.equal(physical.size,8,'Parallel duplicate physical train histories');
for(const t of newtrips){
 const old=t.existingDomesticContinuation;
 if(old){
  const matched=data.trips.find(x=>x.id===old);
  assert(matched,'Foreign segment has no existing original domestic train');
  assert(t.segmentKind==='foreign-prefix'||t.segmentKind==='foreign-suffix');
  assert(t.end<=matched.start||t.start>=matched.end,'Duplicate train at same time on same domestic line '+t.id);
 }
 const midpoint=t.start+Math.floor((t.end-t.start)/2);
 const active=activeRailTrips(data,midpoint,20000).find(x=>x.id===t.id+':DAILY:'+data.simulationTemplateDay);
 assert(active,'Missing genuine Snälltåget at its historic travel midpoint '+t.id);
 const p=railAt(active,midpoint);
 assert(p.pos.every(Number.isFinite)&&p.next>=0&&p.next<t.stops.length);
 assert(p.meters>active._anchors[0]&&p.meters<active._anchors.at(-1));
 for(let i=1;i<t.stops.length;i++){
  const a=t.stops[i-1],b=t.stops[i],secs=b[3]-a[4];
  if(secs<90)continue;
  const epoch=t.start-t.stops[0][4]+Math.floor((a[4]+b[3])/2);
  const train=activeRailTrips(data,epoch,20000).find(x=>x.id===t.id+':DAILY:'+data.simulationTemplateDay);
  assert(train,'New original source train not moving between stops '+t.id);
  const next=railAt(train,epoch);
  assert(next.kmh>0&&next.kmh<230,'Cross-border train frozen or unrealistic rail speed '+t.id+' leg '+i);
 }
 console.log('SNÄLLTÅGET INTERNATIONAL RAILWAY VALID',t.segmentKind,
  t.stops[0][2],'→',t.stops.at(-1)[2],'KM',Math.round(active._anchors.at(-1)/1000));
}
const ref=Date.parse(data.simulationTemplateDay+'T00:00:00+01:00')/1000;
const source=data.trips.filter(t=>t.serviceDay===data.simulationTemplateDay &&
 (t.geometryQuality==='verified-osm-relation'||
 (t.mode==='regional'&&t.geometryQuality==='verified-osm-rail-ways')||
 (t.mode==='intercity'&&t.geometryQuality==='verified-osm-rail-ways'&&
  (['VR Snabbtåg','Vy Tåg','Tågab','RDC EuroNight'].includes(t.agency)||
  (t.agency==='SJ'&&t.sjCompleteVerified)||
  (t.agency==='Snälltåget'&&t.snallCrossborderVerified)))));
const stockholm=(iso)=>Date.parse(iso+'T00:00:00+01:00')/1000;
function prevDate(iso){
 const date=new Date(iso+'T12:00:00Z');date.setUTCDate(date.getUTCDate()-1);
 return date.toISOString().slice(0,10);
}
let compared=0,peak=0;
for(const day of ['2026-11-09','2026-11-10','2026-11-11','2026-11-12','2026-11-13','2026-11-14','2026-11-15']){
 for(let min=0;min<1440;min+=60){
  const epoch=stockholm(day)+min*60;
  const expected=[];
  for(const runDay of [prevDate(day),day]){
   const shift=stockholm(runDay)-ref;
   for(const t of source)if(epoch>=t.start+shift&&epoch<t.end+shift)
    expected.push(t.id+':DAILY:'+runDay);
  }
  const actual=activeRailTrips(data,epoch,20000);
  assert.deepEqual(actual.map(t=>t.id).sort(),expected.sort(),
   'Hidden or invented historic 16-system train on '+day+' minute '+min);
  assert.equal(actual.length,new Set(actual.map(t=>t.id)).size,'Duplicate physical vehicle ID');
  peak=Math.max(peak,actual.length);compared++;
 }
}
console.log('ALL OPERATOR ACTIVE RAIL TRAINS VERIFIED',compared,'INDEPENDENT HOURS ACROSS SEVEN DAYS; PEAK',peak);
console.log('SINGLE INTERNATIONAL RELEASE VALID',data.trips.length,'TOTAL TRAIN TEMPLATES',Object.keys(data.shapes).length,'PHYSICAL RAIL GEOMETRIES, 8 NEW CROSS-BORDER SOURCE SEGMENTS');
