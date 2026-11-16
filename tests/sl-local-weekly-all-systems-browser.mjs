// Comprehensive real Chromium regression: all 16 railway systems, all train
// markers on ALL trains, and each local rail filter at historic Mon/Sat/Sun.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createServer} from 'node:http';
import {resolve,join,extname} from 'node:path';
import {chromium} from 'playwright';
import {activeRailTrips} from '../website/src/rail-data.js';
import {matchesRailFilter} from '../website/src/rail-filter.js';

const root=resolve('website');
const d=JSON.parse(await readFile(join(root,'data/rail.json'),'utf8'));
assert(d.localWeekdaySimulation && d.metroWeekdaySimulation && d.commuterWeekdaySimulation);
const mime={'.html':'text/html','.css':'text/css','.js':'text/javascript','.json':'application/json',
 '.webp':'image/webp','.png':'image/png','.jpg':'image/jpeg','.svg':'image/svg+xml'};
const server=createServer(async(req,res)=>{
 try{
  const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const file=resolve(root,'.'+(pathname==='/'?'/index.html':pathname));
  if(!file.startsWith(root+'/')){res.writeHead(403);res.end();return}
  const payload=await readFile(file);
  res.writeHead(200,{'Content-Type':mime[extname(file)]||'application/octet-stream','Cache-Control':'no-store'});
  res.end(payload);
 }catch(e){res.writeHead(404);res.end('not found')}
});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const url='http://127.0.0.1:'+server.address().port+'/';
const filters=['tram','nockeby','lidingo','city7','roslags','saltsjo','metro','commuter','arlanda','sj','vr','snalltaget','vy','tagab','rdc','malartag','all'];
const scenes=[
 ['2026-11-16T08:30:00+01:00',{width:1500,height:900}],
 ['2026-11-14T12:30:00+01:00',{width:390,height:844}],
 ['2026-11-15T19:30:00+01:00',{width:1500,height:900}]
];
let browser;
try{
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 for(const [stamp,viewport] of scenes){
  const epoch=Date.parse(stamp)/1000;
  const scheduled=activeRailTrips(d,epoch,20000);
  const ctx=await browser.newContext({viewport});
  await ctx.addInitScript(time=>{const raw=Date.now.bind(Date),delta=time-raw();Date.now=()=>raw()+delta},epoch*1000);
  const page=await ctx.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  const response=await page.goto(url,{waitUntil:'domcontentloaded',timeout:90000});
  assert.equal(response.status(),200);
  await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:90000});
  for(const filter of filters){
   const expected=scheduled.filter(t=>matchesRailFilter(t,filter)).length;
   await page.locator('[data-filter="'+filter+'"]').click();
   await page.waitForFunction(n=>document.querySelectorAll('#vehicle-list button.vehicle').length===n,
    expected,{timeout:45000});
   await page.waitForFunction(n=>document.querySelectorAll('.leaflet-marker-icon').length===n,
    expected,{timeout:45000});
   console.log('BROWSER FULL STABLE24',stamp,viewport.width,filter,expected,'rows and markers');
  }
  assert.deepEqual(errors,[],'Browser console exceptions at '+stamp);
  await ctx.close();
 }
} finally {
 await browser?.close();
 server.close();
}
