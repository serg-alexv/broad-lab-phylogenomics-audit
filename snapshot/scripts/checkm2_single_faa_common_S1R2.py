"""HELD S1R2 gates: preserved original row plus nine new targets; no dispatch."""
import math,re
from pathlib import Path
import checkm2_single_faa_common_S1 as old
R=old.R
path=old.path;sha=old.sha;read=old.read;save=old.save;row=old.row;bind=old.bind
verify_manifest=old.verify_manifest;manifest=old.manifest;unit_closed=old.unit_closed
group_receipts_closed=old.group_receipts_closed;pending_is_current=old.pending_is_current
ROLE='SINGLE_FAA_INFERENCE_ONLY_METHOD_QC_S1R2'
LIMITS={'cpu_affinity_max': 2, 'stock_threads': 1, 'sum_group_RSS_bytes': 2147483648, 'linux_available_minimum_bytes': 1073741824, 'disk_reserve_bytes': 42949672960, 'per_genome_prediction_plus_validation_seconds': 600, 'max_logical_genomes': 10, 'max_fresh_genomes': 9, 'max_query_genomes_per_prediction': 1, 'prior_T1_failed_quality_elapsed_seconds': 104.24163487500482, 'prior_S1_actual_unit_seconds_debited': 284.5531904320087, 'new_prediction_plus_validation_seconds': 3211.205174, 'failed_second_new_per_genome_seconds': 599.056561, 'original_quality_total_seconds': 3600, 'cold_session_seconds': 6000}
PHASES=('RUN_FRESH_TARGETS',)
E=R/'evidence/checkm2_single_faa_S1R2';OUT=R/'analysis/checkm2_single_faa_S1R2'
STATE=R/'state/checkm2_single_faa_progress_S1R2.json';STEP=R/'state/checkm2_single_faa_step_S1R2.json'
LAUNCH=R/'state/launch_checkm2_single_faa_S1R2.json';ADMISSION=R/'state/checkm2_single_faa_ready_S1R2.json'
STOP=R/'state/STOP_CHECKM2_SINGLE_FAA_S1R2';UNRESOLVED_HANDOFF=E/'unresolved_ownership_handoff.json'
PRESERVED='GCA_001465115.1';SECOND='GCF_000829055.1'
TARGETS=['GCF_000829055.1', 'GCF_003795125.1', 'GCF_000164675.2', 'GCF_000016825.1', 'GCF_000224985.1', 'GCF_003264015.2', 'GCF_001543145.1', 'GCF_000014425.1', 'GCF_000014505.1']
CAPS={x:(599.056561 if x==SECOND else 600) for x in TARGETS}
ROOT_ROW_SHA='e84a54865d3abb988a9de66dde6da4243bcdc385da9e918d9b5c732762059b76'

def stop():
 if any(p.exists() for p in (R/'state/STOP',R/'state/STOP_CHECKM2_PILOT',STOP)):raise InterruptedError('S1R2/project/biological STOP; never cleared automatically')

def budget_files(session):return old.budget_files(session)

def budget(session):
 session=path(session);commands=list(session.glob('rows/*/unit_*/command.json'));allocations=set(session.glob('rows/*/unit_*_budget.json'));terminals=set(session.glob('rows/*/unit_*/execution.json'))
 if allocations!={p.parent.parent/(p.parent.name+'_budget.json') for p in commands} or terminals!={p.with_name('execution.json') for p in commands}:raise RuntimeError('S1R2 allocated/started/terminal set incomplete; no unknown debit reset')
 for claim in session.glob('rows/*/once_claim.json'):
  if not (claim.parent/'unit_quality/command.json').exists():raise RuntimeError('S1R2 once-claim start/debit unknown; no replay')
 per={};used=0.0
 for command in commands:
  acc=command.parent.parent.name
  if acc not in TARGETS or acc==PRESERVED:raise RuntimeError('Only nine authorized fresh targets may consume current-source units')
  execution=read(command.with_name('execution.json'));elapsed=execution.get('elapsed_seconds')
  if type(elapsed) not in (int,float) or not math.isfinite(elapsed) or elapsed<0 or execution.get('owned_group_empty') is not True or execution.get('remaining_owned_processes')!=[]:raise RuntimeError('S1R2 elapsed/owned-group proof missing')
  used+=elapsed;per[acc]=per.get(acc,0.0)+elapsed
 if len(per)>9 or any(value>CAPS[acc] for acc,value in per.items()) or used>3211.205174:raise RuntimeError('S1R2 historical/per-target/global allowance exhausted')
 return {'prior_T1_failed_quality_seconds':104.24163487500482,'prior_S1_actual_unit_seconds_debited':284.5531904320087,'new_seconds_debited':used,'remaining_seconds':3211.205174-used,'per_genome_seconds':per,'per_target_new_time_caps':CAPS,'new_ceiling_seconds':3211.205174,'original_total_seconds':3600,'total_campaign_seconds_debited':104.24163487500482+284.5531904320087+used}

