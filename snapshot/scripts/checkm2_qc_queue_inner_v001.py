"""HELD P20 single novel genome: sequential original annotation, model-free search, stock resume."""
from pathlib import Path
import argparse,datetime,fcntl,json,math,os,shutil,sys,time,traceback
import checkm2_qc_queue_common_v001 as c
import checkm2_phase_separated_artifacts_N1 as artifacts
import checkm2_qc_queue_observer_v001 as observer
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
original_stop=pilot.legacy.stop_gate

def stop(*args,**kwargs):
 c.stop()
 if LAUNCH:
  from checkm2_saved_admission_read_v001 import admission_sha
  admission_sha(c.ADMISSION,LAUNCH['protocol_admission_sha256'])
 if HELPER_DEADLINE is not None and time.monotonic()>=HELPER_DEADLINE:raise TimeoutError('One continuous owner helper deadline')
 if OWNER_STOP is not None:OWNER_STOP()
 return original_stop(*args,**kwargs)

def bind_runtime_paths():
 # configure() changes these for every cohort, including second and later.
 pilot.OUT=c.OUT;pilot.STATE=c.STEP;pilot.LAUNCH=LAUNCH;pilot.progress=progress
 pilot.legacy.OUT=c.OUT;pilot.legacy.STATE=c.STEP;pilot.legacy.LAUNCH=LAUNCH;pilot.legacy.progress=progress
 pilot.legacy.stop_gate=stop


def invoke(name,command,env,folder):
 stop();spent=c.budget(CURRENT_RUN)
 if spent['known_limit_exceeded']:raise TimeoutError('Known retained shared/row budget exhausted')
 shared=folder.name=='shared';scope=folder.name;prior=spent['shared_units_seconds_charged_once']if shared else spent['per_row_units_seconds'].get(scope,{})
 caps=c.SHARED_UNITS if shared else c.ROW_UNITS
 if name not in caps or name in prior or(folder/name).exists():raise RuntimeError('Global/row phase once claim cannot replay')
 row_left=c.LIMITS['per_input_scientific_seconds']-spent['input_scientific_seconds'].get(scope,0)if not shared else float('inf')
 seconds=min(caps[name],row_left,spent['remaining_cohort_scientific_seconds'],HELPER_DEADLINE-time.monotonic(),OWNER_REMAINING())
 if not 0<seconds<=caps[name]:raise TimeoutError('Finite remaining phase/global allocation exhausted')
 c.save(folder/(name+'_budget.json'),{'declared_unit':name,'scope':'ONE_GLOBAL_SEARCH'if shared else scope,'allowed_seconds':seconds,'phase_ceiling_seconds':caps[name],'debit_before_start':spent,'global_cost_copied_to_rows':False})
 invocations=c.read(CURRENT_RUN/'invocations.json');invocations.append(str(folder/name));c.save(CURRENT_RUN/'invocations.json',invocations)
 try:
  observer.run_unit(name,command,env,folder,seconds,hooks={'save':c.save,'stop_gate':stop,'stat':pilot.legacy.stat,'group':lambda pgid:observer.strict_group(pgid,pilot.legacy.stat),'mem_available':pilot.legacy.mem_available,'progress':raw_progress,'optional_error_sink':note_optional,'controller_rows':controller_rows,'resource_policy':c.resource_policy})
 finally:
  terminal=folder/name/'execution.json'
  if not terminal.exists():raise RuntimeError('Actual phase debit/terminal unknown; no next phase or reset')
  OWNER_CHARGE(c.row(terminal))
 if not c.unit_closed(c.read(folder/name/'execution.json')):raise RuntimeError('Actual own phase0/group closure required')
 if c.budget(CURRENT_RUN)['known_limit_exceeded']:raise TimeoutError('Known observed elapsed exceeded declared allocation')


def base_request(plan,recipe,prefix):return {'input_plan':plan['_row'],'source_manifest':plan['source_manifest'],'protocol_admission':c.row(c.ADMISSION),'selected_inputs':plan['selected_inputs'],'runtime_prefix':str(prefix),'resource_method_amendment':plan['method_amendment']}
def command_for(prefix,module,request,output):return [str(prefix/'bin/python'),'-B',str(R/'scripts'/module),'--request',str(request),'--request-sha256',c.sha(request),'--output',str(output)]

