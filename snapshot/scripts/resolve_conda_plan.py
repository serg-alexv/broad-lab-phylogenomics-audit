"""Resolve every LINK record, including packages already present in cache."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
plan=json.loads((ROOT/'evidence'/'tooling'/'conda_offline_dryrun.json').read_text())
indexes={}
rows=[]
for link in plan['actions']['LINK']:
    channel,subdir=link['channel'],link['platform']
    assert channel in ('conda-forge','bioconda') and subdir in ('linux-64','noarch')
    key=(channel,subdir)
    if key not in indexes:
        indexes[key]=json.loads((ROOT/'work'/'conda_channels'/channel/subdir/'repodata.json').read_text())
    candidates=[]
    for group in ('packages','packages.conda'):
        for filename,record in indexes[key][group].items():
            if (record['name'],record['version'],record['build'])==(link['name'],link['version'],link['build_string']):
                candidates.append((filename,record))
    assert candidates, link
    candidates.sort(key=lambda x:not x[0].endswith('.conda'))
    filename,record=candidates[0]
    row=dict(record)
    row.update(fn=filename,subdir=subdir,channel=link['base_url']+'/'+subdir,
               url=link['base_url']+'/'+subdir+'/'+filename)
    rows.append(row)
assert len(rows)==len(plan['actions']['LINK'])
(ROOT/'evidence'/'tooling'/'resolved_packages.json').write_text(json.dumps(rows,indent=2))
print(json.dumps({'full_link_count':len(rows),'compressed_bytes':sum(r['size'] for r in rows)}))
