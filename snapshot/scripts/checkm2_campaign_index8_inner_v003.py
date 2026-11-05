"""HELD P20 single novel genome: sequential original annotation, model-free search, stock resume."""
from pathlib import Path
import argparse,datetime,fcntl,json,math,os,shutil,sys,time,traceback
import checkm2_campaign_index8_common_v003 as c
import checkm2_phase_separated_artifacts_N1 as artifacts
import checkm2_campaign_index8_observer_v003 as observer
import checkm2_protein_pilot_v001 as pilot
from checkm2_optional_progress_S1R2 import safe_call
R=c.R;LAUNCH=None;CURRENT_RUN=None;INNER_IDENTITY=None;DONE=0;HELPER_DEADLINE=None;PROGRESS_ERRORS=[];PROGRESS_ERROR_COUNT=0

def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def note_optional(value):
 global PROGRESS_ERROR_COUNT
 PROGRESS_ERROR_COUNT+=1
 if len(PROGRESS_ERRORS)<32:PROGRESS_ERRORS.append(value)
 try:print(json.dumps({'optional_progress_io_error':value}),file=sys.stderr,flush=True)
 except OSError:pass

def raw_progress(status,detail,done=None,**extra):
 global DONE
 if type(done)is int and 0<=done<=c.COUNT:DONE=max(DONE,done)
 if 'run_directory'in extra:extra['active_unit_directory']=extra.pop('run_directory')
 owner={'windows_launch_token':LAUNCH['token'],'pid':LAUNCH['pid'],'creation_time_utc':LAUNCH['creation_time_utc'],'input_plan_sha256':LAUNCH['input_plan_sha256'],'protocol_admission_sha256':LAUNCH['protocol_admission_sha256']} if LAUNCH else {}
 current={'run_directory':str(CURRENT_RUN)} if CURRENT_RUN else {}
 c.save(c.STEP,{'status':status,'detail':detail,'done':DONE,'total':c.COUNT,'unit':'validated own-row QC method estimates','operation':c.ROLE,'updated_utc':utc(),'native_linux_identity':INNER_IDENTITY,'production_panel_acceptance':False,**owner,**current,**extra})
def progress(*args,**kwargs):return safe_call(raw_progress,*args,error_sink=note_optional,**kwargs)
pilot.OUT=c.OUT;pilot.STATE=c.STEP;pilot.progress=progress;pilot.legacy.STATE=c.STEP;pilot.legacy.OUT=c.OUT
original_stop=pilot.legacy.stop_gate

def stop(*args,**kwargs):
 c.stop()
 if LAUNCH and c.sha(c.ADMISSION)!=LAUNCH['protocol_admission_sha256']:raise InterruptedError('P20 admission changed')
 if HELPER_DEADLINE is not None and time.monotonic()>=HELPER_DEADLINE:raise TimeoutError('P20 helper finite deadline reached')
 return original_stop(*args,**kwargs)
pilot.legacy.stop_gate=stop


def invoke(name,command,env,folder):
 stop();spent=c.budget(CURRENT_RUN)
 if spent['known_limit_exceeded']:raise TimeoutError('Known retained shared/row budget exhausted')
 shared=folder.name=='shared';scope=folder.name
 prior=spent['shared_units_seconds_charged_once']if shared else spent['per_row_units_seconds'].get(scope,{})
 caps=c.SHARED_UNITS if shared else c.ROW_UNITS
 if name not in caps or name in prior or(folder/name).exists():raise RuntimeError('Global/row phase once claim cannot replay')
 row_left=c.LIMITS['per_input_scientific_seconds']-spent['input_scientific_seconds'].get(scope,0)if not shared else float('inf')
 seconds=min(caps[name],row_left,spent['remaining_cohort_scientific_seconds'],HELPER_DEADLINE-time.monotonic())
 if not 0<seconds<=caps[name]:raise TimeoutError('Finite remaining shared/row phase allowance exhausted')
 c.save(folder/(name+'_budget.json'),{'declared_unit':name,'scope':'ONE_GLOBAL_SEARCH'if shared else scope,'allowed_seconds':seconds,'phase_ceiling_seconds':caps[name],'debit_before_start':spent,'global_cost_copied_to_rows':False})
 invocations=c.read(CURRENT_RUN/'invocations.json');invocations.append(str(folder/name));c.save(CURRENT_RUN/'invocations.json',invocations)
 observer.run_unit(name,command,env,folder,seconds,hooks={'save':c.save,'stop_gate':stop,'stat':pilot.legacy.stat,'group':lambda pgid:observer.strict_group(pgid,pilot.legacy.stat),'mem_available':pilot.legacy.mem_available,'progress':raw_progress,'optional_error_sink':note_optional})
 if not c.unit_closed(c.read(folder/name/'execution.json')):raise RuntimeError('Genuine actual owned phase0/group closure required')
 if c.budget(CURRENT_RUN)['known_limit_exceeded']:raise TimeoutError('Known observed actual elapsed exceeded finite allocation')

