"""One explicitly changed process-lifetime repair; old annotation and all debits survive."""
import math,os
import checkm2_P20_continue19_common_v001 as prior
old=prior.old
R=old.R;path=old.path;sha=old.sha;read=old.read;save=old.save;row=old.row;bind=old.bind
manifest=old.manifest;verify_manifest=old.verify_manifest;unit_closed=old.unit_closed;group_receipts_closed=old.group_receipts_closed;pending_is_current=old.pending_is_current;runtime_gate=old.runtime_gate
E=old.E/'resource_repair_v002';OUT=old.OUT/'resource_repair_v002';STATE=E/'progress.json';STEP=E/'step.json';LAUNCH=E/'native_scientific_launch.json';ADMISSION=E/'Root_runtime_admission.json';STOP=R/'state/STOP_CHECKM2_P20_RESOURCE_REPAIR_V002';UNRESOLVED_HANDOFF=E/'unresolved_ownership_handoff.json'
ACC='GCF_002993975.1';ROLE='P20_ONE_INDEX8_RESOURCE_VARIANT_QUALIFICATION'
PRIOR_ANNOTATION=36.03804357199988;FIRST_FAILED_DIAMOND=110.38959032199637;SECOND_FAILED_DIAMOND=127.56053909700131;PRIOR_DIAMOND=math.fsum([FIRST_FAILED_DIAMOND,SECOND_FAILED_DIAMOND])
UNITS={'unit_diamond':600-PRIOR_DIAMOND,'unit_resume':600,'unit_feature_validation':30}
NEW_SCIENCE=math.fsum(UNITS.values())
LIMITS={**old.LIMITS,'cohort_scientific_seconds':NEW_SCIENCE,'cold_session_seconds':3000}
def stop():
 prior.stop()
 if STOP.exists():raise InterruptedError('P20 resource repair scoped STOP')
def budget(run):
 run=path(run);commands=set(run.glob('rows/*/unit_*/command.json'));terminals=set(run.glob('rows/*/unit_*/execution.json'));allocations=set(run.glob('rows/*/unit_*_budget.json'))
 if terminals!={p.with_name('execution.json')for p in commands}or allocations!={p.parent.parent/(p.parent.name+'_budget.json')for p in commands}:raise RuntimeError('Repair unknown/incomplete debit; no reset')
 spent={}
 for p in terminals:
  acc=p.parent.parent.name;name=p.parent.name;u=read(p);value=u.get('elapsed_seconds')
  if acc!=ACC or name not in UNITS or type(value)not in(int,float)or not math.isfinite(value)or not 0<=value<=UNITS[name] or u.get('owned_group_empty')is not True or u.get('remaining_owned_processes')!=[]:raise RuntimeError('Repair phase/input/debit/closed-group differs')
  spent[name]=value
 used=math.fsum(spent.values());total=math.fsum([PRIOR_ANNOTATION,PRIOR_DIAMOND,used])
 if used>NEW_SCIENCE or total>1410 or total+340.5752029999858>28200:raise RuntimeError('Original phase/input/aggregate allowance exceeded')
 return {'units_seconds_by_accession':{ACC:spent}if spent else {},'input_scientific_seconds':{ACC:total},'cohort_scientific_seconds_debited':used,'remaining_cohort_scientific_seconds':NEW_SCIENCE-used,'old_successful_annotation_seconds_charged':PRIOR_ANNOTATION,'old_failed_DIAMOND_seconds_charged':PRIOR_DIAMOND,'old_original_P20_science_seconds_charged':340.5752029999858,'separate_saved_repair_validation_seconds_charged':43.283077190004406,'original_input_total_scientific_seconds':total,'original_P20_science_aggregate_seconds':340.5752029999858+total,'new_allowance_seconds':NEW_SCIENCE,'borrowed_allowance':False,'all_old_claims_and_debits_preserved':True}
def current_failed_run(step,token,input_plan_sha,protocol_sha):
 p=OUT/'runs_by_token'/(token+'.json')
 if not p.exists():return None
 loc=read(p)
 if loc['launch_token']!=token or loc['input_plan_sha256']!=input_plan_sha or loc['protocol_admission_sha256']!=protocol_sha:raise RuntimeError('Repair failed locator differs')
 bind(loc['binding']);run=path(loc['run_directory'])
 if run.parent!=OUT/'runs' or read(run/'failure.json')['status']!='P20_FAILED_NO_AUTOMATIC_RETRY_OR_FALLBACK':raise RuntimeError('Repair failure evidence differs')
 return run
