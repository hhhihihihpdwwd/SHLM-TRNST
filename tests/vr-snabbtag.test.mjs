import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {matchesRailFilter,railFilterTitle} from '../src/rail-filter.js';
import {loadPhotoCatalog,photoForVehicle} from '../src/photos.js';
import {activeRailTrips,railAt} from '../src/rail-data.js';

test('VR Snabbtåg has its own filter and does not mix with SJ, Mälartåg or SL',()=>{
 const sample=[{mode:'intercity',agency:'VR Snabbtåg'},
               {mode:'intercity',agency:'SJ'},
               {mode:'regional',agency:'Mälartåg'},
               {mode:'commuter',agency:'SL'}];
 assert.deepEqual(sample.filter(x=>matchesRailFilter(x,'vr')),[sample[0]]);
 assert.deepEqual(sample.filter(x=>matchesRailFilter(x,'sj')),[sample[1]]);
 assert.deepEqual(sample.filter(x=>matchesRailFilter(x,'malartag')),[sample[2]]);
 assert.deepEqual(sample.filter(x=>matchesRailFilter(x,'all')),sample);
 assert.equal(railFilterTitle('vr'),'VR Snabbtåg');
});

test('only physical OSM verified VR routes produce renderable historical positions',()=>{
 const epoch=Date.parse('2026-11-09T09:00:00+01:00')/1000;
 const real={id:'vr-original',mode:'intercity',agency:'VR Snabbtåg',
  line:'VR',direction:'to-goteborg',shapeId:'sj-osm:21493221:reverse',
  geometryQuality:'verified-osm-relation',start:epoch-600,end:epoch+600,
  stops:[[59.4,17,'Station A',0,0],[59.35,16.95,'Station B',1200,1200]]};
 const d={shapes:{'sj-osm:21493221:reverse':[[59.4,17],[59.38,16.98],[59.35,16.95]]},
   trips:[real,{...real,id:'vr-fake',geometryQuality:'approximate-stop-connectors'},
          {...real,id:'vr-missing',shapeId:'not-real'}]};
 const active=activeRailTrips(d,epoch,100);
 assert.deepEqual(active.map(x=>x.id),['vr-original']);
 const point=railAt(active[0],epoch);
 assert(point.pos.every(Number.isFinite)&&Number.isFinite(point.kmh));
 assert(active.filter(x=>matchesRailFilter(x,'vr')).length===1);
});

test('real licensed VR X74 example photo exists as locally packaged reference',async()=>{
 const allowed=JSON.parse(readFileSync(new URL('../photos/approved.json',import.meta.url),'utf8'));
 assert.equal(allowed.rail_vr_x74.license,'CC BY-SA 4.0');
 const previous=globalThis.fetch;
 globalThis.fetch=async()=>({ok:true,json:async()=>({
  rail_vr_x74:{...allowed.rail_vr_x74,path:'photos/images/rail_vr_x74.webp'},
  rail_x2000:{...allowed.rail_x2000,path:'photos/images/rail_x2000.webp'}
 })});
 try{
  await loadPhotoCatalog();
  const photo=photoForVehicle({mode:'intercity',agency:'VR Snabbtåg',line:'VR'});
  assert.equal(photo.path,'photos/images/rail_vr_x74.webp');
  assert.equal(photo.illustrative,true);
  assert.match(photo.label,/exempelbild/);
  assert.equal(photoForVehicle({mode:'intercity',agency:'SJ'}).path,
    'photos/images/rail_x2000.webp');
 }finally{globalThis.fetch=previous;}
});

test('VR map UI exposes follow, satellite, loading estimate and preserves all existing controls',()=>{
 const app=readFileSync(new URL('../src/app.js',import.meta.url),'utf8');
 const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
 assert(html.includes('data-filter="vr"'));
 assert(html.includes('data-filter="sj"')&&html.includes('data-filter="malartag"'));
 assert(app.includes("['vr',t=>t.mode==='intercity'&&t.agency==='VR Snabbtåg']"));
 assert(app.includes('focusVrSnabbtag()'));
 assert(app.includes('focusLidingoLine()')&&app.includes('focusMalartagPilot()'));
 assert(html.includes('id="satellite"')&&html.includes('id="follow"'));
 assert(html.includes('id="speed-value"')&&html.includes('id="occupancy-value"'));
 assert(app.includes('function followFrame('));
 assert(app.includes('displayOrder(realActive.filter(v=>matchesRailFilter(v,state.filter)))'));
 assert(app.includes('Exempelbild av VR Snabbtåg X74'));
});
