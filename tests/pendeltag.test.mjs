import test from 'node:test';
import assert from 'node:assert/strict';
import {activeRailTrips,railAt,railPathSplit} from '../src/rail-data.js';

const now=1_800_000_000;
const track=[[59.30,18],[59.31,18.01],[59.32,18.02]];
const sample={schema:1,type:'historical-pendeltag-verified-rail',strictGeometry:true,
  counts:{commuter:1},shapes:{'osm:100':track},
  trips:[{id:'commuter-41',mode:'commuter',shapeId:'osm:100',start:now,end:now+220,
    stops:[[59.30,18,'First',0,20],[59.31,18.01,'Second',100,125],[59.32,18.02,'Last',220,220]]}]};
test('Pendeltåg acceleration/stop/deceleration share exact OSM geometry',()=>{
 const [v]=activeRailTrips(sample,now+50);
 assert(v,'shape-matched commuter trip should activate');
 const stationary=railAt(v,now+10);
 assert.equal(stationary.kmh,0);
 const moving=railAt(v,now+60);
 assert(moving.kmh>0);
 assert.equal(moving.next,1);
 const onPlatform=railAt(v,now+112);
 assert.equal(onPlatform.kmh,0);
 assert.equal(onPlatform.atStop,true);
 const movingAgain=railAt(v,now+166);
 assert(movingAgain.kmh>0);
 assert.equal(movingAgain.next,2);
 assert.equal(railAt(v,now+220).kmh,0);
});
test('Past blue and future grey meet without a gap',()=>{
 const [v]=activeRailTrips(sample,now+55);
 const current=railAt(v,now+55);
 const paths=railPathSplit(v,current.meters);
 assert.deepEqual(paths.past.at(-1),paths.future[0]);
});
test('Inactive journeys are excluded',()=>assert.equal(activeRailTrips(sample,now+3600).length,0));
