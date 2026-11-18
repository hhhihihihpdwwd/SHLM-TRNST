// Actual rendered Stockholm Rail map QA: Metro peak, midday, weekend, night;
// unchanged 15 systems, full map markers, route preview, photo and follow UX.
// Use STABLE29_TEST_URL to test the same build on live GitHub Pages preview.
import assert from 'node:assert/strict';
import {readFile,mkdir} from 'node:fs/promises';
import {createServer} from 'node:http';
import {resolve,join,extname} from 'node:path';
import {chromium} from 'playwright';
import {activeRailTrips,railAt} from '../_release/website/src/rail-data.js';
import {matchesRailFilter} from '../_release/website/src/rail-filter.js';

const root=resolve('_release/website');
const data=JSON.parse(await readFile(join(root,'data/rail.json'),'utf8'));
assert(data.metroWeekdaySimulation && data.counts.metro===13372);
const types={'.html':'text/html','.css':'text/css','.js':'text/javascript','.json':'application/json',
 '.webp':'image/webp','.png':'image/png','.jpg':'image/jpeg','.svg':'image/svg+xml'};
const server=createServer(async(req,res)=>{
 try{
  const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const file=resolve(root,'.'+(pathname==='/'?'/index.html':pathname));
  if(!file.startsWith(root+'/')){res.writeHead(403);res.end();return}
  const payload=await readFile(file);
  res.writeHead(200,{'Content-Type':types[extname(file)]||'application/octet-stream',
   'Cache-Control':'no-store'});res.end(payload);
 }catch(e){res.writeHead(404);res.end('not found')}
});
const online=process.env.STABLE29_TEST_URL;
if(!online)await new Promise(r=>server.listen(0,'127.0.0.1',r));
const url=online||'http://127.0.0.1:'+server.address().port+'/';
const folder=process.env.STABLE29_SHOTS||'_release/qa-screenshots';
await mkdir(folder,{recursive:true});
const scenes=[
 {stamp:'2026-11-18T09:47:00+01:00',viewport:{width:1877,height:799},name:'wednesday-0947-desktop',expected:67,full:true},
 {stamp:'2026-11-18T08:30:00+01:00',viewport:{width:1440,height:900},name:'wednesday-0830-desktop',expected:93},
 {stamp:'2026-11-21T12:30:00+01:00',viewport:{width:390,height:844},name:'saturday-1230-mobile'},
 {stamp:'2026-11-22T00:30:00+01:00',viewport:{width:1440,height:900},name:'sunday-0030-night'},
 {stamp:'2026-11-18T09:47:00+01:00',viewport:{width:390,height:844},name:'wednesday-0947-mobile',expected:67},
];
const filters=['commuter','metro','tram','nockeby','lidingo','city7','roslags','saltsjo',
               'arlanda','sj','vr','snalltaget','vy','tagab','rdc','malartag'];
