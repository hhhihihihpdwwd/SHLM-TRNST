// Real published Stockholm Rail browser verification for each of the
// FIFTEEN other railway systems at fixed 10:53 Swedish local time.
import assert from 'node:assert/strict';
import {chromium} from 'playwright';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {activeRailTrips} from '../_stable29/website/src/rail-data.js';
import {matchesRailFilter} from '../_stable29/website/src/rail-filter.js';

const d=JSON.parse(await readFile('_stable29/website/data/rail.json','utf8'));
const at='2026-11-18T10:53:22+01:00',epoch=Date.parse(at)/1000;
const all=activeRailTrips(d,epoch,30000);
const names=['commuter','tram','nockeby','lidingo','city7','roslags','saltsjo',
 'arlanda','sj','malartag','vr','snalltaget','vy','tagab','rdc'];
const browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
const website='https://hhhihihihpdwwd.github.io/SHLM-TRNST/';
const results=[];
try{
 for(const viewport of [{width:1600,height:900},{width:390,height:844}]){
  const ctx=await browser.newContext({viewport,deviceScaleFactor:1});
  await ctx.addInitScript(time=>{const real=Date.now.bind(Date),delta=time-real();Date.now=()=>real()+delta;},epoch*1000);
  const page=await ctx.newPage();
  const exceptions=[],failedRequests=[];
  page.on('pageerror',e=>exceptions.push(String(e)));
  page.on('requestfailed',req=>{if(/(rail\.json|app\.js|rail-data\.js|design-ui\.js)/.test(req.url()))failedRequests.push(req.url());});
  const response=await page.goto(website+'?readonly-15-systems-audit-20261118',{waitUntil:'domcontentloaded',timeout:120000});
  assert.equal(response.status(),200);
  assert.equal(await page.title(),'Stockholm Rail');
  await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:120000});
  const select=async(filter)=>{
   for(let n=0;n<20;n++){
    const cur=await page.locator('[data-carousel-position="current"]').getAttribute('data-filter');
    if(cur===filter)break;
    await page.locator('#rail-next').click();
   }
   assert.equal(await page.locator('[data-carousel-position="current"]').getAttribute('data-filter'),filter);
   await page.locator('[data-carousel-position="current"]').click();
   const expected=all.filter(v=>matchesRailFilter(v,filter)).length;
   await page.waitForFunction(n=>document.querySelectorAll('#vehicle-list button.vehicle').length===n,
      expected,{timeout:90000});
   await page.waitForFunction(n=>document.querySelectorAll('.leaflet-marker-icon').length===n,
      expected,{timeout:90000});
   // The legacy tram/metro symbols use inline preloaded assets; local rail
   // symbols resolve asynchronously. Wait for image decoding before treating a
   // transient naturalWidth=0 as a broken image.
   if(expected>0){
    await page.waitForFunction(()=>{
      const imgs=[...document.querySelectorAll('.leaflet-marker-icon img')];
      return imgs.length>0 && imgs.every(img=>img.complete && img.naturalWidth>0);
    },null,{timeout:30000});
   }
   const result=await page.evaluate(()=>{
    const elements=[...document.querySelectorAll('.leaflet-marker-icon')];
    const map=document.querySelector('#map').getBoundingClientRect();
    const onscreen=elements.filter(el=>{
      const r=el.getBoundingClientRect();
      return r.right>=map.left&&r.left<=map.right&&r.bottom>=map.top&&r.top<=map.bottom;
    }).length;
    const imgs=[...document.querySelectorAll('.leaflet-marker-icon img')];
    return {list:document.querySelectorAll('#vehicle-list button.vehicle').length,
     markers:elements.length,onscreen,
     loadedImages:imgs.filter(img=>img.complete&&img.naturalWidth>0).length,
     imageCount:imgs.length,
     sourceLink:document.querySelector('title')?.textContent};
   });
   assert.equal(result.list,expected,'List dropped train '+filter);
   assert.equal(result.markers,expected,'Leaflet dropped train '+filter);
   if(expected>0){
    assert.equal(result.loadedImages,result.imageCount,'One or more marker images unloaded '+filter);
   }
   return {...result,expected};
  };
  for(const filter of names){
   const result=await select(filter);
   results.push({device:viewport.width>500?'desktop':'mobile',filter,...result});
   console.log('PUBLIC CHROMIUM 15 OTHER SYSTEMS',viewport.width,filter,
     'GTFS',result.expected,'LIST',result.list,'MARKERS',result.markers,
     'VISIBLE_ONSCREEN',result.onscreen,'MARKER_IMAGES',result.loadedImages+'/'+result.imageCount);
   if(filter==='commuter'||filter==='roslags'||filter==='saltsjo'||filter==='malartag'||filter==='sj'||filter==='arlanda'){
    await page.screenshot({path:'_audit_15/'+(viewport.width>500?'desktop':'mobile')+'-'+filter+'.png',fullPage:true});
   }
  }
  await page.locator('.all-trains-button').click();
  await page.waitForFunction(n=>document.querySelectorAll('.leaflet-marker-icon').length===n,
      all.length,{timeout:90000});
  assert.deepEqual(exceptions,[],'Browser JavaScript exceptions');
  assert.deepEqual(failedRequests,[],'Failed GTFS or app script downloads');
  await ctx.close();
 }
 await writeFile('_audit_15/public-browser-all-systems.json',JSON.stringify({timestamp:at,results},null,2));
 console.log('COMPLETE ONLINE BROWSER AUDIT: 15 FILTERS × DESKTOP + MOBILE (30/30), EXACT SOURCE-TO-RENDER COMPARISON, NO WEBSITE MODIFICATIONS');
}finally{await browser.close()}