def annotate_one(plan,recipe,runtime,folder,item):
 from checkm2_uniform_annotation_cache_QC_v001 import stage_uniform_annotation
 value=stage_uniform_annotation(plan,item,folder,read=c.read,bind=c.bind,row=c.row,save=c.save)
 # There is no new annotation process or invented current annotation0.
 return value


def shared_search(plan,recipe,runtime,run,queries):
 folder=run/'shared';folder.mkdir();prefix=Path(runtime['prefix']);env=environment(prefix);request=folder/'shared_request.json';output=folder/'search_receipts/global_validation.json';output.parent.mkdir()
 c.save(request,{**base_request(plan,recipe,prefix),'request_schema':'TREE2_CAMPAIGN_SHARED_DIAMOND_REQUEST_V003','query_inputs':queries,'database':recipe['runtime_binding']['database'],'diamond_binary':recipe['runtime_binding']['tools']['diamond'],'durable_scratch':str(folder/'scratch'),'search_output':str(folder/'search_output')})
 invoke('unit_shared_diamond',command_for(prefix,'checkm2_qc_queue_shared_producer_v001.py',request,output),env,folder)
 binary=c.row(folder/'unit_shared_diamond/execution.json');c.save(folder/'binary_search_exit0.json',{'status':'ONE_GLOBAL_BINARY0_GROUP_CLOSED_BEFORE_RAW_VALIDATION','execution':binary,'request':c.row(request)})
 invoke('unit_shared_search_validation',command_for(prefix,'checkm2_qc_queue_shared_validate_v001.py',request,output)+['--binary-execution',str(c.bind(binary)),'--binary-execution-sha256',binary['sha256']],env,folder)
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
 tmp=folder/'resume_tmp';tmp.mkdir();route=runtime['ipc_routing'];env=environment(prefix);env['TREE2_EFFECTIVE_ORIGIN_RECEIPT']=str(folder/'effective_import_origins.json')
 command=[str(prefix/'bin/python'),'-B',route['bootstrap_path'],'--proof',route['proof_path'],'--proof-sha256',route['proof_sha256'],'--receipt',str(folder/'target_ipc.json'),'checkm2','predict','--genes','--extension','faa','--threads','1','--lowmem','--resume','--input',str(protein_input),'--output-directory',str(resume),'--tmpdir',str(tmp),'--database_path',str(c.path(runtime['database_path'])),'--dbg_vectors','--debug']
 invoke('unit_resume',command,env,folder)
 after={'protein_files':artifacts.exact_faa_inventory(resume/'protein_files',acc,annotation['selected_faa']['sha256']),'diamond_files':artifacts.exact_diamond_inventory(resume/'diamond_output',c.row(resume/'diamond_output/DIAMOND_RESULTS.tsv'))}
 if before!=after:raise RuntimeError('Stock resume changed accepted query/shard input bytes')
 c.save(folder/'stock_resume_inventory_after.json',after)
 request=folder/'features_request.json';output=folder/'feature_validation.json';refs={'raw_pickle':c.row(resume/'feature_vectors_1.pkl'),'selected_faa':annotation['selected_faa'],'annotation_receipt':annotation['annotation_receipt'],'annotation_unit_execution':annotation['annotation_unit_execution'],'annotation_commit':annotation['annotation_commit'],'quality_report':c.row(resume/'quality_report.tsv'),'quality_unit_execution':c.row(folder/'unit_resume/execution.json'),'shared_search_commit':shared_reference,'global_search_execution':shared['binary_execution'],'global_search_validation_execution':shared['validation_execution'],'split_commit':shared['split_commit'],'raw_shard':shard['artifact']}
 c.save(request,{**base_request(plan,recipe,prefix),'request_schema':'TREE2_CAMPAIGN_SHARED_ROW_FEATURE_REQUEST_V003','accession':acc,'scientific_recipe':plan['scientific_recipe'],'schema':plan['feature_schema'],'artifacts':refs,'resume_output':str(resume),'shared_qualification_commit':qualification})
 invoke('unit_feature_validation',command_for(prefix,'checkm2_qc_queue_feature_validator_v001.py',request,output),env,folder)
 value=c.read(output)
 if value['status']!='P20_FEATURES_PASS_PENDING_NATIVE_CLOSURE'or value['accession']!=acc:raise RuntimeError('Exact own row full feature result required')
 commit={'status':'SHARED_SEARCH_OWN_ROW_FEATURES_VALIDATED_PENDING_CONTROL_AND_OWNER_CLOSURE','accession':acc,'input_plan_sha256':plan['_sha'],'source_manifest_sha256':plan['source_manifest']['sha256'],'annotation_commit':annotation['annotation_commit'],'feature_validation':c.row(output),'shared_search_commit':shared_reference,'raw_shard':shard['artifact'],'per_row_unit_executions':{'unit_annotation':annotation['annotation_unit_execution'],'unit_resume':c.row(folder/'unit_resume/execution.json'),'unit_feature_validation':c.row(folder/'unit_feature_validation/execution.json')},'per_row_search_execution_or_debit_created':False,'source_masks':item['source_masks'],'source_holds_preserved':item['source_holds_preserved'],'source_pending_reasons':item['source_pending_reasons']}
 c.save(folder/'commit.json',commit);return {'accession':acc,'commit':c.row(folder/'commit.json'),'feature_validation':c.row(output),'source_masks':item['source_masks'],'source_taxonomy_or_panel_acceptance':False}

