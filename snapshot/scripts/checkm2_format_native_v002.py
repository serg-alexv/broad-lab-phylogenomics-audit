"""Held one-shot native format controller. Never claims its own future exit."""
from pathlib import Path
import argparse,ctypes,datetime,json,msvcrt,os,subprocess,sys,time,uuid
import checkm2_private_install_controller as base
import checkm2_format_common_v002 as c
R=c.R;TOKEN=uuid.uuid4().hex;STEP=R/'state/checkm2_protein_format_invariance_v002_step.json'
START=base.utc();COMMAND=subprocess.list2cmdline([sys.executable,*sys.orig_argv[1:]])
def progress(status,detail,done=0,**extra):
 row={'status':status,'detail':detail,'done':done,'total':1,'unit':'DNA-wrap61 format controls','updated_utc':base.utc(),'started_utc':START,'ended_utc':None,'pid':base.OWNER['pid'],'creation_time_utc':base.OWNER['creation_time_utc'],'full_command_line':COMMAND,'windows_launch_token':TOKEN,'operation':'FORMAT_CONTROL','diagnostic_only':True,'production_panel_acceptance':False,'benchmark_status':'NOT_RUN','log_path':str(c.E/'namespace_stderr.txt'),**extra}
 if row.get('pid') is None:row.pop('pid',None);row.pop('creation_time_utc',None);row.pop('full_command_line',None)
 c.v.save(c.STATE,row)
 c.v.save(R/'state/stages/04.json',{'id':'04','name':'Independent biological QC',**row})
def identity(child):
 created,ended,kernel,user=base.FILETIME(),base.FILETIME(),base.FILETIME(),base.FILETIME()
 if not base.K.GetProcessTimes(int(child._handle),ctypes.byref(created),ctypes.byref(ended),ctypes.byref(kernel),ctypes.byref(user)):raise ctypes.WinError(ctypes.get_last_error())
 ticks=(created.high<<32)|created.low;seconds,rem=divmod(ticks,10000000);born=datetime.datetime(1601,1,1,tzinfo=datetime.timezone.utc)+datetime.timedelta(seconds=seconds)
 return {'pid':child.pid,'creation_time_utc':born.strftime('%Y-%m-%dT%H:%M:%S')+f'.{rem:07d}Z','windows_creation_filetime_100ns':ticks}
def linux(path):return base.L+'/'+c.path(path).relative_to(R).as_posix()
def file_state(path):return {'exists':path.exists(),'sha256':c.v.sha(path) if path.exists() else None}
def group_receipts_closed(run):
 commands={p.parent for p in run.glob('unit*/command.json')};receipts={p.parent:p for p in run.glob('unit*/execution.json')}
 return bool(commands) and commands==set(receipts) and all(c.v.read(p).get('owned_group_empty') is True for p in receipts.values())
