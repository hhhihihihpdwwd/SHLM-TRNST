import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createServer} from 'node:http';
import {resolve,join,extname} from 'node:path';
import {chromium} from 'playwright';
import {activeRailTrips} from '../_release/website/src/rail-data.js';
import {matchesRailFilter} from '../_release/website/src/rail-filter.js';

const root=resolve('_release/website');
const dataset=JSON.parse(await readFile(join(root,'data/rail.json'),'utf8'));
assert(dataset.arlandaWeekdaySimulation);
const mime={'.html':'text/html','.css':'text/css','.js':'text/javascript','.json':'application/json',
 '.webp':'image/webp','.png':'image/png','.jpg':'image/jpeg','.svg':'image/svg+xml'};
const server=createServer(async(req,res)=>{
 try{
  const path=decodeURIComponent(new URL(req.url,'http://127.0.0.1').pathname);
  const name=resolve(root,'.'+(path==='/'?'/index.html':path));
  if(!name.startsWith(root+'/')){res.writeHead(403);res.end();return}
  const payload=await readFile(name);
  res.writeHead(200,{'Content-Type':mime[extname(name)]||'application/octet-stream'});
  res.end(payload);
 }catch(e){res.writeHead(404);res.end('not found')}
});
const online=process.env.STABLE31_TEST_URL;
if(!online)await new Promise(r=>server.listen(0,'127.0.0.1',r));
const url=online||'http://127.0.0.1:'+server.address().port+'/';
const browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
try{
 for(const day of ['2026-11-16','2026-11-17','2026-11-18','2026-11-19',
   '2026-11-20','2026-11-21','2026-11-22']){
  const stamp=day+'T10:53:22+01:00',epoch=Date.parse(stamp)/1000;
  const expected=activeRailTrips(dataset,epoch,25000).filter(x=>matchesRailFilter(x,'arlanda')).length;
  const context=await browser.newContext({viewport:day.endsWith('21')?{width:390,height:844}:{width:1440,height:900}});
  await context.addInitScript(t=>{const real=Date.now.bind(Date),delta=t-real();Date.now=()=>real()+delta;},epoch*1000);
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(String(e)));
  await page.goto(url,{waitUntil:'domcontentloaded',timeout:80000});
  await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:80000});
  for(let i=0;i<20;i++){
   if(await page.locator('[data-carousel-position="current"]').getAttribute('data-filter')==='arlanda')break;
   await page.locator('#rail-next').click();
  }
  assert.equal(await page.locator('[data-carousel-position="current"]').getAttribute('data-filter'),'arlanda');
  await page.locator('[data-carousel-position="current"]').click();
  await page.waitForFunction(n=>document.querySelectorAll('#vehicle-list button.vehicle').length===n,expected,{timeout:40000});
  await page.waitForFunction(n=>document.querySelectorAll('.leaflet-marker-icon').length===n,expected,{timeout:40000});
  assert(expected>=1,'No authentic Arlanda train on day '+day);
  await page.locator('#vehicle-list button.vehicle').first().click();
  await page.locator('#selected-detail').waitFor({state:'visible'});
  assert((await page.locator('#train-sub').innerText()).includes('veckodag'),
   'Arlanda still misleadingly says Friday each day');
  assert(await page.locator('#stops .stop').count()===3,'Arlanda must retain all 3 actual stations');
  await page.waitForFunction(()=>document.querySelector('.image-placeholder img')?.naturalWidth>0,null,{timeout:25000});
  assert.deepEqual(errors,[],day+' JS error');
  console.log('ARLANDA EXACT HISTORICAL SOURCE WEEK IN CHROMIUM',day,'present',expected,'of',expected,
    '3-station line, verified OSM and photo');
  await context.close();
 }
}finally{await browser.close();if(!online)server.close()}
console.log('ALL SEVEN ARLANDA GTFS DAYTYPE BROWSER CHECKS GREEN');
