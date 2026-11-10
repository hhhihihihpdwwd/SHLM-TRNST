import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {matchesRailFilter,railFilterTitle} from '../src/rail-filter.js';

const vehicles=[
 {id:'p',mode:'commuter',line:'41'},
 {id:'m',mode:'metro',line:'14'},
 {id:'t30',mode:'tram',line:'30'},
 {id:'t31',mode:'tram',line:'31'},
 {id:'n12',mode:'tram',line:'12'},
 {id:'l21',mode:'tram',line:'21'}
];
test('legacy filters remain identical after adding the two local tramways',()=>{
 assert.deepEqual(vehicles.filter(v=>matchesRailFilter(v,'commuter')).map(v=>v.id),['p']);
 assert.deepEqual(vehicles.filter(v=>matchesRailFilter(v,'metro')).map(v=>v.id),['m']);
 assert.deepEqual(vehicles.filter(v=>matchesRailFilter(v,'tram')).map(v=>v.id),['t30','t31']);
});
test('line 12 and 21 have exclusive selection and combined map shows all',()=>{
 assert.deepEqual(vehicles.filter(v=>matchesRailFilter(v,'nockeby')).map(v=>v.id),['n12']);
 assert.deepEqual(vehicles.filter(v=>matchesRailFilter(v,'lidingo')).map(v=>v.id),['l21']);
 assert.equal(vehicles.filter(v=>matchesRailFilter(v,'all')).length,6);
 assert.equal(railFilterTitle('lidingo'),'Lidingöbanan');
});
test('local vehicle photos and UI elements are present; movement and follow engine reused',()=>{
 const photos=readFileSync(new URL('../src/photos.js',import.meta.url),'utf8');
 const app=readFileSync(new URL('../src/app.js',import.meta.url),'utf8');
 const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
 for(const id of ['nockeby','lidingo'])assert(html.includes('data-filter="'+id+'"'));
 for(const image of ['tram_nockeby12','tram_lidingo21'])assert(photos.includes("'"+image+"'"));
 for(const functionName of ['followFrame','railPathSplit','showRealDetail','switchTiles','occupancy'])
   assert(app.includes(functionName));
});

test('map markers and sidebar share exactly the same line-aware filter',()=>{
 const app=readFileSync(new URL('../src/app.js',import.meta.url),'utf8');
 assert(app.includes('for(const v of displayOrder(realActive.filter(v=>matchesRailFilter(v,state.filter)))'));
 assert(app.includes('const showing=displayOrder(realActive.filter(v=>matchesRailFilter(v,state.filter)))'));
 assert(!app.includes("state.filter==='all'||state.filter===v.mode"));
 for(const f of ['nockeby','lidingo']){
   const selected=vehicles.filter(v=>matchesRailFilter(v,f));
   assert.equal(selected.length,1);
   assert.equal(selected[0].line,f==='nockeby'?'12':'21');
 }
});
