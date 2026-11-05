"""One validation-only60s unit over the original committed outputs. No upstream execution."""
from pathlib import Path
import argparse,datetime,fcntl,json,math,os,time,traceback
import checkm2_saved_P20_common_v001 as c
import checkm2_unit_observer_S1R2 as observer
import checkm2_protein_pilot_v001 as pilot
from checkm2_optional_progress_S1R2 import safe_call
LAUNCH=None;DEADLINE=None;RUN=None;ERRORS=[]
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def stop(*args,**kwargs):
 c.stop()
 if DEADLINE is not None and time.monotonic()>=DEADLINE:raise TimeoutError('Saved-validation helper deadline')
 if LAUNCH and c.sha(c.ADMISSION)!=LAUNCH['protocol_admission_sha256']:raise InterruptedError('Saved runtime admission changed')
def progress(status,detail,done=0,**extra):
 if 'run_directory'in extra:extra['active_unit_directory']=extra.pop('run_directory')
 c.save(c.STEP,{'status':status,'detail':detail,'done':done,'total':1,'updated_utc':utc(),'unit':'saved-output validation only','pid':LAUNCH['pid'],'creation_time_utc':LAUNCH['creation_time_utc'],'windows_launch_token':LAUNCH['token'],'native_linux_identity':pilot.legacy.stat(os.getpid()),'run_directory':str(RUN)if RUN else None,'production_panel_acceptance':False,**extra})
