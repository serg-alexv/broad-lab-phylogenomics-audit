"""New N5 gates and strict budget; no scientific imports/dispatch on import."""
from pathlib import Path
import math,os
import checkm2_single_faa_common_S1R2 as base
R=base.R;path=base.path;sha=base.sha;read=base.read;save=base.save;row=base.row;bind=base.bind
manifest=base.manifest;verify_manifest=base.verify_manifest;unit_closed=base.unit_closed;group_receipts_closed=base.group_receipts_closed;pending_is_current=base.pending_is_current
ROLE='PHASE_SEPARATED_N5_SERIAL_FEASIBILITY_ONLY';PHASES=('RUN_FRESH_SERIAL_FIVE_ONCE',)
LIMITS={'cpu_affinity_max': 2, 'stock_threads': 1, 'sum_group_RSS_bytes': 2147483648, 'linux_available_minimum_bytes': 1073741824, 'disk_reserve_bytes': 42949672960, 'per_input_annotation_seconds': 180, 'per_input_diamond_seconds': 600, 'per_input_resume_seconds': 600, 'per_input_validation_seconds': 30, 'per_input_scientific_seconds': 1410, 'cohort_scientific_seconds': 7050, 'cold_session_seconds': 9000}
UNITS={'unit_annotation':180,'unit_diamond':600,'unit_resume':600,'unit_feature_validation':30}
E=R/'evidence/checkm2_phase_separated_N5';OUT=R/'analysis/checkm2_phase_separated_N5'
STATE=R/'state/checkm2_phase_separated_progress_N5.json';STEP=R/'state/checkm2_phase_separated_step_N5.json';LAUNCH=R/'state/launch_checkm2_phase_separated_N5.json';ADMISSION=R/'state/checkm2_phase_separated_ready_N5.json';STOP=R/'state/STOP_CHECKM2_PHASE_SEPARATED_N5';UNRESOLVED_HANDOFF=E/'unresolved_ownership_handoff.json'

def stop():
 if any(p.exists() for p in (STOP,R/'state/STOP',R/'state/STOP_CHECKM2_PILOT')):raise InterruptedError('N5/project/biological STOP')

def budget(run):
 run=path(run);commands=set(run.glob('rows/*/unit_*/command.json'));terminals=set(run.glob('rows/*/unit_*/execution.json'));allocations=set(run.glob('rows/*/unit_*_budget.json'))
 if terminals!={p.with_name('execution.json')for p in commands}or allocations!={p.parent.parent/(p.parent.name+'_budget.json')for p in commands}:raise RuntimeError('N5 unknown/incomplete phase debit; no reset or continuation')
 spent={};per={}
 for p in terminals:
  acc=p.parent.parent.name;name=p.parent.name;unit=read(p);value=unit.get('elapsed_seconds')
  if name not in UNITS or type(value)not in(int,float)or not math.isfinite(value)or value<0 or unit.get('owned_group_empty')is not True or unit.get('remaining_owned_processes')!=[]:raise RuntimeError('N5 elapsed/owned group proof missing')
  if value>UNITS[name]:raise RuntimeError('N5 original phase allowance exceeded')
  spent.setdefault(acc,{})[name]=value
 for acc,values in spent.items():per[acc]=math.fsum(values.values())
 used=math.fsum(per.values())
 if len(per)>5 or any(value>1410 for value in per.values())or used>7050:raise RuntimeError('N5 input/cohort allowance exhausted')
 return {'units_seconds_by_accession':spent,'input_scientific_seconds':per,'cohort_scientific_seconds_debited':used,'remaining_cohort_scientific_seconds':7050-used,'per_input_remaining_seconds':{acc:1410-value for acc,value in per.items()},'prior_N1_and_other_campaign_debits_untouched':True,'new_allowance_seconds':7050}

def budget_files(run):return set(path(run).glob('rows/*/unit_*/command.json'))|set(path(run).glob('rows/*/unit_*/execution.json'))|set(path(run).glob('rows/*/unit_*_budget.json'))