def unresolved_ownership_gate(admission=None):
 records=list((E/'unresolved_ownership').glob('*.json'))
 if UNRESOLVED_HANDOFF.exists():records.append(UNRESOLVED_HANDOFF)
 if not records:return
 if not admission or not admission.get('unresolved_ownership_external_closure'):raise RuntimeError('HELD_UNRESOLVED_S1R2_OWNER_NO_RELAUNCH')
 proof=read(bind(admission['unresolved_ownership_external_closure']))
 if {p.resolve() for p in records}!={bind(x).resolve() for x in proof.get('unresolved_handoff_bindings',[])} or proof.get('status')!='S1R2_UNRESOLVED_OWNER_EXTERNALLY_CLOSED' or any(proof.get(k) is not True for k in ('all_recorded_identities_absent','all_groups_contexts_and_loops_closed','common_leases_released','image_unchanged')):raise RuntimeError('Exact external unresolved-owner closure required')

def preserved_row_gate(cohort,authority_row):
 if authority_row!=cohort['preserved_row_authority'] or authority_row['sha256']!=ROOT_ROW_SHA:raise RuntimeError('Actual Root original-row authority differs')
 authority=read(bind(authority_row))
 if (authority.get('schema')!='TREE2_ROOT_S1_CLOSED_ROW_ONLY_AUTHORITY' or authority.get('status')!='S1_ROW_NATIVE_GROUP_NAMESPACE_IMAGE_LEASE_CLOSED' or authority.get('method_estimate_reuse_authorized') is not True or authority.get('recalculate_accepted_row_authorized') is not False or authority.get('prediction_execution_authorized') is not False or authority.get('cohort_success_or_ten_genome_batch_pass') is not False):raise RuntimeError('Only separately accepted original row reuse is authorized')
 if any(type(authority.get(k)) is not int for k in ('native_exit_code_observed','wsl_exit_code_observed')) or any(authority.get(k) is not True for k in ('owned_unit_groups_empty','ordinary_runtime_closed','image_unchanged','common_leases_reacquired_released','original_artifacts_unchanged')):raise RuntimeError('Actual prior nonzero outer/group/context/image/lease closure required')
 for key in ('mixed_failure_closure','closure_auditor_external_closure','actual_Root_exit_observation'):bind(authority[key])
 snapshot=bind(authority['closed_snapshot_manifest']);verify_manifest(snapshot.parent,read(snapshot))
 oldsession=old.OUT/'sessions'/authority['session_identity_sha256']
 actual={p.resolve() for p in old.budget_files(oldsession)};expected={bind(x).resolve() for x in authority['budget_bindings']}
 if actual!=expected:raise RuntimeError('All nine prior command/terminal/allocation files must stay intact')
 previous=old.budget(oldsession)
 if previous!=authority['debit_budget'] or previous['new_seconds_debited']!=284.5531904320087 or authority.get('conservative_new_global_remaining_seconds')!=3211.205174 or authority.get('failed_second_conservative_per_genome_remaining_seconds')!=599.056561:raise RuntimeError('Actual historical debit set/remaining allowance differs')
 bind(cohort['old_failed_second_once_claim']);failed=read(bind(cohort['old_failed_second_quality_unit']))
 if failed.get('exit_code')!=-15 or failed.get('owned_group_empty') is not True or failed.get('elapsed_seconds')!=0.9434388670051703:raise RuntimeError('Original failed second attempt/debit must remain preserved')
 accepted=authority['accepted_row']
 if accepted['accession']!=PRESERVED or authority['accepted_row_commit_sha256s']!={PRESERVED:accepted['row_commit']['sha256']}:raise RuntimeError('Exactly one original accepted row is permitted')
 commit_path=bind(accepted['row_commit']);commit=read(commit_path)
 if commit.get('binding')!=accepted['original_binding'] or commit.get('native_launch_token') not in authority['closed_native_launch_tokens'] or commit.get('status')!='SINGLE_FAA_EXIT0_FEATURES_VALIDATED_PENDING_NATIVE_CLOSURE':raise RuntimeError('Original source binding/native token/row commit must remain original')
 verify_manifest(commit_path.parent,read(bind(commit['manifest'])))
 for key in ('quality_unit_execution','validation_unit_execution'):
  if commit[key]!=accepted[key] or not unit_closed(read(bind(accepted[key]))):raise RuntimeError('Original first row has no genuine typed exit0/group proof')
 if commit['feature_validation']!=accepted['feature_validation']:raise RuntimeError('Original feature receipt differs')
 features=read(bind(accepted['feature_validation']))
 if (features.get('status')!='SINGLE_FAA_FEATURES_S1_PASS_PENDING_NATIVE_CLOSURE' or features.get('accession')!=PRESERVED or features.get('source_manifest_sha256')!=accepted['original_binding']['source_manifest_sha256'] or features.get('input_plan_sha256')!=accepted['original_binding']['input_plan_sha256'] or features.get('finite_domain_features')!=21241 or features.get('exact_FAA_metadata_features')!=22 or features.get('independently_recomputed_membership_features')!=1220 or features.get('membership_mismatches')!=0):raise RuntimeError('Original validated features/source cannot be rewritten as new-source output')
 return {'accession':PRESERVED,'origin':'PRESERVED_ROOT_ACCEPTED_ORIGINAL_S1_ROW','commit':accepted['row_commit'],'feature_validation':accepted['feature_validation'],'quality_unit_execution':accepted['quality_unit_execution'],'validation_unit_execution':accepted['validation_unit_execution'],'original_binding':accepted['original_binding'],'root_reuse_authority':authority_row,'reused':True,'new_inference_invoked':False}

