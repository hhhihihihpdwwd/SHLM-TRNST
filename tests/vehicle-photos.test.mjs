import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {vehicleFrontSprites} from '../src/vehicle-front-sprites.js';
import {activeRailTrips} from '../src/rail-data.js';
const app=readFileSync(new URL('../src/app.js', import.meta.url),'utf8');
const html=readFileSync(new URL('../index.html', import.meta.url),'utf8');
test('original transport-front images available as embedded WebP data',()=>{
 for(const type of ['metro','commuter','tram','rail','rail_arlanda','localrail']){
  assert.match(vehicleFrontSprites[type],/^data:image\/(?:webp|png);base64,/);
  assert(vehicleFrontSprites[type].length>3000);
 }
});
test('markers reuse original images and remain compact',()=>{
 assert(app.includes("originalSpriteUrl(imageKey)"));
 assert(app.includes("URL.createObjectURL"));
 assert(app.includes("chosen?27:19"));
 assert(app.includes("rail-photo-marker"));
 assert(!html.includes('id="tab-station"'));
});
test('only OSM-verified services across the existing and new rail systems; no fake fallback',()=>{
 const engine=readFileSync(new URL('../src/rail-data.js',import.meta.url),'utf8');
 assert(engine.includes("'verified-osm-relation'"));
 const epoch=Math.floor(Date.now()/1000);
 const shape=[[59.30,18.01],[59.31,18.02]];
 const source={id:'verified',mode:'regional',shapeId:'valid',
   geometryQuality:'verified-osm-relation',start:epoch-120,end:epoch+120,
   stops:[[59.30,18.01,'A',0,0],[59.31,18.02,'B',240,240]]};
 const dataset={shapes:{valid:shape},trips:[source,
   {...source,id:'bad-track',geometryQuality:'approximate-stop-connectors'},
   {...source,id:'bus',mode:'bus'}]};
 assert.deepEqual(activeRailTrips(dataset,epoch).map(t=>t.id),['verified']);
 assert(app.includes('const approximate=false'));
 assert(html.includes('data-filter="metro"'));
 assert(html.includes('data-filter="tram"'));
 const photos=readFileSync(new URL('../src/photos.js',import.meta.url),'utf8');
 assert(photos.includes("'tram_a35'"));
 assert(photos.includes("'rail_malartag'"));
 assert(!html.includes('data-filter="rail"'));
});
