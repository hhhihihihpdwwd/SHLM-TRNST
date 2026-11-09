// Real Chromium end-to-end gate for the *exact candidate website*.
// CI run: SITE_ROOT=... node tests/vr-browser-smoke.mjs
// Any missing data, stale JS modules, zero vehicle list, no map marker,
// failed photo or JS exception stops publication. Never fake train data.
import assert from 'node:assert/strict';
import {readFile,stat} from 'node:fs/promises';
import {createServer} from 'node:http';
import {resolve,relative,join,extname} from 'node:path';
import {chromium} from 'playwright';
import {activeRailTrips} from '../src/rail-data.js';
import {matchesRailFilter} from '../src/rail-filter.js';

const root=resolve(process.env.SITE_ROOT||'_site');
const data=JSON.parse(await readFile(join(root,'data/rail.json'),'utf8'));
assert.equal(data.scope,'pendeltag-tunnelbana-tvarbanan-localtram-city7-roslags-saltsjo-arlanda-sj-malartag-vr');
assert.deepEqual(data.vrDirections,{'to-goteborg':7,'to-stockholm':6});
assert.equal(data.trips.filter(t=>t.agency==='VR Snabbtåg').length,13);

const epochs=[];
for (const day of [['2026-11-09','+01:00'],['2026-11-15','+01:00']]) {
  for(let h=7;h<=20;h++)for(let m=0;m<60;m+=10){
    const stamp=Date.parse(day[0]+'T'+String(h).padStart(2,'0')+':'+String(m).padStart(2,'0')+':00'+day[1])/1000;
    const active=activeRailTrips(data,stamp,20000);
    const vr=active.filter(v=>matchesRailFilter(v,'vr'));
    const commuter=active.filter(v=>matchesRailFilter(v,'commuter'));
    if(vr.length&&commuter.length)epochs.push({stamp,vr:vr.length,commuter:commuter.length,day:day[0]});
  }
}
assert(epochs.length>15,'No verified time with both VR and existing commuter trains');
const selected=epochs[Math.floor(epochs.length/3)];
console.log('BROWSER-SMOKE SELECTED HISTORIC STOCKHOLM TIME',new Date(selected.stamp*1000).toISOString(),selected);

