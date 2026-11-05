"""HELD N1 external file-only close; cannot observe or invent the native owner's future exit."""
import math,time
import checkm2_phase_separated_common_N1 as c

def finalize(plan_path,plan_sha,external_closure):
 start=time.monotonic();plan,recipe,admission=c.plan_gate(plan_path,plan_sha,closed_finalization=True);proof=c.read(c.bind(external_closure));launch=c.read(c.LAUNCH);ep=c.E/'execution_pending_owner_exit.json';execution=c.read(ep)
 if proof.get('status')!='N1_METHOD_NATIVE_GROUP_NAMESPACE_IMAGE_LEASE_CLOSED' or proof.get('native_owner')!=launch['native_owner']:raise RuntimeError('Actual current N1 owner closure required')
 if any(type(proof.get(k))is not int or proof[k]!=0 for k in ('native_exit_code_observed','wsl_exit_code_observed')):raise RuntimeError('Observed actual N1 native/WSL zero required')
 if any(proof.get(k)is not True for k in ('owned_unit_groups_empty','ordinary_runtime_closed','image_unchanged','common_leases_reacquired_released','original_artifacts_unchanged')):raise RuntimeError('Actual group/ordinary namespace/image/lease proof required')
 if proof.get('execution_sha256')!=c.sha(ep) or proof.get('input_plan_sha256')!=plan_sha or proof.get('protocol_admission_sha256')!=c.sha(c.ADMISSION) or proof.get('session_identity_sha256')!=plan['session_identity_sha256']:raise RuntimeError('External current bindings differ')
 snapshot=c.bind(proof['closed_snapshot_manifest']);c.verify_manifest(snapshot.parent,c.read(snapshot))
 if execution.get('status')!='N1_OUTPUTS_CLOSED_PENDING_OBSERVED_OWNER_EXIT_REVIEW' or execution.get('all_started_unit_groups_closed')is not True or type(execution.get('wsl_child_exit_code'))is not int or execution['wsl_child_exit_code']!=0:raise RuntimeError('Required successful guest result missing')
 pending=c.read(c.OUT/'latest_pending_native.json');run=c.path(pending['run_directory']);manifest=c.path(pending['manifest_path'])
 if run.parent!=c.OUT/'runs' or not c.pending_is_current(pending,launch['token'],plan_sha,c.sha(c.ADMISSION),c.E/'namespace_runs'/(launch['token']+'.json')) or c.sha(manifest)!=pending['manifest_sha256']:raise RuntimeError('N1 pending pointer is stale')
 c.verify_manifest(run,c.read(manifest));result=c.read(run/'result.json');acc=recipe['input']['accession']
 if result.get('status')!='N1_CORE_PENDING_NAMESPACE_NATIVE_CLOSURE' or type(result.get('completed_qc_rows'))is not int or result['completed_qc_rows']!=1 or not isinstance(result.get('rows'),list) or len(result['rows'])!=1 or result['rows'][0].get('accession')!=acc or result['rows'][0].get('origin')!='FRESH_NOVEL_PHASE_SEPARATED_N1':raise RuntimeError('Exactly one fresh own N1 result required')
 if result.get('input_plan_sha256')!=plan_sha or result.get('protocol_admission_sha256')!=c.sha(c.ADMISSION) or result.get('session_identity_sha256')!=plan['session_identity_sha256'] or result.get('previously_accepted_rows_recalculated')is not False:raise RuntimeError('Novel/source/context result differs')
 row=result['rows'][0];commit=c.read(c.bind(row['commit']))
 if c.bind(row['commit'])!=run/'commit.json' or commit.get('status')!='N1_FRESH_PHASE_SEPARATED_ROW_VALIDATED_PENDING_NATIVE_CLOSURE' or commit.get('accession')!=acc or commit.get('input_plan_sha256')!=plan_sha or commit.get('source_manifest_sha256')!=plan['source_manifest']['sha256'] or commit.get('native_launch_token')!=launch['token']:raise RuntimeError('Fresh current source/input commit absent')
 expected={name:c.row(run/name/'execution.json') for name in c.UNITS}
 if commit.get('unit_executions')!=expected or any(not c.unit_closed(c.read(c.bind(value))) for value in expected.values()):raise RuntimeError('Four genuine typed exit0/group receipts required')
 if set(c.read(run/'invocations.json'))!={str(run/name) for name in c.UNITS} or len(c.read(run/'invocations.json'))!=4:raise RuntimeError('No omitted, repeated or extra phase invocation allowed')
 ann=c.read(c.bind(commit['annotation_commit']));search=c.read(c.bind(commit['diamond_commit']));prediction=c.read(c.bind(commit['prediction_commit']));features=c.read(c.bind(commit['feature_validation']))
 if ann.get('status')!='N1_ANNOTATION_UNIT0_COMMITTED_PENDING_CONTEXT_CLOSURE' or search.get('status')!='N1_DIAMOND_UNIT0_COMMITTED_PENDING_CONTEXT_CLOSURE' or prediction.get('status')!='N1_STOCK_RESUME_EXIT0_FEATURE_VALIDATION_PENDING':raise RuntimeError('All three committed phase interfaces required')
 for part in (ann,search,prediction):
  p=c.bind(part['manifest']);c.verify_manifest(p.parent,c.read(p))
 if ann.get('unit_execution')!=expected['unit_annotation'] or search.get('unit_execution')!=expected['unit_diamond'] or prediction.get('unit_execution')!=expected['unit_resume'] or ann.get('selected_faa')!=search.get('selected_faa') or prediction.get('fresh_search_commit')!=commit['diamond_commit']:raise RuntimeError('Own phase provenance/FAA/source differs')
 if row['feature_validation']!=commit['feature_validation'] or features.get('status')!='N1_FEATURES_PASS_PENDING_NATIVE_CLOSURE' or features.get('accession')!=acc or features.get('row_count')!=1 or features.get('finite_domain_features')!=21241 or features.get('exact_FAA_metadata_features')!=22 or features.get('independently_recomputed_membership_features')!=1220 or features.get('membership_mismatches')!=0:raise RuntimeError('All corrected own-row features required')
 if features.get('source_FAA_sha256')!=ann['selected_faa']['sha256'] or features.get('source_manifest_sha256')!=plan['source_manifest']['sha256'] or features.get('input_plan_sha256')!=plan_sha or features.get('scientific_recipe_sha256')!=plan['scientific_recipe']['sha256'] or features.get('quality_unit_execution_sha256')!=expected['unit_resume']['sha256']:raise RuntimeError('Exact own row/recipe/FAA bindings required')
 for key in ('source_holds_preserved','source_pending_reasons','source_masks'):
  if features.get(key)!=recipe['input'][key] or commit.get(key)!=recipe['input'][key]:raise RuntimeError('Source holds/pending masks changed')
 for key in ('Completeness','Contamination'):
  if type(features.get(key))not in (int,float) or not math.isfinite(features[key]):raise RuntimeError('Finite own method estimate required')
 budget=c.budget(run)
 if result.get('budget')!=budget:raise RuntimeError('Actual four-unit debit changed')
 if time.monotonic()-start>600:raise TimeoutError('N1 external file-only close exceeded600s')
 destination=c.E/'closed_phases'/c.sha(c.ADMISSION);destination.mkdir(parents=True,exist_ok=False)
 output={'status':'N1_PHASE_SEPARATED_FEASIBILITY_ESTIMATE_PASS_CLOSED','accession':acc,'input_plan_sha256':plan_sha,'scientific_recipe':plan['scientific_recipe'],'source_manifest':plan['source_manifest'],'external_closure':external_closure,'row_commit':row['commit'],'feature_validation':commit['feature_validation'],'actual_phase_units':expected,'canonical_float64_le_row_sha256':features['canonical_float64_le_row_sha256'],'Completeness':features['Completeness'],'Contamination':features['Contamination'],'finite_domain_features':21241,'exact_FAA_metadata_features':22,'independently_recomputed_membership_features':1220,'membership_mismatches':0,'source_holds_preserved':features['source_holds_preserved'],'source_pending_reasons':features['source_pending_reasons'],'source_masks':features['source_masks'],'budget':budget,'previously_accepted_rows_recalculated':False,'model_route_numerical_equivalence_to_separate_same_DNA_run_measured':False,'source_taxonomy_or_production_panel_acceptance':False,'unknown_failed_unstarted_as_negative':False,'continuation_or_fallback_execution_authorized':False}
 c.save(destination/'feasibility_measurement.json',output);c.save(c.OUT/'latest_closed_feasibility.json',c.row(destination/'feasibility_measurement.json'));return output
