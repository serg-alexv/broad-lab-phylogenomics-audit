"""Synthetic launch-only successor/preflight test; no science or processes."""
from pathlib import Path
import hashlib, importlib.util, json, uuid
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('eta',ROOT/'scripts/monitor_qc_eta_v1_1.py')
eta=importlib.util.module_from_spec(spec);spec.loader.exec_module(eta)
R=ROOT/'work'/('monitor_eta_successor_fixture_'+uuid.uuid4().hex);R.mkdir()
def put(rel,value):
    path=R/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value),encoding='utf-8')
    return {'path':rel,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}
accepted=put('metadata/accepted.json',{'status':'ROOT_ACCEPTED_FIXTURE'})
registry=put('metadata/checkm2_accepted_method_result_registry_v001.json',{'rows':[{'accession':'A','authority':accepted}],'accepted_unique_method_accessions':['A']})
queue=put('metadata/queue.json',{'rows':[{'accession':x,'source_supported_scope':True} for x in ['A','S','N1','N2','H']]})
put('state/qc_campaign_queue_v1/intent.json',{'queue':queue})
data=put('metadata/campaign_data.json',{'ordered_new_accessions':['N1','N2'],'historical_review_only':['H'],'cohorts':[{'cohort_index':0,'accessions':['N1']},{'cohort_index':1,'accessions':['N2']}],'controls':[{'accession':'CTRL'}]})
saved=put('metadata/saved.json',{'accession':'S','status':'SAVED_FEATURE_REPAIR_VALIDATED_PENDING_CONTEXT_CLOSURE'})
saved_authority=put('metadata/saved_authority.json',{'status':'ROOT_ADMITTED_REUSE_OF_CLOSED_FIRSTFV0'})
plan=put('metadata/new_canonical_plan.json',{'campaign_data':data,'accepted_registry':registry,'reused_first_feature_checkpoint':saved,'reused_first_feature_authority':saved_authority,'cold_session_seconds':777,'limits':{'global_scientific_seconds':666}})
E='work/new_unique_owner_folder_42'
identity={'pid':777,'windows_creation_filetime_100ns':123,'creation_time_utc':'2026-01-01T00:00:00Z'}
contract=put('metadata/contract.json',{'arguments':['-B','new_native.py','--input-plan',plan['path'],'--input-plan-sha256',plan['sha256']],'registration_directory':E+'/detached_registration'})
launch=put(E+'/detached_registration/launch.json',{'native_owner':identity,'contract':contract})
put(E+'/native_owner.json',{'native_owner':identity,'token':'NEW_TOKEN','started_utc':eta.stamp()})
put(E+'/step.json',{'windows_launch_token':'NEW_TOKEN','status':'PREPARING','detail':'Actual preflight; bulk request does not exist yet'})
put('state/stages/04.json',{'status':'FAILED','windows_launch_token':'OLD_TOKEN','log_path':'work/checkm2_qc_persistent_native_v002/namespace_stderr.txt','current_substep':{'status':'FAILED','declared_unit':'old_failed_search'}})
handoff={'status':'WAITING_WORKER','worker':{**identity,'role':'CONTINUOUS_QC_QUEUE_SESSION_V099','launch_receipt':launch}}
put('state/local_continuation_queue_v1/handoff.json',handoff)
put('state/local_continuation_queue_v1/dispatcher_status.json',{'status':'WAITING_WORKER','AI_calls_during_wait':0})
eta.win_birth=lambda pid:123 if pid==777 else None
service=eta.Estimator(R);value=service.build()
assert value['owner']['pid']==777 and value['owner']['verified_live'] is True
assert value['path_resolution']['work']==E and value['path_resolution']['session'] is None
assert value['path_resolution']['status']=='CANONICAL_PLAN_BOUND_SESSION_PENDING'
assert value['campaign']['accepted_supported']==1 and value['campaign']['saved_validated_reused']==1
assert value['campaign']['all_method_validated_including_saved']==2 and value['campaign']['saved_reused_current_session'] is False
assert value['campaign']['bulk_total']==2 and value['campaign']['remaining_processing_and_history']==3
assert value['campaign']['historical_review_remaining']==1 and value['batch']['total']==2
assert value['batch']['genomes']==1 and value['batch']['controls']==1
assert value['batch']['phase']!='old_failed_search' and value['queue']['status']=='OWNER_ACTIVE'
assert value['eta']['remaining_seconds'] is None and value['budgets']['cold_context_limit_seconds']==777
assert value['budgets']['science_remaining_seconds']==666
# The real request may choose an unrelated SCORE name. Its own parent-plan and
# output-root bindings determine the path; no owner-name/version substitution.
S='analysis/checkm2_qc_persistent_session_unique_output/session'
authority=put('metadata/new_authority.json',{'ordered_new_accessions':['N1','N2'],'historical_review_only':['H'],'campaign_data':data})
put(S+'/bulk_parent_runtime_request.json',{'parent_plan':plan,'campaign_authority':authority,'output_root':str(R/S),'native_launch':{'path':E+'/native_owner.json','sha256':hashlib.sha256((R/E/'native_owner.json').read_bytes()).hexdigest(),'bytes':(R/E/'native_owner.json').stat().st_size}})
after=service.build();assert after['path_resolution']['session']==S
assert after['campaign']['all_method_validated_including_saved']==2,'Accepted/saved counted once'
# Corrupt only a synthetic bound plan. Unknown fields must stay unknown; old
# stage04 failure/counts are not a fallback for a newly detected owner.
put('metadata/new_canonical_plan.json',{'campaign_data':data,'corrupted_after_launch':True})
unknown=service.build()
assert unknown['path_resolution']['status']=='UNRESOLVED'
assert unknown['campaign']['bulk_total'] is None and unknown['campaign']['new_genomes_feature_validated'] is None
assert unknown['eta']['status']=='NEW_WORKER_PATH_UNRESOLVED' and unknown['eta']['remaining_seconds'] is None
assert 'NEW WORKER DETECTED' in unknown['eta']['display_text']
report={'status':'PASS_SYNTHETIC_SUCCESSOR_PREFLIGHT','handoff_only_worker_and_launch_receipt':True,'bound_contract_argv_and_expected_plan_sha':True,'unique_owner_folder_from_registration':True,'preflight_frozen_totals_not_zero':True,'saved_validated_distinct_from_current_reuse':True,'SCORE_from_actual_request_not_native_suffix':True,'bound_plan_drift_emits_unknown_not_zero':True,'old_failure_not_carried_forward':True,'no_double_count_of_accepted_and_saved':True,'fixture':str(R.relative_to(ROOT))}
put('test_receipt.json',report);print(json.dumps(report))
