#!/usr/bin/env python3
"""Repair only archived line 21 gaps using authentic Saturday GTFS trains.

The pinned 2026-11-06 weekday archive has NO Lidingöbanan service between
07:06 and 08:53, nor during much of 16:00-18:00. Saturday 2026-11-07
contains actual GTFS services across these windows. This *historic simulation*
may replay those services, with source provenance attached.

Only pre-existing verified OSM line 21 rail geometries can be used.
All 10 original systems and all their trips/shapes remain unchanged.
"""
from __future__ import annotations
import collections
import copy
import datetime as dt
import json
import os
from pathlib import Path
import build_rail_keyless as gtfs
from refine_osm_routes import project_stops

ROOT=Path(__file__).resolve().parents[1]
RAIL=Path(os.environ.get("STOCKHOLM_RAIL_DATA",str(ROOT/"data"/"rail.json")))
BASE_SCOPE="pendeltag-tunnelbana-tvarbanan-localtram-city7-roslags-saltsjo-arlanda-sj"
SATURDAY=dt.date(2026,11,7)
MAX_DISTANCE=280

def direction(t):
 names=[s[2].casefold().strip() for s in t.get("stops",[])]
 if len(names)<2:return None
 if names[0].startswith("ropsten") and names[-1].startswith("gåshaga"):return "out"
 if names[0].startswith("gåshaga") and names[-1].startswith("ropsten"):return "back"
 return None

def historical_saturday(z,template_day):
 old=gtfs.REFERENCE_DAY
 try:
  gtfs.REFERENCE_DAY=SATURDAY
  data=gtfs.build(z,now=template_day,tram_lines={"21"})
 finally:gtfs.REFERENCE_DAY=old
 return [t for t in data["trips"] if t.get("mode")=="tram" and
         str(t.get("line"))=="21" and t.get("archiveDay")==SATURDAY.isoformat()]

def local_seconds(t):
 stamp=dt.datetime.fromtimestamp(t["start"],gtfs.ZONE)
 return stamp.hour*3600+stamp.minute*60+stamp.second

def gap(t):
 s=local_seconds(t)
 # Genuine 2026-11-07 Saturday trips fill uncovered weekday morning and
 # afternoon windows only. Do not alter existing Friday timetable.
 return (7*3600+5*60<=s<8*3600+50*60 or
         15*3600+30*60<=s<18*3600+45*60)

def integrate(base,saturday):
 if base.get("scope")!=BASE_SCOPE:raise ValueError("Cannot modify unverified SJ baseline")
 frozen=copy.deepcopy(base)
 original=[t for t in base["trips"] if t.get("mode")=="tram" and str(t.get("line"))=="21"]
 if not original:raise ValueError("No historical Lidingöbanan records in baseline")
 originals_per_day=collections.defaultdict(list)
 shapes_by_direction=collections.defaultdict(list)
 for t in original:
  d=direction(t)
  if d is None:continue
  originals_per_day[(t["serviceDay"],d)].append(t)
  sid=t.get("shapeId")
  geometry=base["shapes"].get(sid)
  if geometry and all(existing[0]!=sid for existing in shapes_by_direction[d]):
   shapes_by_direction[d].append((sid,geometry))
 if not all(shapes_by_direction[d] for d in ("out","back")):
  raise ValueError("Missing pre-verified OSM line 21 rail geometries")
 existing_ids={t["id"] for t in base["trips"]}
 selected=[]
 report=collections.Counter()
 for t in saturday:
  d=direction(t)
  if not d or not gap(t):continue
  day=t["serviceDay"]
  matches=originals_per_day.get((day,d),[])
  # Never stack two archived departures for the same direction within 7 min.
  if any(abs(t["start"]-weekday["start"])<420 for weekday in matches):continue
  shape=next(((sid,geom) for sid,geom in shapes_by_direction[d]
              if project_stops(t["stops"],geom,MAX_DISTANCE) is not None),None)
  if shape is None:continue
  sid,_=shape
  identity="LIDINGO-SAT-PROXY:"+t["id"]
  if identity in existing_ids:continue
  record={**t,"id":identity,"mode":"tram","line":"21","shapeId":sid,
          "geometryQuality":"verified-osm-relation",
          "osmRelation":sid.split("local-tram-osm:21:",1)[-1],
          "timetableProxy":"Saturday historical GTFS substituted for an incomplete weekday simulation gap",
          "source":"GTFS Sverige 2, 2026-11-07 Saturday reference, representative historical simulation",
          "archiveDay":SATURDAY.isoformat(),
          "isLiveGPS":False}
  selected.append(record)
  report[(day,d)]+=1
 if not selected:raise ValueError("No authentic Saturday Lidingöbanan gaps could be verified")
 template=base["simulationTemplateDay"]
 template_new=[t for t in selected if t["serviceDay"]==template]
 if not all(any(direction(t)==d for t in template_new) for d in ("out","back")):
  raise ValueError("Missing authentic Saturday gap services for line 21 both directions")
 target_epoch=dt.datetime.fromisoformat(template+"T08:35:00").replace(tzinfo=gtfs.ZONE).timestamp()
 at_morning=[t for t in template_new if t["start"]<=target_epoch<=t["end"]]
 if len(at_morning)<2 or {direction(t) for t in at_morning}!={"out","back"}:
  raise ValueError("08:35 screenshot regression: both Lidingöbanan directions not recovered")
 before=len(original)
 base["trips"].extend(selected)
 base["counts"]["tram"]+=len(selected)
 base["tramLines"]["21"]+=len(selected)
 base["localTramDirections"]["21"]["out"]+=sum(v for (day,d),v in report.items() if d=="out")
 base["localTramDirections"]["21"]["back"]+=sum(v for (day,d),v in report.items() if d=="back")
 assert base["scope"]==frozen["scope"]
 assert base["trips"][:len(frozen["trips"])]==frozen["trips"]
 assert base["shapes"]==frozen["shapes"]
 assert all(base["counts"][k]==v for k,v in frozen["counts"].items() if k!="tram")
 assert all(base["tramLines"][k]==v for k,v in frozen["tramLines"].items() if k!="21")
 assert base["sjDirections"]==frozen["sjDirections"]
 assert base["counts"]["intercity"]==frozen["counts"]["intercity"]==56
 assert base["localTramDirections"]["12"]==frozen["localTramDirections"]["12"]
 print("LIDINGÖBANAN ORIGINAL LINE 21",before,"SATURDAY GAP ADDITIONS",len(selected),
       "BY DAY AND DIRECTION",dict((str(k),v) for k,v in report.items()),flush=True)
 print("LIDINGÖBANAN 08:35 SOURCE-VERIFIED BOTH DIRECTIONS",
       [(t["stops"][0][2],t["stops"][-1][2],t["archiveDay"]) for t in at_morning],
       flush=True)
 return base

def main():
 base=json.loads(RAIL.read_text(encoding="utf8"))
 template=dt.date.fromisoformat(base["simulationTemplateDay"])
 with gtfs.fetch_archive() as z:saturday=historical_saturday(z,template)
 merged=integrate(base,saturday)
 RAIL.write_text(json.dumps(merged,ensure_ascii=False,separators=(",",":")),encoding="utf8")
if __name__=="__main__":main()
