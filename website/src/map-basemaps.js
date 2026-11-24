/**
 * Stockholm Rail — optional three-way basemap control.
 *
 * Presentation only: NEVER modifies GTFS trips, simulated vehicle positions,
 * marker sprites, selected train lines, map bounds, or follow state.
 *
 * Hybrid combines the EXACT same Esri World Imagery raster as Satellit with
 * Esri's transparent World Transportation (roads / railways) and World
 * Boundaries and Places (street/place labels) reference tiles. Leaflet panes
 * put both reference layers ABOVE imagery but BELOW selected-train routes and
 * markers. This requires no Google API key and never scrapes Google tiles.
 */
const IMAGERY={
 url:'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
 credit:'Imagery &copy; Esri, Maxar, Earthstar Geographics, GIS User Community'
};
const MAP_STYLES=Object.freeze({
 standard:{label:'Karta',base:[
  {url:'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
   credit:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'},
  {url:'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
   credit:'Tiles &copy; Esri'}
 ]},
 satellite:{label:'Satellit',base:[IMAGERY]},
 hybrid:{label:'Hybrid',base:[IMAGERY]}
});
const TRANSPORT={
 url:'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}',
 credit:'Vägar och järnvägar &copy; Esri, HERE, OpenStreetMap contributors',
 pane:'sr-hybrid-transport'
};
const LABELS={
 url:'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
 credit:'Ortnamn och gränser &copy; Esri',
 pane:'sr-hybrid-labels'
};
const STORAGE_KEY='stockholm-rail-basemap-v1';

/**
 * @param {L.Map} map An already created Leaflet map.
 * @returns {{current:()=>string,select:(style:string)=>void}}
 */
export function initializeBasemapControl(map){
 const root=document.getElementById('basemap-control');
 const trigger=document.getElementById('satellite');
 const menu=document.getElementById('basemap-menu');
 const label=document.getElementById('basemap-current-label');
 const warning=document.getElementById('basemap-warning');
 const mapFallback=document.getElementById('map-fallback');
 if(!map||!root||!trigger||!menu||!label){
  throw new Error('Missing Stockholm Rail basemap controls');
 }
 const choices=[...menu.querySelectorAll('[data-basemap]')];
 let current='standard',baseLayer=null,referenceLayers=[];
 let generation=0;

 for(const [name,z] of [['sr-hybrid-transport','340'],['sr-hybrid-labels','355']]){
  if(!map.getPane(name))map.createPane(name);
  const pane=map.getPane(name);
  pane.style.zIndex=z;
  pane.style.pointerEvents='none';
 }

 function notify(text=''){
  warning.hidden=!text;
  warning.textContent=text;
 }
 function menuOpen(open,focusTrigger=false){
  menu.hidden=!open;
  trigger.setAttribute('aria-expanded',open?'true':'false');
  root.classList.toggle('is-open',open);
  if(focusTrigger)trigger.focus();
 }
 function syncChoice(){
  label.textContent=MAP_STYLES[current].label;
  trigger.setAttribute('title','Kartvy: '+MAP_STYLES[current].label+' – välj karttyp');
  choices.forEach(choice=>{
   const selected=choice.dataset.basemap===current;
   choice.classList.toggle('is-selected',selected);
   choice.setAttribute('aria-pressed',selected?'true':'false');
  });
 }
 function clearLayers(){
  if(baseLayer){map.removeLayer(baseLayer);baseLayer=null;}
  for(const layer of referenceLayers)map.removeLayer(layer);
  referenceLayers=[];
 }

 function addBase(style,providerIndex,token){
  const list=MAP_STYLES[style].base;
  const provider=list[providerIndex];
  if(!provider)return;
  let errors=0,success=0;
  const tile=L.tileLayer(provider.url,{
   maxZoom:19,updateWhenIdle:true,keepBuffer:2,attribution:provider.credit
  });
  baseLayer=tile;
  tile.on('tileload',()=>{
   if(generation!==token||baseLayer!==tile)return;
   success++;
   mapFallback.hidden=true;
  });
  tile.on('tileerror',()=>{
   if(generation!==token||baseLayer!==tile)return;
   errors++;
   if(errors<3||success>0)return;
   if(providerIndex+1<list.length){
    map.removeLayer(tile);
    addBase(style,providerIndex+1,token);
   }else{
    mapFallback.hidden=false;
    mapFallback.textContent='Kartbilderna kunde inte läsas in. Kontrollera anslutningen.';
   }
  });
  tile.addTo(map);
  // Existing train-route pane (z-index 400) and vehicle markers (600)
  // stay ABOVE both the base map and the two reference panes.
  tile.bringToBack();
 }

 function addHybridReference(part,token){
  const overlay=L.tileLayer(part.url,{
   pane:part.pane,maxZoom:19,updateWhenIdle:true,keepBuffer:2,
   opacity:1,attribution:part.credit,
  });
  let failed=0,loaded=0;
  overlay.on('tileload',()=>{
   if(generation!==token)return;
   loaded++;
   overlay._srLoaded=true;
   if(referenceLayers.every(x=>x._srLoaded))notify('');
  });
  overlay.on('tileerror',()=>{
   if(generation!==token)return;
   failed++;
   if(failed>=3&&loaded===0){
    notify('Vissa kartetiketter kan inte visas just nu. Satellitbilden och tågen fungerar ändå.');
   }
  });
  referenceLayers.push(overlay);
  overlay.addTo(map);
 }

 function select(style,{persist=true}={}){
  if(!Object.prototype.hasOwnProperty.call(MAP_STYLES,style))return;
  const token=++generation;
  clearLayers();
  current=style;
  syncChoice();
  notify();
  mapFallback.hidden=true;
  if(persist){
   try{window.localStorage.setItem(STORAGE_KEY,style);}catch{/* blocked storage: mode still works */}
  }
  addBase(style,0,token);
  if(style==='hybrid'){
   addHybridReference(TRANSPORT,token);
   addHybridReference(LABELS,token);
  }
  menuOpen(false);
  // Preserve map center, zoom, active line filter, route and follow unchanged.
 }

 trigger.addEventListener('click',()=>menuOpen(menu.hidden));
 choices.forEach(choice=>choice.addEventListener('click',()=>select(choice.dataset.basemap)));
 menu.addEventListener('keydown',event=>{
  if(event.key==='Escape'){event.preventDefault();menuOpen(false,true);return;}
  if(event.key==='ArrowDown'||event.key==='ArrowUp'){
   event.preventDefault();
   const index=choices.indexOf(document.activeElement);
   choices[(index+(event.key==='ArrowDown'?1:-1)+choices.length)%choices.length].focus();
  }
 });
 document.addEventListener('keydown',event=>{
  if(event.key==='Escape'&&!menu.hidden)menuOpen(false,true);
 });
 document.addEventListener('pointerdown',event=>{
  if(!menu.hidden&&!root.contains(event.target))menuOpen(false);
 });
 // Map is not rebuilt, so camera/follow/filter stay in place on style changes.
 let remembered='standard';
 try{
  const saved=window.localStorage.getItem(STORAGE_KEY);
  if(Object.prototype.hasOwnProperty.call(MAP_STYLES,saved))remembered=saved;
 }catch{/* localStorage unavailable */}
 select(remembered,{persist:false});
 return {current:()=>current,select};
}
