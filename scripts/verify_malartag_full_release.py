#!/usr/bin/env python3
"""Fail-closed release gate: all five Mälartåg corridors and old ten systems.

Usage:
  python scripts/verify_malartag_full_release.py OLD.json CANDIDATE.json
"""
from __future__ import annotations
import collections
import json
import sys
from pathlib import Path
from build_malartag_candidates import CORRIDORS,contains_station
from refine_osm_routes import project_stops

def verify(before,after):
 allowed={"verified-osm-relation","verified-osm-rail-ways"}
 expected=set(CORRIDORS)
 assert len(expected)==5,("not all five Mälartåg corridors",expected)
 assert before["scope"]=="pendeltag-tunnelbana-tvarbanan-localtram-city7-roslags-saltsjo-arlanda-sj"
 assert after["scope"]==before["scope"]+"-malartag"
 assert after["type"]==before["type"]=="historical-daily-repeating-simulation"
 assert after["trips"][:len(before["trips"])]==before["trips"],"existing vehicle history changed"
 assert all(after["shapes"].get(k)==v for k,v in before["shapes"].items()),"existing rail track changed"
 assert all(after["counts"].get(k)==v for k,v in before["counts"].items()),"existing mode counts changed"
 for name in ("metroLines","tramLines","roslagsLines","saltsjoLines",
              "arlandaDirections","sjDirections","localTramDirections"):
  assert after[name]==before[name],name
 assert after["counts"]["intercity"]==56
 assert before["tramLines"]["21"]>350
 assert before["sjDirections"]==after["sjDirections"]
 assert set(after["malartagDirections"])==expected,after.get("malartagDirections")
 assert set(after["malartagCoverage"])==expected
 assert set(after["malartagCorridors"])==expected
 extra=after["trips"][len(before["trips"]):]
 assert extra and len(extra)==after["counts"]["regional"]
 assert all(t["mode"]=="regional" and t["agency"]=="Mälartåg"
            and t["corridor"] in expected and t["geometryQuality"] in allowed
            and t["shapeId"] in after["shapes"] and t["archiveDay"]=="2026-11-06"
            and t["end"]>t["start"] and len(t["stops"])>=2 for t in extra)
 assert len({t["id"] for t in extra})==len(extra),"duplicate train IDs"
 for train in extra:
  if train["geometryQuality"]=="verified-osm-rail-ways":
   assert train.get("osmWayNetwork") is True and train.get("osmRelation") is None
  else:
   assert train.get("osmWayNetwork") is not True and train.get("osmRelation")
 checked=set()
 for t in extra:
  key=(t["shapeId"],tuple((x[0],x[1],x[2]) for x in t["stops"]))
  if key in checked:continue
  checked.add(key)
  shape=after["shapes"][t["shapeId"]]
  assert len(shape)>=5,("truncated OSM geometry",t["shapeId"])
  assert project_stops(t["stops"],shape,650) is not None,(
       "GTFS station order does not fit genuine OSM geometry",t["corridor"],t["id"])
 for corridor,stops in CORRIDORS.items():
  these=[t for t in extra if t["corridor"]==corridor]
  assert these,("no train",corridor)
  forward=after["malartagDirections"][corridor].get("forward",0)
  reverse=after["malartagDirections"][corridor].get("reverse",0)
  assert forward>0 and reverse>0,("missing physical direction",corridor,forward,reverse)
  assert after["malartagCorridors"][corridor]==len(these),(
      "corridor count mismatch",corridor,after["malartagCorridors"][corridor],len(these))
  names=[s[2] for t in these for s in t["stops"]]
  absent=[stop for stop in stops if not any(contains_station(name,stop) for name in names)]
  assert not absent,("missing required corridor waypoints",corridor,absent)
  # A complete corridor may consist of consecutive genuine short-turn services;
  # all advertised waypoints must be represented, not invented.
  days=collections.Counter(t["serviceDay"] for t in these)
  assert len(days)>=3 and len(set(days.values()))==1,("not repeated daily",corridor,days)
  print("FULL MÄLARTÅG CORRIDOR",corridor,"DAILY",len(these)//len(days),
        "DIRECTIONS",forward//len(days),reverse//len(days),
        "UNIQUE STATIONS",len(set(names)),flush=True)
 print("MÄLARTÅG FIVE-CORRIDOR RELEASE VERIFIED",len(extra),"3-DAY TRAIN RECORDS",
       "OSM STATION-PATTERNS",len(checked),"OLD TRAINS UNCHANGED",len(before["trips"]),flush=True)
 return extra

if __name__=="__main__":
 if len(sys.argv)!=3:raise SystemExit("old-and-candidate-json-required")
 old=json.loads(Path(sys.argv[1]).read_text(encoding="utf8"))
 candidate=json.loads(Path(sys.argv[2]).read_text(encoding="utf8"))
 verify(old,candidate)
