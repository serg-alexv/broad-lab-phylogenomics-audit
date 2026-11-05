"""HELD future shared-query profile: one global search, genuine per-row model units."""
from pathlib import Path
import hashlib,math,os,re,sys
import checkm2_phase_separated_common_P20 as old
R=old.R;path=old.path;sha=old.sha;read=old.read;save=old.save;row=old.row;bind=old.bind
manifest=old.manifest;verify_manifest=old.verify_manifest;unit_closed=old.unit_closed;group_receipts_closed=old.group_receipts_closed;pending_is_current=old.pending_is_current;runtime_gate=old.runtime_gate
ROLE='CAMPAIGN_SHARED_INDEX8_OWN_ROW_QC_V003'
FIXED={'cpu_affinity_max':2,'stock_threads':1,'sum_group_RSS_bytes':2147483648,'linux_available_minimum_bytes':1073741824,'disk_reserve_bytes':42949672960}
ROW_FIELDS={'unit_annotation':'per_input_annotation_seconds','unit_resume':'per_input_resume_seconds','unit_feature_validation':'per_input_validation_seconds'}
SHARED_FIELDS={'unit_shared_diamond':'shared_search_seconds','unit_shared_search_validation':'shared_search_validation_seconds','unit_shared_control_comparison':'shared_control_comparison_seconds'}
MAXIMUM={'unit_annotation':180,'unit_resume':600,'unit_feature_validation':3600,'unit_shared_diamond':10800,'unit_shared_search_validation':3600,'unit_shared_control_comparison':3600}
PLAN_PATH=None;PLAN_SHA=None;COUNT=0;LIMITS={};ROW_UNITS={};SHARED_UNITS={};UNITS={}
E=R/'evidence/checkm2_campaign_index8_v003/UNCONFIGURED';OUT=R/'analysis/checkm2_campaign_index8_v003/UNCONFIGURED'

def configure(plan_path,expected_sha):
 global PLAN_PATH,PLAN_SHA,COUNT,LIMITS,ROW_UNITS,SHARED_UNITS,UNITS,E,OUT,STATE,STEP,LAUNCH,ADMISSION,STOP,UNRESOLVED_HANDOFF
 p=path(plan_path)
 if sha(p)!=expected_sha:raise RuntimeError('Shared profile plan changed')
 plan=read(p);names=plan.get('accessions',[]);cohort=plan.get('cohort_id');controls=plan.get('controls',[]);limits=plan.get('limits',{})
 if plan.get('schema')!='TREE2_CAMPAIGN_SHARED_INDEX8_INPUT_PLAN_V003'or not isinstance(cohort,str)or not re.fullmatch(r'[a-zA-Z0-9_-]{8,80}',cohort)or not 1<=len(names)<=20 or len(set(names))!=len(names)or not 1<=len(controls)<=2:raise RuntimeError('One to20 fresh inputs plus1/2 controls required')
 if any(limits.get(k)!=v for k,v in FIXED.items()):raise RuntimeError('Fixed scientific resource gates changed')
 fields={**ROW_FIELDS,**SHARED_FIELDS};units={n:limits.get(k)for n,k in fields.items()}
 if any(type(v)not in(int,float)or not math.isfinite(v)or not 0<v<=MAXIMUM[n]for n,v in units.items()):raise RuntimeError('Finite row/shared phase allocation invalid')
 row_total=math.fsum(units[n]for n in ROW_FIELDS);shared_total=math.fsum(units[n]for n in SHARED_FIELDS)
 if limits.get('per_input_scientific_seconds')!=row_total or not 0<limits.get('cohort_scientific_seconds',0)<=len(names)*row_total+shared_total or not 1240<limits.get('cold_session_seconds',0)<=40800:raise RuntimeError('Finite one-global-search aggregate/cold budget invalid')
 if PLAN_SHA is not None and(PLAN_SHA!=expected_sha or PLAN_PATH!=p):raise RuntimeError('Cannot switch an active shared cohort')
 PLAN_PATH=p;PLAN_SHA=expected_sha;COUNT=len(names);LIMITS=limits;ROW_UNITS={n:units[n]for n in ROW_FIELDS};SHARED_UNITS={n:units[n]for n in SHARED_FIELDS};UNITS=units
 E=R/'evidence/checkm2_campaign_index8_v003'/cohort;OUT=R/'analysis/checkm2_campaign_index8_v003'/cohort
 STATE=E/'progress.json';STEP=E/'step.json';LAUNCH=E/'native_scientific_launch.json';ADMISSION=E/'Root_runtime_admission.json';STOP=R/'state'/('STOP_CHECKM2_CAMPAIGN_SHARED_'+cohort);UNRESOLVED_HANDOFF=E/'unresolved_ownership_handoff.json'
 return plan

