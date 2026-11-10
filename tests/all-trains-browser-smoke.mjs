// Real desktop & mobile Chromium regression: all active train list rows and all
// map markers at the simulation's busiest hour, plus 16:37 Malmö departure.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createServer} from 'node:http';
import {resolve,join,extname} from 'node:path';
import {chromium} from 'playwright';
import {activeRailTrips,railAt} from '../src/rail-data.js';

const root=resolve(process.env.SITE_ROOT||'_site');
const d=JSON.parse(await readFile(join(root,'data/rail.json'),'utf8'));
let busiest={epoch:0,count:0};
for(let min=0;min<1440;min+=5){
 const epoch=Date.parse('2026-11-10T00:00:00+01:00')/1000+min*60;
 const n=activeRailTrips(d,epoch,20000).length;
 if(n>busiest.count)busiest={epoch,count:n,min};
}
assert(busiest.count>90,'Audit requires >90 trains to catch old list truncation');
const types={'.html':'text/html','.css':'text/css','.js':'text/javascript','.json':'application/json',
 '.webp':'image/webp','.png':'image/png','.jpg':'image/jpeg','.svg':'image/svg+xml'};
const server=createServer(async(req,res)=>{
 try{
  const p=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const f=resolve(root,'.'+(p==='/'?'/index.html':p));
  if(f!==root&&!f.startsWith(root+'/')){res.writeHead(403);res.end();return}
  const b=await readFile(f);
  res.writeHead(200,{'Content-Type':types[extname(f)]||'application/octet-stream','Cache-Control':'no-store'});
  res.end(b);
 }catch(e){res.writeHead(404);res.end('not found')}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const base=(process.env.SMOKE_URL||'http://127.0.0.1:'+server.address().port).replace(/\/$/,'');
let browser;
try{
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 for(const viewport of [{width:1500,height:920},{width:390,height:844}]){
  for(const [phase,epoch] of [['all-trains',busiest.epoch],['malmo-1637',Date.parse('2026-11-10T16:37:00+01:00')/1000]]){
   const context=await browser.newContext({viewport});
   await context.addInitScript(time=>{
    const real=Date.now.bind(Date),shift=time-real();Date.now=()=>real()+shift;
   },epoch*1000);
   const page=await context.newPage(),errors=[];
   page.on('pageerror',e=>errors.push(String(e)));
   const response=await page.goto(base+'/?train-audit-phase='+phase,
    {waitUntil:'domcontentloaded',timeout:60000});
   assert.equal(response.status(),200);
   await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:45000});
   if(phase==='all-trains'){
    await page.locator('[data-filter="all"]').click();
    await page.waitForFunction(expected=>
      document.querySelectorAll('#vehicle-list button.vehicle').length===expected,busiest.count,{timeout:30000});
    assert.equal(await page.locator('#vehicle-list button.vehicle').count(),busiest.count);
    // No fake markers or missing vehicles after zooming to world view;
    // the 280-marker cap is above the actual peak of 235 trains.
    for(let i=0;i<10;i++)await page.locator('.leaflet-control-zoom-out').click();
    await page.waitForTimeout(2200);
    const n=await page.locator('.leaflet-marker-icon').count();
    assert.equal(n,busiest.count,'Map does not render EVERY train that should be active');
    await page.locator('#satellite').click();
    console.log('ALL VISIBLE MAP MARKERS',viewport.width,phase,'expected',busiest.count,'actual',n);
   }else{
    await page.locator('[data-filter="snalltaget"]').click();
    await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:20000});
    const rows=page.locator('#vehicle-list button.vehicle');
    let verified=false;
    for(let i=0;i<await rows.count();i++){
     await rows.nth(i).click();
     await page.waitForFunction(()=>!document.querySelector('#selected-detail')?.hidden,null,{timeout:10000});
     const station=(await page.locator('#next-stop-name').textContent()).trim();
     const speed=parseInt((await page.locator('#speed-value').textContent()).trim(),10);
     if(station==='Lund Centralstation'&&speed>0){verified=true;break}
     await page.locator('#clear').click();
    }
    assert(verified,'Real Chromium still shows Malmö or 0 km/h at 16:37 for 16:18 departure');
    await page.locator('#follow').click();
    console.log('EXACT MALMÖ 16:18 DEPARTURE IS MOVING BY 16:37',viewport.width);
   }
   assert.deepEqual(errors,[],'JavaScript runtime errors on deployed complete 16-system site');
   await context.close();
  }
 }
}finally{
 if(browser)await browser.close();
 await new Promise(resolve=>server.close(resolve));
}
