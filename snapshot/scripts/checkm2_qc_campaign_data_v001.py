"""Pure queue selection and delegated cohort policy, never a science launcher.

One immutable parent scope authorizes deterministic <=20-input chunks. Chunk
checkpoints are computed/pending outer closure, not fabricated ledger closures.
"""
ACCEPTED='ACCEPTED_METHOD_REUSE_VERIFIED'
FRESH='READY_FRESH_QC'
REVIEW='HISTORICAL_DONOR_REVIEW_REUSE_ONLY'
SAVED='GCF_900636715.1'

def campaign_data(queue,registry,repair_packet):
    if queue.get('schema')!='TREE2_CANONICAL_QC_QUEUE_V001':raise RuntimeError('Frozen canonical queue required')
    rows=queue['rows'];by_id={x['accession']:x for x in rows}
    if len(by_id)!=len(rows):raise RuntimeError('Repeated canonical accession')
    accepted=registry['rows']+[registry['additional_baseline']]
    ids=[x['accession']for x in accepted]
    if len(ids)!=len(set(ids))or set(registry['accepted_unique_method_accessions'])!=set(ids):raise RuntimeError('Exact current accepted registry identity set required')
    skip=set(ids);aliases={n for x in accepted for n in x.get('paired_accessions',[])}
    original=repair_packet['exact_original20_queue_ids']
    if len(original)!=20 or len(set(original))!=20 or SAVED in skip:raise RuntimeError('Original20 and saved-unaccepted row must remain exact')
    reserved=[x for x in original if x not in skip and x!=SAVED]
    if len(reserved)!=17 or reserved!=repair_packet['ordered_actions'][1]['queue_ids']:raise RuntimeError('Exact remaining17 original order required')
    ready=sorted((x for x in rows if x['source_supported_scope']is True and x['qc_execution_state']==FRESH),key=lambda x:x['frozen_order'])
    fresh=[x['accession']for x in ready if x['accession']not in skip and not set(x['paired_accessions'])&(skip|aliases)]
    if len(fresh)!=880:raise RuntimeError('Current880 fresh scope changed; reconcile source evidence, never guess')
    reviewed=sorted((x for x in rows if x['source_supported_scope']is True and x['qc_execution_state']==REVIEW),key=lambda x:x['frozen_order'])
    history=[x['accession']for x in reviewed]
    if len(history)!=5:raise RuntimeError('Five historical donor review-only states remain unresolved')
    ordered=reserved+fresh
    if len(ordered)!=897 or len(set(ordered))!=897 or (set(ordered)&(skip|aliases|{SAVED}|set(history))):raise RuntimeError('Repeated, accepted, saved or historical donor cannot be newly predicted')
    for acc in ordered:
        q=by_id[acc]
        if q['source_supported_scope']is not True or q['source_holds_preserved']or q['qc_execution_state']not in(FRESH,'RESERVED_P20_UNSTARTED'):raise RuntimeError('Source-held or unknown queue member cannot become fresh QC')
    cohorts=[reserved]+[fresh[i:i+20]for i in range(0,len(fresh),20)]
    supported={x['accession']for x in rows if x['source_supported_scope']is True};accepted_supported=sorted(supported&skip)
    if len(supported)!=919 or len(accepted_supported)!=16 or set(accepted_supported)|set(ordered)|{SAVED}|set(history)!=supported:raise RuntimeError('16 accepted+1saved+17reserved+880fresh+5review must reconcile919')
    return {'schema':'TREE2_QC_CONTINUOUS_QUEUE_DATA_V001','ordered_new_accessions':ordered,'cohorts':[{'cohort_index':i,'accessions':values,'state':'NOT_STARTED_NO_SCIENTIFIC_CLAIM'}for i,values in enumerate(cohorts)],'accepted_source_supported_skip':accepted_supported,'saved_feature_first_accession':SAVED,'historical_review_only':history,'review_disposition':'NO_FRESH_DISPATCH_WITHOUT_SEPARATE_SOURCE_REUSE_REVIEW','original20':original,'counts':{'source_supported':919,'accepted_method_reuse':16,'saved_validation_pending':1,'remaining_original17':17,'fresh':880,'historical_review_only':5,'new_prediction_inputs':897,'cohorts':45},'source_rows':{acc:by_id[acc]for acc in ordered},'no_new_genome_content_reads':True,'per_cohort_ledger_closure':'NOT_PERMITTED_BEFORE_ACTUAL_OUTER_CLOSURE','source_eligibility_is_biological_QC_PASS':False,'whole_queue_completion':'NOT_GRANTED_WHILE_FIVE_REVIEW_STATES_REMAIN'}

def campaign_cohort_gate(plan,*,read,bind):
    """New common uses this INSTEAD OF old per-cohort external-reservation premise."""
    data_ref=plan['campaign_data'];data=read(bind(data_ref));authority_ref=plan['campaign_authority'];authority=read(bind(authority_ref))
    if authority.get('status')!='ROOT_ADMITTED_ONE_CONTINUOUS_QC_QUEUE_CONTEXT_V001'or authority.get('campaign_data')!=data_ref:raise RuntimeError('One exact Root continuous-queue authority required')
    flags=('saved_feature_repair_must_pass_first','all897_new_inputs_exact_ordered_and_once','same8_controls_and_first_own_features_before_remaining','all_completed_results_pending_real_outer_closure','no_per_cohort_fake_external_closure','all_prior_attempts_and_debits_preserved','no_accepted_annotation_search_or_ML_replay','source_taxonomy_unknown_masks_preserved')
    if any(authority.get(k)is not True for k in flags):raise RuntimeError('Explicit delegated scope/no-replay/closure policy missing')
    if authority.get('ordered_new_accessions')!=data['ordered_new_accessions']or authority.get('historical_review_only')!=data['historical_review_only']:raise RuntimeError('Root exact897/5 scope changed')
    if authority.get('source_manifest')!=plan['source_manifest']or authority.get('accepted_registry')!=plan['accepted_registry']or authority.get('conditional_shared_profile_authority')!=plan['conditional_shared_profile_authority']:raise RuntimeError('Parent source/registry/conditional method bindings differ')
    index=plan.get('cohort_index')
    if type(index)is not int or not 0<=index<len(data['cohorts']):raise RuntimeError('Finite exact cohort index required')
    expected=data['cohorts'][index]['accessions']
    if plan.get('accessions')!=expected or not 1<=len(expected)<=20:raise RuntimeError('Delegated exact <=20 slice/order changed')
    selected=read(bind(plan['selected_inputs']))
    if [x['accession']for x in selected['inputs']]!=expected:raise RuntimeError('Selected input list differs from exact frozen cohort')
    for item in selected['inputs']:
        q=data['source_rows'][item['accession']]
        if item.get('canonical_queue_row')!=q or any(item.get(k)!=q[k]for k in('source_holds_preserved','source_pending_reasons')):raise RuntimeError('Own canonical source/hold context changed')
        if item.get('fasta_sha256')!=q['FNA_from_receipt']['sha256']:raise RuntimeError('Own acquired DNA identity changed')
    if plan.get('saved_feature_repair')!=authority['saved_feature_repair']:raise RuntimeError('First saved-feature exact request/debit prerequisite changed')
    return data,authority,expected
