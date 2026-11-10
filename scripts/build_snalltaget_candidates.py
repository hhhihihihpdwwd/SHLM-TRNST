#!/usr/bin/env python3
"""Import genuine Snälltåget GTFS Stockholm–Malmö segments on 2026-11-06.

GTFS train may continue beyond Malmö to Denmark/Germany or originate there.
Include ONLY the real domestic Stockholm Centralstation—Malmö Centralstation
segment and its original timetable. Deduplicate the same train encoded both
as direct and through service (identical stop times), not invented movements.
"""
from __future__ import annotations
import collections
import datetime as dt
import json
import sys
from pathlib import Path
import build_rail_keyless as gtfs

OPERATOR="Snälltåget"
TRAIN_TYPES={"2","100","101","102","103","106","109"}
STOCKHOLM="stockholm centralstation"
MALMO="malmö centralstation"
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"snalltaget_candidates.json"

def corridor_segment(sequence):
 """Return exact ordered GTFS stop sequence only between actual termini."""
 if len(sequence)<3:return None
 names=[s[1][2].casefold().strip() for s in sequence]
 try:a=names.index(STOCKHOLM);b=names.index(MALMO)
 except ValueError:return None
 if a==b:return None
 segment=sequence[min(a,b):max(a,b)+1]
 if len(segment)<3:return None
 direction="to-malmo" if a<b else "to-stockholm"
 if segment[-1][2]<=segment[0][2]:return None
 return direction,segment

