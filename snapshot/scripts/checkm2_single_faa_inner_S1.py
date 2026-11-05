"""HELD S1: inference on accepted FAA only. There is no annotation dispatch path."""
from pathlib import Path
import argparse,datetime,fcntl,json,os,shutil,time
import checkm2_single_faa_common_S1 as c
import checkm2_protein_pilot_v001 as pilot
R=c.R;STEP=c.STEP;LAUNCH=None;COMMITTED_COUNT=0;REUSE={};CURRENT_RUN=None

def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def progress(status,detail,done=None,**extra):
 global COMMITTED_COUNT
 if done is not None:COMMITTED_COUNT=done
 owner={'windows_launch_token':LAUNCH['token'],'pid':LAUNCH['pid'],'creation_time_utc':LAUNCH['creation_time_utc']} if LAUNCH else {}
 if 'run_directory' in extra:extra['active_unit_directory']=extra.pop('run_directory')
 current={'run_directory':str(CURRENT_RUN)} if CURRENT_RUN else {}
 if LAUNCH:current.update(input_plan_sha256=LAUNCH['input_plan_sha256'],protocol_admission_sha256=LAUNCH['protocol_admission_sha256'])
 c.save(STEP,{'status':status,'detail':detail,'done':COMMITTED_COUNT,'total':10,'unit':'validated single-FAA QC commits','updated_utc':utc(),'operation':'SINGLE_FAA_S1','native_linux_identity':pilot.legacy.stat(os.getpid()),'production_panel_acceptance':False,**owner,**current,**extra})

pilot.OUT=c.OUT;pilot.STATE=STEP;pilot.progress=progress;pilot.legacy.STATE=STEP;pilot.legacy.OUT=c.OUT
original_stop=pilot.legacy.stop_gate

def stop(*args,**kwargs):
 c.stop()
 if LAUNCH and c.sha(c.ADMISSION)!=LAUNCH['protocol_admission_sha256']:raise InterruptedError('S1 admission changed during owned execution')
 return original_stop(*args,**kwargs)
pilot.legacy.stop_gate=stop

def invoke(name,command,env,folder,run,seconds,debit):
 if not 0<seconds<=600:raise TimeoutError('No admissible remaining S1 per-genome/shared time')
 c.save(folder/(name+'_budget.json'),{'unit':name,'debit_before_start_seconds':debit,'allowed_seconds':seconds,'shared_new_seconds':3495.758365,'per_genome_shared_seconds':600,'protocol_admission_sha256':c.sha(c.ADMISSION)})
 index=c.read(run/'invocations.json');index.append(str(folder/name));c.save(run/'invocations.json',index)
 return pilot.run_unit(name,command,env,folder,seconds)

def binding(member,runtime,plan):
 return {'member':member,'input_plan_sha256':plan['_sha'],'session_identity_sha256':plan['session_identity_sha256'],'source_manifest_sha256':plan['source_manifest']['sha256'],'annotation_reuse_authority':c.row(c.bind(c.read(c.ADMISSION)['annotation_reuse_authority'])),'image_sha256':runtime['ready']['runtime_image']['sha256'],'effective_runtime_manifest_sha256':runtime['effective_runtime']['manifest_sha256'],'prediction_genome_count':1,'annotation_invoked':False}

def reused_row(folder,expected):
 p=folder/'commit.json';acc=folder.name
 if not p.exists() or c.sha(p)!=REUSE.get('accepted_row_commit_sha256s',{}).get(acc):raise RuntimeError('S1 partial/unclosed row preserved; no automatic prediction replay')
 commit=c.read(p)
 if commit.get('status')!='SINGLE_FAA_EXIT0_FEATURES_VALIDATED_PENDING_NATIVE_CLOSURE' or commit.get('binding')!=expected or commit.get('native_launch_token') not in REUSE.get('closed_native_launch_tokens',[]):raise RuntimeError('S1 reused row binding/native closure differs')
 c.verify_manifest(folder,c.read(c.bind(commit['manifest'])))
 for key in ('quality_unit_execution','validation_unit_execution'):
  if not c.unit_closed(c.read(c.bind(commit[key]))):raise RuntimeError('S1 reused row child closure missing')
 return commit

def one(member,runtime,plan,session,run):
 acc=member['accession'];folder=session/'rows'/acc;expected=binding(member,runtime,plan)
 if folder.exists():return reused_row(folder,expected),True
 available=c.budget(session);left=min(600,available['remaining_seconds'])
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
 available=c.budget(session);left=min(available['remaining_seconds'],600-available['per_genome_seconds'].get(acc,0))
 if left<=0:raise TimeoutError('No remaining S1 per-genome/global feature-validation budget')
 request={'request_schema':'TREE2_SINGLE_FAA_FEATURE_REQUEST_S1','accession':acc,'runtime_prefix':str(prefix),'cohort_contract':plan['cohort_contract'],'source_manifest':plan['source_manifest'],'protocol_admission':c.row(c.ADMISSION),'input_plan_sha256':plan['_sha'],'schema':plan['feature_schema'],'artifacts':{'raw_pickle':prediction['raw_pickle'],'quality_report':prediction['quality_report'],'quality_unit_execution':prediction['quality_unit_execution'],**{k:member[k] for k in ('selected_faa','annotation_receipt','annotation_unit_execution','annotation_commit')}}}
 request_path=folder/'feature_request.json';c.save(request_path,request);output=folder/'feature_validation.json'
 invoke('unit_feature_validation',[str(prefix/'bin/python'),'-B',str(R/'scripts/checkm2_single_faa_feature_validator_S1.py'),'--request',str(request_path),'--request-sha256',c.sha(request_path),'--output',str(output)],env,folder,run,left,available['new_seconds_debited'])
 features=c.read(output)
 if features.get('status')!='SINGLE_FAA_FEATURES_S1_PASS_PENDING_NATIVE_CLOSURE' or features.get('row_count')!=1 or features.get('accession')!=acc:raise RuntimeError('S1 exact one-accession feature receipt absent')
 c.budget(session)
 commit={'status':'SINGLE_FAA_EXIT0_FEATURES_VALIDATED_PENDING_NATIVE_CLOSURE','accession':acc,'binding':expected,'prediction_commit':c.row(folder/'prediction_commit.json'),'feature_validation':c.row(output),'quality_unit_execution':prediction['quality_unit_execution'],'validation_unit_execution':c.row(folder/'unit_feature_validation/execution.json'),'native_launch_token':LAUNCH['token'],'manifest':c.manifest(folder,'row_manifest.json'),'annotation_invoked':False,'production_panel_acceptance':False}
 c.save(folder/'commit.json',commit);return commit,False