def finish_controls(plan,recipe,runtime,run,shared_reference,first=None,initial_profile=None):
 folder=run/'shared';request=folder/'controls_request.json';output=folder/'control_comparison.json';prefix=Path(runtime['prefix']);original=c.read(c.bind(c.read(c.bind(shared_reference))['request']))
 c.save(request,{**base_request(plan,recipe,prefix),'request_schema':'TREE2_CAMPAIGN_SHARED_CONTROL_REQUEST_V003','query_inputs':original['query_inputs'],'shared_search_commit':shared_reference})
 invoke('unit_shared_control_comparison',command_for(prefix,'checkm2_qc_queue_shared_controls_v001.py',request,output),pilot.environment(prefix),folder)
 if c.read(output)['status']!='ALL_ACCEPTED_SERIAL_CONTROL_RAW_MULTISET_MATCHES':raise RuntimeError('SAME8 raw comparison failed; no current model dispatch')
 return {'control_comparison':c.row(output),'control_comparison_execution':c.row(folder/'unit_shared_control_comparison/execution.json')}


def execute_phases(plan,recipe,runtime,run,state):
 results=state['results'];annotations=state['annotations']
 for item in recipe['inputs']:
  stop();folder=run/'rows'/item['accession'];folder.mkdir();annotations.append(annotate_one(plan,recipe,runtime,folder,item));c.save(run/'annotations_checkpoint.json',{'annotations':annotations,'no_new_annotation_units':True})
 shared_reference=shared_search(plan,recipe,runtime,run,annotations+plan['controls']);state['shared_reference']=shared_reference
 controls=finish_controls(plan,recipe,runtime,run,shared_reference)
 if plan['cohort_index']==0:
  item=recipe['inputs'][0];first=predict_one(plan,recipe,runtime,run/'rows'/item['accession'],item,annotations[0],shared_reference);results.append(first)
  q={'status':'FIRST_OWN_FEATURE_AND_REAL_CONTROLS_QUALIFIED_PENDING_CONTEXT_CLOSURE','campaign_authority':plan['campaign_authority'],'shared_search_commit':shared_reference,'first_row_commit':first['commit'],**controls,'whole_owner_closure_pending':True}
  c.save(run/'shared/qualification_commit.json',q);qualification=c.row(run/'shared/qualification_commit.json');initial=qualification;batch_items=recipe['inputs'][1:];batch_annotations=annotations[1:];progress('RUNNING','First own stock and complete feature checks passed; batch remainder follows',1)
 else:
  initial=plan['initial_in_session_profile'];q={'status':'CURRENT_CONTROLS_AND_INITIAL_IN_SESSION_PROFILE_QUALIFIED_PENDING_CONTEXT_CLOSURE','campaign_authority':plan['campaign_authority'],'shared_search_commit':shared_reference,'initial_in_session_profile':initial,**controls,'whole_owner_closure_pending':True};c.save(run/'shared/qualification_commit.json',q);qualification=c.row(run/'shared/qualification_commit.json');batch_items=recipe['inputs'];batch_annotations=annotations
 c.shared_qualification_gate(plan,qualification,shared_reference);state['qualification']=qualification;state['initial_profile']=initial
 if batch_items:results.extend(predict_batch(plan,recipe,runtime,run,batch_items,batch_annotations,shared_reference,qualification))
 c.save(run/'completed_rows_checkpoint.json',{'rows':results,'qualification':qualification,'budget':c.budget(run),'external_parent_acceptance':'PENDING'});return state



