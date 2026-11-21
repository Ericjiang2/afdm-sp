
import datetime,hashlib,json,time,urllib.parse,urllib.request
from pathlib import Path
root=Path('.trellis/tasks/09-13-trans-next/research/ce-state-literature-v1')
urls={
 'otnes-crossref':'https://api.crossref.org/works?'+urllib.parse.urlencode({'query.bibliographic':'Otnes Tuchler Iterative channel estimation turbo equalization time varying frequency selective channels','rows':2}),
 'chi-arxiv-search':'https://export.arxiv.org/api/query?'+urllib.parse.urlencode({'search_query':'all:AFDM AND all:memory','max_results':5}),
 'bigamp':'https://arxiv.org/html/1310.2632v2',
 'schniter':'https://arxiv.org/html/1101.4724v3',
 'kanazawa':'https://arxiv.org/html/2501.15935v3',
 'ranasinghe':'https://arxiv.org/html/2405.16945v3',
 'zheng':'https://arxiv.org/html/2404.10232v1',
 'zhang':'https://arxiv.org/html/2502.14203v2',
 'tipping':'https://www.miketipping.com/papers/met-fastsbl.pdf'}
manifest={}
for name,url in urls.items():
 item={'url':url,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (academic literature verification)'})
  with urllib.request.urlopen(req,timeout=25) as response:data=response.read();item['content_type']=response.headers.get('Content-Type');item['effective_url']=response.url
  suffix='.pdf' if data.startswith(b'%PDF-') else '.html' if b'<html' in data[:2000].lower() else '.txt'
  path=root/(name+suffix)
  with path.open('xb') as f:f.write(data)
  item.update(path=str(path),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
 except Exception as e:item['error']=type(e).__name__+': '+str(e)
 manifest[name]=item
 (root/'fetch-manifest-v1.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 print(name,item.get('bytes'),item.get('error','OK'),flush=True)
 time.sleep(1)
