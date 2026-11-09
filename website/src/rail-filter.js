// Narrow filter extension: preserve existing mode semantics, add only local lines.
export function matchesRailFilter(v,filter){
  if(filter==='all')return true;
  if(filter==='nockeby')return v.mode==='tram'&&String(v.line)==='12';
  if(filter==='sj')return v.mode==='intercity'&&v.agency==='SJ';
  if(filter==='malartag')return v.mode==='regional'&&v.agency==='Mälartåg';
  if(filter==='arlanda')return v.mode==='express'&&v.agency==='Arlanda Express';
  if(filter==='saltsjo')return v.mode==='saltsjo'&&['25','26'].includes(String(v.line));
  if(filter==='roslags')return v.mode==='localrail'&&['27','28','29'].includes(String(v.line));
  if(filter==='city7')return v.mode==='tram'&&String(v.line)==='7';
  if(filter==='lidingo')return v.mode==='tram'&&String(v.line)==='21';
  if(filter==='tram')return v.mode==='tram'&&['30','31'].includes(String(v.line));
  return v.mode===filter;
}
export function railFilterTitle(filter){
  return ({
    commuter:'Pendeltåg',metro:'Tunnelbana',tram:'Tvärbanan',
    nockeby:'Nockebybanan',lidingo:'Lidingöbanan',city7:'Spårväg City',roslags:'Roslagsbanan',saltsjo:'Saltsjöbanan',arlanda:'Arlanda Express',sj:'SJ',malartag:'Mälartåg',all:'Alla tåg'
  })[filter]||'Alla tåg';
}