OWNER_STOP=None;OWNER_REMAINING=lambda:float('inf');OWNER_CHARGE=lambda ref:None
def environment(prefix):
 env=pilot.environment(prefix)
 for key in('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','TF_NUM_INTRAOP_THREADS','TF_NUM_INTEROP_THREADS'):env[key]='1'
 return env
def controller_rows():
 rows=[];pid=os.getpid()
 for _ in range(64):
  item=pilot.legacy.stat(pid);rows.append(item)
  if item['parent_pid']<=1:break
  pid=item['parent_pid']
 return rows

def run_cohort(plan_ref,runtime,launch,deadline,progress_callback,stop_callback,remaining_callback,charge_callback):
 global LAUNCH,CURRENT_RUN,INNER_IDENTITY,HELPER_DEADLINE,DONE,OWNER_STOP,OWNER_REMAINING,OWNER_CHARGE,raw_progress
 plan,recipe,_=c.plan_gate(c.bind(plan_ref),plan_ref['sha256']);plan['_sha']=plan_ref['sha256'];plan['_row']=plan_ref
 LAUNCH=launch;HELPER_DEADLINE=deadline;DONE=0;OWNER_STOP=stop_callback;OWNER_REMAINING=remaining_callback;OWNER_CHARGE=charge_callback
 bind_runtime_paths();INNER_IDENTITY=pilot.legacy.stat(os.getpid())
 raw_progress=lambda status,detail,done=None,**extra:progress_callback(status,detail,done,**extra)
 run=c.path(plan['run_directory']);run.mkdir(parents=True,exist_ok=False);CURRENT_RUN=run;(run/'rows').mkdir();c.save(run/'invocations.json',[])
 c.save(run/'once_claim.json',{'plan':plan_ref,'native_launch_token':launch['token'],'cohort_index':plan['cohort_index'],'no_native_or_context_exit_claimed':True})
 state={'results':[],'annotations':[]}
 try:
  execute_phases(plan,recipe,runtime,run,state)
  result={'status':'COHORT_COMPUTED_PENDING_CONTEXT_CLOSURE','cohort_index':plan['cohort_index'],'input_plan':plan_ref,'rows':state['results'],'completed_qc_rows':len(state['results']),'shared_search_commit':state['shared_reference'],'same_cohort_qualification':state['qualification'],'initial_in_session_profile':state['initial_profile'],'budget':c.budget(run),'no_per_row_search_exit_or_duplicated_shared_debit':True,'external_parent_closure':'PENDING','source_taxonomy_or_panel_acceptance':False};c.save(run/'result.json',result);c.save(run/'checkpoint_manifest_ref.json',c.manifest(run))
  c.reset_closed_cohort(run);return result
 except BaseException as error:
  c.save(run/'failure.json',{'status':'CONTINUOUS_QC_COHORT_FAILED_NO_AUTOMATIC_RETRY','error':repr(error),'traceback':traceback.format_exc(),'rows':state['results'],'shared_search_commit':state.get('shared_reference'),'actual_debits_preserved':True,'external_parent_closure':'PENDING'});raise

