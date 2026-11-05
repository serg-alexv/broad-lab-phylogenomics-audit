"""One native-owned, finite IPC proof with before/after host and image evidence."""
from pathlib import Path
import json,msvcrt,os,subprocess,time
import checkm2_private_install_controller as base
R=base.R;E=base.E;L=base.L

def global_tmp(marker):
 code="import json,os,pathlib,subprocess; p=pathlib.Path('/tmp');s=p.stat();print(json.dumps({'mount_namespace':os.readlink('/proc/self/ns/mnt'),'dev':s.st_dev,'ino':s.st_ino,'mode':s.st_mode,'mount':subprocess.check_output(['findmnt','-T','/tmp','-n','-o','TARGET,SOURCE,FSTYPE,VFS-OPTIONS'],text=True).strip(),'marker_exists':(p/"+repr(marker)+").exists()}))"
 return json.loads(subprocess.check_output(['wsl','-d','Ubuntu','--','/usr/bin/python3','-B','-c',code],text=True,timeout=30))
def progress(detail,done=0,status='RUNNING'):
 base.save(R/'state/tool_setup_progress.json',{'status':status,'done':done,'total':3,'unit':'IPC proof phases','detail':detail,'updated_utc':base.utc(),'started_utc':base.START,'pid':base.OWNER['pid'],'creation_time_utc':base.OWNER['creation_time_utc'],'log_path':str(E/'ipc_inside_execution.json')})
def main():
 base.gate();closed=base.read(R/'state/checkm2_pilot_baseline_failure_closure.json')
 if closed['status']!='BASELINE_FAILURE_FULLY_CLOSED_READY_FOR_IPC_PROOF' or not closed['native_original_absent'] or not closed['launcher_os_lock_reacquired']:raise RuntimeError('Baseline closure not admitted')
 # The common file-share denial and byte lock exclude the native pilot/setup.
 native=(R/'state/checkm2_pilot_launcher.lock').open('a+b');native.seek(0);msvcrt.locking(native.fileno(),msvcrt.LK_NBLCK,1)
 setup=(R/'state/checkm2_install.lock').open('a+b');setup.seek(0);msvcrt.locking(setup.fileno(),msvcrt.LK_NBLCK,1)
 with (E/'ipc_native_once_claim.json').open('x') as f:json.dump({'at_utc':base.utc(),'owner':base.OWNER,'baseline_closure_sha256':base.sha(R/'state/checkm2_pilot_baseline_failure_closure.json')},f);f.flush();os.fsync(f.fileno())
 (R/'work/checkm2_ipc').mkdir(exist_ok=True)
 marker='tree2-ipc-outside-'+str(base.OWNER['pid']);before=base.private.registry();tmp_before=global_tmp(marker)
 if tmp_before['marker_exists']:raise RuntimeError('Unexpected outside marker')
 base.save(R/'state/launch_tool_setup.json',{**base.OWNER,'script':'scripts/checkm2_ipc_proof_controller.py','phase':'PRIVATE_SHORT_IPC_PROOF_NO_SCIENCE'})
 status='FAILED';error=None;inside=None;imagehash=None;childcode=None
 progress('Checking short private IPC and durable scientific scratch separation; no genome prediction')
 try:
  with (R/'logs/checkm2_ipc_proof.stdout.txt').open('w') as out,(R/'logs/checkm2_ipc_proof.stderr.txt').open('w') as err:
   p=subprocess.Popen(['wsl','-d','Ubuntu','--','/bin/bash',L+'/scripts/checkm2_private_setup_ns.sh','outer','run',L+'/scripts/checkm2_ipc_proof.sh'],stdout=out,stderr=err)
   deadline=time.monotonic()+1200;last=0
   while p.poll() is None:
    if time.monotonic()>deadline or (R/'state/STOP').exists():
     p.terminate();p.wait(timeout=20);raise RuntimeError('IPC proof stopped/deadline; no automatic retry')
    if time.monotonic()-last>3:progress('Verifying read-only runtime and private short socket/Manager capability; no user input required');last=time.monotonic()
    time.sleep(.5)
   childcode=p.returncode
   if childcode:raise RuntimeError('IPC namespace proof exit'+str(childcode))
  inside=base.read(E/'ipc_inside_execution.json');closure=base.read(E/'ipc_runtime_mount_closure.json')
  if inside['status']!='IPC_PRIMITIVES_AND_PRIVATE_CLOSURE_PASS' or not inside['all_owned_probe_groups_closed'] or closure['status']!='CLEAN_UNMOUNT_AND_LOOP_DETACH':raise RuntimeError('IPC primitive/namespace closure not accepted')
  progress('IPC probes closed; verifying the sealed image remained unchanged',2)
  imagepath=R/'tools/checkm2_runtime_ext4.img'
  import hashlib
  digest=hashlib.sha256();count=0;started=time.monotonic();last=0
  with imagepath.open('rb') as f:
   while chunk:=f.read(16*1024**2):
    digest.update(chunk);count+=len(chunk)
    if time.monotonic()-started>600 or (R/'state/STOP').exists():raise RuntimeError('Closed-image verification deadline/STOP')
    if time.monotonic()-last>3:progress(f'IPC probes closed; unchanged-image verification {count}/{imagepath.stat().st_size} bytes',2);last=time.monotonic()
  imagehash=digest.hexdigest()
  if imagehash!=inside['image_sha256']:raise RuntimeError('Runtime image changed')
  status='PRIVATE_SHORT_IPC_PROVEN'
 except BaseException as ex:error=repr(ex)
 finally:
  after=base.private.registry();tmp_after=global_tmp(marker);same=before==after and tmp_before==tmp_after
  if not same:status='FAILED';error='Shared registry or outside /tmp mapping changed'
  receipt={'status':status,'created_utc':base.utc(),'native_owner':base.OWNER,'error':error,'child_exit_code':childcode,'inside_receipt_path':'evidence/checkm2_runtime/ipc_inside_execution.json','inside_receipt_sha256':base.sha(E/'ipc_inside_execution.json') if inside else None,'inside_result':inside,'selected_mode':inside['selected_mode'] if inside else None,'host_registry_before':before,'host_registry_after':after,'host_registry_unchanged':before==after,'global_tmp_before':tmp_before,'global_tmp_after':tmp_after,'global_tmp_unchanged':tmp_before==tmp_after,'image_sha256':imagehash,'effective_runtime_manifest_sha256':inside['effective_runtime_manifest_sha256'] if inside else None,'helper_sha256':base.sha(R/'scripts/checkm2_ipc_alias.py'),'target_bootstrap_sha256':base.sha(R/'scripts/checkm2_ipc_bootstrap.py'),'unchanged_effective_bootstrap_sha256':base.sha(R/'scripts/checkm2_effective_bootstrap.py'),'scientific_prediction_executed':False,'production_acceptance':False,'baseline_closure_path':'state/checkm2_pilot_baseline_failure_closure.json','baseline_closure_sha256':base.sha(R/'state/checkm2_pilot_baseline_failure_closure.json')}
  base.save(E/'ipc_capability_proof.json',receipt)
  progress('Short private IPC and durable scratch separation proved; one fresh resource pilot may be admitted' if status!='FAILED' else error,3 if status!='FAILED' else 0,'COMPLETE' if status!='FAILED' else 'FAILED')
  setup.close();native.close()
 return 0 if status!='FAILED' else 2
if __name__=='__main__':raise SystemExit(main())
