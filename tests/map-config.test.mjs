import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
const source=readFileSync(new URL('../src/app.js',import.meta.url),'utf8');
test('Map is never backed by key-gated CARTO tiles',()=>{
 assert(!source.includes('basemaps.cartocdn.com'));
 assert(source.includes('https://tile.openstreetmap.org/{z}/{x}/{y}.png'));
 assert(source.includes('https://www.openstreetmap.org/copyright'));
});
test('Satellite switch remains available',()=>{
 assert(source.includes('World_Imagery/MapServer/tile/{z}/{y}/{x}'));
});
