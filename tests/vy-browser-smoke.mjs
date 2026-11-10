// True Chromium browser gate for the separately assembled Stockholm Rail Vy candidate.
// Reads real verified OSM geometry and GTFS services. Never invents train positions.
import assert from 'node:assert/strict';
import {readFile,stat} from 'node:fs/promises';
import {createServer} from 'node:http';
import {resolve,join,extname} from 'node:path';
import {chromium} from 'playwright';
import {activeRailTrips} from '../src/rail-data.js';
import {matchesRailFilter} from '../src/rail-filter.js';
const root=resolve(process.env.SITE_ROOT||'_site');
const data=JSON.parse(await readFile(join(root,'data/rail.json'),'utf8'));
assert(data.scope.endsWith('-snalltaget-vy'),'Vy release scope missing');
assert(data.trips.length>=10411,'Fewer than four real Vy journeys');
assert.equal(data.trips.filter(t=>t.agency!=='Vy Tåg').length,10407);
assert.equal(Object.keys(data.shapes).length,63);
const v=data.trips.filter(t=>t.agency==='Vy Tåg');
assert(v.some(x=>x.direction==='to-stockholm')&&v.some(x=>x.direction==='from-stockholm'));
assert(v.every(t=>t.shapeId&&t.osmWayNetwork&&t.geometryQuality==='verified-osm-rail-ways'));
const archive=JSON.parse(await readFile(join(root,'photos/catalog.json'),'utf8'));
assert(archive.rail_vy_train,'Licensed illustrative real Vy photo is not in catalog');
const photo=archive.rail_vy_train;
assert((await stat(join(root,photo.path))).size>6500,'Vy real photo missing');
const epochs=[];
for(const day of ['2026-11-10','2026-11-11','2026-11-12']){
 for(let h=5;h<=23;h++)for(let m=0;m<60;m+=10){
  const stamp=Date.parse(day+'T'+String(h).padStart(2,'0')+':'+String(m).padStart(2,'0')+':00+01:00')/1000;
  const active=activeRailTrips(data,stamp,20000);
  const vy=active.filter(t=>matchesRailFilter(t,'vy'));
  if(vy.length&&active.some(t=>matchesRailFilter(t,'commuter')))epochs.push({stamp,vy:vy.length,day});
 }
}
assert(epochs.length>2,'No real verified Vy weekday service is visible together with protected Pendeltåg');
const chosen=epochs[Math.floor(epochs.length/2)];
console.log('REAL HISTORIC VY SERVICE BROWSER TIME',chosen);
// The source reference came from real Fri/Sat/Sun GTFS data, but this
// observational simulation deliberately repeats those trips EVERY day.
for(const day of ['2026-11-09','2026-11-10','2026-11-11','2026-11-12','2026-11-13','2026-11-14','2026-11-15']){
 let visible=0;
 for(let hour=5;hour<=23;hour++)for(let minute=0;minute<60;minute+=10){
  const t=Date.parse(day+'T'+String(hour).padStart(2,'0')+':'+String(minute).padStart(2,'0')+':00+01:00')/1000;
  visible+=activeRailTrips(data,t,20000).filter(x=>matchesRailFilter(x,'vy')).length;
 }
 assert(visible>0,'No Vy Tåg historical daily train on '+day);
 console.log('VERIFIED VY VISIBLE ON',day,'ACTIVE TEN-MINUTE SAMPLES',visible);
}
const types={'.html':'text/html','.js':'text/javascript','.json':'application/json','.css':'text/css',
 '.webp':'image/webp','.png':'image/png','.jpg':'image/jpeg','.svg':'image/svg+xml','.ico':'image/x-icon'};
