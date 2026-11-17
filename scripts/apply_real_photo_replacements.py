"""Install strictly genuine, credited Wikimedia Commons photo crops into feature branch.

Embedded assets were cut from verified real photos (not text-to-image generation).
Keep old photo files; new filenames provide rollback and bust browser caches.
"""
from __future__ import annotations
import base64,hashlib,io,json
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"website"
ASSETS=ROOT/"scripts/assets/verified-real-photo-replacements.b64.json"
SOURCES={
 "metro_c20_green":{
   "sourceKey":"metro03_0",
   "title":"SL C20, Högdalen metro - 20260515 - 06.jpg",
   "source":"https://commons.wikimedia.org/wiki/File:SL_C20,_Högdalen_metro_-_20260515_-_06.jpg",
   "author":"AleWi",
   "license":"CC BY-SA 4.0",
   "license_url":"https://creativecommons.org/licenses/by-sa/4.0/",
   "label":"Tunnelbana C20 vid Högdalen – verkligt frontfoto (exempelbild)",
   "path":"photos/images/metro_c20_green_near_2026.webp"
 },
 "rail_rdc_euronight":{
   "sourceKey":"rdc_1",
   "title":"2026-10-10 8814 RDC EuroNight ankommer till Stockholm.jpg",
   "source":"https://commons.wikimedia.org/wiki/File:2026-10-10_8814_RDC_EuroNight_ankommer_till_Stockholm.jpg",
   "author":"G och J",
   "license":"CC BY 4.0",
   "license_url":"https://creativecommons.org/licenses/by/4.0/",
   "label":"RDC EuroNight nära Stockholm – verkligt Vectron-foto, närmare beskuret (exempelbild)",
   "path":"photos/images/rail_rdc_euronight_near_2026.webp"
 },
 "rail_oresund":{
   "sourceKey":"oresund_1",
   "title":"I11 449 Bf Malmö C, X31 4606.jpg",
   "source":"https://commons.wikimedia.org/wiki/File:I11_449_Bf_Malm%C3%B6_C,_X31_4606.jpg",
   "author":"Falk2",
   "license":"CC BY-SA 4.0",
   "license_url":"https://creativecommons.org/licenses/by-sa/4.0/",
   "label":"Öresundståg X31 i Malmö C – verkligt närfoto (exempelbild)",
   "path":"photos/images/rail_oresund_near.webp"
 },
}
def main():
  data=json.loads(ASSETS.read_text(encoding="utf8"))
  assert set(data)==set(SOURCES)
  catpath=SITE/"photos/catalog.json"
  approvedpath=SITE/"photos/approved.json"
  oldcat=json.loads(catpath.read_text(encoding="utf8"))
  oldapproved=json.loads(approvedpath.read_text(encoding="utf8"))
  assert set(SOURCES)<=set(oldcat)  # Approved index historically omits RDC; safely add its verified photo only.
  catalog={**oldcat};approved={**oldapproved}
  for key,expected in SOURCES.items():
    val=data[key]
    if val["sourceKey"]!=expected["sourceKey"] or val["type"]!="image/webp":
      raise RuntimeError("Photo provenance ID mismatch "+key)
    raw=base64.b64decode(val["base64"],validate=True)
    image=Image.open(io.BytesIO(raw))
    if image.format!="WEBP" or image.size!=(640,400):
      raise RuntimeError("Unexpected photo bytes/size for "+key)
    if len(raw)>120_000 or len(raw)<8_000:raise RuntimeError("Unexpected photo size "+key)
    dest=SITE/expected["path"]
    if dest.exists():raise RuntimeError("New photo file already exists, refuse overwrite: "+str(dest))
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(raw)
    details={k:expected[k] for k in ("title","source","author","license","license_url","label","path")}
    details["modifications"]="Authentisches Commons-Foto: Zugfront enger beschnitten, 640×400 px, zu WebP konvertiert; keine KI-Fotografie."
    details["originalPhoto"]=True
    details["illustrative"]=True
    details["sha256"]=hashlib.sha256(raw).hexdigest()
    catalog[key]={**oldcat[key],**details}
    approved[key]={**oldapproved.get(key,{}),**details}
    print("REAL CROPPED LICENSED PHOTO",key,expected["author"],expected["license"],
      str(dest.relative_to(SITE)),image.size,len(raw),details["sha256"],flush=True)
  for k in oldcat:
    if k not in SOURCES:assert catalog[k]==oldcat[k]
  for k in oldapproved:
    if k not in SOURCES:assert approved[k]==oldapproved[k]
  catpath.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
  approvedpath.write_text(json.dumps(approved,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
  print("REAL PHOTOS INSTALLED; ORIGINAL 25 IMAGE FILES REMAIN INTACT",flush=True)

if __name__=="__main__":main()