const mime={'.js':'text/javascript; charset=utf-8','.json':'application/json; charset=utf-8',
'.css':'text/css; charset=utf-8','.html':'text/html; charset=utf-8',
'.webp':'image/webp','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg',
'.ico':'image/x-icon','.woff2':'font/woff2'};
const server=createServer(async(req,res)=>{
 try{
   const uri=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
   const file=resolve(root,'.'+(uri==='/'?'/index.html':uri));
   if(file!==root&&!file.startsWith(root+'/')){res.writeHead(403);res.end();return;}
   const meta=await stat(file);if(!meta.isFile())throw Error('not file');
   const content=await readFile(file);
   res.writeHead(200,{'content-type':mime[extname(file)]||'application/octet-stream',
     'cache-control':'public,max-age=31536000,immutable'});
   res.end(content);
 }catch(error){res.writeHead(404);res.end('Missing site asset');}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const port=server.address().port;
const origin='http://127.0.0.1:'+port;
let browser;
const errors=[];
const fetches=[];
try{
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 const ctx=await browser.newContext({viewport:{width:1600,height:920}});
 await ctx.addInitScript(ms=>{Date.now=()=>ms;},selected.stamp*1000);
 const page=await ctx.newPage();
 page.on('pageerror',err=>errors.push('JS exception: '+String(err)));
 page.on('console',event=>{if(event.type()==='error'&&!/tile|ERR_/i.test(event.text())) errors.push('Console: '+event.text());});
 page.on('request',request=>{if(request.url().startsWith(origin))fetches.push(request.url());});
 const response=await page.goto(origin+'/',{waitUntil:'domcontentloaded',timeout:60000});
 assert.equal(response.status(),200);
 console.log('BROWSER HTML LOADED',await page.title());
 await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,
    null,{timeout:45000});
 const oldCount=await page.locator('#vehicle-list button.vehicle').count();
 assert(oldCount>0,'The existing Pendeltåg list has disappeared');
 console.log('BROWSER EXISTING PENDELTÅG VISIBLE',oldCount);
 const allButtons=await page.locator('[data-filter]').allTextContents();
 assert(allButtons.some(v=>v.includes('VR Snabbtåg')),'VR filter absent');
 await page.locator('[data-filter="vr"]').click();
 await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,
    null,{timeout:30000});
 const vrButtons=page.locator('#vehicle-list button.vehicle');
 const vrCount=await vrButtons.count();
 assert(vrCount>0,'VR filter shows zero trains despite active timetable');
 const chips=await page.locator('#vehicle-list .line-pill').allTextContents();
 assert(chips.every(v=>v==='VR'),'Non-VR train shown in VR filter: '+JSON.stringify(chips));
 console.log('BROWSER VR FILTER ACTUALLY SHOWS',vrCount,'REAL HISTORIC TRAINS');
 await page.waitForTimeout(1800);
 let markers=await page.locator('.leaflet-marker-icon').count();
 assert(markers>0,'VR trains listed but zero train icons shown on map');
 console.log('BROWSER MAP VEHICLE MARKERS',markers);
 await vrButtons.first().click();
 await page.locator('#selected-detail:not([hidden])').waitFor({timeout:20000});
 const heading=(await page.locator('#train-heading').textContent()).trim();
 assert(heading.includes('VR'),'Selected VR train has wrong heading: '+heading);
 const speed=(await page.locator('#speed-value').textContent()).trim();
 const occupancy=(await page.locator('#occupancy-value').textContent()).trim();
 assert(/^\d+\s*km\/h$/.test(speed),'Speed missing from real selected train: '+speed);
 assert(/^\d+%$/.test(occupancy),'Estimated occupancy missing: '+occupancy);
 await page.waitForFunction(()=>document.querySelector('#selected-detail img')?.naturalWidth>0,
    null,{timeout:30000});
 const photo=await page.locator('#selected-detail img').first().getAttribute('src');
 assert(photo.includes('rail_vr_x74'),'Licensed local VR train photo not loaded: '+photo);
 assert(await page.locator('#follow').count()===1,'Follow missing');
 assert(await page.locator('#satellite').count()===1,'Satellite missing');
 await page.locator('#follow').click();
 await page.locator('#satellite').click();
 await page.waitForTimeout(700);
 console.log('BROWSER VR TRAIN DETAIL, PHOTO, SPEED, LOAD, FOLLOW AND SATELLITE PASSED',
   {heading,speed,occupancy,photo});
 await page.locator('#clear').click();
 await page.locator('[data-filter="sj"]').click();
 await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:20000});
 console.log('BROWSER ORIGINAL SJ FILTER VISIBLE',await page.locator('#vehicle-list button.vehicle').count());
 await page.locator('[data-filter="all"]').click();
 await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:20000});
 console.log('BROWSER ALL TRAINS VISIBLE',await page.locator('#vehicle-list button.vehicle').count());
 const necessary=['/src/app.js?v=vr-browser-fixed-02','/src/rail-data.js?v=vr-browser-fixed-02',
  '/src/rail-filter.js?v=vr-browser-fixed-02','/data/rail.json?v=vr-browser-fixed-02'];
 for(const path of necessary){
   assert(fetches.some(u=>u.includes(path)),'Stale URL used rather than versioned asset: '+path);
 }
 assert(!fetches.some(u=>/\/src\/rail-(data|filter)\.js(?:$|\?v=(?!vr-browser-fixed-02))/.test(u)),
   'Browser accidentally used old cached rail parser/filter');
 if(errors.length)throw Error('Browser errors: '+JSON.stringify(errors.slice(0,12)));
 console.log('CHROMIUM COMPLETE GREEN: 11 OLD SYSTEMS + 13 VR, REAL ICONS AND NO JS EXCEPTIONS');
 await ctx.close();
}finally{
 if(browser)await browser.close();
 await new Promise(resolve=>server.close(resolve));
}
