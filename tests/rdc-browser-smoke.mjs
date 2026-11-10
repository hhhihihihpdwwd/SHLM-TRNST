// Browser-test the 16-system RDC EuroNight candidate on its actual Leaflet map.
// Select a real historic RDC EuroNight departure on a TUESDAY, not a fabricated live train.
import assert from 'node:assert/strict';
import {readFile,stat} from 'node:fs/promises';
import {createServer} from 'node:http';
import {resolve,join,extname} from 'node:path';
import {chromium} from 'playwright';
import {activeRailTrips} from '../src/rail-data.js';
import {matchesRailFilter} from '../src/rail-filter.js';

const root=resolve(process.env.SITE_ROOT||'_site');
const timetable=JSON.parse(await readFile(join(root,'data/rail.json'),'utf8'));
assert.equal(timetable.scope.endsWith('-snalltaget-vy-tagab-rdc'),true);
assert.equal(timetable.trips.length,10437);
assert.equal(Object.keys(timetable.shapes).length,71);
assert.equal(timetable.trips.filter(t=>t.agency!=='RDC EuroNight').length,10433);
const trips=timetable.trips.filter(t=>t.agency==='RDC EuroNight');
assert.equal(trips.length,4);
assert.deepEqual([...new Set(trips.map(t=>t.direction))].sort(),['from-stockholm','to-stockholm']);
assert.deepEqual([...new Set(trips.map(t=>t.train))].sort(),['344','345']);
assert.equal(trips.filter(t=>t.train==='344').length,2);
assert.equal(trips.filter(t=>t.train==='345').length,2);
for(const t of trips){
 assert(t.shapeId&&t.geometryQuality==='verified-osm-rail-ways'&&t.osmWayNetwork===true);
 assert(timetable.shapes[t.shapeId]?.length>500);
}
const catalog=JSON.parse(await readFile(join(root,'photos/catalog.json'),'utf8'));
assert(catalog.rail_rdc_euronight);
assert.equal(catalog.rail_rdc_euronight.license,'CC BY 4.0');
assert((await stat(join(root,catalog.rail_rdc_euronight.path))).size>6500);

let epochs=[];
for(const date of ['2026-11-10','2026-11-11','2026-11-12']){
 let total=0;
 for(let hour=4;hour<24;hour++)for(let minute=0;minute<60;minute+=10){
  const t=Date.parse(date+'T'+String(hour).padStart(2,'0')+':'+String(minute).padStart(2,'0')+':00+01:00')/1000;
  const active=activeRailTrips(timetable,t,20000);
  const rdc=active.filter(x=>matchesRailFilter(x,'rdc'));
  if(rdc.length&&active.some(x=>matchesRailFilter(x,'commuter')))epochs.push({date,t,count:rdc.length});
  total+=rdc.length;
 }
 assert(total>0,'No RDC EuroNight trains on '+date+' in the daily historical simulation');
 console.log('AUTHENTIC RDC EURONIGHT VISIBLE EVERY DAY',date,'TEN-MINUTE POSITION SAMPLES',total);
}
const selected=epochs[Math.floor(epochs.length/2)];
assert(selected&&selected.count>0);
console.log('CHROMIUM TESTS ACTUAL RDC EURONIGHT TRAINS AT',selected);

const types={'.html':'text/html','.css':'text/css','.js':'text/javascript','.json':'application/json','.webp':'image/webp','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg'};
const server=createServer(async(req,res)=>{
 try{
  const uri=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const f=resolve(root,'.'+(uri==='/'?'/index.html':uri));
  if(f!==root&&!f.startsWith(root+'/')){res.writeHead(403);res.end();return}
  const bytes=await readFile(f);
  res.writeHead(200,{'content-type':types[extname(f)]||'application/octet-stream','cache-control':'no-cache'});
  res.end(bytes);
 }catch(e){res.writeHead(404);res.end('not found')}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const base=(process.env.SMOKE_URL||'http://127.0.0.1:'+server.address().port).replace(/\/$/,'');
let browser;
try{
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 for(const viewport of [{width:1600,height:920},{width:390,height:844}]){
  const context=await browser.newContext({viewport});
  await context.addInitScript(ms=>{const now=Date.now.bind(Date);const diff=ms-now();Date.now=()=>now()+diff;},selected.t*1000);
  const page=await context.newPage(),errors=[],fetched=[];
  page.on('pageerror',e=>errors.push(String(e)));
  page.on('console',m=>{if(m.type()==='error'&&!/tile|ERR_/i.test(m.text()))errors.push(m.text())});
  page.on('request',req=>{if(req.url().startsWith(base))fetched.push(req.url())});
  const response=await page.goto(base+'/?rdc-smoke-01',{waitUntil:'domcontentloaded',timeout:60000});
  assert.equal(response.status(),200);
  await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:45000});
  const original=await page.locator('#vehicle-list button.vehicle').count();
  assert(original>0,'Original commuter filter empty');
  await page.locator('[data-filter="rdc"]').click();
  await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:40000});
  const rows=page.locator('#vehicle-list button.vehicle');
  assert.equal(await rows.count(),selected.count,'Visible RDC EuroNight list differs from genuine simulated GTFS active trips');
  await page.waitForTimeout(1400);
  const icons=page.locator('.leaflet-marker-icon img.rail-photo-marker');
  assert(await icons.count()>0,'No RDC EuroNight train-front marker visible');
  assert(await icons.first().evaluate(n=>n.complete&&n.naturalWidth>0),'RDC EuroNight distinctive marker not decoded');
  await rows.first().click();
  await page.locator('#selected-detail:not([hidden])').waitFor();
  assert((await page.locator('#train-heading').textContent()).includes('RDC EuroNight'));
  await page.waitForFunction(()=>document.querySelector('#selected-detail img')?.naturalWidth>0,null,{timeout:20000});
  assert((await page.locator('#selected-detail img').first().getAttribute('src')).includes('rail_rdc_euronight'));
  assert(/^\d+\s*km\/h$/.test((await page.locator('#speed-value').textContent()).trim()));
  assert(/^\d+%$/.test((await page.locator('#occupancy-value').textContent()).trim()));
  await page.locator('#follow').click();
  await page.locator('#satellite').click();
  await page.locator('#clear').click();
  await page.locator('[data-filter="commuter"]').click();
  await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:30000});
  await page.locator('[data-filter="all"]').click();
  await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:30000});
  for(const name of ['/src/app.js?v=rdc-01','/src/rail-data.js?v=rdc-01',
    '/src/rail-filter.js?v=rdc-01','/data/rail.json?v=rdc-01',
    '/src/rdc-marker-sprite.js?v=rdc-01']){
   assert(fetched.some(x=>x.includes(name)),'Stale/missing cache-versioned asset '+name);
  }
  assert.deepEqual(errors,[],'Browser JavaScript errors');
  console.log('RDC EURONIGHT 16-SYSTEM CHROMIUM PASS',viewport.width,'SCREEN','ORIGINAL',original,'RDC EURONIGHT',selected.count,'MARKERS',await icons.count(),'REAL PHOTO, FOLLOW, SATELLITE, DAILY SIMULATION');
  await context.close();
 }
}finally{
 if(browser)await browser.close();
 await new Promise(resolve=>server.close(resolve));
}
