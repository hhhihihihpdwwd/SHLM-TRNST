// Pure illustrative simulation. Never represent its output as observed GPS.
export function stockholmTime(stamp=Date.now()){
 const fmt=new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Stockholm',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'});
 const p=Object.fromEntries(fmt.formatToParts(new Date(stamp)).map(x=>[x.type,x.value]));
 const date=`${p.year}-${p.month}-${p.day}`;
 return {date,display:`${p.hour}:${p.minute}:${p.second}`,seconds:Number(p.hour)*3600+Number(p.minute)*60+Number(p.second),weekday:new Date(date+'T12:00:00Z').getUTCDay()};
}
export function interpolate(a,b,p){return a.map((v,i)=>v+(b[i]-v)*p)}
export function tripProgress(stops,t){
 if(!stops.length)return null;
 if(t<=stops[0].t)return {position:stops[0].coord,next:0,progress:0};
 for(let i=1;i<stops.length;i++){
  if(t<=stops[i].t){const p=Math.max(0,Math.min(1,(t-stops[i-1].t)/Math.max(1,stops[i].t-stops[i-1].t)));
   return {position:interpolate(stops[i-1].coord,stops[i].coord,p),next:i,progress:i-1+p}}
 }
 return {position:stops.at(-1).coord,next:stops.length-1,progress:stops.length-1};
}
export function occupancy(v,stationIndex,weekday,hour){
 const commute=(weekday>0&&weekday<6)&&(hour>=7&&hour<=9?31:hour>=16&&hour<=18?23:0);
 const hub=/City|Central|T-Centralen|Odenplan/i.test(v.stops[stationIndex].name)?-14:0;
 const seed=[...v.id].reduce((a,c)=>a+c.charCodeAt(0),0);
 return Math.round(Math.max(8,Math.min(94,27+commute+hub+13*Math.sin((seed+stationIndex*17+hour*13)*.34)+stationIndex*3)));
}
export function secondsLabel(t){return `${String(Math.floor(t/3600)%24).padStart(2,'0')}:${String(Math.floor(t%3600/60)).padStart(2,'0')}`}
