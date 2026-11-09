import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {matchesRailFilter,railFilterTitle} from '../src/rail-filter.js';
const vehicles=[{mode:'commuter',line:'41'}, {mode:'metro',line:'14'},
 {mode:'tram',line:'30'}, {mode:'tram',line:'12'}, {mode:'tram',line:'21'},
 {mode:'tram',line:'7'}, {mode:'localrail',line:'27'},
 {mode:'localrail',line:'28'}, {mode:'localrail',line:'29'}];
test('Roslagsbanan 27/28/29 separate; all old filters unchanged',()=>{
 const lines=f=>vehicles.filter(v=>matchesRailFilter(v,f)).map(v=>v.line);
 assert.deepEqual(lines('roslags'),['27','28','29']);
 assert.deepEqual(lines('tram'),['30']);
 assert.deepEqual(lines('nockeby'),['12']);
 assert.deepEqual(lines('lidingo'),['21']);
 assert.deepEqual(lines('city7'),['7']);
 assert.deepEqual(lines('metro'),['14']);
 assert.deepEqual(lines('commuter'),['41']);
 assert.equal(lines('all').length,9);
 assert.equal(railFilterTitle('roslags'),'Roslagsbanan');
});
test('map and sidebar share same filter and preserve follow and satellite',()=>{
 const app=readFileSync(new URL('../src/app.js',import.meta.url),'utf8');
 const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
 assert(app.includes('const showing=displayOrder(realActive.filter(v=>matchesRailFilter(v,state.filter)))'));
 assert(app.includes('displayOrder(realActive.filter(v=>matchesRailFilter(v,state.filter))).slice(0,90)'));
 for(const feature of ['followFrame','railPathSplit','showRealDetail','switchTiles','occupancy','speed-value'])assert(app.includes(feature));
 assert(html.includes('data-filter="roslags"'));
});
test('X10p and X15p approved photos explicitly illustrative',()=>{
 const photo=readFileSync(new URL('../src/photos.js',import.meta.url),'utf8');
 const approved=JSON.parse(readFileSync(new URL('../photos/approved.json',import.meta.url),'utf8'));
 assert(photo.includes("'local_x10p'")&&photo.includes("'local_x15p'"));
 assert(approved.local_x10p.license);
 assert(approved.local_x15p.license);
 assert(approved.local_x10p.label.includes('Beispielbild'));
});
