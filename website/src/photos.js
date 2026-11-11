let photoCatalog={};
export async function loadPhotoCatalog(){
 try{
  const response=await fetch('./photos/catalog.json?v=rdc-01',{cache:'no-cache'});
  if(response.ok)photoCatalog=await response.json();
 }catch(e){console.warn('Local rail photos not available',e)}
 return Object.keys(photoCatalog).length;
}
export function photoForVehicle(v){
 // Historical SJ GTFS identifies the operator, but not the carriage class.
 // Show a licensed, locally packaged real SJ train photo as an explicit
 // illustrative image. Never claim the exact X2000 model ran this service.
 if(v.mode==='regional' && v.agency==='Mälartåg'){
  const example=photoCatalog.rail_malartag;
  return example?{...example,label:'Mälartåg ER1 – exempelbild (fordonstyp för avgången ej verifierad)',illustrative:true}:null;
 }
 if(v.mode==='intercity' && v.agency==='Snälltåget'){
  const sample=photoCatalog.rail_snalltaget;
  return sample?{...sample,label:'Snälltåget – exempelbild (exakt fordonsmodell ej bekräftad)',
   illustrative:true}:null;
 }
 if(v.mode==='intercity' && v.agency==='VR Snabbtåg'){
  const example=photoCatalog.rail_vr_x74;
  return example?{...example,
   label:'VR Snabbtåg X74 – exempelbild (exakt fordon för avgången ej verifierat)',
   illustrative:true}:null;
 }
 if(v.mode==='intercity' && v.agency==='RDC EuroNight'){
  const sample=photoCatalog.rail_rdc_euronight;
  return sample?{...sample,label:'RDC EuroNight i Stockholm – verkligt tåg som exempelbild (exakt avgång ej verifierad)',illustrative:true}:null;
 }
 if(v.mode==='intercity' && v.agency==='Tågab'){
  const photo=photoCatalog.rail_tagab_rc3;
  return photo?{...photo,label:'Tågab Rc3 med personvagnar – exempelbild (exakt lok för avgången ej bekräftat)',illustrative:true}:null;
 }
 if(v.mode==='intercity' && v.agency==='Vy Tåg'){
  const photo=photoCatalog.rail_vy_train;
  return photo?{...photo,label:'Vy-tåg vid Oslo S – exempelbild (exakt fordon för avgången ej bekräftat)',illustrative:true}:null;
 }
 if(v.mode==='intercity' && v.agency==='SJ'){
  const example=photoCatalog.rail_x2000||photoCatalog.rail_sj3000||photoCatalog.rail_sj_rc6;
  return example?{...example,
   label:'SJ-tåg – exempelbild (fordonstyp för avgången ej verifierad)',
   illustrative:true}:null;
 }
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
  else if(/x2000/.test(text))key='rail_x2000';
  else if(/sj 3000|x55/.test(text))key='rail_sj3000';
  else if(/öresund/.test(text))key='rail_oresund';
 }
 return key?photoCatalog[key]||null:null;
}
