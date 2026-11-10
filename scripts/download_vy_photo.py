#!/usr/bin/env python3
"""Download a licensed REAL X52 photograph as an explicitly illustrative Vy-service image.
Source: Wikimedia Commons, AleWi, CC BY-SA 4.0. Never imply the photo is the actual 2026 train.
"""
import io,json,urllib.parse,urllib.request,sys
from pathlib import Path
from PIL import Image

FILENAME='Oslo - 20240713 - 18.jpg'
SOURCE='https://commons.wikimedia.org/wiki/File:'+urllib.parse.quote(FILENAME.replace(' ','_'))
API='https://commons.wikimedia.org/w/api.php?'+urllib.parse.urlencode({
 'action':'query','format':'json','prop':'imageinfo','iiprop':'url','iiurlwidth':'900',
 'titles':'File:'+FILENAME
})
def download(destination):
 q=urllib.request.Request(API,headers={'User-Agent':'StockholmRail/1.0 (personal map photo attribution audit)','Accept':'application/json'})
 with urllib.request.urlopen(q,timeout=60) as r:obj=json.loads(r.read(500000))
 pages=list(obj['query']['pages'].values())
 assert len(pages)==1 and pages[0].get('imageinfo'),'Commons image not found'
 inf=pages[0]['imageinfo'][0]
 url=inf.get('thumburl') or inf['url']
 request=urllib.request.Request(url,headers={'User-Agent':'StockholmRail/1.0 (example photo CC BY 4.0)'})
 with urllib.request.urlopen(request,timeout=80) as r:raw=r.read(7_000_000)
 img=Image.open(io.BytesIO(raw)).convert('RGB')
 img.thumbnail((960,700))
 p=Path(destination)/'photos/images/rail_vy_train.webp';p.parent.mkdir(parents=True,exist_ok=True)
 img.save(p,'WEBP',quality=76,method=5)
 assert p.stat().st_size>6500
 catalog=Path(destination)/'photos/catalog.json'
 data=json.loads(catalog.read_text(encoding='utf8'))
 assert 'rail_vy_x52' not in data
 data['rail_vy_x52']={
  'title':FILENAME,'label':'Vy-tåg i Oslo (exempelbild, ej bekräftat tågsätt)',
  'source':SOURCE,'author':'AleWi','license':'CC BY-SA 4.0','license_url':'https://creativecommons.org/licenses/by-sa/4.0/','modifications':'Resized and compressed to WebP',
  'path':'photos/images/rail_vy_x52.webp'}
 catalog.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
 print('AUTHORIZED LOCAL PHOTOGRAPH',p.stat().st_size,'bytes',SOURCE,'© AleWi CC BY-SA 4.0',flush=True)
def main():
 if len(sys.argv)!=2:raise SystemExit('Usage: download_vy_photo.py WEBSITE_ROOT')
 download(sys.argv[1])
if __name__=='__main__':main()