def configure_argv(argv=None):
 args=list(sys.argv[1:]if argv is None else argv)
 if '--input-plan'in args and '--input-plan-sha256'in args:configure(args[args.index('--input-plan')+1],args[args.index('--input-plan-sha256')+1])
 elif '--request'in args and '--request-sha256'in args:
  p=path(args[args.index('--request')+1])
  if sha(p)!=args[args.index('--request-sha256')+1]:raise RuntimeError('Trusted shared request changed')
  r=read(p);configure(r['input_plan']['path'],r['input_plan']['sha256'])
 elif os.environ.get('TREE2_QC_BATCH_PLAN')or os.environ.get('TREE2_QC_BATCH_PLAN_SHA256'):configure(os.environ['TREE2_QC_BATCH_PLAN'],os.environ['TREE2_QC_BATCH_PLAN_SHA256'])

def stop():
 if any(p.exists()for p in(STOP,R/'state/STOP',R/'state/STOP_CHECKM2_PILOT',R/'state/STOP_CHECKM2_CAMPAIGN_INDEX8')):raise InterruptedError('Shared/global/biological STOP')

def bound_evidence(value):
 if not value:raise RuntimeError('Missing closed authority evidence')
 for ref in value:bind(ref)

def accepted_gate(ref):
 registry=read(bind(ref));entries=registry['rows']+[registry['additional_baseline']];ids=set();aliases=set();dna=set()
 for item in entries:
  acc=item['accession']
  if acc in ids:raise RuntimeError('Duplicate accepted method accession')
  ids.add(acc)
  for key in('commit','feature_validation'):
   if key in item and isinstance(item[key],dict):bind(item[key])
  aliases.update(item.get('paired_accessions',[]))
 if set(registry['accepted_unique_method_accessions'])!=ids:raise RuntimeError('Accepted method registry identity set differs')
 return ids|aliases

def canonical_source_masks(q):
 # Queue fields remain exact; retain extra source/hold context from the immutable
 # original P20 recipe for its reserved members, including the reused annotation.
 ref={'path':'metadata/checkm2_phase_separated_recipe_P20.json','sha256':'78e6bceffc1b86cbb9d2a49c85874730a80d744739e6fa638e2087423aa24a02'}
 template=read(bind(ref));matches=[x for x in template['inputs']if x['accession']==q['accession']]
 if not matches:return dict(q['source_masks'])
 if len(matches)!=1:raise RuntimeError('Original source context accession is ambiguous')
 old_item=matches[0];masks=old_item['source_masks']
 if any(masks.get(k)!=v for k,v in q['source_masks'].items())or old_item['source_holds_preserved']!=q['source_holds_preserved']or old_item['source_pending_reasons']!=q['source_pending_reasons']or masks.get('source_holds')!=q['source_holds_preserved']:raise RuntimeError('Canonical and original source/hold context disagree')
 return dict(masks)

def prior_debits(plan):
 seen=set();total=0.0
 for ref in plan['prior_debit_artifacts']:
  p=bind(ref)
  if p in seen:raise RuntimeError('Duplicate historical debit binding')
  seen.add(p);u=read(p);n=u.get('elapsed_seconds')
  if type(n)not in(int,float)or not math.isfinite(n)or n<0 or u.get('owned_group_empty')is not True or u.get('remaining_owned_processes')!=[] or type(u.get('exit_code'))is not int:raise RuntimeError('Historical attempt/debit/closure is unknown; no reset')
  total=math.fsum((total,n))
 return total