def base_request(plan,recipe,prefix):return {'input_plan':plan['_row'],'source_manifest':plan['source_manifest'],'protocol_admission':c.row(c.ADMISSION),'selected_inputs':plan['selected_inputs'],'runtime_prefix':str(prefix),'resource_method_amendment':plan['method_amendment']}
def command_for(prefix,module,request,output):return [str(prefix/'bin/python'),'-B',str(R/'scripts'/module),'--request',str(request),'--request-sha256',c.sha(request),'--output',str(output)]

def annotate_one(plan,recipe,runtime,folder,item):
 acc=item['accession'];prefix=Path(runtime['prefix'])
 if acc in plan.get('annotation_reuse_by_accession',{}):
  commit=c.annotation_reuse_gate(plan,acc,item);reference=plan['annotation_reuse_by_accession'][acc]['commit'];c.save(folder/'annotation_reuse.json',{'original_commit':reference,'status':'EXACT_CLOSED_ANNOTATION_REUSED_NO_REPLAY'})
 else:
  staged=folder/(acc+'.fna');shutil.copyfile(c.path(item['fasta_path']),staged)
  if c.sha(staged)!=item['fasta_sha256']:raise RuntimeError('Exact acquired staged input changed')
  request=folder/'annotation_request.json';annotation=folder/'annotation';c.save(request,{**base_request(plan,recipe,prefix),'request_schema':'TREE2_PHASE_SEPARATED_P20_ANNOTATION_REQUEST_V001','accession':acc,'staged_fna':c.row(staged)})
  invoke('unit_annotation',command_for(prefix,'checkm2_campaign_index8_annotation_v003.py',request,annotation),pilot.environment(prefix),folder)
  commit={'status':'P20_ANNOTATION_UNIT0_COMMITTED_PENDING_CONTEXT_CLOSURE','accession':acc,'input_plan_sha256':plan['_sha'],'source_manifest_sha256':plan['source_manifest']['sha256'],'selected_faa':c.row(annotation/(acc+'.faa')),'annotation_receipt':c.row(annotation/'annotation_receipt.json'),'unit_execution':c.row(folder/'unit_annotation/execution.json'),'native_launch_token':LAUNCH['token'],'source_masks':item['source_masks'],'manifest':c.manifest(annotation),'all10_author_returns_preserved':True,'coordinate_GFF_FNA_deleted_by_unchanged_author':True}
  c.save(folder/'annotation_commit.json',commit);reference=c.row(folder/'annotation_commit.json')
 return {'accession':acc,'role':'FRESH','selected_faa':commit['selected_faa'],'annotation_receipt':commit['annotation_receipt'],'annotation_unit_execution':commit['unit_execution'],'annotation_commit':reference}

