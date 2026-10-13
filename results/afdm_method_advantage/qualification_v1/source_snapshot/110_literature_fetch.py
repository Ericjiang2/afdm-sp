"""Retrieve a fixed list of public papers; archive errors and reading locations."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '.mission/20261003_10-41-29-afdm-structured-inference-exploration/literature'
IDS = ['1508.07575','2405.16945','2607.18881','2512.14776','2001.03930',
       '2511.21340','1609.07152','2412.09068','1206.5162','1106.1137',
       '1211.5608','1809.09336']

def fetch(item):
    name, url = item
    record = dict(name=name, url=url, accessed=datetime.now(timezone.utc).isoformat())
    try:
        request = urllib.request.Request(url, headers={'User-Agent':'Academic literature verification/1.0'})
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read()
            record.update(status=response.status, final_url=response.geturl(),
                          sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
        target = OUT / (name + '.html')
        target.write_bytes(data)
        record['path'] = str(target.relative_to(ROOT))
    except Exception as error:
        record.update(status='unavailable', error=str(error))
    return record

if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=False)
    query = urllib.parse.urlencode(dict(search_query='all:AFDM AND (all:Bayesian OR all:inference)',
                                       start=0,max_results=10,sortBy='submittedDate',sortOrder='descending'))
    items = [(identifier,'https://arxiv.org/html/'+identifier) for identifier in IDS]
    items.append(('latest-search','https://export.arxiv.org/api/query?'+query))
    with ThreadPoolExecutor(max_workers=3) as executor:
        records = list(executor.map(fetch, items))
    (OUT/'fetch.json').write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps([{k:r.get(k) for k in ('name','status','bytes','error')} for r in records],indent=2))
