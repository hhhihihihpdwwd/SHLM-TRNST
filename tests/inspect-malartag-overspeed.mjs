import {readFileSync} from 'node:fs';
import {activeRailTrips,railAt} from '../src/rail-data.js';
const d=JSON.parse(readFileSync(process.argv[2],'utf8'));
const list=d.trips.filter(t=>t.agency==='Mälartåg'&&t.serviceDay===d.simulationTemplateDay&&t.shapeId==='malartag-osm:4755734:f+4755735:f+3177328:r');
for(const t of list){
 const epoch=t.start+Math.min(60,Math.max(5,Math.floor((t.stops[1][3]-t.stops[0][4])/2)));
 const a=activeRailTrips(d,epoch,20000).find(x=>x.id.startsWith(t.id+':DAILY:')&&x.start===t.start);
 if(!a){console.log('UNAVAILABLE',t.id,epoch);continue}
 const stops=t.stops.slice(0,5),anchors=a._anchors.slice(0,5),positions=stops.map((s,i)=>({name:s[2],arrival:s[3],departure:s[4],distance:Math.round(anchors[i])}));
 const legSpeed=(anchors[1]-anchors[0])/(stops[1][3]-stops[0][4])*3.6;
 const point=railAt(a,epoch);
 console.log('MALARTAG INVESTIGATION',JSON.stringify({id:t.id,shapeId:t.shapeId,tripStart:t.start,tripEnd:t.end,stops:positions,segmentKmh:Math.round(legSpeed),speedNow:point.kmh,next:point.next,geometryDistance:a._geom.distances.at(-1)},null,2));
}
