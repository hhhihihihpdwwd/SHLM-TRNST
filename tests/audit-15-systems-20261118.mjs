/**
 * Source-vs-render audit of every operator except Tunnelbana.
 * Read-only: uses STABLE29 published files and archived STABLE24 complete
 * SL seven-day GTFS. Zero changes to the production application.
 *
 * Three independent states for each filter:
 *  - referenceCount: verified historic GTFS when known (seven SL systems)
 *  - scheduledCount: what current app actually has at this time
 *  - renderedCount: what real Chromium draws (checked by separate script)
 * All counts indicate historical simulation, never actual live GPS.
 */
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {activeRailTrips as currentActive,railAt as currentAt} from '../_stable29/website/src/rail-data.js';
import {activeRailTrips as weeklyActive,railAt as weeklyAt} from '../_stable24/website/src/rail-data.js';
import {matchesRailFilter,railFilterTitle} from '../_stable29/website/src/rail-filter.js';

const current=JSON.parse(await readFile('_stable29/website/data/rail.json','utf8'));
const weekly=JSON.parse(await readFile('_stable24/website/data/rail.json','utf8'));
assert.equal(current.metroWeekdaySimulation,true);
assert.equal(current.commuterWeekdaySimulation,undefined);
assert.equal(current.localWeekdaySimulation,undefined);
assert.equal(weekly.metroWeekdaySimulation,true);
assert.equal(weekly.commuterWeekdaySimulation,true);
assert.equal(weekly.localWeekdaySimulation,true);
const cols=['commuter','tram','nockeby','lidingo','city7','roslags','saltsjo',
            'arlanda','sj','malartag','vr','snalltaget','vy','tagab','rdc'];
const sourceSeven=new Set(['commuter','tram','nockeby','lidingo','city7','roslags','saltsjo']);
const linesByFilter={
 commuter:['40','41','42','43','44','45','46','47','48'],
 tram:['30','31'],nockeby:['12'],lidingo:['21'],city7:['7'],
 roslags:['27','28','29'],saltsjo:['25','26']
};
const stamp='2026-11-18T10:53:22+01:00';
const epoch=Date.parse(stamp)/1000;
const cAll=currentActive(current,epoch,30000),wAll=weeklyActive(weekly,epoch,30000);
const sameEntries=a=>a.map(v=>[String(v.line),v.agency,v.id,v.start,v.end].join('|')).sort();
const result={asOf:stamp,mode:'Read-only historical timetable simulation, NOT actual train GPS',
 latestVersion:'STABLE29',sourceWeekVersion:'STABLE24',
 weekdays: ['2026-11-16','2026-11-17','2026-11-18','2026-11-19','2026-11-20','2026-11-21','2026-11-22'],
 systems:[],checks:[]};