def shared_search(plan,recipe,runtime,run,queries):
 folder=run/'shared';folder.mkdir();prefix=Path(runtime['prefix']);env=pilot.environment(prefix);request=folder/'shared_request.json';output=folder/'search_receipts/global_validation.json';output.parent.mkdir()
 c.save(request,{**base_request(plan,recipe,prefix),'request_schema':'TREE2_CAMPAIGN_SHARED_DIAMOND_REQUEST_V003','query_inputs':queries,'database':recipe['runtime_binding']['database'],'diamond_binary':recipe['runtime_binding']['tools']['diamond'],'durable_scratch':str(folder/'scratch'),'search_output':str(folder/'search_output')})
 invoke('unit_shared_diamond',command_for(prefix,'checkm2_campaign_index8_shared_producer_v003.py',request,output),env,folder)
 binary=c.row(folder/'unit_shared_diamond/execution.json');c.save(folder/'binary_search_exit0.json',{'status':'ONE_GLOBAL_BINARY0_GROUP_CLOSED_BEFORE_RAW_VALIDATION','execution':binary,'request':c.row(request)})
 invoke('unit_shared_search_validation',command_for(prefix,'checkm2_campaign_index8_shared_validate_v003.py',request,output)+['--binary-execution',str(c.bind(binary)),'--binary-execution-sha256',binary['sha256']],env,folder)
 validated=c.read(output)
 if validated['status']!='GLOBAL_SHARED_SEARCH_SPLIT_VALIDATED_PENDING_UNIT_CLOSURE':raise RuntimeError('Exact full shared raw/split validation required')
 commit={'status':'GLOBAL_SHARED_SEARCH_SPLIT_VALIDATED_PENDING_CONTEXT_CLOSURE','input_plan_sha256':plan['_sha'],'source_manifest_sha256':plan['source_manifest']['sha256'],'request':c.row(request),'binary_execution':binary,'validation_execution':c.row(folder/'unit_shared_search_validation/execution.json'),'split_commit':validated['split_commit'],'merged_query':validated['merged_query'],'merged_raw':validated['merged_raw'],'query_inventory':validated['query_inventory'],'selected_faas':validated['selected_faas'],'control_comparison_pending':True,'global_search_charged_once':True}
 c.save(folder/'shared_search_commit.json',commit);return c.row(folder/'shared_search_commit.json')

