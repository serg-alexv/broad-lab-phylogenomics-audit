"""HELD future shared-query profile: one global search, genuine per-row model units."""
from pathlib import Path
import hashlib,math,os,re,sys
import checkm2_phase_separated_common_P20 as old
R=old.R;path=old.path;sha=old.sha;read=old.read;save=old.save;row=old.row;bind=old.bind
manifest=old.manifest;verify_manifest=old.verify_manifest;unit_closed=old.unit_closed;group_receipts_closed=old.group_receipts_closed;pending_is_current=old.pending_is_current;runtime_gate=old.runtime_gate
ROLE='CONTINUOUS_QUEUE_SHARED_INDEX8_OWN_ROW_QC_V001'
FIXED={'cpu_affinity_max':2,'stock_threads':1,'sum_group_RSS_bytes':2147483648,'linux_available_minimum_bytes':1073741824,'disk_reserve_bytes':42949672960}
ROW_FIELDS={'unit_annotation':'per_input_annotation_seconds','unit_resume':'per_input_resume_seconds','unit_feature_validation':'per_input_validation_seconds'}
SHARED_FIELDS={'unit_shared_diamond':'shared_search_seconds','unit_shared_search_validation':'shared_search_validation_seconds','unit_shared_control_comparison':'shared_control_comparison_seconds','unit_stock_batch':'batch_stock_seconds','unit_batch_projection':'batch_projection_seconds'}
MAXIMUM={'unit_annotation':180,'unit_resume':600,'unit_feature_validation':3600,'unit_shared_diamond':10800,'unit_shared_search_validation':3600,'unit_shared_control_comparison':3600,'unit_stock_batch':600,'unit_batch_projection':1200}
PLAN_PATH=None;PLAN_SHA=None;COUNT=0;LIMITS={};ROW_UNITS={};SHARED_UNITS={};UNITS={}
E=R/'evidence/checkm2_campaign_index8_v003/UNCONFIGURED';OUT=R/'analysis/checkm2_campaign_index8_v003/UNCONFIGURED'
STATE=E/'progress.json';STEP=E/'step.json';LAUNCH=E/'native_owner.json';ADMISSION=E/'ROOT_ADMISSION_REQUIRED.json';STOP=R/'state/STOP_CHECKM2_QC_PERSISTENT_V001';UNRESOLVED_HANDOFF=E/'unresolved_ownership_handoff.json'

def sha(value):
 h=hashlib.sha256()
 with path(value).open('rb')as f:
  for data in iter(lambda:f.read(4096),b''):h.update(data)
 return h.hexdigest()

def row(value):
 p=path(value);return {'path':p.relative_to(R).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size}

def bind(value):
 p=path(value['path'])
 if sha(p)!=value['sha256']or ('bytes'in value and p.stat().st_size!=value['bytes']):raise RuntimeError('Bound continuous-QC artifact differs')
 return p

def configure(plan_path,expected_sha):
 global PLAN_PATH,PLAN_SHA,COUNT,LIMITS,ROW_UNITS,SHARED_UNITS,UNITS,E,OUT,STATE,STEP,LAUNCH,ADMISSION,STOP,UNRESOLVED_HANDOFF,ROOT_REQUEST
 p=path(plan_path)
 if sha(p)!=expected_sha:raise RuntimeError('Delegated immutable cohort plan changed')
 plan=read(p);names=plan.get('accessions',[]);cohort=plan.get('cohort_id');controls=plan.get('controls',[]);limits=plan['limits']
 if plan.get('schema')!='TREE2_CAMPAIGN_SHARED_INDEX8_INPUT_PLAN_V003'or not isinstance(cohort,str)or not re.fullmatch(r'[a-zA-Z0-9_-]{8,80}',cohort)or not 1<=len(names)<=20 or len(set(names))!=len(names)or not 1<=len(controls)<=2:raise RuntimeError('Exact <=20 and1/2 controls required')
 fields={**ROW_FIELDS,**SHARED_FIELDS};units={n:limits.get(k)for n,k in fields.items()}
 if any(type(v)not in(int,float)or not math.isfinite(v)or not 0<v<=MAXIMUM[n]for n,v in units.items()):raise RuntimeError('Finite original phase ceilings required')
 if limits['per_input_scientific_seconds']!=math.fsum(units[n]for n in ROW_FIELDS)or not 0<limits['cohort_scientific_seconds']<=len(names)*limits['per_input_scientific_seconds']+math.fsum(units[n]for n in SHARED_FIELDS):raise RuntimeError('One global debit plus row budgets required')
 if PLAN_SHA is not None and(PLAN_SHA!=expected_sha or PLAN_PATH!=p):raise RuntimeError('Previous cohort must be explicitly closed at unit level before switching')
 ROOT_REQUEST=read(bind(plan['parent_runtime_request']));E=path(ROOT_REQUEST['native_launch']['path']).parent;OUT=path(plan['run_directory'])
 PLAN_PATH=p;PLAN_SHA=expected_sha;COUNT=len(names);LIMITS=limits;ROW_UNITS={n:units[n]for n in ROW_FIELDS};SHARED_UNITS={n:units[n]for n in SHARED_FIELDS};UNITS=units
 STATE=E/'progress.json';STEP=E/'step.json';LAUNCH=path(ROOT_REQUEST['native_launch']['path']);ADMISSION=path(ROOT_REQUEST['protocol_admission']['path']);STOP=path(read(ADMISSION)['scoped_stop']);UNRESOLVED_HANDOFF=E/'unresolved_ownership_handoff.json'
 plan['_sha']=expected_sha;plan['_row']=row(p)
 return plan


