/**
 * STABLE32 — REAL Chromium basemap regression.
 * Three basemaps must work on the unchanged Stockholm Rail Leaflet map.
 * This test also proves that changing imagery never removes a scheduled train,
 * changes its stop timeline, marker, selection, or the selected verified route.
 */
import assert from 'node:assert/strict';
import {readFile,mkdir} from 'node:fs/promises';
import {createServer} from 'node:http';
import {resolve,join,extname} from 'node:path';
import {chromium} from 'playwright';
import {activeRailTrips} from '../_release/website/src/rail-data.js';
import {matchesRailFilter} from '../_release/website/src/rail-filter.js';

const root=resolve('_release/website');
const data=JSON.parse(await readFile(join(root,'data/rail.json'),'utf8'));
assert.equal(data.metroWeekdaySimulation,true);
assert.equal(data.commuterWeekdaySimulation,true);
assert.equal(data.localWeekdaySimulation,true);
assert.equal(data.arlandaWeekdaySimulation,true);
assert.equal(data.counts.metro,13372);
assert.equal(data.counts.express,1240);

const mime={'.html':'text/html','.css':'text/css','.js':'text/javascript','.json':'application/json',
 '.webp':'image/webp','.png':'image/png','.jpg':'image/jpeg','.svg':'image/svg+xml'};
const server=createServer(async(request,response)=>{
 try{
  const pathname=decodeURIComponent(new URL(request.url,'http://localhost').pathname);
  const file=resolve(root,'.'+(pathname==='/'?'/index.html':pathname));
  if(!file.startsWith(root+'/')){response.writeHead(403);response.end();return;}
  const bytes=await readFile(file);
  response.writeHead(200,{'Content-Type':mime[extname(file)]||'application/octet-stream',
   'Cache-Control':'no-store'});response.end(bytes);
 }catch(error){response.writeHead(404);response.end('not found')}
});
const publicUrl=process.env.STABLE32_TEST_URL;
if(!publicUrl)await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const url=publicUrl||'http://127.0.0.1:'+server.address().port+'/';
const shots=process.env.STABLE32_SHOTS||'_release/qa-map-styles';
await mkdir(shots,{recursive:true});
const time='2026-11-18T09:47:00+01:00';
const epoch=Date.parse(time)/1000;
const expectedCommuter=activeRailTrips(data,epoch,20000).filter(v=>matchesRailFilter(v,'commuter')).length;
assert(expectedCommuter>0,'Historical Pendeltåg fixture must have trains');
const browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});

async function loadedPane(page,pane){
 await page.waitForFunction(name=>{
  const images=[...document.querySelectorAll('.leaflet-'+name+'-pane img.leaflet-tile')];
  return images.length>0&&images.some(img=>img.complete&&img.naturalWidth>0&&img.classList.contains('leaflet-tile-loaded'));
 },pane,{timeout:60000});
}
async function mode(page,style){
 await page.locator('#satellite').click();
 await page.locator('#basemap-menu').waitFor({state:'visible'});
 assert.equal(await page.locator('#basemap-menu [data-basemap]').count(),3);
 await page.locator('[data-basemap="'+style+'"]').click();
 assert.equal(await page.locator('#basemap-menu').isHidden(),true);
 assert.equal(await page.locator('[data-basemap="'+style+'"]').getAttribute('aria-pressed'),'true');
 assert.equal(await page.locator('#basemap-current-label').innerText(),{standard:'Karta',satellite:'Satellit',hybrid:'Hybrid'}[style]);
 await loadedPane(page,'tile');
 if(style!=='standard'){
  // Ensure the satellite image is actually fetched and visible.
  await page.waitForFunction(()=>[...document.querySelectorAll('.leaflet-tile-pane img.leaflet-tile-loaded')].some(img=>img.src.includes('World_Imagery')&&img.naturalWidth>0),null,{timeout:60000});
 }
 if(style==='hybrid'){
  // Both genuine TRANSPARENT reference services must load, not just a fake
  // "hybrid" toggle that relabels the same satellite photo.
  await loadedPane(page,'sr-hybrid-transport');
  await loadedPane(page,'sr-hybrid-labels');
  const layers=await page.evaluate(()=>{
   const p=name=>document.querySelector('.leaflet-'+name+'-pane');
   return {
    imagery:p('tile').querySelectorAll('img[src*="World_Imagery"]').length,
    roads:p('sr-hybrid-transport').querySelectorAll('img[src*="World_Transportation"]').length,
    labels:p('sr-hybrid-labels').querySelectorAll('img[src*="World_Boundaries_and_Places"]').length,
    roadZ:parseInt(p('sr-hybrid-transport').style.zIndex,10),
    labelZ:parseInt(p('sr-hybrid-labels').style.zIndex,10),
    overlayZ:parseInt(p('overlay').style.zIndex,10)||400,
    markerZ:parseInt(p('marker').style.zIndex,10)||600,
   };
  });
  assert(layers.imagery>0&&layers.roads>0&&layers.labels>0,
   'Hybrid needs THREE different genuine tile sources');
  assert(layers.roadZ>200&&layers.labelZ>layers.roadZ);
  assert(layers.roadZ<layers.overlayZ&&layers.labelZ<layers.markerZ);
  console.log('HYBRID THREE DISTINCT REAL LAYERS',JSON.stringify(layers));
 }else{
  assert.equal(await page.locator('.leaflet-sr-hybrid-transport-pane img').count(),0,
   'Hybrid road reference must not leak into non-hybrid map');
  assert.equal(await page.locator('.leaflet-sr-hybrid-labels-pane img').count(),0,
   'Hybrid label reference must not leak into non-hybrid map');
 }
}

