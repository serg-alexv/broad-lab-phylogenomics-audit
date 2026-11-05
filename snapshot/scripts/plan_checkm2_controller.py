"""Run only dependency resolution inside the verified private namespace."""
from pathlib import Path
import datetime as dt,hashlib,json,os,subprocess,time
import checkm2_private_setup_driver as private
import plan_checkm2_runtime as planner
R=Path(__file__).resolve().parents[1]
L='/mnt/c/'+str(R)[3:].replace('\\','/')
def utc():return dt.datetime.now(dt.timezone.utc).isoformat()
def save(path,value):
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8');os.replace(tmp,path)
def main():
    if os.environ.get('COMPUTERNAME','').upper()!='WD':raise RuntimeError('WD-only resolver')
    if (R/'state/STOP').exists():raise RuntimeError('STOP already requested; no solver launch')
    import msvcrt
    lock=(R/'state/checkm2_resolve.lock').open('a+b');lock.write(b'0');lock.flush();lock.seek(0)
    msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    ev=R/'evidence/checkm2_runtime';ev.mkdir(parents=True,exist_ok=True)
    proof=json.loads((ev/'namespace_proof_receipt.json').read_text())
    if proof['status']!='COMPLETE' or proof['host_registry_unchanged'] is not True:raise RuntimeError('Namespace proof unavailable')
    planner.prepare()
    before=private.registry();save(ev/'resolve_registry_before.json',before)
    for _ in range(40):
        launch=R/'state/launch_tool_setup.json'
        if launch.exists():
            owner=json.loads(launch.read_text(encoding='utf-8-sig'))
            if owner.get('pid')==os.getpid():break
        time.sleep(.1)
    else:raise RuntimeError('Native launcher identity not registered')
    started=utc();state={'status':'RUNNING','done':0,'total':1,'unit':'dependency plan',
      'detail':'Resolving isolated CPU-only CheckM2 runtime; no user input required',
      'pid':os.getpid(),'creation_time_utc':owner['creation_time_utc'],'started_utc':started,
      'log_path':str(ev/'solve.stderr.txt')}
    save(R/'state/tool_setup_progress.json',{**state,'updated_utc':utc()})
    status='FAILED';error=None;childcode=None;summary=None
    try:
        with (ev/'resolve_namespace.stdout.jsonl').open('w') as out,(ev/'resolve_namespace.stderr.txt').open('w') as err:
            child=subprocess.Popen(['wsl','-d','Ubuntu','--','/bin/bash',L+'/scripts/checkm2_private_setup_ns.sh','outer','run',L+'/work/checkm2_resolution/solve_private.sh'],stdout=out,stderr=err)
            while child.poll() is None:
                save(R/'state/tool_setup_progress.json',{**state,'updated_utc':utc()});time.sleep(3)
            childcode=child.returncode
            if childcode!=0:raise RuntimeError(f'Private solver exited{childcode}; inspect solve.stderr.txt')
        summary=planner.audit();status='COMPLETE'
    except Exception as exc:error=repr(exc)
    finally:
        after=private.registry();same=before==after
        if not same:status='FAILED';error='Host registry changed; do not restore unknown baseline'
        receipt={'status':status,'started_utc':started,'ended_utc':utc(),'native_pid':os.getpid(),
                 'child_exit_code':childcode,'error':error,'host_registry_before':before,
                 'host_registry_after':after,'host_registry_unchanged':same,'resolution':summary,
                 'environment_installed':False,'scientific_qc_run':False,
                 'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        save(ev/'resolve_execution_receipt.json',receipt)
        save(R/'state/tool_setup_progress.json',{**state,'status':status,'done':1 if status=='COMPLETE' else 0,
             'detail':'Pinned CPU-only dependency closure resolved; acquisition/installation pending' if status=='COMPLETE' else error,
             'ended_utc':utc(),'updated_utc':utc(),'receipt_path':str(ev/'resolve_execution_receipt.json')})
        lock.close();print(json.dumps(receipt),flush=True)
    return 0 if status=='COMPLETE' else 2
if __name__=='__main__':raise SystemExit(main())
