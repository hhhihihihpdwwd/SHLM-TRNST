import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createServer} from 'node:http';
import {resolve,join,extname} from 'node:path';
import {chromium} from 'playwright';
import {activeRailTrips} from '../src/rail-data.js';
const root=resolve(process.env.SITE_ROOT||'_site');
const d=JSON.parse(await readFile(join(root,'data/rail.json'),'utf8'));
assert.equal(d.trips.length,10798);
assert.deepEqual(d.package05Audit.addedPerOperator,{'Vy Tåg':0,'Tågab':0});
const midnight=Date.parse('2026-11-09T00:00:00+01:00')/1000;
const cases=[];
for(const [agency,filter] of [['Vy Tåg','vy'],['Tågab','tagab']]){
 for(const dir of ['to-stockholm','from-stockholm']){
  let chosen=null;
  for(let m=0;m<24*60;m+=10){
   const epoch=midnight+m*60;
   const vs=activeRailTrips(d,epoch,20000).filter(t=>t.agency===agency);
   if(vs.some(x=>x.direction===dir)){chosen={agency,filter,dir,epoch,count:vs.length};break}
  }
  assert(chosen,'No displayed historic '+agency+' in '+dir);
  cases.push(chosen);
 }
}
const mime={'.html':'text/html','.css':'text/css','.js':'text/javascript','.json':'application/json','.webp':'image/webp','.jpg':'image/jpeg','.png':'image/png','.svg':'image/svg+xml'};
const server=createServer(async(req,res)=>{
 try{
  const url=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const path=resolve(root,'.'+(url==='/'?'/index.html':url));
  if(!path.startsWith(root+'/')){res.writeHead(403);res.end();return}
  const bytes=await readFile(path);
  res.writeHead(200,{'Content-Type':mime[extname(path)]||'application/octet-stream','Cache-Control':'no-store'});
  res.end(bytes);
 }catch{res.writeHead(404);res.end('not found')}
});
await new Promise(ok=>server.listen(0,'127.0.0.1',ok));
const origin=(process.env.SMOKE_URL||('http://127.0.0.1:'+server.address().port)).replace(/[/]$/,'');
let browser;
try{
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 for(const viewport of [{width:1500,height:940},{width:390,height:844}]){
  for(const item of cases){
   const ctx=await browser.newContext({viewport});
   await ctx.addInitScript(t=>{const real=Date.now.bind(Date),delta=t-real();Date.now=()=>real()+delta},item.epoch*1000);
   const page=await ctx.newPage(),errors=[],requested=[];
   page.on('pageerror',e=>errors.push(String(e)));
   page.on('request',r=>{if(r.url().startsWith(origin))requested.push(r.url())});
   const response=await page.goto(origin+'/?package05='+item.filter+'-'+item.dir,{waitUntil:'domcontentloaded',timeout:60000});
   assert.equal(response.status(),200);
   await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:45000});
   await page.locator('[data-filter="'+item.filter+'"]').click();
   await page.waitForFunction(n=>document.querySelectorAll('#vehicle-list button.vehicle').length===n,item.count,{timeout:35000});
   assert.equal(await page.locator('#vehicle-list button.vehicle').count(),item.count);
   await page.waitForTimeout(1400);
   const markers=page.locator('.leaflet-marker-icon img.rail-photo-marker');
   assert.equal(await markers.count(),item.count,'Published map is missing an actual '+item.agency+' marker');
   assert(await markers.first().evaluate(i=>i.complete&&i.naturalWidth>0),'Actual train front marker broken');
   for(const file of ['app.js?v=package05-01','rail-data.js?v=package05-01','rail.json?v=package05-01'])
    assert(requested.some(url=>url.includes(file)),'Stale browser dependency '+file);
   await page.locator('#vehicle-list button.vehicle').first().click();
   await page.locator('#selected-detail:not([hidden])').waitFor({timeout:12000});
   assert(/^\d+\s*km\/h$/.test((await page.locator('#speed-value').textContent()).trim()));
   assert(/^\d+%$/.test((await page.locator('#occupancy-value').textContent()).trim()));
   await page.waitForFunction(()=>document.querySelector('#selected-detail img')?.naturalWidth>0,null,{timeout:18000});
   await page.locator('#follow').click();
   await page.locator('#satellite').click();
   await page.locator('#clear').click();
   for(const name of ['commuter','metro','arlanda','sj','vr','malartag','snalltaget','vy','tagab','rdc','all'])
    assert.equal(await page.locator('[data-filter="'+name+'"]').count(),1);
   assert.deepEqual(errors,[],'Browser error');
   console.log('PACKAGE05 ACTUAL RAIL MAP CHROMIUM GREEN',viewport.width,item.agency,item.dir,'VEHICLES',item.count,'PHOTOS',await markers.count());
   await ctx.close();
  }
 }
}finally{if(browser)await browser.close();await new Promise(ok=>server.close(ok))}
