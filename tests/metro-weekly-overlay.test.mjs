import test from 'node:test';
import assert from 'node:assert/strict';
import {activeRailTrips,railAt} from '../website/src/rail-data.js';

const shape=[[59.3,18.0],[59.32,18.02],[59.34,18.04]];
function trip(id,day,mode,from,to){
 const base=Date.parse(day+'T00:00:00+01:00')/1000;
 return {id,mode,line:mode==='metro'?'13':'40',
  geometryQuality:'verified-osm-relation',shapeId:'osm',
  serviceDay:day,start:base+from,end:base+to,
  stops:[[59.3,18,'A',from,from],[59.34,18.04,'B',to,to]]};
}
const data={type:'historical-daily-repeating-simulation',simulationTemplateDay:'2026-11-06',
 metroWeekdaySimulation:true,
 metroWeekdaySourceDays:{"0":"2026-11-09","1":"2026-11-10","2":"2026-11-04","3":"2026-11-05","4":"2026-11-06","5":"2026-11-07","6":"2026-11-08"},
 shapes:{osm:shape},trips:[
  trip('metro-friday','2026-11-06','metro',12*3600,13*3600),
  trip('metro-saturday','2026-11-07','metro',14*3600,15*3600),
  trip('metro-sunday','2026-11-08','metro',16*3600,17*3600),
  trip('metro-friday-overnight','2026-11-06','metro',23*3600+45*60,24*3600+30*60),
  trip('other-commuter','2026-11-06','commuter',12*3600,13*3600)
 ]};
const active=(date,time)=>activeRailTrips(data,Date.parse(date+'T'+time+'+01:00')/1000,100);
test('real Friday template never falsely appears as Saturday or Sunday Metro service',()=>{
 const fri=active('2026-11-13','12:15:00');
 assert.deepEqual(fri.filter(t=>t.mode==='metro').map(t=>t.id.split(':DAILY')[0]),['metro-friday']);
 const sat=active('2026-11-14','14:15:00');
 assert.deepEqual(sat.filter(t=>t.mode==='metro').map(t=>t.id.split(':DAILY')[0]),['metro-saturday']);
 const sun=active('2026-11-15','16:15:00');
 assert.deepEqual(sun.filter(t=>t.mode==='metro').map(t=>t.id.split(':DAILY')[0]),['metro-sunday']);
});
test('late Friday train survives after midnight on Saturday',()=>{
 const actual=active('2026-11-14','00:15:00').filter(t=>t.mode==='metro');
 assert.equal(actual.length,1);
 assert(actual[0].id.startsWith('metro-friday-overnight'));
 assert.equal(actual[0].serviceDay,'2026-11-13');
 assert(railAt(actual[0],Date.parse('2026-11-14T00:15:00+01:00')/1000).pos.every(Number.isFinite));
});
test('all nonmetro modes continue existing daily historical behavior unchanged',()=>{
 assert.equal(active('2026-11-14','12:15:00').filter(t=>t.mode==='commuter').length,1);
 assert.equal(active('2026-11-15','12:15:00').filter(t=>t.mode==='commuter').length,1);
});
