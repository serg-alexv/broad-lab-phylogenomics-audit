"""Native lifecycle owner for the one engineering memory protocol, never QC."""
import ctypes,datetime,hashlib,json,msvcrt,os,subprocess,time
import checkm2_private_install_controller as base
R=base.R;L=base.L;E=R/'evidence/checkm2_memory_diagnostic';HANDOFF=R/'evidence/checkm2_runtime/memory_diagnostic_prior_closure_bindings.json'
HANDOFF_SHA='f3300c3fbc9caf16344ae9ec3777d906b5293a6a75b5d413743f34aa93c38f90'
def progress(detail,done=0,status='RUNNING',**extra):
 base.save(R/'state/tool_setup_progress.json',{'status':status,'done':done,'total':2,'unit':'engineering memory arms','detail':detail,'updated_utc':base.utc(),'started_utc':base.START,'pid':base.OWNER['pid'],'creation_time_utc':base.OWNER['creation_time_utc'],'log_path':str(E/'v001/inside_execution.json'),'biological_prediction':'RESOURCE_HELD','production_acceptance':False,**extra})
def unchanged_image(expected,arm_count):
 p=R/'tools/checkm2_runtime_ext4.img';digest=hashlib.sha256();count=0;started=time.monotonic();last=0
 with p.open('rb') as f:
  while block:=f.read(16*1024**2):
   digest.update(block);count+=len(block)
   if time.monotonic()-started>600 or (R/'state/STOP').exists():raise RuntimeError('Clean-image verification deadline/STOP')
   if time.monotonic()-last>3:progress(f'Engineering groups/mounts closed; unchanged-image verification {count}/{p.stat().st_size} bytes',arm_count);last=time.monotonic()
 if digest.hexdigest()!=expected:raise RuntimeError('Read-only runtime image changed')
 return digest.hexdigest()