def main(a):
 global LAUNCH,REUSE,CURRENT_RUN
 plan,cohort,admission=c.plan_gate(a.input_plan,a.input_plan_sha256);plan['_sha']=a.input_plan_sha256;LAUNCH=c.read(c.LAUNCH)
 if LAUNCH['token']!=a.launch_token or LAUNCH['input_plan_sha256']!=a.input_plan_sha256 or LAUNCH.get('protocol_admission_sha256')!=c.sha(c.ADMISSION):raise RuntimeError('S1 native/source/authority identity differs')
 pilot.LAUNCH=LAUNCH;pilot.legacy.LAUNCH=LAUNCH
 if admission['phase']=='RECOVER_CLOSED_ROWS':REUSE=c.resume_proof(admission,plan['session_identity_sha256'])
 if os.environ.get('TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED')!='1':raise RuntimeError('Accepted private read-only runtime required')
 lock=(R/'state/checkm2_pilot.lock').open('a+b');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 try:
  os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:2]));stop();runtime=pilot.legacy.ready_gate(R/'state/checkm2_runtime_ready.json',require_effective=True);runtime['ipc_routing'],runtime['private_ipc_namespace']=pilot.legacy.ipc_runtime_gate(runtime);pilot.legacy.no_heavy_science()
  session=c.OUT/'sessions'/plan['session_identity_sha256']
  if admission['phase']=='RUN_FRESH_SERIES':session.mkdir(parents=True,exist_ok=False)
  elif not session.exists():raise RuntimeError('S1 closed-row recovery session missing')
  c.budget(session);claims=session/'phase_claims';claims.mkdir(exist_ok=True)
  with (claims/(c.sha(c.ADMISSION)+'.json')).open('x') as f:json.dump({'launch':LAUNCH,'phase':admission['phase']},f);f.flush();os.fsync(f.fileno())
  run=c.OUT/'runs'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+a.launch_token[:12]);run.mkdir(parents=True,exist_ok=False);CURRENT_RUN=run;c.save(run/'invocations.json',[]);c.save(run/'binding.json',{'plan':plan,'runtime':runtime,'admission':c.row(c.ADMISSION),'launch':LAUNCH})
  by_name={x['accession']:x for x in cohort['annotation_members']};results=[]
  try:
   for acc in cohort['inference_order']:
    stop();commit,reused=one(by_name[acc],runtime,plan,session,run);results.append({'accession':acc,'commit':c.row(session/'rows'/acc/'commit.json'),'feature_validation':commit['feature_validation'],'quality_unit_execution':commit['quality_unit_execution'],'validation_unit_execution':commit['validation_unit_execution'],'reused':reused});progress('RUNNING','Validated single-FAA QC commit '+acc,len(results))
   result={'status':'S1_CORE_PENDING_NAMESPACE_NATIVE_CLOSURE','input_plan_sha256':a.input_plan_sha256,'session_identity_sha256':plan['session_identity_sha256'],'protocol_admission_sha256':c.sha(c.ADMISSION),'rows':results,'budget':c.budget(session),'annotation_functions_invoked':False,'maximum_query_genomes_per_prediction':1,'ten_genome_batch_benchmark_passed':False,'production_panel_acceptance':False}
   c.save(run/'result.json',result);manifest=c.manifest(run);c.save(c.OUT/'latest_pending_native.json',{'status':result['status'],'run_directory':str(run),'result_path':str(run/'result.json'),'manifest_path':str(c.bind(manifest)),'manifest_sha256':manifest['sha256'],'input_plan_sha256':a.input_plan_sha256,'launch_token':a.launch_token,'protocol_admission_sha256':c.sha(c.ADMISSION),'namespace_execution_receipt_path':str(c.E/'namespace_runs'/(a.launch_token+'.json'))});progress('CORE_PENDING_CLOSURE',result['status'],len(results))
  except BaseException as ex:
   c.save(run/'failure.json',{'status':'S1_FAILED_NO_AUTOMATIC_RETRY_OR_FALLBACK','error':repr(ex),'current_invocation_groups_closed':c.group_receipts_closed(run),'annotation_invoked':False,'prediction_replay_authorized':False});progress('FAILED','S1 stopped at first failure; preserve claims, outputs and spent budget',len(results));raise
 finally:lock.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input-plan',required=True);p.add_argument('--input-plan-sha256',required=True);p.add_argument('--launch-token',required=True);main(p.parse_args())
