import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {activeRailTrips} from '../src/rail-data.js';
import {matchesRailFilter,railFilterTitle} from '../src/rail-filter.js';

test('New Vy Tåg filter never changes any original 13 operator filters',()=>{
 const operators=[
  {mode:'intercity',agency:'Vy Tåg'},
  {mode:'intercity',agency:'SJ'},
  {mode:'intercity',agency:'VR Snabbtåg'},
  {mode:'intercity',agency:'Snälltåget'},
  {mode:'regional',agency:'Mälartåg'},
  {mode:'commuter',agency:'SL'}];
 const vy=operators.filter(x=>matchesRailFilter(x,'vy'));
 assert.deepEqual(vy,[operators[0]]);
 for(const key of ['sj','vr','snalltaget','malartag','commuter']){
  assert.equal(matchesRailFilter(operators[0],key),false);
 }
 assert.equal(railFilterTitle('vy'),'Vy Tåg');
});
test('Authentic Vy weekend trips repeat only on their recorded weekday, unlike original daily services',()=>{
 const template='2026-11-06';
 const shape=[[59.33014,18.058154],[59.4,17.9],[59.5,17.7],[59.568759,17.532813]];
 const start=Date.parse('2026-11-06T09:00:00+01:00')/1000;
 const end=Date.parse('2026-11-06T10:00:00+01:00')/1000;
 const base={id:'example',mode:'intercity',agency:'Vy Tåg',geometryQuality:'verified-osm-rail-ways',
  osmWayNetwork:true,shapeId:'vy-osm-rail:to-oslo',serviceDay:template,start,end,
  stops:[[59.33014,18.058154,'Stockholm Centralstation',32400,32400],
         [59.568759,17.532813,'Bålsta station',36000,36000]]};
 const original={...base,id:'original-sj',agency:'SJ',geometryQuality:'verified-osm-relation'};
 const data={type:'historical-daily-repeating-simulation',simulationTemplateDay:template,
  shapes:{'vy-osm-rail:to-oslo':shape},trips:[{...base,historicWeekday:5},original]};
 function count(day){return activeRailTrips(data,Date.parse(day+'T09:30:00+01:00')/1000,20)}
 assert(count('2026-11-07').some(t=>t.agency==='Vy Tåg'),'Saturday Vy trip must run');
 assert(!count('2026-11-06').some(t=>t.agency==='Vy Tåg'),'Friday Vy must be absent');
 assert(!count('2026-11-08').some(t=>t.agency==='Vy Tåg'),'Sunday Vy must be absent');
 assert(count('2026-11-14').some(t=>t.agency==='Vy Tåg'),'Subsequent Saturday repeats');
 assert(count('2026-11-06').some(t=>t.agency==='SJ'),'Original historical SJ repeats unchanged');
});
test('Vy HTML, icon and all 13 old controls remain',()=>{
 const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
 const app=readFileSync(new URL('../src/app.js',import.meta.url),'utf8');
 for(const f of ['commuter','metro','tram','nockeby','lidingo','city7','roslags','saltsjo','arlanda','sj','malartag','vr','snalltaget','vy','all']){
  assert(html.includes('data-filter="'+f+'"'),f);
 }
 assert(app.includes("if(agency==='vy tåg')return 'vy'"));
 assert(app.includes("from './vy-marker-sprite.js?v=vy-01'"));
 assert(app.includes("if(state.filter==='vy')focusVyTåg();"));
});