def main():
 base.gate()
 if os.environ.get('COMPUTERNAME','').upper()!='WD':raise RuntimeError('WD-only engineering diagnostic')
 if base.sha(HANDOFF)!=HANDOFF_SHA:raise RuntimeError('Independent prior closure handoff changed')
 handoff=base.read(HANDOFF)
 if handoff['status']!='PRIOR_RESOURCE_ATTEMPT_CLOSED_ENGINEERING_HANDOFF_ONLY' or not all(handoff[k] for k in ('prior_native_original_absent','prior_scientific_group_empty','native_locks_reacquired_released','linux_compute_lock_reacquired_released')):raise RuntimeError('Prior lifecycle closure not admitted')
 if base.sha(R/handoff['closure_path'])!=handoff['closure_sha256'] or base.sha(R/handoff['bio_stop_path'])!=handoff['bio_stop_sha256']:raise RuntimeError('Prior closure/biological STOP changed')
 for path,key in [('evidence/checkm2_runtime/ipc_capability_proof.json','ipc_capability_proof_sha256'),('evidence/checkm2_runtime/sklearn161_effective_runtime_validated.json','effective_runtime_manifest_sha256'),('scripts/checkm2_ipc_alias.py','ipc_helper_sha256'),('scripts/checkm2_ipc_bootstrap.py','ipc_target_bootstrap_sha256'),('scripts/checkm2_effective_bootstrap.py','effective_bootstrap_sha256'),('scripts/checkm2_pilot.py','controller_source_sha256')]:
  if base.sha(R/path)!=handoff[key]:raise RuntimeError('Prior runtime/source pin differs:'+path)
 native=(R/'state/checkm2_pilot_launcher.lock').open('a+b');native.seek(0);msvcrt.locking(native.fileno(),msvcrt.LK_NBLCK,1)
 setup=(R/'state/checkm2_install.lock').open('a+b');setup.seek(0);msvcrt.locking(setup.fileno(),msvcrt.LK_NBLCK,1)
 E.mkdir(exist_ok=True)
 with (E/'native_once_claim.json').open('x') as f:json.dump({'at_utc':base.utc(),'owner':base.OWNER,'handoff_sha256':HANDOFF_SHA,'primary':'nine_managers_default_fork','comparison':'one_manager_two_stdlib_hold_children_default_fork','genomes_authorized':0},f);f.flush();os.fsync(f.fileno())
 before=base.private.registry();started=base.utc();inside=None;status='ENGINEERING_DIAGNOSTIC_ERROR';error=None;childcode=None;child=None;imagehash=None;wsl_identity=None;wsl_closed=False;linux_closure_proven=False
 base.save(R/'state/launch_tool_setup.json',{**base.OWNER,'script':'scripts/checkm2_memory_diagnostic_controller.py','phase':'ENGINEERING_MEMORY_TOPOLOGY_NOT_GENOME_QC'})
 progress('Starting one bounded default-fork memory diagnostic; genome processing remains held; no user input required')
 try:
  with (R/'logs/checkm2_memory_diagnostic.stdout.txt').open('w') as out,(R/'logs/checkm2_memory_diagnostic.stderr.txt').open('w') as err:
   child=subprocess.Popen(['wsl','-d','Ubuntu','--','/bin/bash',L+'/scripts/checkm2_private_setup_ns.sh','outer','run',L+'/scripts/checkm2_memory_diagnostic.sh'],stdout=out,stderr=err);deadline=time.monotonic()+2100;last=0
   wsl_identity={'pid':child.pid,'creation_time_utc':None,'creation_identity_state':'PENDING_GET_PROCESS_TIMES'}
   created,ended,kernel,user=base.FILETIME(),base.FILETIME(),base.FILETIME(),base.FILETIME()
   if not base.K.GetProcessTimes(int(child._handle),ctypes.byref(created),ctypes.byref(ended),ctypes.byref(kernel),ctypes.byref(user)):raise ctypes.WinError(ctypes.get_last_error())
   ticks=(created.high<<32)|created.low;seconds,remainder=divmod(ticks,10_000_000);born=datetime.datetime(1601,1,1,tzinfo=datetime.timezone.utc)+datetime.timedelta(seconds=seconds)
   wsl_identity={'pid':child.pid,'creation_time_utc':born.strftime('%Y-%m-%dT%H:%M:%S')+f'.{remainder:07d}Z','windows_creation_filetime_100ns':ticks}
   base.save(R/'state/launch_checkm2_memory_diagnostic.json',{'native_owner':base.OWNER,'wsl_child':wsl_identity,'script':'scripts/checkm2_memory_diagnostic.sh','biological_prediction':False,'prior_handoff_sha256':HANDOFF_SHA})
   while child.poll() is None:
    if time.monotonic()>deadline or (R/'state/STOP').exists() or (R/'state/STOP_CHECKM2_MEMORY_DIAGNOSTIC').exists():
     # The Linux supervisor normally reacts first and closes its owned group.
     if time.monotonic()>deadline:child.terminate();child.wait(timeout=20);raise RuntimeError('Outer engineering deadline; no automatic relaunch')
    if time.monotonic()-last>3:
     path=R/'state/checkm2_memory_step.json';step=base.read(path) if path.exists() else {}
     progress(step.get('detail','Verifying sealed read-only runtime before memory observation'),step.get('completed_arm_count',1 if step.get('arm')=='protein_topology' else 0),engineering_step=step);last=time.monotonic()
    time.sleep(.5)
   childcode=child.returncode;wsl_closed=True
  inside=base.read(E/'v001/inside_execution.json');runtime=base.read(E/'v001/runtime_mount_closure.json');ipc=base.read(E/'v001/ipc_mount_closure.json')
  linux_closure_proven=bool(inside.get('all_started_arm_groups_closed') and runtime.get('status')=='CLEAN_UNMOUNT_AND_LOOP_DETACH' and ipc.get('status')=='CLEAN_IPC_ALIAS_AND_BACKING_UNMOUNT')
  if not linux_closure_proven:raise RuntimeError('Engineering group/mount closure unproven; no relaunch')
  imagehash=unchanged_image(handoff['base_image_sha256'],len(inside.get('arms',[])))
  if childcode or inside['status']!='ENGINEERING_OBSERVATIONS_RECORDED_NOT_QC':raise RuntimeError('Engineering target/model/observer error; partial observations retained')
  status='ENGINEERING_DIAGNOSTIC_RECORDED_NOT_QC'
 except BaseException as ex:
  error=repr(ex)
  if child is not None and child.poll() is not None:childcode=child.returncode;wsl_closed=True
  if inside is None and (E/'v001/inside_execution.json').exists():inside=base.read(E/'v001/inside_execution.json')
 finally:
  try:
   after=base.private.registry();hold_unchanged=base.sha(R/handoff['bio_stop_path'])==handoff['bio_stop_sha256']
   if before!=after or not hold_unchanged:status='ENGINEERING_DIAGNOSTIC_ERROR';error='Host registry or biological STOP changed'
   receipt={'status':status,'started_utc':started,'ended_utc':base.utc(),'native_owner':base.OWNER,'wsl_child_identity':wsl_identity,'wsl_child_closed_observed':wsl_closed,'wsl_child_exit_code':childcode,'linux_lifecycle_closure':'PROVEN' if linux_closure_proven else 'UNKNOWN_UNPROVEN_DO_NOT_RELAUNCH','error':error,'inside_result':inside,'image_sha256_after_clean_unmount':imagehash,'host_registry_before':before,'host_registry_after':after,'host_registry_unchanged':before==after,'biological_stop_unchanged':hold_unchanged,'prior_handoff_sha256':HANDOFF_SHA,'models_or_programs_modified':False,'genomes_used':0,'prediction_scores_produced':False,'production_acceptance':False,'forkserver_executed':False,'metric_substitution':False,'controller_sha256':base.sha(__file__)}
   base.save(E/'execution.json',receipt)
   progress('Engineering memory observations closed; '+str((inside or {}).get('comparison_disposition'))+'. Resource stops are not QC passes; genomes remain held.' if status!='ENGINEERING_DIAGNOSTIC_ERROR' else error,len((inside or {}).get('arms',[])),'COMPLETE' if status!='ENGINEERING_DIAGNOSTIC_ERROR' else 'FAILED')
  finally:setup.close();native.close()
 print(json.dumps({'status':status,'native_owner':base.OWNER,'receipt':'evidence/checkm2_memory_diagnostic/execution.json','science_run':False}),flush=True)
 return 0 if status!='ENGINEERING_DIAGNOSTIC_ERROR' else 2
if __name__=='__main__':raise SystemExit(main())
