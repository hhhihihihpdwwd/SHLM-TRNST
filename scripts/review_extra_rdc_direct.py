"""Direct Wikimedia media CDN candidate fetch after successful license verification.
These entries were already checked against Commons imageinfo before the API quota hit.
Never publish without inspecting actual photo pixels. Only a review artifact.
"""
from pathlib import Path
from urllib.parse import quote
import hashlib,io,time,requests
from PIL import Image,ImageOps,ImageDraw
ROOT=Path("_rdc_close_photo_candidates");ROOT.mkdir(exist_ok=True)
files=[
("20230220 Deutschland BTE SJ-Euronight Hamburg-Altona.jpg","Bvcmz248.5","CC0"),
("20230525 Deutschland BTE SJ-Euronight Berlin.jpg","Bvcmz248.5","CC0"),
("2024-02-07 SJ EN346 01.jpg","Nemo bis","CC BY-SA 4.0"),
("2024-08-23 4382 SJ Rc6 1413 med SJ EuroNight i Nässjö.jpg","G och J","CC BY 4.0"),
("2023-03-23 0694 SJ Rc6 1420 med Euronight-tåget mot Hamburg.jpg","G och J","CC BY 4.0"),
]
s=requests.Session();s.headers["User-Agent"]="StockholmRail/1.0 (historical railway map photo license review)"
for i,(title,author,license) in enumerate(files):
  file=title.replace(" ","_")
  md5=hashlib.md5(file.encode("utf-8")).hexdigest()
  q=quote(file,safe="._()-")
  url="https://upload.wikimedia.org/wikipedia/commons/"+md5[0]+"/"+md5[:2]+"/"+q
  for tries in range(4):
    r=s.get(url,timeout=100)
    if r.status_code==200 and r.headers.get("Content-Type","").startswith("image/"):break
    print("DIRECT RETRY",title,r.status_code,r.headers.get("Content-Type"),flush=True)
    time.sleep((tries+1)*3)
  r.raise_for_status()
  raw=r.content
  im=Image.open(io.BytesIO(raw)).convert("RGB")
  im.thumbnail((1000,800),Image.Resampling.LANCZOS)
  im.save(ROOT/(f"rdc_new_{i}.jpg"),"JPEG",quality=88,optimize=True)
  print("DIRECT PHOTO OK",title,len(raw),"source",url,"photo",im.size,flush=True)
cw,ch=500,390
sheet=Image.new("RGB",(cw*3,ch*2),"#f0f3f2")
d=ImageDraw.Draw(sheet)
for i,(title,author,license) in enumerate(files):
 im=Image.open(ROOT/(f"rdc_new_{i}.jpg"))
 im=ImageOps.contain(im,(cw-18,325),Image.Resampling.LANCZOS)
 x=(i%3)*cw;y=(i//3)*ch
 sheet.paste(im,(x+(cw-im.width)//2,y+4))
 d.text((x+12,y+328),title[:54],fill="#19393d")
 d.text((x+12,y+351),f"{author} / {license}",fill="#415a60")
sheet.save(ROOT/"new-rdc-gallery.jpg",quality=90)
print("VALID LICENSED EURO-NIGHT CLOSE PHOTO REVIEW DONE")
