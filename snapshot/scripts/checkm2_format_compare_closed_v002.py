"""File-only final comparison, called by the external retained-handle owner.

No dispatcher or self-exit attestation. The external owner supplies and hashes
the actual exit/group/namespace/lease proof after the native controller exits.
"""
from pathlib import Path
import datetime,time
import checkm2_format_common_v002 as c
import checkm2_protein_invariance_v002 as compare
R=c.R
def closed_native_proof(proof,launch,execution_sha,plan_sha):
 required=('native_exit_code_observed','wsl_exit_code_observed','native_owner','common_leases_reacquired_released','owned_unit_groups_empty','ordinary_runtime_closed','image_unchanged','original_artifacts_unchanged','execution_sha256','input_plan_sha256','protocol_admission_sha256')
 if any(key not in proof for key in required):raise RuntimeError('External current native/lease proof incomplete')
 if proof.get('status')!='FORMAT_CONTROL_NATIVE_GROUP_NAMESPACE_IMAGE_LEASE_CLOSED' or type(proof['native_exit_code_observed']) is not int or proof['native_exit_code_observed']!=0 or type(proof['wsl_exit_code_observed']) is not int or proof['wsl_exit_code_observed']!=0 or proof['native_owner']!=launch['native_owner']:raise RuntimeError('Actual control owner exit/identity not established')
 if any(proof[k] is not True for k in ('common_leases_reacquired_released','owned_unit_groups_empty','ordinary_runtime_closed','image_unchanged','original_artifacts_unchanged')):raise RuntimeError('Current control closure/leases/artifacts unproved')
 if proof['execution_sha256']!=execution_sha or proof['input_plan_sha256']!=plan_sha or proof['protocol_admission_sha256']!=c.v.sha(c.ADMISSION):raise RuntimeError('External control proof cross-binding differs')
