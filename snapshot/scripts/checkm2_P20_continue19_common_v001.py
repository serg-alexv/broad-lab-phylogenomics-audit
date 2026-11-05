"""Continuation of exactly nineteen unstarted reserved inputs; accepted first row is reuse only."""
import math,os
import checkm2_phase_separated_common_P20 as old
R=old.R;path=old.path;sha=old.sha;read=old.read;save=old.save;row=old.row;bind=old.bind
manifest=old.manifest;verify_manifest=old.verify_manifest;unit_closed=old.unit_closed;group_receipts_closed=old.group_receipts_closed;pending_is_current=old.pending_is_current;runtime_gate=old.runtime_gate
E=old.E/'continue19_v001';OUT=old.OUT/'continue19_v001';STATE=E/'progress.json';STEP=E/'step.json';LAUNCH=E/'native_scientific_launch.json';ADMISSION=E/'Root_runtime_admission.json';STOP=R/'state/STOP_CHECKM2_P20_CONTINUE19_V001';UNRESOLVED_HANDOFF=E/'unresolved_ownership_handoff.json'
ROLE='PHASE_SEPARATED_P20_CONTINUE19_ONLY';UNITS=dict(old.UNITS)
LIMITS={**old.LIMITS,'cohort_scientific_seconds':26790,'cold_session_seconds':30000}
def stop():
 old.stop()
 if STOP.exists():raise InterruptedError('P20 continuation19 scoped STOP')
def budget(run):
 run=path(run);commands=set(run.glob('rows/*/unit_*/command.json'));terminals=set(run.glob('rows/*/unit_*/execution.json'));allocations=set(run.glob('rows/*/unit_*_budget.json'))
 if terminals!={p.with_name('execution.json')for p in commands}or allocations!={p.parent.parent/(p.parent.name+'_budget.json')for p in commands}:raise RuntimeError('Continuation19 unknown/incomplete debit; no reset')
 spent={};per={}
 for p in terminals:
  acc=p.parent.parent.name;name=p.parent.name;u=read(p);value=u.get('elapsed_seconds')
  if acc=='GCF_000831485.1' or name not in UNITS or type(value)not in(int,float)or not math.isfinite(value)or not 0<=value<=UNITS[name] or u.get('owned_group_empty')is not True or u.get('remaining_owned_processes')!=[]:raise RuntimeError('Continuation phase/input/debit/closed-group contract differs')
  spent.setdefault(acc,{})[name]=value
 for acc,values in spent.items():per[acc]=math.fsum(values.values())
 used=math.fsum(per.values())
 if len(per)>19 or any(x>1410 for x in per.values())or used>26790 or used+340.5752029999858>28200:raise RuntimeError('Original P20 aggregate or continuation19 allowance exceeded')
 return {'units_seconds_by_accession':spent,'input_scientific_seconds':per,'cohort_scientific_seconds_debited':used,'remaining_cohort_scientific_seconds':26790-used,'per_input_remaining_seconds':{acc:1410-x for acc,x in per.items()},'old_original_scientific_seconds_charged':340.5752029999858,'old_failed_validation_seconds_charged':22.79685944299854,'separate_saved_repair_validation_seconds_charged':43.283077190004406,'original_P20_science_aggregate_seconds':used+340.5752029999858,'old_claims_and_all_other_campaign_debits_untouched':True,'new_allowance_seconds':26790,'unused_first_row_or_N1_N5_allowance_borrowed':False}
def current_failed_run(step,token,input_plan_sha,protocol_sha):
 p=OUT/'runs_by_token'/(token+'.json')
 if not p.exists():return None
 loc=read(p)
 if loc['launch_token']!=token or loc['input_plan_sha256']!=input_plan_sha or loc['protocol_admission_sha256']!=protocol_sha:raise RuntimeError('Continuation required failed-run locator differs')
 bind(loc['binding']);run=path(loc['run_directory']);failure=read(run/'failure.json')
 if run.parent!=OUT/'runs' or failure['status']!='P20_FAILED_NO_AUTOMATIC_RETRY_OR_FALLBACK':raise RuntimeError('Continuation failure evidence differs')
 return run