def predict_one(plan,recipe,runtime,folder,item,annotation,shared_reference,qualification=None):
 acc=item['accession'];prefix=Path(runtime['prefix']);shared=c.read(c.bind(shared_reference));split=c.read(c.bind(shared['split_commit']));shard=next(x for x in split['shards']if x['accession']==acc)
 if shard['rows']==0:
  c.save(folder/'search_no_reported_hits.json',{'status':'SUCCESSFUL_SHARED_SEARCH_NO_REPORTED_HITS_QC_HELD_NOT_NEGATIVE','global_search':shared_reference,'shard':shard,'QC_or_defence_negative':False});raise RuntimeError('Own empty successful search is held, not an absent defence or valid QC estimate')
 if qualification is not None:c.shared_qualification_gate(plan,qualification,shared_reference)
 faa=c.bind(annotation['selected_faa']);protein_input=folder/'protein_input';protein_input.mkdir();shutil.copyfile(faa,protein_input/faa.name)
 resume=folder/'resume_output';(resume/'protein_files').mkdir(parents=True);(resume/'diamond_output').mkdir();shutil.copyfile(faa,resume/'protein_files'/faa.name);shutil.copyfile(c.bind(shard['artifact']),resume/'diamond_output/DIAMOND_RESULTS.tsv')
 artifacts.exact_faa_inventory(protein_input,acc,annotation['selected_faa']['sha256']);before={'protein_files':artifacts.exact_faa_inventory(resume/'protein_files',acc,annotation['selected_faa']['sha256']),'diamond_files':artifacts.exact_diamond_inventory(resume/'diamond_output',c.row(resume/'diamond_output/DIAMOND_RESULTS.tsv'))};c.save(folder/'stock_resume_inventory_before.json',before)
 tmp=folder/'resume_tmp';tmp.mkdir();route=runtime['ipc_routing'];env=pilot.environment(prefix);env['TREE2_EFFECTIVE_ORIGIN_RECEIPT']=str(folder/'effective_import_origins.json')
 command=[str(prefix/'bin/python'),'-B',route['bootstrap_path'],'--proof',route['proof_path'],'--proof-sha256',route['proof_sha256'],'--receipt',str(folder/'target_ipc.json'),'checkm2','predict','--genes','--extension','faa','--threads','1','--lowmem','--resume','--input',str(protein_input),'--output-directory',str(resume),'--tmpdir',str(tmp),'--database_path',str(c.path(runtime['database_path'])),'--dbg_vectors','--debug']
 invoke('unit_resume',command,env,folder)
 after={'protein_files':artifacts.exact_faa_inventory(resume/'protein_files',acc,annotation['selected_faa']['sha256']),'diamond_files':artifacts.exact_diamond_inventory(resume/'diamond_output',c.row(resume/'diamond_output/DIAMOND_RESULTS.tsv'))}
 if before!=after:raise RuntimeError('Stock resume changed accepted query/shard input bytes')
 c.save(folder/'stock_resume_inventory_after.json',after)
 request=folder/'features_request.json';output=folder/'feature_validation.json';refs={'raw_pickle':c.row(resume/'feature_vectors_1.pkl'),'selected_faa':annotation['selected_faa'],'annotation_receipt':annotation['annotation_receipt'],'annotation_unit_execution':annotation['annotation_unit_execution'],'annotation_commit':annotation['annotation_commit'],'quality_report':c.row(resume/'quality_report.tsv'),'quality_unit_execution':c.row(folder/'unit_resume/execution.json'),'shared_search_commit':shared_reference,'global_search_execution':shared['binary_execution'],'global_search_validation_execution':shared['validation_execution'],'split_commit':shared['split_commit'],'raw_shard':shard['artifact']}
 c.save(request,{**base_request(plan,recipe,prefix),'request_schema':'TREE2_CAMPAIGN_SHARED_ROW_FEATURE_REQUEST_V003','accession':acc,'scientific_recipe':plan['scientific_recipe'],'schema':plan['feature_schema'],'artifacts':refs,'resume_output':str(resume),'shared_qualification_commit':qualification})
 invoke('unit_feature_validation',command_for(prefix,'checkm2_campaign_index8_feature_validator_v003.py',request,output),env,folder)
 value=c.read(output)
 if value['status']!='P20_FEATURES_PASS_PENDING_NATIVE_CLOSURE'or value['accession']!=acc:raise RuntimeError('Exact own row full feature result required')
 commit={'status':'SHARED_SEARCH_OWN_ROW_FEATURES_VALIDATED_PENDING_CONTROL_AND_OWNER_CLOSURE','accession':acc,'input_plan_sha256':plan['_sha'],'source_manifest_sha256':plan['source_manifest']['sha256'],'annotation_commit':annotation['annotation_commit'],'feature_validation':c.row(output),'shared_search_commit':shared_reference,'raw_shard':shard['artifact'],'per_row_unit_executions':{'unit_annotation':annotation['annotation_unit_execution'],'unit_resume':c.row(folder/'unit_resume/execution.json'),'unit_feature_validation':c.row(folder/'unit_feature_validation/execution.json')},'per_row_search_execution_or_debit_created':False,'source_masks':item['source_masks'],'source_holds_preserved':item['source_holds_preserved'],'source_pending_reasons':item['source_pending_reasons']}
 c.save(folder/'commit.json',commit);return {'accession':acc,'commit':c.row(folder/'commit.json'),'feature_validation':c.row(output),'source_masks':item['source_masks'],'source_taxonomy_or_panel_acceptance':False}

def finish_controls(plan,recipe,runtime,run,shared_reference,first):
 folder=run/'shared';request=folder/'controls_request.json';output=folder/'control_comparison.json';prefix=Path(runtime['prefix']);original=c.read(c.bind(c.read(c.bind(shared_reference))['request']))
 c.save(request,{**base_request(plan,recipe,prefix),'request_schema':'TREE2_CAMPAIGN_SHARED_CONTROL_REQUEST_V003','query_inputs':original['query_inputs'],'shared_search_commit':shared_reference})
 invoke('unit_shared_control_comparison',command_for(prefix,'checkm2_campaign_index8_shared_controls_v003.py',request,output),pilot.environment(prefix),folder)
 comparison=c.read(output)
 if comparison['status']!='ALL_ACCEPTED_SERIAL_CONTROL_RAW_MULTISET_MATCHES':raise RuntimeError('Real control gate failed; remaining ML held')
 qualification={'status':'FIRST_OWN_FEATURE_AND_REAL_CONTROLS_QUALIFIED_PENDING_CONTEXT_CLOSURE','shared_search_commit':shared_reference,'first_row_commit':first['commit'],'control_comparison':c.row(output),'control_comparison_execution':c.row(folder/'unit_shared_control_comparison/execution.json'),'single_query_equivalence_scope':'ONLY_EXACT_ACCEPTED_CONTROLS_NOT_UNIVERSAL','whole_owner_closure_pending':True}
 c.save(folder/'qualification_commit.json',qualification);return c.row(folder/'qualification_commit.json')

