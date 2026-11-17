import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createServer} from 'node:http';
import {resolve,extname} from 'node:path';
import {chromium} from 'playwright';
import {activeRailTrips} from '../website/src/rail-data.js';
import {matchesRailFilter} from '../website/src/rail-filter.js';
import {updatedThreeTrainMarkers} from '../website/src/updated-train-markers.js';

const root=resolve('website');
const dataset=JSON.parse(await readFile(root+'/data/rail.json','utf8'));
assert.equal(dataset.trips.length,10827);
assert.equal(Object.keys(dataset.shapes).length,107);
const catalog=JSON.parse(await readFile(root+'/photos/catalog.json','utf8'));
const approved=JSON.parse(await readFile(root+'/photos/approved.json','utf8'));
const names=['metro_c20_green','rail_rdc_euronight','rail_oresund'];
const photos=names.map(key=>({key,...catalog[key]}));
for(const p of photos){
 assert(p.originalPhoto===true,'Never supply AI photo under '+p.key);
 assert(p.path.endsWith('.webp')&&p.path.includes('_near'));
 assert(p.license.startsWith('CC BY'));
 assert(p.source.startsWith('https://commons.wikimedia.org/wiki/File:'));
 assert(approved[p.key].path===p.path);
}
for(const name of ['rdc','malartag','tagab']){
 assert(updatedThreeTrainMarkers[name].startsWith('data:image/webp;base64,'));
 const raw=Buffer.from(updatedThreeTrainMarkers[name].split(',')[1],'base64');
 assert(raw.length>1500&&raw.toString('ascii',0,4)==='RIFF');
}
const types={'.html':'text/html','.css':'text/css','.js':'text/javascript','.json':'application/json',
 '.webp':'image/webp','.png':'image/png','.jpg':'image/jpeg','.svg':'image/svg+xml'};
const server=createServer(async(req,res)=>{
 try{
  const path=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const filename=resolve(root,'.'+(path==='/'?'/index.html':path));
  if(!filename.startsWith(root+'/')){res.writeHead(403);res.end();return}
  const bytes=await readFile(filename);
  res.writeHead(200,{'Content-Type':types[extname(filename)]||'application/octet-stream','Cache-Control':'no-store'});
  res.end(bytes);
 }catch{res.writeHead(404);res.end('not found')}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const origin='http://127.0.0.1:'+server.address().port;
const baseline=Date.parse('2026-11-16T08:30:00+01:00')/1000;
const filters=['commuter','metro','tram','nockeby','lidingo','city7','roslags','saltsjo',
 'arlanda','sj','vr','snalltaget','vy','tagab','rdc','malartag'];
let browser;
try{
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 for(const viewport of [{width:1440,height:900},{width:390,height:844}]){
  const context=await browser.newContext({viewport});
  await context.addInitScript(time=>{const old=Date.now.bind(Date),delta=time-old();Date.now=()=>old()+delta},baseline*1000);
  const page=await context.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  await page.goto(origin+'/',{waitUntil:'domcontentloaded',timeout:90000});
  assert.equal(await page.title(),'Stockholm Rail');
  await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0);
  for(const mode of filters){
   const expected=activeRailTrips(dataset,baseline,10000).filter(t=>matchesRailFilter(t,mode)).length;
   await page.locator('[data-filter="'+mode+'"]').click();
   await page.waitForFunction(count=>document.querySelectorAll('#vehicle-list button.vehicle').length===count,expected,{timeout:45000});
   await page.waitForFunction(count=>document.querySelectorAll('.leaflet-marker-icon').length===count,expected,{timeout:45000});
   if(['malartag','rdc','tagab'].includes(mode)&&expected>0){
    const markerImages=page.locator('.leaflet-marker-icon img.rail-photo-marker');
    assert.equal(await markerImages.count(),expected);
    const expected3d=updatedThreeTrainMarkers[mode];
    const actual=await markerImages.first().getAttribute('src');
    assert.equal(actual,expected3d,'Incorrect '+mode+' 3D marker rendering');
    const decoded=await markerImages.first().evaluate(img=>img.complete&&img.naturalWidth>0&&img.naturalHeight>0);
    assert(decoded,'3D marker image did not decode: '+mode);
    console.log('REAL CHROMIUM 3D RENDERED',viewport.width,mode,expected);
   }
   console.log('ALL-SYSTEM MARKER REGRESSION',viewport.width,mode,expected);
  }
  await page.locator('[data-filter="all"]').click();
  const total=activeRailTrips(dataset,baseline,10000).length;
  await page.waitForFunction(count=>document.querySelectorAll('.leaflet-marker-icon').length===count,total,{timeout:60000});
  for(const photo of photos){
   const request=await page.request.get(origin+'/'+photo.path);
   assert(request.ok(),'Real source photo missing: '+photo.path);
   assert(request.headers()['content-type']==='image/webp');
   const result=await page.evaluate(async source=>{
    const img=new Image();img.src=source;
    await img.decode();
    return {width:img.naturalWidth,height:img.naturalHeight};
   },origin+'/'+photo.path);
   assert.equal(result.width,640);
   assert.equal(result.height,400);
   console.log('GENUINE CC PHOTO LOADED',viewport.width,photo.key,photo.author,photo.license);
  }
  assert.deepEqual(errors,[],'Browser errors');
  await context.close();
 }
 // For each of the three operators, verify in browser at least one time when
 // its original GTFS service is genuinely active, rather than fabricating time.
 for(const [mode,agency] of [['malartag','Mälartåg'],['tagab','Tågab'],['rdc','RDC EuroNight']]){
  let stamp=null,count=0;
  for(let day=13;day<=19&&!stamp;day++){
   for(let h=0;h<24;h++){
    const epoch=Date.parse('2026-11-'+day+'T'+String(h).padStart(2,'0')+':30:00+01:00')/1000;
    const matching=activeRailTrips(dataset,epoch,10000).filter(t=>t.agency===agency);
    if(matching.length){stamp=epoch;count=matching.length;break}
   }
  }
  assert(stamp!==null,'No original GTFS sample to verify '+agency);
  const ctx=await browser.newContext({viewport:{width:1440,height:900}});
  await ctx.addInitScript(time=>{const old=Date.now.bind(Date),delta=time-old();Date.now=()=>old()+delta},stamp*1000);
  const page=await ctx.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  await page.goto(origin+'/',{waitUntil:'domcontentloaded',timeout:90000});
  await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:90000});
  await page.locator('[data-filter="'+mode+'"]').click();
  await page.waitForFunction(n=>document.querySelectorAll('.leaflet-marker-icon').length===n,count,{timeout:60000});
  const all=await page.locator('.leaflet-marker-icon img.rail-photo-marker').evaluateAll(els=>
    els.map(el=>({src:el.getAttribute('src'),loaded:el.complete&&el.naturalWidth>0})));
  assert.equal(all.length,count);
  assert(all.every(x=>x.src===updatedThreeTrainMarkers[mode]&&x.loaded),
    mode+' icons differ from user-approved generated 3D marker');
  assert.deepEqual(errors,[]);
  console.log('AUTHENTIC HISTORIC DEPARTURE',mode,new Date(stamp*1000).toISOString(),count,'new 3D map markers PASS');
  await ctx.close();
 }
} finally {await browser?.close();server.close()}
