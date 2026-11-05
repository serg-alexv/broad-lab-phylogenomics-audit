"""HELD S1 inference-only gates. Imports no scientific runtime and dispatches nothing."""
import math
import checkm2_benchmark10_common_T1 as base
R=base.R
path=base.path;sha=base.sha;read=base.read;save=base.save;row=base.row;bind=base.bind
verify_manifest=base.verify_manifest;manifest=base.manifest;unit_closed=base.unit_closed
group_receipts_closed=base.group_receipts_closed;pending_is_current=base.pending_is_current
ROLE='SINGLE_FAA_INFERENCE_ONLY_METHOD_QC_S1'
LIMITS={'cpu_affinity_max':2,'stock_threads':1,'sum_group_RSS_bytes':2147483648,'linux_available_minimum_bytes':1073741824,'disk_reserve_bytes':42949672960,'per_genome_prediction_plus_validation_seconds':600,'max_genomes':10,'max_query_genomes_per_prediction':1,'prior_failed_quality_elapsed_seconds':104.24163487500482,'new_prediction_plus_validation_seconds':3495.758365,'original_quality_total_seconds':3600,'cold_session_seconds':6000}
PHASES=('RUN_FRESH_SERIES','RECOVER_CLOSED_ROWS')
E=R/'evidence/checkm2_single_faa_S1';OUT=R/'analysis/checkm2_single_faa_S1'
STATE=R/'state/checkm2_single_faa_progress_S1.json';STEP=R/'state/checkm2_single_faa_step_S1.json'
LAUNCH=R/'state/launch_checkm2_single_faa_S1.json';ADMISSION=R/'state/checkm2_single_faa_ready_S1.json'
STOP=R/'state/STOP_CHECKM2_SINGLE_FAA_S1';UNRESOLVED_HANDOFF=E/'unresolved_ownership_handoff.json'

def stop():
 if any(p.exists() for p in (R/'state/STOP',R/'state/STOP_CHECKM2_PILOT',STOP)):raise InterruptedError('S1/project/biological STOP; never cleared automatically')

def current_failed_run(step,token,input_plan_sha,protocol_sha):
 # Optional telemetry is a locator only. Required on-disk execution bindings stay strict.
 if not isinstance(step,dict) or step.get('windows_launch_token')!=token or step.get('input_plan_sha256')!=input_plan_sha or step.get('protocol_admission_sha256')!=protocol_sha:return None
 if not isinstance(step.get('run_directory'),str) or not step['run_directory']:return None
 run=path(step['run_directory'])
 if run.parent!=OUT/'runs':raise RuntimeError('S1 failed-run locator leaves current run root')
 record=read(run/'binding.json');failure=read(run/'failure.json');invocations=read(run/'invocations.json');launch=record.get('launch',{})
 if launch.get('token')!=token or launch.get('input_plan_sha256')!=input_plan_sha or launch.get('protocol_admission_sha256')!=protocol_sha or record.get('admission',{}).get('sha256')!=protocol_sha or record.get('plan',{}).get('_sha')!=input_plan_sha:raise RuntimeError('S1 failed-run required launch/source binding differs')
 if failure.get('status')!='S1_FAILED_NO_AUTOMATIC_RETRY_OR_FALLBACK' or failure.get('annotation_invoked') is not False or not isinstance(invocations,list):raise RuntimeError('S1 required failure/invocation evidence incomplete')
 for unit in invocations:
  if not path(unit).is_relative_to(OUT/'sessions'/record['plan']['session_identity_sha256']/'rows'):raise RuntimeError('S1 failed invocation leaves bound inference-only session')
 return run

def budget_files(session):
 session=path(session)
 return set(session.glob('rows/*/unit_*/command.json'))|set(session.glob('rows/*/unit_*/execution.json'))|set(session.glob('rows/*/unit_*_budget.json'))

