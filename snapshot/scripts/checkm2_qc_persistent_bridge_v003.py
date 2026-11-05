"""One existing RO/IPC context: saved file validation FIRST, then admitted QC queue."""
from pathlib import Path
import argparse,datetime,json,os,time,traceback,types,sys
import checkm2_qc_persistent_common_v003 as c
import checkm2_protein_pilot_v001 as pilot
from checkm2_optional_progress_S1R2 import safe_call
from checkm2_saved_admission_read_v001 import admission_sha

def main(a):
 plan,_,authority=c.plan_gate(a.input_plan,a.input_plan_sha256);launch=c.read(c.LAUNCH);deadline=a.helper_deadline_unix
 if launch['token']!=a.launch_token or launch['input_plan_sha256']!=a.input_plan_sha256:raise RuntimeError('Exact continuous native owner differs')
 outer=c.read(c.E/'launch_requests'/(a.launch_token+'.json'))
 if not time.time()<deadline<=outer['cold_wall_deadline_unix']-640+.01:raise RuntimeError('Finite inherited whole-context deadline exceeded')
 os.sched_setaffinity(0,{0});pilot.LAUNCH=launch;pilot.legacy.LAUNCH=launch;identity=pilot.legacy.stat(os.getpid());started=datetime.datetime.now(datetime.timezone.utc).isoformat();errors=[];done=0
 def raw_progress(status,detail,current=None,**extra):
  nonlocal done
  if type(current)is int and 0<=current<=898:done=max(done,current)
  c.save(c.STEP,{'status':status,'detail':detail,'done':done,'total':898,'unit':'own method estimates pending real context closure','windows_launch_token':launch['token'],'pid':launch['pid'],'creation_time_utc':launch['creation_time_utc'],'native_linux_identity':identity,'run_directory':str(c.SCORE),'updated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'started_utc':started,'production_panel_acceptance':False,**extra})
 def progress(*args,**kwargs):return safe_call(raw_progress,*args,error_sink=errors.append,**kwargs)
 pilot.legacy.progress=progress;pilot.legacy.STATE=c.STEP;pilot.legacy.OUT=c.OUT
 def stop():
  c.stop();admission_sha(c.ADMISSION,launch['protocol_admission_sha256'],error_sink=errors.append);c.linux_guard()
  if time.time()>=deadline:raise TimeoutError('Continuous Root-owned context deadline exhausted')
 c.marker_and_exclusivity_gate();stop();progress('PREPARING','Binding immutable runtime/DB/models ONCE; original FIRSTFV0 will be reused without execution',0)
 runtime=pilot.legacy.ready_gate(c.R/'state/checkm2_runtime_ready.json',require_effective=True);runtime['ipc_routing'],runtime['private_ipc_namespace']=pilot.legacy.ipc_runtime_gate(runtime)
 runtime_ref=c.E/'runtime_bindings'/(a.launch_token+'.json');c.save(runtime_ref,{'runtime':runtime,'mount_namespace':os.readlink('/proc/self/ns/mnt'),'resource_limits':c.active_resource_limits()})
 request={'request_schema':'TREE2_QC_CONTINUOUS_RUNTIME_REQUEST_V001','parent_plan':c.row(c.path(a.input_plan)),'protocol_admission':c.row(c.ADMISSION),'campaign_authority':c.row(c.ADMISSION),'source_manifest':plan['source_manifest'],'campaign_data':plan['campaign_data'],'accepted_registry':plan['accepted_registry'],'conditional_shared_profile_authority':plan['conditional_shared_profile_authority'],'saved_feature_repair':plan['saved_feature_repair'],'runtime_binding_receipt':c.row(runtime_ref),'companion_marker':plan['companion_marker'],'post_marker_resource_admission_path':plan['post_marker_resource_admission_path'],'native_launch':c.row(c.LAUNCH),'helper_deadline_unix':deadline,'output_root':str(c.SCORE)}
 packet=c.E/'core_requests'/(a.launch_token+'.json');c.save(packet,request)
 c.SCORE.mkdir(parents=True,exist_ok=False);c.save(c.SCORE/'once_claim.json',{'parent_plan':request['parent_plan'],'Root_admission':request['protocol_admission'],'native_launch_token':a.launch_token,'no_accepted_replay':True});c.save(c.SCORE/'invocations.json',[])
 binding=c.E/'core_bindings'/(a.launch_token+'.json');c.save(binding,{'request':c.row(packet),'runtime':c.row(runtime_ref),'launch':launch});c.save(c.OUT/'runs_by_token'/(a.launch_token+'.json'),{'run_directory':str(c.SCORE),'launch_token':a.launch_token,'input_plan_sha256':a.input_plan_sha256,'protocol_admission_sha256':c.sha(c.ADMISSION),'binding':c.row(binding)})

 rows=[]
 try:
  checkpoint_ref,checkpoint=c.reuse_first_feature_gate(plan);c.save(c.SCORE/'reused_first_feature.json',{'status':'ORIGINAL_FIRSTFV0_REUSED_NO_CURRENT_UNIT_OR_DEBIT','original_checkpoint':checkpoint_ref,'reuse_authority':plan['reused_first_feature_authority'],'new_feature_annotation_DIAMOND_or_ML_runs':0});rows.append({'accession':'GCF_900636715.1','origin':'ORIGINAL_CLOSED_FIRSTFV0_REUSED_NO_CURRENT_EXECUTION','checkpoint':checkpoint_ref,'reuse_authority':plan['reused_first_feature_authority']});progress('RUNNING','Original validated saved-feature checkpoint reused; fresh queued bulk only, no scoring replay',1)
  # Approved finite data-only slot: owner/runtime stay frozen; later source must be
  # immutable, Root-reviewed and restricted to the one declared QC provider.
  job_path=c.path(plan['bulk_job_path']);wait_until=min(deadline-640,time.time()+plan.get('bulk_job_wait_seconds',3600))
  while not job_path.exists():
   stop()
   if time.time()>=wait_until:raise TimeoutError('Root-admitted frozen bulk job not supplied within finite context slot')
   progress('WAITING_AT_GATE','Original features reused; read-only context retained awaiting immutable Root-admitted corrected bulk source',1);time.sleep(2)
  job=c.read(job_path)
  if job.get('status')!='ROOT_ADMITTED_FROZEN_QC_BULK_JOB_IN_EXISTING_RO_CONTEXT_V001'or job.get('parent_plan_sha256')!=a.input_plan_sha256 or job.get('repaired_feature_request_sha256')!='e585a66ecf45d508294ae161024fdef1ee2c57bb55fd5e0f5f4fe3bcdd32621e':raise RuntimeError('Exact Root bulk job scope/first-validation linkage differs')
  source_manifest=job['source_manifest']
  for source in c.read(c.bind(source_manifest))['sources']:c.bind(source)
  provider=c.bind(job['provider_source'])
  if provider!=c.R/'scripts/checkm2_qc_queue_serial_provider_v002.py':raise RuntimeError('Only the declared reviewed QC queue provider may occupy this slot')
  phase=c.read(c.bind(job['phase_admission']))
  if phase.get('status')!='ROOT_ADMITTED_ONE_CONTINUOUS_QC_QUEUE_CONTEXT_V001'or phase.get('input_plan_sha256')!=a.input_plan_sha256 or phase.get('source_manifest')!=source_manifest or phase.get('campaign_data')!=plan['campaign_data']or phase.get('delegated_from_root_session_admission')!=request['protocol_admission']:raise RuntimeError('Separate exact reviewed delegated bulk admission required')
  for review in job['source_review_receipts']:c.bind(review)
  bulk_request={**request,'protocol_admission':job['phase_admission'],'campaign_authority':job['phase_admission'],'source_manifest':source_manifest,'conditional_shared_profile_authority':phase['conditional_shared_profile_authority'],'first_saved_feature_checkpoint':checkpoint_ref,'root_bulk_job':c.row(job_path)}
  import importlib.util
  module=importlib.util.spec_from_file_location('Root_admitted_qc_provider',provider);queue=importlib.util.module_from_spec(module);module.loader.exec_module(queue)
  result=queue.run_campaign(bulk_request,runtime,c.SCORE,checkpoint_ref,progress)
  rows.extend(result['rows']);result={**result,'status':'QC_CONTINUOUS_QUEUE_CORE_PENDING_NATIVE_CLOSURE','rows':rows,'completed_qc_rows':len(rows),'saved_feature_first':checkpoint_ref,'one_RO_IPC_context_for_all_completed_cohorts':True,'source_taxonomy_or_final_panel_acceptance':False,'per_cohort_fake_native_closure_or_ledger_acceptance':False,'optional_progress_errors':errors};c.save(c.SCORE/'result.json',result)
  c.save(c.SCORE/'invocations.json',[str(p.parent)for p in sorted(c.SCORE.rglob('command.json'))]);mf=c.manifest(c.SCORE,'outer_manifest.json');c.save(c.OUT/'latest_pending_native.json',{'status':result['status'],'run_directory':str(c.SCORE),'result_path':str(c.SCORE/'result.json'),'manifest_path':str(c.bind(mf)),'manifest_sha256':mf['sha256'],'input_plan_sha256':a.input_plan_sha256,'launch_token':a.launch_token,'protocol_admission_sha256':c.sha(c.ADMISSION),'namespace_execution_receipt_path':str(c.E/'namespace_runs'/(a.launch_token+'.json'))});progress('CORE_PENDING_CLOSURE','Completed in-context results preserved; real native/namespace/image/lease closure and Root acceptance pending',len(rows))
 except BaseException as e:
  c.save(c.SCORE/'invocations.json',[str(p.parent)for p in sorted(c.SCORE.rglob('command.json'))]);c.save(c.SCORE/'failure.json',{'status':'QC_CONTINUOUS_QUEUE_FAILED_PRESERVE_NO_BLIND_REPLAY','error':repr(e),'traceback':traceback.format_exc(),'completed_initial_rows':rows,'original_claims_and_debits_preserved':True,'actual_native_context_closure':'PENDING'});progress('FAILED','QC session stopped; successful checkpoints and all actual debits preserved',len(rows));raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input-plan',required=True);p.add_argument('--input-plan-sha256',required=True);p.add_argument('--launch-token',required=True);p.add_argument('--helper-deadline-unix',required=True,type=float);main(p.parse_args())
