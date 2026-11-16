import assert from 'node:assert/strict';
import {readFile,mkdir} from 'node:fs/promises';
import {createServer} from 'node:http';
import {resolve,join,extname} from 'node:path';
import {chromium} from 'playwright';
import {activeRailTrips} from '../website/src/rail-data.js';
import {matchesRailFilter} from '../website/src/rail-filter.js';

const root=resolve('website');
const data=JSON.parse(await readFile(join(root,'data/rail.json'),'utf8'));
assert.equal(data.trips.length,10827,'Design must retain the exact pre-edit STABLE21 timetable');
const types={'.html':'text/html','.css':'text/css','.js':'text/javascript','.json':'application/json',
 '.webp':'image/webp','.png':'image/png','.jpg':'image/jpeg','.svg':'image/svg+xml'};
const server=createServer(async(req,res)=>{
 try{
  const path=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const name=resolve(root,'.'+(path==='/'?'/index.html':path));
  if(!name.startsWith(root+'/')){res.writeHead(403);res.end();return}
  const bytes=await readFile(name);
  res.writeHead(200,{'Content-Type':types[extname(name)]||'application/octet-stream','Cache-Control':'no-store'});
  res.end(bytes);
 }catch(e){res.writeHead(404);res.end('missing')}
});
await new Promise(ok=>server.listen(0,'127.0.0.1',ok));
await mkdir('_design_preview',{recursive:true});
const url='http://127.0.0.1:'+server.address().port+'/';
const stamp='2026-11-16T08:30:00+01:00',epoch=Date.parse(stamp)/1000;
const scheduled=activeRailTrips(data,epoch,10000);
const filters=['commuter','metro','tram','nockeby','lidingo','city7','roslags','saltsjo','arlanda','sj','vr','snalltaget','vy','tagab','rdc','malartag'];
async function waitForCount(page,filter){
 const n=scheduled.filter(t=>matchesRailFilter(t,filter)).length;
 await page.waitForFunction(n=>(document.querySelectorAll('#vehicle-list button.vehicle').length===n),
  n,{timeout:60000});
 await page.waitForFunction(n=>(document.querySelectorAll('.leaflet-marker-icon').length===n),
  n,{timeout:60000});
 return n;
}
async function verifyNoControlOverlap(page){
 const a=await page.locator('#home').boundingBox();
 const b=await page.locator('.leaflet-control-zoom').boundingBox();
 const c=await page.locator('#satellite').boundingBox();
 assert(a&&b&&c,'Map controls must be visible');
 const intersect=(x,y)=>Math.max(0,Math.min(x.x+x.width,y.x+y.width)-Math.max(x.x,y.x))*
 Math.max(0,Math.min(x.y+x.height,y.y+y.height)-Math.max(x.y,y.y));
 assert.equal(intersect(a,b),0,'Översikt overlaps + / -');
 assert.equal(intersect(b,c),0,'Zoom overlaps Satellite');
}
let browser;
try{
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 for(const viewport of [{width:1440,height:900},{width:390,height:844}]){
  const context=await browser.newContext({viewport});
  await context.addInitScript(time=>{
   const raw=Date.now.bind(Date),delta=time-raw();Date.now=()=>raw()+delta;
  },epoch*1000);
  const page=await context.newPage(),exceptions=[];
  page.on('pageerror',err=>exceptions.push(String(err)));
  await page.goto(url,{waitUntil:'domcontentloaded',timeout:90000});
  await page.waitForFunction(()=>document.querySelectorAll('#vehicle-list button.vehicle').length>0,null,{timeout:90000});
  assert.equal(await page.locator('header.topbar').count(),0,'Large top banner must be gone');
  assert.equal(await page.locator('#map-info').isHidden(),true,'Info initially hidden');
  assert.equal(await page.locator('[data-carousel-position="current"]').count(),1);
  assert.equal(await page.locator('[data-carousel-position="prev"]').count(),1);
  assert.equal(await page.locator('[data-carousel-position="next"]').count(),1);
  await verifyNoControlOverlap(page);
  await page.locator('#info-toggle').click();
  await page.locator('#map-info').waitFor({state:'visible'});
  assert((await page.locator('#map-info').textContent()).includes('PENDELTÅG'));
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('#map-info').isHidden(),true);
  console.log('HELP AND CONTROLS',viewport.width,'PASS');

  // The 16 central slides form an actual endlessly wrapping interaction.
  for(let i=0;i<filters.length;i++){
   const filter=filters[i];
   assert.equal(await page.locator('[data-carousel-position="current"]').getAttribute('data-filter'),filter);
   const actual=await waitForCount(page,filter);
   console.log('SLIDER AND MARKERS',viewport.width,filter,actual);
   await page.locator('#rail-next').click();
  }
  assert.equal(await page.locator('[data-carousel-position="current"]').getAttribute('data-filter'),'commuter','Infinite slide did not wrap to first');
  await waitForCount(page,'commuter');

  await page.locator('.all-trains-button').click();
  const total=await waitForCount(page,'all');
  assert.equal(total,scheduled.length);
  console.log('ALL TRAINS',viewport.width,total);
  await page.locator('[data-carousel-position="current"]').click();
  await waitForCount(page,'commuter');
  // The map must contain true vehicle positions, never fabricated lines.
  await page.waitForTimeout(1150);
  const mapArea=await page.locator('#map').boundingBox();
  const inside=await page.locator('.leaflet-marker-icon').evaluateAll((els,box)=>
   els.filter(el=>{
    const r=el.getBoundingClientRect();
    return r.right>=box.x-15&&r.left<=box.x+box.width+15&&r.bottom>=box.y-15&&r.top<=box.y+box.height+15;
   }).length,mapArea);
  assert(inside>0,'Framing did not show active filtered vehicles');

  await page.screenshot({path:'_design_preview/'+(viewport.width<500?'mobile':'desktop')+'-map.png',fullPage:true});
  await page.locator('#vehicle-list button.vehicle').first().click();
  await page.locator('#selected-detail').waitFor({state:'visible'});
  assert((await page.locator('#stops .stop').count())>=2,'Station timeline missing');
  assert.equal(await page.locator('#stops .stop.next').count(),1);
  const stopStyles=await page.locator('#stops').evaluate(el=>({
   maxHeight:getComputedStyle(el).maxHeight,overflow:getComputedStyle(el).overflowY
  }));
  assert.equal(stopStyles.overflow,'auto');
  assert.equal(stopStyles.overflow,'auto');
  await page.locator('#follow').click();
  assert((await page.locator('#follow').textContent()).includes('Följer'));
  const subdued=await page.locator('.leaflet-marker-icon:not(.is-selected)').first().evaluate(el=>getComputedStyle(el).opacity);
  assert(Number(subdued)>=.60,'Unselected vehicles too faint: '+subdued);
  await page.screenshot({path:'_design_preview/'+(viewport.width<500?'mobile':'desktop')+'-detail.png',fullPage:true});
  await page.locator('#clear').click();
  await page.locator('#selected-detail').waitFor({state:'hidden'});
  await page.locator('#satellite').click();
  assert((await page.locator('#satellite').textContent()).includes('Karta'),'Satellite button did not switch');
  await page.locator('#home').click();
  assert.deepEqual(exceptions,[],'Browser JS exception');
  console.log('DETAILS FOLLOW MOBILE SATELLITE',viewport.width,'PASS');
  await context.close();
 }
} finally {
 await browser?.close();server.close();
}
