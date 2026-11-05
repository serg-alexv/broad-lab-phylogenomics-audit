"""Held official-protein resource pilot. Requires separate root strategy admission."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import argparse,datetime,fcntl,importlib.util,json,os,shutil,signal,subprocess,time
import checkm2_protein_helpers_v001 as h
R=h.R;OUT=R/'analysis/checkm2_protein_pilot_v001';STATE=R/'state/checkm2_protein_pilot_v001_progress.json';LAUNCH=None
_legacy_source=R/'scripts/checkm2_pilot.py'
if h.sha(_legacy_source)!='9adce984f8451a0e963922abfb56ada3c84b96612187ada3f1788aebef0801e1':raise RuntimeError('Accepted read-only gate dependency changed')
_spec=importlib.util.spec_from_file_location('tree2_protein_private_readonly_gates_v001',_legacy_source)
legacy=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(legacy)
legacy.STATE=STATE;legacy.OUT=OUT;legacy.LAUNCH=None
# This is an isolated instance of our byte-pinned wrapper, not author code.
# Its readiness log adapter cannot write legacy FNA progress or initialize it.
legacy.progress=lambda status,detail,done=0,**extra:progress(status,detail,done,**extra)
STRATEGY=R/'state/checkm2_protein_strategy_ready_v001.json'
LIMIT=2*1024**3;HEADROOM=1024**3;SECONDS=600
class UnitFailure(RuntimeError):
 def __init__(self,receipt):self.receipt=receipt;super().__init__(str(receipt))
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def progress(status,detail,done=0,**extra):
 value={'status':status,'detail':detail,'done':done,'total':1,'unit':'supported-protein pilot genomes','updated_utc':utc(),'started_utc':LAUNCH['started_utc'] if LAUNCH else utc(),'production_acceptance':'NOT_GRANTED','genome_quality_status':'NOT_ACCEPTED','biological_absence_inference':'NONE','completeness':None,'contamination':None,**extra}
 if LAUNCH:value.update(pid=LAUNCH['pid'],creation_time_utc=LAUNCH['creation_time_utc'],windows_launch_token=LAUNCH['token'],native_linux_identity=legacy.stat(os.getpid()))
 h.save(STATE,value)
def static_input():return h.read(R/'analysis/checkm2_pilot/pilot_plan.json')['input']
def held_plan():
 return {'status':'PREPARED_HELD_NOT_RUN','role':'OFFICIAL_PROTEIN_RESOURCE_PILOT_V001','input':static_input(),'strategy_admission_required':str(STRATEGY),'biological_stop':'state/STOP_CHECKM2_PILOT','units':{'original_sequential_annotation':SECONDS,'protein_quality_and_feature_validation':SECONDS},'limits':{'cpu_affinity_max':2,'summed_group_rss_bytes':LIMIT,'linux_headroom_bytes':HEADROOM,'volume_reserve_bytes':40*1024**3},'no_stock_resume':True,'supported_flags':['--genes','--extension','faa','--threads','1','--lowmem','--dbg_vectors'],'source_only_prepare_opens_no_genome':True}
def strategy_gate():
 if not STRATEGY.exists():raise RuntimeError('HELD_STRATEGY_ADMISSION_ABSENT; no biology started')
 strategy=h.read(STRATEGY)
 if strategy.get('schema')!='TREE2_SUPPORTED_PROTEIN_STRATEGY_V1' or strategy.get('status')!='ROOT_ACCEPTED_FOR_ONE_RESOURCE_PILOT' or strategy.get('biological_dispatch_authorized') is not True:raise RuntimeError('HELD_STRATEGY_NOT_ACCEPTED')
 if strategy.get('limits')!={'cpu_affinity_max':2,'summed_group_rss_bytes':LIMIT,'linux_headroom_bytes':HEADROOM,'volume_reserve_bytes':40*1024**3,'seconds_per_declared_unit':SECONDS}:raise RuntimeError('Strategy limits differ from04R1')
 item=static_input()
 if strategy.get('input_binding_sha256')!=h.canonical(item):raise RuntimeError('Strategy input differs')
 for name in ('engineering_execution','engineering_native_closure','engineering_linux_closure','feature_schema','owned_resource_hold_transition'):
  row=strategy[name];path=h.inside(row['path'])
  if h.sha(path)!=row['sha256']:raise RuntimeError('Strategy artifact changed:'+name)
 transition=h.read(h.inside(strategy['owned_resource_hold_transition']['path']))
 if transition.get('authorized_by_decision')!='04R1' or transition.get('removed_marker_sha256')!='352c2cacb99a5ba33cd8e35da845a5a32c6404eb137ae0558ac112477e69db16' or transition.get('removed_owner_token')!='583d75993ca445fca988f7c7264e15e8' or transition.get('old_marker_removed') is not True:raise RuntimeError('Exact owned resource-hold transition not admitted')
 engineering=h.read(h.inside(strategy['engineering_execution']['path']));native=h.read(h.inside(strategy['engineering_native_closure']['path']));linux=h.read(h.inside(strategy['engineering_linux_closure']['path']))
 comparison=next((x for x in engineering.get('inside_result',{}).get('arms',[]) if x.get('arm')=='protein_topology'),{})
 if engineering.get('status')!='ENGINEERING_DIAGNOSTIC_RECORDED_NOT_QC' or engineering.get('linux_lifecycle_closure')!='PROVEN' or engineering.get('wsl_child_closed_observed') is not True or engineering.get('biological_stop_unchanged') is not True:raise RuntimeError('Engineering lifecycle not proved')
 if comparison.get('status')!='ALL_DECLARED_ENGINEERING_STEPS_RECORDED' or comparison.get('owned_group_empty') is not True or comparison.get('peak_summed_rss_bytes',LIMIT+1)>LIMIT or comparison.get('minimum_linux_available_bytes',0)<HEADROOM:raise RuntimeError('Chosen smaller-topology evidence not admitted')
 if native.get('status')!='MEMORY_DIAGNOSTIC_NATIVE_EXIT0_IDENTITIES_LOCKS_CLOSED' or native.get('actual_native_exit_code')!=0 or native.get('actual_wsl_exit_code')!=0 or native.get('protocol_execution_sha256')!=strategy['engineering_execution']['sha256'] or native.get('linux_closure_sha256')!=strategy['engineering_linux_closure']['sha256']:raise RuntimeError('Engineering native closure binding invalid')
 if not native.get('tracked_native_originals_absent') or not all(native['tracked_native_originals_absent'].values()) or not {'checkm2_pilot_launcher.lock','checkm2_install.lock'}.issubset(native.get('native_locks_reacquired_and_released',{})) or not all(native['native_locks_reacquired_and_released'].values()):raise RuntimeError('Native original/lock proof incomplete')
 if linux.get('status')!='MEMORY_DIAGNOSTIC_LINUX_IDENTITIES_AND_LOCK_CLOSED' or linux.get('compute_lock_reacquired_and_released') is not True or linux.get('remaining_image_loop_associations')!=[]:raise RuntimeError('Engineering Linux closure invalid')
 if strategy['feature_schema']['sha256']!='2be7bda6589a445a8b70023d9cf84ffadc76a380db112b34a70ce0094fc53adb' or strategy.get('original_prodigal_source_sha256')!='4d962b423281b81edf3e9eec7ce3219388a0df8ae52c13cde883419826592b6f':raise RuntimeError('Reviewed protein source/schema differs')
 required={'scripts/checkm2_protein_pilot_v001.py','scripts/checkm2_protein_helpers_v001.py','scripts/checkm2_protein_image_entry_v001.py','scripts/checkm2_protein_image_v001.sh','scripts/launch_checkm2_protein_pilot_v001.ps1','scripts/checkm2_pilot.py','scripts/checkm2_effective_gate.py','scripts/checkm2_effective_bootstrap.py','scripts/checkm2_runtime_image.py','scripts/checkm2_ipc_alias.py','scripts/checkm2_ipc_bootstrap.py','scripts/checkm2_private_setup_ns.sh'}
 sources={row['path']:row for row in strategy['sources']}
 if not required.issubset(sources):raise RuntimeError('Strategy lacks executed source pins')
 for row in sources.values():
  if h.sha(h.inside(row['path']))!=row['sha256']:raise RuntimeError('Executed source changed')
 if strategy.get('dbg_vectors_output_only_source_verified') is not True or strategy.get('monitor_adapter_ready') is not True:raise RuntimeError('Feature-flag/source or live-monitor admission pending')
 return strategy,item
def verify_input(item):
 source=legacy.inside(item['fasta_path'])
 for path,expected in [(source,item['fasta_sha256']),(R/'raw'/item['accession']/'acquisition_receipt.json',item['acquisition_receipt_sha256']),(R/'qc/source_provenance_audit.json',item['source_provenance_audit_sha256']),(R/'metadata/provisional_panel.json',item['provisional_panel_sha256'])]:
  if h.sha(path)!=expected:raise RuntimeError('Input/source snapshot changed:'+str(path))
 if source.stat().st_size!=item['fasta_bytes']:raise RuntimeError('Input size differs')
 return source
def manifest(folder,name):
 rows=[{'path':p.relative_to(folder).as_posix(),'bytes':p.stat().st_size,'sha256':h.sha(p)} for p in sorted(folder.rglob('*')) if p.is_file() and p!=folder/name]
 h.save(folder/name,{'files':rows,'all_files_closed_before_hash':True});return h.sha(folder/name)
def verify_manifest(folder,name):
 for row in h.read(folder/name)['files']:
  p=h.inside(folder/row['path'])
  if p.stat().st_size!=row['bytes'] or h.sha(p)!=row['sha256']:raise RuntimeError('Checkpoint artifact changed')
def all_unit_groups_closed(run):
 commands={p.parent for p in run.glob('unit*/command.json')};executions={p.parent:p for p in run.glob('unit*/execution.json')}
 return commands==set(executions) and all(h.read(p).get('owned_group_empty') is True for p in executions.values())
def run_unit(name,cmd,env,run,timeout=SECONDS):
 folder=run/name;folder.mkdir(exist_ok=False);started_utc=utc();started=time.monotonic();child=None;identity=None;error=None;failure_kind=None;peak=0;min_available=2**63;peak_rows=[];remaining=[]
 h.save(folder/'command.json',{'command':cmd,'environment':{k:env.get(k) for k in ('TMPDIR','TMP','TEMP','KERAS_HOME','XDG_CACHE_HOME','XDG_CONFIG_HOME','MPLCONFIGDIR','NUMBA_CACHE_DIR','GLIBC_TUNABLES','PYTHONPATH','PYTHONNOUSERSITE','PYTHONDONTWRITEBYTECODE','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','TF_NUM_INTRAOP_THREADS','TF_NUM_INTEROP_THREADS')},'HOME_unchanged':env.get('HOME')==os.environ.get('HOME'),'declared_unit':name,'timeout_seconds':timeout})
 try:
  legacy.stop_gate()
  with (folder/'stdout.txt').open('w') as out,(folder/'stderr.txt').open('w') as err:
   child=subprocess.Popen(cmd,env=env,stdout=out,stderr=err,start_new_session=True)
   try:identity=legacy.stat(child.pid)
   except FileNotFoundError:identity={'pid':child.pid,'creation_identity':'EXITED_BEFORE_PROC_OBSERVATION'}
   while child.poll() is None:
    rows=legacy.group(child.pid);rss=sum(x['rss_bytes'] for x in rows);available=legacy.mem_available();min_available=min(min_available,available)
    if rss>peak:peak=rss;peak_rows=rows
    if rss>LIMIT:raise RuntimeError('RESOURCE_GATE summed group RSS '+str(rss)+' exceeds2GiB')
    if available<HEADROOM:raise RuntimeError('RESOURCE_GATE Linux headroom below1GiB')
    if time.monotonic()-started>timeout:raise TimeoutError('Declared scientific unit deadline')
    legacy.stop_gate();progress('RUNNING',name,declared_unit=name,declared_unit_limit_seconds=timeout,worker_pid=child.pid,worker_creation_identity=identity,group_rss_bytes=rss,linux_available_bytes=available,elapsed_seconds=time.monotonic()-started,log_path=str(folder/'stderr.txt'),run_directory=str(run));time.sleep(.25)
   if child.returncode!=0:raise RuntimeError('Scientific unit exit '+str(child.returncode))
 except BaseException as ex:error=repr(ex);failure_kind='RESOURCE' if 'RESOURCE_GATE' in str(ex) else 'STOP' if isinstance(ex,InterruptedError) else 'TIMEOUT' if isinstance(ex,TimeoutError) else 'RUNTIME_OR_OBSERVER'
 finally:
  if child is not None:
   if child.poll() is None:
    try:os.killpg(child.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    try:child.wait(timeout=10)
    except subprocess.TimeoutExpired:
     try:os.killpg(child.pid,signal.SIGKILL)
     except ProcessLookupError:pass
     child.wait(timeout=5)
   remaining=legacy.group(child.pid)
   if remaining:
    if error is None:error='Direct child exited but owned descendants remained; forced cleanup forbids scientific success';failure_kind='CLOSURE'
    try:os.killpg(child.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    deadline=time.monotonic()+5
    while remaining and time.monotonic()<deadline:time.sleep(.1);remaining=legacy.group(child.pid)
  receipt={'status':'UNIT_EXIT0_GROUP_CLOSED' if error is None and child is not None and not remaining else 'UNIT_FAILED_OR_CLOSURE_UNPROVEN','declared_unit':name,'started_utc':started_utc,'ended_utc':utc(),'elapsed_seconds':time.monotonic()-started,'error':error,'failure_kind':failure_kind,'child_identity':identity if child else None,'exit_code':child.returncode if child else None,'owned_group_empty':child is not None and not remaining,'remaining_owned_processes':remaining,'sampled_peak_summed_rss_bytes':peak,'peak_per_pid_RSS_rows':peak_rows,'sampled_min_linux_available_bytes':min_available if min_available!=2**63 else None,'timeout_seconds':timeout,'budget_metric':'SUM_PROCESS_RSS','pss_substitution':False}
  h.save(folder/'execution.json',receipt)
 if receipt['status']!='UNIT_EXIT0_GROUP_CLOSED':raise UnitFailure(receipt)
 return receipt
def environment(prefix):
 env=os.environ.copy()
 for key,name in {'KERAS_HOME':'checkm2_keras','XDG_CACHE_HOME':'checkm2_private_xdg','XDG_CONFIG_HOME':'checkm2_private_config','MPLCONFIGDIR':'checkm2_mpl','NUMBA_CACHE_DIR':'checkm2_numba'}.items():
  path=R/'work'/name;path.mkdir(parents=True,exist_ok=True);env[key]=str(path)
 env.update(TMPDIR='/tmp',TMP='/tmp',TEMP='/tmp',PATH=str(prefix/'bin')+os.pathsep+env.get('PATH',''),PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',PYTHONWARNINGS='default',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2',NUMEXPR_NUM_THREADS='2',TF_NUM_INTRAOP_THREADS='2',TF_NUM_INTEROP_THREADS='1',CUDA_VISIBLE_DEVICES='-1')
 return env
def execute(run,binding,strategy):
 runtime=binding['runtime'];prefix=Path(runtime['prefix']);helper=R/'scripts/checkm2_protein_helpers_v001.py';env=environment(prefix);item=binding['input'];source=verify_input(item)
 inputdir=run/'original_input';inputdir.mkdir();staged=inputdir/(item['accession']+'.fna');shutil.copyfile(source,staged)
 if h.sha(staged)!=item['fasta_sha256']:raise RuntimeError('Staged FNA differs')
 schema=strategy['feature_schema'];annotation_plan={'input':{**item,'staged_fna':str(staged)},'runtime_prefix':str(prefix),'original_prodigal_source_sha256':strategy['original_prodigal_source_sha256'],'prodigal_program_sha256':runtime['tools']['prodigal']['sha256']};h.save(run/'annotation_plan.json',annotation_plan)
 annotation=run/'annotation';run_unit('unit01_original_annotation',[str(prefix/'bin/python'),'-B',str(helper),'annotate','--plan',str(run/'annotation_plan.json'),'--output',str(annotation)],env,run)
 annotated=h.read(annotation/'annotation_receipt.json');faa=h.inside(annotated['faa_path'])
 if annotated['status']!='ORIGINAL_SEQUENTIAL_PRODIGAL_COMPLETED_NOT_GENOME_ACCEPTANCE' or h.sha(faa)!=annotated['faa_sha256']:raise RuntimeError('Annotation checkpoint not admitted')
 annotation_manifest_sha=manifest(annotation,'manifest.json');quality_input=run/'protein_input';quality_input.mkdir();copied=quality_input/(item['accession']+'.faa');shutil.copyfile(faa,copied)
 if h.sha(copied)!=annotated['faa_sha256']:raise RuntimeError('Selected FAA changed during staging')
 quality_binding={'role':'SUPPORTED_PROTEIN_QUALITY_FROM_ORIGINAL_CALLER_V001','source_FNA_sha256':item['fasta_sha256'],'annotation_manifest_sha256':annotation_manifest_sha,'annotation_receipt_sha256':h.sha(annotation/'annotation_receipt.json'),'annotation_unit_execution_sha256':h.sha(run/'unit01_original_annotation/execution.json'),'selected_FAA_sha256':annotated['faa_sha256'],'selected_FAA_bytes':annotated['faa_bytes'],'exact_basename':copied.name,'original_caller_sha256':strategy['original_prodigal_source_sha256'],'core_model_database_binding':{'image_sha256':runtime['ready']['runtime_image']['sha256'],'models_manifest_sha256':runtime['models_manifest_sha256'],'database_sha256':runtime['database_sha256'],'effective_runtime_manifest_sha256':runtime['effective_runtime']['manifest_sha256']},'flags':{'genes':True,'extension':'faa','threads':1,'lowmem':True,'dbg_vectors':True,'mode':'auto'},'feature_schema_sha256':schema['sha256']};h.save(run/'protein_quality_binding.json',quality_binding)
 tmp=run/'durable_quality_tmp';tmp.mkdir();quality=run/'quality_output';route=runtime['ipc_routing'];env['TREE2_EFFECTIVE_ORIGIN_RECEIPT']=str(run/'effective_import_origins.json')
 cmd=[str(prefix/'bin/python'),'-B',route['bootstrap_path'],'--proof',route['proof_path'],'--proof-sha256',route['proof_sha256'],'--receipt',str(run/'target_ipc.json'),'checkm2','predict','--genes','--extension','faa','--threads','1','--lowmem','--input',str(quality_input),'--output-directory',str(quality),'--tmpdir',str(tmp),'--database_path',runtime['database_path'],'--dbg_vectors','--debug']
 quality_started=time.monotonic();quality_receipt=run_unit('unit02_protein_quality',cmd,env,run)
 row,comp,cont=h.parse_protein_report(quality/'quality_report.tsv',item['accession'])
 featureplan={'accession':item['accession'],'schema_path':str(h.inside(schema['path'])),'schema_sha256':schema['sha256'],'quality_output':str(quality),'selected_faa_path':str(copied),'selected_faa_sha256':annotated['faa_sha256']};h.save(run/'feature_validation_plan.json',featureplan)
 remaining=SECONDS-(time.monotonic()-quality_started)
 if remaining<=0:raise TimeoutError('Protein quality plus validation unit exceeded600s')
 run_unit('unit02_feature_validation',[str(prefix/'bin/python'),'-B',str(helper),'validate-features','--plan',str(run/'feature_validation_plan.json'),'--output',str(run/'feature_validation.json')],env,run,remaining)
 result={'status':'SUPPORTED_PROTEIN_RESOURCE_PILOT_CORE_PENDING_NAMESPACE_CLOSURE','accession':item['accession'],'Completeness':comp,'Contamination':cont,'raw_author_protein_report_row':row,'author_protein_report_columns':h.PROTEIN_COLUMNS,'DNA_columns_intentionally_absent_in_author_protein_report':h.DNA_COLUMNS,'separate_original_annotation_receipt':str(annotation/'annotation_receipt.json'),'annotation_receipt_sha256':h.sha(annotation/'annotation_receipt.json'),'FAA_sha256':annotated['faa_sha256'],'protein_quality_binding_sha256':h.sha(run/'protein_quality_binding.json'),'feature_validation_receipt':str(run/'feature_validation.json'),'feature_validation_sha256':h.sha(run/'feature_validation.json'),'supported_protein_route_used':True,'nucleotide_numeric_equivalence_measured':False,'stock_resume_used':False,'genome_quality_acceptance':'NOT_GRANTED','taxonomy_acceptance':'NOT_GRANTED','production_acceptance':'NOT_GRANTED','source_metadata_comparison_only':item['source_metadata_checkm'],'units_closed':True}
 h.save(run/'result.json',result);return result
def main(args):
 if not args.run and not args.mount_smoke:
  plan=held_plan();h.save(OUT/'held_plan.json',plan);print(json.dumps(plan));return
 if os.environ.get('TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED')!='1':raise RuntimeError('Private accepted runtime required before biology/preflight')
 global LAUNCH
 if not args.launch_token:raise RuntimeError('Matching native launch token required')
 launch=h.read(R/'state/launch_checkm2_protein_pilot_v001.json')
 if launch['token']!=args.launch_token:raise RuntimeError('Native launch token differs')
 LAUNCH=launch;legacy.LAUNCH=launch;strategy,item=strategy_gate();legacy.stop_gate(args.mount_smoke)
 lock=(R/'state/checkm2_pilot.lock').open('a+b');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 try:
  os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:2]));runtime=legacy.ready_gate(args.ready_receipt,require_effective=True);runtime['ipc_routing'],runtime['private_ipc_namespace']=legacy.ipc_runtime_gate(runtime);legacy.no_heavy_science()
  if args.mount_smoke:
   h.save(R/'evidence/checkm2_protein_pilot_v001/namespace_runs'/(LAUNCH['token']+'_preflight.json'),{'status':'READONLY_TOOL_PREFLIGHT_PASS_PENDING_CLOSURE','runtime':runtime,'scientific_prediction':'NOT_RUN'});progress('PREFLIGHT_DONE_PENDING_NAMESPACE_CLOSURE','Supported-protein source/runtime/strategy preflight passed; no biology');return
  legacy.stop_gate();options={'role':'OFFICIAL_PROTEIN_RESOURCE_PILOT_V001','threads':1,'genes':True,'extension':'faa','lowmem':True,'author_Diamond_block':0.5,'dbg_vectors':True,'mode':'auto','units_seconds':{'annotation':SECONDS,'protein_quality_including_validation':SECONDS},'strategy_sha256':h.sha(STRATEGY),'controller_sha256':h.sha(__file__),'helper_sha256':h.sha(R/'scripts/checkm2_protein_helpers_v001.py'),'feature_schema_sha256':strategy['feature_schema']['sha256'],'no_stock_resume':True};binding={'input':item,'runtime':runtime,'options':options};key=legacy.binding_digest(binding)
  claims=OUT/'once';claims.mkdir(parents=True,exist_ok=True)
  with (claims/(h.sha(STRATEGY)+'.json')).open('x') as f:json.dump({'strategy_sha256':h.sha(STRATEGY),'binding_sha256':key,'launch':LAUNCH,'started_utc':utc()},f);f.flush();os.fsync(f.fileno())
  run=OUT/'runs'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+key[:12]);run.mkdir(parents=True,exist_ok=False);h.save(run/'binding.json',binding);shutil.copyfile(__file__,run/'controller_source_at_execution.py');shutil.copyfile(R/'scripts/checkm2_protein_helpers_v001.py',run/'helper_source_at_execution.py')
  try:
   result=execute(run,binding,strategy);digest=manifest(run,'manifest.json');h.save(OUT/'latest.json',{'result_path':str(run/'result.json'),'manifest_path':str(run/'manifest.json'),'manifest_sha256':digest,'binding_sha256':key,'namespace_execution_receipt_path':str(R/'evidence/checkm2_protein_pilot_v001/namespace_runs'/(LAUNCH['token']+'.json'))});progress('PREDICTION_DONE_PENDING_NAMESPACE_CLOSURE','Supported protein estimate and full raw feature schema verified; no production acceptance',1,result_path=str(run/'result.json'),completeness=result['Completeness'],contamination=result['Contamination'],binding_sha256=key)
  except BaseException as ex:
   kind=ex.receipt.get('failure_kind') if isinstance(ex,UnitFailure) else None
   status='BLOCKED_RESOURCE' if kind=='RESOURCE' or 'RESOURCE_GATE' in str(ex) else 'STOPPED' if kind=='STOP' or isinstance(ex,InterruptedError) else 'INTERRUPTED_BUDGET' if kind=='TIMEOUT' or isinstance(ex,TimeoutError) else 'FAILED_RUNTIME_OR_SCHEMA';failure={'status':status,'error':repr(ex),'ended_utc':utc(),'run_directory':str(run),'binding_sha256':key,'completeness':None,'contamination':None,'production_acceptance':'NOT_GRANTED'};h.save(run/'failure_receipt.json',failure)
   closed=all_unit_groups_closed(run)
   if closed:failure['failure_manifest_sha256']=manifest(run,'failure_manifest.json')
   failure['all_started_unit_groups_closed']=closed;h.save(OUT/'last_exit.json',failure);progress(status,str(ex),run_directory=str(run),binding_sha256=key,log_path=str(run/'failure_receipt.json'));raise
 finally:lock.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--mount-smoke',action='store_true');p.add_argument('--ready-receipt',default=str(R/'state/checkm2_runtime_ready.json'));p.add_argument('--launch-token');a=p.parse_args()
 try:main(a)
 except BaseException as ex:
  if LAUNCH:
   previous=h.read(STATE) if STATE.exists() else {}
   if previous.get('windows_launch_token')!=LAUNCH['token'] or previous.get('status') not in ('BLOCKED_RESOURCE','STOPPED','INTERRUPTED_BUDGET','FAILED_RUNTIME_OR_SCHEMA'):progress('FAILED_PRECHECK',repr(ex))
  print(repr(ex),file=sys.stderr);raise SystemExit(1)
