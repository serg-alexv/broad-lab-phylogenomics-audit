"""HELD S1R2: preserved original row plus nine fresh targets; inference on accepted FAA only. There is no annotation dispatch path."""
from pathlib import Path
import argparse,datetime,fcntl,json,os,shutil,time
import checkm2_single_faa_common_S1R2 as c
import checkm2_unit_observer_S1R2 as observer
from checkm2_optional_progress_S1R2 import safe_call
import sys
import checkm2_protein_pilot_v001 as pilot
R=c.R;STEP=c.STEP;LAUNCH=None;COMMITTED_COUNT=1;CURRENT_RUN=None;INNER_IDENTITY=None;PROGRESS_ERRORS=[];PROGRESS_ERROR_COUNT=0

def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def raw_progress(status,detail,done=None,**extra):
 global COMMITTED_COUNT
 if type(done) is int and 1<=done<=10:COMMITTED_COUNT=max(COMMITTED_COUNT,done)
 owner={'windows_launch_token':LAUNCH['token'],'pid':LAUNCH['pid'],'creation_time_utc':LAUNCH['creation_time_utc']} if LAUNCH else {}
 if 'run_directory' in extra:extra['active_unit_directory']=extra.pop('run_directory')
 current={'run_directory':str(CURRENT_RUN)} if CURRENT_RUN else {}
 if LAUNCH:current.update(input_plan_sha256=LAUNCH['input_plan_sha256'],protocol_admission_sha256=LAUNCH['protocol_admission_sha256'])
 c.save(STEP,{'status':status,'detail':detail,'done':COMMITTED_COUNT,'total':10,'unit':'validated single-FAA QC commits','updated_utc':utc(),'operation':'SINGLE_FAA_S1R2','native_linux_identity':INNER_IDENTITY,'production_panel_acceptance':False,**owner,**current,**extra})

def note_optional(value):
 global PROGRESS_ERROR_COUNT
 PROGRESS_ERROR_COUNT+=1
 if len(PROGRESS_ERRORS)<32:PROGRESS_ERRORS.append(value)
 try:print(json.dumps({'optional_progress_io_error':value}),file=sys.stderr,flush=True)
 except OSError:pass

def progress(status,detail,done=None,**extra):
 return safe_call(raw_progress,status,detail,done,error_sink=note_optional,**extra)

pilot.OUT=c.OUT;pilot.STATE=STEP;pilot.progress=progress;pilot.legacy.STATE=STEP;pilot.legacy.OUT=c.OUT
original_stop=pilot.legacy.stop_gate

def stop(*args,**kwargs):
 c.stop()
 if LAUNCH and c.sha(c.ADMISSION)!=LAUNCH['protocol_admission_sha256']:raise InterruptedError('S1 admission changed during owned execution')
 return original_stop(*args,**kwargs)
pilot.legacy.stop_gate=stop

def invoke(name,command,env,folder,run,seconds,debit):
 if not 0<seconds<=600:raise TimeoutError('No admissible remaining S1 per-genome/shared time')
 c.save(folder/(name+'_budget.json'),{'unit':name,'debit_before_start_seconds':debit,'allowed_seconds':seconds,'shared_new_seconds':3211.205174,'per_genome_shared_seconds':600,'per_target_new_cap_seconds':c.CAPS[folder.name],'protocol_admission_sha256':c.sha(c.ADMISSION)})
 index=c.read(run/'invocations.json');index.append(str(folder/name));c.save(run/'invocations.json',index)
 return observer.run_unit(name,command,env,folder,seconds,hooks={'save':c.save,'stop_gate':stop,'stat':pilot.legacy.stat,'group':lambda pgid:observer.strict_group(pgid,pilot.legacy.stat),'mem_available':pilot.legacy.mem_available,'progress':raw_progress,'optional_error_sink':note_optional})

def binding(member,runtime,plan):
 return {'member':member,'input_plan_sha256':plan['_sha'],'session_identity_sha256':plan['session_identity_sha256'],'source_manifest_sha256':plan['source_manifest']['sha256'],'annotation_reuse_authority':c.row(c.bind(c.read(c.ADMISSION)['annotation_reuse_authority'])),'image_sha256':runtime['ready']['runtime_image']['sha256'],'effective_runtime_manifest_sha256':runtime['effective_runtime']['manifest_sha256'],'prediction_genome_count':1,'annotation_invoked':False,'preserved_row_authority':c.read(c.ADMISSION)['preserved_row_authority']}

