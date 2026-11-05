"""Explicit conditional shared-query authority; never invents a whole-owner0.

This is a new opt-in hook. Frozen V3 baseline_gate remains unchanged. A new
consumer may call it only for the authority mode below; all raw/control/own-row
gates still belong to the original shared provider.
"""
def conditional_baseline_gate(plan,*,read,bind,unit_closed):
    ref=plan['conditional_shared_profile_authority'];authority=read(bind(ref))
    if authority.get('status')!='ROOT_APPROVED_CONDITIONAL_SHARED_INDEX8_FROM_CLOSED_SERIAL_ROWS':raise RuntimeError('Explicit new conditional shared-profile authority required')
    true=('supersedes_only_prior_whole_owner0_planning_prerequisite','no_prior_whole_owner0_claim','first_repaired_feature0_required','first_own_complete_features_and_same8_fullraw_controls_before_remaining','all_old_exits_and_debits_preserved','no_accepted_annotation_or_ML_replay','same_cohort_empirical_resource_fit_required','fixed_author_filters_DB_models_and_feature_math','source_and_unknown_masks_preserved')
    if any(authority.get(k)is not True for k in true):raise RuntimeError('Scoped conditional policy/gates missing')
    if authority.get('default4_raw_and_model_input_equivalence')is not False or authority.get('source_taxonomy_or_panel_acceptance')is not False or authority.get('quality_thresholds')!={'completeness_min':95,'contamination_max':5}:raise RuntimeError('No equivalence, threshold or panel promotion')
    if authority.get('index_chunks')!=8 or authority.get('block_size')!=.5 or authority.get('threads')!=1:raise RuntimeError('Exact fixed distinct index8 search profile required')
    serial=read(bind(authority['closed_serial_row_authority']))
    if serial.get('status')!='ROOT_ACCEPTED_CLOSED_DISTINCT_INDEX8_OWN_ROW_FOR_BULK'or serial.get('all_owner_context_and_lease_closure_verified')is not True or serial.get('own_feature_math_verified')is not True:raise RuntimeError('Genuine accepted serial own row/failed-context closure required')
    for key,expected in(('actual_context_native_exit_code',2),('actual_context_WSL_exit_code',1)):
        if type(serial.get(key))is not int or serial[key]!=expected:raise RuntimeError('Original failed parent exits must remain exact2/1, never whole0')
    registry=read(bind(plan['accepted_registry']));entries=registry['rows']+[registry['additional_baseline']]
    matches=[x for x in entries if x['accession']==serial['accession']]
    if len(matches)!=1 or matches[0].get('authority')!=authority['closed_serial_row_authority']or matches[0].get('commit')!=serial.get('commit')or matches[0].get('feature_validation')!=serial.get('feature_validation'):raise RuntimeError('Same8 serial donor must belong to exact accepted registry')
    commit=read(bind(serial['commit']));features=read(bind(serial['feature_validation']))
    if features.get('finite_domain_features')!=21241 or features.get('exact_FAA_metadata_features')!=22 or features.get('independently_recomputed_membership_features')!=1220 or features.get('membership_mismatches')!=0:raise RuntimeError('Serial own complete feature proof missing')
    search=read(bind(commit['diamond_commit']));receipt=read(bind(search['diamond_receipt']))
    if receipt.get('index_chunks')!=8 or receipt.get('block_size')!=.5 or receipt.get('threads')!=1 or receipt.get('database')!=plan['runtime_binding']['database']:raise RuntimeError('Actual SAME8/DB serial baseline required')
    for key in('unit_execution','validation_unit_execution'):
        if not unit_closed(read(bind(search[key]))):raise RuntimeError('Serial reference binary/raw-validation actual0 required')
    if not any(c.get('accession')==serial['accession']and c.get('serial_search_commit')==commit['diamond_commit']and c.get('accepted_method_authority')==authority['closed_serial_row_authority']for c in plan['controls']):raise RuntimeError('The accepted serial donor must be an actual same-cohort search-only control')
    if authority.get('saved_feature_repair')!=plan['saved_feature_repair']:raise RuntimeError('Feature-first repaired request/debit binding differs')
    for evidence in authority.get('closure_and_result_evidence',[]):bind(evidence)
    return authority