def main(a):
 if os.name!='nt' or os.environ.get('COMPUTERNAME','').upper()!='WD' or not Path(sys.argv[0]).is_absolute():raise RuntimeError('Absolute WD native controller invocation required')
 plan,baseline,admitted=c.plan_gate(a.input_plan,a.input_plan_sha256);base.gate()
 native=(R/'state/checkm2_pilot_launcher.lock').open('r+b');native.seek(0);msvcrt.locking(native.fileno(),msvcrt.LK_NBLCK,1)
 install=(R/'state/checkm2_install.lock').open('r+b');install.seek(0);msvcrt.locking(install.fileno(),msvcrt.LK_NBLCK,1)
 c.E.mkdir(parents=True,exist_ok=True)
 with (c.E/'native_once_claim.json').open('x') as f:json.dump({'at_utc':base.utc(),'native_owner':base.OWNER,'token':TOKEN,'input_plan_sha256':a.input_plan_sha256,'protocol_admission_sha256':c.v.sha(c.ADMISSION)},f);f.flush();os.fsync(f.fileno())
 previous=R/'state/stages/04.json'
 if previous.exists():c.v.save(c.E/'previous_stage04_registration.json',c.v.read(previous))
 registry_before=base.private.registry();bio_before=file_state(R/'state/STOP_CHECKM2_PILOT');child=None;child_id=None;code=None;closed=False;envelope=None;run=None;guest_closed=False;error=None;status='CONTROL_FAILED_OR_CLOSURE_UNPROVEN'
 try:
  progress('RUNNING','One DNA-wrap61 format control admitted; runtime initialization pending',0)
  launch={'native_owner':base.OWNER,'pid':base.OWNER['pid'],'creation_time_utc':base.OWNER['creation_time_utc'],'token':TOKEN,'started_utc':START,'operation':'PREDICTION','role':c.ROLE,'script':str(Path(__file__).resolve()),'input_plan_sha256':a.input_plan_sha256,'stdout':str(c.E/'namespace_stdout.txt'),'stderr':str(c.E/'namespace_stderr.txt')}
  c.v.save(c.LAUNCH,launch)
  ready=R/'state/checkm2_runtime_ready.json';ipc=R/'evidence/checkm2_runtime/ipc_capability_proof.json'
  requests=R/'state/checkm2_protein_format_invariance_v002_launch_requests';requests.mkdir(exist_ok=True)
  request={'token':TOKEN,'operation':'PREDICTION','role':c.ROLE,'input_plan_path':linux(a.input_plan),'input_plan_sha256':a.input_plan_sha256,'protocol_admission_path':linux(c.ADMISSION),'protocol_admission_sha256':c.v.sha(c.ADMISSION),'ready_receipt_path':linux(ready),'ready_receipt_sha256':c.v.sha(ready),'ipc_proof_path':linux(ipc),'ipc_proof_sha256':c.v.sha(ipc)}
  with (requests/(TOKEN+'.json')).open('x') as f:json.dump(request,f,indent=2);f.flush();os.fsync(f.fileno())
  env={**os.environ,'TREE2_CHECKM2_PILOT_LAUNCH_TOKEN':TOKEN,'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1'}
  with (c.E/'namespace_stdout.txt').open('w') as out,(c.E/'namespace_stderr.txt').open('w') as err:
   child=subprocess.Popen(['wsl','-d','Ubuntu','--','/bin/bash',base.L+'/scripts/checkm2_private_setup_ns.sh','outer','run',base.L+'/scripts/checkm2_format_v002.sh'],env=env,stdout=out,stderr=err)
   child_id=identity(child);launch['wsl_child']=child_id;c.v.save(c.LAUNCH,launch)
   deadline=time.monotonic()+2700;last=0
   while child.poll() is None:
    if time.monotonic()>deadline:raise TimeoutError('Outer format limit; current guest closure unknown, no retry')
    if time.monotonic()-last>2:
     step=c.v.read(STEP) if STEP.exists() else {}
     progress('RUNNING',step.get('detail','Read-only runtime initialization for the one DNA-wrap61 control'),min(1,int(step.get('done',0))),current_substep=step,wsl_child_identity=child_id);last=time.monotonic()
    time.sleep(.3)
   code=child.returncode;closed=True
  envelope_path=c.E/'namespace_runs'/(TOKEN+'.json');envelope=c.v.read(envelope_path)
  pending=c.OUT/'latest_pending_native.json'
  if pending.exists():
   latest=c.v.read(pending)
   if latest['input_plan_sha256']!=a.input_plan_sha256:raise RuntimeError('Different control pending pointer')
   run=c.path(latest['run_directory']);c.verify_manifest(run,c.v.read(c.path(latest['manifest_path'])));guest_closed=group_receipts_closed(run)
  if code!=0 or envelope.get('status')!='NAMESPACE_CLOSED_AND_VERIFIED' or envelope.get('helper_exit_code')!=0 or envelope.get('image_unchanged') is not True or not guest_closed:raise RuntimeError('Control target/groups/runtime did not close successfully')
  c.plan_gate(a.input_plan,a.input_plan_sha256)
  status='CONTROL_OUTPUTS_NAMESPACE_CLOSED_PENDING_OBSERVED_OWNER_EXIT_COMPARISON'
 except BaseException as ex:
  error=repr(ex)
  if child is not None and child.poll() is not None:code=child.returncode;closed=True
 finally:
  try:
   registry_after=base.private.registry();bio_after=file_state(R/'state/STOP_CHECKM2_PILOT')
   if registry_before!=registry_after or bio_before!=bio_after:status='CONTROL_FAILED_OR_CLOSURE_UNPROVEN';error='Host registry or biological STOP changed'
   receipt={'status':status,'started_utc':START,'ended_utc':base.utc(),'native_owner':base.OWNER,'wsl_child_identity':child_id,'wsl_child_closed_observed':closed,'wsl_child_exit_code':code,'native_owner_exit_code':'NOT_YET_OBSERVABLE_BY_SELF','error':error,'namespace_envelope':envelope,'all_started_unit_groups_closed':guest_closed,'run_directory':str(run) if run else None,'input_plan_sha256':a.input_plan_sha256,'protocol_admission_sha256':c.v.sha(c.ADMISSION),'host_registry_unchanged':registry_before==registry_after,'biological_STOP_unchanged':bio_before==bio_after,'format_comparison':'HELD_UNTIL_EXTERNAL_ACTUAL_NATIVE_EXIT_AND_COMMON_LEASE_PROOF','production_panel_acceptance':False}
   c.v.save(c.E/'execution_pending_owner_exit.json',receipt)
   if status.startswith('CONTROL_OUTPUTS_NAMESPACE_CLOSED'):
    progress('PENDING_NATIVE_EXIT_AND_COMPARISON','Format-control outputs and namespace closed; actual owner exit, released leases and comparison still pending; benchmark not run',1,diagnostic_completion='CORE_OUTPUTS_ONLY_PENDING_COMPARISON',pid=None,creation_time_utc=None)
   else:progress('FAILED','Format control failed or closure unproven; original baseline remains preserved; no retry',0,pid=None,creation_time_utc=None)
  finally:install.close();native.close()
 print(json.dumps({'status':status,'native_owner':base.OWNER,'actual_owner_exit_requires_external_observation':True}),flush=True)
 return 0 if status.startswith('CONTROL_OUTPUTS_NAMESPACE_CLOSED') else 2
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input-plan',required=True);p.add_argument('--input-plan-sha256',required=True);a=p.parse_args();raise SystemExit(main(a))