def one(member,runtime,plan,session,run):
 acc=member['accession'];folder=session/'rows'/acc;expected=binding(member,runtime,plan)
 if acc not in c.TARGETS or acc==c.PRESERVED:raise RuntimeError('Preserved or unknown row cannot be dispatched')
 if folder.exists():raise RuntimeError('S1R2 once/partial row preserved; no automatic prediction replay')
 available=c.budget(session);left=min(c.CAPS[acc],available['remaining_seconds'])
 if left<=0:raise TimeoutError('S1 original shared budget exhausted')
 source=c.bind(member['selected_faa']);folder.mkdir(parents=True,exist_ok=False)
 with (folder/'once_claim.json').open('x') as f:json.dump({'accession':acc,'binding':expected,'native_launch_token':LAUNCH['token']},f);f.flush();os.fsync(f.fileno())
 inputs=folder/'protein_input';inputs.mkdir();staged=inputs/(acc+'.faa');shutil.copyfile(source,staged)
 if c.sha(staged)!=member['selected_faa']['sha256']:raise RuntimeError('S1 staged accepted FAA differs')
 prefix=Path(runtime['prefix']);env=pilot.environment(prefix);route=runtime['ipc_routing'];quality=folder/'quality_output';tmp=folder/'durable_tmp';tmp.mkdir();env['TREE2_EFFECTIVE_ORIGIN_RECEIPT']=str(folder/'effective_import_origins.json')
 command=[str(prefix/'bin/python'),'-B',route['bootstrap_path'],'--proof',route['proof_path'],'--proof-sha256',route['proof_sha256'],'--receipt',str(folder/'target_ipc.json'),'checkm2','predict','--genes','--extension','faa','--threads','1','--lowmem','--input',str(inputs),'--output-directory',str(quality),'--tmpdir',str(tmp),'--database_path',runtime['database_path'],'--dbg_vectors','--debug']
 invoke('unit_quality',command,env,folder,run,left,available['new_seconds_debited'])
 prediction={'status':'SINGLE_FAA_EXIT0_RAW_PREDICTION_COMMITTED_VALIDATION_PENDING','accession':acc,'quality_unit_execution':c.row(folder/'unit_quality/execution.json'),'raw_pickle':c.row(quality/'feature_vectors_1.pkl'),'quality_report':c.row(quality/'quality_report.tsv'),'native_launch_token':LAUNCH['token'],'manifest':c.manifest(folder,'prediction_manifest.json')}
 c.save(folder/'prediction_commit.json',prediction)
 available=c.budget(session);left=min(available['remaining_seconds'],c.CAPS[acc]-available['per_genome_seconds'].get(acc,0))
 if left<=0:raise TimeoutError('No remaining S1 per-genome/global feature-validation budget')
 request={'request_schema':'TREE2_SINGLE_FAA_FEATURE_REQUEST_S1R2','accession':acc,'runtime_prefix':str(prefix),'cohort_contract':plan['cohort_contract'],'source_manifest':plan['source_manifest'],'protocol_admission':c.row(c.ADMISSION),'input_plan_sha256':plan['_sha'],'schema':plan['feature_schema'],'artifacts':{'raw_pickle':prediction['raw_pickle'],'quality_report':prediction['quality_report'],'quality_unit_execution':prediction['quality_unit_execution'],**{k:member[k] for k in ('selected_faa','annotation_receipt','annotation_unit_execution','annotation_commit')}}}
 request_path=folder/'feature_request.json';c.save(request_path,request);output=folder/'feature_validation.json'
 invoke('unit_feature_validation',[str(prefix/'bin/python'),'-B',str(R/'scripts/checkm2_single_faa_feature_validator_S1R2.py'),'--request',str(request_path),'--request-sha256',c.sha(request_path),'--output',str(output)],env,folder,run,left,available['new_seconds_debited'])
 features=c.read(output)
 if features.get('status')!='SINGLE_FAA_FEATURES_S1R2_PASS_PENDING_NATIVE_CLOSURE' or features.get('row_count')!=1 or features.get('accession')!=acc:raise RuntimeError('S1 exact one-accession feature receipt absent')
 c.budget(session)
 commit={'status':'SINGLE_FAA_S1R2_EXIT0_FEATURES_VALIDATED_PENDING_NATIVE_CLOSURE','accession':acc,'binding':expected,'prediction_commit':c.row(folder/'prediction_commit.json'),'feature_validation':c.row(output),'quality_unit_execution':prediction['quality_unit_execution'],'validation_unit_execution':c.row(folder/'unit_feature_validation/execution.json'),'native_launch_token':LAUNCH['token'],'manifest':c.manifest(folder,'row_manifest.json'),'annotation_invoked':False,'production_panel_acceptance':False}
 c.save(folder/'commit.json',commit);return commit,False

