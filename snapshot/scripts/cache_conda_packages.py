"""Cache exact solver-selected official packages, verifying channel SHA256."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'/'python_lib'))
import requests


def fetch(row):
    suffix=row['url'].split('/conda_channels/',1)[1]
    channel,subdir,filename=suffix.split('/')
    assert channel in ('conda-forge','bioconda') and subdir in ('linux-64','noarch')
    assert filename==row['fn'] and '..' not in filename
    url='https://conda.anaconda.org/'+suffix
    dest=ROOT/'work'/'conda_channels'/channel/subdir/filename
    receipt={k:row.get(k) for k in ('name','version','build','size','sha256','license','depends')}
    receipt['source_url']=url
    if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest()==row['sha256']:
        receipt['action']='VERIFIED_SKIP'
        return receipt
    part=dest.with_name(dest.name+'.part')
    for attempt in range(3):
        try:
            h=hashlib.sha256()
            count=0
            with requests.get(url,stream=True,timeout=(15,90),allow_redirects=False) as response:
                if response.status_code!=200:
                    raise RuntimeError(f'{url} HTTP {response.status_code}')
                with part.open('wb') as f:
                    for chunk in response.iter_content(1024*1024):
                        f.write(chunk);h.update(chunk);count+=len(chunk)
                    f.flush();os.fsync(f.fileno())
            assert count==row['size'] and h.hexdigest()==row['sha256'], 'Package checksum/size mismatch'
            os.replace(part,dest)
            receipt['action']='CACHED_VERIFIED'
            return receipt
        except Exception:
            if attempt==2:raise
            time.sleep(2**attempt)


if __name__=='__main__':
    rows=json.loads((ROOT/'evidence'/'tooling'/'resolved_packages.json').read_text())
    assert sum(x['size'] for x in rows)<500*1024**2, 'Compressed download exceeds bounded admission'
    receipts=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        for receipt in ex.map(fetch,rows):
            receipts.append(receipt)
            print(json.dumps(receipt),flush=True)
    (ROOT/'evidence'/'tooling'/'package_sources.json').write_text(json.dumps(receipts,indent=2))
