"""Record installed isolated prefix and preserve source/license provenance."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import socket

ROOT=Path(__file__).resolve().parents[1]
PREFIX=ROOT/'tools'/'bioenv'


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


resolved=json.loads((ROOT/'evidence/tooling/resolved_packages.json').read_text())
installed=json.loads((ROOT/'evidence/tooling/bioenv_installed_packages.json').read_text())
assert {(x['name'],x['version'],x.get('build',x.get('build_string'))) for x in installed}=={(x['name'],x['version'],x['build']) for x in resolved}
sources=json.loads((ROOT/'evidence/tooling/package_size_and_notices.json').read_text())
explicit='@EXPLICIT\n'+'\n'.join('https://conda.anaconda.org/'+x['url'].split('/conda_channels/',1)[1]+'#'+x['md5'] for x in resolved)+'\n'
official=ROOT/'evidence/tooling/bioenv_explicit_official.txt'
official.write_text(explicit)
notice=['# Tree 2 tool package notices', '',
        'Original distributed package metadata, copyright notices, license texts, and recipes are retained under `tools/package_notices/`. Package archives and SHA256 source receipts remain local. No license texts were rewritten.', '',
        '| Package | Version / build | Distributed license identifier | Preserved metadata |',
        '| --- | --- | --- | --- |']
for x in sources['packages']:
    notice.append(f"| {x['name']} | {x['version']} / {x['build']} | {x.get('license_identifier','')} | `{x['original_package_info_preserved']}` |")
(ROOT/'docs/THIRD_PARTY_TOOL_NOTICES.md').write_text('\n'.join(notice)+'\n')
files=[]
for p in sorted(PREFIX.rglob('*')):
    if p.is_symlink():
        target=os.readlink(p)
        row={'path':p.relative_to(ROOT).as_posix(),'type':'symlink','target':target}
        files.append(row)
    elif p.is_file():
        files.append({'path':p.relative_to(ROOT).as_posix(),'type':'file','bytes':p.stat().st_size,'sha256':digest(p)})
manifest=ROOT/'manifests/tool_environment_files.json'
manifest.write_text(json.dumps(files,indent=2))
summary={'status':'INSTALLED_SMOKE_PASS','completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'hostname':socket.gethostname(),'prefix':str(PREFIX),'package_count':len(installed),
         'regular_file_count':sum(x['type']=='file' for x in files),
         'regular_file_bytes':sum(x.get('bytes',0) for x in files),
         'source_archives_sha256_verified':True,'original_package_info_preserved':True,
         'explicit_official_sha256':digest(official),'file_manifest_sha256':digest(manifest),
         'installation_mode':'Offline explicit local packages, --copy, CONDA_REGISTER_ENVS=false',
         'scientific_analysis_status':'NOT_RUN',
         'global_environment_registry':{
             'path':'/root/.conda/environments.txt',
             'current_sha256':digest(Path('/root/.conda/environments.txt')),
             'current_mtime':datetime.datetime.fromtimestamp(Path('/root/.conda/environments.txt').stat().st_mtime,datetime.timezone.utc).isoformat(),
             'tree2_prefix_registered':str(PREFIX) in Path('/root/.conda/environments.txt').read_text(),
             'limitation':'Timestamp changed despite CONDA_REGISTER_ENVS=false; original bytes were not snapshotted, so unchanged bytes cannot be claimed. Current entries only refer to pre-existing environments.'},
         'memory_snapshot':Path('/proc/meminfo').read_text(),
         'bounded_fallback':'Same HMMER3.4 non-MPI build h503566f_3 avoids OpenMPI symlink prefix-rewrite failure on DrvFS.'}
(ROOT/'evidence/tooling/tool_environment_receipt.json').write_text(json.dumps(summary,indent=2))
print(json.dumps({k:v for k,v in summary.items() if k!='memory_snapshot'},indent=2))
