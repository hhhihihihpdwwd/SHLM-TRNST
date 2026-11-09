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
REF_START=gtfs.REFERENCE_DAY
# ONE carefully isolated pilot corridor: Uppsala–Tierp–Gävle; no other Mälartåg routes.
CORRIDORS={\n "gavle":("uppsala","tierp","gävle"),\n}\n# Prevent ambiguous overlap (e.g. Stockholm-Uppsala on its own) being
# assigned to the wrong corridor. Do not infer missing journey segments.
SIGNATURES={\n "gavle":("gävle","tierp","skutskär","älvkarleby","tobo","örbyhus"),\n}\ndef norm(s):
 return unicodedata.normalize("NFKC",s or "").casefold().strip()
def contains_station(name,anchor):
 # "Sala" must not match "Salaspår", and "C" is never stripped from a city name.
 value=norm(name).replace(" centralstation","").replace(" central","").replace(" resecentrum","")
 return value==anchor or value.startswith(anchor+" ") or value.startswith(anchor+"-")
def agency_ok(s):
 s=norm(s)
 return any(x in s for x in ("mälartåg","mälardalstrafik","malartag","malardalstrafik"))
def corridor_for(names,route_text=""):
 """Conservative classification from unique corridor stops and route metadata.

 Subsections lacking a distinctive station are not guessed. Identical segments
 shared by more than one corridor require explicit route naming.
 """
 names=[norm(n) for n in names]
 text=norm(route_text)
 hits={key:sum(any(contains_station(n,anchor) for n in names) for anchor in signature)
       for key,signature in SIGNATURES.items()}
 best=max(hits.values(),default=0)
 if best:
  winners=[key for key,score in hits.items() if score==best]
  if len(winners)==1:return winners[0]
  by_route=[key for key in winners if sum(a in text for a in CORRIDORS[key])>=2]
  return by_route[0] if len(by_route)==1 else None
 # Route metadata is used only for distinctive, unambiguous route descriptions.
 matches=[key for key,signature in SIGNATURES.items() if any(a in text for a in signature)]
 return matches[0] if len(matches)==1 else None

def build(z,now):
 dates=[REF_START]
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
  if len(entries)<2 or any(a[2]>b[2] or a[3]>b[3] for a,b in zip(entries,entries[1:])):continue
  route,days,head,train=selected[tid]
  stops=[e[1] for e in entries]
  corridor=corridor_for([s[2] for s in stops],route["routeText"])
  if corridor is None:unclassified+=1;continue\n  if not (any(contains_station(n,"uppsala") for n in (s[2] for s in stops))\n          and any(contains_station(n,"gävle") for n in (s[2] for s in stops))):\n   unclassified+=1;continue
  for source_day in days:
   for target in targets:
    # Repeat identical archived service for every day of the week.
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