def annotation_gate(plan):
 commit=read(bind(plan['reused_annotation_commit']))
 if commit['status']!='P20_ANNOTATION_UNIT0_COMMITTED_PENDING_CONTEXT_CLOSURE' or commit['accession']!=ACC or commit['input_plan_sha256']!=plan['prior_continuation_plan']['sha256'] or commit['source_manifest_sha256']!=plan['prior_source_manifest']['sha256']:raise RuntimeError('Exact old annotation phase provenance differs')
 verify_manifest(bind(commit['manifest']).parent,read(bind(commit['manifest'])))
 if not unit_closed(read(bind(commit['unit_execution']))) or read(bind(commit['unit_execution']))['elapsed_seconds']!=PRIOR_ANNOTATION:raise RuntimeError('Original successful annotation actual0/elapsed required')
 bind(commit['selected_faa']);bind(commit['annotation_receipt'])
 return commit
def plan_gate(plan_path,expected_sha,require_admission=True,closed_finalization=False):
 stop();p=path(plan_path)
 if sha(p)!=expected_sha:raise RuntimeError('Repair plan SHA differs')
 plan=read(p)
 if plan.get('schema')!='TREE2_P20_ONE_INDEX8_RESOURCE_REPAIR_PLAN_V002' or plan.get('limits')!=LIMITS or plan.get('role')!=ROLE or plan.get('accessions')!=[ACC] or plan.get('phase_order')!=list(UNITS):raise RuntimeError('Exact one repaired-input plan required')
 previous,recipe,_=prior.plan_gate(bind(plan['prior_continuation_plan']),plan['prior_continuation_plan']['sha256'],require_admission=False,closed_finalization=True)
 if previous['source_manifest']!=plan['prior_source_manifest'] or previous['accepted_registry']!=plan['accepted_registry'] or previous['queue_launch_context']!=plan['queue_launch_context'] or plan['remaining_reserved_accessions']!=[x['accession']for x in recipe['inputs'][1:]]:raise RuntimeError('Previous reservation/source/accepted/remaining order differs')
 if recipe['inputs'][0]['accession']!=ACC:raise RuntimeError('Frozen reserved first repair order differs')
 closure=read(bind(plan['failed_closed_authority']))
 if closure.get('status')!='ROOT_FAILED_CLOSED_COHORT_REPAIR_REQUIRED' or closure.get('owned_group_namespace_image_lease_closure_verified')is not True or closure.get('actual_native_exit_code')!=2 or closure.get('actual_WSL_exit_code')!=1 or closure['successful_annotation_reusable']!=plan['reused_annotation_commit']:raise RuntimeError('Actual failed-attempt closure authority required')
 for ref in closure['closure_and_result_evidence']:bind(ref)
 failed=read(bind(plan['failed_DIAMOND_execution']))
 if failed['exit_code']!=-15 or failed['failure_kind']!='RESOURCE' or failed['elapsed_seconds']!=FIRST_FAILED_DIAMOND or failed['owned_group_empty']is not True or failed['remaining_owned_processes']!=[] or failed['sampled_peak_summed_rss_bytes']!=2149838848:raise RuntimeError('Old failed-search debit/closure must survive')
 second=read(bind(plan['second_failed_DIAMOND_execution']))
 if second['exit_code']!=-15 or second['elapsed_seconds']!=SECOND_FAILED_DIAMOND or second['owned_group_empty']is not True or second['remaining_owned_processes']!=[] or second['sampled_peak_summed_rss_bytes']!=2181656576:raise RuntimeError('Second failed-search debit/closure must survive')
 closed=read(bind(plan['second_failure_closed_authority']))
 if closed['status']!='ROOT_CLOSED_RESOURCE_FAILURE_NO_UNCHANGED_RETRY' or closed['all_current_and_prior_owner_context_image_IPC_and_three_lease_closure_verified']is not True:raise RuntimeError('Second actual native/guest/context failure closure required')
 bind(closed['complete_closure_receipt']);bind(closed['external_closure_audit_actual_exit']);bind(closed['actual_native_exit'])
 method=read(bind(plan['method_amendment']))
 if method['status']!='ROOT_REVIEWED_INDEX8_RESOURCE_VARIANT_FOR_ONE_EMPIRICAL_QUALIFICATION' or method['index_chunks']!=8 or method['block_size']!=0.5 or method['threads']!=1 or method['real_genome_numerical_equivalence_established']is not False:raise RuntimeError('Explicit resource-parameter variant review required; no silent equivalence')
 synthetic=read(bind(method['closed_synthetic_authority']))
 if synthetic['status']!='ROOT_ACCEPTED_CLOSED_SYNTHETIC_INDEX_COMPARISON_ONLY' or synthetic['actual_native_exit_code']!=0 or synthetic['full_owner_context_and_three_lease_closure_verified']is not True:raise RuntimeError('Closed synthetic option comparison required')
 for ref in synthetic['closure_and_result_evidence']:bind(ref)
 ann=annotation_gate(plan)
 if ann['source_masks']!=recipe['inputs'][0]['source_masks']:raise RuntimeError('Reused annotation masks differ')
 for ref in read(bind(plan['source_manifest']))['sources']:bind(ref)
 proposal=read(bind(plan['repair_proposal']))
 if proposal['action']!='REPAIR_CLOSED_LEDGER_COHORT':raise RuntimeError('Bound repair proposal differs')
 if UNRESOLVED_HANDOFF.exists() or list((E/'unresolved_ownership').glob('*.json')):raise RuntimeError('Unknown ownership blocks new repair')
 token=os.environ.get('TREE2_CHECKM2_PILOT_LAUNCH_TOKEN')
 for claim in OUT.glob('sessions/*/once_claim.json'):
  consumed=read(claim)
  if consumed['input_plan_sha256']!=expected_sha or(not closed_finalization and consumed['native_launch_token']!=token):raise RuntimeError('Changed repair already consumed; no automatic retry')
 recipe={**recipe,'inputs':recipe['inputs'][:1],'inference_order':[ACC],'role':ROLE,'limits':LIMITS,'phases':UNITS,'resource_variant':{'index_chunks':8,'block_size':0.5,'threads':1,'method_amendment':plan['method_amendment']}}
 if not require_admission:return plan,recipe,None
 admitted=read(ADMISSION)
 if admitted.get('status')!='ROOT_ADMITTED_ONE_P20_INDEX8_RESOURCE_REPAIR_SESSION_V002' or admitted.get('phase')!='QUALIFY_INDEX8_SEARCH_THEN_STOCK_FEATURES_ONCE' or admitted.get('input_plan_sha256')!=expected_sha or admitted.get('limits')!=LIMITS or admitted.get('max_inputs')!=1 or admitted.get('annotation_replay_authorized')is not False:raise RuntimeError('Separate source-specific one repaired-session admission required')
 if read(bind(admitted['preflight_actual_exit'])).get('actual_exit_code')!=0:raise RuntimeError('Fresh preflight actual0 required')
 bind(admitted['preflight_receipt']);return plan,recipe,admitted