def current_failed_run(step,token,input_plan_sha,protocol_sha):
 locator=OUT/'runs_by_token'/(token+'.json')
 if locator.exists():
  owned=read(locator)
  if owned.get('launch_token')!=token or owned.get('input_plan_sha256')!=input_plan_sha or owned.get('protocol_admission_sha256')!=protocol_sha:raise RuntimeError('Required per-token run locator differs')
  run=path(owned['run_directory']);bind(owned['binding'])
 elif isinstance(step,dict) and step.get('windows_launch_token')==token and step.get('input_plan_sha256')==input_plan_sha and step.get('protocol_admission_sha256')==protocol_sha and isinstance(step.get('run_directory'),str) and step['run_directory']:
  run=path(step['run_directory'])
 else:return None
 if run.parent!=OUT/'runs':raise RuntimeError('S1R2 failed run locator escapes owned root')
 record=read(run/'binding.json');failure=read(run/'failure.json');units=read(run/'invocations.json');launch=record.get('launch',{})
 if launch.get('token')!=token or launch.get('input_plan_sha256')!=input_plan_sha or launch.get('protocol_admission_sha256')!=protocol_sha or record.get('admission',{}).get('sha256')!=protocol_sha or record.get('plan',{}).get('_sha')!=input_plan_sha:raise RuntimeError('Required S1R2 failed-run binding differs')
 if failure.get('status')!='S1R2_FAILED_NO_AUTOMATIC_RETRY_OR_FALLBACK' or failure.get('annotation_invoked') is not False or not isinstance(units,list):raise RuntimeError('Required failed-run evidence absent')
 for unit in units:
  if not path(unit).is_relative_to(OUT/'sessions'/record['plan']['session_identity_sha256']/'rows'):raise RuntimeError('Invocation escapes current fresh-target session')
 return run

def observer_proof_gate(plan,admission):
 proof=read(bind(admission['observer_boundary_proof']))
 if proof.get('schema')!='TREE2_S1R2_OBSERVER_BOUNDARY_PROOF_CLOSED_V001' or proof.get('status')!='S1R2_NON_GENOMIC_OBSERVER_BOUNDARY_PASS_CLOSED':raise RuntimeError('Actual externally closed observer capability proof required')
 if any(type(proof.get(k)) is not int or proof[k]!=0 for k in ('actual_native_exit_code_observed','actual_wsl_exit_code_observed')) or any(proof.get(k) is not True for k in ('all_proof_owned_identities_absent','common_leases_reacquired_and_released','no_genomes_models_mounts_or_image_reads')) or proof.get('historical_cause_proved') is not False:raise RuntimeError('Observer proof actual exit/ownership/lease/limited-scope closure absent')
 if proof.get('source_plan')!=plan['observer_boundary_proof_plan']:raise RuntimeError('Observer proof source-plan binding differs')
 bind(proof['source_plan']);sources={x['path']:x for x in read(bind(plan['source_manifest']))['sources']}
 if proof.get('observer_source')!=sources['scripts/checkm2_unit_observer_S1R2.py'] or proof.get('optional_helper_source')!=sources['scripts/checkm2_optional_progress_S1R2.py']:raise RuntimeError('Exact observer/helper capability proof differs from scientific source cut')
 bind(proof['observer_source']);bind(proof['optional_helper_source']);native=read(bind(proof['native_result']));linux=read(bind(proof['linux_result']))
 if native.get('status')!='S1R2_NON_GENOMIC_PROOF_PENDING_EXTERNAL_NATIVE_EXIT' or type(native.get('actual_wsl_exit_code')) is not int or native['actual_wsl_exit_code']!=0 or native.get('linux_result_sha256')!=proof['linux_result']['sha256'] or native.get('source_plan_sha256')!=proof['source_plan']['sha256'] or native.get('common_Windows_lease_release_errors')!=[]:raise RuntimeError('Actual proof native receipt differs')
 if linux.get('status')!='S1R2_NON_GENOMIC_PROOF_PASS_CLOSED' or linux.get('owned_cleanup',{}).get('closure_proven') is not True or linux['owned_cleanup'].get('forced_action') is not False or linux.get('source_plan_sha256')!=proof['source_plan']['sha256']:raise RuntimeError('Proof Linux helper/descendant ordinary closure absent')
 return proof

