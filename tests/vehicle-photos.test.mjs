import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {vehicleFrontSprites} from '../src/vehicle-front-sprites.js';
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
test('only shape-verified Pendeltåg, Tunnelbana, Tvärbanan; no fake fallback',()=>{
 const engine=readFileSync(new URL('../src/rail-data.js',import.meta.url),'utf8');
 assert(engine.includes("!['commuter','metro','tram','localrail'].includes(trip.mode)"));
 assert(engine.includes("trip.geometryQuality!=='verified-osm-relation'"));
 assert(app.includes('const approximate=false'));
 assert(html.includes('data-filter="metro"'));
 assert(html.includes('data-filter="tram"'));
 const photos=readFileSync(new URL('../src/photos.js',import.meta.url),'utf8');
 assert(photos.includes("'tram_a35'"));
 assert(!html.includes('data-filter="rail"'));
});
