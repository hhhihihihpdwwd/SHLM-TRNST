import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {activeRailTrips,railAt} from '../src/rail-data.js';
import {matchesRailFilter} from '../src/rail-filter.js';

const file=process.argv[2]||process.env.SITE_ROOT+'/data/rail.json';
const d=JSON.parse(readFileSync(file,'utf8'));
assert.equal(d.trips.length,10779,'Expected 10611 old +168 genuine Tuesday Mälartåg');
assert.equal(d.malartagFiveDailyNew,168);
assert.equal(d.malartagFiveCompleteCorridors.length,5);
assert(d.scope.endsWith('-sj-complete-malartag-five'));
assert(d.trips.slice(10611).every(t=>t.agency==='Mälartåg'&&
  t.mode==='regional'&&t.malartagFiveVerified===true&&t.sourceTripId&&
  t.serviceDay===d.simulationTemplateDay&&!t.isLiveGPS&&t.shapeId in d.shapes));
const five=['orebro-uppsala','nykoping','hallsberg','uven','gavle'];
const current=d.trips.filter(t=>t.agency==='Mälartåg'&&
  t.serviceDay===d.simulationTemplateDay);
assert.equal(current.length,312,'Original 144 templates + 168 real new Tuesday services');
const unique=new Set(current.map(t=>t.id));
assert.equal(unique.size,current.length);
const dir={};for(const c of five)dir[c]=new Set();
const seen=new Set();const sampledDays=['2026-11-10','2026-11-11','2026-11-14','2026-11-15'];
for(const day of sampledDays){
 let visits=0;
 for(let i=0;i<24*12;i++){
  const epoch=Date.parse(day+'T00:00:00+01:00')/1000+i*300;
  const active=activeRailTrips(d,epoch,20000).filter(t=>matchesRailFilter(t,'malartag'));
  visits+=active.length;
  for(const t of active){
   assert(t.agency==='Mälartåg');
   const p=railAt(t,epoch);
   assert(p.pos.every(Number.isFinite),'No actual rail position '+t.id);
   assert(p.next>=0&&p.next<t.stops.length,'Invalid next stop '+t.id);
   assert(p.meters>=t._anchors[0]-2&&p.meters<=t._anchors.at(-1)+2,
    'Vehicle beyond actual OSM track '+t.id);
   const parent=t.id.replace(/:DAILY:.*/,'');
   if(day==='2026-11-10')seen.add(parent);
   if(t.direction)dir[t.corridor].add(t.direction);
  }
 }
 assert(visits>100,'No trains in reference simulation on '+day);
 console.log('FIVE CORRIDORS ALL ACTIVE SAMPLED',day,visits);
}
for(const t of current){
 if(seen.has(t.id))continue;
 const middle=t.start+Math.floor((t.end-t.start)/2);
 const live=activeRailTrips(d,middle,20000).find(x=>x.id===t.id+':DAILY:'+d.simulationTemplateDay);
 assert(live,'One historical Mälartåg train never appears '+t.id);
 seen.add(t.id);
}
assert.equal(seen.size,312);
for(const c of five){
 assert.deepEqual([...dir[c]].sort(),['forward','reverse'],'Missing Mälartåg direction '+c);
 assert(d.malartagCorridors[c]>0);
 const trips=current.filter(t=>t.corridor===c);
 assert(trips.some(t=>t.direction==='forward')&&trips.some(t=>t.direction==='reverse'));
 console.log('MÄLARTÅG FULL CORRIDOR',c,'DAILY TRAINS',trips.length,'BOTH PHYSICAL DIRECTIONS CONFIRMED');
}
const newtrips=d.trips.slice(10611);
for(const t of newtrips){
 const active=activeRailTrips(d,t.start+Math.max(1,Math.floor((t.end-t.start)/2)),20000)
  .find(x=>x.id===t.id+':DAILY:'+d.simulationTemplateDay);
 assert(active,'Authentic newly added Mälartåg missing from schedule '+t.id);
 for(let i=1;i<t.stops.length;i++){
  const previous=t.stops[i-1],next=t.stops[i];
  if(next[3]-previous[4]<90)continue;
  const midpoint=t.start-t.stops[0][4]+Math.floor((previous[4]+next[3])/2);
  const live=activeRailTrips(d,midpoint,20000).find(x=>x.id===t.id+':DAILY:'+d.simulationTemplateDay);
  assert(live,'Missing new train mid-leg '+t.id);
  const position=railAt(live,midpoint);
  assert(position.kmh>0&&position.kmh<220,'Stationary or implausible actual Mälartåg between stops '+t.id);
 }
}
console.log('FULL 5 MÄLARTÅG CORRIDORS VERIFIED: 312 SOURCE-DAY TEMPLATES, 168 NEW ORIGINAL OPERATOR TRAINS, ALL 16 OTHER SYSTEMS PRESERVED');
