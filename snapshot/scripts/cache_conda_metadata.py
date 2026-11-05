"""Cache official current channel metadata for offline WSL solver; no redirects."""
import bz2
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools' / 'python_lib'))
import requests


def fetch(pair):
    channel, subdir = pair
    dest = ROOT / 'work' / 'conda_channels' / channel / subdir
    dest.mkdir(parents=True, exist_ok=True)
    url = f'https://conda.anaconda.org/{channel}/{subdir}/current_repodata.json.bz2'
    started = time.time()
    response = requests.get(url, timeout=(15, 90), allow_redirects=False)
    if response.status_code != 200:
        raise RuntimeError(f'{url}: HTTP {response.status_code}')
    raw = response.content
    data = bz2.decompress(raw)
    json.loads(data)
    part = dest / 'repodata.json.part'
    part.write_bytes(data)
    os.replace(part, dest / 'repodata.json')
    receipt = {'source_url':url, 'bytes_compressed':len(raw), 'bytes_json':len(data),
               'sha256_compressed':hashlib.sha256(raw).hexdigest(),
               'sha256_json':hashlib.sha256(data).hexdigest(), 'seconds':time.time()-started}
    (dest / 'source_receipt.json').write_text(json.dumps(receipt, indent=2))
    return receipt


if __name__ == '__main__':
    pairs = [(c,s) for c in ('conda-forge','bioconda') for s in ('linux-64','noarch')]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        for receipt in ex.map(fetch, pairs):
            print(json.dumps(receipt), flush=True)
