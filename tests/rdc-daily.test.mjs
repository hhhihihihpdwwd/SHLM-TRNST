import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {activeRailTrips} from '../src/rail-data.js';
import {matchesRailFilter,railFilterTitle} from '../src/rail-filter.js';

test('RDC EuroNight filter remains isolated from all 15 existing systems',()=>{
 const euro={agency:'RDC EuroNight',mode:'intercity',train:'344'};
 assert(matchesRailFilter(euro,'rdc'));
 assert(matchesRailFilter(euro,'all'));
 for(const key of ['commuter','metro','tram','nockeby','lidingo','city7',
  'roslags','saltsjo','arlanda','sj','vr','snalltaget','vy','tagab','malartag']){
   assert(!matchesRailFilter(euro,key),'Unexpected RDC match in '+key);
 }
 assert.equal(railFilterTitle('rdc'),'RDC EuroNight');
});

test('A real overnight EN344 reference trip remains active after midnight and repeats daily',()=>{
 const baseDay='2026-11-06';
 const start=Date.parse('2026-11-06T21:53:00+01:00')/1000;
 const end=Date.parse('2026-11-07T09:45:00+01:00')/1000;
 const e={id:'authentic-en344-schedule-reference',agency:'RDC EuroNight',line:'EN 344',train:'344',
  mode:'intercity',direction:'to-stockholm',geometryQuality:'verified-osm-rail-ways',
  osmWayNetwork:true,serviceDay:baseDay,start,end,shapeId:'rdc-test-shape',destination:'Stockholm C',
  stops:[[53.5531,10.0067,'Hamburg Hbf',21*3600+53*60,21*3600+53*60],
   [54.8241,9.3637,'Padborg',24*3600+29*60,24*3600+29*60],
   [55.705,13.1872,'Lund C',28*3600+35*60,28*3600+35*60],
   [59.33014,18.058154,'Stockholm C',33*3600+45*60,33*3600+45*60]]};
 const data={type:'historical-daily-repeating-simulation',simulationTemplateDay:baseDay,
  shapes:{'rdc-test-shape':[[53.5531,10.0067],[54.8241,9.3637],[55.705,13.1872],[59.33014,18.058154]]},
  trips:[e]};
 for(const day of ['2026-11-09','2026-11-10','2026-11-11','2026-11-12','2026-11-13','2026-11-14','2026-11-15']){
  const evening=Date.parse(day+'T22:30:00+01:00')/1000;
  const active=activeRailTrips(data,evening,100);
  assert(active.some(x=>matchesRailFilter(x,'rdc')),'RDC absent on '+day);
 }
 for(const day of ['2026-11-10','2026-11-12','2026-11-14']){
  const dawn=Date.parse(day+'T02:00:00+01:00')/1000;
  assert(activeRailTrips(data,dawn,100).some(x=>matchesRailFilter(x,'rdc')),
   'RDC stopped at midnight on '+day);
 }
});

test('RDC distinct 3D night train image and real-photo label do not change existing 15 operator symbols',()=>{
 const app=readFileSync(new URL('../src/app.js',import.meta.url),'utf8');
 const filters=readFileSync(new URL('../src/rail-filter.js',import.meta.url),'utf8');
 const photos=readFileSync(new URL('../src/photos.js',import.meta.url),'utf8');
 const rail=readFileSync(new URL('../src/rail-data.js',import.meta.url),'utf8');
 const sprite=readFileSync(new URL('../src/rdc-marker-sprite.js',import.meta.url),'utf8');
 assert(sprite.includes('<svg')&&sprite.includes('rdcMarker'));
 assert(app.includes("if(agency==='rdc euronight')return 'rdc'"));
 assert(app.includes("operatorKey==='rdc'?rdcMarker"));
 assert(app.includes("if(state.filter==='rdc')focusRdcEuroNight();"));
 assert(filters.includes("filter==='rdc'"));
 assert(rail.includes("'RDC EuroNight'"));
 assert(photos.includes('photoCatalog.rail_rdc_euronight'));
});
