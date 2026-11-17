"""Strip the white background and dark icon tile from two approved train fronts.

The actual train artwork remains the exact previously approved B motif.
Input: the two immutable original 72px STABLE27 B marker assets.
Output: transparent standalone WebP trains (48x48). No GTFS or route changes.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ICONS = {
 "roslagsbanan": {
  "source": "roslagsbanan-B-approved.webp",
  "output": "roslagsbanan-B-standalone.webp",
  "outline": [(139,110),(145,100),(155,97),(168,95),(212,94),(230,96),(238,103),(241,110),(253,116),(271,128),(291,148),(301,162),(306,176),(307,250),(307,267),(302,275),(289,284),(272,288),(256,296),(240,301),(228,305),(214,307),(202,305),(188,307),(171,305),(159,305),(141,303),(126,300),(113,299),(99,292),(88,284),(79,272),(77,254),(78,221),(83,194),(88,173),(93,153),(103,133),(114,119),(129,113)]
 },
 "saltsjobanan": {
  "source": "saltsjobanan-B-approved.webp",
  "output": "saltsjobanan-B-standalone.webp",
  "outline": [(151,119),(153,110),(159,108),(207,107),(222,111),(236,116),(248,125),(263,137),(279,148),(293,164),(308,180),(311,195),(312,253),(308,266),(298,278),(281,287),(259,295),(243,302),(226,308),(206,314),(191,315),(166,318),(143,317),(123,314),(110,311),(97,307),(87,299),(79,282),(78,269),(78,224),(83,198),(93,169),(105,143),(119,130),(134,122)]
 }
}
def main():
 folder=ROOT/"website/src/assets"
 for name,item in ICONS.items():
  source=folder/item["source"]
  assert source.is_file(),f"Missing original approved B artwork: {source}"
  original=Image.open(source).convert("RGBA")
  assert original.size==(72,72),f"Unexpected original dimensions for {name}: {original.size}"
  # Trace the train silhouette on the existing B icon (no new train artwork).
  outline=[(x/5,y/5) for x,y in item["outline"]]
  mask=Image.new("L",(72,72),0)
  ImageDraw.Draw(mask).polygon(outline,fill=255)
  original.putalpha(mask.filter(ImageFilter.GaussianBlur(0.5)))
  cropped=original.crop((14,17,64,65))
  cropped.thumbnail((46,46),Image.Resampling.LANCZOS)
  isolated=Image.new("RGBA",(48,48),(0,0,0,0))
  isolated.alpha_composite(cropped,((48-cropped.width)//2,(48-cropped.height)//2))
  out=folder/item["output"]
  isolated.save(out,"WEBP",lossless=True,method=6)
  check=Image.open(out).convert("RGBA")
  assert check.size==(48,48)
  for corner in [(0,0),(47,0),(0,47),(47,47),(0,24),(24,0)]:
   assert check.getpixel(corner)[3]==0,(name,"Background tile still visible",corner)
  assert check.getpixel((24,25))[3]>200,(name,"Train body lost")
  opaque=sum(a>128 for a in check.getchannel("A").getdata())
  assert 350<=opaque<=1700,(name,"Wrong freestanding train mask",opaque)
  print("PASS",name,"background fully transparent, train remains",opaque,"opaque pixels","sha256",hashlib.sha256(out.read_bytes()).hexdigest(),flush=True)
if __name__=="__main__":
 main()