def configure_argv(argv=None):
 args=list(sys.argv[1:]if argv is None else argv)
 if '--request'in args and '--request-sha256'in args:
  p=path(args[args.index('--request')+1])
  if sha(p)!=args[args.index('--request-sha256')+1]:raise RuntimeError('Trusted cohort phase request differs')
  request=read(p)
  if 'input_plan'in request:configure(request['input_plan']['path'],request['input_plan']['sha256'])
 elif '--input-plan'in args and '--input-plan-sha256'in args:
  p=path(args[args.index('--input-plan')+1])
  if read(p).get('schema')=='TREE2_CAMPAIGN_SHARED_INDEX8_INPUT_PLAN_V003':configure(p,args[args.index('--input-plan-sha256')+1])


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
 # These are the exact uniform919 masks, not a replacement for the independently
 # retained original P20 metadata context in selected_inputs.
 return dict(q['source_masks'])


def prior_debits(plan):
 seen=set();total=0.0
 for ref in plan['prior_debit_artifacts']:
  p=bind(ref)
  if p in seen:raise RuntimeError('Duplicate historical debit binding')
  seen.add(p);u=read(p);n=u.get('elapsed_seconds')
  if type(n)not in(int,float)or not math.isfinite(n)or n<0 or u.get('owned_group_empty')is not True or u.get('remaining_owned_processes')!=[] or type(u.get('exit_code'))is not int:raise RuntimeError('Historical attempt/debit/closure is unknown; no reset')
  total=math.fsum((total,n))
 return total

def legacy_annotation_reuse_gate(plan,acc,item):
 spec=plan['annotation_reuse_by_accession'][acc];commit=read(bind(spec['commit']));authority=read(bind(spec['closed_authority']))
 if authority.get('all_current_and_prior_owner_context_image_IPC_and_three_lease_closure_verified')is not True and authority.get('owned_group_namespace_image_lease_closure_verified')is not True:raise RuntimeError('Original annotation attempt external closure authority required')
 if commit.get('accession')!=acc or commit.get('status')!='P20_ANNOTATION_UNIT0_COMMITTED_PENDING_CONTEXT_CLOSURE' or commit.get('input_plan_sha256')!=spec['original_plan_sha256'] or commit.get('source_manifest_sha256')!=spec['original_source_manifest_sha256']:raise RuntimeError('Original annotation provenance cannot be relabelled')
 verify_manifest(bind(commit['manifest']).parent,read(bind(commit['manifest'])))
 unit=read(bind(commit['unit_execution']));receipt=read(bind(commit['annotation_receipt']))
 if not unit_closed(unit)or receipt['accession']!=acc or receipt['source_fna_sha256']!=item['fasta_sha256']or receipt['faa_sha256']!=commit['selected_faa']['sha256']or commit['source_masks']!=item['source_masks']:raise RuntimeError('Original actual0/FAA/source/masks differ')
 if commit['unit_execution'] not in plan['prior_debit_artifacts']:raise RuntimeError('Reused original annotation debit must remain bound and charged')
 bind(commit['selected_faa']);return commit

