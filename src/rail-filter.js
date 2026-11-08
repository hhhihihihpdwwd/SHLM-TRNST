// Narrow filter extension: preserve existing mode semantics, add only local lines.
export function matchesRailFilter(v,filter){
  if(filter==='all')return true;
  if(filter==='nockeby')return v.mode==='tram'&&String(v.line)==='12';
  if(filter==='lidingo')return v.mode==='tram'&&String(v.line)==='21';
  if(filter==='tram')return v.mode==='tram'&&['30','31'].includes(String(v.line));
  return v.mode===filter;
}
export function railFilterTitle(filter){
  return ({
    commuter:'Pendeltåg',metro:'Tunnelbana',tram:'Tvärbanan',
    nockeby:'Nockebybanan',lidingo:'Lidingöbanan',all:'Alla tåg'
  })[filter]||'Alla tåg';
}
