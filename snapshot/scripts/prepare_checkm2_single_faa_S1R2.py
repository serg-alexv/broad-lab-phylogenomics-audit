"""Source-only S1R2 cut. Writes held metadata/checkpoint; never admits or dispatches."""
from pathlib import Path
import ast,hashlib,json,shutil,os,uuid
R=Path(__file__).resolve().parents[1]
ORIGINAL='04cf0befe7e969694de9698066d8406d2bc65a5de3990dbe9896fa075ecae2a2'
FILES=[
'scripts/checkm2_optional_progress_S1R2.py','scripts/checkm2_unit_observer_S1R2.py',
'scripts/checkm2_single_faa_common_S1R2.py','scripts/checkm2_single_faa_inner_S1R2.py','scripts/checkm2_single_faa_close_S1R2.py','scripts/checkm2_single_faa_feature_validator_S1R2.py',
'scripts/checkm2_single_faa_entry_S1R2.py','scripts/checkm2_single_faa_native_S1R2.py','scripts/checkm2_single_faa_S1R2.sh',
'scripts/checkm2_S1R2_observer_proof.py','scripts/checkm2_S1R2_observer_proof_native.py','scripts/test_checkm2_single_faa_S1R2_source.py','scripts/prepare_checkm2_single_faa_S1R2.py',
'metadata/checkm2_single_faa_cohort_contract_S1R2.json','metadata/checkm2_S1R2_observer_proof_HELD.json','metadata/checkm2_single_faa_source_fixture_receipt_S1R2.json','docs/CHECKM2_SINGLE_FAA_OPERATIONAL_REPAIR_S1R2.md']
def row(value):
 p=R/value;return {'path':value,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
def read(value):return json.loads((R/value).read_text(encoding='utf-8-sig'))
def write(value,data):
 p=R/value;p.parent.mkdir(parents=True,exist_ok=True);payload=(json.dumps(data,indent=2)+'\n').encode()
 if p.exists():
  if p.read_bytes()!=payload:raise RuntimeError('Existing source cut differs; preserve it: '+value)
  return row(value)
 temporary=p.with_name(p.name+'.'+uuid.uuid4().hex+'.part')
 with temporary.open('xb') as handle:handle.write(payload);handle.flush();os.fsync(handle.fileno())
 os.replace(temporary,p);return row(value)
def main():
 original=row('metadata/checkm2_single_faa_implementation_S1.json')
 if original['sha256']!=ORIGINAL:raise RuntimeError('Frozen original S1 manifest changed')
 old=read(original['path'])['sources']
 if len(old)!=58:raise RuntimeError('Exact original58 required')
 for item in old:
  if row(item['path'])!=item:raise RuntimeError('Original source changed: '+item['path'])
 for name in FILES:
  if name.endswith('.py'):ast.parse((R/name).read_text())
 cohort_path='metadata/checkm2_single_faa_cohort_contract_S1R2.json';cohort=read(cohort_path);limits=cohort['limits'];fixture=read('metadata/checkm2_single_faa_source_fixture_receipt_S1R2.json')
 for item in fixture['sources']:
  if row(item['path'])!=item:raise RuntimeError('Source fixtures do not bind current component')
 if fixture['status']!='PASS_SOURCE_ONLY_NOT_CAPABILITY_PROOF' or fixture['fixtures_passed']!=13:raise RuntimeError('Source fixture gate absent')
 rows=[*old,*[row(name) for name in FILES]]
 if len(rows)!=len({x['path'] for x in rows}):raise RuntimeError('Source paths duplicate')
 source=write('metadata/checkm2_single_faa_implementation_S1R2.json',{'schema':'TREE2_SINGLE_FAA_SOURCE_MANIFEST_S1R2','status':'HELD_SOURCE_REVIEW_NO_PROOF_OR_INFERENCE_ADMISSION','original58_unchanged':True,'sources':rows,'source_only_no_runtime_or_scientific_dispatch':True})
 role='SINGLE_FAA_INFERENCE_ONLY_METHOD_QC_S1R2';contract=row(cohort_path);proof=row('metadata/checkm2_S1R2_observer_proof_HELD.json')
 identity=hashlib.sha256(json.dumps({'source_manifest_sha256':source['sha256'],'cohort_contract_sha256':contract['sha256'],'role':role},sort_keys=True,separators=(',',':')).encode()).hexdigest()
 plan=write('metadata/checkm2_single_faa_execution_plan_S1R2.json',{'schema':'TREE2_SINGLE_FAA_INPUT_PLAN_S1R2','status':'HELD_PRESERVED_ONE_FRESH_NINE_NO_EXECUTION_ADMISSION','role':role,'phase':'RUN_FRESH_TARGETS','cohort_contract':contract,'source_manifest':source,'original_S1_source_manifest':original,'feature_schema':cohort['schema_v002'],'observer_boundary_proof_plan':proof,'limits':limits,'session_identity_sha256':identity,'annotation_reuse_authority':cohort['annotation_reuse_authority'],'preserved_row_authority':cohort['preserved_row_authority'],'logical_rows':10,'preserved_original_rows':1,'maximum_fresh_predictions':9,'actual_observer_boundary_proof':None,'actual_fresh_inference_rows':None,'actual_native_closure':None,'annotation_functions_invoked':False,'original_S1_phase_success':False,'ten_query_batch_benchmark_passed':False,'execution_admission':None})
 template=write('metadata/checkm2_single_faa_admission_template_S1R2.json',{'schema':'TREE2_SINGLE_FAA_INFERENCE_ADMISSION_S1R2','status':'HELD_SOURCE_REVIEW_NOT_ADMITTED','role':role,'single_faa_execution_authorized':False,'phase':'RUN_FRESH_TARGETS','max_predictions_per_accession':1,'max_new_predictions':9,'max_query_genomes_per_prediction':1,'input_plan_sha256':plan['sha256'],'source_manifest_sha256':source['sha256'],'cohort_contract_sha256':contract['sha256'],'limits':limits,'annotation_reuse_authority':cohort['annotation_reuse_authority'],'preserved_row_authority':cohort['preserved_row_authority'],'preserved_row_reuse_gate_passed':False,'explicit_second_attempt_exception':False,'annotation_reuse_gate_passed':False,'prior_failure_context_closed':False,'source_math_GO':False,'resource_lifecycle_GO':False,'monitor_standard_stage04_ready':False,'observer_boundary_proof':None,'unresolved_ownership_external_closure':None})
 destination=R/'checkpoints'/('checkm2_single_faa_S1R2_source_'+source['sha256'][:16]);destination.mkdir(parents=True,exist_ok=True)
 checkpoint=[]
 for item in [*rows,source,plan,template]:
  source_path=R/item['path'];target=destination/item['path'];target.parent.mkdir(parents=True,exist_ok=True)
  if not target.exists():
   temporary=target.with_name(target.name+'.'+uuid.uuid4().hex+'.part');shutil.copyfile(source_path,temporary)
   if hashlib.sha256(temporary.read_bytes()).hexdigest()!=item['sha256']:raise RuntimeError('Incomplete source checkpoint copy')
   os.replace(temporary,target)
  if hashlib.sha256(target.read_bytes()).hexdigest()!=item['sha256']:raise RuntimeError('Checkpoint hash differs')
  checkpoint.append(item)
 manifest={'status':'HELD_SOURCE_ONLY_CHECKPOINT','source_manifest_sha256':source['sha256'],'files':checkpoint,'source_only_no_scientific_artifacts':True}
 write((destination/'manifest.json').relative_to(R).as_posix(),manifest)
 receipt=write('metadata/checkm2_single_faa_source_preparation_S1R2.json',{'status':'SOURCE_FROZEN_HELD_PENDING_INDEPENDENT_REVIEWS_AND_REAL_OBSERVER_PROOF','source_manifest':source,'input_plan':plan,'admission_template':template,'cohort_contract':contract,'observer_boundary_proof_plan':proof,'source_fixture_receipt':row('metadata/checkm2_single_faa_source_fixture_receipt_S1R2.json'),'checkpoint_manifest':row((destination/'manifest.json').relative_to(R).as_posix()),'original58_unchanged':True,'source_count':len(rows),'logical10_equals_original1_plus_fresh9':True,'no_runtime_scientific_or_fault_proof_execution':True,'no_Ready_or_stage04_write':True,'author_does_not_independently_approve_own_feature_component':True})
 print(json.dumps({'source_manifest':source,'input_plan':plan,'receipt':receipt,'source_count':len(rows)}))
if __name__=='__main__':main()