def request_gate(request):
 for key in('input_plan','source_manifest','protocol_admission','selected_inputs'):bind(request[key])
 plan,recipe,admitted=plan_gate(request['input_plan']['path'],request['input_plan']['sha256']);runtime_gate(request,recipe)
 if request.get('resource_method_amendment')!=plan['method_amendment'] or request['source_manifest']!=plan['source_manifest'] or request['protocol_admission']!=row(ADMISSION) or request['selected_inputs']!=recipe['selected_inputs'] or request.get('accession')!=ACC:raise RuntimeError('Repair own authority/input differs')
 return plan,{**recipe,'input':recipe['inputs'][0]},admitted
def phase_commit_gate(plan,request,artifacts,annotation_commit,search_commit):
 acc=request['accession']
 if artifacts['annotation_commit']!=plan['reused_annotation_commit'] or annotation_commit!=annotation_gate(plan):raise RuntimeError('Only exact Root-reviewed old annotation may be reused')
 for commit,plan_sha,source_sha in ((annotation_commit,plan['prior_continuation_plan']['sha256'],plan['prior_source_manifest']['sha256']),(search_commit,request['input_plan']['sha256'],request['source_manifest']['sha256'])):
  if commit.get('accession')!=acc or commit.get('input_plan_sha256')!=plan_sha or commit.get('source_manifest_sha256')!=source_sha or commit.get('selected_faa')!=artifacts['selected_faa']:raise RuntimeError('Phase-specific old annotation/new search provenance differs')
  verify_manifest(bind(commit['manifest']).parent,read(bind(commit['manifest'])))
