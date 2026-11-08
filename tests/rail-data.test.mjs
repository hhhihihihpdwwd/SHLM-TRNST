import test from 'node:test';
import assert from 'node:assert/strict';
import {activeRailTrips,railAt,railPathSplit} from '../src/rail-data.js';
const now=Math.floor(Date.now()/1000);
const dataset={schema:1,counts:{metro:1},shapes:{one:[[59.3,18],[59.32,18.02],[59.34,18.04]]},trips:[
{id:'test',mode:'metro',shapeId:'one',start:now-50,end:now+50,
stops:[[59.3,18,'First',0,0],[59.32,18.02,'Middle',50,50],[59.34,18.04,'Last',100,100]]}
]};
test('actual GTFS shape is used, no fabricated direct connectors',()=>{
 const active=activeRailTrips(dataset,now);
 assert.equal(active.length,1);
 const state=railAt(active[0],now);
 assert(Number.isFinite(state.pos[0]) && Number.isFinite(state.pos[1]));
 const pieces=railPathSplit(active[0],state.meters);
 assert(pieces.past.length>=2 && pieces.future.length>=2);
 assert(Math.abs(pieces.past.at(-1)[0]-pieces.future[0][0])<0.00001);
});
test('not scheduled outside service time',()=>{
 assert.equal(activeRailTrips(dataset,now+3600).length,0);
});
