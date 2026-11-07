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
 assert(app.includes("vehicleFrontSprites[imageKey]"));
 assert(app.includes("chosen?27:19"));
 assert(app.includes("rail-photo-marker"));
 assert(!html.includes('id="tab-station"'));
});
test('map route quality is not mislabeled verified when fallback estimated',()=>{
 assert(app.includes("v.geometryQuality==='approximate-stop-connectors'"));
 assert(app.includes("verified-osm-relation"));
});
