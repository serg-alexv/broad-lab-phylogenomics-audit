"""Freeze only N5 source/metadata. No raw inputs, runtime, image, models or scientific process."""
from pathlib import Path
import ast,datetime,hashlib,json,os
R=Path(__file__).resolve().parents[1]
def read(n):return json.loads((R/n).read_text())
def row(n):
 p=R/n;return{'path':n,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
def save(n,d):
 p=R/n
 with p.open('x',newline='\n')as f:json.dump(d,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def main():
 original_name='metadata/checkm2_phase_separated_implementation_N1_v002.json';assert row(original_name)['sha256']=='4c5828cf8dd5d4451d5fce9447644ee5be49aca02f939e5dac613db93112bdce';original=read(original_name);sources={x['path']:x for x in original['sources']}
 assert len(sources)==111
 for name,expected in sources.items():
  if row(name)!=expected:raise RuntimeError('Original111 source changed: '+name)
 names=[str(p.relative_to(R)).replace('\\','/')for p in(R/'scripts').glob('checkm2_phase_separated_*_N5.py')]
 names+=['scripts/checkm2_phase_separated_N5.sh','scripts/test_checkm2_phase_separated_sources_N5_v002.py','scripts/test_checkm2_phase_separated_OPS_N5.py','scripts/prepare_checkm2_phase_separated_history_N5.py','scripts/prepare_checkm2_phase_separated_source_cut_N5.py','metadata/checkm2_phase_separated_recipe_N5.json','metadata/checkm2_phase_separated_source_fixtures_N5_v002.json','metadata/checkm2_phase_separated_OPS_pure_fixtures_N5.json','metadata/checkm2_phase_separated_OPS_component_HELD_N5_v001.json','metadata/checkm2_N5_source_selection_implementation_authority_v001.json','metadata/checkm2_N5_independent_history_selection_review_v002.json','metadata/checkm2_accepted_method_result_registry_v002.json','evidence/checkm2_phase_separated_N1/root_closed_method_acceptance_N1.json','docs/CHECKM2_PHASE_SEPARATED_N5_IMPLEMENTATION_HELD.md','docs/CHECKM2_PHASE_SEPARATED_OPS_N5_SOURCE.md']
 for suffix in('','_v002'):names+=['metadata/checkm2_phase_separated_'+kind+'_N5'+suffix+'.json'for kind in('history_index','queue','selected_inputs')]
 names+=[str(p.relative_to(R)).replace('\\','/')for p in(R/'metadata/checkm2_N5_selection_integrity').glob('*.json')]
 for n in names:
  if n.endswith('.py'):ast.parse((R/n).read_text())
  sources[n]=row(n)
 recipe=read('metadata/checkm2_phase_separated_recipe_N5.json');recipe_row=row('metadata/checkm2_phase_separated_recipe_N5.json')
 save('metadata/checkm2_phase_separated_implementation_N5_v002.json',{'schema':'TREE2_PHASE_SEPARATED_N5_SOURCE_MANIFEST_V001','status':'HELD_FROZEN_SOURCE_NO_EXECUTION_ADMISSION','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'original111_manifest':row(original_name),'original111_and75_exact':True,'scientific_component_author_not_independent_reviewer':True,'sources':list(sources.values()),'scope_authority':recipe['scope_authority'],'selected_inputs':recipe['selected_inputs'],'role':recipe['role'],'scientific_execution_authorized':False})
 manifest=row('metadata/checkm2_phase_separated_implementation_N5_v002.json');identity=hashlib.sha256(json.dumps({'source':manifest['sha256'],'recipe':recipe_row['sha256'],'accessions':recipe['inference_order'],'scope_authority':recipe['scope_authority']['sha256']},sort_keys=True).encode()).hexdigest()
 plan={'schema':'TREE2_PHASE_SEPARATED_N5_INPUT_PLAN_V001','status':'HELD_SOURCE_ONLY_NO_SCIENTIFIC_GRANT','role':recipe['role'],'scientific_recipe':recipe_row,'source_manifest':manifest,'selected_inputs':recipe['selected_inputs'],'feature_schema':recipe['schema_v002'],'scope_authority':recipe['scope_authority'],'limits':recipe['limits'],'session_identity_sha256':identity,'accessions':recipe['inference_order'],'inputs':recipe['inputs'],'strict_serial_four_phases_per_input':True,'actual_annotation_search_prediction_or_feature_outputs':None,'scientific_execution_authorized':False}
 save('metadata/checkm2_phase_separated_execution_plan_N5_v002.json',plan);plan_row=row('metadata/checkm2_phase_separated_execution_plan_N5_v002.json')
 save('metadata/checkm2_phase_separated_admission_TEMPLATE_N5_v002.json',{'schema':'TREE2_PHASE_SEPARATED_N5_ADMISSION_V001','status':'HELD_NOT_ADMITTED','role':recipe['role'],'n5_execution_authorized':False,'phase':'RUN_FRESH_SERIAL_FIVE_ONCE','max_inputs':5,'input_plan_sha256':plan_row['sha256'],'source_manifest_sha256':manifest['sha256'],'recipe_sha256':recipe_row['sha256'],'limits':recipe['limits'],'novel_selection_history_GO':None,'source_math_ABI_GO':None,'resource_lifecycle_GO':None,'monitor_standard_stage04_ready':False,'actual_Root_scientific_authority':None,'actual_prelaunch':None})
 print(json.dumps({'source_manifest':manifest,'input_plan':plan_row,'recipe':recipe_row,'source_count':len(sources),'actual_scientific_execution_authorized':False}))
if __name__=='__main__':main()
