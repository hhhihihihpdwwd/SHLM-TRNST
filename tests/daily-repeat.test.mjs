import test from 'node:test';
import assert from 'node:assert/strict';
import {activeRailTrips,railAt} from '../src/rail-data.js';

const template='2026-11-08',zone='+01:00';
const noon=Date.parse(template+'T12:30:00'+zone)/1000;
const end=Date.parse(template+'T13:15:00'+zone)/1000;
const midnight=Date.parse(template+'T23:45:00'+zone)/1000;
const next=Date.parse('2026-11-09T00:20:00+01:00')/1000;
const shape=[[59.30,18.01],[59.35,18.03],[59.40,18.05]];
const data={type:'historical-daily-repeating-simulation',
 simulationTemplateDay:template,
 shapes:{track:shape},
 trips:[
  {id:'weekday-noon',mode:'metro',line:'14',shapeId:'track',
   geometryQuality:'verified-osm-relation',serviceDay:template,
   start:noon,end,
   stops:[[59.30,18.01,'A',45000,45000],[59.40,18.05,'B',47700,47700]]},
  {id:'weekday-night',mode:'metro',line:'14',shapeId:'track',
   geometryQuality:'verified-osm-relation',serviceDay:template,
   start:midnight,end:next,
   stops:[[59.30,18.01,'A',85500,85500],[59.40,18.05,'B',87600,87600]]}
 ]};
test('one historic weekday is repeated every day and same local hour, winter and summer',()=>{
 const dates=['2026-11-09','2026-11-10','2026-11-11','2026-11-12','2026-11-13','2026-11-14','2026-11-15','2027-07-13'];
 for(const date of dates){
  const summer=date.includes('-07-');
  const epoch=Date.parse(date+'T12:47:00'+(summer?'+02:00':'+01:00'))/1000;
  const found=activeRailTrips(data,epoch,100);
  assert.equal(found.length,1,date);
  assert(found[0].id.startsWith('weekday-noon'));
  assert(found[0].serviceDay===date);
  const at=railAt(found[0],epoch);
  assert(at.pos.every(Number.isFinite));
 }
});
test('night services naturally become fewer based on real template, not arbitrary occupancy',()=>{
 const midday=Date.parse('2026-11-12T12:47:00+01:00')/1000;
 const at3=Date.parse('2026-11-12T03:00:00+01:00')/1000;
 assert.equal(activeRailTrips(data,midday).length,1);
 assert.equal(activeRailTrips(data,at3).length,0);
});
test('overnight template trips survive on next calendar day',()=>{
 const at=Date.parse('2026-11-13T00:05:00+01:00')/1000;
 const found=activeRailTrips(data,at,100);
 assert.equal(found.length,1);
 assert(found[0].id.includes('weekday-night'));
 assert.equal(found[0].serviceDay,'2026-11-12');
});
