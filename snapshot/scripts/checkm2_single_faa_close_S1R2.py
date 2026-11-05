"""HELD file-only compound close: original accepted one plus current fresh nine."""
import datetime,time
import checkm2_single_faa_common_S1R2 as c
from checkm2_optional_progress_S1R2 import safe_call

def feature_summary(features,member,origin):
 return {'accession':member['accession'],'origin':origin,'Completeness':features['Completeness'],'Contamination':features['Contamination'],'source_holds_preserved':features['source_holds_preserved'],'feature_validation':member['feature_validation'],'quality_unit_execution':member['quality_unit_execution'],'validation_unit_execution':member['validation_unit_execution'],'commit':member['commit'],'production_acceptance':'NOT_GRANTED'}

def compound_rows(result,preserved,targets,logical_names):
 rows=result.get('rows',[]);fresh=result.get('fresh_rows',[])
 if any(type(result.get(k)) is not int for k in ('completed_qc_rows','preserved_count','fresh_count')) or result.get('completed_qc_rows')!=10 or result.get('preserved_count')!=1 or result.get('fresh_count')!=9 or result.get('preserved_rows')!=[preserved] or len(fresh)!=9 or {x['accession'] for x in fresh}!=set(targets) or rows!=[preserved,*fresh] or len(rows)!=10 or {x['accession'] for x in rows}!=set(logical_names):raise RuntimeError('Compound exact one original plus nine fresh rows required')
 return rows,fresh