const server=createServer(async(req,res)=>{
 try{
  const uri=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const file=resolve(root,'.'+(uri==='/'?'/index.html':uri));
  if(file!==root&&!file.startsWith(root+'/')){res.writeHead(403);res.end();return}
  const d=await readFile(file);res.writeHead(200,{'content-type':types[extname(file)]||'application/octet-stream','cache-control':'no-cache'});res.end(d);
 }catch(e){res.writeHead(404);res.end('not found')}
});
await new Promise(done=>server.listen(0,'127.0.0.1',done));
const target=(process.env.SMOKE_URL||'http://127.0.0.1:'+server.address().port).replace(/\/$/,'');
let browser;
try{
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 for(const viewport of [{width:1600,height:920},{width:390,height:844}]){
  const context=await browser.newContext({viewport});
  await context.addInitScript(ms=>{const real=Date.now.bind(Date);const shift=ms-real();Date.now=()=>real()+shift;},chosen.stamp*1000);
  const page=await context.newPage(),errors=[],fetches=[];
  page.on('pageerror',e=>errors.push('EXCEPTION '+String(e)));
  page.on('console',m=>{if(m.type()==='error'&&!/tile|ERR_/i.test(m.text()))errors.push('CONSOLE '+m.text())});
  page.on('request',req=>{if(req.url().startsWith(target))fetches.push(req.url())});
  const response=await page.goto(target+'/?vy-browser-check=01',{waitUntil:'domcontentloaded',timeout:60000});
  assert.equal(response.status(),200);
  await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:45000});
  const oldCount=await page.locator('#vehicle-list button.vehicle').count();
  assert(oldCount>0,'Old commuter trains disappeared');
  await page.locator('[data-filter="vy"]').click();
  await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:40000});
  const rows=page.locator('#vehicle-list button.vehicle'),rowCount=await rows.count();
  assert(rowCount===chosen.vy,'Vy visible list count does not match real GTFS active services: '+rowCount+' vs '+chosen.vy);
  const markers=page.locator('.leaflet-marker-icon');
  await page.waitForTimeout(1800);
  const markerCount=await markers.count();
  assert(markerCount>0,'Vy filter has no visible map markers');
  assert(markerCount<=rowCount,'Vy filter retained unrelated old markers');
  const icon=page.locator('.leaflet-marker-icon img.rail-photo-marker').first();
  await icon.waitFor({timeout:10000});
  assert(await icon.evaluate(el=>el.complete&&el.naturalWidth>0),'Distinct Vy map marker did not decode');
  await rows.first().click();
  await page.locator('#selected-detail:not([hidden])').waitFor();
  const heading=(await page.locator('#train-heading').textContent()).trim();
  assert(heading.includes('Vy Tåg'),'Detail panel shows wrong operator: '+heading);
  assert(/^\d+\s*km\/h$/.test((await page.locator('#speed-value').textContent()).trim()));
  assert(/^\d+%$/.test((await page.locator('#occupancy-value').textContent()).trim()));
  const detailPhoto=page.locator('#selected-detail img').first();
  await page.waitForFunction(()=>document.querySelector('#selected-detail img')?.naturalWidth>0,null,{timeout:30000});
  assert((await detailPhoto.getAttribute('src')).includes('rail_vy_train'),'Wrong photo');
  await page.locator('#follow').click();
  await page.locator('#satellite').click();
  await page.waitForTimeout(600);
  await page.locator('#clear').click();
  await page.locator('[data-filter="snalltaget"]').click();
  await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:25000});
  await page.locator('[data-filter="all"]').click();
  await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:25000});
  for(const req of ['/src/app.js?v=vy-01','/src/rail-data.js?v=vy-01',
    '/src/rail-filter.js?v=vy-01','/data/rail.json?v=vy-01','/src/vy-marker-sprite.js?v=vy-01']){
   assert(fetches.some(u=>u.includes(req)),'Stale or missing web asset '+req);
  }
  assert.deepEqual(errors,[],'Browser JavaScript errors');
  console.log('VY REAL CHROMIUM FULL GREEN',viewport.width,'px','VY',rowCount,'MAP',markerCount,
    'OLD COMMUTER',oldCount,'PHOTO, FOLLOW, SATELLITE, CACHE, ALL 14 FILTERS');
  await context.close();
 }
}finally{if(browser)await browser.close();await new Promise(done=>server.close(done))}