def execute_phases(plan,recipe,runtime,run,state):
 results=state['results'];annotations=state['annotations']
 for item in recipe['inputs']:
  stop();folder=run/'rows'/item['accession'];folder.mkdir();annotations.append(annotate_one(plan,recipe,runtime,folder,item));c.save(run/'annotations_checkpoint.json',{'annotations':annotations,'budget':c.budget(run),'accepted_annotated_source_not_genome_QC':True})
 queries=annotations+plan['controls'];shared_reference=shared_search(plan,recipe,runtime,run,queries);state['shared_reference']=shared_reference
 first_item=recipe['inputs'][0];first=predict_one(plan,recipe,runtime,run/'rows'/first_item['accession'],first_item,annotations[0],shared_reference);results.append(first)
 c.save(run/'first_row_checkpoint_before_controls.json',{'row':first,'budget':c.budget(run),'control_comparison_pending':True,'Root_acceptance_pending':True});progress('RUNNING','First own model/features checkpoint preserved; finishing real controls',1)
 qualification=finish_controls(plan,recipe,runtime,run,shared_reference,first);state['qualification']=qualification
 for item,annotation in zip(recipe['inputs'][1:],annotations[1:]):
  stop();c.shared_qualification_gate(plan,qualification,shared_reference);value=predict_one(plan,recipe,runtime,run/'rows'/item['accession'],item,annotation,shared_reference,qualification);results.append(value);c.save(run/'completed_rows_checkpoint.json',{'rows':results,'qualification':qualification,'budget':c.budget(run)});progress('RUNNING','Own row model/features validated using one global shared search',len(results))
 return state