def budget(session):
 session=path(session);commands=list(session.glob('rows/*/unit_*/command.json'));allocations=list(session.glob('rows/*/unit_*_budget.json'));expected={p.parent.parent/(p.parent.name+'_budget.json') for p in commands}
 terminals=set(session.glob('rows/*/unit_*/execution.json'))
 if set(allocations)!=expected or terminals!={p.with_name('execution.json') for p in commands}:raise RuntimeError('S1 allocated/started/terminal unit set incomplete; elapsed UNKNOWN, no reset')
 for claim in session.glob('rows/*/once_claim.json'):
  if not (claim.parent/'unit_quality/command.json').exists():raise RuntimeError('S1 prediction claim has no observed start/debit; no reset')
 per_genome={};used=0.0
 for command in commands:
  terminal=command.with_name('execution.json')
  if not terminal.exists():raise RuntimeError('S1 terminal elapsed UNKNOWN; no replay or debit reset')
  ex=read(terminal);elapsed=ex.get('elapsed_seconds')
  if type(elapsed) not in (int,float) or not math.isfinite(elapsed) or elapsed<0 or ex.get('owned_group_empty') is not True or ex.get('remaining_owned_processes')!=[]:raise RuntimeError('S1 elapsed/owned-group closure unproved')
  acc=command.parent.parent.name;used+=elapsed;per_genome[acc]=per_genome.get(acc,0.0)+elapsed
 if len(per_genome)>10 or any(v>600 for v in per_genome.values()) or used>LIMITS['new_prediction_plus_validation_seconds']:raise RuntimeError('S1 shared/per-genome allocation exhausted; no new allowance')
 return {'prior_failed_quality_seconds':LIMITS['prior_failed_quality_elapsed_seconds'],'new_seconds_debited':used,'remaining_seconds':LIMITS['new_prediction_plus_validation_seconds']-used,'per_genome_seconds':per_genome,'new_ceiling_seconds':LIMITS['new_prediction_plus_validation_seconds'],'original_total_seconds':3600}

def unresolved_ownership_gate(admission=None):
 records=list((E/'unresolved_ownership').glob('*.json'))
 if UNRESOLVED_HANDOFF.exists():records.append(UNRESOLVED_HANDOFF)
 if not records:return
 if not admission or not admission.get('unresolved_ownership_external_closure'):raise RuntimeError('HELD_UNRESOLVED_S1_OWNERSHIP_NO_RELAUNCH')
 proof=read(bind(admission['unresolved_ownership_external_closure']))
 if {p.resolve() for p in records}!={bind(x).resolve() for x in proof.get('unresolved_handoff_bindings',[])} or proof.get('status')!='S1_UNRESOLVED_OWNER_EXTERNALLY_CLOSED' or any(proof.get(k) is not True for k in ('all_recorded_identities_absent','all_groups_contexts_and_loops_closed','common_leases_released','image_unchanged')):raise RuntimeError('S1 unresolved ownership needs exact external closure')

def annotation_authority(cohort,admission):
 authority=read(bind(admission['annotation_reuse_authority']))
 if authority.get('status')!='ACCEPTED_TEN_ANNOTATIONS_AFTER_FAILED_T1_QUALITY_FOR_S1_PREPARATION' or authority.get('annotation_reuse_authorized') is not True or authority.get('prediction_execution_authorized') is not False:raise RuntimeError('Root annotation-only authority absent')
 expected={x['accession']:x['annotation_commit']['sha256'] for x in cohort['annotation_members']}
 if authority.get('accepted_annotation_commit_sha256s')!=expected:raise RuntimeError('Root authority must bind all ten exact annotation commits')
 failed=read(bind(authority['failed_quality_unit']));bind(authority['failure_closure'])
 if authority['failed_quality_unit']!=cohort['failed_T1_quality_unit'] or failed.get('elapsed_seconds')!=LIMITS['prior_failed_quality_elapsed_seconds'] or failed.get('exit_code')!=-15 or failed.get('owned_group_empty') is not True or failed.get('remaining_owned_processes')!=[]:raise RuntimeError('Prior failed quality debit/closure differs')
 # Root explicitly accepts annotation reuse despite UNKNOWN original outer-native exit.
 # No prior successful ten-genome prediction or original native exit0 is inferred here.
 for member in cohort['annotation_members']:
  commit=read(bind(member['annotation_commit']))
  if commit.get('status')!='ANNOTATION_EXIT0_VALIDATED_ATOMIC_COMMIT' or commit.get('selected_faa')!=member['selected_faa'] or commit.get('annotation_receipt')!=member['annotation_receipt'] or commit.get('unit_execution')!=member['annotation_unit_execution']:raise RuntimeError('Annotation member/commit differs')
  for k in ('selected_faa','annotation_receipt','annotation_unit_execution'):bind(member[k])
  if not unit_closed(read(bind(member['annotation_unit_execution']))):raise RuntimeError('Original annotation unit exit0/group closure required')
  verify_manifest(bind(member['annotation_commit']).parent,read(bind(commit['manifest'])))
 return authority

