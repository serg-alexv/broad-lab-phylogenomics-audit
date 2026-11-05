"""Freeze only a HELD T1 operational tuple; never create a retry admission."""
from pathlib import Path
import ast,hashlib,json,os
R=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(name):
 p=R/name;return {'path':name,'sha256':sha(p),'bytes':p.stat().st_size}
def read(name):return json.loads((R/name).read_text())
def write(name,obj):
 p=R/name;data=(json.dumps(obj,indent=2)+'\n').encode()
 if p.exists():
  if p.read_bytes()!=data:raise RuntimeError('Held T1 tuple changed; preserve reviewed revision before refresh:'+name)
 else:
  with p.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 return pin(name)
def main():
 original='metadata/checkm2_benchmark10_implementation_v002.json'
 if sha(R/original)!='ca7d48fc4ac927209cce4e4d3e2b4bbef9d9ecc99984d98aa4f30a94f5cb65f0':raise RuntimeError('Original37 manifest differs')
 sources={x['path']:x for x in read(original)['sources']}
 for x in sources.values():
  if pin(x['path'])!=x:raise RuntimeError('Original37 source changed')
 own=['checkm2_optional_telemetry_v001.py','checkm2_owned_cleanup_T1.py','checkm2_benchmark10_common_T1.py','checkm2_benchmark10_inner_T1.py','checkm2_benchmark10_close_T1.py','checkm2_benchmark10_entry_T1.py','checkm2_benchmark10_native_T1.py','checkm2_benchmark10_protein_T1.sh','prepare_checkm2_benchmark10_recovery_controller_T1.py','prepare_checkm2_benchmark10_recovery_tuple_T1.py','test_checkm2_benchmark10_recovery_budget_T1.py']
 for name in own:
  x=pin('scripts/'+name);sources[x['path']]=x
  if name.endswith('.py'):ast.parse((R/x['path']).read_text())
 if sources['scripts/checkm2_optional_telemetry_v001.py']['sha256']!='561164f65f9ee0dd312cb7fd365312cc0a46c86485a3218382add15b630903ef':raise RuntimeError('Tested optional reader differs')
 if b'\r' in (R/'scripts/checkm2_benchmark10_protein_T1.sh').read_bytes():raise RuntimeError('T1 executed shell contains CR')
 manifest=write('metadata/checkm2_benchmark10_implementation_T1.json',{'schema':'TREE2_BENCHMARK10_OPERATIONAL_SOURCE_MANIFEST_T1','status':'HELD_OPERATIONAL_REPAIR_REVIEW_NO_RETRY','sources':list(sources.values()),'original37_scientific_and_operational_sources_unchanged':True,'scientific_caller_validator_math_fork_inputs_holds_unchanged':True,'new_owned_cleanup_requires_independent_review':True,'cached_reader_probe_does_not_validate_forced_cleanup':True})
 policy=pin('metadata/checkm2_benchmark10_recovery_policy_T1.json')
 if policy['sha256']!='e6542c79c80780d93a3a99bacaa825580e6a1c8dd3ace1032ab7292fe1f50e21':raise RuntimeError('Historical debit/recovery policy differs')
 base=read('metadata/checkm2_benchmark10_execution_plan_v002.json')
 if sha(R/'metadata/checkm2_benchmark10_execution_plan_v002.json')!='42c5ec31053a3b856f60676932647b3b795ef805c4c399c239376a4c91c424b1':raise RuntimeError('Original failed plan differs')
 base.update(status='HELD_T1_OPERATIONAL_REPAIR_NO_RETRY_ADMISSION',source_manifest=manifest,operational_recovery_policy=policy,original_failed_plan=pin('metadata/checkm2_benchmark10_execution_plan_v002.json'),real_annotation_commits=None,real_prediction_commit=None,real_boundary_or_resume_demonstrated=False,execution_admission=None)
 base['session_identity_sha256']=hashlib.sha256(json.dumps({'original_session':base['session_identity_sha256'],'T1_source_manifest':manifest['sha256'],'recovery_policy':policy['sha256'],'isolated_workspace':'analysis/checkm2_benchmark10_protein_recovery_T1'},sort_keys=True,separators=(',',':')).encode()).hexdigest()
 plan=write('metadata/checkm2_benchmark10_execution_plan_T1.json',base)
 template=read('metadata/checkm2_benchmark10_admission_template_v002.json');template.update(status='HELD_T1_NOT_ADMITTED_NO_RETRY',input_plan_sha256=plan['sha256'],source_manifest_sha256=manifest['sha256'],operational_recovery_policy_sha256=policy['sha256'],historical_unknown_annotation_debit_seconds=600,new_annotation_seconds_remaining=5400,total_annotation_allowance_including_history_seconds=6000,max_campaign_physical_attempts=11,benchmark_execution_authorized=False,source_math_GO=False,resource_lifecycle_GO=False,monitor_standard_stage04_ready=False,resume_authority=None,unresolved_ownership_external_closure=None)
 write('metadata/checkm2_benchmark10_admission_template_T1.json',template)
 print(json.dumps({'status':'HELD_SOURCE_ONLY_NO_T1_RETRY','source_manifest':manifest,'input_plan':plan,'policy':policy,'original37_modified':False,'no_runtime_or_data_calls':True}))
if __name__=='__main__':main()
