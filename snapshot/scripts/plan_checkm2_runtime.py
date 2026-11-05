"""Prepare and audit exact CPU-only CheckM2 runtime resolution.

This script does not invoke conda or install anything. Run the emitted shell
script only through a separately verified project-private mount namespace.
"""
from pathlib import Path
import argparse, datetime, hashlib, json, os, shutil
R=Path(__file__).resolve().parents[1]
WORK=R/'work/checkm2_resolution'
EVIDENCE=R/'evidence/checkm2_runtime'
SPECS=['python=3.12','checkm2=1.1.0=pyhdfd78af_2','diamond=2.1.11',
       'tensorflow=2.19.1=cpu_py312h3336143_5','tensorflow-base=2.19.1=cpu_py312h9edca52_5',
       '_x86_64-microarch-level=3=5_skylake']
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def atomic(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp')
    with tmp.open('w',encoding='utf-8',newline='\n') as f:
        json.dump(obj,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)
def prepare():
    WORK.mkdir(parents=True,exist_ok=True);EVIDENCE.mkdir(parents=True,exist_ok=True)
    inputs=[]
    for channel in ('conda-forge','bioconda'):
        for subdir in ('linux-64','noarch'):
            source=R/'work/conda_channels'/channel/subdir/'repodata.json'
            dest=WORK/'channels'/channel/subdir/'repodata.json'
            dest.parent.mkdir(parents=True,exist_ok=True)
            if not dest.exists():shutil.copyfile(source,dest)
            if sha(source)!=sha(dest):
                supplement=json.loads((EVIDENCE/'metadata_supplement.json').read_text())
                match=[x for x in supplement['derived_channels'] if x['path']==str(dest.relative_to(R))]
                if len(match)!=1 or match[0]['base_sha256']!=sha(source) or match[0]['derived_sha256']!=sha(dest):
                    raise RuntimeError('Unverified metadata copy drift: '+str(dest))
            inputs.append({'channel':channel,'subdir':subdir,'path':str(dest.relative_to(R)),
                           'sha256':sha(dest),'bytes':dest.stat().st_size})
    linux='/mnt/'+R.drive[0].lower()+'/'+str(R)[3:].replace('\\','/') if os.name=='nt' else str(R)
    lines=['#!/usr/bin/env bash','set -euo pipefail',f"ROOT='{linux}'",
           'test "${TREE2_PRIVATE_NAMESPACE_VERIFIED:-}" = 1 || { echo "Require verified private namespace" >&2; exit 80; }',
           'export CONDA_PKGS_DIRS="$ROOT/work/checkm2_resolution/pkgs"',
           'export CONDA_ENVS_PATH="$ROOT/work/checkm2_resolution/envs"',
           'export TMPDIR="$ROOT/work/checkm2_resolution/tmp" TMP="$ROOT/work/checkm2_resolution/tmp" TEMP="$ROOT/work/checkm2_resolution/tmp"',
           'export XDG_CACHE_HOME="$ROOT/work/checkm2_resolution/xdg"',
           'export CONDA_REGISTER_ENVS=false CONDA_REPORT_ERRORS=false CONDA_NOTIFY_OUTDATED_CONDA=false CONDA_AUTO_UPDATE_CONDA=false',
           'export CONDA_NO_PLUGINS=false',
           'export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2',
           'mkdir -p "$TMPDIR" "$XDG_CACHE_HOME" "$CONDA_PKGS_DIRS" "$CONDA_ENVS_PATH"',
           'ulimit -v 2097152',
           '/usr/bin/timeout --signal=TERM --kill-after=10s 600s /usr/bin/time -v /root/miniconda3/bin/conda create --dry-run --json --solver libmamba --override-channels --no-default-packages --copy --repodata-fn repodata.json -p "$ROOT/tools/checkm2_env" -c "file://$ROOT/work/checkm2_resolution/channels/conda-forge" -c "file://$ROOT/work/checkm2_resolution/channels/bioconda" '+ ' '.join("'"+s+"'" for s in SPECS)+' > "$ROOT/evidence/checkm2_runtime/solve.json" 2> "$ROOT/evidence/checkm2_runtime/solve.stderr.txt" &',
           'SOLVER_PID=$!',
           'while kill -0 "$SOLVER_PID" 2>/dev/null; do',
           '  if [[ -f "$ROOT/state/STOP" ]]; then kill -TERM "$SOLVER_PID" 2>/dev/null || true; wait "$SOLVER_PID" || true; exit 130; fi',
           '  sleep 2',
           'done',
           'wait "$SOLVER_PID"']
    script=WORK/'solve_private.sh';script.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    atomic(EVIDENCE/'resolution_inputs.json',{'prepared_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'status':'PREPARED_NOT_SOLVED','constraints':SPECS,'inputs':inputs,
           'solver_script':str(script.relative_to(R)),'solver_script_sha256':sha(script),
           'isolation_requirement':'Verified mount namespace redirects all registries/caches into project; no outside entrypoint call authorized by this script',
           'gpu_policy':'Reject all CUDA/cuDNN/NCCL packages; CPU TensorFlow only'})
    return {'status':'PREPARED_NOT_SOLVED','specs':SPECS,'script':str(script)}
def audit():
    plan=json.loads((EVIDENCE/'solve.json').read_text(encoding='utf-8-sig'))
    if not plan.get('success'):raise RuntimeError('Solver did not succeed: '+str(plan.get('error')))
    rows=[];indexes={}
    for link in plan['actions']['LINK']:
        channel,subdir=link['channel'],link['platform']
        if channel not in ('conda-forge','bioconda') or subdir not in ('linux-64','noarch'):
            raise RuntimeError('Unexpected channel/subdir: '+str(link))
        if (channel,subdir) not in indexes:
            indexes[channel,subdir]=json.loads((WORK/'channels'/channel/subdir/'repodata.json').read_text())
        data=indexes[channel,subdir];found=[]
        for group in ('packages','packages.conda'):
            for fn,rec in data[group].items():
                if (rec['name'],rec['version'],rec['build'])==(link['name'],link['version'],link['build_string']):found.append((fn,rec))
        if not found:raise RuntimeError('No exact official record for '+str(link))
        found.sort(key=lambda row:not row[0].endswith('.conda'));fn,rec=found[0]
        name=rec['name'].lower()
        if any(x in name for x in ('cuda','cudnn','cublas','nccl','cutensor','cufft','curand','cusolver','cusparse')):
            raise RuntimeError('GPU dependency forbidden: '+name)
        if not rec.get('sha256'):raise RuntimeError('Missing package SHA256: '+fn)
        rows.append({**rec,'fn':fn,'subdir':subdir,'channel_name':channel,
                     'url':f'https://conda.anaconda.org/{channel}/{subdir}/{fn}'})
    byname={r['name']:r for r in rows}
    assert byname['python']['version'].startswith('3.12.')
    assert byname['checkm2']['version']=='1.1.0' and byname['checkm2']['build']=='pyhdfd78af_2'
    assert byname['diamond']['version']=='2.1.11'
    assert byname['tensorflow']['version']=='2.19.1' and byname['tensorflow']['build'].startswith('cpu_py312')
    assert byname['tensorflow-base']['build'].startswith('cpu_py312')
    assert byname['tensorflow']['build']=='cpu_py312h3336143_5'
    assert byname['tensorflow-base']['build']=='cpu_py312h9edca52_5'
    assert byname['_x86_64-microarch-level']['version']=='3'
    assert byname['_x86_64-microarch-level']['build']=='5_skylake'
    atomic(EVIDENCE/'resolved_packages.json',rows)
    summary={'status':'SOLVED_CPU_ONLY_PINNED','package_count':len(rows),'compressed_bytes':sum(r['size'] for r in rows),
             'records_sha256':sha(EVIDENCE/'resolved_packages.json'),
             'pins':{n:{k:byname[n][k] for k in ('version','build','size','sha256')} for n in ('python','checkm2','diamond','tensorflow','tensorflow-base')},
             'unpacked_bytes':'NOT_MEASURED_UNTIL_PACKAGE_INSPECTION','installation':'NOT_RUN'}
    summary['cpu_provider']={k:byname['_x86_64-microarch-level'][k] for k in ('version','build','depends','sha256')}
    atomic(EVIDENCE/'resolution_summary.json',summary)
    return summary
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','audit']);args=ap.parse_args()
    print(json.dumps(prepare() if args.action=='prepare' else audit()))