def finalize(plan_path,plan_sha,external_closure):
 start=time.monotonic();plan,cohort,admission=c.plan_gate(plan_path,plan_sha,closed_finalization=True);proof=c.read(c.bind(external_closure));launch=c.read(c.LAUNCH);execution_path=c.E/'execution_pending_owner_exit.json';execution=c.read(execution_path)
 if proof.get('status')!='S1R2_COMPOUND_NATIVE_GROUP_NAMESPACE_IMAGE_LEASE_CLOSED' or proof.get('native_owner')!=launch['native_owner']:raise RuntimeError('Current S1R2 actual native identity/closure absent')
 if any(type(proof.get(k)) is not int or proof[k]!=0 for k in ('native_exit_code_observed','wsl_exit_code_observed')):raise RuntimeError('Current actual native/WSL zero exits required; old S1 nonzero exits remain historical')
 if any(proof.get(k) is not True for k in ('owned_unit_groups_empty','ordinary_runtime_closed','image_unchanged','common_leases_reacquired_released','original_artifacts_unchanged')):raise RuntimeError('Current child/context/image/lease closure incomplete')
 if proof.get('execution_sha256')!=c.sha(execution_path) or proof.get('input_plan_sha256')!=plan_sha or proof.get('protocol_admission_sha256')!=c.sha(c.ADMISSION) or proof.get('session_identity_sha256')!=plan['session_identity_sha256']:raise RuntimeError('Current closure/source/session binding differs')
 snapshot=c.bind(proof['closed_snapshot_manifest']);c.verify_manifest(snapshot.parent,c.read(snapshot))
 if execution.get('status')!='S1R2_OUTPUTS_CLOSED_PENDING_OBSERVED_OWNER_EXIT_REVIEW' or execution.get('all_started_unit_groups_closed') is not True or type(execution.get('wsl_child_exit_code')) is not int or execution['wsl_child_exit_code']!=0:raise RuntimeError('Current guest outputs/actual closure unproved')
 pending=c.read(c.OUT/'latest_pending_native.json');run=c.path(pending['run_directory']);manifest=c.path(pending['manifest_path'])
 if not c.pending_is_current(pending,launch['token'],plan_sha,c.sha(c.ADMISSION),c.E/'namespace_runs'/(launch['token']+'.json')) or c.sha(manifest)!=pending['manifest_sha256']:raise RuntimeError('Current pointer/manifest is stale')
 c.verify_manifest(run,c.read(manifest));result=c.read(run/'result.json')
 if result.get('status')!='S1R2_CORE_PENDING_NAMESPACE_NATIVE_CLOSURE' or result.get('annotation_functions_invoked') is not False or result.get('maximum_query_genomes_per_prediction')!=1 or result.get('protocol_admission_sha256')!=c.sha(c.ADMISSION) or result.get('input_plan_sha256')!=plan_sha or result.get('session_identity_sha256')!=plan['session_identity_sha256']:raise RuntimeError('Inference-only current result binding differs')
 expected={x['accession']:x for x in cohort['inputs']};annotation={x['accession']:x for x in cohort['annotation_members']};rows=result.get('rows',[]);fresh=result.get('fresh_rows',[]);preserved=c.preserved_row_gate(cohort,admission['preserved_row_authority'])
 rows,fresh=compound_rows(result,preserved,c.TARGETS,expected)
 quality_paths=set();validation_paths=set();feature_paths=set();summary=[];row_map={};holds=[]
 original_features=c.read(c.bind(preserved['feature_validation']))
 if original_features.get('source_holds_preserved')!=expected[c.PRESERVED]['source_holds_preserved']:raise RuntimeError('Original accepted row source mask changed')
 summary.append(feature_summary(original_features,preserved,preserved['origin']));row_map[c.PRESERVED]=original_features['canonical_float64_le_row_sha256']
 quality_paths.add(c.bind(preserved['quality_unit_execution']));validation_paths.add(c.bind(preserved['validation_unit_execution']));feature_paths.add(c.bind(preserved['feature_validation']))
 if original_features['source_holds_preserved']:holds.append(c.PRESERVED)
 for member in fresh:
  acc=member['accession'];p=c.bind(member['commit']);commit=c.read(p)
  if member.get('origin')!='FRESH_CURRENT_S1R2_ROW' or member.get('reused') is not False or p!=c.OUT/'sessions'/plan['session_identity_sha256']/'rows'/acc/'commit.json' or commit.get('status')!='SINGLE_FAA_S1R2_EXIT0_FEATURES_VALIDATED_PENDING_NATIVE_CLOSURE' or commit.get('native_launch_token')!=launch['token']:raise RuntimeError('Fresh current per-target commit/token absent')
  binding=commit['binding']
  if binding.get('member')!=annotation[acc] or binding.get('input_plan_sha256')!=plan_sha or binding.get('source_manifest_sha256')!=plan['source_manifest']['sha256'] or binding.get('session_identity_sha256')!=plan['session_identity_sha256'] or binding.get('annotation_reuse_authority')!=admission['annotation_reuse_authority'] or binding.get('preserved_row_authority')!=admission['preserved_row_authority'] or binding.get('prediction_genome_count')!=1 or binding.get('annotation_invoked') is not False:raise RuntimeError('Fresh own annotation/source/Root bindings differ')
  c.verify_manifest(p.parent,c.read(c.bind(commit['manifest'])))
  for key,seen,unit in [('quality_unit_execution',quality_paths,'unit_quality'),('validation_unit_execution',validation_paths,'unit_feature_validation')]:
   q=c.bind(commit[key]);seen.add(q)
   if member.get(key)!=commit[key] or q!=p.parent/unit/'execution.json' or not c.unit_closed(c.read(q)):raise RuntimeError('Fresh genuine typed exit0/group receipt required')
  f=c.bind(commit['feature_validation']);feature_paths.add(f);features=c.read(f)
  if member.get('feature_validation')!=commit['feature_validation'] or f!=p.parent/'feature_validation.json' or features.get('status')!='SINGLE_FAA_FEATURES_S1R2_PASS_PENDING_NATIVE_CLOSURE' or features.get('row_count')!=1 or features.get('accession')!=acc or features.get('finite_domain_features')!=21241 or features.get('exact_FAA_metadata_features')!=22 or features.get('independently_recomputed_membership_features')!=1220 or features.get('membership_mismatches')!=0:raise RuntimeError('Fresh own exact feature validation required')
  if features.get('source_holds_preserved')!=expected[acc]['source_holds_preserved'] or features.get('input_plan_sha256')!=plan_sha or features.get('source_manifest_sha256')!=plan['source_manifest']['sha256'] or features.get('cohort_contract_sha256')!=plan['cohort_contract']['sha256']:raise RuntimeError('Fresh source/cohort/mask bindings changed')
  if features['source_holds_preserved']:holds.append(acc)
  row_map[acc]=features['canonical_float64_le_row_sha256'];summary.append(feature_summary(features,member,member['origin']))
 if len(quality_paths)!=10 or len(validation_paths)!=10 or len(feature_paths)!=10 or sorted(holds)!=sorted(cohort['expected_source_hold_accessions']):raise RuntimeError('Ten genuine logical receipts/source masks missing')
 session=c.OUT/'sessions'/plan['session_identity_sha256'];budget=c.budget(session)
 if len(list(session.glob('rows/*/unit_quality/command.json')))!=9 or len(list(session.glob('rows/*/unit_feature_validation/command.json')))!=9 or (session/'rows'/c.PRESERVED).exists():raise RuntimeError('Exactly nine current predictions+validators and no original-row replay required')
 destination=c.E/'closed_phases'/c.sha(c.ADMISSION);destination.mkdir(parents=True,exist_ok=False)
 output={'status':'S1R2_COMPOUND_METHOD_ESTIMATES_PASS_CLOSED','input_plan_sha256':plan_sha,'cohort_contract':plan['cohort_contract'],'annotation_reuse_authority':admission['annotation_reuse_authority'],'preserved_row_authority':admission['preserved_row_authority'],'preserved_count':1,'fresh_count':9,'rows':summary,'canonical_accession_row_hashes':row_map,'finite_domain_features_total':212410,'exact_FAA_metadata_features_total':220,'independently_recomputed_membership_features_total':12200,'membership_mismatches':0,'actual_original_unit_receipts':2,'actual_current_unit_receipts':18,'budget':budget,'external_closure':external_closure,'prediction_genomes_per_call':1,'original_S1_whole_phase_success':False,'original_ten_genome_batch_resource_benchmark_passed':False,'annotation_functions_invoked':False,'source_taxonomy_or_production_panel_acceptance':False,'unknown_failed_unstarted_as_negative':False}
 if time.monotonic()-start>600:raise TimeoutError('External file-only compound close exceeded600s')
 c.save(destination/'cohort_measurements.json',output)
 authority={**proof,'status':'S1R2_COMPOUND_NATIVE_GROUP_NAMESPACE_IMAGE_LEASE_CLOSED','preserved_original_row_authority':admission['preserved_row_authority'],'fresh_current_row_commit_sha256s':{x['accession']:x['commit']['sha256'] for x in fresh},'logical_row_commit_sha256s':{x['accession']:x['commit']['sha256'] for x in rows},'current_closed_native_launch_tokens':[launch['token']],'prior_and_current_tokens_kept_separate':True,'budget_bindings':[c.row(p) for p in sorted(c.budget_files(session))],'continuation_execution_authorized':False,'production_panel_acceptance':False}
 c.save(destination/'closed_compound_authority.json',authority);c.save(c.OUT/'latest_closed_series.json',c.row(destination/'cohort_measurements.json'))
 progress={'status':'PENDING_SOURCE_TAXONOMY_AND_COHORT_QC','detail':'One original accepted estimate plus nine fresh estimates closed; source/taxonomy/panel review remains held','done':10,'total':10,'unit':'validated single-FAA QC commits','updated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'operation':'SINGLE_FAA_S1R2_CLOSED','diagnostic':c.row(destination/'cohort_measurements.json'),'production_panel_acceptance':False,'pid':None,'creation_time_utc':None}
 safe_call(c.save,c.STATE,progress);safe_call(c.save,c.R/'state/stages/04.json',{'id':'04','name':'Independent biological QC',**progress});return output
