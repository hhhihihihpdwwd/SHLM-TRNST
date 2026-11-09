#!/usr/bin/env python3
"""Inspect why long-distance Mälartåg train route relations lack usable geometry."""
import collections
import json
import urllib.request
from pathlib import Path
from refine_osm_routes import BASE
from append_malartag import geometry_large,geometry_components,read_regional_osm

IDS=[5386847,5386848,3293019,3293020,3177328,4755734]
def inspect(rid):
 obj=read_regional_osm(BASE+"route/"+str(rid))
 print("RELATION",rid,"TOPLEVEL",list(obj)[:25],"TYPE",obj.get("type"),flush=True)
 g=obj.get("geojson")
 if not isinstance(g,dict):print("NO-GEOJSON",type(g).__name__,str(g)[:400],flush=True);return
 print("GEOJSON",rid,"TYPE",g.get("type"),"KEYS",list(g)[:15],"features",len(g.get("features",[])),flush=True)
 sequences=[]
 for feat in g.get("features",[]):
  geo=feat.get("geometry") or {}
  sequences.append((geo.get("type"),len(geo.get("coordinates",[])),(feat.get("properties") or {}).get("name")))
 print("FEATURE CONTENT",rid,sequences[:22],flush=True)
 try:whole=geometry_large(g)
 except Exception as exc:whole=None;print("GEOM ERROR",repr(exc),flush=True)
 try:parts=geometry_components(g)
 except Exception as exc:parts=[];print("COMPONENT ERROR",repr(exc),flush=True)
 print("RECOVERABLE GEOMETRY",rid,"whole",len(whole or []),"parts",[(len(s),s[0],s[-1]) for s in parts[:15]],flush=True)

if __name__=="__main__":
 for rid in IDS:
  try:inspect(rid)
  except Exception as exc:print("INSPECT FAILED",rid,str(exc)[:500],flush=True)