def main(a):
 global LAUNCH,CURRENT_RUN,INNER_IDENTITY
 plan,cohort,admission=c.plan_gate(a.input_plan,a.input_plan_sha256);plan['_sha']=a.input_plan_sha256;LAUNCH=c.read(c.LAUNCH)
 if LAUNCH['token']!=a.launch_token or LAUNCH['input_plan_sha256']!=a.input_plan_sha256 or LAUNCH.get('protocol_admission_sha256')!=c.sha(c.ADMISSION):raise RuntimeError('S1 native/source/authority identity differs')
 pilot.LAUNCH=LAUNCH;pilot.legacy.LAUNCH=LAUNCH
 INNER_IDENTITY=pilot.legacy.stat(os.getpid()) # Required identity gate, outside optional callback.
 if os.environ.get('TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED')!='1':raise RuntimeError('Accepted private read-only runtime required')
 lock=(R/'state/checkm2_pilot.lock').open('a+b');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 try:
  os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:2]));stop();runtime=pilot.legacy.ready_gate(R/'state/checkm2_runtime_ready.json',require_effective=True);runtime['ipc_routing'],runtime['private_ipc_namespace']=pilot.legacy.ipc_runtime_gate(runtime);pilot.legacy.no_heavy_science()
  session=c.OUT/'sessions'/plan['session_identity_sha256']
  session.mkdir(parents=True,exist_ok=False)
  c.budget(session);claims=session/'phase_claims';claims.mkdir(exist_ok=True)
  with (claims/(c.sha(c.ADMISSION)+'.json')).open('x') as f:json.dump({'launch':LAUNCH,'phase':admission['phase']},f);f.flush();os.fsync(f.fileno())
  run=c.OUT/'runs'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+a.launch_token[:12]);run.mkdir(parents=True,exist_ok=False);CURRENT_RUN=run;c.save(run/'invocations.json',[]);c.save(run/'binding.json',{'plan':plan,'runtime':runtime,'admission':c.row(c.ADMISSION),'launch':LAUNCH})
  c.save(c.OUT/'runs_by_token'/(a.launch_token+'.json'),{'run_directory':str(run),'launch_token':a.launch_token,'input_plan_sha256':a.input_plan_sha256,'protocol_admission_sha256':c.sha(c.ADMISSION),'binding':c.row(run/'binding.json')})
  by_name={x['accession']:x for x in cohort['annotation_members']};preserved=c.preserved_row_gate(cohort,admission['preserved_row_authority']);results=[preserved];fresh=[]
  c.save(run/'preserved_original_row_reference.json',preserved);progress('RUNNING','Root-accepted original row preserved; nine new target calls pending',1)
  try:
   for acc in cohort['inference_order']:
    stop();commit,reused=one(by_name[acc],runtime,plan,session,run);entry={'accession':acc,'origin':'FRESH_CURRENT_S1R2_ROW','commit':c.row(session/'rows'/acc/'commit.json'),'feature_validation':commit['feature_validation'],'quality_unit_execution':commit['quality_unit_execution'],'validation_unit_execution':commit['validation_unit_execution'],'reused':False};results.append(entry);fresh.append(entry);progress('RUNNING','Validated new target QC commit '+acc,len(results))
   result={'status':'S1R2_CORE_PENDING_NAMESPACE_NATIVE_CLOSURE','input_plan_sha256':a.input_plan_sha256,'session_identity_sha256':plan['session_identity_sha256'],'protocol_admission_sha256':c.sha(c.ADMISSION),'rows':results,'preserved_rows':[preserved],'fresh_rows':fresh,'completed_qc_rows':len(results),'preserved_count':1,'fresh_count':len(fresh),'optional_progress_error_count':PROGRESS_ERROR_COUNT,'optional_progress_errors_first32':PROGRESS_ERRORS,'budget':c.budget(session),'annotation_functions_invoked':False,'maximum_query_genomes_per_prediction':1,'ten_genome_batch_benchmark_passed':False,'production_panel_acceptance':False}
   c.save(run/'result.json',result);manifest=c.manifest(run);c.save(c.OUT/'latest_pending_native.json',{'status':result['status'],'run_directory':str(run),'result_path':str(run/'result.json'),'manifest_path':str(c.bind(manifest)),'manifest_sha256':manifest['sha256'],'input_plan_sha256':a.input_plan_sha256,'launch_token':a.launch_token,'protocol_admission_sha256':c.sha(c.ADMISSION),'namespace_execution_receipt_path':str(c.E/'namespace_runs'/(a.launch_token+'.json'))});progress('CORE_PENDING_CLOSURE',result['status'],len(results))
  except BaseException as ex:
   c.save(run/'failure.json',{'status':'S1R2_FAILED_NO_AUTOMATIC_RETRY_OR_FALLBACK','error':repr(ex),'current_invocation_groups_closed':c.group_receipts_closed(run),'annotation_invoked':False,'prediction_replay_authorized':False});progress('FAILED','S1 stopped at first failure; preserve claims, outputs and spent budget',len(results));raise
 finally:lock.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input-plan',required=True);p.add_argument('--input-plan-sha256',required=True);p.add_argument('--launch-token',required=True);main(p.parse_args())