def build(archive,template_day):
 refday=gtfs.REFERENCE_DAY
 valid=gtfs.service_calendar(archive,[refday])[refday]
 agencies={a["agency_id"]:a.get("agency_name","").strip()
           for a in gtfs.records(archive,"agency.txt")}
 owners={k for k,v in agencies.items() if v.casefold()==OPERATOR.casefold()}
 if not owners:raise ValueError("Historic GTFS does not identify Snälltåget")
 routes={r["route_id"]:r for r in gtfs.records(archive,"routes.txt")
         if r.get("agency_id") in owners and r.get("route_type") in TRAIN_TYPES}
 if not routes:raise ValueError("No Snälltåget rail routes in the archive")
 trips={t["trip_id"]:t for t in gtfs.records(archive,"trips.txt")
        if t.get("route_id") in routes and t.get("service_id") in valid}
 stations={}
 for x in gtfs.records(archive,"stops.txt"):
  if not x.get("stop_id"):continue
  try:lat,lon=float(x["stop_lat"]),float(x["stop_lon"])
  except (KeyError,ValueError):continue
  if 55<=lat<=62 and 11<=lon<=20:
   stations[x["stop_id"]]=(round(lat,6),round(lon,6),x.get("stop_name",""))
 timetables=collections.defaultdict(list)
 for x in gtfs.records(archive,"stop_times.txt"):
  tid=x.get("trip_id")
  if tid not in trips:continue
  stop=stations.get(x.get("stop_id"))
  if not stop or not stop[2]:continue
  try:seq=int(x["stop_sequence"])
  except (KeyError,ValueError):continue
  arrival=gtfs.clock(x.get("arrival_time"))
  departure=gtfs.clock(x.get("departure_time"))
  if arrival is None and departure is None:continue
  if arrival is None:arrival=departure
  if departure is None:departure=arrival
  timetables[tid].append((seq,stop,arrival,departure))
 candidate_groups=collections.defaultdict(list)
 for tid,seq in timetables.items():
  seq.sort(key=lambda s:s[0])
  section=corridor_segment(seq)
  if section is None:continue
  direction,stops=section
  first=(stops[0][3] if stops[0][3] is not None else stops[0][2])
  last=(stops[-1][2] if stops[-1][2] is not None else stops[-1][3])
  if last<=first:continue
  # Dedup by the complete actual segment schedule, not just start/arrival.
  sig=(direction,tuple((s[1][2],s[2],s[3]) for s in stops))
  all_names=[s[1][2] for s in seq]
  direct=int(all_names[0].casefold()==STOCKHOLM and all_names[-1].casefold()==MALMO or
             all_names[0].casefold()==MALMO and all_names[-1].casefold()==STOCKHOLM)
  candidate_groups[sig].append((direct,tid,stops,all_names,direction,
                                routes[trips[tid]["route_id"]].get("route_short_name","")))
 retained=[]
 for variants in candidate_groups.values():
  # Prefer genuine direct Stockholm–Malmö train over same-timed international
  # duplicate, but retain source ID of the selected real GTFS service.
  direct,tid,stops,all_names,direction,train_number=sorted(
   variants,key=lambda v:(-v[0],v[1]))[0]
  retained.append((tid,stops,all_names,direction,train_number,len(variants)))
 accepted=[];counts=collections.Counter()
 for tid,seq,all_names,direction,train_number,duplicates in retained:
  for offset in (-1,0,1):
   day=template_day+dt.timedelta(days=offset)
   zero=dt.datetime.combine(day,dt.time(),tzinfo=gtfs.ZONE)
   accepted.append({
    "id":"SNALL-GTFS:"+tid+":"+day.isoformat(),
    "mode":"rail","agency":OPERATOR,"sourceAgency":OPERATOR,
    "line":"Snälltåget","train":train_number or "Snälltåget",
    "direction":direction,"destination":seq[-1][1][2],
    "throughOrigin":all_names[0],"throughDestination":all_names[-1],
    "domesticSegmentOnly":True,
    "duplicateGtfsVariants":duplicates,
    "serviceDay":day.isoformat(),"archiveDay":refday.isoformat(),
    "start":int((zero+dt.timedelta(seconds=seq[0][3])).timestamp()),
    "end":int((zero+dt.timedelta(seconds=seq[-1][2])).timestamp()),
    "stops":[[s[1][0],s[1][1],s[1][2],s[2],s[3]] for s in seq],
    "source":"GTFS Sverige 2, Snälltåget, 2026-11-06 historical Friday",
    "geometryQuality":"awaiting-verified-OSM","shapeId":None,
    "vehicleModel":"Snälltåget locomotive-hauled train (illustrative, not trip verified)",
    "vehiclePhotoStatus":"licensed-illustrative-example","isLiveGPS":False,
   })
   counts[direction]+=1
 if any(counts[d]<1 for d in ("to-malmo","to-stockholm")):
  raise ValueError("Historic Snälltåget Stockholm–Malmö missing one direction")
 for t in accepted:
  assert t["end"]>t["start"] and t["stops"][0][2]!=t["stops"][-1][2]
 print("SNALL GTFS AUTHENTIC",len(trips),"FRIDAY OPERATOR TRIP DEFINITIONS",
       "UNIQUE DOMESTIC SEGMENTS",len(retained),
       "DEDUPED",sum(max(0,v[-1]-1) for v in retained),
       "THREE-DAY RECORDS",len(accepted),
       "BY DIRECTION",dict(counts),flush=True)
 for t in accepted:
  if t["serviceDay"]==template_day.isoformat():
   print("SNALL SOURCE TRIP",t["id"],t["direction"],
     "ORIGINAL",t["throughOrigin"],"to",t["throughDestination"],
     "SECTION",t["stops"][0][2],"→",t["stops"][-1][2],
     "DEPART",t["stops"][0][4],"ARRIVE",t["stops"][-1][3],
     "STOPS",[s[2] for s in t["stops"]],flush=True)
 return {"operator":OPERATOR,"referenceDay":refday.isoformat(),
         "templateDay":template_day.isoformat(),"trips":accepted,
         "counts":dict(counts),"uniquePerDay":len(retained)}

def main():
 if len(sys.argv)!=2:raise SystemExit("Usage: build_snalltaget_candidates.py YYYY-MM-DD")
 template_day=dt.date.fromisoformat(sys.argv[1])
 with gtfs.fetch_archive() as archive:
  data=build(archive,template_day)
 OUT.parent.mkdir(parents=True,exist_ok=True)
 OUT.write_text(json.dumps(data,ensure_ascii=False,separators=(",",":")),encoding="utf8")
 print("SNALL HISTORIC DATA WRITTEN",OUT,flush=True)
if __name__=="__main__":main()