def plan_gate(plan_path,expected_sha,require_admission=True,closed_finalization=False):
 stop();p=path(plan_path)
 if sha(p)!=expected_sha:raise RuntimeError('Continuation19 plan SHA differs')
 plan=read(p)
 if plan.get('schema')!='TREE2_P20_RESERVED_NINETEEN_CONTINUATION_PLAN_V001' or plan.get('limits')!=LIMITS or plan.get('role')!=ROLE:raise RuntimeError('Exact reviewed nineteen continuation plan required')
 original,recipe,_=old.plan_gate(bind(plan['original_plan']),plan['original_plan']['sha256'],closed_finalization=True)
 expected=recipe['inputs'][1:];names=[x['accession']for x in expected]
 if len(names)!=19 or names!=plan['accessions'] or len(set(names))!=19 or 'GCF_000831485.1'in names:raise RuntimeError('Only original reserved nineteen in exact order are eligible')
 accepted=read(bind(plan['accepted_registry']));saved=read(bind(plan['saved_first_row_acceptance']))
 if saved.get('status')!='ROOT_ACCEPTED_CLOSED_SAVED_FIRST_P20_METHOD_ESTIMATE_FOR_REUSE_ONLY' or saved.get('accession')!='GCF_000831485.1':raise RuntimeError('Closed saved-first-row acceptance required')
 bind(saved['closed_method_evidence']);external=read(bind(saved['external_audit_actual_exit']))
 if external.get('actual_exit_code')!=0:raise RuntimeError('First-row closure auditor actual0 required')
 accepted_ids={x['accession']for x in accepted['rows']}|{accepted['additional_baseline']['accession']}
 if 'GCF_000831485.1'not in accepted_ids or set(names)&accepted_ids or accepted.get('accepted_unique_method_accessions')!=list(dict.fromkeys(accepted['accepted_unique_method_accessions'])) or set(accepted['accepted_unique_method_accessions'])!=accepted_ids:raise RuntimeError('Accepted result or identity registry must not be replayed')
 context=read(bind(plan['queue_launch_context']));reservation=read(bind(context['queue_reservation']))
 if reservation.get('kind')!='RESERVED' or context['queue_ids']!=reservation['queue_ids'] or context['queue_ids']!=[recipe['inputs'][0]['accession']]+names:raise RuntimeError('Exact original20 queue reservation must survive')
 for item in expected:
  if list(old.OUT.glob('runs/*/rows/'+item['accession']+'/once_claim.json')):raise RuntimeError('An original reserved input is already consumed; review rather than replay')
 for ref in read(bind(plan['source_manifest']))['sources']:bind(ref)
 if UNRESOLVED_HANDOFF.exists() or list((E/'unresolved_ownership').glob('*.json')):raise RuntimeError('Continuation unresolved ownership blocks a new session')
 token=os.environ.get('TREE2_CHECKM2_PILOT_LAUNCH_TOKEN')
 for claim in OUT.glob('sessions/*/once_claim.json'):
  prior=read(claim)
  if prior['input_plan_sha256']!=expected_sha or(not closed_finalization and prior['native_launch_token']!=token):raise RuntimeError('Continuation19 once claim consumed; no automatic retry')
 recipe={**recipe,'inputs':expected,'inference_order':names,'role':ROLE,'limits':LIMITS,'phases':UNITS}
 if not require_admission:return plan,recipe,None
 admitted=read(ADMISSION)
 if admitted.get('status')!='ROOT_ADMITTED_ONE_P20_CONTINUE19_SESSION_V001' or admitted.get('phase')!='CONTINUE_RESERVED19_ONCE' or admitted.get('input_plan_sha256')!=expected_sha or admitted.get('limits')!=LIMITS or admitted.get('max_inputs')!=19:raise RuntimeError('Separate fresh nineteen scientific/session admission required')
 pre=read(bind(admitted['preflight_actual_exit']))
 if pre.get('actual_exit_code')!=0:raise RuntimeError('Fresh continuation preflight actual0 required')
 bind(admitted['preflight_receipt']);return plan,recipe,admitted
def request_gate(request):
 for key in('input_plan','source_manifest','protocol_admission','selected_inputs'):bind(request[key])
 plan,recipe,admitted=plan_gate(request['input_plan']['path'],request['input_plan']['sha256']);runtime_gate(request,recipe)
 if request['source_manifest']!=plan['source_manifest'] or request['protocol_admission']!=row(ADMISSION) or request['selected_inputs']!=recipe['selected_inputs']:raise RuntimeError('Continuation own source/authority/input selection request differs')
 found=[x for x in recipe['inputs']if x['accession']==request.get('accession')]
 if len(found)!=1:raise RuntimeError('Only one of the nineteen own inputs may be invoked')
 return plan,{**recipe,'input':found[0]},admitted
