"""Prepare a HELD source tuple only; never stages data or creates a Ready admission."""
from pathlib import Path
import ast,hashlib,json,os
R=Path(__file__).resolve().parents[1]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(name):return json.loads((R/name).read_text())
def pin(name):
 p=R/name;return {'path':name,'sha256':sha(p),'bytes':p.stat().st_size}
def write(name,obj):
 p=R/name;data=(json.dumps(obj,indent=2)+'\n').encode()
 if p.exists():
  if p.read_bytes()!=data:raise RuntimeError('Preserve reviewed held S1 revision before refreshing:'+name)
 else:
  with p.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 return pin(name)

def main():
 prior='metadata/checkm2_benchmark10_implementation_T1.json'
 if sha(R/prior)!='a4052ef77041eb0962eae67e70de854960307659b2e7bbb5b9ad81877d392812':raise RuntimeError('Frozen original48 manifest differs')
 sources={x['path']:x for x in read(prior)['sources']}
 for x in sources.values():
  if pin(x['path'])!=x:raise RuntimeError('Frozen original48 source changed:'+x['path'])
 names=['checkm2_single_faa_common_S1.py','checkm2_single_faa_inner_S1.py','checkm2_single_faa_close_S1.py','checkm2_single_faa_entry_S1.py','checkm2_single_faa_native_S1.py','checkm2_single_faa_S1.sh','checkm2_single_faa_feature_validator_S1.py','test_checkm2_single_faa_budget_S1.py','test_checkm2_single_faa_feature_source_S1.py','prepare_checkm2_single_faa_tuple_S1.py']
 for name in names:
  p='scripts/'+name;sources[p]=pin(p)
  if name.endswith('.py'):ast.parse((R/p).read_text())
 if b'\r' in (R/'scripts/checkm2_single_faa_S1.sh').read_bytes():raise RuntimeError('S1 shell contains CR')
 contract=pin('metadata/checkm2_single_faa_cohort_contract_S1_bound.json')
 if contract['sha256']!='904d6be6f4370a0370f6d6adacdbfab0742047b278ebb0dbe65272cae070a574':raise RuntimeError('Reviewed S1 bound annotation contract differs')
 cohort=read(contract['path']);common=ast.parse((R/'scripts/checkm2_single_faa_common_S1.py').read_text());limits=ast.literal_eval(next(n.value for n in common.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='LIMITS' for t in n.targets)))
 if limits!=cohort['limits']:raise RuntimeError('S1 producer/validator limits differ')
 manifest=write('metadata/checkm2_single_faa_implementation_S1.json',{'schema':'TREE2_SINGLE_FAA_SOURCE_MANIFEST_S1','status':'HELD_SOURCE_REVIEW_NO_INFERENCE_ADMISSION','sources':list(sources.values()),'original48_unchanged':True,'source_only_no_annotation_or_runtime_dispatch':True})
 session=hashlib.sha256(json.dumps({'cohort':contract['sha256'],'sources':manifest['sha256'],'workspace':'analysis/checkm2_single_faa_S1','failed_quality_debit':104.24163487500482},sort_keys=True,separators=(',',':')).encode()).hexdigest()
 plan=write('metadata/checkm2_single_faa_execution_plan_S1.json',{'schema':'TREE2_SINGLE_FAA_INPUT_PLAN_S1','status':'HELD_ANNOTATION_AUTHORITY_BOUND_NO_INFERENCE_ADMISSION','role':'SINGLE_FAA_INFERENCE_ONLY_METHOD_QC_S1','cohort_contract':contract,'source_manifest':manifest,'feature_schema':cohort['schema_v002'],'limits':limits,'session_identity_sha256':session,'annotation_reuse_authority':cohort['annotation_reuse_authority'],'actual_inference_rows':None,'actual_native_closure':None,'annotation_functions_invoked':False,'ten_query_batch_benchmark_passed':False,'execution_admission':None})
 template={'schema':'TREE2_SINGLE_FAA_INFERENCE_ADMISSION_S1','status':'HELD_SOURCE_REVIEW_NOT_ADMITTED','role':'SINGLE_FAA_INFERENCE_ONLY_METHOD_QC_S1','single_faa_execution_authorized':False,'phase':'RUN_FRESH_SERIES','max_predictions_per_accession':1,'max_query_genomes_per_prediction':1,'input_plan_sha256':plan['sha256'],'source_manifest_sha256':manifest['sha256'],'cohort_contract_sha256':contract['sha256'],'limits':limits,'annotation_reuse_authority':cohort['annotation_reuse_authority'],'annotation_reuse_gate_passed':False,'prior_failure_context_closed':False,'source_math_GO':False,'resource_lifecycle_GO':False,'monitor_standard_stage04_ready':False,'closed_row_reuse_authority':None,'unresolved_ownership_external_closure':None}
 write('metadata/checkm2_single_faa_admission_template_S1.json',template)
 print(json.dumps({'status':'HELD_SOURCE_ONLY_NO_S1_RUN','manifest':manifest,'plan':plan,'cohort':contract,'source_count':len(sources),'Ready_or_stage04_written':False}))

if __name__=='__main__':main()