def finalize(plan_path,plan_sha,external_closure):
 """Only the externally supervised file-only owner may call after native exit.

The root protocol must authorize finalization. Its caller retains the declared
file-only resource/deadline supervision and publishes the standard stage04.
"""
 start=time.monotonic();plan,baseline,admission=c.plan_gate(plan_path,plan_sha)
 proof=c.v.read(c.bind(external_closure));launch=c.v.read(c.LAUNCH);execution_path=c.E/'execution_pending_owner_exit.json';execution=c.v.read(execution_path)
 closed_native_proof(proof,launch,c.v.sha(execution_path),plan_sha)
 if execution['status']!='CONTROL_OUTPUTS_NAMESPACE_CLOSED_PENDING_OBSERVED_OWNER_EXIT_COMPARISON' or execution['all_started_unit_groups_closed'] is not True or execution['wsl_child_exit_code']!=0:raise RuntimeError('Successful closed control output absent')
 pending=c.v.read(c.OUT/'latest_pending_native.json');run=c.path(pending['run_directory'])
 if pending['input_plan_sha256']!=plan_sha:raise RuntimeError('Different pending control')
 manifest_path=c.path(pending['manifest_path'])
 if c.v.sha(manifest_path)!=pending['manifest_sha256']:raise RuntimeError('Control manifest changed after close')
 c.verify_manifest(run,c.v.read(manifest_path));result=c.v.read(run/'result.json')
 if result['input_plan_sha256']!=plan_sha or result['protocol_admission_sha256']!=c.v.sha(c.ADMISSION):raise RuntimeError('Control result/admission mismatch')
 feature=c.v.read(c.bind(result['feature_validation']));annotation=c.v.read(c.bind(result['annotation_receipt']));semantics=c.v.read(c.bind(result['semantic_identity']));quality_binding=c.v.read(c.bind(result['protein_quality_binding']))
 if semantics['original_sha256']!=plan['input']['fasta_sha256'] or semantics['original_sha256']==semantics['derived_sha256'] or semantics['original_semantics']!=semantics['derived_semantics']:raise RuntimeError('Genuine format-only DNA perturbation not established')
 if quality_binding['derived_FNA_sha256']!=semantics['derived_sha256'] or annotation['source_fna_sha256']!=semantics['derived_sha256'] or feature['source_FAA_sha256']!=annotation['faa_sha256'] or c.v.sha(c.bind(result['selected_faa']))!=annotation['faa_sha256']:raise RuntimeError('Control FNA/FAA/feature cross-binding differs')
 original_quality=c.v.read(c.bind(plan['baseline_quality_binding']))
 for key in ('core_model_database_binding','flags','original_caller_sha256'):
  if quality_binding[key]!=original_quality[key]:raise RuntimeError('Control method/options differ from baseline')
 def chain(role,validation_sha,manifest_sha,execution_sha,native_sha,authority):
  return {'status':'HASH_VERIFIED_VALIDATION_AND_NATIVE_CLOSED','role':role,'validation_sha256':validation_sha,'manifest_sha256':manifest_sha,'execution_sha256':execution_sha,'native_and_lease_closure_sha256':native_sha,'owned_group_empty':True,'native_exit_observed':True,'native_exit_code':0,'ordinary_runtime_closed':True,'image_unchanged':True,'common_leases_released':True,'original_artifacts_unchanged':True,'root_authority_sha256':authority}
 b=plan['baseline'];baseline_chain=chain('POSTHOC_BASELINE',b['validation']['sha256'],b['closed_manifest']['sha256'],b['execution']['sha256'],b['native_closure']['sha256'],b['root_acceptance']['sha256'])
 control_chain=chain('FORMAT_CONTROL',result['feature_validation']['sha256'],pending['manifest_sha256'],c.v.sha(execution_path),external_closure['sha256'],c.v.sha(c.ADMISSION))
 reference=compare.feature_evidence_from_closed_validation(baseline['validation'],baseline_chain);control=compare.feature_evidence_from_closed_validation(feature,control_chain)
 checks={'features':compare.compare_feature_receipts(reference,control),'report':compare.compare_protein_rows(baseline['validation']['raw_author_protein_report_row'],result['raw_author_protein_report_row']),'annotation':compare.compare_annotation_receipts(c.v.read(c.bind(plan['baseline_annotation'])),annotation)}
 reference_diamond=c.fasta.diamond_digest(c.path(plan['baseline_diamond_directory']));control_diamond=c.fasta.diamond_digest(c.path(result['quality_output'])/'diamond_output')
 checks['DIAMOND']=compare.compare_diamond_receipts(reference_diamond,control_diamond)
 if time.monotonic()-start>600:raise TimeoutError('External file-only comparison exceeded600s')
 passed=checks['features']['equal'] and checks['report']['equal_within_declared_tolerance'] and checks['annotation']['equal'] and checks['DIAMOND']['equal']
 output={'status':'FORMAT_CONTROL_V002_PASS_CLOSED' if passed else 'FORMAT_CONTROL_V002_DIFFERENCE_DETECTED','role':c.ROLE,'input_plan_sha256':plan_sha,'external_native_closure':external_closure,'baseline_root_authority_sha256':b['root_acceptance']['sha256'],'protocol_admission_sha256':c.v.sha(c.ADMISSION),'checks':checks,'baseline_features':reference,'control_features':control,'baseline_DIAMOND':reference_diamond,'control_DIAMOND':control_diamond,'original_failed_and_posthoc_artifacts_preserved':True,'production_panel_acceptance':False,'benchmark_acceptance':False,'nucleotide_route_numeric_equivalence_measured':False}
 destination=c.E/'comparison.json'
 if destination.exists():raise RuntimeError('Final comparison already recorded; no silent overwrite')
 c.v.save(destination,output)
 c.v.save(c.OUT/'latest_finalized.json',{'status':output['status'],'comparison_path':str(destination),'comparison_sha256':c.v.sha(destination),'external_native_closure':external_closure,'run_directory':str(run),'production_panel_acceptance':False})
 ended=datetime.datetime.now(datetime.timezone.utc).isoformat()
 diagnostic={'status':'COMPLETED' if passed else 'FAILED','done':1 if passed else 0,'total':1,'unit':'DNA-wrap61 format controls','updated_utc':ended,'ended_utc':ended,'detail':'DNA-wrap61 format control passed with actual exits/leases/comparison; benchmark remains pending' if passed else 'DNA-wrap61 control differences detected; no production acceptance','diagnostic_completion':output['status'],'operation':'FORMAT_CONTROL_COMPARISON','comparison_path':str(destination),'external_native_closure':external_closure,'production_panel_acceptance':False,'benchmark_status':'NOT_RUN','native_owner_history':launch['native_owner']}
 c.v.save(c.STATE,diagnostic)
 c.v.save(R/'state/stages/04.json',{'id':'04','name':'Independent biological QC',**diagnostic,'status':'PENDING_BENCHMARK' if passed else 'FAILED','ended_utc':None})
 return output