def current_failed_run(step,token,input_plan_sha,protocol_sha):
 locator=OUT/'runs_by_token'/(token+'.json')
 if not locator.exists():return None
 loc=read(locator)
 if loc.get('launch_token')!=token or loc.get('input_plan_sha256')!=input_plan_sha or loc.get('protocol_admission_sha256')!=protocol_sha:raise RuntimeError('Required N5 run locator mismatch')
 run=path(loc['run_directory']);bind(loc['binding'])
 if run.parent!=OUT/'runs':raise RuntimeError('N5 run locator escapes owned root')
 failure=read(run/'failure.json');commands=read(run/'invocations.json')
 if failure.get('status')!='N5_FAILED_NO_AUTOMATIC_RETRY_OR_FALLBACK' or not isinstance(commands,list):raise RuntimeError('Required N5 failure/units absent')
 if any(path(x).parent.parent!=run/'rows' or path(x).name not in UNITS for x in commands):raise RuntimeError('N5 invocation escapes declared run')
 return run

def history_gate(recipe):
 history=read(bind(recipe['history']));selected=read(bind(recipe['selected_inputs']));bind(recipe['queue']);bind(recipe['N1_closed_acceptance']);bind(recipe['accepted_method_registry'])
 names=[x['accession']for x in recipe['inputs']]
 if history.get('unresolved_history')!=[]or len(names)!=5 or len(set(names))!=5 or len({x['species_taxid']for x in recipe['inputs']})!=5 or names!=[x['accession']for x in selected['inputs']]or names!=recipe['inference_order']:raise RuntimeError('N5 exact five distinct first-label inputs/order differs')
 for item,actual in zip(recipe['inputs'],selected['actual_selected_FNAs']):
  if item['accession']in history['excluded_prior_accessions_and_paired_aliases']or actual['accession']!=item['accession']or actual['FNA']['sha256']!=item['fasta_sha256']:raise RuntimeError('Previously claimed or changed N5 input')
  observed=read(bind(actual['integrity_observation']))
  if observed['status']!='HASHED_ONCE_SHA256_SIZE_MATCH'or observed['actual_sha256']!=item['fasta_sha256']:raise RuntimeError('N5 authorized integrity observation absent')
 for record in history['claim_inventory']:bind(record['artifact'])
 import prepare_checkm2_phase_separated_history_N5 as index
 old_paths={x['artifact']['path']for x in history['claim_inventory']};current_paths={x[0]for x in index.inventory()}
 def own(n):return n.startswith(('analysis/checkm2_phase_separated_N5/','evidence/checkm2_phase_separated_N5/','state/checkm2_phase_separated_N5_launch_requests/'))or n=='state/launch_checkm2_phase_separated_N5.json'
 if {x for x in current_paths if not own(x)}!=old_paths:raise RuntimeError('N5 authoritative history inventory changed; no silent fresh selection')
 registry=read(bind(history['registry']));prior={x['accession']for x in registry['rows']}|{registry['additional_baseline']['accession']}
 if set(names)&prior:raise RuntimeError('Accepted/control donor cannot replay')
 for key in('manifest','commit','genomes_tsv'):bind(recipe['nomenclature_type_hold_context'][key])
 return selected

