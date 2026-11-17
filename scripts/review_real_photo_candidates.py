"""Download genuinely photographed Wikimedia Commons train candidates for manual review.

No synthesized photographs, no unlicensed images, no production changes.
"""
import io,json,re,time
from html import unescape
from pathlib import Path
import requests
from PIL import Image,ImageDraw,ImageFont,ImageOps

USER_AGENT="StockholmRail/1.0 (educational historical railway map; licensing review)"
API="https://commons.wikimedia.org/w/api.php"
SOURCES={
 "metro03":[
  "SL C20, Högdalen metro - 20260515 - 06.jpg",
  "C20, Slussen Metro, 20240106 - 07.jpg",
  "C20, Slussen Metro, 20240106 - 08.jpg",
 ],
 "rdc":[
  "2026-10-10 8818 RDC EuroNight ankommer till Stockholm.jpg",
  "2026-10-10 8814 RDC EuroNight ankommer till Stockholm.jpg",
 ],
 "oresund":[
  "Öresundståg, Växjö, 20220806.jpg",
  "I11 449 Bf Malmö C, X31 4606.jpg",
  "20190917 Malmo C Oresundstag 0148 (48835473606).jpg",
 ]
}
ROOT=Path("_real_photo_candidates");ROOT.mkdir(exist_ok=True)
session=requests.Session()
session.headers.update({"User-Agent":USER_AGENT,"Accept":"application/json,image/webp,image/jpeg,*/*"})
records=[]
for category,titles in SOURCES.items():
 for i,title in enumerate(titles):
  obj=None
  for attempt in range(3):
   try:
    response=session.get(API,params={"action":"query","format":"json","formatversion":"2",
     "prop":"imageinfo","iiprop":"url|extmetadata|size","iiurlwidth":"1400",
     "titles":"File:"+title},timeout=50)
    response.raise_for_status()
    pages=response.json()["query"]["pages"]
    if len(pages)!=1 or "imageinfo" not in pages[0]:
     raise RuntimeError("Commons file missing "+title+": "+str(pages)[:120])
    obj=pages[0]["imageinfo"][0]
    break
   except Exception as exc:
    print("SOURCE RETRY",category,title,str(exc),flush=True)
    if attempt==2:raise
    time.sleep(3*(attempt+1))
  meta=obj.get("extmetadata",{})
  license=unescape(re.sub("<[^>]*>","",meta.get("LicenseShortName",{}).get("value",""))).strip()
  author=unescape(re.sub("<[^>]*>","",meta.get("Artist",{}).get("value",""))).strip()
  if not (license.startswith("CC BY") or license.startswith("CC0")):
   raise RuntimeError("Unsupported/unverified photo license "+title+": "+license)
  if not author:raise RuntimeError("Missing real photo author credit "+title)
  thumb=obj.get("thumburl") or obj.get("url")
  response=session.get(thumb,timeout=80);response.raise_for_status()
  raw=response.content
  if len(raw)<15000:raise RuntimeError("File unexpectedly tiny, probably error page "+title)
  image=Image.open(io.BytesIO(raw)).convert("RGB")
  if image.width<650 or image.height<450:raise RuntimeError("Photograph low resolution "+title)
  resized=image.copy();resized.thumbnail((880,670),Image.Resampling.LANCZOS)
  key=f"{category}_{i}"
  resized.save(ROOT/(key+".jpg"),"JPEG",quality=87,optimize=True)
  record={"category":category,"key":key,"title":title,
    "source":"https://commons.wikimedia.org/wiki/File:"+title.replace(" ","_"),
    "author":author,"license":license,
    "license_url":unescape(meta.get("LicenseUrl",{}).get("value","")),
    "url":thumb,"source_width":obj["width"],"source_height":obj["height"],
    "preview_width":resized.width,"preview_height":resized.height,
    "realPhotograph":True}
  records.append(record)
  print("LICENSED REAL PHOTO",key,title,license,"author",author,
    "size",resized.size,flush=True)
ROOT.joinpath("metadata.json").write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf8")
cw,ch=480,394
sheet=Image.new("RGB",(cw*3,ch*3),(239,244,243))
draw=ImageDraw.Draw(sheet)
for n,record in enumerate(records):
 x=(n%3)*cw;y=(n//3)*ch
 im=Image.open(ROOT/(record["key"]+".jpg")).convert("RGB")
 im=ImageOps.contain(im,(cw-18,308),Image.Resampling.LANCZOS)
 sheet.paste(im,(x+(cw-im.width)//2,y+8))
 label=record["key"]+" | "+record["title"]
 if len(label)>56:label=label[:53]+"..."
 draw.text((x+12,y+321),label,fill=(32,55,57))
 draw.text((x+12,y+345),record["author"][:68]+" | "+record["license"],fill=(74,97,100))
sheet.save(ROOT/"candidate-contact-sheet.jpg",quality=90)
print("REAL-PHOTO CANDIDATE GALLERY COMPLETE",len(records),flush=True)
