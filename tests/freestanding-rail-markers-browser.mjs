import assert from 'node:assert/strict';
import {readFile,mkdir} from 'node:fs/promises';
import {createServer} from 'node:http';
import {resolve,extname} from 'node:path';
import {chromium} from 'playwright';
import {activeRailTrips} from '../website/src/rail-data.js';
import {matchesRailFilter} from '../website/src/rail-filter.js';

const root=resolve('website');
const source=JSON.parse(await readFile(root+'/data/rail.json','utf8'));
assert.equal(source.trips.length,10827);
assert.equal(Object.keys(source.shapes).length,107);
const selectedPaths={
 roslags:'./src/assets/roslagsbanan-B-standalone.webp?v=free-train-01',
 saltsjo:'./src/assets/saltsjobanan-B-standalone.webp?v=free-train-01'
};
const types={'.html':'text/html','.css':'text/css','.js':'text/javascript',
 '.json':'application/json','.webp':'image/webp','.png':'image/png','.jpg':'image/jpeg','.svg':'image/svg+xml'};
const server=createServer(async(req,res)=>{
 try{
  const uri=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const path=resolve(root,'.'+(uri==='/'?'/index.html':uri));
  if(!path.startsWith(root+'/')){res.writeHead(403);res.end();return}
  const bytes=await readFile(path);
  res.writeHead(200,{'Content-Type':types[extname(path)]||'application/octet-stream','Cache-Control':'no-store'});
  res.end(bytes);
 }catch{res.writeHead(404);res.end('missing')}
});
await new Promise(ok=>server.listen(0,'127.0.0.1',ok));
await mkdir('_freestanding-b-previews',{recursive:true});
const origin='http://127.0.0.1:'+server.address().port;
const filters=['commuter','metro','tram','nockeby','lidingo','city7','roslags','saltsjo',
 'arlanda','sj','vr','snalltaget','vy','tagab','rdc','malartag'];
