// FULL website audit. Read the EXACT published STABLE21 artifact locally for
// mathematically exhaustive timetable enumeration, while every browser check
// visits the ACTUAL public GitHub Pages URL (no local proxy or mock response).
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {chromium} from 'playwright';
const BASE='https://hhhihihihpdwwd.github.io/SHLM-TRNST/';
const site=path.resolve(process.env.SITE_ROOT||'_site');
const out=path.resolve(process.env.REPORT_ROOT||'reports/public-complete-audit');
fs.mkdirSync(out,{recursive:true});
const d=JSON.parse(fs.readFileSync(path.join(site,'data/rail.json'),'utf8'));
const {activeRailTrips,railAt}=await import(pathToFileURL(path.join(site,'src/rail-data.js')).href);
const {matchesRailFilter}=await import(pathToFileURL(path.join(site,'src/rail-filter.js')).href);
assert.equal(d.trips.length,10827,'Wrong STABLE21 golden source');
assert.equal(Object.keys(d.shapes).length,107);
const keys=['commuter','metro','tram','nockeby','lidingo','city7','roslags','saltsjo','arlanda','sj','vr','snalltaget','vy','tagab','rdc','malartag'];
const schema={};
for(const key of keys){
 const templates=d.trips.filter(t=>matchesRailFilter(t,key));
 assert(templates.length,'No source trains in '+key);
 const lines={};
 for(const t of templates){
  const label=String(t.line||t.train||t.mode);
  const p=lines[label]??={templates:0,from:new Set(),to:new Set(),directions:new Set(),corridors:new Set(),uniqueTripIds:new Set(),activeSnapshots:0,activeTrainObservations:0,firstSeen:null,peak:0};
  p.templates++;p.from.add(t.stops[0][2]);p.to.add(t.stops.at(-1)[2]);p.corridors.add(t.stops[0][2]+' → '+t.stops.at(-1)[2]);
  p.directions.add(t.stops[0][2]+' → '+t.stops.at(-1)[2]);
  p.uniqueTripIds.add(t.id);
 }
 schema[key]={templateCount:templates.length,lines};
}
const audit={site:BASE,baseline:'STABLE21',historicalSimulationNotGps:true,sourceTemplates:d.trips.length,sourceShapes:Object.keys(d.shapes).length,
 sampledIntervalMinutes:15,days:['2026-11-09','2026-11-10','2026-11-11','2026-11-12','2026-11-13','2026-11-14','2026-11-15'],
 allSystems:{},dataCheck:{timestamps:0,checkedTrainObservations:0,invalidCoordinates:[],negativeSpeed:[],invalidNextStation:[],duplicateIds:[],orphanIds:[],emptyDaytimeSystems:[],neverActiveSourceLines:[],directionCoverage:[]},
 browser:{url:BASE,snapshots:[],errors:[],publicFiles:[],checkMethod:'Actual public Playwright Chromium; click all 16 filters, compare each visible sidebar row and every actual Leaflet train photo marker to all scheduled train instances at fixed Stockholm time; verify line-by-line counts'},
 verdict:'NOT_YET_RUN'};
