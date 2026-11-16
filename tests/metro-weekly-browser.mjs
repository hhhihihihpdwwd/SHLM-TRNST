import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createServer} from 'node:http';
import {resolve,join,extname} from 'node:path';
import {chromium} from 'playwright';
import {activeRailTrips,railAt} from '../website/src/rail-data.js';

const root=resolve('website');
const d=JSON.parse(await readFile(join(root,'data/rail.json'),'utf8'));
assert.equal(d.metroWeekdaySimulation,true);
const types={'.html':'text/html','.css':'text/css','.js':'text/javascript','.json':'application/json',
 '.webp':'image/webp','.png':'image/png','.jpg':'image/jpeg','.svg':'image/svg+xml'};
const server=createServer(async(req,res)=>{
 try {
  const p=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const file=resolve(root,'.'+(p==='/'?'/index.html':p));
  if(!file.startsWith(root+'/')){res.writeHead(403);res.end();return}
  const bytes=await readFile(file);
  res.writeHead(200,{'Content-Type':types[extname(file)]||'application/octet-stream','Cache-Control':'no-store'});
  res.end(bytes);
 }catch(e){res.writeHead(404);res.end('missing')}
});
await new Promise(ok=>server.listen(0,'127.0.0.1',ok));
const base='http://127.0.0.1:'+server.address().port;
let browser;
try{
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 // Compare precisely against all scheduled, OSM-projected Metro vehicles,
 // including 01:15 on Saturday and all three peak + weekend windows.
 const sample=['2026-11-13T08:30:00+01:00','2026-11-14T01:15:00+01:00',
  '2026-11-14T12:30:00+01:00','2026-11-15T12:30:00+01:00',
  '2026-11-16T08:30:00+01:00','2026-11-16T19:30:00+01:00'];
 for(const stamp of sample){
  const epoch=Date.parse(stamp)/1000;
  const expected=activeRailTrips(d,epoch,20000).filter(t=>t.mode==='metro');
  assert(expected.length>0,'No Metro service at '+stamp);
  assert(expected.every(t=>railAt(t,epoch).pos.every(Number.isFinite)));
  const context=await browser.newContext({viewport:{width:1500,height:920}});
  await context.addInitScript(t=>{const old=Date.now.bind(Date),shift=t-old();Date.now=()=>old()+shift},epoch*1000);
  const page=await context.newPage();
  const jsErrors=[];page.on('pageerror',e=>jsErrors.push(String(e)));
  await page.goto(base+'/',{waitUntil:'domcontentloaded',timeout:60000});
  await page.locator('[data-filter="metro"]').click();
  await page.waitForFunction(count=>document.querySelectorAll('#vehicle-list button.vehicle').length===count,
   expected.length,{timeout:90000});
  // The sidebar updates synchronously; Leaflet markers follow on the next
  // (up to 90 ms) animation tick. Do not count stale previous-filter icons.
  await page.waitForFunction(count=>
    document.querySelectorAll('.leaflet-marker-icon').length===count,
    expected.length,{timeout:30000});
  const actualList=await page.locator('#vehicle-list button.vehicle').count();
  const actualMarkers=await page.locator('.leaflet-marker-icon').count();
  assert.equal(actualList,expected.length,'metro list mismatch '+stamp);
  assert.equal(actualMarkers,expected.length,'metro marker mismatch '+stamp);
  assert.deepEqual(jsErrors,[],'browser exceptions '+stamp);
  console.log('BROWSER METRO',stamp,'EXPECTED',expected.length,'LIST',actualList,'MARKERS',actualMarkers);
  await context.close();
 }
} finally {
 await browser?.close();
 server.close();
}