def main(a):
 global LAUNCH,DEADLINE,RUN
 plan,recipe,admitted=c.plan_gate(a.input_plan,a.input_plan_sha256);LAUNCH=c.read(c.LAUNCH)
 if LAUNCH['token']!=a.launch_token or LAUNCH['input_plan_sha256']!=a.input_plan_sha256:raise RuntimeError('Saved-validation exact launch binding differs')
 request=c.read(c.E/'launch_requests'/(a.launch_token+'.json'));deadline=a.helper_deadline_unix
 if not math.isfinite(deadline)or not time.time()<deadline<=request['cold_wall_deadline_unix']-640+.01 or deadline-time.time()>1160.01:raise RuntimeError('Saved-validation cold/helper bound differs')
 DEADLINE=time.monotonic()+deadline-time.time();pilot.LAUNCH=LAUNCH;pilot.legacy.LAUNCH=LAUNCH
 if os.environ.get('TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED')!='1':raise RuntimeError('Accepted read-only image required')
 lock=(c.R/'state/checkm2_pilot.lock').open('r+b');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 try:
  os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:2]));stop();runtime=pilot.legacy.ready_gate(c.R/'state/checkm2_runtime_ready.json',require_effective=True);runtime['ipc_routing'],runtime['private_ipc_namespace']=pilot.legacy.ipc_runtime_gate(runtime);pilot.legacy.no_heavy_science()
  session=c.OUT/'sessions'/a.input_plan_sha256;session.mkdir(parents=True,exist_ok=False)
  with(session/'once_claim.json').open('x')as f:json.dump({'native_launch_token':a.launch_token,'input_plan_sha256':a.input_plan_sha256,'only_saved_validation':True},f);f.flush();os.fsync(f.fileno())
  RUN=c.OUT/'runs'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+a.launch_token[:12]);RUN.mkdir(parents=True,exist_ok=False);(RUN/'rows/GCF_000831485.1').mkdir(parents=True);c.save(RUN/'invocations.json',[])
  c.save(RUN/'binding.json',{'plan':plan,'runtime':runtime,'launch':LAUNCH,'admission':c.row(c.ADMISSION),'immutable_request':request});c.save(c.OUT/'runs_by_token'/(a.launch_token+'.json'),{'run_directory':str(RUN),'launch_token':a.launch_token,'input_plan_sha256':a.input_plan_sha256,'protocol_admission_sha256':c.sha(c.ADMISSION),'binding':c.row(RUN/'binding.json')})
  try:
   authority=c.read(c.bind(plan['saved_validation_authority']));original=authority['original_request'];prefix=c.path(recipe['runtime_binding']['canonical_prefix']);folder=RUN/'rows/GCF_000831485.1';output=folder/'feature_validation.json'
   command=[str(prefix/'bin/python'),'-B',str(c.bind(authority['validator_source'])),'--repair-authority',str(c.bind(plan['saved_validation_authority'])),'--repair-authority-sha256',plan['saved_validation_authority']['sha256'],'--request',str(c.bind(original)),'--request-sha256',original['sha256'],'--output',str(output)]
   env=pilot.environment(prefix);seconds=min(60,DEADLINE-time.monotonic());assert seconds>0
   c.save(folder/'unit_saved_validation_budget.json',{'allowed_seconds':seconds,'new_explicit_validation_allowance':60,'prior_debits':c.budget(RUN),'only_saved_validation':True});c.save(RUN/'invocations.json',[str(folder/'unit_saved_validation')]);progress('RUNNING','Validating saved first-row features; no annotation/search/model replay')
   observer.run_unit('unit_saved_validation',command,env,folder,seconds,hooks={'save':c.save,'stop_gate':stop,'stat':pilot.legacy.stat,'group':lambda pgid:observer.strict_group(pgid,pilot.legacy.stat),'mem_available':pilot.legacy.mem_available,'progress':progress,'optional_error_sink':ERRORS.append})
   unit=c.read(folder/'unit_saved_validation/execution.json');features=c.read(output)
   if not c.unit_closed(unit)or features.get('status')!='P20_SAVED_FEATURES_REPAIR_PASS_PENDING_REPAIR_OWNER_CLOSURE' or features.get('accession')!='GCF_000831485.1' or features.get('finite_domain_features')!=21241 or features.get('exact_FAA_metadata_features')!=22 or features.get('independently_recomputed_membership_features')!=1220 or features.get('membership_mismatches')!=0:raise RuntimeError('Saved-validation actual unit/complete features not passed')
   member={'accession':'GCF_000831485.1','feature_validation':c.row(output),'unit_execution':c.row(folder/'unit_saved_validation/execution.json'),'original_successful_units':authority['successful_original_units'],'preserved_failed_unit':authority['preserved_failed_validation_unit'],'source_masks':features['source_masks'],'source_pending_reasons':features['source_pending_reasons'],'source_holds_preserved':features['source_holds_preserved']}
   c.save(folder/'commit.json',{'status':'SAVED_P20_ROW_VALIDATED_PENDING_REPAIR_NATIVE_CLOSURE',**member,'input_plan_sha256':a.input_plan_sha256,'manifest':c.manifest(folder,'row_manifest.json'),'production_panel_acceptance':False})
   result={'status':'P20_SAVED_CORE_PENDING_NAMESPACE_NATIVE_CLOSURE','completed_qc_rows':1,'rows':[member],'input_plan_sha256':a.input_plan_sha256,'protocol_admission_sha256':c.sha(c.ADMISSION),'budget':c.budget(RUN),'annotation_DIAMOND_or_ML_runs':0,'previously_accepted_rows_recalculated':False,'production_panel_acceptance':False};c.save(RUN/'result.json',result);mf=c.manifest(RUN)
   c.save(c.OUT/'latest_pending_native.json',{'status':result['status'],'run_directory':str(RUN),'result_path':str(RUN/'result.json'),'manifest_path':str(c.bind(mf)),'manifest_sha256':mf['sha256'],'input_plan_sha256':a.input_plan_sha256,'launch_token':a.launch_token,'protocol_admission_sha256':c.sha(c.ADMISSION),'namespace_execution_receipt_path':str(c.E/'namespace_runs'/(a.launch_token+'.json'))});progress('CORE_PENDING_CLOSURE','Saved first-row validation complete; repair native/context closure pending',1)
  except BaseException as error:
   c.save(RUN/'failure.json',{'status':'SAVED_P20_VALIDATION_FAILED_NO_AUTOMATIC_RETRY','error':repr(error),'traceback':traceback.format_exc(),'invocation_groups_closed':c.group_receipts_closed(RUN),'no_upstream_replay':True,'previous_debits_preserved':True});raise
 finally:fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input-plan',required=True);p.add_argument('--input-plan-sha256',required=True);p.add_argument('--launch-token',required=True);p.add_argument('--helper-deadline-unix',required=True,type=float);main(p.parse_args())
