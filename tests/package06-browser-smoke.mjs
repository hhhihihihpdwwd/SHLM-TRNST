import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createServer} from 'node:http';
import {resolve,join,extname} from 'node:path';
import {chromium} from 'playwright';
import {pathToFileURL} from 'node:url';
const root=resolve(process.env.SITE_ROOT||'_site');
const {activeRailTrips}=await import(pathToFileURL(join(root,'src/rail-data.js')).href);
const d=JSON.parse(await readFile(join(root,'data/rail.json'),'utf8'));
assert.equal(d.trips.length,10799);
assert.equal(d.trips.filter(t=>t.agency==='RDC EuroNight').length,5);
const schedule=[
 ['2026-11-10T18:37:00+01:00','tue-hamburg'],
 ['2026-11-11T22:37:00+01:00','wed-hamburg'],
 ['2026-11-12T19:37:00+01:00','thu-berlin'],
 ['2026-11-14T19:37:00+01:00','sat-berlin']
];
const types={'.html':'text/html','.css':'text/css','.js':'text/javascript','.json':'application/json',
 '.webp':'image/webp','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg'};
const server=createServer(async(req,res)=>{
 try{
  const path=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const file=resolve(root,'.'+(path==='/'?'/index.html':path));
  if(!file.startsWith(root+'/')){res.writeHead(403);res.end();return}
  const bytes=await readFile(file);
  res.writeHead(200,{'content-type':types[extname(file)]||'application/octet-stream','cache-control':'no-store'});
  res.end(bytes);
 }catch{res.writeHead(404);res.end('not found')}
});
await new Promise(done=>server.listen(0,'127.0.0.1',done));
const host=(process.env.SMOKE_URL||('http://127.0.0.1:'+server.address().port)).replace(/[/]$/,'');
let browser;
try{
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 for(const size of [{width:1480,height:930},{width:390,height:844}]){
  for(const [clock,variant] of schedule){
   const epoch=Date.parse(clock)/1000;
   const expected=activeRailTrips(d,epoch,20000).filter(x=>x.agency==='RDC EuroNight');
   assert(expected.some(x=>x.package06Variant===variant),'Source RDC schedule not on route '+clock);
   const ctx=await browser.newContext({viewport:size});
   await ctx.addInitScript(t=>{const original=Date.now.bind(Date),delta=t-original();Date.now=()=>original()+delta;},epoch*1000);
   const page=await ctx.newPage(),errors=[],requests=[];
   page.on('pageerror',e=>errors.push(String(e)));
   page.on('request',r=>{if(r.url().startsWith(host))requests.push(r.url())});
   const response=await page.goto(host+'/?rdc-actual-autumn='+variant,{waitUntil:'domcontentloaded',timeout:60000});
   assert.equal(response.status(),200);
   await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:45000});
   await page.locator('[data-filter="rdc"]').click();
   await page.waitForFunction(count=>document.querySelectorAll('#vehicle-list button.vehicle').length===count,expected.length,{timeout:35000});
   assert.equal(await page.locator('#vehicle-list button.vehicle').count(),expected.length);
   await page.waitForTimeout(1200);
   const markers=page.locator('.leaflet-marker-icon img.rail-photo-marker');
   assert.equal(await markers.count(),expected.length,'Actual train markers missing');
   assert(await markers.first().evaluate(i=>i.complete&&i.naturalWidth>0),'RDC marker failed to decode');
   for(const ver of ['app.js?v=package06-01','rail-data.js?v=package06-01','rail.json?v=package06-01'])
    assert(requests.some(url=>url.includes(ver)),'Stale data or JS '+ver);
   await page.locator('#vehicle-list button.vehicle').first().click();
   await page.locator('#selected-detail:not([hidden])').waitFor({timeout:12000});
   assert(/^\d+\s*km\/h$/.test((await page.locator('#speed-value').textContent()).trim()));
   assert(/^\d+%$/.test((await page.locator('#occupancy-value').textContent()).trim()));
   await page.waitForFunction(()=>document.querySelector('#selected-detail img')?.naturalWidth>0,null,{timeout:16000});
   await page.locator('#follow').click();
   await page.locator('#satellite').click();
   await page.locator('#clear').click();
   for(const key of ['commuter','metro','arlanda','sj','vr','snalltaget','vy','tagab','rdc','malartag','all'])
    assert.equal(await page.locator('[data-filter="'+key+'"]').count(),1,'Original operator filter missing '+key);
   assert.deepEqual(errors,[],'Actual production railway browser JS error');
   console.log('RDC EN344/345 AUTUMN REAL MAP CHROMIUM GREEN',size.width,variant,
     'TRAIN MARKERS',await markers.count(),'REAL CLOCK',clock);
   await ctx.close();
  }
 }
}finally{if(browser)await browser.close();await new Promise(done=>server.close(done))}
