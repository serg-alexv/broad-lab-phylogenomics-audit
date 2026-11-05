"""Pure workflow authority gate for a distinct method; no search/model/science imports."""
def qualification_gate(ref,*,read,bind,unit_closed,bound_evidence):
 q=read(bind(ref))
 if q.get('status')!='ROOT_ACCEPTED_CLOSED_DISTINCT_INDEX8_OWN_ROW_FOR_BULK' or q.get('scope')!='METHOD_PROFILE_AND_MEASUREMENT_REUSE_ONLY':raise RuntimeError('Explicit distinct-profile own-row Root authority required')
 if (q.get('index_chunks'),q.get('block_size'),q.get('threads'))!=(8,.5,1):raise RuntimeError('Exact supported stock index8/block.5/thread1 profile required')
 yes=('empirical_qualification_accepted','own_feature_math_verified','resource_gates_unchanged','all_owner_context_and_lease_closure_verified','failed_reference_gate_preserved','old_default4_estimates_preserved_with_parameter_tags','quality_thresholds_unchanged','independent_panel_QC_required','borderline_and_conflicting_evidence_held','all_prior_attempts_claims_and_actual_debits_preserved')
 if any(q.get(k)is not True for k in yes):raise RuntimeError('Original failures, resources, thresholds, masks and independent QC must remain explicit')
 no=('raw_output_equivalence_to_default4','full_model_input_equivalence_to_default4','old_estimates_overwritten','accepted_annotation_or_prediction_replayed','source_taxonomy_or_final_panel_acceptance')
 if any(q.get(k)is not False for k in no):raise RuntimeError('A distinct method cannot become claimed equivalence, replay or panel acceptance')
 if type(q.get('actual_context_native_exit_code'))is not int or type(q.get('actual_context_WSL_exit_code'))is not int:raise RuntimeError('Original NONZERO cohort exits remain observed integers, never relabelled zero')
 native=read(bind(q['actual_context_native_exit_receipt']))
 if native.get('native_exit_code_observed')!=q['actual_context_native_exit_code']:raise RuntimeError('Observed original native exit evidence differs')
 closed=read(bind(q['external_closed_context']))
 if closed.get('all_owner_context_and_lease_closure_verified')is not True or closed.get('actual_native_exit_code')!=q['actual_context_native_exit_code']or closed.get('actual_WSL_exit_code')!=q['actual_context_WSL_exit_code']:raise RuntimeError('Whole failed context must actually close; successful own row is a separate scope')
 difference=read(bind(q['reference_difference_evidence']))
 if difference.get('raw_output_equivalent')is not False or difference.get('full_model_input_equivalent')is not False or not difference.get('known_KO_input_differences'):raise RuntimeError('Actual failed reference/raw and model-input differences remain bound')
 bound_evidence(q.get('closure_and_result_evidence'))
 commit=read(bind(q['commit']));feature=read(bind(q['feature_validation']));acc=q['accession']
 if commit.get('accession')!=acc or commit.get('feature_validation')!=q['feature_validation']or feature.get('accession')!=acc:raise RuntimeError('Exact accepted own measurement commit/feature association required')
 if (feature.get('finite_domain_features'),feature.get('exact_FAA_metadata_features'),feature.get('independently_recomputed_membership_features'))!=(21241,22,1220):raise RuntimeError('Complete original numerical validation remains required')
 units=commit.get('unit_executions',{});expected={'unit_annotation','unit_diamond','unit_saved_search_validation','unit_resume','unit_feature_validation'}
 if set(units)!=expected:raise RuntimeError('Exactly five real own phases, including original annotation, required')
 for unit in units.values():
  if not unit_closed(read(bind(unit))):raise RuntimeError('Each own phase must retain its actual typed0/group-closed receipt')
 return q
