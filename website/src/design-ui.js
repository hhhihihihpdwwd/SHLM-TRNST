/**
 * Stockholm Rail design shell. Pure presentation: intentionally no GTFS,
 * geographic route, train marker, timetable, or source-data modifications.
 */
const FILTER_ACCENTS={
 commuter:'#3975ad',metro:'#bc576c',tram:'#dc8239',
 nockeby:'#d49640',lidingo:'#35917f',city7:'#be414c',
 roslags:'#8563b2',saltsjo:'#487ca2',arlanda:'#d3a02d',
 sj:'#a34e5d',vr:'#257782',snalltaget:'#b94148',
 vy:'#287e77',tagab:'#a65c40',rdc:'#6953a0',malartag:'#8264b1'
};
let carouselButtons=[];
let currentKey='commuter';
let lastKey='commuter';
let infoOpen=false;

function cycle(step) {
 const index=carouselButtons.findIndex(b=>b.dataset.filter===lastKey);
 const n=carouselButtons.length;
 if(!n)return;
 const next=carouselButtons[(index+step+n)%n];
 next?.click(); // Use the ORIGINAL app's filter handler and state, never a parallel filter.
}
function updateCarousel(filter) {
 currentKey=filter;
 if(filter!=='all'&&carouselButtons.some(b=>b.dataset.filter===filter))lastKey=filter;
 const n=carouselButtons.length;
 const index=carouselButtons.findIndex(b=>b.dataset.filter===lastKey);
 carouselButtons.forEach((b,i)=>{
  let role='hidden';
  if(i===index)role='current';
  else if((i+1)%n===index)role='prev';
  else if((index+1)%n===i)role='next';
  b.dataset.carouselPosition=role;
  b.tabIndex=role==='hidden'?-1:0;
  b.setAttribute('aria-hidden',role==='hidden'?'true':'false');
  b.setAttribute('aria-pressed',filter===b.dataset.filter?'true':'false');
  b.title=b.textContent.trim();
 });
 const all=document.querySelector('.all-trains-button');
 if(all){
  all.classList.toggle('active',filter==='all');
  all.setAttribute('aria-pressed',filter==='all'?'true':'false');
 }
 document.querySelector('.rail-navigation')?.style.setProperty('--rail-active-color',FILTER_ACCENTS[lastKey]||'#264f58');
}
export function syncRailCarousel(filter){updateCarousel(filter)}

export function initializeDesignChrome() {
 carouselButtons=Array.from(document.querySelectorAll('.mode-switch button[data-filter]'));
 carouselButtons.forEach(button=>{
  button.style.setProperty('--line-accent',FILTER_ACCENTS[button.dataset.filter]||'#547a82');
  button.setAttribute('aria-label','Visa '+button.textContent.trim());
 });
 const navigation=document.querySelector('.rail-navigation');
 document.getElementById('rail-prev')?.addEventListener('click',()=>cycle(-1));
 document.getElementById('rail-next')?.addEventListener('click',()=>cycle(1));
 navigation?.addEventListener('keydown',event=>{
  if(event.key==='ArrowRight'||event.key==='ArrowLeft'){
   event.preventDefault();cycle(event.key==='ArrowRight'?1:-1);
  }
 });
 // Native touch gestures, not a fake CSS-only sliding control.
 let pointer=null;
 navigation?.addEventListener('touchstart',event=>{
  const p=event.changedTouches?.[0];
  if(p)pointer={x:p.clientX,y:p.clientY};
 },{passive:true});
 navigation?.addEventListener('touchend',event=>{
  const p=event.changedTouches?.[0];
  if(!pointer||!p)return;
  const dx=p.clientX-pointer.x,dy=p.clientY-pointer.y;
  pointer=null;
  if(Math.abs(dx)>42&&Math.abs(dx)>Math.abs(dy)*1.3){
   event.preventDefault();cycle(dx<0?1:-1);
  }
 },{passive:false});
 const help=document.getElementById('info-toggle');
 const panel=document.getElementById('map-info');
 const close=document.getElementById('info-close');
 const showInfo=(open)=>{
  if(!panel||!help)return;
  infoOpen=open;panel.hidden=!open;
  help.setAttribute('aria-expanded',open?'true':'false');
  if(open)close?.focus();else help.focus();
 };
 help?.addEventListener('click',()=>showInfo(!infoOpen));
 close?.addEventListener('click',()=>showInfo(false));
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&infoOpen)showInfo(false)});
 document.addEventListener('pointerdown',e=>{
  if(infoOpen&&!e.target.closest('.info-hub'))showInfo(false);
 });
 updateCarousel('commuter');
}
