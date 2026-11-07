#!/usr/bin/env python3
"""Download only user-approved Wikimedia Commons rail photos; validate and credit.
No arbitrary image search, no runtime Commons dependency, no stock-image swapping.
"""
from pathlib import Path
import io, json, time, urllib.parse, urllib.request
from PIL import Image, ImageOps

BASE=Path(__file__).resolve().parents[1]
TARGET=BASE/"photos"/"images"
APPROVED=json.loads((BASE/"photos"/"approved.json").read_text(encoding="utf8"))
TARGET.mkdir(parents=True,exist_ok=True)
result={}
failures={}
for name,info in APPROVED.items():
    path=TARGET/(name+".webp")
    if path.exists() and path.stat().st_size>2500:
        result[name]={**info,"path":"photos/images/"+name+".webp"}
        continue
    title=info["title"]
    base="https://commons.wikimedia.org/wiki/Special:Redirect/file/"+urllib.parse.quote(title)
    urls=[base+"?width=900",base]
    for url in urls:
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"StockholmRail/0.2 (educational personal rail gallery; Wikimedia attribution included)","Accept":"image/*"})
            with urllib.request.urlopen(req,timeout=30) as response:
                content=response.read(24_000_000)
            with Image.open(io.BytesIO(content)) as picture:
                picture.load()
                im=ImageOps.exif_transpose(picture).convert("RGB")
                im.thumbnail((900,900))
                im.save(path,format="WEBP",quality=82,method=5)
            if path.stat().st_size<2500:raise ValueError("image too small")
            result[name]={**info,"path":"photos/images/"+name+".webp"}
            print("PHOTO VERIFIED",name,path.stat().st_size,flush=True)
            break
        except Exception as exc:
            failures[name]=str(exc)[:160]
            time.sleep(.25)
if len(result)<3:
    print("WARNING: Few approved Wikimedia images were reachable; retaining honest vehicle placeholders.",flush=True)
(BASE/"photos"/"catalog.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
print("PHOTO COVERAGE",len(result),"/",len(APPROVED),"missing",list(failures))
