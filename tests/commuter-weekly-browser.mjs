import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createServer} from 'node:http';
import {resolve,join,extname} from 'node:path';
import {chromium} from 'playwright';
import {activeRailTrips} from '../website/src/rail-data.js';

const root=resolve('website');
const d=JSON.parse(await readFile(join(root,'data/rail.json'),'utf8'));
assert.equal(d.commuterWeekdaySimulation,true);
const mime={'.html':'text/html','.css':'text/css','.js':'text/javascript','.json':'application/json',
 '.webp':'image/webp','.png':'image/png','.jpg':'image/jpeg','.svg':'image/svg+xml'};
const server=createServer(async(req,res)=>{
 try {
  const uri=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const file=resolve(root,'.'+(uri==='/'?'/index.html':uri));
  if(!file.startsWith(root+'/')){res.writeHead(403);res.end();return}
  const b=await readFile(file);
  res.writeHead(200,{'Content-Type':mime[extname(file)]||'application/octet-stream','Cache-Control':'no-store'});
  res.end(b);
 }catch(e){res.writeHead(404);res.end('missing')}
});
await new Promise(ok=>server.listen(0,'127.0.0.1',ok));
let browser;
try{
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 const times=['2026-11-13T08:30:00+01:00','2026-11-14T00:30:00+01:00',
  '2026-11-14T12:30:00+01:00','2026-11-15T12:30:00+01:00',
  '2026-11-16T08:30:00+01:00','2026-11-16T19:30:00+01:00'];
 for(const stamp of times){
  const epoch=Date.parse(stamp)/1000;
  for(const [mode,filter] of [['commuter','commuter'],['metro','metro']]){
   const expected=activeRailTrips(d,epoch,20000).filter(t=>t.mode===mode).length;
   if(expected===0)continue; // never create a train when no genuine schedule.
   const context=await browser.newContext({viewport:{width:1500,height:900}});
   await context.addInitScript(time=>{const clock=Date.now.bind(Date),delta=time-clock();Date.now=()=>clock()+delta},epoch*1000);
   const page=await context.newPage();const errors=[];
   page.on('pageerror',e=>errors.push(String(e)));
   const response=await page.goto('http://127.0.0.1:'+server.address().port+'/',{waitUntil:'domcontentloaded',timeout:90000});
   assert.equal(response.status(),200);
   await page.locator('[data-filter="'+filter+'"]').click();
   await page.waitForFunction(n=>document.querySelectorAll('#vehicle-list button.vehicle').length===n,expected,{timeout:90000});
   await page.waitForFunction(n=>document.querySelectorAll('.leaflet-marker-icon').length===n,expected,{timeout:30000});
   assert.deepEqual(errors,[]);
   console.log('BROWSER',mode,stamp,'list',expected,'markers',expected);
   await context.close();
  }
 }
}finally{await browser?.close();server.close()}
