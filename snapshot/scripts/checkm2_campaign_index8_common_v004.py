"""One source cut for serial <=20-genome cohorts; data-only plans, no launch on import."""
from pathlib import Path
import math,os,re,sys
import checkm2_phase_separated_common_P20 as old
R=old.R;path=old.path;sha=old.sha;read=old.read;save=old.save;row=old.row;bind=old.bind
manifest=old.manifest;verify_manifest=old.verify_manifest;unit_closed=old.unit_closed;group_receipts_closed=old.group_receipts_closed;pending_is_current=old.pending_is_current;runtime_gate=old.runtime_gate
ROLE='CAMPAIGN_SERIAL_INDEX8_OWN_ROW_QC_V002'
UNITS={}
FIXED={'cpu_affinity_max':2,'stock_threads':1,'sum_group_RSS_bytes':2147483648,'linux_available_minimum_bytes':1073741824,'disk_reserve_bytes':42949672960}
PHASE_FIELDS={'unit_annotation':'per_input_annotation_seconds','unit_diamond':'per_input_diamond_seconds','unit_saved_search_validation':'per_input_saved_search_validation_seconds','unit_resume':'per_input_resume_seconds','unit_feature_validation':'per_input_validation_seconds'}
PHASE_MAX={'unit_annotation':180,'unit_diamond':3600,'unit_saved_search_validation':3600,'unit_resume':600,'unit_feature_validation':3600,'unit_reference_comparison':3600}
PLAN_PATH=None;PLAN_SHA=None;COUNT=0;LIMITS={};E=R/'evidence/checkm2_campaign_index8_v002/UNCONFIGURED';OUT=R/'analysis/checkm2_campaign_index8_v002/UNCONFIGURED'

