"""Separate saved-output validation authority and accounting. No fresh caller/search/model path."""
import math,os
from pathlib import Path
import checkm2_phase_separated_common_P20 as old
R=old.R;path=old.path;sha=old.sha;read=old.read;save=old.save;row=old.row;bind=old.bind
manifest=old.manifest;verify_manifest=old.verify_manifest;unit_closed=old.unit_closed;group_receipts_closed=old.group_receipts_closed;pending_is_current=old.pending_is_current
E=old.E/'metadata_ABI_repair_runtime_v001';OUT=old.OUT/'metadata_ABI_repair_v001'
STATE=E/'progress.json';STEP=E/'step.json';LAUNCH=E/'native_scientific_launch.json';ADMISSION=E/'Root_runtime_admission.json'
STOP=R/'state/STOP_CHECKM2_SAVED_P20_V001';UNRESOLVED_HANDOFF=E/'unresolved_ownership_handoff.json'
ROLE='P20_SAVED_OUTPUT_VALIDATION_REPAIR_V001';UNITS={'unit_saved_validation':60}
LIMITS={'cpu_affinity_max':2,'stock_threads':1,'sum_group_RSS_bytes':2147483648,'linux_available_minimum_bytes':1073741824,'disk_reserve_bytes':42949672960,'saved_validation_seconds':60,'cold_session_seconds':2400,'prehelper_preflight_max_seconds':600,'helper_max_seconds':1160,'post_unmount_hash_max_seconds':600,'fatal_cleanup_seconds':40}
def stop():
 old.stop()
 if STOP.exists():raise InterruptedError('Saved-validation scoped STOP')
def plan_gate(plan_path,expected_sha,require_admission=True,closed_finalization=False):
 stop();p=path(plan_path)
 if sha(p)!=expected_sha:raise RuntimeError('Saved-validation execution plan changed')
 plan=read(p)
 if plan.get('schema')!='TREE2_P20_SAVED_VALIDATION_RUNTIME_PLAN_V001' or plan.get('limits')!=LIMITS:raise RuntimeError('Saved-only scope and resource contract required')
 original,recipe,_=old.plan_gate(bind(plan['original_plan']),plan['original_plan']['sha256'],closed_finalization=True)
 authority=read(bind(plan['saved_validation_authority']))
 if authority.get('status')!='ROOT_ADMITTED_ONE_P20_SAVED_FEATURE_VALIDATION_REPAIR_V001' or authority.get('saved_output_validation_only')is not True or authority.get('annotation_DIAMOND_or_ML_execution_authorized')is not False or authority.get('maximum_validation_seconds')!=60:raise RuntimeError('Separate reviewed validation60 authority required')
 closure=read(bind(authority['external_closure']));audit_exit=read(bind(plan['original_closure_audit_actual_exit']))
 if closure.get('status')!='ACTUAL_FAILED_ATTEMPT_CLOSED_PARTIAL_PHASES_PRESERVED' or audit_exit.get('actual_exit_code')!=0 or audit_exit.get('exact_birth_handle_retained')is not True:raise RuntimeError('Original failed native/guest/contexts/leases must be actually closed')
 for ref in read(bind(plan['source_manifest']))['sources']:bind(ref)
 context=read(bind(plan['queue_launch_context']));reservation=read(bind(context['queue_reservation']))
 if reservation.get('kind')!='RESERVED' or reservation['queue_ids']!=context['queue_ids'] or context['queue_ids'][0]!='GCF_000831485.1' or len(context['queue_ids'])!=20:raise RuntimeError('Exact P20 queue reservation required')
 if UNRESOLVED_HANDOFF.exists() or list((E/'unresolved_ownership').glob('*.json')):raise RuntimeError('Saved-validation unresolved owner')
 for claim in OUT.glob('sessions/*/once_claim.json'):
  prior=read(claim)
  if prior['input_plan_sha256']!=expected_sha or(not closed_finalization and prior['native_launch_token']!=os.environ.get('TREE2_CHECKM2_PILOT_LAUNCH_TOKEN')):raise RuntimeError('Saved validation attempt already consumed; no automatic retry')
 if not require_admission:return plan,recipe,None
 admitted=read(ADMISSION)
 if admitted.get('status')!='ROOT_ADMITTED_ONE_SAVED_P20_NATIVE_SESSION_V001' or admitted.get('phase')!='SAVED_VALIDATE_ONCE' or admitted.get('input_plan_sha256')!=expected_sha or admitted.get('limits')!=LIMITS:raise RuntimeError('Fresh preflight and separate native session admission required')
 preflight=read(bind(admitted['preflight_actual_exit']))
 if preflight.get('actual_exit_code')!=0 or preflight.get('exact_birth_handle_retained')is not True:raise RuntimeError('Preflight actual retained0 required')
 bind(admitted['preflight_receipt']);return plan,recipe,admitted
def budget(run):
 run=path(run);commands=list(run.glob('rows/*/unit_*/command.json'));units=list(run.glob('rows/*/unit_*/execution.json'))
 if len(commands)>1 or {p.with_name('execution.json')for p in commands}!=set(units):raise RuntimeError('Unknown saved-validation debit; preserve no reset')
 used=0
 for p in units:
  u=read(p);value=u.get('elapsed_seconds')
  if p.parent.name!='unit_saved_validation' or type(value)not in(int,float)or not math.isfinite(value)or not 0<=value<=60 or u.get('owned_group_empty')is not True or u.get('remaining_owned_processes')!=[]:raise RuntimeError('Saved-validation unit/allowance/closure differs')
  used+=value
 return {'new_explicit_saved_validation_ceiling_seconds':60,'new_saved_validation_seconds_debited':used,'old_P20_scientific_seconds_charged':340.5752029999858,'old_failed_validation_seconds_charged':22.79685944299854,'old_validation30_remaining_not_reallocated_seconds':7.20314055700146,'old_claims_and_debits_untouched':True,'other_campaign_allowance_borrowed':False}
def current_failed_run(step,token,input_plan_sha,protocol_sha):
 loc=OUT/'runs_by_token'/(token+'.json')
 if not loc.exists():return None
 data=read(loc)
 if data['launch_token']!=token or data['input_plan_sha256']!=input_plan_sha or data['protocol_admission_sha256']!=protocol_sha:raise RuntimeError('Saved-validation required locator differs')
 bind(data['binding']);run=path(data['run_directory']);read(run/'failure.json');return run