const b=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
try{
 for(const scene of scenes){
  const epoch=Date.parse(scene.stamp)/1000;
  const scheduled=activeRailTrips(data,epoch,25000);
  const metro=scheduled.filter(t=>t.mode==='metro');
  if(scene.expected!==undefined)assert.equal(metro.length,scene.expected,'Source count differs for '+scene.name);
  const ctx=await b.newContext({viewport:scene.viewport,deviceScaleFactor:1});
  await ctx.addInitScript(t=>{
   const real=Date.now.bind(Date),offset=t-real();
   Date.now=()=>real()+offset;
  },epoch*1000);
  const page=await ctx.newPage(),errors=[];
  page.on('pageerror',err=>errors.push(String(err)));
  const response=await page.goto(url,{waitUntil:'domcontentloaded',timeout:100000});
  assert.equal(response.status(),200,'Preview/public URL not accessible: '+url);
  assert.equal(await page.title(),'Stockholm Rail');
  await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,
    null,{timeout:100000});
  const filter=async name=>{
   const expected=scheduled.filter(t=>matchesRailFilter(t,name)).length;
   const button=page.locator('[data-filter="'+name+'"]');
   if(name==='all')await page.locator('.all-trains-button').click();
   else{
    // Original infinite slider; click arrows to bring matching category to center.
    for(let i=0;i<filters.length;i++){
     const current=await page.locator('[data-carousel-position="current"]').getAttribute('data-filter');
     if(current===name)break;
     await page.locator('#rail-next').click();
    }
    assert.equal(await page.locator('[data-carousel-position="current"]').getAttribute('data-filter'),name);
    await page.locator('[data-carousel-position="current"]').click();
   }
   if(expected>0){
    await page.waitForFunction(count=>
       document.querySelectorAll('#vehicle-list button.vehicle').length===count,
       expected,{timeout:100000});
   }
   await page.waitForFunction(count=>document.querySelectorAll('.leaflet-marker-icon').length===count,
     expected,{timeout:100000});
   console.log('CHROMIUM',scene.name,name,'active GTFS',expected,'list+markers exact');
   return expected;
  };
  await filter('metro');
  await page.waitForTimeout(1300);
  const onscreen=await page.locator('.leaflet-marker-icon').evaluateAll(els=>{
   const map=document.querySelector('#map').getBoundingClientRect();
   return els.filter(el=>{
    const r=el.getBoundingClientRect();
    return r.right>=map.left&&r.left<=map.right&&r.bottom>=map.top&&r.top<=map.bottom;
   }).length;
  });
  console.log('VISIBLE REAL MAP',scene.name,'onscreen',onscreen,'of',metro.length,'TOTAL METRO');
  assert(onscreen>=Math.max(1,Math.floor(metro.length*.8)),
    'Most Metro trains not visible after fitBounds '+scene.name+' '+onscreen+'/'+metro.length);
  await page.screenshot({path:folder+'/'+scene.name+'-metro.png',fullPage:true});
  if(scene.full){
   for(const name of filters)await filter(name);
   await filter('all');
   assert.equal(await page.locator('.leaflet-marker-icon').count(),scheduled.length);
   await filter('metro');
  }
  if(metro.length){
   await page.locator('#vehicle-list button.vehicle').first().click();
   await page.locator('#selected-detail').waitFor({state:'visible'});
   assert(await page.locator('#train-heading').innerText());
   assert((await page.locator('#train-sub').innerText()).includes('veckodag'),
     'Metro user-facing help still wrongly says one Friday every day');
   assert(await page.locator('#stops .stop').count()>=2,'Missing stop timeline');
   const src=await page.locator('.image-placeholder img').getAttribute('src');
   assert(src,'Train photos must remain accessible');
   await page.waitForFunction(()=>document.querySelector('.image-placeholder img')?.naturalWidth>0,
     null,{timeout:25000});
   await page.locator('#follow').click();
   assert((await page.locator('#follow').innerText()).includes('Följer'));
   // Leaflet uses Canvas; no SVG-only route test.
   const canvas=page.locator('.leaflet-overlay-pane canvas');
   await canvas.first().waitFor({state:'attached',timeout:15000});
   const hasPixels=await canvas.evaluateAll(nodes=>nodes.some(node=>{
    try{
     const c=node.getContext('2d');
     if(!c)return false;
     const bytes=c.getImageData(0,0,node.width,node.height).data;
     let n=0;
     for(let i=3;i<bytes.length;i+=4)if(bytes[i]>0&&++n>=20)return true;
    }catch(e){return false}
    return false;
   }));
   assert(hasPixels,'Selected train route was not actually painted on map Canvas');
   await page.screenshot({path:folder+'/'+scene.name+'-train-details.png',fullPage:true});
   await page.locator('#clear').click();
  }
  assert.deepEqual(errors,[],'No map JS exceptions: '+scene.name);
  await ctx.close();
 }
 console.log('STABLE29 COMPLETE BROWSER REGRESSION AND VISUAL CAPTURES PASS: exact real GTFS trains, routes, all existing modes');
}finally{await b.close();if(!online)server.close()}
