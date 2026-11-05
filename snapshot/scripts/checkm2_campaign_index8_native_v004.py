"""Plan-configured serial campaign native owner; never claims its own future exit."""
from pathlib import Path
import argparse,ctypes,datetime,json,msvcrt,os,subprocess,sys,time,uuid
from contextlib import contextmanager
COLD_STARTED_MONOTONIC=time.monotonic()
import checkm2_private_install_controller as base
import checkm2_campaign_index8_common_v003 as c
c.configure_argv()
from checkm2_optional_telemetry_v001 import read_optional_telemetry, structured_exception
from checkm2_optional_progress_S1R2 import safe_call
import checkm2_owned_cleanup_T1 as ownership
R=c.R;TOKEN=uuid.uuid4().hex;STEP=c.STEP
TELEMETRY_CACHE={};TELEMETRY_ERRORS={'count':0};COMMITTED_DONE=0;TELEMETRY_UNAVAILABLE=False;TELEMETRY_BAD_FIELDS=[]
DISPLAY_WRITE_ERRORS={'count':0};DISPLAY_WRITE_UNAVAILABLE=False
START=base.utc();COMMAND=subprocess.list2cmdline([sys.executable,*sys.orig_argv[1:]])
def committed_done(value=None):
 global COMMITTED_DONE
 if type(value) is int and 0<=value<=c.COUNT:COMMITTED_DONE=max(COMMITTED_DONE,value)
 return COMMITTED_DONE

def require_core_result(result):
 if (result.get('status')!='P20_CORE_PENDING_NAMESPACE_NATIVE_CLOSURE'
  or type(result.get('completed_qc_rows')) is not int or result['completed_qc_rows']!=c.COUNT
  or not isinstance(result.get('rows'),list) or len(result['rows'])!=c.COUNT):
  raise RuntimeError('Required campaign result does not prove the exact admitted row count')
 return c.COUNT

def record_display_error(detail):
 DISPLAY_WRITE_ERRORS['count']+=1;DISPLAY_WRITE_ERRORS.setdefault('first',detail);DISPLAY_WRITE_ERRORS['last']=detail
 if DISPLAY_WRITE_ERRORS['count']<=16:
  try:sys.stderr.write(json.dumps({'optional_native_display_write_error':detail})+'\n');sys.stderr.flush()
  except OSError:pass

def progress(status,detail,done=None,**extra):
 global DISPLAY_WRITE_UNAVAILABLE
 if (TELEMETRY_UNAVAILABLE or DISPLAY_WRITE_UNAVAILABLE) and status=='RUNNING' and not str(detail).startswith('Optional progress stale/unavailable;'):detail='Optional progress stale/unavailable; actual handle supervision continues. Last operation: '+str(detail)
 row={'status':status,'detail':detail,'done':committed_done(done),'total':c.COUNT,'unit':'campaign own-row QC method estimates','updated_utc':base.utc(),'started_utc':START,'ended_utc':None,'pid':base.OWNER['pid'],'creation_time_utc':base.OWNER['creation_time_utc'],'full_command_line':COMMAND,'windows_launch_token':TOKEN,'operation':c.ROLE,'diagnostic_only':False,'production_panel_acceptance':False,'QC_series_status':'NOT_ACCEPTED','log_path':str(c.E/'namespace_stderr.txt'),'optional_telemetry_stale_or_unavailable':TELEMETRY_UNAVAILABLE,'optional_malformed_fields':TELEMETRY_BAD_FIELDS,**extra}
 if row.get('pid') is None:row.pop('pid',None);row.pop('creation_time_utc',None);row.pop('full_command_line',None)
 row.update(optional_display_write_errors=DISPLAY_WRITE_ERRORS,optional_display_write_unavailable=DISPLAY_WRITE_UNAVAILABLE)
 outcomes=[]
 for target,value in ((c.STATE,row),(R/'state/stages/04.json',{'id':'04','name':'Independent biological QC',**row})):
  outcomes.append(safe_call(c.save,target,value,error_sink=lambda d:record_display_error({**d,'last_operation':'optional_native_display_write','operation_path':str(target)})))
 DISPLAY_WRITE_UNAVAILABLE=any(x is not None for x in outcomes)
