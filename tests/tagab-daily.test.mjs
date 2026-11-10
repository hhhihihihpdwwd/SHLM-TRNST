import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {activeRailTrips} from '../src/rail-data.js';
import {matchesRailFilter,railFilterTitle} from '../src/rail-filter.js';

test('Tågab is 15th isolated rail operator; all original 14 filters remain',()=>{
 const tagab={mode:'intercity',agency:'Tågab',line:'7067'};
 const others=[
  {mode:'intercity',agency:'SJ'},
  {mode:'intercity',agency:'VR Snabbtåg'},
  {mode:'intercity',agency:'Snälltåget'},
  {mode:'intercity',agency:'Vy Tåg'},
  {mode:'regional',agency:'Mälartåg'},
  {mode:'commuter',agency:'SL'}
 ];
 assert(matchesRailFilter(tagab,'tagab'));
 assert(matchesRailFilter(tagab,'all'));
 for(const mode of ['sj','vr','snalltaget','vy','malartag','commuter','metro','arlanda']){
  assert(!matchesRailFilter(tagab,mode),mode);
 }
 for(const v of others)assert(!matchesRailFilter(v,'tagab'),v.agency);
 assert.equal(railFilterTitle('tagab'),'Tågab');
});

test('Historic Tågab references repeat EVERY day, just like original 14 systems',()=>{
 const template='2026-11-06';
 const start=Date.parse('2026-11-06T10:00:00+01:00')/1000;
 const end=Date.parse('2026-11-06T12:00:00+01:00')/1000;
 const shape=[[59.33014,18.058154],[59.35,17.96],[59.41,17.83],[59.55,17.71]];
 const train={id:'tagab-test',mode:'intercity',agency:'Tågab',line:'7055',train:'7055',
  direction:'from-stockholm',historicWeekdays:[5],shapeId:'test-track',
  geometryQuality:'verified-osm-rail-ways',osmWayNetwork:true,
  serviceDay:template,start,end,destination:'Karlstad Centralstation',
  stops:[[59.33014,18.058154,'Stockholm Centralstation',36000,36000],
         [59.55,17.71,'Example intermediate stop',43200,43200]]};
 const original={...train,id:'vy-test',agency:'Vy Tåg'};
 const data={type:'historical-daily-repeating-simulation',simulationTemplateDay:template,
  shapes:{'test-track':shape},trips:[train,original]};
 for(const date of ['2026-11-09','2026-11-10','2026-11-11','2026-11-12','2026-11-13','2026-11-14','2026-11-15']){
  const t=Date.parse(date+'T11:00:00+01:00')/1000;
  const active=activeRailTrips(data,t,100);
  assert(active.some(v=>matchesRailFilter(v,'tagab')),'Tågab missing on '+date);
  assert(active.some(v=>matchesRailFilter(v,'vy')),'Previously integrated Vy missing on '+date);
 }
});

test('Tågab original miniature, real photo label, focus and operator button remain isolated',()=>{
 const app=readFileSync(new URL('../src/app.js',import.meta.url),'utf8');
 const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
 const photos=readFileSync(new URL('../src/photos.js',import.meta.url),'utf8');
 const marker=readFileSync(new URL('../src/tagab-marker-sprite.js',import.meta.url),'utf8');
 const data=readFileSync(new URL('../src/rail-data.js',import.meta.url),'utf8');
 assert(marker.includes('<svg')&&marker.includes('encodeURIComponent(svg)'));
 assert(app.includes("if(agency==='tågab')return 'tagab'"));
 assert(app.includes("operatorKey==='tagab'?tagabMarker"));
 assert(app.includes("if(state.filter==='tagab')focusTagab();"));
 assert(photos.includes("photoCatalog.rail_tagab_rc3"));
 assert(data.includes("'Vy Tåg','Tågab'"));
 for(const f of ['commuter','metro','tram','nockeby','lidingo','city7','roslags',
  'saltsjo','arlanda','sj','vr','snalltaget','vy','malartag','all']){
  assert(html.includes('data-filter="'+f+'"'),f);
 }
});
