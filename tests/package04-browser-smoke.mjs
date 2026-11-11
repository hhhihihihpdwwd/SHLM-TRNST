import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createServer} from 'node:http';
import {resolve,join,extname} from 'node:path';
import {chromium} from 'playwright';
import {activeRailTrips} from '../src/rail-data.js';
const root=resolve(process.env.SITE_ROOT||'_site');
const d=JSON.parse(await readFile(join(root,'data/rail.json'),'utf8'));
assert.equal(d.trips.length,10798);
const starts=Date.parse('2026-11-09T00:00:00+01:00')/1000;
const instants={};
for(const direction of ['from-stockholm','to-stockholm']){
 let best=null;
 for(let min=0;min<1440;min+=10){
  const epoch=starts+min*60;
  const vr=activeRailTrips(d,epoch,20000).filter(t=>t.agency==='VR Snabbtåg');
  const newN=vr.filter(t=>t.package04Verified&&t.direction===direction).length;
  if(newN>0&&(!best||newN>best.newN))best={epoch,newN,expected:vr.length};
 }
 assert(best,'No verified package04 journey on map in '+direction);
 instants[direction]=best;
}
const types={'.html':'text/html','.css':'text/css','.js':'text/javascript','.json':'application/json',
 '.webp':'image/webp','.jpg':'image/jpeg','.png':'image/png','.svg':'image/svg+xml'};
const server=createServer(async(req,res)=>{
 try{
  const path=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const f=resolve(root,'.'+(path==='/'?'/index.html':path));
  if(!f.startsWith(root+'/')){res.writeHead(403);res.end();return}
  const bytes=await readFile(f);
  res.writeHead(200,{'Content-Type':types[extname(f)]||'application/octet-stream','Cache-Control':'no-store'});
  res.end(bytes);
 }catch{res.writeHead(404);res.end('not found')}
});
await new Promise(ok=>server.listen(0,'127.0.0.1',ok));
const host=(process.env.SMOKE_URL||('http://127.0.0.1:'+server.address().port)).replace(/[/]$/,'');
let browser;
try{
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 for(const viewport of [{width:1500,height:940},{width:390,height:844}]){
  for(const [direction,best] of Object.entries(instants)){
   const ctx=await browser.newContext({viewport});
   await ctx.addInitScript(epoch=>{
    const real=Date.now.bind(Date),delta=epoch-real();Date.now=()=>real()+delta;
   },best.epoch*1000);
   const page=await ctx.newPage(),errors=[],requests=[];
   page.on('pageerror',e=>errors.push(String(e)));
   page.on('request',r=>{if(r.url().startsWith(host))requests.push(r.url())});
   const response=await page.goto(host+'/?package04-vr='+direction,{waitUntil:'domcontentloaded',timeout:60000});
   assert.equal(response.status(),200);
   await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:50000});
   await page.locator('[data-filter="vr"]').click();
   await page.waitForFunction(n=>document.querySelectorAll('#vehicle-list button.vehicle').length===n,best.expected,{timeout:45000});
   assert.equal(await page.locator('#vehicle-list button.vehicle').count(),best.expected);
   await page.waitForTimeout(1600);
   const markers=page.locator('.leaflet-marker-icon img.rail-photo-marker');
   assert.equal(await markers.count(),best.expected,'VR map markers do not match timetable vehicle count');
   assert(await markers.first().evaluate(i=>i.complete&&i.naturalWidth>0),'VR train marker photo broken');
   for(const key of ['app.js?v=package04-01','rail-data.js?v=package04-01','rail.json?v=package04-01'])
    assert(requests.some(url=>url.includes(key)),'Old cached JS or timetable '+key);
   await page.locator('#vehicle-list button.vehicle').first().click();
   await page.locator('#selected-detail:not([hidden])').waitFor({timeout:15000});
   assert(/^\d+\s*km\/h$/.test((await page.locator('#speed-value').textContent()).trim()));
   assert(/^\d+%$/.test((await page.locator('#occupancy-value').textContent()).trim()));
   await page.waitForFunction(()=>document.querySelector('#selected-detail img')?.naturalWidth>0,null,{timeout:14000});
   await page.locator('#follow').click();
   await page.locator('#satellite').click();
   await page.locator('#clear').click();
   for(const f of ['commuter','metro','arlanda','sj','vr','malartag','snalltaget','vy','tagab','rdc','all'])
    assert.equal(await page.locator('[data-filter="'+f+'"]').count(),1);
   assert.deepEqual(errors,[],'Public map browser errors');
   console.log('VR PACKAGE04 REAL CHROMIUM GREEN',viewport.width,direction,
    'VALID VR TRAINS',best.expected,'NEW IN DIRECTION',best.newN,'MARKERS',await markers.count());
   await ctx.close();
  }
 }
}finally{if(browser)await browser.close();await new Promise(ok=>server.close(ok))}