def plan_gate(plan_path,expected_sha,require_admission=True,closed_finalization=False):
 stop();p=path(plan_path)
 if sha(p)!=expected_sha:raise RuntimeError('S1R2 immutable plan SHA differs')
 plan=read(p)
 if plan.get('schema')!='TREE2_SINGLE_FAA_INPUT_PLAN_S1R2' or plan.get('role')!=ROLE or plan.get('limits')!=LIMITS:raise RuntimeError('S1R2 scope/limits differ')
 cohort=read(bind(plan['cohort_contract']))
 if cohort.get('schema')!='TREE2_SINGLE_FAA_COHORT_CONTRACT_S1R2' or cohort.get('limits')!=LIMITS or cohort.get('fresh_target_accessions')!=TARGETS or cohort.get('preserved_accessions')!=[PRESERVED] or cohort.get('per_target_new_time_caps')!=CAPS:raise RuntimeError('Preserved1/fresh9 cohort/caps differ')
 inputs=cohort['inputs'];members=cohort['annotation_members'];expected={x['accession'] for x in inputs}
 if len(inputs)!=10 or len(members)!=10 or len(expected)!=10 or expected!={PRESERVED,*TARGETS} or {x['accession'] for x in members}!=expected:raise RuntimeError('Original logical ten annotation set must stay exact')
 if plan.get('feature_schema')!=cohort.get('schema_v002'):raise RuntimeError('Exact schema producer/consumer binding required')
 bind(plan['feature_schema'])
 if cohort['inference_order']!=[x['accession'] for x in sorted((x for x in members if x['accession'] in TARGETS),key=lambda x:(-x['selected_faa']['bytes'],x['accession']))]:raise RuntimeError('Fresh-target largest-first order differs')
 for item in read(bind(plan['source_manifest']))['sources']:bind(item)
 if not require_admission:unresolved_ownership_gate();return plan,cohort,None
 if not ADMISSION.exists():raise RuntimeError('HELD_S1R2_SEPARATE_REPAIR_AUTHORITY_ABSENT')
 a=read(ADMISSION);unresolved_ownership_gate(a)
 if a.get('schema')!='TREE2_SINGLE_FAA_INFERENCE_ADMISSION_S1R2' or a.get('status')!='ADMITTED_ONE_OPERATIONAL_REPAIR_NINE_FAA_SERIES' or a.get('role')!=ROLE or a.get('single_faa_execution_authorized') is not True or a.get('phase')!='RUN_FRESH_TARGETS' or a.get('max_predictions_per_accession')!=1 or a.get('max_new_predictions')!=9 or a.get('max_query_genomes_per_prediction')!=1:raise RuntimeError('Explicit one new attempt per target/9 maximum authority required')
 if a.get('input_plan_sha256')!=expected_sha or a.get('source_manifest_sha256')!=plan['source_manifest']['sha256'] or a.get('cohort_contract_sha256')!=plan['cohort_contract']['sha256'] or a.get('limits')!=LIMITS:raise RuntimeError('Repair/source/time bindings differ')
 if any(a.get(k) is not True for k in ('preserved_row_reuse_gate_passed','explicit_second_attempt_exception','annotation_reuse_gate_passed','prior_failure_context_closed','source_math_GO','resource_lifecycle_GO','monitor_standard_stage04_ready')):raise RuntimeError('S1R2 required Root/source/resource gates held')
 if a.get('annotation_reuse_authority')!=cohort['annotation_reuse_authority']:raise RuntimeError('Original ten annotation authority differs')
 old.annotation_authority(cohort,a);preserved_row_gate(cohort,a['preserved_row_authority']);observer_proof_gate(plan,a)
 return plan,cohort,a