def annotation_reuse_gate(plan,acc,item):
 spec=plan['annotation_reuse_by_accession'][acc];commit=read(bind(spec['commit']));authority=read(bind(spec['closed_authority']))
 if authority.get('all_current_and_prior_owner_context_image_IPC_and_three_lease_closure_verified')is not True and authority.get('owned_group_namespace_image_lease_closure_verified')is not True:raise RuntimeError('Original annotation attempt external closure authority required')
 if commit.get('accession')!=acc or commit.get('status')!='P20_ANNOTATION_UNIT0_COMMITTED_PENDING_CONTEXT_CLOSURE' or commit.get('input_plan_sha256')!=spec['original_plan_sha256'] or commit.get('source_manifest_sha256')!=spec['original_source_manifest_sha256']:raise RuntimeError('Original annotation provenance cannot be relabelled')
 verify_manifest(bind(commit['manifest']).parent,read(bind(commit['manifest'])))
 unit=read(bind(commit['unit_execution']));receipt=read(bind(commit['annotation_receipt']))
 if not unit_closed(unit)or receipt['accession']!=acc or receipt['source_fna_sha256']!=item['fasta_sha256']or receipt['faa_sha256']!=commit['selected_faa']['sha256']or commit['source_masks']!=item['source_masks']:raise RuntimeError('Original actual0/FAA/source/masks differ')
 if commit['unit_execution'] not in plan['prior_debit_artifacts']:raise RuntimeError('Reused original annotation debit must remain bound and charged')
 bind(commit['selected_faa']);return commit

def baseline_gate(plan):
 a=read(bind(plan['serial_index8_baseline_acceptance']))
 if a.get('status')!='ROOT_ACCEPTED_CLOSED_INDEX8_METHOD_FOR_BULK'or type(a.get('actual_native_exit_code'))is not int or type(a.get('actual_WSL_exit_code'))is not int or a.get('actual_native_exit_code')!=0 or a.get('actual_WSL_exit_code')!=0 or a.get('all_owner_context_and_lease_closure_verified')is not True or a.get('own_feature_math_verified')is not True or a.get('index_chunks')!=8:raise RuntimeError('Current closed accepted serial-index8 profile must exist before future batched admission')
 bound_evidence(a.get('closure_and_result_evidence'));return a

def controls_gate(plan,registry):
 entries={x['accession']:x for x in registry['rows']+[registry['additional_baseline']]};names=[]
 for spec in plan['controls']:
  acc=spec['accession'];names.append(acc)
  if acc not in entries or acc in plan['accessions']or spec.get('role')!='SEARCH_ONLY_CONTROL'or entries[acc].get('authority')!=spec['accepted_method_authority']:raise RuntimeError('Control must be an exact disjoint accepted serial donor')
  bind(spec['accepted_method_authority']);accepted=read(bind(entries[acc]['commit']))
  if accepted.get('accession')!=acc or accepted.get('diamond_commit')!=spec['serial_search_commit']or accepted.get('annotation_commit')!=spec['annotation_commit']:raise RuntimeError('Control search and annotation must belong to the actual accepted registry row')
  annotation=read(bind(spec['annotation_commit']))
  if annotation.get('accession')!=acc or annotation.get('selected_faa')!=spec['selected_faa']or annotation.get('annotation_receipt')!=spec['annotation_receipt']or annotation.get('unit_execution')!=spec['annotation_unit_execution']:raise RuntimeError('Accepted control original annotation/FAA/unit join differs')
  commit=read(bind(spec['serial_search_commit']));receipt=read(bind(commit['diamond_receipt']))
  if commit['accession']!=acc or commit['selected_faa']!=spec['selected_faa']or commit['raw_diamond']!=spec['reference_raw_diamond']or receipt['index_chunks']!=8 or receipt['block_size']!=0.5 or receipt['threads']!=1 or receipt['database']!=plan['runtime_binding']['database']:raise RuntimeError('Exact accepted serial-index8 FAA/query/DB/raw reference required')
  for key in('unit_execution','validation_unit_execution'):
   if not unit_closed(read(bind(commit[key]))):raise RuntimeError('Actual serial reference search/validation0 required')
  for key in('selected_faa','annotation_receipt','annotation_unit_execution','annotation_commit','reference_raw_diamond'):bind(spec[key])
  if not unit_closed(read(bind(spec['annotation_unit_execution']))):raise RuntimeError('Accepted control annotation0 required, no regeneration')
 if len(set(names))!=len(names):raise RuntimeError('Duplicate controls')
 aliases={v for x in plan['controls']for v in x.get('paired_accessions',[])}
 if aliases&set(plan['accessions']):raise RuntimeError('Control alias overlaps fresh input')
 return names