def resume_proof(admission,session,allow_current_budget_growth=False):
 proof=read(bind(admission['closed_row_reuse_authority']))
 if proof.get('status')!='S1_ROW_NATIVE_GROUP_NAMESPACE_IMAGE_LEASE_CLOSED' or proof.get('session_identity_sha256')!=session:raise RuntimeError('Separately closed S1 rows required for recovery')
 if any(type(proof.get(k)) is not int for k in ('native_exit_code_observed','wsl_exit_code_observed')):raise RuntimeError('S1 recovery requires actual observed outer exits, not disappearance')
 if any(proof.get(k) is not True for k in ('owned_unit_groups_empty','ordinary_runtime_closed','image_unchanged','common_leases_reacquired_released','original_artifacts_unchanged')):raise RuntimeError('S1 recovery closure/leases incomplete')
 if not isinstance(proof.get('accepted_row_commit_sha256s'),dict) or not proof['accepted_row_commit_sha256s'] or not isinstance(proof.get('closed_native_launch_tokens'),list) or not proof['closed_native_launch_tokens']:raise RuntimeError('Exact closed row/token map required')
 snapshot=bind(proof['closed_snapshot_manifest']);verify_manifest(snapshot.parent,read(snapshot))
 actual={p.resolve() for p in budget_files(OUT/'sessions'/session)};expected={bind(x).resolve() for x in proof.get('budget_bindings',[])}
 if (not expected.issubset(actual)) or (not allow_current_budget_growth and actual!=expected):raise RuntimeError('Complete prior S1 budget/terminal set differs; no debit reset')
 return proof

def plan_gate(plan_path,expected_sha,require_admission=True,closed_finalization=False):
 stop();p=path(plan_path)
 if sha(p)!=expected_sha:raise RuntimeError('S1 immutable plan differs')
 plan=read(p)
 if plan.get('schema')!='TREE2_SINGLE_FAA_INPUT_PLAN_S1' or plan.get('role')!=ROLE or plan.get('limits')!=LIMITS:raise RuntimeError('Wrong S1 scope/limits')
 cohort=read(bind(plan['cohort_contract']));inputs=cohort['inputs'];members=cohort['annotation_members']
 if cohort.get('schema')!='TREE2_SINGLE_FAA_COHORT_CONTRACT_S1' or cohort.get('limits')!=LIMITS:raise RuntimeError('S1 cohort contract limits differ')
 if plan.get('feature_schema')!=cohort.get('schema_v002'):raise RuntimeError('S1 producer/consumer feature schema binding differs')
 bind(plan['feature_schema'])
 if len(inputs)!=10 or len(members)!=10 or {x['accession'] for x in inputs}!={x['accession'] for x in members} or len({x['accession'] for x in inputs})!=10:raise RuntimeError('S1 exact original ten annotation set required')
 expected=sorted(members,key=lambda x:(-x['selected_faa']['bytes'],x['accession']))
 if cohort['inference_order']!=[x['accession'] for x in expected]:raise RuntimeError('Largest-FAA-first deterministic order differs')
 for item in read(bind(plan['source_manifest']))['sources']:bind(item)
 if not require_admission:unresolved_ownership_gate();return plan,cohort,None
 if not ADMISSION.exists():raise RuntimeError('HELD_S1_ANNOTATION_AUTHORITY_AND_ADMISSION_ABSENT')
 a=read(ADMISSION);unresolved_ownership_gate(a)
 if a.get('schema')!='TREE2_SINGLE_FAA_INFERENCE_ADMISSION_S1' or a.get('status')!='ADMITTED_ONE_SERIAL_TEN_FAA_SERIES' or a.get('role')!=ROLE or a.get('single_faa_execution_authorized') is not True or a.get('phase') not in PHASES or a.get('max_predictions_per_accession')!=1 or a.get('max_query_genomes_per_prediction')!=1:raise RuntimeError('No explicit inference-only S1 authority')
 if a.get('input_plan_sha256')!=expected_sha or a.get('source_manifest_sha256')!=plan['source_manifest']['sha256'] or a.get('cohort_contract_sha256')!=plan['cohort_contract']['sha256'] or a.get('limits')!=LIMITS:raise RuntimeError('S1 admission/source/budget binding differs')
 if any(a.get(k) is not True for k in ('annotation_reuse_gate_passed','prior_failure_context_closed','source_math_GO','resource_lifecycle_GO','monitor_standard_stage04_ready')):raise RuntimeError('S1 source/annotation/ownership/monitor gates held')
 if a.get('annotation_reuse_authority')!=cohort.get('annotation_reuse_authority'):raise RuntimeError('S1 actual Root annotation authority differs from bound cohort')
 annotation_authority(cohort,a)
 if a['phase']=='RECOVER_CLOSED_ROWS':resume_proof(a,plan['session_identity_sha256'],allow_current_budget_growth=closed_finalization)
 return plan,cohort,a