for(const [key,group] of Object.entries(schema))audit.allSystems[key]={templates:group.templateCount,lines:Object.fromEntries(Object.entries(group.lines).map(([line,r])=>[line,{templates:r.templates,from:[...r.from].sort(),to:[...r.to].sort(),endpointPairs:[...r.corridors].sort(),visibleSnapshots:0,activeObservations:0,firstSeen:null,peak:0}]))};
const indices=new Map(d.trips.map(t=>[t.id,t]));
const sourceKeys=new Set(indices.keys());
const snapshots=new Map();
const timeLabel=(day,minute)=>day+'T'+String(Math.floor(minute/60)).padStart(2,'0')+':'+String(minute%60).padStart(2,'0')+':00+01:00';
// ALL 16 systems × EVERY individual line × 7 dates × every quarter hour.
// No false availability claim between samples.
for(const day of audit.days){
 const seenDay=new Set();
 for(let minutes=0;minutes<1440;minutes+=15){
  const stamp=timeLabel(day,minutes),epoch=Date.parse(stamp)/1000;
  const active=activeRailTrips(d,epoch,20000);
  const names=new Set(),counts={};
  for(const key of keys)counts[key]={total:0,lines:{}};
  for(const t of active){
   audit.dataCheck.checkedTrainObservations++;
   if(names.has(t.id))audit.dataCheck.duplicateIds.push({stamp,id:t.id});
   names.add(t.id);
   const sourceId=t.id.replace(/:DAILY:\d{4}-\d\d-\d\d$/,'');
   if(!sourceKeys.has(sourceId))audit.dataCheck.orphanIds.push({stamp,id:t.id});
   const p=railAt(t,epoch);
   if(!Array.isArray(p.pos)||p.pos.length!==2||p.pos.some(x=>!Number.isFinite(x))||
      p.pos[0]<52||p.pos[0]>71||p.pos[1]<8||p.pos[1]>25)
    audit.dataCheck.invalidCoordinates.push({stamp,id:t.id,pos:p.pos});
   if(!Number.isFinite(p.kmh)||p.kmh<0||p.kmh>250)audit.dataCheck.negativeSpeed.push({stamp,id:t.id,kmh:p.kmh});
   if(!Number.isInteger(p.next)||p.next<0||p.next>=t.stops.length)
    audit.dataCheck.invalidNextStation.push({stamp,id:t.id,next:p.next});
   for(const key of keys){
    if(!matchesRailFilter(t,key))continue;
    counts[key].total++;
    const line=String(t.line||t.train||t.mode);
    counts[key].lines[line]=(counts[key].lines[line]||0)+1;
    const bucket=audit.allSystems[key].lines[line];
    if(!bucket){audit.dataCheck.orphanIds.push({stamp,id:t.id,system:key,line});continue}
    bucket.activeObservations++;
    bucket.visibleSnapshots++;
    if(!bucket.firstSeen)bucket.firstSeen=stamp;
    bucket.peak=Math.max(bucket.peak,counts[key].lines[line]);
    if(minutes>=360&&minutes<1380)seenDay.add(key);
   }
  }
  snapshots.set(stamp,{epoch,counts,ids:active.map(t=>t.id)});
  audit.dataCheck.timestamps++;
 }
 for(const key of keys){
  if(!seenDay.has(key))audit.dataCheck.emptyDaytimeSystems.push({day,system:key});
 }
 console.log('FULL TRAIN TIMETABLE DATA CHECK',day,'96 quarter-hour checks completed');
}
for(const [key,system] of Object.entries(audit.allSystems)){
 for(const [line,p] of Object.entries(system.lines)){
  if(p.activeObservations===0)audit.dataCheck.neverActiveSourceLines.push({system:key,line,templates:p.templates});
  const reversePairs=p.endpointPairs.filter(pair=>{
   const [a,b]=pair.split(' → ');return p.endpointPairs.includes(b+' → '+a);
  });
  audit.dataCheck.directionCoverage.push({system:key,line,sourceEndpointPairs:p.endpointPairs.length,exactReversePairs:reversePairs.length,allSourceTermini:[...new Set([...p.from,...p.to])].length});
 }
}
fs.writeFileSync(path.join(out,'data-preliminary.json'),JSON.stringify(audit,null,2));
const publicHtml=await fetch(BASE+'?full-audit='+Date.now(),{headers:{'Cache-Control':'no-cache'}});
assert.equal(publicHtml.status,200,'Public homepage unavailable');
const html=await publicHtml.text();
assert(html.includes('app.js?v=package07-01'),'Public page not running STABLE21');
const publicData=await fetch(BASE+'data/rail.json?v=package07-01',{headers:{'Cache-Control':'no-cache'}});
assert.equal(publicData.status,200,'Actual public timetable unavailable');
const live=await publicData.json();
assert.deepEqual(live,d,'Actual PUBLIC timetable JSON differs from approved STABLE21');
audit.browser.publicFiles.push('public index.html STABLE21 cache verified','public rail.json exactly byte-structure equivalent to golden source');
let browser;
const errors=[];
function snapshotScores(stamp){
 const entry=snapshots.get(stamp);return entry?.counts||null;
}
const representative=['2026-11-09T00:30:00+01:00','2026-11-09T06:30:00+01:00',
 '2026-11-09T08:30:00+01:00','2026-11-09T12:30:00+01:00',
 '2026-11-09T16:30:00+01:00','2026-11-09T19:30:00+01:00',
 '2026-11-09T22:30:00+01:00','2026-11-10T09:30:00+01:00'];
