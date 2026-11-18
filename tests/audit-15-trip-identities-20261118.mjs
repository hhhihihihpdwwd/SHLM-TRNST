// Additional independent timetable identity audit, not just equal train counts.
// Compares actual historical train departure/end locations/times and route stop
// patterns against complete archived seven-day GTFS for seven SL families.
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {activeRailTrips as app} from '../_stable29/website/src/rail-data.js';
import {activeRailTrips as historic} from '../_stable24/website/src/rail-data.js';
import {matchesRailFilter} from '../_stable29/website/src/rail-filter.js';

const a=JSON.parse(await readFile('_stable29/website/data/rail.json'));
const b=JSON.parse(await readFile('_stable24/website/data/rail.json'));
const filters=['commuter','tram','nockeby','lidingo','city7','roslags','saltsjo'];
const scenarios=['2026-11-18T10:53:22+01:00','2026-11-18T07:30:00+01:00',
 '2026-11-18T16:30:00+01:00','2026-11-21T10:53:22+01:00',
 '2026-11-22T19:30:00+01:00'];
const fmt=new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Stockholm',hour:'2-digit',minute:'2-digit',hourCycle:'h23'});
const norm=str=>String(str||'').normalize('NFKC').trim().toLowerCase();
const pattern=t=>[
 String(t.line),fmt.format(new Date(t.start*1000)),
 norm(t.stops[0][2]),norm(t.stops.at(-1)[2]),
 fmt.format(new Date(t.end*1000)),
 t.stops.length,
].join('|');
function diff(lhs,rhs){
 const counts=new Map();
 for(const t of rhs){
  const key=pattern(t);counts.set(key,(counts.get(key)||0)+1);
 }
 const missing=[];
 for(const t of lhs){
  const key=pattern(t),n=counts.get(key)||0;
  if(n>0)counts.set(key,n-1);
  else missing.push({line:t.line,start:fmt.format(new Date(t.start*1000)),
      destination:t.stops.at(-1)[2],origin:t.stops[0][2],end:fmt.format(new Date(t.end*1000)),numStops:t.stops.length});
 }
 return missing;
}
const output=[];
for(const when of scenarios){
 const epoch=Date.parse(when)/1000;
 const actual=app(a,epoch,30000),reference=historic(b,epoch,30000);
 for(const f of filters){
  const A=actual.filter(x=>matchesRailFilter(x,f)),B=reference.filter(x=>matchesRailFilter(x,f));
  const missing=diff(B,A),extra=diff(A,B);
  const row={when,filter:f,app:A.length,gtfs:B.length,
    missingActualGTFSPatterns:missing.length,extraAppPatterns:extra.length,
    examplesMissing:missing.slice(0,4),examplesExtra:extra.slice(0,4)};
  output.push(row);
  console.log('TRIP PATTERN IDENTITY',when,f,'app',A.length,'gtfs',B.length,
    'missingVerifiedGTFS',missing.length,'extraInstead',extra.length,
    'firstMissing',JSON.stringify(missing.slice(0,2)));
 }
}
await mkdir('_audit_15',{recursive:true});
await writeFile('_audit_15/trip-identity-parity.json',JSON.stringify(output,null,2));
console.log('ALL 7 SL HISTORICAL SOURCE TRIP-IDENTITY AUDITS COMPLETE');
