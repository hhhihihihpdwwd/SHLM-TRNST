// Full SJ South/West/North/Night integrated train test on actual Leaflet map.
// All added services are authentic Nov 2026 SJ trains, simulated DAILY.
// No fake routes, no unrelated markers, no UI redesign.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createServer} from 'node:http';
import {resolve,join,extname} from 'node:path';
import {chromium} from 'playwright';
import {activeRailTrips} from '../src/rail-data.js';
import {matchesRailFilter} from '../src/rail-filter.js';

const root=resolve(process.env.SITE_ROOT||'_site');
const data=JSON.parse(await readFile(join(root,'data/rail.json'),'utf8'));
assert(data.scope.endsWith('-vy-tagab-rdc-sj-complete'));
assert.equal(data.trips.length,10611);
assert.equal(data.sjCompleteAdded,174);
const additions=data.trips.slice(10437);
assert.equal(additions.length,174);
assert(additions.every(t=>t.agency==='SJ'&&t.geometryQuality==='verified-osm-rail-ways'&&t.osmWayNetwork===true));
for(const [label,pattern] of [
 ['Göteborg',/göteborg/i],['Malmö',/malmö/i],['Oslo',/oslo/i],
 ['Falun',/falun/i],['Duved',/duved/i],['Sundsvall',/sundsvall/i],
 ['Umeå',/umeå/i],['Luleå',/luleå/i]
]){
 assert(additions.some(t=>pattern.test(t.destination)||pattern.test(t.stops[0][2])),
  'Missing actual SJ '+label+' corridor');
}
assert(additions.some(x=>x.serviceCategory==='night'),'No historical northern night trains added');
assert(data.trips.slice(0,10437).every(t=>t.agency!=='SJ'||t.id));
const allFilters=['commuter','metro','tram','nockeby','lidingo','city7','roslags','saltsjo',
 'arlanda','sj','vr','snalltaget','vy','tagab','rdc','malartag','all'];

let choices=[];
for(const day of ['2026-11-10','2026-11-11','2026-11-12']){
 let found=0;
 for(let hour=6;hour<23;hour++)for(let minute=0;minute<60;minute+=20){
  const stamp=Date.parse(day+'T'+String(hour).padStart(2,'0')+':'+String(minute).padStart(2,'0')+':00+01:00')/1000;
  const live=activeRailTrips(data,stamp,20000);
  const sj=live.filter(t=>matchesRailFilter(t,'sj'));
  const added=sj.filter(t=>t.id.startsWith('SJ-FULL-'));
  if(sj.length&&added.length&&live.some(x=>matchesRailFilter(x,'commuter'))){
   choices.push({stamp,day,sj:sj.length,added:added.length});found++;
  }
 }
 assert(found>0,'No NEW SJ historical trains active on '+day);
 console.log('SJ COMPLETE DAILY HISTORICAL RAIL VISIBLE',day,found,'VERIFIED TIMES');
}
const selected=choices[Math.floor(choices.length/2)];
console.log('SJ FULL NETWORK CHROMIUM TIMESTAMP',selected);

const types={'.html':'text/html','.css':'text/css','.js':'text/javascript','.json':'application/json',
 '.webp':'image/webp','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg'};
const server=createServer(async(req,res)=>{
 try{
  const uri=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const file=resolve(root,'.'+(uri==='/'?'/index.html':uri));
  if(file!==root&&!file.startsWith(root+'/')){res.writeHead(403);res.end();return}
  const bytes=await readFile(file);
  res.writeHead(200,{'content-type':types[extname(file)]||'application/octet-stream','cache-control':'no-cache'});
  res.end(bytes);
 }catch(e){res.writeHead(404);res.end('not found')}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const target=(process.env.SMOKE_URL||'http://127.0.0.1:'+server.address().port).replace(/\/$/,'');
let browser;
try{
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 for(const viewport of [{width:1550,height:940},{width:390,height:844}]){
  const context=await browser.newContext({viewport});
  await context.addInitScript(epoch=>{
   const now=Date.now.bind(Date),diff=epoch-now();Date.now=()=>now()+diff;
  },selected.stamp*1000);
  const page=await context.newPage(),errors=[],requests=[];
  page.on('pageerror',e=>errors.push(String(e)));
  page.on('console',m=>{if(m.type()==='error'&&!/tile|ERR_/i.test(m.text()))errors.push(m.text())});
  page.on('request',r=>{if(r.url().startsWith(target))requests.push(r.url())});
  const response=await page.goto(target+'/?sj-complete-check=01',{waitUntil:'domcontentloaded',timeout:60000});
  assert.equal(response.status(),200);
  await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:45000});
  const before=await page.locator('#vehicle-list button.vehicle').count();
  assert(before>0,'Original 16-system commuter view failed');
  await page.locator('[data-filter="sj"]').click();
  await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:40000});
  const rows=page.locator('#vehicle-list button.vehicle');
  assert.equal(await rows.count(),selected.sj,'Live SJ count differs from authenticated historical dataset');
  const markers=page.locator('.leaflet-marker-icon img.rail-photo-marker');
  await page.waitForTimeout(900);
  assert(await markers.count()>0,'SJ rail marker missing on map');
  assert(await markers.first().evaluate(n=>n.complete&&n.naturalWidth>0),'SJ image failed to decode');
  await rows.first().click();
  await page.locator('#selected-detail:not([hidden])').waitFor();
  assert(/^\d+\s*km\/h$/.test((await page.locator('#speed-value').textContent()).trim()));
  assert(/^\d+%$/.test((await page.locator('#occupancy-value').textContent()).trim()));
  await page.locator('#follow').click();
  await page.locator('#satellite').click();
  await page.locator('#clear').click();
  for(const key of ['commuter','tagab','vy','rdc','sj','all']){
   await page.locator('[data-filter="'+key+'"]').click();
  }
  for(const f of allFilters){
   assert(await page.locator('[data-filter="'+f+'"]').count()===1,'Previous system button missing '+f);
  }
  for(const path of ['/src/app.js?v=sj-complete-01','/src/rail-data.js?v=sj-complete-01','/data/rail.json?v=sj-complete-01']){
   assert(requests.some(x=>x.includes(path)),'Unversioned or stale SJ asset '+path);
  }
  assert.deepEqual(errors,[],'Browser runtime errors');
  console.log('SJ COMPLETE 16-SYSTEM MAP CHROMIUM GREEN',viewport.width,'SJ',selected.sj,
    'NEW SJ ACTIVE',selected.added,'MARKERS',await markers.count(),'ORIGINAL COMMUTER',before);
  await context.close();
 }
}finally{
 if(browser)await browser.close();
 await new Promise(resolve=>server.close(resolve));
}