def plan_gate(plan_path,expected_sha,require_admission=True,closed_finalization=False):
 plan=configure(plan_path,expected_sha);stop()
 if plan.get('role')!=ROLE:raise RuntimeError('Shared profile role differs')
 for ref in read(bind(plan['source_manifest']))['sources']:bind(ref)
 if plan['canonical_queue']['sha256']!='44d456e79af0f84a2c35a2dd3e1b6f8cd748df31d17ee8273becca7a765b75f1':raise RuntimeError('Canonical chosen/source scope differs')
 bind(plan['method_amendment']);baseline_gate(plan);registry=read(bind(plan['accepted_registry']));accepted=accepted_gate(plan['accepted_registry']);controls=controls_gate(plan,registry)
 authority=read(bind(plan['cohort_authority']))
 if authority.get('status')!='ROOT_APPROVED_ONE_FUTURE_SHARED_INDEX8_COHORT' or authority.get('accessions')!=plan['accessions']or authority.get('controls')!=plan['controls']or authority.get('limits')!=LIMITS or authority.get('prior_debit_artifacts')!=plan['prior_debit_artifacts']or any(authority.get(k)is not True for k in('shared_search_charged_once','same_cohort_empirical_fit_and_control_gate','accepted_annotation_or_prediction_never_replayed','fallback_only_after_external_closure_and_new_authority','all_prior_claims_allocations_and_debits_retained')):raise RuntimeError('Explicit held-new-profile cohort/source/budget authority required')
 queue=read(bind(plan['canonical_queue']));members={x['accession']:x for x in queue['rows']};selected=read(bind(plan['selected_inputs']))
 context=read(bind(plan['queue_launch_context']));proposal=read(bind(context['queue_proposal']));reservation=read(bind(context['queue_reservation']))
 if context['canonical_QC_queue']!=plan['canonical_queue']or proposal['queue_ids']!=context['queue_ids']or reservation['kind']!='RESERVED'or reservation['proposal_sha256']!=context['queue_proposal']['sha256']:raise RuntimeError('Durable exact queue reservation required')
 names=plan['accessions'];remaining=[x for x in context['queue_ids']if x not in accepted]
 if names!=remaining[:len(names)]or names!=[x['accession']for x in selected['inputs']]:raise RuntimeError('Fresh species-first order changed')
 for item in selected['inputs']:
  q=members[item['accession']]
  if item['accession']in accepted or set(q['paired_accessions'])&accepted or q['source_supported_scope']is not True or q['qc_execution_state']not in('READY_FRESH_QC','RESERVED_P20_UNSTARTED')or item['canonical_queue_row']!=q or item['source_masks']!=canonical_source_masks(q):raise RuntimeError('Accepted/held/source mask state cannot become a fresh row')
  if any(item[k]!=q[k]for k in('species','species_taxid','genus','family','source_pending_reasons','source_holds_preserved','metadata_qc'))or item['fasta_sha256']!=q['FNA_from_receipt']['sha256']:raise RuntimeError('Own source identity/context differs')
  bind(q['acquisition_receipt'])
  if item['accession']in plan.get('annotation_reuse_by_accession',{}):annotation_reuse_gate(plan,item['accession'],item)
 prior_debits(plan)
 if UNRESOLVED_HANDOFF.exists()or list((E/'unresolved_ownership').glob('*.json')):raise RuntimeError('Unknown owner blocks fresh profile')
 token=os.environ.get('TREE2_CHECKM2_PILOT_LAUNCH_TOKEN')
 for p in OUT.glob('sessions/*/once_claim.json'):
  prior=read(p)
  if prior['input_plan_sha256']!=expected_sha or(not closed_finalization and prior['native_launch_token']!=token):raise RuntimeError('Shared profile once claim consumed; no automatic replay/fallback')
 if plan['scientific_recipe']['sha256']!='78e6bceffc1b86cbb9d2a49c85874730a80d744739e6fa638e2087423aa24a02':raise RuntimeError('Unchanged author/model/DB recipe required')
 template=read(bind(plan['scientific_recipe']))
 if template['runtime_binding']!=plan['runtime_binding']:raise RuntimeError('Exact accepted runtime/binary/DB controls required')
 recipe={**template,'inputs':selected['inputs'],'controls':plan['controls'],'inference_order':names,'selected_inputs':plan['selected_inputs'],'role':ROLE,'limits':LIMITS,'phases':UNITS}
 if not require_admission:return plan,recipe,None
 admitted=read(ADMISSION)
 if admitted.get('status')!='ROOT_ADMITTED_ONE_SHARED_INDEX8_COHORT_V003'or admitted.get('input_plan_sha256')!=expected_sha or admitted.get('source_manifest_sha256')!=plan['source_manifest']['sha256']or admitted.get('limits')!=LIMITS or admitted.get('max_inputs')!=COUNT or admitted.get('same_cohort_profile_qualification')is not True:raise RuntimeError('Separate future empirical shared-profile admission required')
 if read(bind(admitted['preflight_actual_exit'])).get('actual_exit_code')!=0:raise RuntimeError('Fresh actual preflight0 required')
 bind(admitted['preflight_receipt']);return plan,recipe,admitted

