import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createServer} from 'node:http';
import {resolve,join,extname} from 'node:path';
import {chromium} from 'playwright';
import {activeRailTrips} from '../src/rail-data.js';
const root=resolve(process.env.SITE_ROOT||'_site');
const d=JSON.parse(await readFile(join(root,'data/rail.json'),'utf8'));
assert.equal(d.trips.length,10789);
const mime={'.html':'text/html','.css':'text/css','.js':'text/javascript','.json':'application/json',
 '.webp':'image/webp','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg'};
const server=createServer(async(req,res)=>{
 try{
  const uri=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const file=resolve(root,'.'+(uri==='/'?'/index.html':uri));
  if(!file.startsWith(root+'/')){res.writeHead(403);res.end();return}
  const bytes=await readFile(file);
  res.writeHead(200,{'content-type':mime[extname(file)]||'application/octet-stream','cache-control':'no-store'});
  res.end(bytes);
 }catch{res.writeHead(404);res.end('not found')}
});
await new Promise(ok=>server.listen(0,'127.0.0.1',ok));
const host=('http://127.0.0.1:'+server.address().port);
let browser;
try{
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 for(const v of [
  {agency:'SJ',filter:'sj',time:'2026-11-09T10:10:00+01:00'},
  {agency:'VR Snabbtåg',filter:'vr',time:'2026-11-09T21:00:00+01:00'}]){
  const epoch=Date.parse(v.time)/1000;
  assert(activeRailTrips(d,epoch,20000).some(t=>t.package03Verified&&t.agency===v.agency));
  for(const viewport of [{width:1440,height:900},{width:390,height:844}]){
   const context=await browser.newContext({viewport});
   await context.addInitScript(ms=>{
    const orig=Date.now.bind(Date),delta=ms-orig();Date.now=()=>orig()+delta;
   },epoch*1000);
   const page=await context.newPage(),errors=[],requests=[];
   page.on('pageerror',e=>errors.push(String(e)));
   page.on('request',r=>{if(r.url().startsWith(host))requests.push(r.url())});
   const response=await page.goto(host+'/?package03=1',{waitUntil:'domcontentloaded',timeout:60000});
   assert.equal(response.status(),200);
   await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:45000});
   await page.locator('[data-filter="'+v.filter+'"]').click();
   await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:25000});
   await page.waitForTimeout(1600);
   assert((await page.locator('.leaflet-marker-icon img.rail-photo-marker').count())>0,'Missing train markers '+v.agency);
   for(const s of ['app.js?v=package03-01','rail-data.js?v=package03-01','rail.json?v=package03-01']){
    assert(requests.some(x=>x.includes(s)),'Browser is using old cache '+s);
   }
   const first=page.locator('#vehicle-list button.vehicle').first();
   await first.click();
   await page.locator('#selected-detail:not([hidden])').waitFor({timeout:12000});
   await page.locator('#follow').click();
   await page.locator('#satellite').click();
   assert.deepEqual(errors,[],'Browser script errors '+v.agency);
   console.log('PACKAGE03 CHROMIUM GREEN',v.agency,viewport.width,'PHOTO MAP MARKERS',await page.locator('.leaflet-marker-icon img.rail-photo-marker').count());
   await context.close();
  }
 }
}finally{if(browser)await browser.close();await new Promise(ok=>server.close(ok))}
