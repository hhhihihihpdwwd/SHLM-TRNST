// Verify actual 16-system interactive map with the eight non-overlapping
// German/Danish Snälltåget source-authenticated rail components in Chromium.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createServer} from 'node:http';
import {resolve,join,extname} from 'node:path';
import {chromium} from 'playwright';
import {activeRailTrips} from '../src/rail-data.js';
import {matchesRailFilter} from '../src/rail-filter.js';

const root=resolve(process.env.SITE_ROOT||'_site');
const d=JSON.parse(await readFile(join(root,'data/rail.json'),'utf8'));
assert.equal(d.trips.length,10787);
assert(d.scope.endsWith('-intl-four'));
let best={epoch:0,added:0,count:0};
for(let min=0;min<48*60;min+=10){
 const epoch=Date.parse('2026-11-10T00:00:00+01:00')/1000+min*60;
 const trains=activeRailTrips(d,epoch,20000).filter(t=>matchesRailFilter(t,'snalltaget'));
 const added=trains.filter(x=>x.snallCrossborderVerified).length;
 if(added>best.added||(added===best.added&&trains.length>best.count))
  best={epoch,added,count:trains.length};
}
assert(best.added>0&&best.count>=best.added);
const mime={'.html':'text/html','.css':'text/css','.js':'text/javascript','.json':'application/json',
 '.webp':'image/webp','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg'};
const server=createServer(async(req,res)=>{
 try{
  const uri=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const file=resolve(root,'.'+(uri==='/'?'/index.html':uri));
  if(file!==root&&!file.startsWith(root+'/')){res.writeHead(403);res.end();return}
  const bytes=await readFile(file);
  res.writeHead(200,{'content-type':mime[extname(file)]||'application/octet-stream','cache-control':'no-store'});
  res.end(bytes);
 }catch(e){res.writeHead(404);res.end('not found')}
});
await new Promise(ok=>server.listen(0,'127.0.0.1',ok));
const host=(process.env.SMOKE_URL||'http://127.0.0.1:'+server.address().port).replace(/\/$/,'');
let browser;
try{
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 for(const viewport of [{width:1530,height:930},{width:390,height:844}]){
  const context=await browser.newContext({viewport});
  await context.addInitScript(epoch=>{
   const original=Date.now.bind(Date),shift=epoch-original();Date.now=()=>original()+shift;
  },best.epoch*1000);
  const page=await context.newPage(),errors=[],requests=[];
  page.on('pageerror',e=>errors.push(String(e)));
  page.on('request',r=>{if(r.url().startsWith(host))requests.push(r.url())});
  const response=await page.goto(host+'/?intl-four-release-check=01',{waitUntil:'domcontentloaded',timeout:60000});
  assert.equal(response.status(),200);
  await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:45000});
  await page.locator('[data-filter="snalltaget"]').click();
  await page.waitForFunction(n=>document.querySelectorAll('#vehicle-list button.vehicle').length===n,best.count,{timeout:35000});
  assert.equal(await page.locator('#vehicle-list button.vehicle').count(),best.count,
   'Real Snälltåget side panel missing a source-backed international train');
  const markers=page.locator('.leaflet-marker-icon img.rail-photo-marker');
  await page.waitForTimeout(1400);
  assert.equal(await markers.count(),best.count,
   'Real map omits one historic foreign train photograph marker');
  assert(await markers.first().evaluate(i=>i.complete&&i.naturalWidth>0),
   'Authentic photo-real style train front marker failed to decode');
  const first=page.locator('#vehicle-list button.vehicle').first();
  await first.click();
  await page.locator('#selected-detail:not([hidden])').waitFor({timeout:12000});
  assert(/^\d+\s*km\/h$/.test((await page.locator('#speed-value').textContent()).trim()));
  assert(/^\d+%$/.test((await page.locator('#occupancy-value').textContent()).trim()));
  await page.waitForFunction(()=>document.querySelector('#selected-detail img')?.naturalWidth>0,null,{timeout:16000});
  await page.locator('#follow').click();
  await page.locator('#satellite').click();
  await page.locator('#clear').click();
  for(const key of ['commuter','metro','arlanda','sj','malartag','vr','snalltaget','vy','tagab','rdc','all']){
   assert.equal(await page.locator('[data-filter="'+key+'"]').count(),1,'Previous operator filter disappeared: '+key);
  }
  await page.locator('[data-filter="all"]').click();
  await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:30000});
  for(const file of ['/src/app.js?v=intl-four-01','/src/rail-data.js?v=intl-four-01',
   '/data/rail.json?v=intl-four-01']){
   assert(requests.some(url=>url.includes(file)),'Stale or missing versioned international file '+file);
  }
  assert.deepEqual(errors,[],'Real public international map Javascript errors');
  console.log('FULL INTERNATIONAL FOUR OPERATOR CHROMIUM GREEN',viewport.width,
   'ALL SNÄLLTÅGET AT TEST INSTANT',best.count,
   'NEW EUROPEAN SOURCE ROUTES',best.added,
   'PHOTO FRONT TRAIN ICONS',await markers.count(),'FOLLOW SATELLITE AND ORIGINAL OPERATORS PRESERVED');
  await context.close();
 }
}finally{
 if(browser)await browser.close();
 await new Promise(done=>server.close(done));
}