def shared_inputs_gate(plan,recipe,query_inputs):
 expected=plan['accessions']+[x['accession']for x in plan['controls']]
 if len(query_inputs)>22 or [x['accession']for x in query_inputs]!=expected or len(set(expected))!=len(expected):raise RuntimeError('Exact<=20fresh+1/2control combined author-query order required')
 for i,entry in enumerate(query_inputs):
  acc=entry['accession']
  for key in('selected_faa','annotation_receipt','annotation_unit_execution','annotation_commit'):bind(entry[key])
  if not unit_closed(read(bind(entry['annotation_unit_execution']))):raise RuntimeError('Each query must originate from genuine annotation0')
  if i<COUNT:
   if entry.get('role')!='FRESH':raise RuntimeError('Fresh query role differs')
   item=recipe['inputs'][i];ann=read(bind(entry['annotation_commit']))
   if acc in plan.get('annotation_reuse_by_accession',{}):
    if ann!=annotation_reuse_gate(plan,acc,item):raise RuntimeError('Exact closed annotation reuse required')
   elif ann['input_plan_sha256']!=PLAN_SHA or ann['source_manifest_sha256']!=plan['source_manifest']['sha256']:raise RuntimeError('Fresh annotation current source differs')
   if ann['accession']!=acc or ann['selected_faa']!=entry['selected_faa']or ann['annotation_receipt']!=entry['annotation_receipt']or ann['unit_execution']!=entry['annotation_unit_execution']:raise RuntimeError('Own query FAA/annotation association differs')
  elif entry!=plan['controls'][i-COUNT]:raise RuntimeError('Exact accepted control query inventory differs')
 return expected

def request_gate(request):
 for key in('input_plan','source_manifest','protocol_admission','selected_inputs'):bind(request[key])
 plan,recipe,admitted=plan_gate(request['input_plan']['path'],request['input_plan']['sha256']);runtime_gate(request,recipe)
 if request.get('resource_method_amendment')!=plan['method_amendment']:raise RuntimeError('Explicit shared index8 resource-method amendment differs')
 if request['source_manifest']!=plan['source_manifest']or request['protocol_admission']!=row(ADMISSION)or request['selected_inputs']!=plan['selected_inputs']:raise RuntimeError('Current shared phase authority/source differs')
 if request['request_schema'] in('TREE2_CAMPAIGN_SHARED_DIAMOND_REQUEST_V003','TREE2_CAMPAIGN_SHARED_CONTROL_REQUEST_V003'):
  shared_inputs_gate(plan,recipe,request['query_inputs']);return plan,recipe,admitted
 matches=[x for x in recipe['inputs']if x['accession']==request.get('accession')]
 if len(matches)!=1:raise RuntimeError('Own fresh accession required')
 return plan,{**recipe,'input':matches[0]},admitted