def baseline_gate(plan):
 from checkm2_conditional_shared_profile_hook_v001 import conditional_baseline_gate
 return conditional_baseline_gate(plan,read=read,bind=bind,unit_closed=unit_closed)


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
 from checkm2_qc_campaign_data_v001 import campaign_cohort_gate
 data,authority,names=campaign_cohort_gate(plan,read=read,bind=bind)
 for ref in read(bind(plan['source_manifest']))['sources']:bind(ref)
 parent=read(bind(ROOT_REQUEST['parent_plan']))
 job=read(bind(ROOT_REQUEST['root_bulk_job']))
 if job['phase_admission']!=ROOT_REQUEST['protocol_admission']or job['source_manifest']!=plan['source_manifest']or ROOT_REQUEST['protocol_admission']!=plan['campaign_authority']or ROOT_REQUEST['source_manifest']!=plan['source_manifest']:raise RuntimeError('One reviewed delegated owner/source binding differs')
 if authority.get('input_plan_sha256')!=ROOT_REQUEST['parent_plan']['sha256']or authority.get('delegated_from_root_session_admission')is None:raise RuntimeError('Actual Root parent/delegated phase authority required')
 if plan['limits']!=authority['cohort_limits']:raise RuntimeError('Delegated finite cohort limits differ from Root phase admission')
 baseline_gate(plan);registry=read(bind(plan['accepted_registry']));accepted=accepted_gate(plan['accepted_registry']);controls_gate(plan,registry)
 selected=read(bind(plan['selected_inputs']))
 for item in selected['inputs']:
  q=data['source_rows'][item['accession']]
  if item['accession']in accepted or set(q['paired_accessions'])&accepted or item['source_masks']!=canonical_source_masks(q):raise RuntimeError('Accepted donor or source masks changed')
  bind(q['acquisition_receipt'])
 first=read(bind(plan['saved_feature_checkpoint']))
 if first.get('status')!='SAVED_FEATURE_REPAIR_VALIDATED_PENDING_CONTEXT_CLOSURE'or first.get('accession')!='GCF_900636715.1'or first.get('annotation_DIAMOND_or_ML_runs')!=0 or not unit_closed(read(bind(first['new_validation_execution']))):raise RuntimeError('Actual repaired complete saved-feature0 must precede every cohort')
 features=read(bind(first['feature_validation']))
 if (features.get('finite_domain_features'),features.get('exact_FAA_metadata_features'),features.get('independently_recomputed_membership_features'),features.get('membership_mismatches'))!=(21241,22,1220,0):raise RuntimeError('First saved full-feature proof incomplete')
 if UNRESOLVED_HANDOFF.exists()or list((E/'unresolved_ownership').glob('*.json')):raise RuntimeError('Unresolved ownership blocks continuation')
 if plan['scientific_recipe']['sha256']!='78e6bceffc1b86cbb9d2a49c85874730a80d744739e6fa638e2087423aa24a02':raise RuntimeError('Unchanged author/model/DB recipe required')
 template=read(bind(plan['scientific_recipe']))
 if template['runtime_binding']!=plan['runtime_binding']:raise RuntimeError('Accepted runtime/DB/model binding differs')
 prior_debits(plan)
 recipe={**template,'inputs':selected['inputs'],'controls':plan['controls'],'inference_order':names,'selected_inputs':plan['selected_inputs'],'role':ROLE,'limits':LIMITS,'phases':UNITS}
 return plan,recipe,authority


def shared_inputs_gate(plan,recipe,query_inputs):
 expected=plan['accessions']+[x['accession']for x in plan['controls']]
 if len(query_inputs)>22 or [x['accession']for x in query_inputs]!=expected or len(set(expected))!=len(expected):raise RuntimeError('Exact<=20fresh+1/2control combined author-query order required')
 for i,entry in enumerate(query_inputs):
  acc=entry['accession']
  for key in('selected_faa','annotation_receipt','annotation_unit_execution','annotation_commit'):bind(entry[key])
  if not annotation_execution_closed(read(bind(entry['annotation_unit_execution']))):raise RuntimeError('Each query must originate from genuine annotation0')
  if i<COUNT:
   if entry.get('role')!='FRESH':raise RuntimeError('Fresh query role differs')
   item=recipe['inputs'][i];ann=read(bind(entry['annotation_commit']))
   if ann!=annotation_reuse_gate(plan,acc,item):raise RuntimeError('Actual closed uniform annotation cache binding differs')
   if ann['accession']!=acc or ann['selected_faa']!=entry['selected_faa']or ann['annotation_receipt']!=entry['annotation_receipt']or ann['unit_execution']!=entry['annotation_unit_execution']:raise RuntimeError('Own query FAA/annotation association differs')
  elif entry!=plan['controls'][i-COUNT]:raise RuntimeError('Exact accepted control query inventory differs')
 return expected

