// GTFS timetable adapter: UTC epoch for times, source shape coordinates for positions.
// No fallback straight-track geometry for actual services.
const TIMETABLE_URL='./data/rail.json';
const pathCache=new Map(),projectionCache=new Map();
export async function loadRailTimetable(){
 try {
  const response=await fetch(TIMETABLE_URL,{cache:'no-cache'});
  if(!response.ok)return null;
  const data=await response.json();
  if(data.schema!==1||!Array.isArray(data.trips)||!data.shapes||!data.trips.length)return null;
  if(!['pendeltag-tunnelbana-tvarbanan-localtram-city7-roslags-saltsjo-arlanda','pendeltag-tunnelbana-tvarbanan-localtram-city7-roslags-saltsjo-arlanda-malartag'].includes(data.scope)||!data.counts?.commuter||!data.counts?.metro||!data.counts?.tram||!['30','31','12','21','7'].every(line=>data.tramLines?.[line]>0))return null;
  return data;
 }catch(e){console.warn('Verified timetable unavailable; preserving current release',e);return null}
}
function dist(a,b){
 const k=Math.PI/180,R=6371000,dl=(b[1]-a[1])*k,dp=(b[0]-a[0])*k;
 const x=Math.sin(dp/2)**2+Math.cos(a[0]*k)*Math.cos(b[0]*k)*Math.sin(dl/2)**2;
 return R*2*Math.atan2(Math.sqrt(x),Math.sqrt(1-x));
}
function geometry(shapeId,allShapes){
 if(pathCache.has(shapeId))return pathCache.get(shapeId);
 const points=allShapes[shapeId];
 if(!Array.isArray(points)||points.length<2)return null;
 const total=[0];
 for(let i=1;i<points.length;i++)total.push(total[i-1]+dist(points[i-1],points[i]));
 const entry={points,distances:total};
 if(pathCache.size>600)pathCache.clear();
 pathCache.set(shapeId,entry);
 return entry;
}
function nearestDistance(p,geom,minimum){
 let best=minimum,err=Infinity;
 // Monotonic search: choosing points behind the previous stop would make trains reverse.
 for(let i=1;i<geom.points.length;i++){
  if(geom.distances[i]<minimum-50)continue;
  const a=geom.points[i-1],b=geom.points[i],scale=111100*Math.cos(p[0]*Math.PI/180);
  const dx=(b[1]-a[1])*scale,dy=(b[0]-a[0])*111100;
  const px=(p[1]-a[1])*scale,py=(p[0]-a[0])*111100;
  const fraction=Math.max(0,Math.min(1,(px*dx+py*dy)/(dx*dx+dy*dy||1)));
  const d=geom.distances[i-1]+(geom.distances[i]-geom.distances[i-1])*fraction;
  if(d<minimum-50)continue;
  const error=Math.hypot(px-dx*fraction,py-dy*fraction);
  if(error<err){err=error;best=d}
 }
 return {distance:best,error:err};
}
function anchors(trip,geom){
 const key=trip.shapeId+':'+trip.stops.map(s=>s[2]).join('|');
 if(projectionCache.has(key))return projectionCache.get(key);
 let min=0;const out=[];
 for(const stop of trip.stops){
  const p=nearestDistance(stop,geom,min);
  if(p.error>850){projectionCache.set(key,null);return null}
  min=Math.max(min,p.distance);out.push(min);
 }
 if(out.length<2||out.at(-1)-out[0]<30){projectionCache.set(key,null);return null}
 if(projectionCache.size>1500)projectionCache.clear();
 projectionCache.set(key,out);return out;
}
function atDistance(g,target){
 const cumulative=g.distances,pts=g.points;
 if(target<=0)return pts[0];
 if(target>=cumulative.at(-1))return pts.at(-1);
 let a=1,b=cumulative.length-1;
 while(a<b){const m=(a+b)>>1;if(cumulative[m]<target)a=m+1;else b=m}
 const i=a,f=(target-cumulative[i-1])/Math.max(.001,cumulative[i]-cumulative[i-1]);
 return [pts[i-1][0]+(pts[i][0]-pts[i-1][0])*f,pts[i-1][1]+(pts[i][1]-pts[i-1][1])*f];
}
export function activeRailTrips(dataset,epoch,limit=900){
 if(!dataset)return [];
 const candidates=[];
 for(const trip of dataset.trips){
  if(!['commuter','metro','tram','localrail','saltsjo','express','regional'].includes(trip.mode)||trip.geometryQuality!=='verified-osm-relation')continue;
  if(epoch<trip.start-60||epoch>trip.end+80)continue;
  const geom=geometry(trip.shapeId,dataset.shapes);
  if(!geom)continue;
  const track=anchors(trip,geom);
  if(!track)continue;
  candidates.push({...trip,_geom:geom,_anchors:track});
  if(candidates.length>=limit)break;
 }
 return candidates;
}
export function railAt(trip,epoch){
 const stops=trip.stops,anchor=trip._anchors,geom=trip._geom;
 const base=trip.start-stops[0][3];
 const seconds=epoch-base;
 let next=0;
 while(next<stops.length-1 && seconds>=stops[next][4])next++;
 let distance=anchor[next];
 if(next>0 && seconds<stops[next][3]){
  const prev=next-1,a=stops[prev][4],b=stops[next][3];
  const factor=Math.min(1,Math.max(0,(seconds-a)/Math.max(1,b-a)));
  distance=anchor[prev]+(anchor[next]-anchor[prev])*factor;
 }
 let kmh=0;
 if(next>0 && seconds>=stops[next-1][4] && seconds<stops[next][3]){
   const duration=stops[next][3]-stops[next-1][4];
   kmh=duration>0?Math.max(0,(anchor[next]-anchor[next-1])/duration*3.6):0;
 }
 return {pos:atDistance(geom,distance),next,meters:distance,kmh:Math.round(kmh)};
}
export function railPathSplit(trip,meters){
 const g=trip._geom,a=trip._anchors[0],b=trip._anchors.at(-1),progress=Math.min(b,Math.max(a,meters));
 function piece(start,end){
  const result=[atDistance(g,start)];
  for(let i=1;i<g.points.length-1;i++)if(g.distances[i]>start&&g.distances[i]<end)result.push(g.points[i]);
  result.push(atDistance(g,end));return result;
 }
 return {past:piece(a,progress),future:piece(progress,b)};
}