def global_commit_gate(plan,request,artifacts):
 shared=read(bind(artifacts['shared_search_commit']));global_request=read(bind(shared['request']))
 if shared.get('status')!='GLOBAL_SHARED_SEARCH_SPLIT_VALIDATED_PENDING_CONTEXT_CLOSURE'or shared.get('input_plan_sha256')!=request['input_plan']['sha256']or shared.get('source_manifest_sha256')!=request['source_manifest']['sha256']:raise RuntimeError('Current shared parent source differs')
 for key,parent in(('global_search_execution','binary_execution'),('global_search_validation_execution','validation_execution'),('split_commit','split_commit')):
  if artifacts[key]!=shared[parent]:raise RuntimeError('One global search/split execution association differs')
 for key in('binary_execution','validation_execution'):
  if not unit_closed(read(bind(shared[key]))):raise RuntimeError('Actual global binary/raw validation0 required')
 _,recipe,_=plan_gate(request['input_plan']['path'],request['input_plan']['sha256'])
 shared_inputs_gate(plan,recipe,global_request['query_inputs'])
 if global_request['input_plan']!=request['input_plan']or global_request['source_manifest']!=request['source_manifest']or global_request['selected_inputs']!=request['selected_inputs']:raise RuntimeError('Merged original query/request current source differs')
 split=read(bind(shared['split_commit']));expected=plan['accessions']+[x['accession']for x in plan['controls']]
 if split.get('status')!='ONE_CLOSED_SEARCH_SPLIT_COMMITTED_NOT_GENOME_QC'or split['declared_accessions']!=expected or split['inputs']['query_fasta']!=shared['merged_query']or split['inputs']['merged_tsv']!=shared['merged_raw']or split['inputs']['search_execution']!=shared['binary_execution']or split['search_debit']['actual_unit_count']!=1:raise RuntimeError('Shared raw/shard/one-global-debit parent differs')
 query=read(bind(shared['query_inventory']))
 if query['query_fasta']!=shared['merged_query']or query['declared_accessions']!=expected:raise RuntimeError('Actual author query inventory binding differs')
 acc=request['accession'];shards=[x for x in split['shards']if x['accession']==acc]
 if len(shards)!=1 or shared['selected_faas'][acc]!=artifacts['selected_faa']or shards[0]['search_binding_id']!=split['search_binding_id']:raise RuntimeError('Own exact shared FAA/query/shard join differs')
 bind(shards[0]['artifact'])
 from checkm2_protein_helpers_v001 import parse_fasta,AA
 proteins=parse_fasta(bind(artifacts['selected_faa']).read_text(),AA)
 own={acc+'\u03a9'+x['id']:{'accession':acc,'length':len(x['sequence']),'sequence_sha256':hashlib.sha256(x['sequence'].encode('ascii')).hexdigest()}for x in proteins}
 actual={k:v for k,v in query['queries'].items()if v['accession']==acc}
 if own!=actual:raise RuntimeError('Own FAA sequence inventory differs from merged original query')
 if acc!=plan['accessions'][0]:shared_qualification_gate(plan,request['shared_qualification_commit'],artifacts['shared_search_commit'])
 return shards[0]