const epoch=Date.parse('2026-11-16T08:30:00+01:00')/1000;
const active=activeRailTrips(source,epoch,10000);
for(const mode of ['roslags','saltsjo'])assert(active.filter(t=>matchesRailFilter(t,mode)).length>0,mode+' has no test trains');
let browser;
try{
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 for(const viewport of [{width:1440,height:900},{width:390,height:844}]){
  const context=await browser.newContext({viewport});
  await context.addInitScript(date=>{
   const old=Date.now.bind(Date);const delta=date-old();Date.now=()=>old()+delta;
  },epoch*1000);
  const page=await context.newPage();
  const pageErrors=[];
  page.on('pageerror',error=>pageErrors.push(String(error)));
  const response=await page.goto(origin+'/',{waitUntil:'domcontentloaded',timeout:90000});
  assert.equal(response.status(),200);
  assert.equal(await page.title(),'Stockholm Rail');
  await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:90000});
  for(const mode of filters){
   const curr=await page.locator('[data-carousel-position="current"]').getAttribute('data-filter');
   assert.equal(curr,mode);
   const expected=active.filter(t=>matchesRailFilter(t,mode)).length;
   await page.waitForFunction(n=>document.querySelectorAll('#vehicle-list button.vehicle').length===n,expected,{timeout:60000});
   await page.waitForFunction(n=>document.querySelectorAll('.leaflet-marker-icon').length===n,expected,{timeout:60000});
   const images=page.locator('.leaflet-marker-icon img.rail-photo-marker');
   assert.equal(await images.count(),expected,'Missing marker images for '+mode);
   const states=await images.evaluateAll(els=>els.map(el=>({
    source:el.getAttribute('src'),loaded:el.complete&&el.naturalWidth>0&&el.naturalHeight>0,
    width:el.naturalWidth,height:el.naturalHeight
   })));
   if(selectedPaths[mode]){
    assert(states.length>0,'No active '+mode+' markers to inspect');
    assert(states.every(x=>x.source===selectedPaths[mode]),'Wrong B icon assigned to '+mode);
    assert(states.every(x=>x.loaded&&x.width===48&&x.height===48),'Transparent train marker failed to decode for '+mode);

    // The missing test in STABLE27: opaque image-tile pixels must NOT be
    // visible. Assert real decoded ALPHA at the four corners, the two sides,
    // and visible foreground in the train's nose via browser Canvas.
    const pixels=await images.first().evaluate(img=>{
      const c=document.createElement('canvas');c.width=48;c.height=48;
      const ctx=c.getContext('2d');ctx.drawImage(img,0,0,48,48);
      const alpha=(x,y)=>ctx.getImageData(x,y,1,1).data[3];
      return {corners:[[0,0],[47,0],[0,47],[47,47],[0,24],[24,0]].map(([x,y])=>alpha(x,y)),
        center:alpha(24,25),
        cssWidth:parseFloat(getComputedStyle(img).width),
        cssHeight:parseFloat(getComputedStyle(img).height)};
    });
    assert(pixels.corners.every(x=>x===0),
      'FAILED: user sees the old white/dark rectangular image tile, not a train silhouette: '+JSON.stringify(pixels));
    assert(pixels.center>=200,'Train silhouette unexpectedly removed '+JSON.stringify(pixels));
    assert.equal(pixels.cssWidth,19,'Unselected map icon larger/different than other trains');
    assert.equal(pixels.cssHeight,19,'Unselected map icon height wrong');
    console.log('ACTUAL MAP PIXELS',viewport.width,mode,'transparent corners',pixels.corners,'train alpha',pixels.center);
    const lines=new Set(active.filter(t=>matchesRailFilter(t,mode)).map(t=>String(t.line)));
    assert([...lines].every(l=>mode==='roslags'?['27','28','29'].includes(l):['25','26'].includes(l)));
    console.log('FREE-STANDING B ORIGINAL TRAIN RENDERED',viewport.width,mode,expected,'train icons for lines',JSON.stringify([...lines]));
    await page.screenshot({path:'_freestanding-b-previews/'+mode+'-'+viewport.width+'.png',fullPage:true});
   }else{
    assert(states.every(x=>!Object.values(selectedPaths).includes(x.source)),
      'Accidentally modified unrelated '+mode+' markers');
    // Baseline operators and their original asset loading are unchanged byte-for-byte.
    // Loading quality is strictly asserted for the two B icons above.
   }
   await page.locator('#rail-next').click();
  }
  assert.equal(await page.locator('[data-carousel-position="current"]').getAttribute('data-filter'),'commuter','Slide did not wrap');
  await page.locator('.all-trains-button').click();
  await page.waitForFunction(n=>document.querySelectorAll('.leaflet-marker-icon').length===n,active.length,{timeout:90000});
  const all=await page.locator('.leaflet-marker-icon img.rail-photo-marker').evaluateAll(els=>
   els.map(img=>({src:img.getAttribute('src'),loaded:img.complete&&img.naturalWidth>0})));
  assert.equal(all.length,active.length);
  assert(all.every(x=>x.loaded),'All trains includes broken marker');
  assert.equal(all.filter(x=>x.src===selectedPaths.roslags).length,active.filter(t=>matchesRailFilter(t,'roslags')).length);
  assert.equal(all.filter(x=>x.src===selectedPaths.saltsjo).length,active.filter(t=>matchesRailFilter(t,'saltsjo')).length);
  console.log('ALL TRAINS EXACT ORIGINAL COUNT',viewport.width,active.length);
  // Selection and follow keep both the unchanged map route and the B icon.
  for(const mode of ['roslags','saltsjo']){
   for(let nav=0;nav<=filters.length;nav++){
    if(await page.locator('[data-carousel-position="current"]').getAttribute('data-filter')===mode)break;
    await page.locator('#rail-next').click();
   }
   await page.locator('[data-carousel-position="current"]').click();
   await page.waitForFunction(n=>document.querySelectorAll('#vehicle-list button.vehicle').length===n,
    active.filter(t=>matchesRailFilter(t,mode)).length,{timeout:60000});
   await page.locator('#vehicle-list button.vehicle').first().click();
   await page.locator('#selected-detail').waitFor({state:'visible'});
   await page.waitForFunction(()=>document.querySelectorAll('.leaflet-marker-icon.is-selected img.rail-photo-marker').length===1,
    null,{timeout:60000});
   const sel=await page.locator('.leaflet-marker-icon.is-selected img.rail-photo-marker').first().getAttribute('src');
   assert.equal(sel,selectedPaths[mode],'Selected train lost its original B icon');
   const selectedPixels=await page.locator('.leaflet-marker-icon.is-selected img.rail-photo-marker').first().evaluate(img=>{
     const c=document.createElement('canvas');c.width=48;c.height=48;const ctx=c.getContext('2d');ctx.drawImage(img,0,0,48,48);
     return {a:ctx.getImageData(0,0,1,1).data[3],width:parseFloat(getComputedStyle(img).width)};
   });
   assert.equal(selectedPixels.a,0,'Selected train has an opaque corner/background');
   assert.equal(selectedPixels.width,27,'Selected train must keep original 27px map size');

   assert(await page.locator('#stops .stop').count()>=2);
   await page.locator('#follow').click();
   assert((await page.locator('#follow').textContent()).includes('Följer'));
   await page.locator('#clear').click();
   await page.locator('#selected-detail').waitFor({state:'hidden'});
   console.log('FOLLOW AND DETAIL PRESERVED',viewport.width,mode);
  }
  assert.deepEqual(pageErrors,[],'Browser JavaScript errors');
  await context.close();
 }
 // Check authentic original GTFS coverage for ALL FIVE lines, not just current vehicles.
 const seen=new Set();
 const groups=['25','26','27','28','29'];
 for(let day=9;day<=15;day++){
  for(let h=0;h<24;h++){
   const instant=Date.parse('2026-11-'+String(day).padStart(2,'0')+
    'T'+String(h).padStart(2,'0')+':30:00+01:00')/1000;
   const trains=activeRailTrips(source,instant,10000);
   for(const t of trains)if(groups.includes(String(t.line)))seen.add(String(t.line));
  }
 }
 assert.deepEqual([...seen].sort(),[...groups].sort(),'Missing historical service for an affected line');
 console.log('ALL FIVE GTFS LINES OBSERVED ON SOURCE SCHEDULE',JSON.stringify([...seen].sort()));
}finally{
 await browser?.close();server.close();
}
