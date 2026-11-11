import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createServer} from 'node:http';
import {resolve,join,extname} from 'node:path';
import {pathToFileURL} from 'node:url';
import {chromium} from 'playwright';
const root=resolve(process.env.SITE_ROOT||'_site');
const d=JSON.parse(await readFile(join(root,'data/rail.json'),'utf8'));
assert.equal(d.trips.length,10827);
assert.equal(d.trips.filter(t=>t.package07Verified).length,28);
const {activeRailTrips}=await import(pathToFileURL(join(root,'src/rail-data.js')).href);
const {matchesRailFilter}=await import(pathToFileURL(join(root,'src/rail-filter.js')).href);
const zero=Date.parse('2026-11-09T00:00:00+01:00')/1000;
const scenes=[];
for(const mode of ['commuter','metro']){
 const candidates=d.trips.filter(t=>t.package07Verified&&t.mode===mode);
 assert(candidates.length>0);
 let best=null;
 for(let minute=0;minute<1440;minute+=10){
  const epoch=zero+minute*60;
  const active=activeRailTrips(d,epoch,20000);
  const verified=active.filter(t=>t.package07Verified&&t.mode===mode);
  if(verified.length && (!best||verified.length>best.verified))
    best={epoch,filter:mode,verified:verified.length,label:'new-authentic-'+mode};
 }
 assert(best,'new '+mode+' train not on map during the day');
 scenes.push(best);
}
scenes.push({epoch:Date.parse('2026-11-09T13:07:00+01:00')/1000,filter:'all',label:'all-nine-rail-systems'});
const types={'.html':'text/html','.css':'text/css','.js':'text/javascript','.json':'application/json',
 '.webp':'image/webp','.svg':'image/svg+xml','.jpg':'image/jpeg','.png':'image/png'};
const server=createServer(async(req,res)=>{
 try{
  const p=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const file=resolve(root,'.'+(p==='/'?'/index.html':p));
  if(!file.startsWith(root+'/')){res.writeHead(403);res.end();return}
  const bytes=await readFile(file);
  res.writeHead(200,{'Content-Type':types[extname(file)]||'application/octet-stream','Cache-Control':'no-store'});res.end(bytes);
 }catch{res.writeHead(404);res.end('not found')}
});
await new Promise(ok=>server.listen(0,'127.0.0.1',ok));
const host=(process.env.SMOKE_URL||('http://127.0.0.1:'+server.address().port)).replace(/[/]$/,'');
let browser;
const allFilters=['commuter','metro','tram','nockeby','lidingo','city7','roslags','saltsjo','arlanda'];
try{
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 for(const viewport of [{width:1460,height:940},{width:390,height:844}]){
  for(const scene of scenes){
   const ctx=await browser.newContext({viewport});
   await ctx.addInitScript(t=>{const real=Date.now.bind(Date),offset=t-real();Date.now=()=>real()+offset},scene.epoch*1000);
   const page=await ctx.newPage(),errors=[],requested=[];
   page.on('pageerror',e=>errors.push(String(e)));
   page.on('request',r=>{if(r.url().startsWith(host))requested.push(r.url())});
   const response=await page.goto(host+'/?package07='+scene.label,{waitUntil:'domcontentloaded',timeout:65000});
   assert.equal(response.status(),200);
   await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:60000});
   for(const key of ['app.js?v=package07-01','rail-data.js?v=package07-01','rail.json?v=package07-01'])
    assert(requested.some(x=>x.includes(key)),'Browser still using old public site cache '+key);
   const filters=scene.filter==='all'?allFilters:[scene.filter];
   for(const filter of filters){
    const expected=activeRailTrips(d,scene.epoch,10000).filter(x=>matchesRailFilter(x,filter));
    assert(expected.length>0,'No genuine moving train for filter '+filter+' at '+scene.epoch);
    await page.locator('[data-filter="'+filter+'"]').click();
    await page.waitForFunction(n=>document.querySelectorAll('#vehicle-list button.vehicle').length===n,expected.length,{timeout:30000});
    assert.equal(await page.locator('#vehicle-list button.vehicle').count(),expected.length,'Missing filtered '+filter+' trains');
    await page.waitForTimeout(550);
    const markers=page.locator('.leaflet-marker-icon img.rail-photo-marker');
    assert.equal(await markers.count(),expected.length,'Visible physical '+filter+' markers do not match published trip list');
    assert(await markers.first().evaluate(i=>i.complete&&i.naturalWidth>0),'Train photo marker broken '+filter);
    if(scene.filter!=='all')
     assert(expected.some(t=>t.package07Verified),'No verified NEW historical return train in '+filter);
    console.log('LOCAL RAIL PUBLIC MAP FILTER',viewport.width,filter,'VISIBLE REAL TRAINS',expected.length);
   }
   await page.locator('#vehicle-list button.vehicle').first().click();
   await page.locator('#selected-detail:not([hidden])').waitFor({timeout:12000});
   assert(/^\d+\s*km\/h$/.test((await page.locator('#speed-value').textContent()).trim()));
   assert(/^\d+%$/.test((await page.locator('#occupancy-value').textContent()).trim()));
   await page.waitForFunction(()=>document.querySelector('#selected-detail img')?.naturalWidth>0,null,{timeout:16000});
   await page.locator('#follow').click();
   await page.locator('#satellite').click();
   await page.locator('#clear').click();
   for(const name of [...allFilters,'sj','vr','snalltaget','vy','tagab','rdc','malartag','all'])
    assert.equal(await page.locator('[data-filter="'+name+'"]').count(),1,'Missing old filter '+name);
   assert.deepEqual(errors,[],'Local rail Chromium page script errors');
   console.log('PACKAGE07 CHROMIUM GREEN',viewport.width,scene.label,'ALL RAIL SYSTEMS AND ORIGINAL CONTROLS RETAINED');
   await ctx.close();
  }
 }
}finally{if(browser)await browser.close();await new Promise(ok=>server.close(ok))}