def request_gate(request):
 for key in('input_plan','source_manifest','protocol_admission','selected_inputs'):bind(request[key])
 plan,recipe,admitted=plan_gate(request['input_plan']['path'],request['input_plan']['sha256']);runtime_gate(request,recipe)
 if request.get('resource_method_amendment')!=plan['method_amendment']:raise RuntimeError('Explicit shared index8 resource-method amendment differs')
 if request['source_manifest']!=plan['source_manifest']or request['protocol_admission']!=row(ADMISSION)or request['selected_inputs']!=plan['selected_inputs']:raise RuntimeError('Current shared phase authority/source differs')
 if request['request_schema']=='TREE2_QC_STOCK_BATCH_PROJECTION_REQUEST_V001':
  if not set(request['accessions'])<=set(plan['accessions']):raise RuntimeError('Foreign stock projection member')
  return plan,recipe,admitted
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
ROOT_REQUEST=None
configure_argv()


def resource_policy():
 from checkm2_qc_persistent_common_v002 import resource_policy as owner_policy
 return owner_policy(ROOT_REQUEST)

def annotation_reuse_gate(plan,acc,item):
 from checkm2_uniform_annotation_cache_QC_v001 import uniform_annotation_gate
 descriptor=read(path(plan['run_directory'])/'rows'/acc/'annotation_commit.json')
 uniform_annotation_gate(plan,item,descriptor,read=read,bind=bind)
 return descriptor

def annotation_execution_closed(value):
 from checkm2_uniform_annotation_cache_QC_v001 import annotation_execution_closed as predicate
 return predicate(value)

def validate_query_annotation(plan,entry,proteins):
 acc=entry['accession'];receipt=read(bind(entry['annotation_receipt']))
 if acc in plan['accessions']:
  item=next(x for x in read(bind(plan['selected_inputs']))['inputs']if x['accession']==acc)
  descriptor=annotation_reuse_gate(plan,acc,item)
  if descriptor['selected_faa']!=entry['selected_faa']or descriptor['annotation_receipt']!=entry['annotation_receipt']or descriptor['unit_execution']!=entry['annotation_unit_execution']or receipt['protein_count']!=len(proteins):raise RuntimeError('Own genuine uniform FAA/receipt/unit/count differs')
 else:
  from checkm2_protein_helpers_v001 import sequence_receipt
  if receipt['accession']!=acc or receipt['faa_sha256']!=entry['selected_faa']['sha256']or receipt['protein_sequences']!=sequence_receipt(proteins):raise RuntimeError('Exact accepted legacy-control FAA/header/sequence differs')
 return True

def batch_projection_gate(plan,request,artifacts):
 batch=read(bind(artifacts['batch_prediction_commit']));projection=read(bind(artifacts['batch_projection_commit']))
 if batch.get('status')!='SUPPORTED_STOCK_BATCH0_PENDING_PROJECTION_AND_CONTEXT_CLOSURE'or batch['input_plan_sha256']!=request['input_plan']['sha256']or batch['source_manifest_sha256']!=request['source_manifest']['sha256']or batch['shared_search_commit']!=artifacts['shared_search_commit']:raise RuntimeError('Actual current shared stock-batch source differs')
 if batch['stock_batch_execution']!=artifacts['quality_unit_execution']or not unit_closed(read(bind(batch['stock_batch_execution']))):raise RuntimeError('One genuine global stock-batch0 required, no per-row model0')
 if read(bind(batch['stock_batch_execution'])).get('declared_unit')!='unit_stock_batch'or path(batch['stock_batch_execution']['path']).parent.name!='unit_stock_batch':raise RuntimeError('Actual global stock unit identity required')
 if projection.get('status')!='BATCH_STOCK_FEATURE_ROWS_PROJECTED_PENDING_UNIT_AND_CONTEXT_CLOSURE'or projection['batch_prediction_commit']!=artifacts['batch_prediction_commit']or projection['stock_batch_execution']!=batch['stock_batch_execution']or projection['accessions']!=batch['accessions']or not unit_closed(read(bind(artifacts['batch_projection_execution']))):raise RuntimeError('One genuine own hash-first projection0 required')
 if projection['raw_batch_pickle']!=batch['raw_pickle']or projection['raw_batch_report']!=batch['quality_report']:raise RuntimeError('Original stock batch inputs changed')
 bind(batch['raw_pickle']);bind(batch['quality_report'])
 if read(bind(artifacts['batch_projection_execution'])).get('declared_unit')!='unit_batch_projection':raise RuntimeError('Actual global file projection identity required')
 own=[x for x in projection['rows']if x['accession']==request['accession']]
 if len(own)!=1 or own[0]['raw_pickle']!=artifacts['raw_pickle']or own[0]['quality_report']!=artifacts['quality_report']:raise RuntimeError('Exact projected own Name/pickle/report join required')
 shared_qualification_gate(plan,request['shared_qualification_commit'],artifacts['shared_search_commit'])
 return own[0]

