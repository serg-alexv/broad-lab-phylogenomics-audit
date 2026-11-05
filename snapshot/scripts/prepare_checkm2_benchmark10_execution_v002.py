"""Freeze HELD benchmark source/plan/templates from metadata; no runtime calls."""
from pathlib import Path
import ast,hashlib,json,os
R=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(relative):
 p=R/relative;return {'path':relative,'sha256':sha(p),'bytes':p.stat().st_size}
def read(relative):return json.loads((R/relative).read_text())
def write(relative,value):
 p=R/relative;data=(json.dumps(value,indent=2)+'\n').encode()
 if p.exists():
  if p.read_bytes()!=data:raise RuntimeError('Held source output changed; preserve/review before refreshing:'+relative)
 else:
  tmp=p.with_suffix('.partial')
  with tmp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
  os.replace(tmp,p)
 return pin(relative)
def main():
 active='metadata/checkm2_format_implementation_v002_ENV1.json'
 if sha(R/active)!='61818341fb9a6b33956d20abb4e8c4b956b45be565be5f5acf0e28323a823d43':raise RuntimeError('Accepted active control source manifest differs')
 sources={row['path']:row for row in read(active)['sources']}
 for row in sources.values():
  if pin(row['path'])!=row:raise RuntimeError('Active control source was changed')
 own=['checkm2_benchmark10_common_v002.py','checkm2_benchmark10_inner_v002.py','checkm2_benchmark10_native_v002.py','checkm2_benchmark10_entry_v002.py','checkm2_benchmark10_close_v002.py','checkm2_benchmark10_protein_v002.sh','checkm2_benchmark10_feature_validator_v002.py','prepare_checkm2_benchmark10_wrappers_v002.py','prepare_checkm2_benchmark10_execution_v002.py','test_checkm2_benchmark10_workflow_v002.py']
 for name in own:
  row=pin('scripts/'+name);sources[row['path']]=row
  if name.endswith('.py'):ast.parse((R/row['path']).read_text())
 if sources['scripts/checkm2_benchmark10_feature_validator_v002.py']['sha256']!='221c04021d718960c7b736a5255c48bb5f7792e980ae512f2a6ef463ddcd933b':raise RuntimeError('Independent row validator source differs')
 shell=R/'scripts/checkm2_benchmark10_protein_v002.sh'
 if b'\r' in shell.read_bytes():raise RuntimeError('Benchmark shell contains CR')
 manifest=write('metadata/checkm2_benchmark10_implementation_v002.json',{'schema':'TREE2_BENCHMARK10_EXECUTOR_SOURCE_MANIFEST_V002','status':'HELD_SOURCE_REVIEW_NO_EXECUTION','sources':list(sources.values()),'accepted_original27_control_sources_unchanged':True,'resource_and_original_annotation_helpers_reused_unchanged':True,'LF_and_explicit_Linux_env_transport_required':True,'scientific_data_or_runtime_execution_during_preparation':False})
 recipe=pin('metadata/checkm2_benchmark10_protein_recipe_v002_bound.json')
 if recipe['sha256']!='2e003f02e6b1886ebe65c4e4d7a9351d84e6ad404d09384ece668089ba3f5fce':raise RuntimeError('Bound HELD recipe differs')
 obj=read(recipe['path']);limits=obj['limits'];identity=hashlib.sha256(json.dumps({'strategy':obj['source_strategy']['sha256'],'recipe':recipe['sha256'],'sources':manifest['sha256'],'image':'c40e6918688eaf2e1a9e4161e77a4b473c3f611de575b39a89bdc03fba224ad4','schema':'90e482515c6924386a888aa14a036f7659acf9ad0c49814cb08a3a7e1f76f5ee'},sort_keys=True,separators=(',',':')).encode()).hexdigest()
 plan=write('metadata/checkm2_benchmark10_execution_plan_v002.json',{'schema':'TREE2_BENCHMARK10_PROTEIN_INPUT_PLAN_V002','status':'HELD_SOURCE_REVIEW_AND_NEW_PHASE_ADMISSION','role':obj['role'],'strategy':obj['source_strategy'],'recipe':recipe,'source_manifest':manifest,'session_identity_sha256':identity,'format_control_comparison':obj['method_gates']['closed_format_control_comparison'],'format_control_root_acceptance':obj['method_gates']['root_format_control_acceptance'],'feature_schema':pin('metadata/checkm2_feature_schema_v002.json'),'original_prodigal_source_sha256':'4d962b423281b81edf3e9eec7ce3219388a0df8ae52c13cde883419826592b6f','limits':limits,'execution_admission':None,'real_annotation_commits':None,'real_prediction_commit':None,'real_boundary_or_resume_demonstrated':False,'no_eleventh_genome':True,'all3_ancillary_holds_preserved':True,'stock_resume_force_split_or_automatic_retry':False,'production_or_full_panel_acceptance':False})
 template={'schema':'TREE2_BENCHMARK10_PROTEIN_ADMISSION_V002','status':'HELD_NOT_ADMITTED','role':obj['role'],'phase':'BOUNDARY_AFTER_FIRST_ANNOTATION','benchmark_execution_authorized':False,'max_batch_prediction_attempts':1,'input_plan_sha256':plan['sha256'],'source_manifest_sha256':manifest['sha256'],'recipe_sha256':recipe['sha256'],'format_control_comparison':obj['method_gates']['closed_format_control_comparison'],'format_control_root_acceptance':obj['method_gates']['root_format_control_acceptance'],'limits':limits,'format_control_gate_passed':False,'monitor_standard_stage04_ready':False,'source_math_GO':False,'resource_lifecycle_GO':False,'resume_authority':None,'external_boundary_first_annotation_exit_lease_proof_required_before_CONTINUE':True,'native_outer_seconds':10800,'helper_outer_seconds':10200,'closed_image_hash_seconds':600,'no_full_panel_grant':True}
 write('metadata/checkm2_benchmark10_admission_template_v002.json',template)
 print(json.dumps({'status':'HELD_SOURCE_ONLY','source_manifest':manifest,'input_plan':plan,'no_runtime_or_data_calls':True}))
if __name__=='__main__':main()