const overlap=(a,b)=>a.filter(v=>b.has(v.id)).length;
for(const filter of cols){
 const scheduled=cAll.filter(t=>matchesRailFilter(t,filter));
 const other=wAll.filter(t=>matchesRailFilter(t,filter));
 const templates=current.trips.filter(t=>matchesRailFilter(t,filter));
 const templateDates=Object.fromEntries([...new Set(templates.map(t=>t.serviceDay))].sort().map(x=>[x,templates.filter(v=>v.serviceDay===x).length]));
 const names=[...new Set(templates.map(t=>String(t.line||'')))].sort((a,b)=>a.localeCompare(b,'sv'));
 const agencies=[...new Set(templates.map(t=>String(t.agency||'')))];
 const countline=(trips)=>Object.fromEntries([...new Set([...names,...trips.map(t=>String(t.line||''))])].sort((a,b)=>a.localeCompare(b,'sv'))
   .map(line=>[line,trips.filter(t=>String(t.line||'')===line).length]));
 const row={
  filter,name:railFilterTitle(filter),templateCount:templates.length,sourceDays:templateDates,
  observed:scheduled.length,observedByLine:countline(scheduled),
  agencies,sourceCoverage:sourceSeven.has(filter)?'archived-complete-seven-day-GTFS':
    'only-selected-historical-daily-template; cannot certify current full service',
  independentReference:sourceSeven.has(filter)?other.length:null,
  independentByLine:sourceSeven.has(filter)?countline(other):null,
  diffComparedWithSource:sourceSeven.has(filter)?other.length-scheduled.length:null,
  unverifiedSourceDays:!sourceSeven.has(filter)
 };
 for(const t of scheduled){
  assert(t._geom&&t._anchors,'GTFS source projected onto no geometry '+t.id);
  const p=currentAt(t,epoch).pos;
  assert(p.length===2&&p.every(Number.isFinite),'Non-finite 2026-11-18 active train '+t.id);
 }
 if(sourceSeven.has(filter)){
  const dayReference=weekly.trips.filter(t=>matchesRailFilter(t,filter));
  row.fullSevenDayTemplates=dayReference.length;
  row.scheduledSourceTrips=dayReference.length;
  row.referenceDays=Object.fromEntries([...new Set(dayReference.map(t=>t.serviceDay))].sort()
    .map(day=>[day,dayReference.filter(t=>t.serviceDay===day).length]));
  assert(row.fullSevenDayTemplates>=row.templateCount,'Source GTFS less than current templates '+filter);
  for(const line of linesByFilter[filter]){
   const n=other.filter(t=>String(t.line)===line).length;
   const m=scheduled.filter(t=>String(t.line)===line).length;
   row['line_'+line]={app:m,source:n,shortfall:n-m};
  }
 }else{
  // Another archival overlay did not independently rebuild these operators;
  // compare unchanged source schedules only, never call this full GTFS parity.
  row.sameScheduledAsSTABLE24=JSON.stringify(sameEntries(scheduled))===JSON.stringify(sameEntries(other));
 }
 result.systems.push(row);
 console.log('SYSTEM',filter,
   'shownByScheduledSource',row.observed,'archivedGTFSReference',row.independentReference??'NOT VERIFIED',
   'difference',row.diffComparedWithSource??'UNKNOWN',
   'templates',row.templateCount,
   'activeLines',JSON.stringify(row.observedByLine),
   'source-day-types',JSON.stringify(row.sourceDays));
 if(row.diffComparedWithSource>0)
  console.log('MISSING CONFIRMED HISTORIC SL',filter,row.diffComparedWithSource,
    'individual-lines',JSON.stringify(Object.fromEntries(Object.entries(row).filter(([k])=>k.startsWith('line_')))));
}
const watchTimes=['00:30:00','05:30:00','07:30:00','08:30:00','10:53:22','12:30:00',
                  '16:30:00','19:30:00','23:30:00'];
let checked=0;
for(const day of result.weekdays){
 const daily={day,systems:[]};
 for(const time of watchTimes){
  const e=Date.parse(day+'T'+time+'+01:00')/1000;
  const a=currentActive(current,e,30000),b=weeklyActive(weekly,e,30000);
  for(const f of cols){
   const n=a.filter(t=>matchesRailFilter(t,f)).length;
   const g=b.filter(t=>matchesRailFilter(t,f)).length;
   daily.systems.push({time,filter:f,app:n,source:sourceSeven.has(f)?g:null,
     difference:sourceSeven.has(f)?g-n:null});
   if(sourceSeven.has(f)){
    assert(g>=0&&n>=0);
   }
   checked++;
  }
 }
 result.checks.push(daily);
}
const deficits=result.systems.filter(s=>s.diffComparedWithSource>0);
result.totals={
 allCurrentSimulated:cAll.length,allArchived24:wAll.length,
 totalOther15Current:cAll.filter(v=>v.mode!=='metro').length,
 totalSevenSourceSLCurrent:result.systems.filter(v=>sourceSeven.has(v.filter)).reduce((s,v)=>s+v.independentReference,0),
 totalSevenCurrentSL:result.systems.filter(v=>sourceSeven.has(v.filter)).reduce((s,v)=>s+v.observed,0),
 missingFromArchivedSevenNow:deficits.reduce((s,v)=>s+v.diffComparedWithSource,0),
 fullReferenceSystems:[...sourceSeven],
 otherUnverifiedSystems:cols.filter(f=>!sourceSeven.has(f)),
 checkpoints:checked
};
assert.equal(result.systems.length,15);
await mkdir('_audit_15',{recursive:true});
await writeFile('_audit_15/data-vs-archived-gtfs.json',JSON.stringify(result,null,2));
console.log('TOTALS '+JSON.stringify(result.totals));
console.log('15 OTHER SYSTEM DATA COMPARISON COMPLETED, NO PRODUCTION CHANGE');