def shared_qualification_gate(plan,reference,shared_reference):
 qualified=read(bind(reference))
 if qualified.get('status')!='FIRST_OWN_FEATURE_AND_REAL_CONTROLS_QUALIFIED_PENDING_CONTEXT_CLOSURE'or qualified.get('shared_search_commit')!=shared_reference:raise RuntimeError('First own prediction/control gate must precede all remaining ML')
 if not unit_closed(read(bind(qualified['control_comparison_execution']))):raise RuntimeError('Actual full control comparison0 required')
 comparison=read(bind(qualified['control_comparison']))
 if comparison.get('status')!='ALL_ACCEPTED_SERIAL_CONTROL_RAW_MULTISET_MATCHES' or comparison.get('shared_search_commit')!=shared_reference or [x['accession']for x in comparison['matches']]!=[x['accession']for x in plan['controls']]or any(x.get('full12field_multiplicity_match')is not True or x.get('reference')!=spec['reference_raw_diamond']for x,spec in zip(comparison['matches'],plan['controls'])):raise RuntimeError('All exact accepted real control matches required')
 first=read(bind(qualified['first_row_commit']));feature=read(bind(first['feature_validation']))
 if first.get('shared_search_commit')!=shared_reference or first['accession']!=plan['accessions'][0]or feature['accession']!=first['accession']or (feature['finite_domain_features'],feature['exact_FAA_metadata_features'],feature['independently_recomputed_membership_features'])!=(21241,22,1220):raise RuntimeError('First genuine own complete feature checkpoint required')
 for key in('unit_resume','unit_feature_validation'):
  if not unit_closed(read(bind(first['per_row_unit_executions'][key]))):raise RuntimeError('Actual first own model/features0 required')
 return qualified

def budget(run):
 run=path(run);commands=set(run.glob('rows/*/unit_*/command.json'))|set(run.glob('shared/unit_*/command.json'));terminals=set(run.glob('rows/*/unit_*/execution.json'))|set(run.glob('shared/unit_*/execution.json'));alloc=set(run.glob('rows/*/unit_*_budget.json'))|set(run.glob('shared/unit_*_budget.json'))
 if terminals!={p.with_name('execution.json')for p in commands}or alloc!={p.parent.parent/(p.parent.name+'_budget.json')for p in commands}:raise RuntimeError('Unknown attempt/global debit; no reset or fallback')
 plan=read(PLAN_PATH);rows={};global_cost={}
 for p in terminals:
  u=read(p);scope=p.parent.parent.name;unit=p.parent.name;n=u.get('elapsed_seconds')
  if type(n)not in(int,float)or not math.isfinite(n)or n<0 or u.get('owned_group_empty')is not True or u.get('remaining_owned_processes')!=[]:raise RuntimeError('Known actual group/debit required')
  if scope=='shared':
   if unit not in SHARED_UNITS or unit in global_cost:raise RuntimeError('Each global unit charged once only')
   global_cost[unit]=n
  else:
   if scope not in plan['accessions']or unit not in ROW_UNITS:raise RuntimeError('No per-row DIAMOND/validation units may be invented')
   rows.setdefault(scope,{})[unit]=n
 per={acc:math.fsum(v.values())for acc,v in rows.items()};row_seconds=math.fsum(per.values());shared_seconds=math.fsum(global_cost.values());used=math.fsum((row_seconds,shared_seconds));prior=prior_debits(plan)
 exceeded=any(n>ROW_UNITS[k]for v in rows.values()for k,n in v.items())or any(n>SHARED_UNITS[k]for k,n in global_cost.items())or any(n>LIMITS['per_input_scientific_seconds']for n in per.values())or used>LIMITS['cohort_scientific_seconds']
 return {'per_row_units_seconds':rows,'input_scientific_seconds':per,'shared_units_seconds_charged_once':global_cost,'shared_scientific_seconds':shared_seconds,'row_scientific_seconds':row_seconds,'cohort_scientific_seconds_debited':used,'remaining_cohort_scientific_seconds':max(0,LIMITS['cohort_scientific_seconds']-used),'known_limit_exceeded':exceeded,'prior_actual_scientific_seconds_retained':prior,'prior_plus_new_actual_scientific_seconds':prior+used,'per_row_search_debits_or_fake_unit_receipts_created':False}

def current_failed_run(step,token,input_plan_sha,protocol_sha):
 locator=OUT/'runs_by_token'/(token+'.json')
 if not locator.exists():return None
 item=read(locator)
 if item['launch_token']!=token or item['input_plan_sha256']!=input_plan_sha or item['protocol_admission_sha256']!=protocol_sha:raise RuntimeError('Shared required token locator differs')
 bind(item['binding']);run=path(item['run_directory'])
 if run.parent!=OUT/'runs'or read(run/'failure.json')['status']!='SHARED_PROFILE_FAILED_NO_AUTOMATIC_REPLAY_OR_FALLBACK':raise RuntimeError('Shared failure evidence differs')
 return run
configure_argv()
