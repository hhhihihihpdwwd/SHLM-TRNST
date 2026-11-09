import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {matchesRailFilter,railFilterTitle} from '../src/rail-filter.js';
import {activeRailTrips,railAt} from '../src/rail-data.js';

test('SJ selection is exclusive and nine established systems keep their filters',()=>{
 const sources=[{mode:'commuter',agency:'SL'},{mode:'metro',agency:'SL'},
  {mode:'tram',line:'30'},{mode:'tram',line:'12'},
  {mode:'tram',line:'21'},{mode:'tram',line:'7'},
  {mode:'localrail',line:'27'},{mode:'saltsjo',line:'25'},
  {mode:'express',agency:'Arlanda Express'},{mode:'intercity',agency:'SJ'}];
 assert.deepEqual(sources.filter(x=>matchesRailFilter(x,'sj')), [sources[9]]);
 assert.equal(sources.filter(x=>matchesRailFilter(x,'all')).length,10);
 assert.equal(sources.filter(x=>matchesRailFilter(x,'commuter')).length,1);
 assert.equal(sources.filter(x=>matchesRailFilter(x,'arlanda')).length,1);
 assert.equal(railFilterTitle('sj'),'SJ');
 const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
 assert(html.includes('data-filter="sj"'));
 assert(!html.includes('data-filter="malartag"'));
});
test('real OSM-verified SJ train can be rendered without making up tracks',()=>{
 const epoch=Date.parse('2026-11-09T12:30:00+01:00')/1000;
 const shape=[[59.33,18.05],[59.32,18.03],[59.28,17.99]];
 const valid={id:'sj-valid',mode:'intercity',agency:'SJ',line:'SJ',
  geometryQuality:'verified-osm-relation',shapeId:'sj-test',
  start:epoch-600,end:epoch+600,
  stops:[[59.33,18.05,'Stockholm C',0,0],[59.28,17.99,'Destination',1200,1200]]};
 const data={shapes:{'sj-test':shape},trips:[valid,
   {...valid,id:'fake',geometryQuality:'approximate-stop-connectors'},
   {...valid,id:'unrelated',mode:'regional'}]};
 const active=activeRailTrips(data,epoch,100);
 assert.deepEqual(active.map(t=>t.id),['sj-valid']);
 const at=railAt(active[0],epoch);
 assert(at.pos.every(Number.isFinite));
 assert(Number.isFinite(at.kmh));
});
test('SJ is fairly included in combined rail map and sidebar list',()=>{
 const app=readFileSync(new URL('../src/app.js',import.meta.url),'utf8');
 assert(app.includes("['sj',t=>t.mode==='intercity'&&t.agency==='SJ']"));
 assert(app.includes('displayOrder(realActive.filter(v=>matchesRailFilter(v,state.filter)))'));
});
