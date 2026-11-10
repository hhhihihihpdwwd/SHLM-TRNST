import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {activeRailTrips} from '../src/rail-data.js';
import {matchesRailFilter} from '../src/rail-filter.js';

test('Full SJ rollout changes no existing filter and new SJ OSM-way train is valid',()=>{
 const rail=readFileSync(new URL('../src/rail-data.js',import.meta.url),'utf8');
 const app=readFileSync(new URL('../src/app.js',import.meta.url),'utf8');
 const filters=readFileSync(new URL('../src/rail-filter.js',import.meta.url),'utf8');
 assert(rail.includes("source.sjCompleteVerified===true"));
 assert(rail.includes("String(dataset.scope||'').endsWith('-sj-complete')"));
 assert(rail.includes("-tagab-rdc-sj-complete"));
 assert(app.includes("if(agency==='sj')")||app.includes("agency==='sj'"));
 assert(filters.includes("filter==='sj'"));
 for(const key of ['commuter','metro','tram','nockeby','lidingo','city7',
  'roslags','saltsjo','arlanda','sj','vr','snalltaget','vy','tagab','rdc','malartag']){
  assert(!matchesRailFilter({agency:'SJ',mode:'intercity'},key)||key==='sj',key);
 }
});
test('Actual GTFS SJ North overnight journey can remain visible after midnight and every day',()=>{
 const date='2026-11-06',begin=Date.parse('2026-11-06T21:00:00+01:00')/1000;
 const end=Date.parse('2026-11-07T09:00:00+01:00')/1000;
 const trip={id:'sj-night-example',mode:'intercity',agency:'SJ',line:'SJ',train:'93',
  start:begin,end,serviceDay:date,geometryQuality:'verified-osm-rail-ways',
  osmWayNetwork:true,shapeId:'real-osm-test',direction:'to-stockholm',
  stops:[[59.33014,18.058154,'Stockholm Centralstation',21*3600,21*3600],
    [59.849,17.638,'Uppsala Centralstation',22*3600,22*3600],
    [60.674,17.142,'Gävle Centralstation',23*3600,23*3600],
    [62.39,17.31,'Sundsvall Centralstation',33*3600,33*3600]]};
 const dataset={type:'historical-daily-repeating-simulation',
  simulationTemplateDay:date,
  shapes:{'real-osm-test':[[59.33014,18.058154],[59.849,17.638],[60.674,17.142],[62.39,17.31]]},
  trips:[trip]};
 for(const day of ['2026-11-09','2026-11-10','2026-11-11','2026-11-12','2026-11-13']){
  const d=Date.parse(day+'T23:00:00+01:00')/1000;
  assert(activeRailTrips(dataset,d,100).some(t=>matchesRailFilter(t,'sj')),day);
 }
 for(const day of ['2026-11-10','2026-11-11']){
  const t=Date.parse(day+'T01:00:00+01:00')/1000;
  assert(activeRailTrips(dataset,t,100).some(x=>x.agency==='SJ'),'SJ overnight ceased at midnight '+day);
 }
});