def optional_step():
 global TELEMETRY_CACHE,TELEMETRY_UNAVAILABLE,TELEMETRY_BAD_FIELDS
 TELEMETRY_CACHE,diagnostic=read_optional_telemetry(STEP,TOKEN,TELEMETRY_CACHE)
 TELEMETRY_CACHE=dict(TELEMETRY_CACHE);TELEMETRY_BAD_FIELDS=[]
 if 'done' in TELEMETRY_CACHE and not (type(TELEMETRY_CACHE['done']) is int and 0<=TELEMETRY_CACHE['done']<=c.COUNT):TELEMETRY_BAD_FIELDS.append('done')
 TELEMETRY_CACHE['done']=committed_done(TELEMETRY_CACHE.get('done'))
 if 'native_linux_identity' in TELEMETRY_CACHE and not isinstance(TELEMETRY_CACHE['native_linux_identity'],dict):TELEMETRY_BAD_FIELDS.append('native_linux_identity');TELEMETRY_CACHE['native_linux_identity']={}
 if 'detail' in TELEMETRY_CACHE and not isinstance(TELEMETRY_CACHE['detail'],str):TELEMETRY_BAD_FIELDS.append('detail');TELEMETRY_CACHE['detail']='Last optional operation text unavailable'
 TELEMETRY_UNAVAILABLE=diagnostic is not None or bool(TELEMETRY_BAD_FIELDS)
 if diagnostic is not None:
  TELEMETRY_ERRORS['count']+=1;TELEMETRY_ERRORS.setdefault('first',diagnostic)
  TELEMETRY_ERRORS['last']=diagnostic;TELEMETRY_ERRORS['last_utc']=base.utc()
 return TELEMETRY_CACHE

def identity(child):
 created,ended,kernel,user=base.FILETIME(),base.FILETIME(),base.FILETIME(),base.FILETIME()
 if not base.K.GetProcessTimes(int(child._handle),ctypes.byref(created),ctypes.byref(ended),ctypes.byref(kernel),ctypes.byref(user)):raise ctypes.WinError(ctypes.get_last_error())
 ticks=(created.high<<32)|created.low;seconds,rem=divmod(ticks,10000000);born=datetime.datetime(1601,1,1,tzinfo=datetime.timezone.utc)+datetime.timedelta(seconds=seconds)
 return {'pid':child.pid,'creation_time_utc':born.strftime('%Y-%m-%dT%H:%M:%S')+f'.{rem:07d}Z','windows_creation_filetime_100ns':ticks}
def linux(path):return base.L+'/'+c.path(path).relative_to(R).as_posix()
def file_state(path):return {'exists':path.exists(),'sha256':c.sha(path) if path.exists() else None}
def group_receipts_closed(run):
 return c.group_receipts_closed(run)

@contextmanager
def common_locks():
 handles=[];errors=[]
 try:
  for name in ('checkm2_pilot_launcher.lock','checkm2_install.lock'):
   handle=(R/'state'/name).open('r+b');handles.append((handle,False));handle.seek(0)
   msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1);handles[-1]=(handle,True)
  yield
 finally:
  for handle,locked in reversed(handles):
   try:
    if locked:handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
   except BaseException as error:errors.append(structured_exception(error,'required common lock release'))
   finally:handle.close()
  if errors:raise RuntimeError('Common lock release failed: '+repr(errors))

def main(a):
 if os.name!='nt' or os.environ.get('COMPUTERNAME','').upper()!='WD' or not Path(sys.argv[0]).is_absolute():raise RuntimeError('Absolute WD native controller invocation required')
 plan,baseline,admitted=c.plan_gate(a.input_plan,a.input_plan_sha256);base.gate()
 committed_done(0)  # New cohort count only; accepted upstream work remains excluded by the common gate.
 with common_locks():return locked_main(a,plan,baseline,admitted)

