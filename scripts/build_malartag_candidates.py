#!/usr/bin/env python3
"""Build isolated historical Mälartåg GTFS candidates, preserving EVERY scheduled stop.

Source: pinned GTFS Sverige 2 archive already used by Stockholm Rail.
Historical reference-week patterns are mapped to the simulator's current week;
positions are NOT live GPS. Never synthesize services or stations.
"""
import collections
import datetime as dt
import json
import unicodedata
from pathlib import Path
import build_rail_keyless as gtfs

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"malartag_candidates.json"
REF_START=gtfs.SOURCE_START
# Official Mälardalstrafik five-corridor definitions, not arbitrary line numbers.
CORRIDORS={
 "orebro-uppsala":("örebro","eskilstuna","stockholm","uppsala"),
 "nykoping":("norrköping","nyköping","stockholm"),
 "hallsberg":("hallsberg","katrineholm","stockholm"),
 "uven":("linköping","norrköping","eskilstuna","västerås","sala"),
 "gavle":("uppsala","tierp","gävle"),
}
def norm(s):
 return unicodedata.normalize("NFKC",s or "").casefold().replace(" centralstation","").replace(" central","").replace(" c","").strip()
def agency_ok(s):
 s=norm(s)
 return any(x in s for x in ("mälartåg","mälardalstrafik","malartag","malardalstrafik"))
def corridor_for(names,route_text=""):
 """Classify only unambiguous services with corridor-specific station evidence."""
 names=[norm(n) for n in names]
 text=norm(route_text)
 scores={}
 for key,anchors in CORRIDORS.items():
  score=sum(any(a in n for n in names) for a in anchors)
  route_score=sum(a in text for a in anchors)
  # Two distinguishing stations, plus full direction in stop order.
  if score>=2 or (score>=1 and route_score>=2):
   scores[key]=(score,route_score)
 if not scores:return None
 high=max(scores.values())
 winners=[key for key,value in scores.items() if value==high]
 return winners[0] if len(winners)==1 else None

def build(z,now):
 dates=[REF_START+dt.timedelta(days=i) for i in range(7)]
 valid=gtfs.service_calendar(z,dates)
 agencies={r.get("agency_id"):r.get("agency_name","") for r in gtfs.records(z,"agency.txt")}
 routes={}
 for r in gtfs.records(z,"routes.txt"):
  name=agencies.get(r.get("agency_id"),"")
  label=" ".join((r.get("route_short_name",""),r.get("route_long_name","")))
  if r.get("route_type") in ("2","100","101","102","103","106","109") and (agency_ok(name) or agency_ok(label)):
   routes[r["route_id"]]={"agency":name,"routeText":label}
 if not routes:raise ValueError("No authentic Mälartåg routes in pinned GTFS archive")
 points={}
 for r in gtfs.records(z,"stops.txt"):
  try:lat,lon=float(r["stop_lat"]),float(r["stop_lon"])
  except (KeyError,ValueError):continue
  if 57.3<lat<61.4 and 14.0<lon<19.7:
   points[r["stop_id"]]=[round(lat,6),round(lon,6),r.get("stop_name","")]
 selected={}
 for r in gtfs.records(z,"trips.txt"):
  route=routes.get(r.get("route_id"))
  if not route:continue
  days=[day for day in dates if r.get("service_id") in valid[day]]
  if days:selected[r["trip_id"]]=(route,days,r.get("trip_headsign",""),r.get("trip_short_name",""))
 times=collections.defaultdict(list)
 for r in gtfs.records(z,"stop_times.txt"):
  tid=r.get("trip_id")
  if tid not in selected or r.get("stop_id") not in points:continue
  a=gtfs.clock(r.get("arrival_time",""));d=gtfs.clock(r.get("departure_time",""))
  if a is None and d is None:continue
  try:seq=int(r["stop_sequence"])
  except (ValueError,KeyError):continue
  times[tid].append((seq,points[r["stop_id"]],a if a is not None else d,d if d is not None else a))
 targets=[now-dt.timedelta(days=1),now,now+dt.timedelta(days=1)]
 output=[];counts=collections.Counter();unclassified=0
 for tid,entries in times.items():
  entries.sort(key=lambda x:x[0])
  if len(entries)<2 or any(a[2]>b[2] for a,b in zip(entries,entries[1:])):continue
  route,days,head,train=selected[tid]
  stops=[e[1] for e in entries]
  corridor=corridor_for([s[2] for s in stops],route["routeText"])
  if corridor is None:unclassified+=1;continue
  for source_day in days:
   for target in targets:
    if source_day.weekday()!=target.weekday():continue
    zero=dt.datetime.combine(target,dt.time(),gtfs.ZONE)
    first,last=entries[0][2],entries[-1][3]
    if last<=first:continue
    output.append({
     "id":"MALARTAG-ARCHIVE:"+tid+":"+target.isoformat(),
     "mode":"rail","agency":"Mälartåg","line":corridor,"corridor":corridor,
     "routeName":route["routeText"],"destination":head or stops[-1][2],
     "train":train,"serviceDay":target.isoformat(),
     "start":int((zero+dt.timedelta(seconds=first)).timestamp()),
     "end":int((zero+dt.timedelta(seconds=last)).timestamp()),
     "stops":[[s[1][0],s[1][1],s[1][2],s[2],s[3]] for s in entries],
     "shapeId":None,"geometryQuality":"awaiting-verified-OSM",
     "source":"Historical GTFS Sverige 2 "+source_day.isoformat(),
     "archiveDay":source_day.isoformat(),"isLiveGPS":False
    })
    counts[corridor]+=1
 if not output:raise ValueError("No dated historical Mälartåg train trips")
 print("MÄLARTÅG CANDIDATES",dict(counts),"UNCLASSIFIED",unclassified,flush=True)
 return {"trips":output,"corridors":CORRIDORS,"counts":dict(counts),"unclassified":unclassified}

def main():
 now=dt.datetime.now(gtfs.ZONE).date()
 with gtfs.fetch_archive() as z:result=build(z,now)
 OUT.parent.mkdir(parents=True,exist_ok=True)
 OUT.write_text(json.dumps(result,ensure_ascii=False,separators=(",",":")),encoding="utf8")
if __name__=="__main__":main()
