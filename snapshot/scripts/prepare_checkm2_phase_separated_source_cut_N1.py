"""Freeze held N1 source/plan only. Never read a genome, image, model or pickle."""
from pathlib import Path
import ast,datetime,hashlib,json
R=Path(__file__).resolve().parents[1]
def read(n):return json.loads((R/n).read_text())
def row(n):
 p=R/n
 return {'path':n,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
def save(n,d):
 p=R/n
 if p.exists():raise RuntimeError('Preserve prior frozen source proposal rather than overwrite: '+n)
 with p.open('x',newline='\n') as f:json.dump(d,f,indent=2);f.write('\n')
def main():
 original=read('metadata/checkm2_single_faa_implementation_S1R2.json');sources={x['path']:x for x in original['sources']}
 for n,expected in sources.items():
  if row(n)!=expected:raise RuntimeError('Original accepted75 source changed: '+n)
 names=[str(p.relative_to(R)).replace('\\','/') for p in (R/'scripts').glob('checkm2_phase_separated_*_N1.py')]
 names+=['scripts/checkm2_phase_separated_N1.sh','scripts/test_checkm2_phase_separated_sources_N1.py','scripts/test_checkm2_phase_separated_OPS_N1.py','scripts/test_checkm2_phase_separated_artifacts_N1.py','scripts/prepare_checkm2_phase_separated_source_cut_N1.py']
 for suffix in ('','_v002','_v003'):
  names+=['scripts/prepare_checkm2_phase_separated_history_N1'+suffix+'.py']
  names+=['metadata/checkm2_phase_separated_'+key+'_N1'+suffix+'.json' for key in ('history_index','queue','selected_input')]
 names+=['metadata/checkm2_phase_separated_recipe_N1.json','metadata/checkm2_phase_separated_source_fixtures_N1.json','metadata/checkm2_N1_novelty_queue_review_v003.json','metadata/checkm2_phase_separated_artifact_component_N1.json','docs/CHECKM2_PHASE_SEPARATED_N1_IMPLEMENTATION_HELD.md','metadata/checkm2_accepted_method_result_registry_v001.json','evidence/checkm2_phase_separated_N1/root_scope_source_selection_authority.json','metadata/nomenclature_type_holds/v001/commit.json','metadata/nomenclature_type_holds/v001/manifest.json','metadata/nomenclature_type_holds/v001/genomes.tsv']
 for n in names:
  if not (R/n).is_file():raise RuntimeError('Missing frozen source component: '+n)
  if n.endswith('.py'):ast.parse((R/n).read_text())
  sources[n]=row(n)
 recipe=read('metadata/checkm2_phase_separated_recipe_N1.json');acc=recipe['input']['accession']
 save('metadata/checkm2_phase_separated_implementation_N1_v002.json',{'schema':'TREE2_PHASE_SEPARATED_N1_SOURCE_MANIFEST_V001','status':'HELD_FROZEN_SOURCE_NO_EXECUTION_ADMISSION','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'original75_manifest':row('metadata/checkm2_single_faa_implementation_S1R2.json'),'original75_exact':True,'scientific_component_author_not_independent_reviewer':True,'sources':list(sources.values()),'scope_authority':recipe['scope_authority'],'selected_input':recipe['selected_input'],'role':recipe['role'],'scientific_execution_authorized':False})
 source=row('metadata/checkm2_phase_separated_implementation_N1_v002.json');recipe_row=row('metadata/checkm2_phase_separated_recipe_N1.json')
 identity=hashlib.sha256(json.dumps({'source':source['sha256'],'recipe':recipe_row['sha256'],'accession':acc,'scope_authority':recipe['scope_authority']['sha256']},sort_keys=True).encode()).hexdigest()
 plan={'schema':'TREE2_PHASE_SEPARATED_N1_INPUT_PLAN_V001','status':'HELD_SOURCE_ONLY_NO_SCIENTIFIC_GRANT','role':recipe['role'],'scientific_recipe':recipe_row,'source_manifest':source,'selected_input':recipe['selected_input'],'feature_schema':recipe['schema_v002'],'scope_authority':recipe['scope_authority'],'limits':recipe['limits'],'session_identity_sha256':identity,'accession':acc,'input':recipe['input'],'actual_annotation_search_prediction_or_feature_outputs':None,'scientific_execution_authorized':False}
 save('metadata/checkm2_phase_separated_execution_plan_N1_v002.json',plan);plan_row=row('metadata/checkm2_phase_separated_execution_plan_N1_v002.json')
 save('metadata/checkm2_phase_separated_admission_TEMPLATE_N1_v002.json',{'schema':'TREE2_PHASE_SEPARATED_N1_ADMISSION_V001','status':'HELD_NOT_ADMITTED','role':recipe['role'],'n1_execution_authorized':False,'phase':'RUN_FRESH_ONCE','max_inputs':1,'input_plan_sha256':plan_row['sha256'],'source_manifest_sha256':source['sha256'],'recipe_sha256':recipe_row['sha256'],'limits':recipe['limits'],'novel_selection_history_GO':None,'source_math_ABI_GO':None,'resource_lifecycle_GO':None,'monitor_standard_stage04_ready':False,'actual_Root_scientific_authority':None,'actual_prelaunch':None})
 print(json.dumps({'source_manifest':source,'input_plan':plan_row,'source_count':len(sources),'actual_scientific_execution_authorized':False}))
if __name__=='__main__':main()
