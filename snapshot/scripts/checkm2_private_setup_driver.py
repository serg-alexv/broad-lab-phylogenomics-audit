"""Windows driver for a bounded private Linux mount-namespace setup proof."""
from pathlib import Path
import datetime as dt, hashlib,json,os,subprocess,sys,time
R=Path(__file__).resolve().parents[1]
L='/mnt/c/'+str(R)[3:].replace('\\','/')
def utc():return dt.datetime.now(dt.timezone.utc).isoformat()
def save(p,obj):
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8');os.replace(t,p)
def registry():
 code="import hashlib,json,pathlib; p=pathlib.Path('/root/.conda/environments.txt'); s=p.stat(); print(json.dumps({'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'mtime_ns':s.st_mtime_ns,'size':s.st_size,'canary_exists':pathlib.Path('/root/.conda/TREE2_PRIVATE_NAMESPACE_CANARY').exists()}))"
 return json.loads(subprocess.check_output(['wsl','-d','Ubuntu','--','/usr/bin/python3','-c',code],text=True))
def main():
 if os.environ.get('COMPUTERNAME','').upper()!='WD':raise RuntimeError('WD-only setup')
 ev=R/'evidence/checkm2_runtime';ev.mkdir(parents=True,exist_ok=True)
 for d in ('work/checkm2_private_registry','work/checkm2_private_tmp','work/checkm2_private_xdg','tools/checkm2_runtime_pkgs','tools/checkm2_runtime_envs'):(R/d).mkdir(parents=True,exist_ok=True)
 before=registry();save(ev/'host_registry_before.json',before)
 if before['canary_exists']:raise RuntimeError('Unexpected host registry canary before proof')
 log=R/'logs/checkm2_private_setup.log';err=R/'logs/checkm2_private_setup.stderr'
 started=utc();launch=R/'state/launch_tool_setup.json'
 for _ in range(30):
  if launch.exists() and json.loads(launch.read_text(encoding='utf-8-sig')).get('pid')==os.getpid():break
  time.sleep(.1)
 owner=json.loads(launch.read_text(encoding='utf-8-sig')) if launch.exists() else {}
 state={'status':'RUNNING','done':0,'total':1,'unit':'proof','detail':'Testing registry-free private installer namespace; no user input required','pid':os.getpid(),'creation_time_utc':owner.get('creation_time_utc'),'started_utc':started,'log_path':str(log)}
 save(R/'state/tool_setup_progress.json',{**state,'updated_utc':utc()})
 status='FAILED';failure=None
 try:
  with log.open('w',encoding='utf-8') as out,err.open('w',encoding='utf-8') as er:
   p=subprocess.Popen(['wsl','-d','Ubuntu','--','/bin/bash',L+'/scripts/checkm2_private_setup_ns.sh','outer','proof'],stdout=out,stderr=er)
   deadline=time.monotonic()+90
   while p.poll() is None:
    if (R/'state/STOP').exists() or time.monotonic()>deadline:
     p.terminate();p.wait(timeout=15);raise RuntimeError('Setup proof stopped or timed out')
    save(R/'state/tool_setup_progress.json',{**state,'updated_utc':utc()});time.sleep(2)
   if p.returncode:raise RuntimeError(f'Private namespace proof exited {p.returncode}; see stderr')
  status='COMPLETE'
 except Exception as exc:failure=repr(exc)
 finally:
  after=registry();same=before==after
  if not same:status='FAILED';failure='Host registry baseline changed; do not restore blindly'
  receipt={'status':status,'before':before,'after':after,'host_registry_unchanged':same,'error':failure,'at_utc':utc(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'environment_installed':False,'scientific_pilot_run':False}
  save(ev/'namespace_proof_receipt.json',receipt)
  save(R/'state/tool_setup_progress.json',{**state,'status':status,'done':1 if status=='COMPLETE' else 0,'detail':'Private namespace proof passed; isolated runtime resolution next' if status=='COMPLETE' else failure,'updated_utc':utc(),'ended_utc':utc(),'receipt_path':str(ev/'namespace_proof_receipt.json')})
  print(json.dumps(receipt),flush=True)
 return 0 if status=='COMPLETE' else 2
if __name__=='__main__':raise SystemExit(main())