def configure(plan_path,expected_sha):
 global PLAN_PATH,PLAN_SHA,COUNT,LIMITS,UNITS,E,OUT,STATE,STEP,LAUNCH,ADMISSION,STOP,UNRESOLVED_HANDOFF
 p=path(plan_path)
 if sha(p)!=expected_sha:raise RuntimeError('Campaign immutable plan hash differs')
 plan=read(p);cohort=plan.get('cohort_id');names=plan.get('accessions',[])
 if plan.get('schema')!='TREE2_CAMPAIGN_INDEX8_INPUT_PLAN_V002' or not isinstance(cohort,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{8,80}',cohort) or not 1<=len(names)<=20 or len(set(names))!=len(names):raise RuntimeError('Campaign plan identity/count invalid')
 limits=plan.get('limits',{})
 if any(limits.get(k)!=v for k,v in FIXED.items()):raise RuntimeError('CPU/RSS/headroom/disk gates unchanged')
 units={name:limits.get(field)for name,field in PHASE_FIELDS.items()}
 if any(type(n)not in(int,float)or not math.isfinite(n)or not 0<n<=PHASE_MAX[name]for name,n in units.items()):raise RuntimeError('Data-bound finite phase ceiling exceeds declared maximum')
 overrides=plan.get('phase_caps_by_accession',{})
 if set(overrides)-set(names):raise RuntimeError('Per-input cap override names an undeclared genome')
 for acc,values in overrides.items():
  if set(values)-set(units)or any(type(n)not in(int,float)or not math.isfinite(n)or not 0<n<=PHASE_MAX[name]for name,n in values.items()):raise RuntimeError('Invalid explicit per-input phase cap')
 largest=max([math.fsum(units.values()),*[math.fsum({**units,**values}.values())for values in overrides.values()]])
 input_cap=limits.get('per_input_scientific_seconds');control=limits.get('reference_control_seconds',0)
 if type(input_cap)not in(int,float)or not math.isfinite(input_cap)or not largest<=input_cap<=math.fsum(PHASE_MAX[n]for n in units):raise RuntimeError('Input finite aggregate must include declared phase ceilings')
 comparison=limits.get('per_reference_comparison_seconds',120)
 if type(comparison)not in(int,float)or not math.isfinite(comparison)or not 0<comparison<=3600:raise RuntimeError('Finite file-only reference comparison limit invalid')
 if (not plan.get('search_only_control')and control!=0)or(plan.get('search_only_control')and not 0<control<=10800):raise RuntimeError('Optional control finite allocation must be explicit')
 total=limits.get('cohort_scientific_seconds');cold=limits.get('cold_session_seconds')
 if type(total)not in(int,float)or not math.isfinite(total)or not 0<total<=len(names)*input_cap+control or type(cold)not in(int,float)or not math.isfinite(cold)or not 1240<cold<=40800:raise RuntimeError('Finite cohort/cold bounds invalid; theoretical phase sum need not fit cold')
 if PLAN_SHA is not None and (PLAN_SHA!=expected_sha or PLAN_PATH!=p):raise RuntimeError('Cannot switch a running cohort')
 UNITS=units
 PLAN_PATH=p;PLAN_SHA=expected_sha;COUNT=len(names);LIMITS=limits
 E=R/'evidence/checkm2_campaign_index8_v002'/cohort;OUT=R/'analysis/checkm2_campaign_index8_v002'/cohort
 STATE=E/'progress.json';STEP=E/'step.json';LAUNCH=E/'native_scientific_launch.json';ADMISSION=E/'Root_runtime_admission.json';STOP=R/'state'/('STOP_CHECKM2_CAMPAIGN_INDEX8_'+cohort);UNRESOLVED_HANDOFF=E/'unresolved_ownership_handoff.json'
 return plan

def phase_cap(name,accession,plan=None):
 plan=read(PLAN_PATH)if plan is None else plan
 default=LIMITS.get('per_reference_comparison_seconds',120)if name=='unit_reference_comparison'else UNITS[name]
 return plan.get('phase_caps_by_accession',{}).get(accession,{}).get(name,default)

def input_cap(accession):
 return LIMITS['reference_control_seconds']if accession=='REFERENCE_CONTROL'else LIMITS['per_input_scientific_seconds']

def configure_argv(argv=None):
 args=list(sys.argv[1:] if argv is None else argv)
 if '--input-plan'in args and '--input-plan-sha256'in args:configure(args[args.index('--input-plan')+1],args[args.index('--input-plan-sha256')+1])
 elif '--request'in args and '--request-sha256'in args:
  p=path(args[args.index('--request')+1])
  if sha(p)!=args[args.index('--request-sha256')+1]:raise RuntimeError('Request changed before cohort configuration')
  request=read(p);configure(request['input_plan']['path'],request['input_plan']['sha256'])
 elif os.environ.get('TREE2_QC_BATCH_PLAN')or os.environ.get('TREE2_QC_BATCH_PLAN_SHA256'):
  configure(os.environ['TREE2_QC_BATCH_PLAN'],os.environ['TREE2_QC_BATCH_PLAN_SHA256'])

def stop():
 if any(p.exists()for p in(R/'state/STOP',R/'state/STOP_CHECKM2_PILOT',R/'state/STOP_CHECKM2_CAMPAIGN_INDEX8',STOP)):raise InterruptedError('Campaign/global/biological STOP')

def bound_evidence(value):
 if not value:raise RuntimeError('Missing closed authority evidence')
 for ref in value:bind(ref)

def qualification_gate(ref):
 from checkm2_distinct_index8_profile_policy_v001 import qualification_gate as distinct_gate
 return distinct_gate(ref,read=read,bind=bind,unit_closed=unit_closed,bound_evidence=bound_evidence)


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

def qualification_registry_gate(qualification,registry_ref):
 registry=read(bind(registry_ref));entries=registry['rows']+[registry['additional_baseline']]
 found=[x for x in entries if x['accession']==qualification.get('accession')]
 if len(found)!=1:raise RuntimeError('Qualification donor must already be accepted for reuse')
 for key in('commit','feature_validation'):
  if key not in qualification or key not in found[0]or bind(qualification[key])!=bind(found[0][key]):raise RuntimeError('Qualification accepted own commit/feature association differs')

def reference_control_gate(plan,accepted):
 spec=plan['search_only_control']
 if spec.get('role')!='SEARCH_ONLY_CONTROL'or spec['accession']not in accepted or spec['accession']in plan['accessions']:raise RuntimeError('One explicitly accepted reference donor only; no annotation/ML replay')
 for key in('selected_faa','annotation_receipt','annotation_unit_execution','reference_raw_diamond','accepted_method_authority'):bind(spec[key])
 authority=read(bind(spec['accepted_method_authority']));registry=read(bind(plan['accepted_registry']));entry=next(x for x in registry['rows']+[registry['additional_baseline']]if x['accession']==spec['accession'])
 if entry.get('authority')!=spec['accepted_method_authority'] or authority.get('accession')!=spec['accession']:raise RuntimeError('Reference Root acceptance association differs')
 annotation=read(bind(spec['annotation_receipt']))
 if annotation['accession']!=spec['accession']or annotation['faa_sha256']!=spec['selected_faa']['sha256']or not unit_closed(read(bind(spec['annotation_unit_execution']))):raise RuntimeError('Accepted own reference FAA/annotation0 required')
 return spec

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

def plan_gate(plan_path,expected_sha,require_admission=True,closed_finalization=False):
 plan=configure(plan_path,expected_sha);stop()
 if plan.get('role')!=ROLE:raise RuntimeError('Campaign role differs')
 for ref in read(bind(plan['source_manifest']))['sources']:bind(ref)
 accepted=accepted_gate(plan['accepted_registry'])
 if plan.get('search_only_control'):reference_control_gate(plan,accepted)
 if plan['mode']=='CLOSED_INDEX8_PROFILE':
  qualification=qualification_gate(plan['qualification_acceptance']);qualification_registry_gate(qualification,plan['accepted_registry'])
  if qualification.get('accession') not in accepted:raise RuntimeError('Qualified accession must be reused, never rerun')
 elif plan['mode']=='CONDITIONAL_INDEX8_PROMOTION':
  method=read(bind(plan['conditional_method_authority']))
  if method.get('status')!='ROOT_APPROVED_CONDITIONAL_INDEX8_PROMOTION_COHORT' or method.get('first_accession')!=plan['accessions'][0] or plan['accessions'][0]!='GCF_002993975.1' or method.get('index_chunks')!=8 or method.get('block_size')!=0.5 or method.get('threads')!=1 or any(method.get(k)is not True for k in('all_prior_search_attempts_closed_and_charged','first_complete_feature_checked_row_before_remaining_inputs','accepted_predictions_never_replayed','resource_guards_unchanged')):raise RuntimeError('Explicit conditional first-row promotion authority required')
  bound_evidence(method.get('closure_and_result_evidence'))
  failures=method.get('prior_DIAMOND_executions',[])
  if len(failures)!=4 or method.get('new_search_allowance_is_additional_not_reset')is not True or method.get('new_search_allowance_seconds')!=phase_cap('unit_diamond',plan['accessions'][0],plan):raise RuntimeError('All four prior failed composite attempts and explicit additional search allocation required')
  actuals=[]
  for ref in failures:
   u=read(bind(ref));n=u.get('elapsed_seconds')
   if ref not in plan['prior_debit_artifacts']or type(n)not in(int,float)or not math.isfinite(n)or n<0 or u.get('exit_code')!=-15 or u.get('owned_group_empty')is not True or u.get('remaining_owned_processes')!=[]:raise RuntimeError('Prior known failed search must be closed and fully charged')
   actuals.append(n)
  if math.fsum(actuals)!=method.get('prior_search_seconds_charged'):raise RuntimeError('Prior search actual elapsed cannot reset or omit polling overshoot')
  if set(plan['annotation_reuse_by_accession'])!={plan['accessions'][0]}:raise RuntimeError('First conditional input must reuse its accepted annotation')
 else:raise RuntimeError('Unknown index8 method qualification mode')
 
 if plan['canonical_queue']['sha256']!='44d456e79af0f84a2c35a2dd3e1b6f8cd748df31d17ee8273becca7a765b75f1':raise RuntimeError('Canonical campaign scope changed')
 queue=read(bind(plan['canonical_queue']));qrows={x['queue_id']:x for x in queue['rows']};selection=read(bind(plan['selected_inputs']));names=plan['accessions']
 context=read(bind(plan['queue_launch_context']));proposal=read(bind(context['queue_proposal']));reservation=read(bind(context['queue_reservation']))
 if context['canonical_QC_queue']!=plan['canonical_queue'] or proposal.get('queue')!=plan['canonical_queue'] or reservation.get('kind')!='RESERVED' or reservation['queue_ids']!=context['queue_ids'] or proposal['queue_ids']!=context['queue_ids'] or reservation['proposal_sha256']!=context['queue_proposal']['sha256']:raise RuntimeError('Exact durable queue reservation/proposal differs')
 authority=read(bind(plan['cohort_authority']))
 if authority.get('status')!='ROOT_APPROVED_CAMPAIGN_INDEX8_COHORT_SELECTION_AND_BUDGET' or authority.get('queue_sha256')!=plan['canonical_queue']['sha256'] or authority.get('queue_proposal_sha256')!=context['queue_proposal']['sha256'] or authority.get('accessions')!=names or authority.get('limits')!=LIMITS or authority.get('prior_debit_artifacts')!=plan['prior_debit_artifacts'] or any(authority.get(k)is not True for k in('all_previous_attempts_and_claims_preserved','no_accepted_phase_replay','no_undocumented_allowance_reset','all_selected_inputs_fresh_or_explicit_closed_phase_reuse_verified')):raise RuntimeError('Explicit current cohort provenance/budget authority required')
 prior_debits(plan)
 if authority.get('new_finite_unstarted_input_time_allocations_explicitly_approved')is not True:raise RuntimeError('Data-bound finite phase allocations require explicit Root approval; prior attempt actuals cannot reset')
 if plan.get('carried_cold_ceiling_seconds')is not None and LIMITS['cold_session_seconds']>plan['carried_cold_ceiling_seconds']:raise RuntimeError('Carried closed-attempt cold allowance exceeded')
 remaining=[n for n in context['queue_ids']if n not in accepted]
 if names!=remaining[:len(names)] or len(selection['inputs'])!=COUNT or names!=[x['accession']for x in selection['inputs']]:raise RuntimeError('Cohort must follow exact unaccepted reserved order')
 for item in selection['inputs']:
  acc=item['accession'];q=qrows[acc]
  if acc in accepted or set(q['paired_accessions'])&accepted or q['source_supported_scope']is not True or q['qc_execution_state']not in('READY_FRESH_QC','RESERVED_P20_UNSTARTED') or item.get('canonical_queue_row')!=q:raise RuntimeError('Accepted/held/historical or changed queue member cannot run fresh')
  if any(item[k]!=q[k]for k in('species','species_taxid','genus','family','source_pending_reasons','source_holds_preserved','metadata_qc'))or item['source_masks']!=canonical_source_masks(q):raise RuntimeError('Original source context/masks changed')
  if item['fasta_path']!=q['FNA_from_receipt']['path'] or item['fasta_sha256']!=q['FNA_from_receipt']['sha256'] or item['fasta_bytes']!=q['FNA_from_receipt']['bytes']:raise RuntimeError('Acquired input identity differs')
  bind(q['acquisition_receipt'])
  if acc in plan['annotation_reuse_by_accession']:annotation_reuse_gate(plan,acc,item)
 if UNRESOLVED_HANDOFF.exists()or list((E/'unresolved_ownership').glob('*.json')):raise RuntimeError('Unresolved cohort owner; no relaunch')
 token=os.environ.get('TREE2_CHECKM2_PILOT_LAUNCH_TOKEN')
 for p in OUT.glob('sessions/*/once_claim.json'):
  claim=read(p)
  if claim['input_plan_sha256']!=expected_sha or(not closed_finalization and claim['native_launch_token']!=token):raise RuntimeError('Cohort once claim consumed; no automatic replay')
 
 if plan['scientific_recipe']['sha256']!='78e6bceffc1b86cbb9d2a49c85874730a80d744739e6fa638e2087423aa24a02':raise RuntimeError('Unchanged scientific template recipe required')
 bind(plan['method_amendment']);template=read(bind(plan['scientific_recipe']))
 recipe={**template,'inputs':selection['inputs'],'inference_order':names,'selected_inputs':plan['selected_inputs'],'role':ROLE,'limits':LIMITS,'phases':UNITS,'resource_variant':{'index_chunks':8,'block_size':0.5,'threads':1,'method_amendment':plan['method_amendment']}}
 if not require_admission:return plan,recipe,None
 a=read(ADMISSION)
 if a.get('status')!='ROOT_ADMITTED_ONE_CAMPAIGN_INDEX8_SERIAL_COHORT' or a.get('input_plan_sha256')!=expected_sha or a.get('source_manifest_sha256')!=plan['source_manifest']['sha256']or a.get('limits')!=LIMITS or a.get('max_inputs')!=COUNT or a.get('scientific_execution_authorized')is not True:raise RuntimeError('Separate exact-cohort scientific admission required')
 if read(bind(a['preflight_actual_exit'])).get('actual_exit_code')!=0:raise RuntimeError('Fresh actual preflight0 required')
 bind(a['preflight_receipt']);return plan,recipe,a

def request_gate(request):
 for key in('input_plan','source_manifest','protocol_admission','selected_inputs'):bind(request[key])
 plan,recipe,a=plan_gate(request['input_plan']['path'],request['input_plan']['sha256']);runtime_gate(request,recipe)
 if request['source_manifest']!=plan['source_manifest']or request['protocol_admission']!=row(ADMISSION)or request['selected_inputs']!=plan['selected_inputs']or request.get('resource_method_amendment')!=plan['method_amendment']:raise RuntimeError('Own cohort authority/source/request differs')
 if request.get('role')=='SEARCH_ONLY_CONTROL':
  spec=reference_control_gate(plan,accepted_gate(plan['accepted_registry']))
  if request.get('request_schema')!='TREE2_PHASE_SEPARATED_P20_DIAMOND_REQUEST_V001'or request.get('control_reference')!=spec or request.get('accession')!=spec['accession']or any(request.get(k)!=spec[k]for k in('selected_faa','annotation_receipt','annotation_unit_execution'))or a.get('reference_search_only_control_authorized')is not True:raise RuntimeError('Control restricted to exact one search-only request; no annotation/ML')
  return plan,{**recipe,'input':{'accession':spec['accession']}},a
 inputs=[x for x in recipe['inputs']if x['accession']==request.get('accession')]
 if len(inputs)!=1:raise RuntimeError('Own accession join required')
 return plan,{**recipe,'input':inputs[0]},a

def annotation_reuse_gate(plan,acc,item):
 spec=plan['annotation_reuse_by_accession'][acc];commit=read(bind(spec['commit']));authority=read(bind(spec['closed_authority']))
 if authority.get('all_current_and_prior_owner_context_image_IPC_and_three_lease_closure_verified')is not True and authority.get('owned_group_namespace_image_lease_closure_verified')is not True:raise RuntimeError('Original annotation attempt external closure authority required')
 if commit.get('accession')!=acc or commit.get('status')!='P20_ANNOTATION_UNIT0_COMMITTED_PENDING_CONTEXT_CLOSURE' or commit.get('input_plan_sha256')!=spec['original_plan_sha256'] or commit.get('source_manifest_sha256')!=spec['original_source_manifest_sha256']:raise RuntimeError('Original annotation provenance cannot be relabelled')
 verify_manifest(bind(commit['manifest']).parent,read(bind(commit['manifest'])))
 unit=read(bind(commit['unit_execution']));receipt=read(bind(commit['annotation_receipt']))
 if not unit_closed(unit)or receipt['accession']!=acc or receipt['source_fna_sha256']!=item['fasta_sha256']or receipt['faa_sha256']!=commit['selected_faa']['sha256']or commit['source_masks']!=item['source_masks']:raise RuntimeError('Original actual0/FAA/source/masks differ')
 if commit['unit_execution'] not in plan['prior_debit_artifacts']:raise RuntimeError('Reused original annotation debit must remain bound and charged')
 bind(commit['selected_faa']);return commit

def phase_commit_gate(plan,request,artifacts,annotation,search):
 acc=request['accession']
 if acc in plan['annotation_reuse_by_accession']:
  item=next(x for x in read(bind(plan['selected_inputs']))['inputs']if x['accession']==acc)
  if artifacts['annotation_commit']!=plan['annotation_reuse_by_accession'][acc]['commit']or annotation!=annotation_reuse_gate(plan,acc,item):raise RuntimeError('Only exact original annotation reuse is authorized')
  commits=(search,)
 else:commits=(annotation,search)
 for commit in commits:
  if commit.get('accession')!=acc or commit.get('input_plan_sha256')!=request['input_plan']['sha256']or commit.get('source_manifest_sha256')!=request['source_manifest']['sha256']or commit.get('selected_faa')!=artifacts['selected_faa']:raise RuntimeError('Own new phase provenance differs; no fabricated reused unit')
  verify_manifest(bind(commit['manifest']).parent,read(bind(commit['manifest'])))

def budget(run):
 commands=set(path(run).glob('rows/*/unit_*/command.json'))|set(path(run).glob('controls/*/unit_*/command.json'));terminals=set(path(run).glob('rows/*/unit_*/execution.json'))|set(path(run).glob('controls/*/unit_*/execution.json'));alloc=set(path(run).glob('rows/*/unit_*_budget.json'))|set(path(run).glob('controls/*/unit_*_budget.json'))
 if terminals!={p.with_name('execution.json')for p in commands}or alloc!={p.parent.parent/(p.parent.name+'_budget.json')for p in commands}:raise RuntimeError('Unknown/incomplete actual attempt debit; no replay/reset')
 plan=read(PLAN_PATH);spent={}
 for p in terminals:
  u=read(p);acc=p.parent.parent.name;name=p.parent.name;n=u.get('elapsed_seconds')
  control=acc=='REFERENCE_CONTROL'and bool(plan.get('search_only_control'))and name in('unit_diamond','unit_saved_search_validation','unit_reference_comparison')
  if (acc not in plan['accessions']and not control)or name not in set(UNITS)|{'unit_reference_comparison'} or type(n)not in(int,float)or not math.isfinite(n)or n<0 or u.get('owned_group_empty')is not True or u.get('remaining_owned_processes')!=[]:raise RuntimeError('Unit debit/resource/closure differs')
  spent.setdefault(acc,{})[name]=n
 per={acc:math.fsum(v.values())for acc,v in spent.items()};used=math.fsum(per.values());prior=prior_debits(plan)
 exceeded=any(n>input_cap(acc)for acc,n in per.items())or used>LIMITS['cohort_scientific_seconds']or any(n>phase_cap(name,acc,plan)for acc,values in spent.items()for name,n in values.items())
 return {'units_seconds_by_accession':spent,'input_scientific_seconds':per,'cohort_scientific_seconds_debited':used,'remaining_cohort_scientific_seconds':max(0,LIMITS['cohort_scientific_seconds']-used),'known_limit_exceeded':exceeded,'prior_actual_scientific_seconds_retained':prior,'prior_plus_new_actual_scientific_seconds':prior+used,'reference_control_seconds_debited':per.get('REFERENCE_CONTROL',0),'no_allowance_borrowing_or_historical_reset':True}

def current_failed_run(step,token,input_plan_sha,protocol_sha):
 p=OUT/'runs_by_token'/(token+'.json')
 if not p.exists():return None
 loc=read(p)
 if loc['launch_token']!=token or loc['input_plan_sha256']!=input_plan_sha or loc['protocol_admission_sha256']!=protocol_sha:raise RuntimeError('Required cohort locator differs')
 bind(loc['binding']);run=path(loc['run_directory'])
 if run.parent!=OUT/'runs' or read(run/'failure.json')['status']!='P20_FAILED_NO_AUTOMATIC_RETRY_OR_FALLBACK':raise RuntimeError('Current failure evidence absent')
 return run
configure_argv()