def plan_gate(plan_path,expected_sha,require_admission=True,closed_finalization=False):
 stop();p=path(plan_path)
 if sha(p)!=expected_sha:raise RuntimeError('N5 input plan SHA mismatch')
 plan=read(p)
 if plan.get('schema')!='TREE2_PHASE_SEPARATED_N5_INPUT_PLAN_V001' or plan.get('role')!=ROLE or plan.get('limits')!=LIMITS:raise RuntimeError('N5 plan scope/limits differ')
 recipe=read(bind(plan['scientific_recipe']));history_gate(recipe)
 if recipe.get('limits')!=LIMITS or recipe.get('role')!=ROLE or recipe.get('phases')!=UNITS:raise RuntimeError('N5 recipe differs')
 authority=read(bind(recipe['scope_authority']))
 if authority.get('status')!='APPROVED_FIVE_NOVEL_LOCAL_SELECTION_AND_SOURCE_IMPLEMENTATION_ONLY' or authority.get('source_implementation_authorized') is not True:raise RuntimeError('Root source/selection authority missing')
 for item in read(bind(plan['source_manifest']))['sources']:bind(item)
 for item in recipe['inputs']:
  source=path(item['fasta_path'])
  if sha(source)!=item['fasta_sha256']or source.stat().st_size!=item['fasta_bytes']:raise RuntimeError('Selected acquired N5 FNA changed')
 if UNRESOLVED_HANDOFF.exists() or list((E/'unresolved_ownership').glob('*.json')):raise RuntimeError('Unresolved N5 owner; no new attempt')
 token=os.environ.get('TREE2_CHECKM2_PILOT_LAUNCH_TOKEN')
 for claim in OUT.glob('sessions/*/once_claim.json'):
  existing=read(claim)
  if existing.get('input_plan_sha256')!=expected_sha or (not closed_finalization and (not token or existing.get('native_launch_token')!=token)):raise RuntimeError('N5 once claim already exists; no replay/new session reset')
 if not require_admission:return plan,recipe,None
 a=read(ADMISSION)
 if a.get('schema')!='TREE2_PHASE_SEPARATED_N5_ADMISSION_V001' or a.get('status')!='ADMITTED_ONE_FRESH_N5_SERIAL_FEASIBILITY_CONTROL' or a.get('role')!=ROLE or a.get('n5_execution_authorized') is not True or a.get('phase')!='RUN_FRESH_SERIAL_FIVE_ONCE' or a.get('max_inputs')!=5:raise RuntimeError('Separate N5 scientific admission absent')
 if a.get('input_plan_sha256')!=expected_sha or a.get('source_manifest_sha256')!=plan['source_manifest']['sha256'] or a.get('recipe_sha256')!=plan['scientific_recipe']['sha256'] or a.get('limits')!=LIMITS:raise RuntimeError('N5 admission binding differs')
 if any(a.get(x) is not True for x in ('novel_selection_history_GO','source_math_ABI_GO','resource_lifecycle_GO','monitor_standard_stage04_ready')):raise RuntimeError('N5 scientific/source/resource gate held')
 return plan,recipe,a


def runtime_gate(request,recipe):
 binding=recipe['runtime_binding'];prefix=path(binding['canonical_prefix'])
 if path(request['runtime_prefix'])!=prefix:raise RuntimeError('N5 consumer canonical accepted runtime prefix differs')
 ready=read(bind(recipe['accepted_runtime_ready_receipt']));bind(binding['effective_manifest'])
 if ready.get('checkm2_version')!='1.1.0' or ready.get('diamond_version')!='2.1.11' or ready.get('runtime_image',{}).get('sha256')!=binding['image_sha256'] or path(ready['prefix_linux'])!=prefix or path(ready['database_path'])!=path(binding['database']['path']):raise RuntimeError('N5 immutable accepted Ready/image/tool/DB3 ABI differs')
 if any(os.environ.get(key)!=value for key,value in binding['required_environment'].items()):raise RuntimeError('N5 process controls differ from accepted effective runtime')
 from checkm2_pilot import readonly_runtime_gate
 readonly_runtime_gate(ready)
 for key,expected in (('database',binding['database']),('diamond_binary',binding['tools']['diamond'])):
  if key in request and request[key]!=expected:raise RuntimeError('N5 original DB/binary request differs from immutable accepted recipe')
 return prefix

def request_gate(request):
 for name in ('input_plan','source_manifest','protocol_admission','selected_inputs'):bind(request[name])
 plan,recipe,admission=plan_gate(request['input_plan']['path'],request['input_plan']['sha256'])
 runtime_gate(request,recipe)
 if request['source_manifest']!=plan['source_manifest'] or request['protocol_admission']!=row(ADMISSION) or request['selected_inputs']!=recipe['selected_inputs']:raise RuntimeError('N5 phase request differs from admitted input/source')
 matches=[x for x in recipe['inputs']if x['accession']==request.get('accession')]
 if len(matches)!=1:raise RuntimeError('N5 phase request must name its exact own selected input')
 return plan,{**recipe,'input':matches[0]},admission