def locked_main(a,plan,baseline,admitted):
 c.E.mkdir(parents=True,exist_ok=True)
 protocol_sha=c.sha(c.ADMISSION)
 if c.read(c.ADMISSION)!=admitted:raise RuntimeError('Required admission changed after plan gate')
 claims=c.E/'native_phase_claims';claims.mkdir(exist_ok=True)
 with (claims/(protocol_sha+'.json')).open('x') as f:json.dump({'at_utc':base.utc(),'native_owner':base.OWNER,'token':TOKEN,'input_plan_sha256':a.input_plan_sha256,'protocol_admission_sha256':protocol_sha},f);f.flush();os.fsync(f.fileno())
 registry_before=base.private.registry();bio_before=file_state(R/'state/STOP_CHECKM2_PILOT');child=None;child_id=None;code=None;closed=False;envelope=None;run=None;guest_closed=False;error=None;fatal_cleanup=None;handoff=None;status='P20_FAILED_OR_CLOSURE_UNPROVEN'
 try:
  progress('RUNNING',f'Root-admitted serial campaign: {c.COUNT} inputs with own annotation/search/resume/feature commits; runtime initialization pending',0)
  launch={'native_owner':base.OWNER,'pid':base.OWNER['pid'],'creation_time_utc':base.OWNER['creation_time_utc'],'token':TOKEN,'started_utc':START,'operation':'PREDICTION','role':c.ROLE,'script':str(Path(__file__).resolve()),'input_plan_sha256':a.input_plan_sha256,'protocol_admission_sha256':protocol_sha,'phase':admitted['phase'],'stdout':str(c.E/'namespace_stdout.txt'),'stderr':str(c.E/'namespace_stderr.txt')}
  c.save(c.LAUNCH,launch)
  if time.monotonic()-COLD_STARTED_MONOTONIC>600:
   raise TimeoutError('P20 native before-helper preflight exceeded600s; inference not started')
  ready=R/'state/checkm2_runtime_ready.json';ipc=R/'evidence/checkm2_runtime/ipc_capability_proof.json'
  requests=c.E/'launch_requests';requests.mkdir(exist_ok=True)
  request={'token':TOKEN,'operation':'PREDICTION','role':c.ROLE,'input_plan_path':linux(a.input_plan),'input_plan_sha256':a.input_plan_sha256,'protocol_admission_path':linux(c.ADMISSION),'protocol_admission_sha256':protocol_sha,'ready_receipt_path':linux(ready),'ready_receipt_sha256':c.sha(ready),'ipc_proof_path':linux(ipc),'ipc_proof_sha256':c.sha(ipc)}
  request.update(cold_session_seconds=c.LIMITS['cold_session_seconds'], helper_max_seconds=c.LIMITS['cold_session_seconds']-1240,
   prehelper_preflight_max_seconds=600, post_unmount_hash_max_seconds=600,
   fatal_cleanup_seconds=40,
   cold_wall_deadline_unix=time.time()+max(0,c.LIMITS['cold_session_seconds']-(time.monotonic()-COLD_STARTED_MONOTONIC)))
  with (requests/(TOKEN+'.json')).open('x') as f:json.dump(request,f,indent=2);f.flush();os.fsync(f.fileno())
  env={**os.environ,'TREE2_CHECKM2_PILOT_LAUNCH_TOKEN':TOKEN,'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1'}
  with (c.E/'namespace_stdout.txt').open('w') as out,(c.E/'namespace_stderr.txt').open('w') as err:
   child=subprocess.Popen(['wsl','-d','Ubuntu','--','/usr/bin/env','TREE2_CHECKM2_PILOT_LAUNCH_TOKEN='+TOKEN,'TREE2_QC_BATCH_PLAN='+linux(a.input_plan),'TREE2_QC_BATCH_PLAN_SHA256='+a.input_plan_sha256,'/bin/bash',base.L+'/scripts/checkm2_private_setup_ns.sh','outer','run',base.L+'/scripts/checkm2_campaign_index8_shell_v004.sh','--input-plan',linux(a.input_plan),'--input-plan-sha256',a.input_plan_sha256],env=env,stdout=out,stderr=err)
   child_id=identity(child);launch['wsl_child']=child_id;c.save(c.LAUNCH,launch)
   deadline=COLD_STARTED_MONOTONIC+c.LIMITS['cold_session_seconds']-40;last=0
   while child.poll() is None:
    if time.monotonic()>deadline:raise TimeoutError('P20 cold wall deadline; bounded ownership cleanup follows')
    if time.monotonic()-last>30:
     step=optional_step()
     progress('RUNNING',step.get('detail','Read-only runtime initialization for the admitted serial campaign'),step.get('done'),current_substep=step,wsl_child_identity=child_id,optional_telemetry_errors=TELEMETRY_ERRORS);last=time.monotonic()
    time.sleep(.3)
   code=child.returncode;closed=True
  envelope_path=c.E/'namespace_runs'/(TOKEN+'.json');envelope=c.read(envelope_path)
  terminal_inner=envelope.get('inner_progress')
  if isinstance(terminal_inner,dict):committed_done(terminal_inner.get('done'))
  pending=c.OUT/'latest_pending_native.json'
  if code==0:
   if not pending.exists():raise RuntimeError('Successful P20 phase has no required current pending pointer')
   latest=c.read(pending)
   if not c.pending_is_current(latest,TOKEN,a.input_plan_sha256,launch['protocol_admission_sha256'],envelope_path):raise RuntimeError('Current P20 launch/protocol/namespace pointer absent or stale')
   run=c.path(latest['run_directory']);manifest_path=c.path(latest['manifest_path'])
   if c.sha(manifest_path)!=latest['manifest_sha256']:raise RuntimeError('Required P20 manifest SHA differs')
   c.verify_manifest(run,c.read(manifest_path));guest_closed=group_receipts_closed(run)
   required_result=c.read(run/'result.json')
   committed_done(require_core_result(required_result))
  else:
   # Optional progress is only a locator; common verifies required run evidence.
   run=c.current_failed_run(optional_step(),TOKEN,a.input_plan_sha256,launch['protocol_admission_sha256'])
   if run is not None:guest_closed=group_receipts_closed(run)
  if code!=0 or envelope.get('status')!='NAMESPACE_CLOSED_AND_VERIFIED' or envelope.get('helper_exit_code')!=0 or envelope.get('image_unchanged') is not True or not guest_closed:raise RuntimeError('P20 target/groups/runtime did not close successfully')
  c.plan_gate(a.input_plan,a.input_plan_sha256,closed_finalization=True)
  if c.sha(c.ADMISSION)!=launch['protocol_admission_sha256']:raise RuntimeError('P20 phase Ready changed during owned execution')
  status='P20_OUTPUTS_CLOSED_PENDING_OBSERVED_OWNER_EXIT_REVIEW'
 except BaseException as ex:
  error=structured_exception(ex,'native P20 supervision; strict evidence or progress publication')
  optional_step()
  if child is not None:
   cleanup_started=time.monotonic();stop=None;cleanup_errors=[]
   if child.poll() is None:
    try:stop=ownership.scoped_stop(c.STOP,TOKEN,'FATAL_NATIVE_P20_SUPERVISOR_ERROR')
    except BaseException as stop_error:cleanup_errors.append(structured_exception(stop_error,c.STOP))
    while child.poll() is None and time.monotonic()-cleanup_started<40:
     try:progress('RUNNING','Owned native failure: waiting for scoped guest cleanup; no retry',0,wsl_child_identity=child_id)
     except BaseException as progress_error:cleanup_errors.append(structured_exception(progress_error,'cleanup progress publication'))
     time.sleep(.2)
   if child.poll() is not None:code=child.wait();closed=True
   fatal_cleanup={'elapsed_seconds':time.monotonic()-cleanup_started,'scoped_STOP':stop,
    'actual_wsl_handle_reaped':closed,'actual_wsl_exit_code':code if closed else None,
    'actual_wsl_identity':child_id,'errors':cleanup_errors,'guest_cleanup_not_inferred_from_WSL_exit':True}
   if not closed:
    status='FAILED_OWNED_WORK_UNKNOWN_CLOSURE'
    try:handoff=ownership.immutable_handoff(c.E,c.UNRESOLVED_HANDOFF,TOKEN,'native_WSL',
     {'native_owner':base.OWNER,'wsl_child_identity':child_id,'actual_wsl_poll':child.poll(),
      'cleanup':fatal_cleanup,'original_exception':error,'guest_closure':'UNKNOWN'})
    except BaseException as handoff_error:handoff={'write_failed':structured_exception(handoff_error,c.UNRESOLVED_HANDOFF)}
   else:
    status='FAILED_OWNED_WORK'
    # This is required evidence, not optional progress and not a WSL-exit inference.
    envelope_path=c.E/'namespace_runs'/(TOKEN+'.json')
    try:
     if envelope_path.exists():envelope=c.read(envelope_path)
    except BaseException as evidence_error:cleanup_errors.append(structured_exception(evidence_error,envelope_path))
    no_guest_started=isinstance(envelope,dict) and envelope.get('helper_started') is False
    normal_closed=(isinstance(envelope,dict) and envelope.get('status')=='NAMESPACE_CLOSED_AND_VERIFIED'
     and envelope.get('image_unchanged') is True and guest_closed)
    fatal_closed=(isinstance(envelope,dict) and envelope.get('status')=='FAILED_OWNED_WORK_CLOSED_NOT_ACCEPTED'
     and envelope.get('cleanup',{}).get('closure_proven') is True
     and envelope.get('ordinary_closure_evidence',{}).get('verified') is True)
    if not (no_guest_started or normal_closed or fatal_closed):
     status='FAILED_OWNED_WORK_UNKNOWN_CLOSURE'
     try:handoff=ownership.immutable_handoff(c.E,c.UNRESOLVED_HANDOFF,TOKEN,'native_guest_closure',
      {'native_owner':base.OWNER,'wsl_child_identity':child_id,'actual_wsl_exit_code':code,
       'cleanup':fatal_cleanup,'original_exception':error,'namespace_envelope':envelope,
       'guest_closure':'UNKNOWN_NOT_INFERRED_FROM_WSL_EXIT'})
     except BaseException as handoff_error:handoff={'write_failed':structured_exception(handoff_error,c.UNRESOLVED_HANDOFF)}
 finally:
  try:
   try:registry_after=base.private.registry();bio_after=file_state(R/'state/STOP_CHECKM2_PILOT')
   except BaseException as audit_error:
    registry_after=None;bio_after=None;status='FAILED_OWNED_WORK_UNKNOWN_CLOSURE'
    error={'original_exception':error,'required_final_audit_error':structured_exception(audit_error,'required registry/biological STOP audit')}
   if registry_before!=registry_after or bio_before!=bio_after:
    status='FAILED_OWNED_WORK_UNKNOWN_CLOSURE' if child is not None else 'FAILED_PRECHECK'
    error={'message':'Host registry or biological STOP changed','original_exception':error}
   receipt={'status':status,'started_utc':START,'ended_utc':base.utc(),'native_owner':base.OWNER,'wsl_child_identity':child_id,'wsl_child_closed_observed':closed,'wsl_child_exit_code':code,'native_owner_exit_code':'NOT_YET_OBSERVABLE_BY_SELF','error':error,'namespace_envelope':envelope,'fatal_cleanup':fatal_cleanup,'unresolved_ownership_handoff':handoff,'optional_telemetry_errors':TELEMETRY_ERRORS,'optional_display_write_errors':DISPLAY_WRITE_ERRORS,'all_started_unit_groups_closed':guest_closed,'run_directory':str(run) if run else None,'input_plan_sha256':a.input_plan_sha256,'protocol_admission_sha256':protocol_sha,'host_registry_unchanged':registry_before==registry_after,'biological_STOP_unchanged':bio_before==bio_after,'P20_review':'HELD_UNTIL_EXTERNAL_ACTUAL_NATIVE_EXIT_AND_COMMON_LEASE_PROOF','production_panel_acceptance':False}
   try:c.save(c.E/'execution_pending_owner_exit.json',receipt)
   except BaseException as terminal_error:
    status='FAILED_OWNED_WORK_UNKNOWN_CLOSURE';secondary=structured_exception(terminal_error,c.E/'execution_pending_owner_exit.json')
    fallback={**receipt,'status':status,'original_error':error,'required_terminal_write_error':secondary,'no_relaunch':True}
    try:ownership.immutable_handoff(c.E,c.UNRESOLVED_HANDOFF,TOKEN,'required_terminal_write',fallback)
    except BaseException as fallback_error:
     try:sys.stderr.write(json.dumps({**fallback,'secondary_handoff_write_error':structured_exception(fallback_error,c.UNRESOLVED_HANDOFF)})+'\n');sys.stderr.flush()
     except OSError:pass
   if status.startswith('P20_OUTPUTS_CLOSED'):
    progress('PENDING_NATIVE_EXIT_AND_COMPARISON','P20 outputs closed; external actual owner exit and released leases/root review pending',committed_done(),diagnostic_completion='CORE_OUTPUTS_ONLY_PENDING_COMPARISON',pid=None,creation_time_utc=None)
   else:progress('FAILED_OWNED_WORK_UNKNOWN_CLOSURE' if status=='FAILED_OWNED_WORK_UNKNOWN_CLOSURE' else 'FAILED','Campaign stopped; exact ownership/closure evidence held; no automatic retry',0,pid=None,creation_time_utc=None)
  finally:pass  # common_locks closes all descriptors even if a pre-dispatch required write fails.
 try:print(json.dumps({'status':status,'native_owner':base.OWNER,'actual_owner_exit_requires_external_observation':True}),flush=True)
 except OSError:pass
 return 0 if status.startswith('P20_OUTPUTS_CLOSED') else 2
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input-plan',required=True);p.add_argument('--input-plan-sha256',required=True);a=p.parse_args();raise SystemExit(main(a))
