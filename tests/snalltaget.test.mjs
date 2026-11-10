import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {loadPhotoCatalog,photoForVehicle} from '../src/photos.js';
import {matchesRailFilter,railFilterTitle} from '../src/rail-filter.js';
import {activeRailTrips,railAt} from '../src/rail-data.js';

test('Snälltåget isolated as 13th railway without changing SJ/VR/Mälartåg',()=>{
 const sample=[{mode:'intercity',agency:'Snälltåget'},
   {mode:'intercity',agency:'SJ'},{mode:'intercity',agency:'VR Snabbtåg'},
   {mode:'regional',agency:'Mälartåg'},{mode:'commuter',agency:'SL'}];
 assert.deepEqual(sample.filter(x=>matchesRailFilter(x,'snalltaget')),[sample[0]]);
 assert.deepEqual(sample.filter(x=>matchesRailFilter(x,'sj')),[sample[1]]);
 assert.deepEqual(sample.filter(x=>matchesRailFilter(x,'vr')),[sample[2]]);
 assert.deepEqual(sample.filter(x=>matchesRailFilter(x,'malartag')),[sample[3]]);
 assert.equal(railFilterTitle('snalltaget'),'Snälltåget');
});

test('Snälltåget only renders actual verified OSM rail relation, never approximate rail',()=>{
 const epoch=Date.parse('2026-11-09T13:50:00+01:00')/1000;
 const real={id:'snall-original',mode:'intercity',agency:'Snälltåget',line:'Snälltåget',
  direction:'to-malmo',shapeId:'sj-osm:8860632:forward',geometryQuality:'verified-osm-relation',
  start:epoch-450,end:epoch+450,stops:[[59.33,18.06,'Stockholm Centralstation',0,0],
    [59.30,18.02,'Malmö Centralstation',900,900]]};
 const data={shapes:{'sj-osm:8860632:forward':[[59.33,18.06],[59.32,18.05],[59.30,18.02]]},
  trips:[real,{...real,id:'unverified',geometryQuality:'approximate-straight-line'},
               {...real,id:'no-route',shapeId:'nonexistent'}]};
 const shown=activeRailTrips(data,epoch,100);
 assert.deepEqual(shown.map(x=>x.id),['snall-original']);
 assert(railAt(shown[0],epoch).pos.every(Number.isFinite));
});

test('licensed real Snälltåget train photo is explicitly illustrative',async()=>{
 const allowed=JSON.parse(readFileSync(new URL('../photos/approved.json',import.meta.url),'utf8'));
 assert.equal(allowed.rail_snalltaget.license,'CC BY-SA 2.0');
 const old=globalThis.fetch;
 globalThis.fetch=async()=>({ok:true,json:async()=>({
  rail_snalltaget:{...allowed.rail_snalltaget,path:'photos/images/rail_snalltaget.webp'},
  rail_x2000:{...allowed.rail_x2000,path:'photos/images/rail_x2000.webp'}
 })});
 try{
  await loadPhotoCatalog();
  const pic=photoForVehicle({mode:'intercity',agency:'Snälltåget',line:'Snälltåget'});
  assert.equal(pic.path,'photos/images/rail_snalltaget.webp');
  assert.equal(pic.illustrative,true);
  assert.equal(photoForVehicle({mode:'intercity',agency:'SJ'}).path,
    'photos/images/rail_x2000.webp');
 }finally{globalThis.fetch=old}
});

test('cache versions and all 12 old rail controls remain, new operator has distinct marker',()=>{
 const app=readFileSync(new URL('../src/app.js',import.meta.url),'utf8');
 const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
 const data=readFileSync(new URL('../src/rail-data.js',import.meta.url),'utf8');
 for(const p of ['rail-data','rail-filter','photos']){
  assert(new RegExp("from './"+p+"\\.js\\?v=(vy-01|snalltaget-01)'").test(app),'Unversioned '+p+' causes zero trains');
 }
 assert(/src="\.\/src\/app\.js\?v=(vy-01|snalltaget-01)"/.test(html));
 assert(data.includes("const TIMETABLE_URL='./data/rail.json?v=snalltaget-01';"));
 assert(html.includes('data-filter="snalltaget"'));
 for(const f of ['sj','vr','malartag','lidingo','nockeby','metro','commuter','all']){
  assert(html.includes('data-filter="'+f+'"'),f);
 }
 assert(html.includes('id="follow"')&&html.includes('id="satellite"'));
 assert(html.includes('id="speed-value"')&&html.includes('id="occupancy-value"'));
 assert(app.includes('focusSnalltaget()'));
 assert(app.includes('focusLidingoLine()'));
 assert(app.includes('focusMalartagPilot()'));
 assert(app.includes('focusVrSnabbtag()'));
 assert(app.includes("['snalltaget',t=>t.mode==='intercity'&&t.agency==='Snälltåget']"));
 assert(app.includes("if(agency==='snälltåget')return 'snalltaget'"),'Dedicated Snälltåget photo marker missing');
 assert(app.includes("if(agency==='mälartåg')return 'malartag'"),'Dedicated Mälartåg photo marker missing');
 assert(app.includes("if(agency==='vr snabbtåg')return 'vr'"),'Dedicated VR photo marker missing');
 assert(app.includes('Exempelbild av Snälltåget'));
});
