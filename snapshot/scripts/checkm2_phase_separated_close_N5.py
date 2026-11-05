"""N5 file-only external close: exactly five independently validated serial rows,20 real units."""
import math,time
import checkm2_phase_separated_common_N5 as c

def normalized_invocations(values,expected):
 if not isinstance(values,list)or len(values)!=20 or len({c.path(x)for x in values})!=20 or {c.path(x)for x in values}!=set(expected):raise RuntimeError('N5 exact20 genuine normalized phase invocations required')
 return [c.path(x)for x in values]

def finalize(plan_path,plan_sha,external_closure):
 start=time.monotonic();plan,recipe,admission=c.plan_gate(plan_path,plan_sha,closed_finalization=True);proof=c.read(c.bind(external_closure));launch=c.read(c.LAUNCH);ep=c.E/'execution_pending_owner_exit.json';execution=c.read(ep)
 if proof.get('status')!='N5_METHOD_NATIVE_GROUP_NAMESPACE_IMAGE_LEASE_CLOSED'or proof.get('native_owner')!=launch['native_owner']:raise RuntimeError('N5 actual current owner closure required')
 if any(type(proof.get(k))is not int or proof[k]!=0 for k in('native_exit_code_observed','wsl_exit_code_observed')):raise RuntimeError('Observed actual N5 native/WSL0 required')
 if any(proof.get(k)is not True for k in('owned_unit_groups_empty','ordinary_runtime_closed','image_unchanged','common_leases_reacquired_released','original_artifacts_unchanged')):raise RuntimeError('N5 group/ordinary namespace/image/lease proof incomplete')
 if proof.get('execution_sha256')!=c.sha(ep)or proof.get('input_plan_sha256')!=plan_sha or proof.get('protocol_admission_sha256')!=c.sha(c.ADMISSION)or proof.get('session_identity_sha256')!=plan['session_identity_sha256']:raise RuntimeError('N5 external current bindings differ')
 snapshot=c.bind(proof['closed_snapshot_manifest']);c.verify_manifest(snapshot.parent,c.read(snapshot))
 if execution.get('status')!='N5_OUTPUTS_CLOSED_PENDING_OBSERVED_OWNER_EXIT_REVIEW'or execution.get('all_started_unit_groups_closed')is not True or type(execution.get('wsl_child_exit_code'))is not int or execution['wsl_child_exit_code']!=0:raise RuntimeError('N5 actual successful guest closure absent')
 pending=c.read(c.OUT/'latest_pending_native.json');run=c.path(pending['run_directory']);manifest=c.path(pending['manifest_path'])
 if run.parent!=c.OUT/'runs'or not c.pending_is_current(pending,launch['token'],plan_sha,c.sha(c.ADMISSION),c.E/'namespace_runs'/(launch['token']+'.json'))or c.sha(manifest)!=pending['manifest_sha256']:raise RuntimeError('N5 pending pointer stale')
 c.verify_manifest(run,c.read(manifest));result=c.read(run/'result.json');expected_names=recipe['inference_order'];rows=result.get('rows')
 if result.get('status')!='N5_CORE_PENDING_NAMESPACE_NATIVE_CLOSURE'or type(result.get('completed_qc_rows'))is not int or result['completed_qc_rows']!=5 or not isinstance(rows,list)or len(rows)!=5 or [x['accession']for x in rows]!=expected_names or len(set(expected_names))!=5:raise RuntimeError('N5 exact five own rows in selected serial order required')
 if result.get('input_plan_sha256')!=plan_sha or result.get('protocol_admission_sha256')!=c.sha(c.ADMISSION)or result.get('session_identity_sha256')!=plan['session_identity_sha256']or result.get('previously_accepted_rows_recalculated')is not False or result.get('strict_serial_four_phases_per_input')is not True or result.get('model_batch_genomes_per_invocation')!=1:raise RuntimeError('N5 serial/fresh/source context differs')
 expected_units=set();summary=[];hashes={};contexts={x['accession']:x for x in recipe['inputs']}
 for member in rows:
  acc=member['accession'];item=contexts[acc];folder=run/'rows'/acc
  if member.get('origin')!='FRESH_NOVEL_PHASE_SEPARATED_N5'or c.bind(member['commit'])!=folder/'commit.json':raise RuntimeError('N5 own fresh row location differs')
  commit=c.read(c.bind(member['commit']))
  if commit.get('status')!='N5_FRESH_PHASE_SEPARATED_ROW_VALIDATED_PENDING_NATIVE_CLOSURE'or commit.get('accession')!=acc or commit.get('input_plan_sha256')!=plan_sha or commit.get('source_manifest_sha256')!=plan['source_manifest']['sha256']or commit.get('native_launch_token')!=launch['token']:raise RuntimeError('N5 current source/input row commit absent')
  own={name:c.row(folder/name/'execution.json')for name in c.UNITS}
  if commit.get('unit_executions')!=own or any(not c.unit_closed(c.read(c.bind(ref)))for ref in own.values()):raise RuntimeError('N5 four actual typed unit0/group receipts per own input required')
  expected_units|={folder/name for name in c.UNITS};m=c.bind(commit['manifest']);c.verify_manifest(m.parent,c.read(m))
  ann=c.read(c.bind(commit['annotation_commit']));search=c.read(c.bind(commit['diamond_commit']));prediction=c.read(c.bind(commit['prediction_commit']));features=c.read(c.bind(commit['feature_validation']))
  if ann.get('status')!='N5_ANNOTATION_UNIT0_COMMITTED_PENDING_CONTEXT_CLOSURE'or search.get('status')!='N5_DIAMOND_UNIT0_COMMITTED_PENDING_CONTEXT_CLOSURE'or prediction.get('status')!='N5_STOCK_RESUME_EXIT0_FEATURE_VALIDATION_PENDING':raise RuntimeError('N5 committed four-phase interfaces absent')
  for phase in(ann,search,prediction):
   if phase.get('accession')!=acc:raise RuntimeError('N5 phase belongs to another input')
   p=c.bind(phase['manifest']);c.verify_manifest(p.parent,c.read(p))
  if ann.get('unit_execution')!=own['unit_annotation']or search.get('unit_execution')!=own['unit_diamond']or prediction.get('unit_execution')!=own['unit_resume']or ann.get('selected_faa')!=search.get('selected_faa')or prediction.get('fresh_search_commit')!=commit['diamond_commit']:raise RuntimeError('N5 own FAA/phase provenance differs')
  if member['feature_validation']!=commit['feature_validation']or features.get('status')!='N5_FEATURES_PASS_PENDING_NATIVE_CLOSURE'or features.get('accession')!=acc or features.get('row_count')!=1 or features.get('finite_domain_features')!=21241 or features.get('exact_FAA_metadata_features')!=22 or features.get('independently_recomputed_membership_features')!=1220 or features.get('membership_mismatches')!=0:raise RuntimeError('N5 own complete corrected feature receipt required')
  if features.get('source_FAA_sha256')!=ann['selected_faa']['sha256']or features.get('source_manifest_sha256')!=plan['source_manifest']['sha256']or features.get('input_plan_sha256')!=plan_sha or features.get('scientific_recipe_sha256')!=plan['scientific_recipe']['sha256']or features.get('quality_unit_execution_sha256')!=own['unit_resume']['sha256']:raise RuntimeError('N5 own row/recipe/FAA/unit bindings changed')
  for key in('source_holds_preserved','source_pending_reasons','source_masks'):
   if features.get(key)!=item[key]or commit.get(key)!=item[key]:raise RuntimeError('N5 source uncertainty/masks changed')
  for key in('Completeness','Contamination'):
   if type(features.get(key))not in(int,float)or not math.isfinite(features[key]):raise RuntimeError('Finite own method estimate required')
  hashes[acc]=features['canonical_float64_le_row_sha256'];summary.append({'accession':acc,'Completeness':features['Completeness'],'Contamination':features['Contamination'],'commit':member['commit'],'feature_validation':member['feature_validation'],'unit_executions':own,'source_holds_preserved':item['source_holds_preserved'],'source_pending_reasons':item['source_pending_reasons'],'source_masks':item['source_masks'],'production_acceptance':False})
 normalized_invocations(c.read(run/'invocations.json'),expected_units);budget=c.budget(run)
 if len(expected_units)!=20 or result.get('budget')!=budget:raise RuntimeError('N5 actual20-unit debit changed')
 if time.monotonic()-start>600:raise TimeoutError('N5 external file-only close exceeded600s')
 destination=c.E/'closed_phases'/c.sha(c.ADMISSION);destination.mkdir(parents=True,exist_ok=False)
 output={'status':'N5_SERIAL_PHASE_SEPARATED_FEASIBILITY_ESTIMATES_PASS_CLOSED','input_plan_sha256':plan_sha,'scientific_recipe':plan['scientific_recipe'],'source_manifest':plan['source_manifest'],'external_closure':external_closure,'rows':summary,'canonical_accession_row_hashes':hashes,'actual_phase_units':20,'finite_domain_features_total':106205,'exact_FAA_metadata_features_total':110,'independently_recomputed_membership_features_total':6100,'membership_mismatches':0,'budget':budget,'strict_serial_four_phases_per_genome':True,'maximum_ML_query_genomes':1,'previously_accepted_rows_recalculated':False,'source_taxonomy_or_production_panel_acceptance':False,'unknown_failed_unstarted_as_negative':False,'continuation_or_fallback_execution_authorized':False}
 c.save(destination/'feasibility_measurements.json',output);c.save(c.OUT/'latest_closed_feasibility.json',c.row(destination/'feasibility_measurements.json'));return output