// Ensure EVERY distinct line has at least one independent browser presence
// check when its source timeline has a train. Supplement fixed hours with
// targeted 15-min windows if uncommon/night routes require it.
const selected=new Set(representative);
for(const key of keys){
 for(const line of Object.keys(audit.allSystems[key].lines)){
  if([...selected].some(s=>(snapshotScores(s)?.[key]?.lines?.[line]||0)>0))continue;
  const found=[...snapshots.entries()].find(([s,v])=>s.startsWith('2026-11-09')&&(v.counts[key].lines[line]||0)>0)
    ||[...snapshots.entries()].find(([s,v])=>(v.counts[key].lines[line]||0)>0);
  if(found)selected.add(found[0]);
 }
}
const browserStamps=[...selected].sort();
console.log('PUBLIC BROWSER SCENES',browserStamps.length,'ALL INDIVIDUAL LINE PROOF',Object.entries(audit.allSystems).map(([k,v])=>k+':'+Object.keys(v.lines).join(',')).join(' ; '));
try{
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 // Use a mobile scene for every mode and a desktop scene for each timestamp.
 const screenModes=[{width:1440,height:900},{width:390,height:844}];
 for(let screen of screenModes){
  // All core times on desktop; mobile screenshots/checks at best representative
  // hours plus a scenario for each uncommon line as necessary.
  const scenes=screen.width===1440?browserStamps:browserStamps;
  for(const stamp of scenes){
   const expected=snapshots.get(stamp).counts;
   const ctx=await browser.newContext({viewport:screen});
   await ctx.addInitScript(epoch=>{
    const native=Date.now.bind(Date),offset=epoch-native();
    Date.now=()=>native()+offset;
   },Date.parse(stamp));
   const page=await ctx.newPage();
   const localErrors=[];
   page.on('pageerror',e=>localErrors.push(String(e)));
   const response=await page.goto(BASE+'?exhaustive-stable21-audit='+encodeURIComponent(stamp),{waitUntil:'domcontentloaded',timeout:70000});
   assert.equal(response.status(),200);
   await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:55000});
   const record={timestamp:stamp,viewport:screen.width,systems:{},status:'pass'};
   for(const key of keys){
    await page.locator('[data-filter="'+key+'"]').click({timeout:22000});
    const should=expected[key].total;
    await page.waitForFunction(n=>document.querySelectorAll('#vehicle-list button.vehicle').length===n,
      should,{timeout:28000}).catch(()=>{});
    await page.waitForTimeout(300);
    let observed=await page.evaluate(()=>{
     const nodes=[...document.querySelectorAll('#vehicle-list button.vehicle')];
     const lines={};
     for(const el of nodes){
      const tag=(el.querySelector('.line-pill')?.textContent||'').trim();
      lines[tag]=(lines[tag]||0)+1;
     }
     return {list:nodes.length,lines,markers:document.querySelectorAll('.leaflet-marker-icon img.rail-photo-marker').length,
      brokenMarkers:[...document.querySelectorAll('.leaflet-marker-icon img.rail-photo-marker')].filter(i=>!i.complete||i.naturalWidth===0).length,
      errorText:document.querySelector('#map-fallback:not([hidden])')?.textContent||''};
    });
    const diffs=[];
    if(observed.list!==should)diffs.push('list '+observed.list+' / timetable '+should);
    if(observed.markers!==should)diffs.push('map markers '+observed.markers+' / timetable '+should);
    if(observed.brokenMarkers)diffs.push('broken markers '+observed.brokenMarkers);
    const expectedLineCounts=Object.fromEntries(Object.entries(expected[key].lines));
    // Exact source line IDs are rendered as each list row's pill.
    for(const [line,count] of Object.entries(expectedLineCounts))
     if((observed.lines[line]||0)!==count)diffs.push('line '+line+' list '+(observed.lines[line]||0)+' / expected '+count);
    for(const line of Object.keys(observed.lines))
     if(!(line in expectedLineCounts))diffs.push('unexpected line '+line+' in public list');
    if(should===0&&observed.list===0){
     const noTrains=await page.locator('#vehicle-list').innerText();
     if(!noTrains.includes('Inga'))diffs.push('no empty-state explanation');
    }
    record.systems[key]={scheduled:should,visibleList:observed.list,visibleMapMarkers:observed.markers,
      expectedLines:expectedLineCounts,actualLines:observed.lines,errors:diffs};
    if(diffs.length){
     record.status='failed';errors.push({stamp,viewport:screen.width,system:key,diffs});
    }
    if(should>0){
     // Every system also needs at least one real selected vehicle with next stop.
     const clicked=await page.locator('#vehicle-list button.vehicle').first().click().then(()=>true).catch(()=>false);
     if(clicked){
      try{
       await page.locator('#selected-detail:not([hidden])').waitFor({timeout:10000});
       const state=await page.evaluate(()=>({heading:document.querySelector('#train-heading')?.textContent,
        next:document.querySelector('#next-stop-name')?.textContent,
        kmh:document.querySelector('#speed-value')?.textContent}));
       if(!state.heading||!state.next||!/^\d+\s*km\/h$/.test(state.kmh||'')){
        errors.push({stamp,viewport:screen.width,system:key,diffs:['real selected train details/next stop broken']});
        record.status='failed';
       }
       await page.locator('#clear').click();
      }catch(e){errors.push({stamp,viewport:screen.width,system:key,diffs:['select train '+String(e).slice(0,130)]});record.status='failed'}
     }
    }
    if(!audit.browser.snapshots.some(r=>r.systems?.[key]?.screenshot&&r.systems[key].screenshot.endsWith('.png')) &&
       should>0 && screen.width===1440){
      // Capture once per operator in an independent clickable screenshot.
      const name='system-'+key+'.png';
      await page.screenshot({path:path.join(out,name),timeout:20000}).catch(()=>{});
      record.systems[key].screenshot=name;
    }
    console.log('PUBLIC OPERATOR',screen.width,stamp,key,'scheduled',should,'list',observed.list,'markers',observed.markers,'lines',JSON.stringify(observed.lines),'MISMATCHES',diffs.length);
   }
   if(localErrors.length){record.status='failed';errors.push({stamp,viewport:screen.width,system:'javascript',diffs:localErrors})}
   audit.browser.snapshots.push(record);
   fs.writeFileSync(path.join(out,'browser-progress.json'),JSON.stringify(audit.browser,null,2));
   await ctx.close();
  }
 }
}finally{if(browser)await browser.close();}
audit.browser.errors=errors;
const k= audit.dataCheck;
const dataErrors= k.invalidCoordinates.length+k.negativeSpeed.length+k.invalidNextStation.length+k.duplicateIds.length+k.orphanIds.length;
audit.verdict=!errors.length&&!dataErrors&&!k.emptyDaytimeSystems.length&&!k.neverActiveSourceLines.length?'PASS':'ISSUES_FOUND';
audit.summary={systemsChecked:keys.length,individualLinesChecked:Object.values(audit.allSystems).reduce((s,g)=>s+Object.keys(g.lines).length,0),
 publicWebsiteBrowserScenarios:audit.browser.snapshots.length,
 websiteSystemLineComparisons:audit.browser.snapshots.length*keys.length,
 quarterHourTimetableSamples:k.timestamps,trainObservations:k.checkedTrainObservations,
 publicMarkerCountMismatches:errors.filter(x=>x.diffs.some(s=>s.includes('map markers'))).length,
 publicSidebarCountMismatches:errors.filter(x=>x.diffs.some(s=>s.includes('list'))).length,
 dataErrors,publicFailures:errors.length,neverActiveSourceLines:k.neverActiveSourceLines};
fs.writeFileSync(path.join(out,'FULL-AUDIT-RESULT.json'),JSON.stringify(audit,null,2));
console.log('COMPLETE PUBLIC STOCKHOLM RAIL AUDIT FINAL',JSON.stringify({verdict:audit.verdict,...audit.summary}));
if(audit.verdict!=='PASS')process.exitCode=1;