def batch_feature_result_gate(request,result):
 if 'batch_prediction_commit'in request['artifacts']:
  projection=read(bind(request['artifacts']['batch_projection_commit']));own=next(x for x in projection['rows']if x['accession']==request['accession'])
  if own['canonical_float64_le_row_sha256']!=result['canonical_float64_le_row_sha256']:raise RuntimeError('Projection changed exact21241 own canonical values')
  result['quality_execution_scope']='ONE_GLOBAL_SUPPORTED_STOCK_BATCH_EXIT0_NOT_PER_ROW_MODEL_EXIT'
  result['batch_prediction_commit']=request['artifacts']['batch_prediction_commit'];result['batch_projection_commit']=request['artifacts']['batch_projection_commit'];result['batch_projection_execution']=request['artifacts']['batch_projection_execution']

def own_source_projection(item,report):
 if report['raw_report']['Name']!=item['accession']:raise RuntimeError('Exact own report/source name join required')
 return {'original_source_context':item,'source_holds_preserved':item['source_holds_preserved'],'source_hold_active':bool(item['source_holds_preserved']),'numeric_benchmark_status':'MEASURED_ONLY_NOT_A_PANEL_PASS','source_taxonomy_acceptance':'NOT_GRANTED','production_acceptance':'NOT_GRANTED'}

def shared_qualification_gate(plan,reference,shared_reference):
 qualified=read(bind(reference))
 if qualified.get('shared_search_commit')!=shared_reference or not unit_closed(read(bind(qualified['control_comparison_execution']))):raise RuntimeError('Current shared controls must have actual0 before batch inference')
 comparison=read(bind(qualified['control_comparison']))
 if comparison.get('status')!='ALL_ACCEPTED_SERIAL_CONTROL_RAW_MULTISET_MATCHES'or comparison.get('shared_search_commit')!=shared_reference or [x['accession']for x in comparison['matches']]!=[x['accession']for x in plan['controls']]or any(x.get('full12field_multiplicity_match')is not True for x in comparison['matches']):raise RuntimeError('Current SAME8 full12/multiplicity raw-control gate failed')
 initial=qualified if qualified.get('status')=='FIRST_OWN_FEATURE_AND_REAL_CONTROLS_QUALIFIED_PENDING_CONTEXT_CLOSURE'else read(bind(qualified['initial_in_session_profile']))
 if initial.get('status')!='FIRST_OWN_FEATURE_AND_REAL_CONTROLS_QUALIFIED_PENDING_CONTEXT_CLOSURE'or initial.get('campaign_authority')!=plan['campaign_authority']:raise RuntimeError('Same admitted session first own validated profile required')
 first=read(bind(initial['first_row_commit']));feature=read(bind(first['feature_validation']))
 if (feature.get('finite_domain_features'),feature.get('exact_FAA_metadata_features'),feature.get('independently_recomputed_membership_features'),feature.get('membership_mismatches'))!=(21241,22,1220,0):raise RuntimeError('Initial own full feature math required, independent of95/5 estimate outcome')
 for key in('unit_resume','unit_feature_validation'):
  if not unit_closed(read(bind(first['per_row_unit_executions'][key]))):raise RuntimeError('Initial actual own model/feature0 required')
 if qualified is not initial and qualified.get('status')!='CURRENT_CONTROLS_AND_INITIAL_IN_SESSION_PROFILE_QUALIFIED_PENDING_CONTEXT_CLOSURE':raise RuntimeError('Unknown in-session conditional qualification')
 return qualified

def reset_closed_cohort(run):
 global PLAN_PATH,PLAN_SHA
 if not all(unit_closed(read(p))for p in path(run).glob('**/unit_*/execution.json'))or budget(run)['known_limit_exceeded']:raise RuntimeError('No data-cohort switch after failed/unknown/over-budget unit')
 PLAN_PATH=None;PLAN_SHA=None
