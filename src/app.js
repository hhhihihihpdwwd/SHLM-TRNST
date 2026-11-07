import {stockholmTime,tripProgress,occupancy,secondsLabel} from './simulation.js';
import {services,central} from './demo-data.js';
const $=id=>document.getElementById(id);
const state={filter:'all',selected:null,follow:false,satellite:false,station:false};
let map,roads,railLayer,lastRouteUpdate=0,markers=new Map(),lastDetailUpdate=0;
function setupMap(){
 if(!window.L){$('map-fallback').hidden=false;return}
 map=L.map('map',{zoomControl:false,preferCanvas:true}).setView([59.334,18.058],11);
 L.control.zoom({position:'bottomright'}).addTo(map);
 roads=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,updateWhenIdle:true,keepBuffer:2,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'}).addTo(map);
 railLayer=L.layerGroup().addTo(map);
 map.on('dragstart zoomstart',()=>{state.follow=false;updateFollow()});
}
function switchTiles(){
 if(!map)return;
 if(roads)map.removeLayer(roads);
 const sat=state.satellite;
 roads=L.tileLayer(sat?'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}':'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
 {maxZoom:19,updateWhenIdle:true,keepBuffer:2,attribution:sat?'Tiles &copy; Esri':'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'}).addTo(map);
 roads.bringToBack();
 $('satellite').textContent=sat?'▦ Karta':'◫ Satellit';
}
function scheduledStops(v,clock){
 const base=Math.floor(clock.seconds/1800)*1800+({'metro-13':-370,'metro-19':-180,'commuter-43':-550,'rail-1':-240}[v.id]||0);
 return v.stops.map(s=>({...s,t:base+s.t}));
}
function vehicleAt(v,now){const stops=scheduledStops(v,now);return {...v,stops,pg:tripProgress(stops,now.seconds)}}
function visibleVehicles(){return services.filter(v=>state.filter==='all'||v.mode===state.filter)}
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
 const list=$('vehicle-list');list.replaceChildren(...visibleVehicles().map(makeVehicleButton));
}
function clearRoutes(){railLayer?.clearLayers();lastRouteUpdate=0}
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
 $('tab-trains').classList.add('active');$('tab-station').classList.remove('active');
 refreshList();updateFollow();refreshSelected();
 if(map){map.flyTo(vehicleAt(v,stockholmTime()).pg.position,12,{duration:1.15})}
}
function selectVehicle(v){setSelected(v)}
function clearSelected(){
 state.selected=null;state.follow=false;state.station=false;
 $('selected-detail').hidden=true;$('vehicle-list').hidden=false;$('station-view').hidden=true;
 $('tab-trains').classList.add('active');$('tab-station').classList.remove('active');
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
 $('tab-trains').classList.remove('active');$('tab-station').classList.add('active');
 const examples=[['SPÅR A','SJ Regional','Uppsala','#517e98'],['SPÅR B','Mälartåg','Västerås','#9169b0'],['SPÅR C','','Ledigt','#67888b'],['SPÅR D','Arlanda Express','Arlanda','#d2a44b']];
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
function tick(){
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
function start(){
 setupMap();refreshList();
 document.querySelectorAll('[data-filter]').forEach(b=>b.onclick=()=>{
  state.filter=b.dataset.filter;
  document.querySelectorAll('[data-filter]').forEach(x=>x.classList.toggle('active',x===b));
  if(state.selected&&state.filter!=='all'&&state.selected.mode!==state.filter)clearSelected();
  refreshList();tick();
 });
 $('satellite').onclick=()=>{state.satellite=!state.satellite;switchTiles()};
 $('home').onclick=()=>{clearSelected();map?.flyTo([59.334,18.058],11,{duration:1.1})};
 $('tab-trains').onclick=clearSelected;$('tab-station').onclick=showStation;
 $('clear').onclick=clearSelected;
 $('follow').onclick=()=>{state.follow=!state.follow;updateFollow()};
 tick();setInterval(tick,100);
}
start();
