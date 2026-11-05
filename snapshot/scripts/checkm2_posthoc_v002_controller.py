"""Native owner of ONE posthoc file-only validation; no biological dispatcher."""
from pathlib import Path
import ctypes,datetime,hashlib,json,msvcrt,os,subprocess,time,uuid
import checkm2_private_install_controller as base
import checkm2_posthoc_v002_validator as v
R=base.R;L=base.L;E=R/'evidence/checkm2_posthoc_v002';A=E/'admission.json'
TOKEN=uuid.uuid4().hex
def progress(status,detail,done=0,**extra):
 row={'status':status,'detail':detail,'done':done,'total':1,'unit':'saved-output feature validations','updated_utc':base.utc(),'started_utc':base.START,'pid':base.OWNER['pid'],'creation_time_utc':base.OWNER['creation_time_utc'],'windows_launch_token':TOKEN,'scope':'FILE_ONLY_POSTHOC_V002_NO_PREDICTION_RERUN','original_attempt_namespace_token':'00af8837b20c4bd3a06966f63800007e','original_attempt_status':'FAILED_RUNTIME_OR_SCHEMA_PRESERVED','log_path':str(E/'execution.json'),'production_acceptance':'NOT_GRANTED','genome_quality_status':'NOT_PRODUCTION_ACCEPTED','completeness':None,'contamination':None,**extra}
 v.save(R/'state/checkm2_posthoc_v002_progress.json',row)
 v.save(R/'state/checkm2_protein_pilot_v001_progress.json',row)
def identity(child):
 created,ended,kernel,user=base.FILETIME(),base.FILETIME(),base.FILETIME(),base.FILETIME()
 if not base.K.GetProcessTimes(int(child._handle),ctypes.byref(created),ctypes.byref(ended),ctypes.byref(kernel),ctypes.byref(user)):raise ctypes.WinError(ctypes.get_last_error())
 ticks=(created.high<<32)|created.low;sec,rem=divmod(ticks,10_000_000);born=datetime.datetime(1601,1,1,tzinfo=datetime.timezone.utc)+datetime.timedelta(seconds=sec)
 return {'pid':child.pid,'creation_time_utc':born.strftime('%Y-%m-%dT%H:%M:%S')+f'.{rem:07d}Z','windows_creation_filetime_100ns':ticks}
def file_state(path):
 p=R/path
 return {'exists':p.exists(),'sha256':base.sha(p) if p.exists() else None}
def image_hash(expected):
 p=R/'tools/checkm2_runtime_ext4.img';digest=hashlib.sha256();count=0;started=time.monotonic();last=0
 with p.open('rb') as f:
  while block:=f.read(8*1024**2):
   if time.monotonic()-started>600 or (R/'state/STOP').exists() or (R/'state/STOP_CHECKM2_POSTHOC_V002').exists():raise RuntimeError('Closed-image verification deadline/STOP')
   digest.update(block);count+=len(block)
   if time.monotonic()-last>3:progress('RUNNING',f'Saved-output validation only; runtime closed, verifying unchanged image {count:,}/{p.stat().st_size:,} bytes; no prediction rerun');last=time.monotonic()
 if digest.hexdigest()!=expected:raise RuntimeError('Sealed image changed')
 return digest.hexdigest()
