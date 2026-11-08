let photoCatalog={};
export async function loadPhotoCatalog(){
 try{
  const response=await fetch('./photos/catalog.json',{cache:'default'});
  if(response.ok)photoCatalog=await response.json();
 }catch(e){console.warn('Local rail photos not available',e)}
 return Object.keys(photoCatalog).length;
}
export function photoForVehicle(v){
 const line=String(v.line||'').trim(),name=(v.destination||'').toLowerCase();
 let key=null;
 if(v.mode==='metro')key=['13','14'].includes(line)?'metro_c30':line==='10'||line==='11'?'metro_c20_blue':'metro_c20_green';
 if(v.mode==='commuter')key='commuter_x60';
 if(v.mode==='express' && v.agency==='Arlanda Express')key='rail_arlanda';
 if(v.mode==='saltsjo')key='local_saltsjo';
 if(v.mode==='localrail')key=String(v.id||'').split('').reduce((n,c)=>n+c.charCodeAt(0),0)%2?'local_x10p':'local_x15p';
 if(v.mode==='tram')key=['30','31'].includes(line)?'tram_a35':line==='12'?'tram_nockeby12':line==='21'?'tram_lidingo21':line==='7'?'tram_city7':null;
 if(v.mode==='rail'){
  const text=(v.train+' '+v.agency+' '+v.destination).toLowerCase();
  if(/arlanda express/.test(text))key='rail_arlanda';
  else if(/mälartåg/.test(text))key='rail_malartag';
  else if(/x2000/.test(text))key='rail_x2000';
  else if(/sj 3000|x55/.test(text))key='rail_sj3000';
  else if(/öresund/.test(text))key='rail_oresund';
 }
 return key?photoCatalog[key]||null:null;
}
