import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {activeRailTrips,railAt} from '../src/rail-data.js';
import {matchesRailFilter,railFilterTitle} from '../src/rail-filter.js';

test('connected physical OSM railway ways are allowed ONLY for Mälartåg',()=>{
 const epoch=Date.parse('2026-11-09T12:10:00+01:00')/1000;
 const path=[[59.33,18.01],[59.35,18.00],[59.37,17.99]];
 const original={id:'old-sj',mode:'intercity',agency:'SJ',line:'SJ',shapeId:'old',
    geometryQuality:'verified-osm-relation',start:epoch-180,end:epoch+180,
    stops:[[59.33,18.01,'Stockholm C',0,0],[59.37,17.99,'Next',360,360]]};
 const regional={...original,id:'malartag-osm-ways',mode:'regional',
    agency:'Mälartåg',line:'nykoping',corridor:'nykoping',
    geometryQuality:'verified-osm-rail-ways'};
 const dataset={shapes:{old:path},trips:[original,regional,
    {...regional,id:'fake',geometryQuality:'approximate-stop-connectors'},
    {...regional,id:'fake-sj',mode:'intercity',agency:'SJ'},
    {...regional,id:'bus',mode:'bus'}]};
 const active=activeRailTrips(dataset,epoch,100);
 assert.deepEqual(active.map(t=>t.id),['old-sj','malartag-osm-ways']);
 assert.deepEqual(active.filter(t=>matchesRailFilter(t,'sj')).map(t=>t.id),['old-sj']);
 assert.deepEqual(active.filter(t=>matchesRailFilter(t,'malartag')).map(t=>t.id),['malartag-osm-ways']);
 assert.equal(railFilterTitle('malartag'),'Mälartåg');
 assert(railAt(active[1],epoch).pos.every(Number.isFinite));
});
test('Mälartåg is isolated in UI and cannot replace the Lidingöbanan/SJ camera',()=>{
 const app=readFileSync(new URL('../src/app.js',import.meta.url),'utf8');
 const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
 const photos=readFileSync(new URL('../src/photos.js',import.meta.url),'utf8');
 assert(html.includes('data-filter="malartag"'));
 assert(app.includes('focusMalartagPilot()'));
 assert(app.includes('focusLidingoLine()'));
 assert(app.includes("['malartag',t=>t.mode==='regional'&&t.agency==='Mälartåg']"));
 assert(app.includes("['sj',t=>t.mode==='intercity'&&t.agency==='SJ']"));
 assert(photos.includes("v.mode==='regional' && v.agency==='Mälartåg'"));
 assert(app.includes('Exempelbild av Mälartåg'));
});
