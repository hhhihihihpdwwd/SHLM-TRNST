import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createServer} from 'node:http';
import {resolve,join,extname} from 'node:path';
import {chromium} from 'playwright';
import {activeRailTrips} from '../src/rail-data.js';
import {matchesRailFilter} from '../src/rail-filter.js';
const root=resolve(process.env.SITE_ROOT||'_site');
const dataset=JSON.parse(await readFile(join(root,'data/rail.json'),'utf8'));
assert(dataset.scope.endsWith('-malartag-five'));
assert.equal(dataset.trips.length,10779);
let selected={count:0};
for(let i=5*12;i<23*12;i++){
 const epoch=Date.parse('2026-11-10T00:00:00+01:00')/1000+i*300;
 const m=activeRailTrips(dataset,epoch,20000).filter(t=>matchesRailFilter(t,'malartag'));
 if(m.length>selected.count)selected={count:m.length,epoch};
}
assert(selected.count>8);
console.log('REAL MÄLARTÅG BROWSER AUDIT TIMESTAMP',selected);
const types={'.html':'text/html','.css':'text/css','.js':'text/javascript','.json':'application/json',
 '.webp':'image/webp','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg'};
const server=createServer(async(req,res)=>{
 try{
  const uri=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const p=resolve(root,'.'+(uri==='/'?'/index.html':uri));
  if(p!==root&&!p.startsWith(root+'/')){res.writeHead(403);res.end();return}
  const bytes=await readFile(p);
  res.writeHead(200,{'content-type':types[extname(p)]||'application/octet-stream','cache-control':'no-store'});
  res.end(bytes);
 }catch(e){res.writeHead(404);res.end('not found')}
});
await new Promise(done=>server.listen(0,'127.0.0.1',done));
const base=(process.env.SMOKE_URL||'http://127.0.0.1:'+server.address().port).replace(/\/$/,'');
let browser;
try{
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 for(const viewport of [{width:1530,height:930},{width:390,height:844}]){
  const context=await browser.newContext({viewport});
  await context.addInitScript(epoch=>{
   const real=Date.now.bind(Date),offset=epoch-real();Date.now=()=>real()+offset;
  },selected.epoch*1000);
  const page=await context.newPage(),errors=[],requests=[];
  page.on('pageerror',e=>errors.push(String(e)));
  page.on('request',r=>{if(r.url().startsWith(base))requests.push(r.url())});
  const response=await page.goto(base+'/?malartag-five-check=01',{waitUntil:'domcontentloaded',timeout:60000});
  assert.equal(response.status(),200);
  await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:45000});
  await page.locator('[data-filter="malartag"]').click();
  await page.waitForFunction(n=>document.querySelectorAll('#vehicle-list button.vehicle').length===n,selected.count,{timeout:35000});
  const rows=page.locator('#vehicle-list button.vehicle');
  assert.equal(await rows.count(),selected.count,'Actual displayed Mälartåg list differs from all historical running trains');
  const markers=page.locator('.leaflet-marker-icon img.rail-photo-marker');
  await page.waitForTimeout(1200);
  assert.equal(await markers.count(),selected.count,'Some actual running Mälartåg trains missing from entire map');
  assert(await markers.first().evaluate(x=>x.complete&&x.naturalWidth>0),'Photo-real 3D mini train marker not displayed');
  await rows.first().click();
  await page.locator('#selected-detail:not([hidden])').waitFor({timeout:12000});
  assert(/^\d+\s*km\/h$/.test((await page.locator('#speed-value').textContent()).trim()));
  assert(/^\d+%$/.test((await page.locator('#occupancy-value').textContent()).trim()));
  await page.waitForFunction(()=>document.querySelector('#selected-detail img')?.naturalWidth>0,null,{timeout:16000});
  await page.locator('#follow').click();
  await page.locator('#satellite').click();
  await page.locator('#clear').click();
  for(const filter of ['commuter','sj','vr','snalltaget','vy','tagab','rdc','malartag','all']){
   assert.equal(await page.locator('[data-filter="'+filter+'"]').count(),1,'Prior operator missing '+filter);
  }
  await page.locator('[data-filter="all"]').click();
  await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:30000});
  for(const item of ['/src/app.js?v=malartag-five-01','/src/rail-data.js?v=malartag-five-01',
   '/data/rail.json?v=malartag-five-01']){
   assert(requests.some(url=>url.includes(item)),'Unversioned or missing cache-controlled verified Mälartåg file '+item);
  }
  assert.deepEqual(errors,[],'Javascript errors in actual complete railway map');
  console.log('FULL MÄLARTÅG FIVE-CORRIDOR LIVE MAP CHROMIUM PASS',viewport.width,
   'VISIBLE TRAINS',selected.count,'MAP MARKERS',await markers.count(),'PHOTO, SPEED, FOLLOW, SATELLITE AND ORIGINALS');
  await context.close();
 }
}finally{
 if(browser)await browser.close();
 await new Promise(done=>server.close(done));
}
