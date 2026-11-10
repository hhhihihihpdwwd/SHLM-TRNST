import {stockholmTime,tripProgress,occupancy,secondsLabel} from './simulation.js';
import {services,central} from './demo-data.js';
import {loadRailTimetable,activeRailTrips,railAt,railPathSplit} from './rail-data.js?v=tagab-01';
import {loadPhotoCatalog,photoForVehicle} from './photos.js?v=tagab-01';
import {vehicleFrontSprites} from './vehicle-front-sprites.js';
import {operatorMarkerSprites} from './operator-marker-sprites.js?v=operator-markers-01';
import {approvedTrainMarkers} from './approved-train-markers.js?v=train-icons-02';
import {vyMarkerSprites} from './vy-marker-sprite.js?v=vy-01';
import {tagabMarker} from './tagab-marker-sprite.js?v=tagab-01';
import {matchesRailFilter,railFilterTitle} from './rail-filter.js?v=tagab-01';
const $=id=>document.getElementById(id);
const state={filter:'commuter',selected:null,follow:false,satellite:false,station:false};
let map,roads,railLayer,lastRouteUpdate=0,markers=new Map(),lastDetailUpdate=0;
function setupMap(){
 if(!window.L){$('map-fallback').hidden=false;return}
 map=L.map('map',{zoomControl:false,preferCanvas:true}).setView([59.334,18.058],11);
 L.control.zoom({position:'bottomright'}).addTo(map);
 setBaseLayer(false);
 railLayer=L.layerGroup().addTo(map);
 map.on('dragstart zoomstart',()=>{state.follow=false;updateFollow()});
}
// No API key required. A failed basemap is replaced rather than left blank.
const BASEMAPS={
  standard:[
    {url:'https://tile.openstreetmap.org/{z}/{x}/{y}.png',credit:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'},
    {url:'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',credit:'Tiles &copy; Esri'}
  ],
  satellite:[
    {url:'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',credit:'Imagery &copy; Esri'}
  ]
};
let baseLoadGeneration=0;
function setBaseLayer(satellite,providerIndex=0){
 if(!map)return;
 const generation=++baseLoadGeneration;
 const providers=BASEMAPS[satellite?'satellite':'standard'];
 const provider=providers[providerIndex]||providers[0];
 if(roads){map.removeLayer(roads);roads=null}
 const layer=L.tileLayer(provider.url,{maxZoom:19,updateWhenIdle:true,keepBuffer:2,attribution:provider.credit});
 roads=layer;let errors=0,success=0;
 layer.on('tileload',()=>{success++;if(generation!==baseLoadGeneration)return;$('map-fallback').hidden=true});
 layer.on('tileerror',()=>{
  if(generation!==baseLoadGeneration)return;
  errors++;
  if(success===0 && errors>=3 && providerIndex+1<providers.length){
   setBaseLayer(satellite,providerIndex+1);
  }else if(success===0&&errors>=3){
   $('map-fallback').hidden=false;
   $('map-fallback').textContent='Kartendienst nicht erreichbar. Bitte Verbindung prüfen.';
  }
 });
 layer.addTo(map);
 layer.bringToBack();
 $('satellite').textContent=satellite?'▦ Karta':'◫ Satellit';
}
function switchTiles(){setBaseLayer(state.satellite)}
function scheduledStops(v,clock){
 const base=Math.floor(clock.seconds/1800)*1800+({'metro-13':-370,'metro-19':-180,'commuter-43':-550,'rail-1':-240}[v.id]||0);
 return v.stops.map(s=>({...s,t:base+s.t}));
}
function vehicleAt(v,now){const stops=scheduledStops(v,now);return {...v,stops,pg:tripProgress(stops,now.seconds)}}
function visibleVehicles(){return services.filter(v=>matchesRailFilter(v,state.filter))}
function makeVehicleButton(v){
 const btn=document.createElement('button');btn.className='vehicle'+(state.selected?.id!==v.id&&state.selected?' muted':'');
 const badge=document.createElement('span');badge.className='line-pill';badge.style.background=v.color;badge.textContent=v.line;
 const center=document.createElement('span');
 const name=document.createElement('span');name.className='vehicle-title';name.textContent=v.title;
 const sub=document.createElement('span');sub.className='vehicle-sub';sub.textContent='Mot '+v.destination+' · Exempeltrafik';
 center.append(name,sub);
 const icon=document.createElement('span');icon.className='train-icon';icon.textContent='↗';
 btn.append(badge,center,icon);btn.addEventListener('click',()=>selectVehicle(v));return btn;
}
function refreshList(){
 if(railDataset){showRealList();return}
 const list=$('vehicle-list');list.replaceChildren(...visibleVehicles().map(makeVehicleButton));
}
function clearRoutes(){railLayer?.clearLayers();lastRouteUpdate=0;selectedRouteId=null;selectedRouteLines=null}
function routeFor(v){
 if(!map)return;
 railLayer.clearLayers();
 const {stops,pg}=v,idx=pg.next,position=pg.position;
 // Dashed schematic between approximate stops; NOT a verified railway line.
 const past=stops.slice(0,idx).map(s=>s.coord).concat([position]);
 const future=[position,...stops.slice(idx).map(s=>s.coord)];
 L.polyline(future,{color:'#78928a',weight:4,dashArray:'5 7',opacity:.82,interactive:false}).addTo(railLayer);
 L.polyline(past,{color:'#387e9f',weight:5,dashArray:'5 7',opacity:.96,interactive:false}).addTo(railLayer);
 for(const s of stops)L.circleMarker(s.coord,{radius:4,color:'#fff',weight:2,fillColor:'#4b8a7b',fillOpacity:1}).addTo(railLayer).bindTooltip(s.name);
}
function setSelected(v){
 state.selected=v;state.station=false;state.follow=false;
 $('selected-detail').hidden=false;$('vehicle-list').hidden=true;$('station-view').hidden=true;
 $('tab-trains').classList.add('active');$('tab-station')?.classList.remove('active');
 refreshList();updateFollow();refreshSelected();
 if(map){map.flyTo(vehicleAt(v,stockholmTime()).pg.position,12,{duration:1.15})}
}
function selectVehicle(v){setSelected(v)}
function clearSelected(){
 if(railDataset){clearReal();return}
 state.selected=null;state.follow=false;state.station=false;
 $('selected-detail').hidden=true;$('vehicle-list').hidden=false;$('station-view').hidden=true;
 $('tab-trains').classList.add('active');$('tab-station')?.classList.remove('active');
 clearRoutes();refreshList();updateFollow();
}
function updateFollow(){$('follow').textContent=state.follow?'◎ Följer tåget':'◎ Följ tåget';$('follow').classList.toggle('active',state.follow)}
function refreshSelected(){
 if(!state.selected)return;
 const now=stockholmTime(),v=vehicleAt(state.selected,now),idx=v.pg.next;
 $('train-heading').textContent=v.title+' → '+v.destination;
 $('train-sub').textContent='Demonstration · uppskattad position, ingen GPS';
 $('next-stop-name').textContent=v.stops[idx].name;
 $('next-stop-time').textContent='Exempel · '+secondsLabel(v.stops[idx].t);
 const value=occupancy(v,idx,now.weekday,Math.floor(now.seconds/3600));
 $('occupancy-value').textContent=value+'%';$('occupancy-fill').style.width=value+'%';
 const rows=v.stops.map((s,i)=>{
  const row=document.createElement('div');row.className='stop'+(i<idx?' passed':i===idx?' next':'');
  const name=document.createElement('span');name.textContent=s.name;
  const time=document.createElement('span');time.textContent=secondsLabel(s.t);
  row.append(name,time);return row});
 $('stops').replaceChildren(...rows);
 routeFor(v);lastRouteUpdate=performance.now();
}
function showStation(){
 state.station=true;state.follow=false;state.selected=null;clearRoutes();
 $('vehicle-list').hidden=true;$('selected-detail').hidden=true;$('station-view').hidden=false;
 $('tab-trains').classList.remove('active');$('tab-station')?.classList.add('active');
 const examples=[['SPÅR A','SJ Regional','Uppsala','#517e98'],['SPÅR B','Pendeltåg','Uppsala','#9169b0'],['SPÅR C','','Ledigt','#67888b'],['SPÅR D','Arlanda Express','Arlanda','#d2a44b']];
 $('platforms').replaceChildren(...examples.map(([num,train,dest,color])=>{
  const box=document.createElement('div');box.className='platform';
  const head=document.createElement('div');head.className='head';head.textContent=num;
  const track=document.createElement('div');track.className='track';
  if(train){const car=document.createElement('div');car.className='track-train';car.style.background=color;track.append(car)}
  const label=document.createElement('div');label.className='destination';label.textContent=train?train+' · '+dest:dest;
  box.append(head,track,label);return box
 }));
 if(map)map.flyTo(central,15,{duration:1.2});
}

let railDataset=null,realActive=[],realLastList=0,realLastDraw=0;
let selectedRouteId=null,selectedRouteLines=null;
let lastCameraFrame=0;let cameraAnimationStarted=false;
let photoSelection=0,lastPhotoVehicleId=null;
function showVerifiedPhoto(v){
 if(lastPhotoVehicleId===v.id)return;
 lastPhotoVehicleId=v.id;
 const token=++photoSelection,el=document.querySelector('.image-placeholder');
 if(!el)return;
 const pic=photoForVehicle(v);el.replaceChildren();
 if(!pic){el.textContent='Fordonssymbol · verifierat modellspecifikt foto saknas';return}
 const img=document.createElement('img');img.src='./'+pic.path;img.alt=pic.label||'Godkänt fordonsfoto';
 img.style.cssText='width:100%;height:170px;object-fit:cover;border-radius:9px';
 img.onerror=()=>{if(token===photoSelection)el.textContent='Fotot kunde inte laddas';};
 const link=document.createElement('a');link.href=pic.source;link.target='_blank';link.rel='noopener noreferrer';
 link.textContent=(pic.author||'Foto')+' · '+(pic.license||'Wikimedia Commons');link.style.cssText='font-size:10px;color:#587B74;margin-top:8px';
 if(pic.illustrative){
  const note=document.createElement('div');
  note.textContent=v.agency==='Tågab'?'Exempelbild av Tågab Rc3 med persontåg · exakt fordon för avgången ej verifierat':v.agency==='Vy Tåg'?'Exempelbild av Vy-tåg i Oslo · exakt fordon för avgången ej verifierat':v.agency==='Snälltåget'?'Exempelbild av Snälltåget · exakt fordonsmodell ej bekräftad':v.agency==='VR Snabbtåg'?'Exempelbild av VR Snabbtåg X74 · exakt fordon för avgången ej verifierat':v.agency==='Mälartåg'?'Exempelbild av Mälartåg · exakt fordon för avgången ej verifierat':'Exempelbild av SJ-tåg · fordonstyp för denna avgång ej verifierad';
  note.style.cssText='font-size:11px;color:#587B74;line-height:1.45;margin-top:5px';
  el.append(img,note,link);
 }else el.append(img,link);
}
// A compact transport pictogram; unlike the old large dot it stays readable
// at low zoom and never rebuilds for every animation frame.
const originalSpriteUrls=new Map();
function originalSpriteUrl(key){
 if(originalSpriteUrls.has(key))return originalSpriteUrls.get(key);
 const data=vehicleFrontSprites[key]||vehicleFrontSprites.rail;
 const encoded=data.split(',')[1];
 const binary=atob(encoded);
 const bytes=new Uint8Array(binary.length);
 for(let i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);
 const url=URL.createObjectURL(new Blob([bytes],{type:'image/webp'}));
 originalSpriteUrls.set(key,url);
 return url;
}
// The original Stockholm Transit vehicle-front photo sprites are restored here.
// Small sizes keep the network legible even with hundreds of rail vehicles.
// The original six photo sprites remain intact. Only operators with new
// approved photo markers are overridden; others keep their historical art.
function markerSpriteKey(v){
 const agency=String(v.agency||'').toLowerCase();
 if(agency==='mälartåg')return 'malartag';
 if(agency==='vr snabbtåg')return 'vr';
 if(agency==='snälltåget')return 'snalltaget';
 if(agency==='vy tåg')return 'vy';
 if(agency==='tågab')return 'tagab';
 if(agency==='sj'){
  // Select a specific SJ front only when the record actually identifies it.
  const type=String(v.vehicleType||v.vehicle_type||v.rollingStock||v.rolling_stock||v.trainType||'').toLowerCase();
  if(/x55|sj\\s*3000/.test(type))return 'sj3000';
  if(/x40/.test(type))return 'sj_x40';
  if(/rc6|intercity/.test(type))return 'sj_intercity';
  if(/night|natt|sovvagn/.test(type))return 'sj_night';
 }
 return null;
}
const operatorSpriteUrls=new Map();
function originalOperatorSpriteUrl(key){
 if(operatorSpriteUrls.has(key))return operatorSpriteUrls.get(key);
 const data=approvedTrainMarkers[key]||operatorMarkerSprites[key]||vyMarkerSprites[key];
 if(!data)return originalSpriteUrl('rail');
 const binary=atob(data.split(',')[1]);
 const bytes=new Uint8Array(binary.length);
 for(let i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);
 const url=URL.createObjectURL(new Blob([bytes],{type:'image/webp'}));
 operatorSpriteUrls.set(key,url);return url;
}
function miniRailIcon(v,chosen=false){
 const operatorKey=markerSpriteKey(v);
 const imageKey=v.mode==='tram'?'tram':v.mode==='metro'?'metro':
  v.mode==='commuter'?'commuter':v.mode==='localrail'?'localrail':v.mode==='saltsjo'?'localrail':v.mode==='express'?'rail_arlanda':v.mode==='rail'&&/arlanda express/i.test(v.agency+' '+v.destination)?'rail_arlanda':'rail';
 const img=operatorKey==='tagab'?tagabMarker:operatorKey&&(approvedTrainMarkers[operatorKey]||operatorMarkerSprites[operatorKey]||vyMarkerSprites[operatorKey])?originalOperatorSpriteUrl(operatorKey):originalSpriteUrl(imageKey);
 const size=chosen?27:19;
 const html='<img alt="" aria-hidden="true" draggable="false" class="rail-photo-marker" src="'+img+'">';
 return L.divIcon({className:'rail-photo-icon'+(chosen?' is-selected':''),html,iconSize:[size,size],iconAnchor:[size/2,size/2]});
}
const railColors={metro:'#CB5264',commuter:'#4D80BB',tram:'#E78B35',rail:'#C89D52'};
function realColor(v){
 if(v.mode==='regional')return '#8066A3';
 if(v.mode==='intercity'&&v.agency==='VR Snabbtåg')return '#326E78';
  if(v.mode==='intercity'&&v.agency==='Snälltåget')return '#B93A43';
 if(v.mode==='intercity'&&v.agency==='Vy Tåg')return '#167D79';
 if(v.mode==='intercity'&&v.agency==='Tågab')return '#A24837';
 if(v.mode==='intercity')return '#9D565F';
 if(v.mode==='express')return '#E4AE20';
 if(v.mode==='saltsjo')return '#517BA0';
 if(v.mode==='localrail')return '#7956A7';
 if(v.mode==='metro'){
  const n=Number(v.line);
  return n===10||n===11?'#3178C4':n===13||n===14?'#CF5364':'#4B997C';
 }
 return railColors[v.mode]||'#537F85';
}
function realTitle(v){return (v.mode==='express'?'Arlanda Express':(v.line||v.train||v.mode.toUpperCase()))+' · '+(v.destination||'Stockholm')}
// Fair ordering for "Alla tåg": otherwise Pendeltåg can occupy the first
// 90 list items and 280 map markers while all other systems are present.
function displayOrder(trips){
 if(state.filter!=='all')return trips;
 const keys=[
  ['commuter',t=>t.mode==='commuter'],
  ['metro',t=>t.mode==='metro'],
  ['tvar',t=>t.mode==='tram'&&['30','31'].includes(String(t.line))],
  ['nockeby',t=>String(t.line)==='12'&&t.mode==='tram'],
  ['lidingo',t=>String(t.line)==='21'&&t.mode==='tram'],
  ['city7',t=>String(t.line)==='7'&&t.mode==='tram'],
  ['roslags',t=>t.mode==='localrail'],
  ['saltsjo',t=>t.mode==='saltsjo'],
  ['arlanda',t=>t.mode==='express'],
  ['sj',t=>t.mode==='intercity'&&t.agency==='SJ'],
  ['vr',t=>t.mode==='intercity'&&t.agency==='VR Snabbtåg'],
  ['snalltaget',t=>t.mode==='intercity'&&t.agency==='Snälltåget'],
  ['vy',t=>t.mode==='intercity'&&t.agency==='Vy Tåg'],
  ['tagab',t=>t.mode==='intercity'&&t.agency==='Tågab'],
  ['malartag',t=>t.mode==='regional'&&t.agency==='Mälartåg']
 ];
 const queues=keys.map(([_,match])=>trips.filter(match));
 const used=new Set(queues.flat().map(t=>t.id));
 const leftovers=trips.filter(t=>!used.has(t.id));
 const arranged=[];
 let depth=0,more=true;
 while(more){
  more=false;
  for(const q of queues){
   if(depth<q.length){arranged.push(q[depth]);more=true;}
  }
  depth++;
 }
 return arranged.concat(leftovers);
}
function showRealList(){
 if(!railDataset)return;
 const list=$('vehicle-list');list.innerHTML='';
 const frag=document.createDocumentFragment();
 for(const v of displayOrder(realActive.filter(v=>matchesRailFilter(v,state.filter))).slice(0,90)){
  const btn=document.createElement('button');btn.className='vehicle'+(state.selected&&state.selected.id!==v.id?' muted':'');
  const chip=document.createElement('span');chip.className='line-pill';chip.style.background=realColor(v);chip.textContent=(v.line||v.mode.slice(0,2).toUpperCase());
  const t=document.createElement('span');
  const name=document.createElement('span');name.className='vehicle-title';name.textContent=realTitle(v);
  const sub=document.createElement('span');sub.className='vehicle-sub';sub.textContent=v.agency==='Tågab'?'Historiska Tågab-avgångar · upprepas dagligen · ingen live-GPS':v.agency==='Vy Tåg'?'Historiska Vy-avgångar · upprepas dagligen · ingen live-GPS':(v.mode==='tram'&&String(v.line)==='21'&&v.archiveDay==='2026-11-07')?'Historiskt lördagsschema · simulerad reservavgång':v.timetableProxy?'Historisk fredagsavgång · upprepas varje dag':railDataset?.type?.startsWith('historical-')?'Historiskt dagsmönster · simulerat':v.agency+' · Tidtabell, ingen GPS';
  t.append(name,sub);btn.append(chip,t);btn.onclick=()=>selectReal(v);frag.append(btn);
 }
 list.append(frag);
 if(!frag.childNodes.length && !list.childNodes.length){
  const empty=document.createElement('div');
  empty.className='vehicle-sub';
  empty.style.cssText='padding:18px 4px;line-height:1.6';
  empty.textContent=state.filter==='tagab'?'Inga historiska Tågab-avgångar vid denna tidpunkt. Avgångarna upprepas dagligen i simuleringen.':state.filter==='vy'?'Inga historiska Vy-avgångar vid denna tidpunkt. Avgångarna upprepas varje dag i simuleringen.': 'Inga verifierade tåg för den valda linjen vid aktuell tid. Historiska tidtabeller kan sakna avgångar; inga tågpositioner hittas på.';
  list.append(empty);
 }
}
function selectReal(v){
 lastPhotoVehicleId=null;
 state.selected=v;state.station=false;state.follow=false;selectedRouteId=null;selectedRouteLines=null;
 $('vehicle-list').hidden=true;$('station-view').hidden=true;$('selected-detail').hidden=false;
 $('tab-trains').classList.add('active');$('tab-station')?.classList.remove('active');
 updateFollow();showRealDetail();
 const p=railAt(v,Date.now()/1000).pos;if(map)map.flyTo(p,12,{duration:1});
}
function clearReal(){
 lastPhotoVehicleId=null;
 state.selected=null;state.follow=false;clearRoutes();
 $('vehicle-list').hidden=false;$('selected-detail').hidden=true;$('station-view').hidden=true;
 $('tab-trains').classList.add('active');$('tab-station')?.classList.remove('active');
 showRealList();updateFollow();
}
function showRealDetail(){
 const v=state.selected;if(!v||!railDataset)return;
 const epoch=Date.now()/1000,current=railAt(v,epoch),idx=current.next;
 const stops=v.stops,first=stops[0][3],base=v.start-first;
 $('train-heading').textContent=realTitle(v);
 showVerifiedPhoto(v);
 $('train-sub').textContent=(v.mode==='tram'&&String(v.line)==='21'&&v.archiveDay==='2026-11-07')?'Historiskt lördagsschema som simulerad reservavgång · OSM-spår, ingen GPS':v.timetableProxy?'Historisk fredagstidtabell varje dag · OSM-spår, ingen GPS':railDataset?.type?.startsWith('historical-')?(['verified-osm-relation','verified-osm-rail-ways'].includes(v.geometryQuality)?'Historiskt veckoschema · OSM-spår · simulerad position':'Historiskt veckoschema · ungefärlig färdväg · ingen GPS'):'GTFS · '+v.agency+' · Planerad färd, ingen GPS';
 if(v.stopAlignmentCaveat)$('train-sub').textContent+=' · Enebybergs stationspunkt avviker cirka 690 m från OSM-linjen';
 $('next-stop-name').textContent=stops[idx][2];
 const toTime=s=>new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Stockholm',hour:'2-digit',minute:'2-digit'}).format(new Date((base+s)*1000));
 $('next-stop-time').textContent='Plan '+toTime(stops[idx][3]);
 const mock={id:v.id,stops:stops.map(s=>({name:s[2]}))},now=stockholmTime();
 const occ=occupancy(mock,idx,now.weekday,Math.floor(now.seconds/3600));
 $('occupancy-value').textContent=occ+'%';$('occupancy-fill').style.width=occ+'%';
 const speed=$('speed-value');if(speed)speed.textContent=current.kmh+' km/h';
 const container=$('stops');container.innerHTML='';
 for(let i=0;i<stops.length;i++){
  const node=document.createElement('div');node.className='stop'+(i<idx?' passed':i===idx?' next':'');
  const label=document.createElement('span');label.textContent=stops[i][2];
  const time=document.createElement('span');time.textContent=toTime(stops[i][3]);
  node.append(label,time);container.append(node);
 }
 if(map){
  const segments=railPathSplit(v,current.meters);
  const approximate=false; // Pendeltåg build rejects unverified geometry
  if(selectedRouteId!==v.id||!selectedRouteLines){
   railLayer.clearLayers();
   selectedRouteId=v.id;
   selectedRouteLines={
    future:L.polyline(segments.future,{color:'#728F93',weight:4,opacity:.82,...(approximate?{dashArray:'6 7'}:{})}).addTo(railLayer),
    past:L.polyline(segments.past,{color:'#267FAC',weight:5,opacity:.97,...(approximate?{dashArray:'6 7'}:{})}).addTo(railLayer)
   };
   for(const stop of stops)L.circleMarker([stop[0],stop[1]],{radius:3,fillColor:'#fff',fillOpacity:1,color:'#458578'}).addTo(railLayer).bindTooltip(stop[2]);
  }else{
   selectedRouteLines.future.setLatLngs(segments.future);
   selectedRouteLines.past.setLatLngs(segments.past);
  }
 }
}
// Camera advances independently of timetable polling and marker redraws.
function followFrame(timestamp){
 requestAnimationFrame(followFrame);
 if(!map||!railDataset||!state.follow||!state.selected||state.station){
  lastCameraFrame=timestamp;return;
 }
 if(timestamp-lastCameraFrame<30)return;
 const dt=Math.min(90,Math.max(1,timestamp-lastCameraFrame||33));
 lastCameraFrame=timestamp;
 const p=railAt(state.selected,Date.now()/1000).pos,c=map.getCenter();
 const currentMarker=markers.get(state.selected.id);
 if(currentMarker)currentMarker.setLatLng(p);
 const d=map.distance(c,p);if(d<1.4)return;
 // Exponential damping prevents jerks on 100 ms marker and 15 s data updates.
 const alpha=1-Math.exp(-dt/270);
 map.panTo([c.lat+(p[0]-c.lat)*alpha,c.lng+(p[1]-c.lng)*alpha],{animate:false,noMoveStart:true});
}
function tickReal(){
 const now=Date.now(),epoch=now/1000;
 $('clock').textContent=stockholmTime(now).display;
 if(now-realLastList>15000){
  realActive=activeRailTrips(railDataset,epoch,10000);realLastList=now;showRealList();
  if(state.selected&&!realActive.some(v=>v.id===state.selected.id))clearReal();
 }
 if(!map||now-realLastDraw<90)return;realLastDraw=now;
 const selected=state.selected;
 const showing=displayOrder(realActive.filter(v=>matchesRailFilter(v,state.filter)));
 const seen=new Set(showing.map(v=>v.id));
 for(const [id,m] of markers)if(!seen.has(id)){map.removeLayer(m);markers.delete(id)}
 const bounds=map.getBounds().pad(.12);
 let drawn=0;
 for(const v of showing){
  const p=railAt(v,epoch).pos;
  const selectedHere=selected?.id===v.id;
  let marker=markers.get(v.id);
  if(!bounds.contains(p)&&!selectedHere){
   if(marker){map.removeLayer(marker);markers.delete(v.id)}
   continue;
  }
  // Keep the selected train even when crowded, prevent excessive DOM markers.
  if(drawn>=280&&!selectedHere){
   if(marker){map.removeLayer(marker);markers.delete(v.id)}continue;
  }
  drawn++;
  if(!marker){
   marker=L.marker(p,{icon:miniRailIcon(v,selectedHere),keyboard:false,riseOnHover:true}).addTo(map);
   marker.on('click',()=>selectReal(v));markers.set(v.id,marker);
   marker._railStyle=selectedHere?'selected':'normal';
  }else marker.setLatLng(p);
  const markerStyle=selectedHere?'selected':selected?'dimmed':'normal';
  if(marker._railStyle!==markerStyle){
   marker._railStyle=markerStyle;
   marker.setOpacity(markerStyle==='dimmed'?.27:1);
   marker.setIcon(miniRailIcon(v,selectedHere));
   marker.setZIndexOffset(selectedHere?1100:0);
  }
 }
 if(selected&&now-lastRouteUpdate>1400){showRealDetail();lastRouteUpdate=now}
}

async function initializeReal(){
 const data=await loadRailTimetable();
 if(!data){$('vehicle-list').textContent='Verifierade spårdata saknas. Tidigare version är oförändrad.';return;}
 railDataset=data;
 state.selected=null;state.follow=false;markers.forEach(m=>map?.removeLayer(m));markers.clear();clearRoutes();
 $('vehicle-list').hidden=false;$('selected-detail').hidden=true;
 const label=document.querySelector('.map-note strong');if(label)label.textContent='PENDELTÅG · TUNNELBANA · TVÄRBANAN · LOKALBANOR · SPÅRVÄG CITY · ROSLAGSBANAN · SALTSJÖBANAN · ARLANDA EXPRESS · SJ · MÄLARTÅG';
 const hint=document.querySelector('.map-note span');
 if(hint){
   if(data.type?.startsWith('historical-')){
     const verified=Object.values(data.routeRefinement?.verifiedTrips||{}).reduce((sum,n)=>sum+Number(n||0),0);
     const total=data.trips.length;
     hint.textContent=data.counts.commuter+' Pendeltåg + '+data.counts.metro+' Tunnelbana + '+(data.tramLines['30']+data.tramLines['31'])+' Tvärbanan + '+data.tramLines['12']+' Nockebybanan + '+data.tramLines['21']+' Lidingöbanan + '+data.tramLines['7']+' Spårväg City + '+data.counts.localrail+' Roslagsbanan + '+data.counts.saltsjo+' Saltsjöbanan + '+data.counts.express+' Arlanda Express + '+((data.counts.intercity||0)-(data.vrDirections?Object.values(data.vrDirections).reduce((a,n)=>a+n,0):0)-(data.snalltagetDirections?Object.values(data.snalltagetDirections).reduce((a,n)=>a+n,0):0))+' SJ + '+(data.vrDirections?Object.values(data.vrDirections).reduce((a,n)=>a+n,0):0)+' VR Snabbtåg + '+(data.counts.regional||0)+' Mälartåg + '+(data.snalltagetDirections?Object.values(data.snalltagetDirections).reduce((a,n)=>a+n,0):0)+' Snälltåget · historisk tidtabell, simulerade positioner';
   }else hint.textContent='Planerade positioner på verifierade GTFS-linjer · ingen GPS';
 }
 const heading=document.querySelector('.sidebar-heading h1');if(heading)heading.textContent=railFilterTitle(state.filter);
 realLastList=0;tickReal();
}
function tick(){
 if(railDataset){tickReal();return}
 $('clock').textContent=stockholmTime().display;
 return;
 const now=stockholmTime();$('clock').textContent=now.display;
 if(map){
  const visible=visibleVehicles(),shown=new Set(visible.map(v=>v.id));
  for(const [id,m] of markers){if(!shown.has(id)){map.removeLayer(m);markers.delete(id)}}
  for(const v of visible){
   const current=vehicleAt(v,now),chosen=state.selected?.id===v.id,dimmed=!!state.selected&&!chosen;
   let m=markers.get(v.id);
   if(!m){
    m=L.marker(current.pg.position).addTo(map);markers.set(v.id,m);
    m.on('click',()=>selectVehicle(v));
   }else m.setLatLng(current.pg.position);
   const key=[chosen,dimmed].join(':');
   if(m._railStyle!==key){
    m._railStyle=key;
    m.setIcon(L.divIcon({html:`<div class="train-marker" style="background:${v.color};opacity:${dimmed?.34:1};transform:scale(${chosen?1.2:1})">▣</div>`,iconSize:[24,24],iconAnchor:[12,12],className:''}));
    m.setZIndexOffset(chosen?1000:0);
   }
   if(chosen){
    const nowMs=performance.now();
    if(nowMs-lastRouteUpdate>1100){routeFor(current);lastRouteUpdate=nowMs}
    if(state.follow){
     const center=map.getCenter(),target=L.latLng(current.pg.position);
     if(map.distance(center,target)>4)map.panTo([center.lat+(target.lat-center.lat)*.06,center.lng+(target.lng-center.lng)*.06],{animate:false});
    }
   }
  }
 }
 const time=performance.now();
 if(state.selected&&time-lastDetailUpdate>1900){lastDetailUpdate=time;refreshSelected()}
}
// The SJ expansion can leave the camera zoomed out over Scandinavia.
// Keep Lidingöbanan focused on the verified Ropsten–Gåshaga endpoints,
// including when there is a temporary gap in the historical timetable.
function focusLidingoLine(){
 if(!map||!railDataset)return;
 const journey=railDataset.trips.find(t=>
   matchesRailFilter(t,'lidingo') &&
   ['verified-osm-relation','verified-osm-rail-ways'].includes(t.geometryQuality) &&
   Array.isArray(t.stops)&&t.stops.length>=2);
 if(!journey)return;
 const points=journey.stops.map(stop=>[Number(stop[0]),Number(stop[1])])
   .filter(p=>p.every(Number.isFinite));
 if(points.length<2)return;
 const bounds=L.latLngBounds(points);
 if(bounds.isValid())map.flyToBounds(bounds,{padding:[65,65],maxZoom:13,duration:1.0});
}
function focusMalartagPilot(){
 if(!map||!railDataset)return;
 const trips=railDataset.trips.filter(t=>matchesRailFilter(t,'malartag')&&
   ['verified-osm-relation','verified-osm-rail-ways'].includes(t.geometryQuality)&&Array.isArray(t.stops));
 if(!trips.length)return;
 const points=trips.flatMap(t=>t.stops.map(s=>[Number(s[0]),Number(s[1])]))
   .filter(p=>p.every(Number.isFinite));
 if(points.length<2)return;
 const bounds=L.latLngBounds(points);
 if(bounds.isValid())map.flyToBounds(bounds,{padding:[50,50],maxZoom:10,duration:1});
}
// Zoom to the verified Stockholm–Göteborg corridor while leaving Follow,
// satellite tiles, train times and all other railway cameras untouched.
function focusVrSnabbtag(){
 if(!map||!railDataset)return;
 const trip=railDataset.trips.find(t=>matchesRailFilter(t,'vr')&&
   ['verified-osm-relation','verified-osm-rail-ways'].includes(t.geometryQuality)&&
   Array.isArray(t.stops));
 if(!trip)return;
 const points=trip.stops.map(s=>[Number(s[0]),Number(s[1])])
  .filter(p=>p.every(Number.isFinite));
 if(points.length<2)return;
 const bounds=L.latLngBounds(points);
 if(bounds.isValid())map.flyToBounds(bounds,{padding:[50,50],maxZoom:8,duration:1.1});
}
// Focus only the genuine archived Snälltåget Stockholm–Malmö route.
function focusSnalltaget(){
 if(!map||!railDataset)return;
 const t=railDataset.trips.find(v=>matchesRailFilter(v,'snalltaget')&&
   v.geometryQuality==='verified-osm-relation'&&Array.isArray(v.stops));
 if(!t)return;
 const points=t.stops.map(s=>[Number(s[0]),Number(s[1])])
  .filter(p=>p.every(Number.isFinite));
 if(points.length<2)return;
 const box=L.latLngBounds(points);
 if(box.isValid())map.flyToBounds(box,{padding:[50,50],maxZoom:8,duration:1.1});
}
// Focus only real GTFS Vy Tåg Stockholm–Oslo stations; rail path itself is verified OSM.
function focusVyTåg(){
 if(!map||!railDataset)return;
 const t=railDataset.trips.find(v=>v.agency==='Vy Tåg'&&Array.isArray(v.stops)&&v.geometryQuality==='verified-osm-rail-ways');
 if(!t)return;
 const pts=t.stops.map(s=>[Number(s[0]),Number(s[1])]).filter(p=>p.every(Number.isFinite));
 const b=L.latLngBounds(pts);if(b.isValid())map.flyToBounds(b,{padding:[50,50],maxZoom:7,duration:1.1});
}
// Only frame actual historical Tågab stations, never use synthetic route lines.
function focusTagab(){
 if(!map||!railDataset)return;
 const t=railDataset.trips.find(v=>v.agency==='Tågab'&&v.destination?.includes('Göteborg')&&v.geometryQuality==='verified-osm-rail-ways');
 if(!t)return;
 const pts=t.stops.map(s=>[Number(s[0]),Number(s[1])]).filter(p=>p.every(Number.isFinite));
 if(pts.length<2)return;
 const b=L.latLngBounds(pts);
 if(b.isValid())map.flyToBounds(b,{padding:[50,50],maxZoom:7,duration:1.1});
}
function start(){
 setupMap();$('vehicle-list').textContent='Läser in verifierade Pendeltåg-, Tunnelbana- och Tvärbanan-rutter…';
 document.querySelectorAll('[data-filter]').forEach(b=>b.onclick=()=>{
  state.filter=b.dataset.filter;
  realLastList=0; // selected line refreshes before drawing
  const heading=document.querySelector('.sidebar-heading h1');
  if(heading)heading.textContent=railFilterTitle(state.filter);
  document.querySelectorAll('[data-filter]').forEach(x=>x.classList.toggle('active',x===b));
  if(state.selected&&!matchesRailFilter(state.selected,state.filter))clearSelected();
  if(state.filter==='lidingo')focusLidingoLine();
  if(state.filter==='malartag')focusMalartagPilot();
  if(state.filter==='vr')focusVrSnabbtag();
  if(state.filter==='snalltaget')focusSnalltaget();
  if(state.filter==='vy')focusVyTåg();
  if(state.filter==='tagab')focusTagab();
  refreshList();tick();
 });
 $('satellite').onclick=()=>{state.satellite=!state.satellite;switchTiles()};
 $('home').onclick=()=>{clearSelected();map?.flyTo([59.334,18.058],11,{duration:1.1})};
 $('tab-trains').onclick=clearSelected;
 $('clear').onclick=clearSelected;
 $('follow').onclick=()=>{state.follow=!state.follow;updateFollow()};
 tick();setInterval(tick,100);requestAnimationFrame(followFrame);loadPhotoCatalog().then(()=>{lastPhotoVehicleId=null;if(state.selected&&railDataset)showVerifiedPhoto(state.selected)});initializeReal();
}
start();
