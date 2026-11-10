import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {matchesRailFilter,railFilterTitle} from '../src/rail-filter.js';
const v=[{mode:'commuter',line:'41'},{mode:'metro',line:'14'}, {mode:'tram',line:'30'},
{mode:'tram',line:'12'},{mode:'tram',line:'21'},{mode:'tram',line:'7'},
{mode:'localrail',line:'27'},{mode:'localrail',line:'28'},{mode:'localrail',line:'29'},
{mode:'saltsjo',line:'25'},{mode:'saltsjo',line:'26'},
{mode:'express',line:'AX',agency:'Arlanda Express'}];
test('Express filter exclusive and eight prior mode filters preserved',()=>{
 const lines=f=>v.filter(x=>matchesRailFilter(x,f)).map(x=>x.line);
 assert.deepEqual(lines('arlanda'),['AX']);
 assert.deepEqual(lines('saltsjo'),['25','26']);
 assert.deepEqual(lines('roslags'),['27','28','29']);
 assert.deepEqual(lines('tram'),['30']);
 assert.deepEqual(lines('nockeby'),['12']);
 assert.deepEqual(lines('lidingo'),['21']);
 assert.deepEqual(lines('city7'),['7']);
 assert.deepEqual(lines('metro'),['14']);
 assert.deepEqual(lines('commuter'),['41']);
 assert.equal(lines('all').length,v.length);
 assert.equal(railFilterTitle('arlanda'),'Arlanda Express');
});
test('map and list share Express filter; follow/speed/occupancy/satellite preserved',()=>{
 const app=readFileSync(new URL('../src/app.js',import.meta.url),'utf8');
 const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
 const photos=readFileSync(new URL('../src/photos.js',import.meta.url),'utf8');
 assert(app.includes('const showing=displayOrder(realActive.filter(v=>matchesRailFilter(v,state.filter)))'));
 assert(app.includes('displayOrder(realActive.filter(v=>matchesRailFilter(v,state.filter)))'));
 assert(app.includes('realActive=activeRailTrips(railDataset,epoch,10000)'));
 assert(app.includes('function displayOrder(trips)'));
 for(const x of ['followFrame','railPathSplit','showRealDetail','switchTiles','occupancy','speed-value'])assert(app.includes(x));
 assert(html.includes('data-filter="arlanda"'));
 assert(photos.includes("v.mode==='express'")&&photos.includes("'rail_arlanda'"));
});