def main(a):
 global LAUNCH,CURRENT_RUN,INNER_IDENTITY,HELPER_DEADLINE
 plan,recipe,admitted=c.plan_gate(a.input_plan,a.input_plan_sha256);plan['_sha']=a.input_plan_sha256;plan['_row']=c.row(c.path(a.input_plan));LAUNCH=c.read(c.LAUNCH)
 if LAUNCH['token']!=a.launch_token or LAUNCH['input_plan_sha256']!=a.input_plan_sha256 or LAUNCH['protocol_admission_sha256']!=c.sha(c.ADMISSION):raise RuntimeError('P20 launch/source/authority differs')
 request=c.read(c.E/'launch_requests'/(a.launch_token+'.json'))
 if request.get('token')!=a.launch_token or request.get('input_plan_sha256')!=a.input_plan_sha256 or request.get('protocol_admission_sha256')!=c.sha(c.ADMISSION)or request.get('cold_session_seconds')!=c.LIMITS['cold_session_seconds'] or request.get('helper_max_seconds')!=c.LIMITS['cold_session_seconds']-1240:raise RuntimeError('P20 immutable cold request differs')
 deadline=a.helper_deadline_unix
 if not math.isfinite(deadline)or deadline>request['cold_wall_deadline_unix']-640+0.01 or deadline-time.time()>c.LIMITS['cold_session_seconds']-1240+0.01 or deadline<=time.time():raise TimeoutError('P20 helper deadline exceeds immutable fresh cold allocation')
 HELPER_DEADLINE=time.monotonic()+deadline-time.time();pilot.LAUNCH=LAUNCH;pilot.legacy.LAUNCH=LAUNCH;INNER_IDENTITY=pilot.legacy.stat(os.getpid())
 if os.environ.get('TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED')!='1':raise RuntimeError('Private read-only accepted runtime required')
 lock=(R/'state/checkm2_pilot.lock').open('a+b')
 try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BaseException:lock.close();raise
 try:
  os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:2]));stop();runtime=pilot.legacy.ready_gate(R/'state/checkm2_runtime_ready.json',require_effective=True);runtime['ipc_routing'],runtime['private_ipc_namespace']=pilot.legacy.ipc_runtime_gate(runtime);pilot.legacy.no_heavy_science()
  session=c.OUT/'sessions'/plan['session_identity_sha256'];session.mkdir(parents=True,exist_ok=False)
  with(session/'once_claim.json').open('x')as f:json.dump({'native_launch_token':a.launch_token,'input_plan_sha256':a.input_plan_sha256,'source_manifest_sha256':plan['source_manifest']['sha256'],'accessions':recipe['inference_order'],'phase':'RUN_ONE_FUTURE_SHARED_INDEX8_COHORT_ONCE'},f);f.flush();os.fsync(f.fileno())
  run=c.OUT/'runs'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+a.launch_token[:12]);run.mkdir(parents=True,exist_ok=False);CURRENT_RUN=run;c.save(run/'invocations.json',[]);(run/'rows').mkdir()
  c.save(run/'binding.json',{'plan':plan,'runtime':runtime,'admission':c.row(c.ADMISSION),'launch':LAUNCH,'immutable_request':request,'helper_deadline_unix':deadline})
  c.save(c.OUT/'runs_by_token'/(a.launch_token+'.json'),{'run_directory':str(run),'launch_token':a.launch_token,'input_plan_sha256':a.input_plan_sha256,'protocol_admission_sha256':c.sha(c.ADMISSION),'binding':c.row(run/'binding.json')})

  results=[];annotations=[];shared_reference=None;qualification=None;state={'results':results,'annotations':annotations,'shared_reference':None,'qualification':None}
  try:
   execute_phases(plan,recipe,runtime,run,state);shared_reference=state['shared_reference'];qualification=state['qualification']
   result={'status':'P20_CORE_PENDING_NAMESPACE_NATIVE_CLOSURE','input_plan_sha256':a.input_plan_sha256,'source_manifest_sha256':plan['source_manifest']['sha256'],'completed_qc_rows':len(results),'rows':results,'annotations':annotations,'shared_search_commit':shared_reference,'qualification_commit':qualification,'budget':c.budget(run),'shared_DIAMOND_actual_units':1,'shared_raw_validation_actual_units':1,'shared_control_comparison_actual_units':1,'per_row_DIAMOND_units_created':0,'per_row_model_units':c.COUNT,'per_row_feature_units':c.COUNT,'accepted_control_annotation_or_model_replayed':False,'whole_owner_context_acceptance_pending':True,'source_taxonomy_or_panel_acceptance':False}
   c.save(run/'result.json',result);manifest=c.manifest(run);c.save(c.OUT/'latest_pending_native.json',{'status':result['status'],'run_directory':str(run),'result_path':str(run/'result.json'),'manifest_path':str(c.bind(manifest)),'manifest_sha256':manifest['sha256'],'input_plan_sha256':a.input_plan_sha256,'launch_token':a.launch_token,'protocol_admission_sha256':c.sha(c.ADMISSION),'namespace_execution_receipt_path':str(c.E/'namespace_runs'/(a.launch_token+'.json'))});progress('CORE_PENDING_CLOSURE',result['status'],c.COUNT)
  except BaseException as ex:
   closed=None;debit=None;secondary=[]
   try:closed=c.group_receipts_closed(run)
   except BaseException as e:secondary.append(repr(e))
   try:debit=c.budget(run)
   except BaseException as e:secondary.append(repr(e))
   c.save(run/'failure.json',{'status':'SHARED_PROFILE_FAILED_NO_AUTOMATIC_REPLAY_OR_FALLBACK','error':repr(ex),'traceback':traceback.format_exc(),'owned_unit_groups_closed':closed,'known_budget':debit,'secondary_errors':secondary,'completed_rows':results,'annotations_checkpoint':annotations,'shared_search_commit':state['shared_reference'],'global_qualification_commit':state['qualification'],'no_automatic_fallback_or_unit_replay':True,'bounded_future_fallback':'Frozen V2 per-row only after full external closure/new authority; reuse actual annotation commits and retain ALL shared costs. A successful validated global search is not blindly recalculated.'});progress('FAILED','Shared profile stopped; preserve global and per-row checkpoints',len(results));raise
 finally:
  try:fcntl.flock(lock,fcntl.LOCK_UN)
  finally:lock.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input-plan',required=True);p.add_argument('--input-plan-sha256',required=True);p.add_argument('--launch-token',required=True);p.add_argument('--helper-deadline-unix',required=True,type=float);main(p.parse_args())
