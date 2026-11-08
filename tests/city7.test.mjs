import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {matchesRailFilter,railFilterTitle} from '../src/rail-filter.js';
const vehicles=[{mode:'commuter',line:'41'},{mode:'metro',line:'14'},
 {mode:'tram',line:'30'},{mode:'tram',line:'31'},
 {mode:'tram',line:'12'},{mode:'tram',line:'21'},{mode:'tram',line:'7'}];
test('new city 7 selection is exclusive and all old filters still match',()=>{
 const selected=filter=>vehicles.filter(v=>matchesRailFilter(v,filter)).map(v=>v.line);
 assert.deepEqual(selected('commuter'),['41']);
 assert.deepEqual(selected('metro'),['14']);
 assert.deepEqual(selected('tram'),['30','31']);
 assert.deepEqual(selected('nockeby'),['12']);
 assert.deepEqual(selected('lidingo'),['21']);
 assert.deepEqual(selected('city7'),['7']);
 assert.equal(selected('all').length,7);
 assert.equal(railFilterTitle('city7'),'Spårväg City');
});
test('both visible marker map and list use same dedicated line-aware selector',()=>{
 const app=readFileSync(new URL('../src/app.js',import.meta.url),'utf8');
 assert.match(app,/const showing=realActive\.filter\(v=>matchesRailFilter\(v,state\.filter\)\)/);
 assert.match(app,/realActive\.filter\(v=>matchesRailFilter\(v,state\.filter\)\)\.slice\(0,90\)/);
 assert(!app.includes("state.filter==='all'||state.filter===v.mode"));
});
test('camera, progress line, speed, occupancy and satellite remain in place',()=>{
 const app=readFileSync(new URL('../src/app.js',import.meta.url),'utf8');
 const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
 const photos=readFileSync(new URL('../src/photos.js',import.meta.url),'utf8');
 for(const feature of ['followFrame','railPathSplit','showRealDetail','switchTiles','occupancy','speed-value'])
   assert(app.includes(feature));
 assert(html.includes('data-filter="city7"'));
 assert(photos.includes("'tram_city7'"));
});
