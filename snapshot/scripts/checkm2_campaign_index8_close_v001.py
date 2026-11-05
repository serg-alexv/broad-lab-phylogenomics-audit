"""File-only dynamic cohort finalizer; external actual-owner closure is prerequisite."""
import argparse
import checkm2_campaign_index8_common_v001 as c

def finalize(plan_path,plan_sha,proof_path,proof_sha):
 plan,recipe,_=c.plan_gate(plan_path,plan_sha,closed_finalization=True)
 if c.sha(c.path(proof_path))!=proof_sha:raise RuntimeError('External closure proof changed')
 proof=c.read(c.path(proof_path));pending=c.read(c.OUT/'latest_pending_native.json')
 if proof.get('status')!='CAMPAIGN_INDEX8_NATIVE_GROUP_NAMESPACE_IMAGE_LEASE_CLOSED' or proof.get('input_plan_sha256')!=plan_sha or proof.get('launch_token')!=pending['launch_token']or type(proof.get('actual_native_exit_code'))is not int or proof['actual_native_exit_code']!=0 or type(proof.get('actual_WSL_exit_code'))is not int or proof['actual_WSL_exit_code']!=0 or any(proof.get(k)is not True for k in('all_owned_groups_absent','ordinary_namespace_IPC_image_closed','image_pre_and_post_hashes_verified','common_three_leases_released','registry_and_protected_artifacts_unchanged')):raise RuntimeError('Actual external native/guest/image/groups/leases closure required')
 c.bound_evidence(proof.get('closure_and_result_evidence'))
 run=c.path(pending['run_directory']);result=c.read(run/'result.json')
 if run.parent!=c.OUT/'runs'or result.get('status')!='P20_CORE_PENDING_NAMESPACE_NATIVE_CLOSURE'or result['input_plan_sha256']!=plan_sha or result.get('completed_qc_rows')!=c.COUNT or [x['accession']for x in result['rows']]!=plan['accessions']or proof.get('run_directory')!=str(run):raise RuntimeError('Exact current own cohort result required')
 if c.budget(run)['known_limit_exceeded']:raise RuntimeError('Known actual debit exceeded allocation; no acceptance')
 manifest_path=c.path(pending['manifest_path'])
 if c.sha(manifest_path)!=pending['manifest_sha256']or proof.get('result')!=c.row(run/'result.json'):raise RuntimeError('Externally bound original result/manifest changed')
 c.verify_manifest(run,c.read(manifest_path))
 for entry in result['rows']:
  commit=c.read(c.bind(entry['commit']));feature=c.read(c.bind(entry['feature_validation']))
  if commit['input_plan_sha256']!=plan_sha or commit['accession']!=entry['accession']or feature['accession']!=entry['accession']or feature['status']!='P20_FEATURES_PASS_PENDING_NATIVE_CLOSURE'or (feature['finite_domain_features'],feature['exact_FAA_metadata_features'],feature['independently_recomputed_membership_features'])!=(21241,22,1220):raise RuntimeError('Own complete feature chain differs')
  for ref in commit['unit_executions'].values():
   if not c.unit_closed(c.read(c.bind(ref))):raise RuntimeError('Each actual original/reused unit0 must be genuine')
 target=c.OUT/'closed'/pending['launch_token']/'closed_method_receipt.json'
 if target.exists():raise RuntimeError('Closed cohort receipt already exists; no overwrite')
 value={'schema':'TREE2_CAMPAIGN_INDEX8_CLOSED_METHOD_COHORT_V001','status':'CAMPAIGN_COHORT_CLOSED_METHOD_OUTPUTS_PENDING_ROOT_ACCEPTANCE','input_plan':c.row(c.path(plan_path)),'external_closure':c.row(c.path(proof_path)),'result':c.row(run/'result.json'),'completed_rows':result['rows'],'budget':c.budget(run),'method_variant':recipe['resource_variant'],'new_actual_unit_count':4*c.COUNT-len(plan['annotation_reuse_by_accession'])+int(bool(plan.get('search_only_control'))),'reused_original_unit_count':len(plan['annotation_reuse_by_accession']),'all_source_masks_preserved':True,'source_taxonomy_or_final_panel_accepted':False,'queue_ledger_or_registry_updated':False}
 c.save(target,value);c.save(c.OUT/'latest_closed_method.json',c.row(target));return c.row(target)
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for arg in('input-plan','input-plan-sha256','external-proof','external-proof-sha256'):p.add_argument('--'+arg,required=True)
 a=p.parse_args();print(finalize(a.input_plan,a.input_plan_sha256,a.external_proof,a.external_proof_sha256))