try{
 for(const [device,viewport] of [
  ['desktop',{width:1550,height:900}],
  ['mobile',{width:390,height:844}],
 ]){
  const context=await browser.newContext({viewport,deviceScaleFactor:1});
  await context.addInitScript(time=>{
   const real=Date.now.bind(Date),offset=time-real();
   Date.now=()=>real()+offset;
  },epoch*1000);
  const page=await context.newPage();
  const errors=[];
  page.on('pageerror',err=>errors.push(String(err)));
  const response=await page.goto(url,{waitUntil:'domcontentloaded',timeout:120000});
  assert.equal(response.status(),200);
  assert.equal(await page.title(),'Stockholm Rail');
  await page.waitForFunction(n=>document.querySelectorAll('#vehicle-list button.vehicle').length===n,
   expectedCommuter,{timeout:120000});
  await page.waitForFunction(n=>document.querySelectorAll('.leaflet-marker-icon').length===n,
   expectedCommuter,{timeout:120000});
  await page.waitForTimeout(1100);
  // Preserve selected train detail and path across switches.
  await page.locator('#vehicle-list button.vehicle').first().click();
  await page.locator('#selected-detail').waitFor({state:'visible',timeout:10000});
  const originalHeading=await page.locator('#train-heading').innerText();
  const originalStops=await page.locator('#stops .stop').allTextContents();
  assert(originalHeading.length>0&&originalStops.length>=2);
  const count=await page.locator('.leaflet-marker-icon').count();
  assert.equal(count,expectedCommuter);
  assert.equal(await page.locator('[data-basemap]').count(),3);
  await mode(page,'standard');
  await page.screenshot({path:shots+'/'+device+'-1-map.png',fullPage:true});
  await mode(page,'satellite');
  await page.screenshot({path:shots+'/'+device+'-2-satellite.png',fullPage:true});
  await mode(page,'hybrid');
  await page.waitForTimeout(600);
  await page.screenshot({path:shots+'/'+device+'-3-hybrid-road-rail-labels.png',fullPage:true});

  assert.equal(await page.locator('.leaflet-marker-icon').count(),count,
   'Changing basemap must not remove scheduled vehicles');
  assert.equal(await page.locator('#train-heading').innerText(),originalHeading,
   'Map style accidentally deselected current train');
  assert.deepEqual(await page.locator('#stops .stop').allTextContents(),originalStops,
   'Map style modified the selected train station list');
  assert.equal(await page.locator('#selected-detail').isVisible(),true);
  assert.equal(await page.locator('#basemap-warning').isHidden(),true,
   'Hybrid labels/rail overlay did not load normally');

  // Choice is keyboard-accessible, escapes without changing selected view.
  await page.locator('#satellite').click();
  assert.equal(await page.locator('#basemap-menu').isVisible(),true);
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('#basemap-menu').isHidden(),true);
  assert.equal(await page.locator('#basemap-current-label').innerText(),'Hybrid');

  // Map choice persists on reload; layout, markers, photos still load.
  await page.reload({waitUntil:'domcontentloaded',timeout:120000});
  await page.waitForFunction(n=>document.querySelectorAll('.leaflet-marker-icon').length===n,
   expectedCommuter,{timeout:120000});
  assert.equal(await page.locator('#basemap-current-label').innerText(),'Hybrid');
  await loadedPane(page,'sr-hybrid-transport');
  await loadedPane(page,'sr-hybrid-labels');
  await mode(page,'standard');

  assert.deepEqual(errors,[],'No script failures during real layer switching: '+device);
  console.log('STABLE32 THREE MAP STYLES CHROMIUM PASS',device,
   'three tile sources, '+count+' vehicles identical, selected train path and history preserved, keyboard and reload passed');
  await context.close();
 }
 console.log('STABLE32 ALL REAL TILE HYBRID/SATELLITE/MAP REGRESSIONS PASS');
}finally{
 await browser.close();
 if(!publicUrl)server.close();
}