def predict_batch(plan,recipe,runtime,run,items,annotations,shared_reference,qualification):
 c.shared_qualification_gate(plan,qualification,shared_reference)
 prefix=Path(runtime['prefix']);shared=c.read(c.bind(shared_reference));split=c.read(c.bind(shared['split_commit']));names=[x['accession']for x in items]
 selected={x['accession']:x for x in annotations};shards={x['accession']:x for x in split['shards']};root=run/'shared';inputs=run/'stock_batch_input';inputs.mkdir();resume=run/'stock_batch_output';(resume/'protein_files').mkdir(parents=True);(resume/'diamond_output').mkdir()
 for acc in names:
  if shards[acc]['rows']<=0:raise RuntimeError('Successful shared search has no own reported hits; hold, not negative')
  source=c.bind(selected[acc]['selected_faa']);shutil.copyfile(source,inputs/(acc+'.faa'));shutil.copyfile(source,resume/'protein_files'/(acc+'.faa'))
 raw=resume/'diamond_output/DIAMOND_RESULTS.tsv'
 with raw.open('xb')as out:
  for acc in names:
   data=c.bind(shards[acc]['artifact']).read_bytes()
   if not data.endswith(b'\n'):raise RuntimeError('Exact committed shard must end at complete original row')
   out.write(data)
  out.flush();os.fsync(out.fileno())
 def inventory():
  files={p.name:p for p in(resume/'protein_files').iterdir()}
  if set(files)!={acc+'.faa'for acc in names}or any(p.is_symlink()or not p.is_file()for p in files.values()):raise RuntimeError('Exact complete stock-batch FAA inventory required')
  rows={acc:c.row(files[acc+'.faa'])for acc in names}
  if any(rows[acc]['sha256']!=selected[acc]['selected_faa']['sha256']or rows[acc]['bytes']!=selected[acc]['selected_faa']['bytes']for acc in names):raise RuntimeError('Batch protein input differs from own committed FAA')
  if {p.name for p in(resume/'diamond_output').iterdir()}!={'DIAMOND_RESULTS.tsv'}:raise RuntimeError('Batch raw inventory has extras')
  return {'proteins':rows,'raw':c.row(raw)}
 before=inventory();c.save(root/'stock_batch_inventory_before.json',before);tmp=run/'stock_batch_tmp';tmp.mkdir();route=runtime['ipc_routing'];env=environment(prefix);env['TREE2_EFFECTIVE_ORIGIN_RECEIPT']=str(root/'batch_effective_import_origins.json')
 command=[str(prefix/'bin/python'),'-B',route['bootstrap_path'],'--proof',route['proof_path'],'--proof-sha256',route['proof_sha256'],'--receipt',str(root/'batch_target_ipc.json'),'checkm2','predict','--genes','--extension','faa','--threads','1','--lowmem','--resume','--input',str(inputs),'--output-directory',str(resume),'--tmpdir',str(tmp),'--database_path',str(c.path(runtime['database_path'])),'--dbg_vectors','--debug']
 invoke('unit_stock_batch',command,env,root)
 if inventory()!=before or {p.name for p in resume.glob('feature_vectors_*.pkl')}!={'feature_vectors_1.pkl'}:raise RuntimeError('Stock batch altered complete input inventory or emitted unexpected chunks')
 batch={'status':'SUPPORTED_STOCK_BATCH0_PENDING_PROJECTION_AND_CONTEXT_CLOSURE','input_plan_sha256':plan['_sha'],'source_manifest_sha256':plan['source_manifest']['sha256'],'accessions':names,'stock_batch_execution':c.row(root/'unit_stock_batch/execution.json'),'shared_search_commit':shared_reference,'raw_pickle':c.row(resume/'feature_vectors_1.pkl'),'quality_report':c.row(resume/'quality_report.tsv'),'own_input_inventory':before,'same_cohort_qualification':qualification,'global_ML_debit_not_copied_to_rows':True};c.save(root/'batch_prediction_commit.json',batch);batch_ref=c.row(root/'batch_prediction_commit.json')
 request=root/'batch_projection_request.json';projection=root/'batch_projection';c.save(request,{**base_request(plan,recipe,prefix),'request_schema':'TREE2_QC_STOCK_BATCH_PROJECTION_REQUEST_V001','accessions':names,'batch_prediction_commit':batch_ref})
 invoke('unit_batch_projection',command_for(prefix,'checkm2_qc_queue_batch_project_v001.py',request,projection),env,root)
 projection_ref=c.row(projection/'projection_commit.json');projected=c.read(c.bind(projection_ref));outputs=[]
 for item in items:
  acc=item['accession'];annotation=selected[acc];own=next(x for x in projected['rows']if x['accession']==acc);folder=run/'rows'/acc;own_resume=c.path(own['raw_pickle']['path']).parent;(own_resume/'protein_files').mkdir();(own_resume/'diamond_output').mkdir();shutil.copyfile(c.bind(annotation['selected_faa']),own_resume/'protein_files'/(acc+'.faa'));shutil.copyfile(c.bind(shards[acc]['artifact']),own_resume/'diamond_output/DIAMOND_RESULTS.tsv')
  refs={'raw_pickle':own['raw_pickle'],'selected_faa':annotation['selected_faa'],'annotation_receipt':annotation['annotation_receipt'],'annotation_unit_execution':annotation['annotation_unit_execution'],'annotation_commit':annotation['annotation_commit'],'quality_report':own['quality_report'],'quality_unit_execution':batch['stock_batch_execution'],'shared_search_commit':shared_reference,'global_search_execution':shared['binary_execution'],'global_search_validation_execution':shared['validation_execution'],'split_commit':shared['split_commit'],'raw_shard':shards[acc]['artifact'],'batch_prediction_commit':batch_ref,'batch_projection_commit':projection_ref,'batch_projection_execution':c.row(root/'unit_batch_projection/execution.json')}
  request=folder/'features_request.json';output=folder/'feature_validation.json';c.save(request,{**base_request(plan,recipe,prefix),'request_schema':'TREE2_CAMPAIGN_SHARED_ROW_FEATURE_REQUEST_V003','accession':acc,'scientific_recipe':plan['scientific_recipe'],'schema':plan['feature_schema'],'artifacts':refs,'resume_output':str(own_resume),'shared_qualification_commit':qualification})
  invoke('unit_feature_validation',command_for(prefix,'checkm2_qc_queue_feature_validator_v001.py',request,output),env,folder)
  value=c.read(output)
  if value['status']!='P20_FEATURES_PASS_PENDING_NATIVE_CLOSURE'or value['accession']!=acc:raise RuntimeError('Full own projected batch features required')
  commit={'status':'SHARED_SEARCH_BATCH_STOCK_OWN_ROW_VALIDATED_PENDING_CONTEXT_CLOSURE','accession':acc,'input_plan_sha256':plan['_sha'],'source_manifest_sha256':plan['source_manifest']['sha256'],'annotation_commit':annotation['annotation_commit'],'feature_validation':c.row(output),'shared_search_commit':shared_reference,'raw_shard':shards[acc]['artifact'],'global_stock_batch_execution':batch['stock_batch_execution'],'batch_prediction_commit':batch_ref,'batch_projection_commit':projection_ref,'batch_projection_execution':refs['batch_projection_execution'],'per_row_unit_executions':{'unit_annotation':annotation['annotation_unit_execution'],'unit_feature_validation':c.row(folder/'unit_feature_validation/execution.json')},'per_row_ML_or_search_exit_or_debit_created':False,'source_masks':item['source_masks'],'source_holds_preserved':item['source_holds_preserved'],'source_pending_reasons':item['source_pending_reasons']};c.save(folder/'commit.json',commit);outputs.append({'accession':acc,'commit':c.row(folder/'commit.json'),'feature_validation':c.row(output),'source_masks':item['source_masks'],'source_taxonomy_or_panel_acceptance':False});progress('RUNNING','Own batch projection/model-input checks complete without model replay',len(outputs)+(1 if plan['cohort_index']==0 else 0))
 return outputs
