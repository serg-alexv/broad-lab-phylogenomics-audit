"""Synthetic estimator validation. No genomes/models/scientific processes."""
from pathlib import Path
import hashlib, importlib.util, json, uuid
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("eta",ROOT/"scripts/monitor_qc_eta_v1.py");eta=importlib.util.module_from_spec(spec);spec.loader.exec_module(eta)
R=ROOT/"work"/("monitor_eta_fixture_"+uuid.uuid4().hex);R.mkdir()
def put(rel,value):
    path=R/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value),encoding="utf-8")
    return {"path":rel,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"bytes":path.stat().st_size}
S="analysis/checkm2_qc_persistent_session_v002/session";C=S+"/cohorts/000"
data=put("metadata/data.json",{"cohorts":[{"cohort_index":0,"accessions":["N1"]},{"cohort_index":1,"accessions":["N2"]}]})
authority=put("metadata/authority.json",{"ordered_new_accessions":["N1","N2"],"historical_review_only":["H"],"campaign_data":data})
put(S+"/bulk_parent_runtime_request.json",{"campaign_authority":authority})
put("state/stages/04.json",{"status":"PREPARING","windows_launch_token":"SYNTHETIC_TOKEN","current_substep":{"declared_unit":"unit_shared_diamond","current_cohort":0,"windows_launch_token":"SYNTHETIC_TOKEN"}})
put("work/checkm2_qc_persistent_native_v002/native_owner.json",{})
accepted=put("metadata/accepted.json",{"status":"ROOT_ACCEPTED_FIXTURE"})
put("metadata/checkm2_accepted_method_result_registry_v001.json",{"rows":[{"accession":"A","authority":accepted}],"accepted_unique_method_accessions":["A"]})
queue=put("metadata/queue.json",{"rows":[{"accession":x,"source_supported_scope":True} for x in ["A","S","N1","N2","H"]]})
put("state/qc_campaign_queue_v1/intent.json",{"queue":queue})
saved=put("metadata/saved.json",{"accession":"S"})
put(S+"/reused_first_feature.json",{"status":"ORIGINAL_FIRSTFV0_REUSED_NO_CURRENT_UNIT_OR_DEBIT","original_checkpoint":saved})
put("state/monitor_qc_eta_v1/timing_input.json",{"total_query_proteins":4000,"cohorts":[{"index":0,"query_proteins":1000},{"index":1,"query_proteins":3000}]})
plan=put(S+"/cohort_plans/000/input_plan.json",{"accessions":["N1"],"controls":[{}]})
put(C+"/shared/unit_shared_diamond/execution.json",{"status":"UNIT_FAILED_OR_CLOSURE_UNPROVEN","exit_code":-15,"elapsed_seconds":5000,"failure_kind":"STOP"})
service=eta.Estimator(R)
first=service.build();assert first["eta"]["remaining_seconds"] is None and first["campaign"]["first_new_genomes_completed"]==0
assert first["queue"]["status"]=="STOPPED_OR_REPAIRING"
search={"status":"UNIT_EXIT0_GROUP_CLOSED","exit_code":0,"owned_group_empty":True,"remaining_owned_processes":[],"started_utc":"2026-01-01T00:00:00Z","ended_utc":"2026-01-01T00:00:30Z","elapsed_seconds":30}
put(C+"/shared/unit_shared_diamond/execution.json",search)
unit={**search,"started_utc":"2026-01-01T00:00:30Z","ended_utc":"2026-01-01T00:00:50Z","elapsed_seconds":20}
execution=put(C+"/rows/N1/unit_feature_validation/execution.json",unit)
feature=put(C+"/rows/N1/feature_validation.json",{"status":"P20_FEATURES_PASS_PENDING_NATIVE_CLOSURE","accession":"N1","finite_domain_features":21241,"exact_FAA_metadata_features":22,"independently_recomputed_membership_features":1220,"membership_mismatches":0,"input_plan_sha256":plan["sha256"]})
put(C+"/rows/N1/commit.json",{"status":"SHARED_SEARCH_OWN_ROW_FEATURES_VALIDATED_PENDING_CONTROL_AND_OWNER_CLOSURE","accession":"N1","input_plan_sha256":plan["sha256"],"feature_validation":feature,"per_row_unit_executions":{"unit_feature_validation":execution}})
second=service.build();assert second["campaign"]["first_new_genomes_completed"]==1 and second["campaign"]["closed_cohorts"]==0
assert second["eta"]["remaining_seconds"] is None,"Feature success alone must not calibrate whole-cohort speed"
put(C+"/result.json",{"status":"COHORT_COMPUTED_PENDING_CONTEXT_CLOSURE","cohort_index":0,"input_plan":plan,"rows":[{"accession":"N1"}]})
put(S+"/bulk_actual_debit_ledger.json",{"remaining_new_global_seconds":100})
third=service.build();assert third["campaign"]["closed_cohorts"]==1 and third["campaign"]["new_bulk_cohort_checkpointed"]==1
assert abs(third["eta"]["remaining_seconds"]-110)<1e-8,"Protein-weighted search plus per-genome residual required"
assert third["eta"]["finish_msk"] is None and third["eta"]["historical_review_eta_seconds"] is None
assert third["campaign"]["all_method_validated_including_saved"]==3 and third["campaign"]["remaining_processing_and_history"]==2
assert third["budgets"]["diagnostics"],"Forecast exceeding remaining finite budget must be diagnostic"
report={"status":"PASS_SYNTHETIC_ESTIMATOR_ONLY","interrupted_phase_not_calibration":True,"features_before_checkpoint_distinguished":True,"protein_weighted_full_cohort_calibration":True,"five_history_scope_remains_unforecasted":True,"inactive_owner_has_no_finish_clock":True,"budget_excess_is_diagnostic_only":True,"fixture":str(R.relative_to(ROOT))}
put("test_receipt.json",report);print(json.dumps(report))
