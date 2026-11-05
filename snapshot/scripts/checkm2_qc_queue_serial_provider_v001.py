"""One existing RO context: delegated shared-search/cohort-batch queue.

The historical filename is the owner's reviewed slot ABI; stock inference is
two calls in the first cohort, one batch call thereafter. No owner is launched.
"""
from pathlib import Path
import datetime,hashlib,json,math,os,shutil,time
import checkm2_qc_queue_common_v001 as c

def run_campaign(request,runtime,score,first_checkpoint_ref,progress):
    import checkm2_qc_queue_inner_v001 as engine
    from checkm2_saved_admission_read_v001 import admission_sha
    score=c.path(score);authority=c.read(c.bind(request['protocol_admission']));data=c.read(c.bind(request['campaign_data']));parent=c.read(c.bind(request['parent_plan']));job=c.read(c.bind(request['root_bulk_job']))
    if authority.get('status')!='ROOT_ADMITTED_ONE_CONTINUOUS_QC_QUEUE_CONTEXT_V001'or job['phase_admission']!=request['protocol_admission']or authority['campaign_data']!=request['campaign_data']or authority['source_manifest']!=request['source_manifest']:raise RuntimeError('One actual Root-reviewed delegated bulk phase required')
    for source in c.read(c.bind(request['source_manifest']))['sources']:c.bind(source)
    first=c.read(c.bind(first_checkpoint_ref))
    if first.get('status')!='SAVED_FEATURE_REPAIR_VALIDATED_PENDING_CONTEXT_CLOSURE'or first.get('annotation_DIAMOND_or_ML_runs')!=0 or not c.unit_closed(c.read(c.bind(first['new_validation_execution']))):raise RuntimeError('Complete saved-feature0 must happen first; never repeat it here')
    raw_feature=c.read(c.bind(first['feature_validation']))
    if (raw_feature.get('finite_domain_features'),raw_feature.get('exact_FAA_metadata_features'),raw_feature.get('independently_recomputed_membership_features'),raw_feature.get('membership_mismatches'))!=(21241,22,1220,0):raise RuntimeError('First complete own feature math required')
    limits=authority['limits'];cap=limits['global_scientific_seconds']
    if type(cap)not in(int,float)or not math.isfinite(cap)or cap<=0:raise RuntimeError('Fresh explicit finite global bulk allocation required')
    deadline_unix=request['helper_deadline_unix']
    if type(deadline_unix)not in(int,float)or not math.isfinite(deadline_unix)or deadline_unix<=time.time():raise RuntimeError('Actual finite inherited whole-context deadline required')
    deadline=time.monotonic()+deadline_unix-time.time();parent_request=score/'bulk_parent_runtime_request.json'
    if parent_request.exists()or(score/'campaign_once_claim.json').exists():raise RuntimeError('Bulk job claim exists; no automatic replay or allowance reset')
    c.save(parent_request,request);request_ref=c.row(parent_request);c.save(score/'campaign_once_claim.json',{'campaign_authority':request['protocol_admission'],'parent_runtime_request':request_ref,'ordered_new_accessions':data['ordered_new_accessions'],'initial_saved_feature_checkpoint':first_checkpoint_ref,'no_external_closure_or_acceptance_claimed':True})
    originals=authority['prior_debit_artifacts'];seen=set();old_spent=0.
    repair=c.read(c.bind(authority['saved_feature_repair']));repaired_request=c.read(c.bind(repair['repaired_request']));old_saved=c.read(c.bind(repaired_request['saved_phase_authority']))
    mandatory=old_saved['all_prior_21_unit_receipts']+[repaired_request['artifacts']['quality_unit_execution'],repair['failed_validation_execution'],first['new_validation_execution']]
    supplied={c.path(ref['path']):ref for ref in originals}
    if any(supplied.get(c.path(ref['path']))!=ref for ref in mandatory):raise RuntimeError('All21 original costs plus stock0/feature1/repaired-feature0 must survive in exact prior bindings')
    for ref in originals:
        p=c.bind(ref);unit=c.read(p);seconds=unit.get('elapsed_seconds')
        if p in seen or type(seconds)not in(int,float)or not math.isfinite(seconds)or seconds<0:raise RuntimeError('Prior exact actual phase set/debits cannot be omitted, repeated or reset')
        seen.add(p);old_spent+=seconds
    if c.bind(first['new_validation_execution'])not in seen:raise RuntimeError('Already completed first validation must be retained in prior debit bindings')
    ledger=[];new_spent=0.;completed=[];cohorts=[];initial_profile=None
    def persist():
        c.save(score/'bulk_actual_debit_ledger.json',{'status':'KNOWN_ACTUAL_PHASE_DEBITS_PENDING_CONTEXT_CLOSURE','campaign_authority':request['protocol_admission'],'prior_actual_phase_artifacts':originals,'prior_actual_scientific_seconds':old_spent,'new_actual_phase_artifacts':ledger,'new_actual_scientific_seconds':new_spent,'prior_plus_new_scientific_seconds':old_spent+new_spent,'new_global_allowance_seconds':cap,'remaining_new_global_seconds':max(0,cap-new_spent),'no_copied_global_cost_per_row':True})
    def charge(ref):
        nonlocal new_spent
        p=c.bind(ref);unit=c.read(p);seconds=unit.get('elapsed_seconds')
        if p in seen or type(seconds)not in(int,float)or not math.isfinite(seconds)or seconds<0:raise RuntimeError('Current actual debit absent or duplicated; stop without reset')
        seen.add(p);ledger.append(ref);new_spent+=seconds;persist()
        if unit.get('owned_group_empty')is not True or unit.get('remaining_owned_processes')!=[]:raise RuntimeError('Actual phase group closure unknown; no next unit')
        if new_spent>cap:raise TimeoutError('Known actual new global allocation exhausted')
    def stop():
        admission_sha(c.path(request['protocol_admission']['path']),request['protocol_admission']['sha256'])
        current=c.read(c.bind(request['parent_plan']))
        if any(c.path(p).exists()for p in('state/STOP','state/STOP_CHECKM2_PILOT',authority['scoped_stop'])):raise InterruptedError('Root/project QC STOP')
        if time.monotonic()>=deadline or new_spent>=cap:raise TimeoutError('Inherited finite cold/global budget exhausted')
        from checkm2_qc_persistent_common_v002 import resource_policy
        policy=resource_policy(request)
        if engine.pilot.legacy.mem_available()<policy['linux_available_minimum_bytes']or shutil.disk_usage(c.R).free<42949672960:raise RuntimeError('RESOURCE_GATE protective headroom or40GiB reserve')
        if os.sched_getaffinity(0)!={0}:raise RuntimeError('One CPU0 source profile changed')
    persist();native=c.read(c.bind(request['native_launch']));launch={**native,'root_session_protocol_admission_sha256':native['protocol_admission_sha256'],'protocol_admission_sha256':request['protocol_admission']['sha256']}
    recipe_ref=authority['scientific_recipe'];template=c.read(c.bind(recipe_ref));plan_dir=score/'cohort_plans';plan_dir.mkdir()
    try:
        for part in data['cohorts']:
            stop();index=part['cohort_index'];names=part['accessions'];folder=plan_dir/f'{index:03d}';folder.mkdir();selected=[]
            for acc in names:
                q=data['source_rows'][acc]
                legacy=[x for x in template['inputs']if x['accession']==acc]
                selected.append({**q,'canonical_queue_row':q,'fasta_path':q['FNA_from_receipt']['path'],'fasta_sha256':q['FNA_from_receipt']['sha256'],'fasta_bytes':q['FNA_from_receipt']['bytes'],'source_masks':c.canonical_source_masks(q),'role':'FRESH_QC_ON_EXISTING_CLOSED_UNIFORM_PROTEOME','selection_status':q['qc_execution_state'],'legacy_P20_source_context':legacy[0]if legacy else None})
            selected_path=folder/'selected_inputs.json';c.save(selected_path,{'inputs':selected,'canonical_queue':data['canonical_queue'],'parent_campaign_authority':request['protocol_admission'],'no_fresh_genome_or_gene_acquisition':True})
            run=score/'cohorts'/f'{index:03d}'
            plan={'schema':'TREE2_CAMPAIGN_SHARED_INDEX8_INPUT_PLAN_V003','role':c.ROLE,'cohort_id':f'continuous_QC_{index:03d}','cohort_index':index,'accessions':names,'controls':data['controls'],'limits':authority['cohort_limits'],'source_manifest':request['source_manifest'],'scientific_recipe':recipe_ref,'runtime_binding':template['runtime_binding'],'feature_schema':template['schema_v002'],'selected_inputs':c.row(selected_path),'canonical_queue':data['canonical_queue'],'accepted_registry':request['accepted_registry'],'campaign_data':request['campaign_data'],'campaign_authority':request['protocol_admission'],'conditional_shared_profile_authority':request['conditional_shared_profile_authority'],'saved_feature_repair':authority['saved_feature_repair'],'saved_feature_checkpoint':first_checkpoint_ref,'uniform_annotation_authority':data['uniform_annotation_authority'],'uniform_annotation_reuse':{acc:data['uniform_annotation_cache_candidates'][acc]for acc in names},'annotation_reuse_by_accession':{},'method_amendment':request['conditional_shared_profile_authority'],'prior_debit_artifacts':originals+ledger[:],'parent_runtime_request':request_ref,'run_directory':str(run),'initial_in_session_profile':initial_profile,'external_parent_acceptance':'PENDING'}
            plan_path=folder/'input_plan.json';c.save(plan_path,plan);ref=c.row(plan_path)
            offset=1+len(completed)
            def cohort_progress(status,detail,done=None,**extra):
                actual=0 if type(done)is not int else done
                progress(status,detail,offset+actual,current_cohort=index,total_new_inputs897=897,**extra)
            result=engine.run_cohort(ref,runtime,launch,deadline,cohort_progress,stop,lambda:max(0,cap-new_spent),charge)
            if len(result['rows'])!=len(names)or [x['accession']for x in result['rows']]!=names:raise RuntimeError('Exact disjoint cohort rows required')
            completed.extend(result['rows']);cohorts.append(c.row(run/'result.json'));initial_profile=result['initial_in_session_profile']
            c.save(score/'completed_campaign_checkpoint.json',{'status':'COMPUTED_PENDING_CONTEXT_CLOSURE','saved_feature_first':first_checkpoint_ref,'rows':completed,'cohort_results':cohorts,'completed_new_rows':len(completed),'accepted_prior_source_supported':16,'historical_review_only_remaining':data['historical_review_only'],'global_actual_debit_ledger':c.row(score/'bulk_actual_debit_ledger.json'),'queue_ledger_or_method_registry_changed':False})
        queue=c.read(c.bind(data['canonical_queue']));by={x['accession']:x for x in queue['rows']};history=[by[acc]for acc in data['historical_review_only']]
        c.save(score/'required_history_reuse_review.json',{'status':'REQUIRED_FIVE_HISTORICAL_DONOR_REUSE_AUDITS_NOT_QUEUE_EXHAUSTION','rows':history,'required_actions':['Bind each actual prior gene/search/model command and typed exit/closure; completed phases cannot replay','Reuse exact accepted uniform annotations; identify any prior complete saved search/model result before new scoring','Admit only genuinely unstarted or explicitly repair-qualified scoring under retained old claims/debits','All919 eligible dispositions must reconcile before wholeQC queue completion'],'actual_unresolved_rows':len(history),'unknown_as_negative':False,'automatic_local_Root_followup_required':True})
        return {'status':'QC_CONTINUOUS_NEW_ROWS_PENDING_CONTEXT_CLOSURE_AND_REQUIRED_HISTORY_AUDIT','rows':completed,'completed_new_qc_rows':len(completed),'saved_feature_checkpoint':first_checkpoint_ref,'cohort_results':cohorts,'same_RO_IPC_context_reused':True,'science_debit_ledger':c.row(score/'bulk_actual_debit_ledger.json'),'required_history_reuse_review':c.row(score/'required_history_reuse_review.json'),'source_supported_method_rows_after_acceptance':16+1+len(completed),'all919_QC_completed':False,'source_taxonomy_or_panel_acceptance':False}
    except BaseException as error:
        persist();c.save(score/'campaign_failure.json',{'status':'QC_CAMPAIGN_FAILED_NO_AUTOMATIC_RETRY_OR_PHASE_REPLAY','error':repr(error),'completed_rows':completed,'cohort_results':cohorts,'global_actual_debit_ledger':c.row(score/'bulk_actual_debit_ledger.json'),'partial_results_pending_actual_parent_closure':True,'unknown_failed_unstarted_as_negative':False});raise
