#!/usr/bin/env python3
"""Read-only survey of genuine OSM train route relation metadata around Stockholm."""
import json
import urllib.parse
import urllib.request
import time
from collections import Counter
from pathlib import Path

ENDPOINTS=("https://overpass-api.de/api/interpreter","https://overpass.kumi.systems/api/interpreter")
QUERY='[out:json][timeout:90];relation["route"="train"](58.7,15.7,60.7,19.2);out tags;'
def main():
 last=None
 for url in ENDPOINTS:
  try:
   req=urllib.request.Request(url,data=urllib.parse.urlencode({"data":QUERY}).encode(),headers={
    "Content-Type":"application/x-www-form-urlencoded","User-Agent":"StockholmRail SJ OSM Audit/1.0"})
   with urllib.request.urlopen(req,timeout=105) as result:body=result.read(20_000_000)
   data=json.loads(body)
   items=data.get("elements",[])
   print("OSM TRAIN RELATIONS",len(items),flush=True)
   for x in items:
    t=x.get("tags") or {}
    label=" ".join(str(t.get(k,"")) for k in ("name","operator","from","to","ref"))
    if any(token in label.casefold() for token in ("stockholm","västerås","uppsala","sj ","sj ab","sj regional","malmö","göteborg")):
     print("OSM SJ CANDIDATE",x.get("id"),json.dumps({k:t.get(k) for k in ("name","from","to","operator","network","ref")},ensure_ascii=False),flush=True)
   return
  except Exception as ex:
   last=ex
   print("OSM SERVER ERROR",url,str(ex)[:250],flush=True)
 raise RuntimeError("Both Overpass servers failed: "+str(last))
if __name__=="__main__":main()
