"""Bounded private-namespace owner of one file-only validator group."""
from pathlib import Path
import fcntl,json,os,shutil,signal,subprocess,time
import checkm2_runtime_image as image
import checkm2_posthoc_v002_validator as v
R=v.R;E=R/'evidence/checkm2_posthoc_v002/v001';ADMISSION=R/'evidence/checkm2_posthoc_v002/admission.json'
RSS=2*1024**3;HEADROOM=1024**3
def available():return int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
def rows(pgid):
 values=[]
 for path in Path('/proc').iterdir():
  if not path.name.isdigit():continue
  try:
   x=(path/'stat').read_text().rsplit(')',1)[1].split()
   if int(x[2])==pgid:values.append({'pid':int(path.name),'parent_pid':int(x[1]),'process_group':int(x[2]),'creation_ticks':int(x[19]),'state':x[0],'rss_bytes':int(x[21])*os.sysconf('SC_PAGE_SIZE'),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()})
  except (FileNotFoundError,ProcessLookupError):pass
 return values
def stopped():return (R/'state/STOP').exists() or (R/'state/STOP_CHECKM2_POSTHOC_V002').exists()
def step(detail,**extra):v.save(R/'state/checkm2_posthoc_v002_step.json',{'updated_utc':image.utc(),'detail':detail,'scope':'SAVED_OUTPUT_VALIDATION_ONLY_NO_PREDICTION_RERUN',**extra})
def close_child(child):
 if child is None:return []
 if child.poll() is None:
  try:os.killpg(child.pid,signal.SIGTERM)
  except ProcessLookupError:pass
  try:child.wait(timeout=5)
  except subprocess.TimeoutExpired:
   try:os.killpg(child.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   child.wait(timeout=5)
 remaining=rows(child.pid)
 if remaining:
  try:os.killpg(child.pid,signal.SIGKILL)
  except ProcessLookupError:pass
  deadline=time.monotonic()+5
  while remaining and time.monotonic()<deadline:time.sleep(.1);remaining=rows(child.pid)
 return remaining
def main():
 image.private();admission=v.read(ADMISSION);v.preflight(admission);E.mkdir(parents=True,exist_ok=False)
 lock=(R/'state/checkm2_pilot.lock').open('a+b');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 with (E/'once_claim.json').open('x') as f:json.dump({'scope':'ONE_FILE_ONLY_POSTHOC_VALIDATION','at_utc':image.utc(),'admission_sha256':v.sha(ADMISSION)},f);f.flush();os.fsync(f.fileno())
 os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:2]));child=None;error=None;target=None;peak=0;minmem=2**63;identity=None;remaining=[];started=None;execution=None
 try:
  if stopped() or available()<HEADROOM or shutil.disk_usage(R).free<40*1024**3:raise RuntimeError('STOP/headroom/disk preflight gate')
  step('Saved-output validation only; verifying pinned read-only image; no prediction rerun')
  with image.RuntimeImage(True,True,E/'runtime_mount.json') as mounted:
   import checkm2_effective_bootstrap as bootstrap
   bootstrap.bind_overlay(mounted) # bind/verify only; never preload/main/model import
   if mounted.result['image_sha256']!=admission['runtime_image_sha256']:raise RuntimeError('Admitted runtime image differs')
   effective=v.read(v.bind(admission['effective_runtime']));env={**os.environ,**effective['required_runtime_environment'],'TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED':'1','TREE2_CHECKM2_RUNTIME_MOUNT_RECEIPT':str(mounted.receipt)}
   prefix=v.inside(admission['runtime_prefix']);cmd=[str(prefix/'bin/python'),'-B',str(R/'scripts/checkm2_posthoc_v002_validator.py'),'--admission',str(ADMISSION),'--admission-sha256',v.sha(ADMISSION),'--output',str(E/'validation.json')]
   v.save(E/'command.json',{'command':cmd,'HOME_unchanged':env.get('HOME')==os.environ.get('HOME'),'models_or_genomes_generated':0,'limits':{'cpu_affinity_max':2,'summed_group_RSS_bytes':RSS,'Linux_headroom_bytes':HEADROOM,'seconds':600}})
   try:
    with (E/'stdout.txt').open('w') as out,(E/'stderr.txt').open('w') as err:
     child=subprocess.Popen(cmd,env=env,stdout=out,stderr=err,start_new_session=True);started=time.monotonic();born=rows(child.pid);identity=next((x for x in born if x['pid']==child.pid),{'pid':child.pid,'creation_identity':'UNKNOWN_EXITED_EARLY'})
     while child.poll() is None:
      observed=rows(child.pid);rss=sum(x['rss_bytes'] for x in observed);peak=max(peak,rss);mem=available();minmem=min(minmem,mem)
      if rss>RSS:raise RuntimeError('RESOURCE_GATE summedRSS exceeds2GiB')
      if mem<HEADROOM:raise RuntimeError('RESOURCE_GATE Linuxheadroom below1GiB')
      if stopped():raise InterruptedError('Posthoc STOP requested')
      if time.monotonic()-started>600:raise TimeoutError('File-only validation exceeded600s')
      step('Saved-output validation only; checking existing raw features/AA/memberships; no prediction rerun',worker_pid=child.pid,worker_creation_identity=identity,group_rss_bytes=rss,linux_available_bytes=mem,elapsed_seconds=time.monotonic()-started);time.sleep(.2)
     if child.returncode!=0:raise RuntimeError('File-only validator exit'+str(child.returncode))
     remaining=rows(child.pid)
     if remaining:raise RuntimeError('Unexpected validator descendants remain')
     target=v.read(E/'validation.json')
     if target.get('status')!='PRESERVED_04R1_FEATURES_AND_MEMBERSHIP_V002_PASS_PENDING_CLOSURE':raise RuntimeError('Validator target did not PASS')
   except BaseException:
    # Close the only child group BEFORE the runtime context attempts unmount.
    remaining=close_child(child)
    raise
 except BaseException as ex:error=repr(ex)
 finally:
  if child is not None:remaining=close_child(child)
  closed=child is not None and not remaining
  execution={'status':'FILE_ONLY_VALIDATION_PASS_PENDING_NATIVE_IMAGE_PROOF' if error is None and closed and target else 'FILE_ONLY_VALIDATION_FAILED_OR_UNPROVEN','ended_utc':image.utc(),'error':error,'target_identity':identity,'target_exit_code':child.returncode if child else None,'owned_group_empty':closed,'remaining_owned_processes':remaining,'sampled_peak_summed_RSS_bytes':peak,'sampled_min_Linux_available_bytes':minmem if minmem!=2**63 else None,'elapsed_validation_seconds':time.monotonic()-started if started else None,'validation_path':str(E/'validation.json'),'target':target,'no_prediction_rerun':True,'genomes_FAA_or_models_generated':0,'private_IPC_alias_needed_or_created':False,'outer5664_exit_code':'UNKNOWN_NOT_CAPTURED'}
  v.save(E/'inside_execution.json',execution);lock.close()
 return 0 if execution['status']=='FILE_ONLY_VALIDATION_PASS_PENDING_NATIVE_IMAGE_PROOF' else 2
if __name__=='__main__':raise SystemExit(main())
