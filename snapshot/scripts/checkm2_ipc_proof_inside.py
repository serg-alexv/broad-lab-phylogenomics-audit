"""One bounded IPC backend capability test; no genome or scientific model imports."""
from pathlib import Path
import fcntl,json,os,signal,subprocess,time,uuid
import checkm2_runtime_image as image
import checkm2_ipc_alias as ipc
R=image.R;E=image.E

def process_group(pgid):
 rows=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   f=(p/'stat').read_text().rsplit(')',1)[1].split()
   if int(f[2])==pgid and f[0]!='Z':
    rss=int(next(line.split()[1] for line in (p/'status').read_text().splitlines() if line.startswith('VmRSS:')))*1024
    rows.append({'pid':int(p.name),'creation_ticks':int(f[19]),'rss_bytes':rss})
  except (OSError,StopIteration,ValueError):continue
 return rows

def probe(mode,workspace,env):
 stem=mode.lower();alias_receipt=E/('ipc_'+stem+'_mount.json');child_receipt=E/('ipc_'+stem+'_probe.json')
 with ipc.IpcAlias(workspace/stem,mode,alias_receipt):
  childenv={**env,'TMPDIR':'/tmp','TMP':'/tmp','TEMP':'/tmp','TREE2_CHECKM2_PRIVATE_IPC_VERIFIED':'1','TREE2_CHECKM2_PRIVATE_IPC_RECEIPT':str(alias_receipt)}
  args=[str(image.PREFIX/'bin/python'),'-B',str(R/'scripts/checkm2_ipc_alias.py'),'--child-probe','--nonce',uuid.uuid4().hex[:16],'--receipt',str(child_receipt),'--scientific-scratch',str(workspace/'scientific_scratch')]
  with (E/('ipc_'+stem+'_stdout.txt')).open('w') as out,(E/('ipc_'+stem+'_stderr.txt')).open('w') as err:
   p=subprocess.Popen(args,env=childenv,start_new_session=True,stdout=out,stderr=err);started=time.monotonic();peak=0;failure=None
   while p.poll() is None:
    rows=process_group(p.pid);peak=max(peak,sum(x['rss_bytes'] for x in rows))
    available=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
    if time.monotonic()-started>30 or peak>2*1024**3 or available<1024**3 or (R/'state/STOP').exists():
     failure='Probe timeout, RSS/headroom gate, or STOP';os.killpg(p.pid,signal.SIGTERM);break
    time.sleep(.1)
   if failure:
    try:p.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=5)
   code=p.wait(timeout=5)
   remaining=process_group(p.pid)
   if remaining:raise RuntimeError('Probe descendant group not closed:'+repr(remaining))
   if failure:raise RuntimeError(failure)
  result=ipc.read(child_receipt)
  if code==8 and result['status']=='PROJECT_SOCKET_UNSUPPORTED' and mode=='PROJECT_BIND':pass
  elif code or result['status']!='PASS_SHORT_AF_UNIX_AND_SYNCMANAGER':raise RuntimeError('IPC primitive proof failed: '+repr(result))
  elif not all(result.get(k) for k in ('manager_child_closed','ipc_cache_survived_author_tmpdir_override','scientific_tempfiles_remain_project_durable')):raise RuntimeError('IPC/scientific separation not proved')
  result.update(child_exit_code=code,owned_group_empty=True,peak_owned_rss_bytes=peak,resource_limits={'threads':2,'rss_bytes':2*1024**3,'minimum_available_bytes':1024**3,'timeout_seconds':30})
  ipc.save(E/('ipc_'+stem+'_execution.json'),result)
 closure=ipc.read(alias_receipt.with_name(alias_receipt.stem+'_closure.json'))
 if closure['status']!='CLEAN_IPC_ALIAS_AND_BACKING_UNMOUNT':raise RuntimeError('IPC context did not close cleanly')
 return result

def main():
 image.private();claim=E/'ipc_inside_once_claim.json'
 with claim.open('x') as f:json.dump({'at_utc':ipc.utc(),'pid':os.getpid(),'scope':'ONE_PRIMARY_ONE_UNSUPPORTED_SOCKET_FALLBACK_NO_SCIENCE'},f);f.flush();os.fsync(f.fileno())
 lock=(R/'state/checkm2_pilot.lock').open('a+b');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 workspace=R/'work/checkm2_ipc/proof_v001';workspace.mkdir(exist_ok=False);(workspace/'scientific_scratch').mkdir()
 specpath=E/'sklearn161_effective_runtime_validated.json';effective=ipc.read(specpath)
 status='FAILED';primary=None;fallback=None;error=None
 try:
  with image.RuntimeImage(True,True,E/'ipc_runtime_mount.json') as mounted:
   if effective['base_image']['sha256']!=mounted.result['image_sha256']:raise RuntimeError('Proven runtime image differs')
   import checkm2_effective_bootstrap as bootstrap
   bootstrap.bind_overlay(mounted)
   env={**os.environ,**effective['required_runtime_environment'],'TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED':'1','TREE2_CHECKM2_RUNTIME_MOUNT_RECEIPT':str(mounted.receipt),'TREE2_EFFECTIVE_RUNTIME_MANIFEST':str(specpath),'TREE2_EFFECTIVE_RUNTIME_MANIFEST_SHA256':ipc.sha(specpath)}
   primary=probe('PROJECT_BIND',workspace,env)
   if primary['status']=='PROJECT_SOCKET_UNSUPPORTED':fallback=probe('TMPFS_32M',workspace,env)
   selected=fallback or primary
   if selected['status']!='PASS_SHORT_AF_UNIX_AND_SYNCMANAGER':raise RuntimeError('No IPC backend accepted')
  closure=ipc.read(E/'ipc_runtime_mount_closure.json')
  if closure['status']!='CLEAN_UNMOUNT_AND_LOOP_DETACH':raise RuntimeError('Runtime mount did not close')
  status='IPC_PRIMITIVES_AND_PRIVATE_CLOSURE_PASS'
 except BaseException as ex:error=repr(ex)
 finally:
  ipc.save(E/'ipc_inside_execution.json',{'status':status,'closed_utc':ipc.utc(),'error':error,'primary':primary,'fallback':fallback,'selected_mode':'TMPFS_32M' if fallback else 'PROJECT_BIND','all_owned_probe_groups_closed':bool((fallback or primary) and (fallback or primary).get('owned_group_empty')),'image_sha256':effective['base_image']['sha256'],'effective_runtime_manifest_sha256':ipc.sha(specpath),'helper_sha256':ipc.sha(R/'scripts/checkm2_ipc_alias.py'),'target_bootstrap_sha256':ipc.sha(R/'scripts/checkm2_ipc_bootstrap.py'),'unchanged_effective_bootstrap_sha256':ipc.sha(R/'scripts/checkm2_effective_bootstrap.py'),'genome_prediction_executed':False})
  lock.close()
 return 0 if status!='FAILED' else 2
if __name__=='__main__':raise SystemExit(main())