def main():
 base.gate()
 if os.environ.get('COMPUTERNAME','').upper()!='WD':raise RuntimeError('WD-only file validation')
 admission=v.read(A);v.preflight(admission)
 if admission.get('limits')!={'cpu_affinity_max':2,'summed_group_RSS_bytes':2147483648,'Linux_headroom_bytes':1073741824,'volume_reserve_bytes':42949672960,'validation_seconds':600}:raise RuntimeError('File-only limits changed')
 native=(R/'state/checkm2_pilot_launcher.lock').open('a+b');native.seek(0);msvcrt.locking(native.fileno(),msvcrt.LK_NBLCK,1)
 install=(R/'state/checkm2_install.lock').open('a+b');install.seek(0);msvcrt.locking(install.fileno(),msvcrt.LK_NBLCK,1)
 E.mkdir(exist_ok=True)
 with (E/'native_once_claim.json').open('x') as f:json.dump({'at_utc':base.utc(),'native_owner':base.OWNER,'token':TOKEN,'admission_sha256':base.sha(A),'scope':'ONE_FILE_ONLY_VALIDATION_NO_PREDICTION_RERUN'},f);f.flush();os.fsync(f.fileno())
 child=None;child_id=None;child_closed=False;code=None;inside=None;closure=None;status='POSTHOC_VALIDATION_FAILED_OR_UNPROVEN';error=None;sealed=None
 before=base.private.registry();hold_before=file_state('state/STOP_CHECKM2_PILOT');started=base.utc()
 progress('RUNNING','Saved-output validation only; checking preserved feature artifacts in pinned runtime; no prediction rerun')
 try:
  with (E/'namespace_stdout.txt').open('w') as out,(E/'namespace_stderr.txt').open('w') as err:
   child=subprocess.Popen(['wsl','-d','Ubuntu','--','/bin/bash',L+'/scripts/checkm2_private_setup_ns.sh','outer','run',L+'/scripts/checkm2_posthoc_v002.sh'],stdout=out,stderr=err)
   child_id={'pid':child.pid,'creation_identity':'UNKNOWN_PENDING_QUERY'};child_id=identity(child)
   v.save(R/'state/launch_checkm2_posthoc_v002.json',{'native_owner':base.OWNER,'wsl_child':child_id,'token':TOKEN,'script':str(R/'scripts/checkm2_posthoc_v002_controller.py'),'scope':'FILE_ONLY_NO_PREDICTION_RERUN','admission_sha256':base.sha(A)})
   deadline=time.monotonic()+1500;last=0
   while child.poll() is None:
    if time.monotonic()>deadline:raise TimeoutError('Outer posthoc limit reached; child/namespace closure unproven; no relaunch')
    if time.monotonic()-last>2:
     p=R/'state/checkm2_posthoc_v002_step.json';step=v.read(p) if p.exists() else {}
     progress('RUNNING',step.get('detail','Saved-output validation only; verifying read-only runtime; no prediction rerun'),wsl_child_identity=child_id,file_validation_step=step);last=time.monotonic()
    time.sleep(.3)
   code=child.returncode;child_closed=True
  p=E/'v001';inside=v.read(p/'inside_execution.json');closure=v.read(p/'runtime_mount_closure.json')
  if not inside.get('owned_group_empty') or closure.get('status')!='CLEAN_UNMOUNT_AND_LOOP_DETACH' or closure.get('readonly') is not True:raise RuntimeError('File validator group/image closure unproved')
  sealed=image_hash(admission['runtime_image_sha256'])
  if code!=0 or inside.get('status')!='FILE_ONLY_VALIDATION_PASS_PENDING_NATIVE_IMAGE_PROOF':raise RuntimeError('Preserved-output validation did not PASS')
  v.preflight(admission) # prove originals/source pins still unchanged after validation
  status='PRESERVED_04R1_VALIDATION_V002_PASS_CLOSED'
 except BaseException as ex:
  error=repr(ex)
  if child is not None and child.poll() is not None:code=child.returncode;child_closed=True
 finally:
  try:
   after=base.private.registry();hold_after=file_state('state/STOP_CHECKM2_PILOT')
   if before!=after or hold_before!=hold_after:status='POSTHOC_VALIDATION_FAILED_OR_UNPROVEN';error='Host registry or biological STOP changed'
   receipt={'status':status,'started_utc':started,'ended_utc':base.utc(),'native_owner':base.OWNER,'wsl_child_identity':child_id,'wsl_child_closed_observed':child_closed,'wsl_child_exit_code':code,'error':error,'inside':inside,'runtime_mount_closure':closure,'image_sha256_after_clean_unmount':sealed,'host_registry_unchanged':before==after,'biological_STOP_before':hold_before,'biological_STOP_after':hold_after,'biological_STOP_unchanged':hold_before==hold_after,'admission_sha256':base.sha(A),'source_controller_sha256':base.sha(__file__),'original_outer5664_exit_code':'UNKNOWN_NOT_CAPTURED','annotation_DIAMOND_ML_or_new_genome_FAA':False,'original_attempt_failed_status_unchanged':True,'production_acceptance':'NOT_GRANTED','format_control_acceptance':'NOT_GRANTED'}
   v.save(E/'execution.json',receipt)
   stable=bool(child_closed and isinstance(inside,dict) and inside.get('owned_group_empty') is True and isinstance(closure,dict) and closure.get('status')=='CLEAN_UNMOUNT_AND_LOOP_DETACH' and closure.get('readonly') is True)
   native_stable={'admission.json','admission_prepared.json','native_once_claim.json','execution.json','source_fixture_report.json'}
   files=[{'path':x.relative_to(E).as_posix(),'bytes':x.stat().st_size,'sha256':base.sha(x)} for x in sorted(E.rglob('*')) if x.is_file() and x!=E/'manifest.json' and (stable or x.relative_to(E).as_posix() in native_stable)]
   v.save(E/'manifest.json',{'files':files,'all_outputs_stable_after_observed_native_child_close':stable,'unproven_guest_outputs_excluded':not stable,'closure_basis':{'native_WSL_child_closed':child_closed,'owned_guest_group_empty':inside.get('owned_group_empty') if isinstance(inside,dict) else None,'ordinary_runtime_closure_status':closure.get('status') if isinstance(closure,dict) else None}})
   if status=='PRESERVED_04R1_VALIDATION_V002_PASS_CLOSED':
    result=inside['target'];pointer={'status':status,'original_failed_attempt':'analysis/checkm2_protein_pilot_v001/runs/20261027T001421Z-1ae7a083d47d','execution_path':str(E/'execution.json'),'execution_sha256':base.sha(E/'execution.json'),'manifest_path':str(E/'manifest.json'),'manifest_sha256':base.sha(E/'manifest.json'),'validation_path':str(E/'v001/validation.json'),'validation_sha256':base.sha(E/'v001/validation.json'),'Completeness':result['Completeness'],'Contamination':result['Contamination'],'no_prediction_rerun':True,'production_acceptance':'NOT_GRANTED'}
    v.save(R/'state/checkm2_posthoc_v002_latest.json',pointer)
    progress('COMPLETED','Saved-output feature validation passed and runtime closed; original computation preserved; no prediction rerun',1,completeness=result['Completeness'],contamination=result['Contamination'],validated_baseline_pointer=str(R/'state/checkm2_posthoc_v002_latest.json'))
   else:progress('FAILED','Saved-output validation failed or closure unproven; original outputs remain held; see receipt',0)
  finally:install.close();native.close()
 print(json.dumps({'status':status,'native_owner':base.OWNER,'scope':'FILE_ONLY_NO_PREDICTION_RERUN'}),flush=True)
 return 0 if status=='PRESERVED_04R1_VALIDATION_V002_PASS_CLOSED' else 2
if __name__=='__main__':raise SystemExit(main())
