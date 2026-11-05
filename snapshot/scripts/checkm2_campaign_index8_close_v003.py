"""HELD future file-only global/per-row closure; never attests its own future exit."""
import argparse
import checkm2_campaign_index8_common_v003 as c

def finalize(plan_path,plan_sha,proof_path,proof_sha):
 plan,recipe,_=c.plan_gate(plan_path,plan_sha,closed_finalization=True)
 if c.sha(c.path(proof_path))!=proof_sha:raise RuntimeError('Actual external shared cohort closure changed')
 proof=c.read(c.path(proof_path));pending=c.read(c.OUT/'latest_pending_native.json');run=c.path(pending['run_directory']);result=c.read(run/'result.json')
 if proof.get('status')!='SHARED_INDEX8_NATIVE_GROUP_NAMESPACE_IMAGE_LEASE_CLOSED'or proof.get('input_plan_sha256')!=plan_sha or proof.get('launch_token')!=pending['launch_token']or type(proof.get('actual_native_exit_code'))is not int or proof['actual_native_exit_code']!=0 or type(proof.get('actual_WSL_exit_code'))is not int or proof['actual_WSL_exit_code']!=0 or any(proof.get(k)is not True for k in('all_owned_groups_absent','ordinary_namespace_IPC_image_closed','image_pre_and_post_hashes_verified','common_three_leases_released','registry_and_protected_artifacts_unchanged')):raise RuntimeError('Actual external native/guest/groups/contexts/leases required')
 c.bound_evidence(proof.get('closure_and_result_evidence'))
 if result['input_plan_sha256']!=plan_sha or result['completed_qc_rows']!=c.COUNT or [x['accession']for x in result['rows']]!=plan['accessions']or proof.get('result')!=c.row(run/'result.json'):raise RuntimeError('Exact current own result set required')
 if c.sha(c.path(pending['manifest_path']))!=pending['manifest_sha256']:raise RuntimeError('Global/per-row manifest changed')
 c.verify_manifest(run,c.read(c.path(pending['manifest_path'])));budget=c.budget(run)
 if budget['known_limit_exceeded']:raise RuntimeError('Finite known global/row allowance exhausted')
 shared=c.read(c.bind(result['shared_search_commit']));c.shared_qualification_gate(plan,result['qualification_commit'],result['shared_search_commit'])
 for ref in(shared['binary_execution'],shared['validation_execution']):
  if not c.unit_closed(c.read(c.bind(ref))):raise RuntimeError('Genuine ONE global binary/raw-validation0 required')
 for entry in result['rows']:
  commit=c.read(c.bind(entry['commit']));feature=c.read(c.bind(entry['feature_validation']))
  if feature['accession']!=entry['accession']or (feature['finite_domain_features'],feature['exact_FAA_metadata_features'],feature['independently_recomputed_membership_features'])!=(21241,22,1220)or commit['shared_search_commit']!=result['shared_search_commit']:raise RuntimeError('Each own feature chain/global parent required')
  for ref in commit['per_row_unit_executions'].values():
   if not c.unit_closed(c.read(c.bind(ref))):raise RuntimeError('Genuine per-row annotation/model/features0 required')
 target=c.OUT/'closed'/pending['launch_token']/'closed_method_receipt.json'
 if target.exists():raise RuntimeError('Preserve existing immutable closed cohort')
 c.save(target,{'status':'SHARED_INDEX8_COHORT_METHOD_OUTPUTS_CLOSED_PENDING_ROOT_ACCEPTANCE','plan':c.row(c.path(plan_path)),'external_closure':c.row(c.path(proof_path)),'rows':result['rows'],'shared_search_commit':result['shared_search_commit'],'qualification_commit':result['qualification_commit'],'budget':budget,'search_unit_count':1,'per_row_search_receipts_or_debits_created':False,'source_taxonomy_or_panel_acceptance':False,'queue_ledger_or_registry_updated':False});c.save(c.OUT/'latest_closed_method.json',c.row(target));return c.row(target)
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for name in('input-plan','input-plan-sha256','external-proof','external-proof-sha256'):p.add_argument('--'+name,required=True)
 a=p.parse_args();print(finalize(a.input_plan,a.input_plan_sha256,a.external_proof,a.external_proof_sha256))
