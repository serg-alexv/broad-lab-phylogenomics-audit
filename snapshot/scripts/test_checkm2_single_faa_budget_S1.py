"""Pure synthetic metadata checks only: no processes, genomes, scientific imports or state rows."""
import ast,copy,json,uuid
from pathlib import Path
import checkm2_single_faa_common_S1 as c

def require_error(fn):
 try:fn()
 except (RuntimeError,FileNotFoundError,KeyError):return
 raise AssertionError('Unsafe/missing evidence was accepted')

def fake_unit(root,name,seconds,acc='DUMMY_ACCESSION.1'):
 folder=root/'rows'/acc;unit=folder/name;unit.mkdir(parents=True,exist_ok=True)
 c.save(folder/'once_claim.json',{'synthetic_only':True})
 c.save(folder/(name+'_budget.json'),{'synthetic_only':True})
 c.save(unit/'command.json',{'synthetic_only':'NEVER_EXECUTED'})
 c.save(unit/'execution.json',{'elapsed_seconds':seconds,'owned_group_empty':True,'remaining_owned_processes':[]})
 return unit

def main():
 root=c.R/'work'/('single_faa_S1_pure_'+uuid.uuid4().hex);root.mkdir(parents=True);checks=[]
 empty=root/'empty';empty.mkdir();b=c.budget(empty)
 assert b['prior_failed_quality_seconds']==104.24163487500482 and b['remaining_seconds']==3495.758365;checks.append('Historical failed quality debit is fixed once; no fresh3600 allowance')
 good=root/'good';fake_unit(good,'unit_quality',228);fake_unit(good,'unit_feature_validation',2);b=c.budget(good)
 assert b['new_seconds_debited']==230 and b['per_genome_seconds']['DUMMY_ACCESSION.1']==230 and b['remaining_seconds']==3495.758365-230;checks.append('Quality and independent validation share one per-genome/global allocation')
 too_long=root/'too_long';fake_unit(too_long,'unit_quality',590);fake_unit(too_long,'unit_feature_validation',11);require_error(lambda:c.budget(too_long));checks.append('A second600s validator allowance cannot extend a genome past600s')
 missing=root/'missing';u=fake_unit(missing,'unit_quality',1);(u/'execution.json').unlink();require_error(lambda:c.budget(missing));checks.append('Missing terminal elapsed blocks rather than resets its debit')
 deleted=root/'deleted_command';u=fake_unit(deleted,'unit_quality',1);(u/'command.json').unlink();require_error(lambda:c.budget(deleted));checks.append('Deleting a command while its terminal/allocation remains cannot erase time')
 claimed=root/'claimed_only';folder=claimed/'rows/DUMMY_ACCESSION.1';folder.mkdir(parents=True);c.save(folder/'once_claim.json',{'synthetic_only':True});require_error(lambda:c.budget(claimed));checks.append('Prediction once-claim without start evidence stays unresolved and nonreplayable')
 node=next(x for x in ast.parse((c.R/'scripts/checkm2_single_faa_common_S1.py').read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='current_failed_run');out=root/'locator';run=out/'runs/fake';run.mkdir(parents=True)
 read=lambda p:json.loads(Path(p).read_text());env={'OUT':out,'path':lambda p:Path(p).resolve(),'read':read};exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual-current-failed-run-AST>','exec'),env);locate=env['current_failed_run'];step={'windows_launch_token':'TOKEN','input_plan_sha256':'PLAN','protocol_admission_sha256':'ADMIT','run_directory':str(run)}
 assert locate({**step,'windows_launch_token':'OLD'},'TOKEN','PLAN','ADMIT') is None
 require_error(lambda:locate(step,'TOKEN','PLAN','ADMIT'))
 c.save(run/'binding.json',{'launch':{'token':'TOKEN','input_plan_sha256':'PLAN','protocol_admission_sha256':'ADMIT'},'admission':{'sha256':'ADMIT'},'plan':{'_sha':'PLAN','session_identity_sha256':'SESSION'}});c.save(run/'failure.json',{'status':'S1_FAILED_NO_AUTOMATIC_RETRY_OR_FALLBACK','annotation_invoked':False});c.save(run/'invocations.json',[])
 assert locate(step,'TOKEN','PLAN','ADMIT')==run;checks.append('Optional current-run locator cannot replace required failure/launch/source evidence')
 tree=ast.parse((c.R/'scripts/checkm2_single_faa_inner_S1.py').read_text());strings=[x.value for x in ast.walk(tree) if isinstance(x,ast.Constant) and isinstance(x.value,str)]
 assert 'annotate' not in strings and '--genes' in strings and '--lowmem' in strings and '--resume' not in strings;checks.append('New dispatcher has no annotation or stock-resume command path')
 producer=next(n.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='request' for t in n.targets))
 class Dummy:
  ADMISSION='DUMMY_NEVER_READ'
  @staticmethod
  def row(p):return {'path':'DUMMY','sha256':'ADMIT','bytes':0}
 artifact={'path':'DUMMY','sha256':'SHA','bytes':0};schema={'path':'DUMMY_SCHEMA','sha256':'90e482515c6924386a888aa14a036f7659acf9ad0c49814cb08a3a7e1f76f5ee','bytes':0}
 produced=eval(compile(ast.Expression(producer),'<actual-producer-request-AST>','eval'),{'c':Dummy,'acc':'DUMMY_ACCESSION.1','prefix':Path('/DUMMY'),'plan':{'_sha':'PLAN','cohort_contract':artifact,'source_manifest':artifact,'feature_schema':schema},'prediction':{k:artifact for k in ('raw_pickle','quality_report','quality_unit_execution')},'member':{k:artifact for k in ('selected_faa','annotation_receipt','annotation_unit_execution','annotation_commit')}})
 consumer=ast.parse((c.R/'scripts/checkm2_single_faa_feature_validator_S1.py').read_text());required={n.slice.value for n in ast.walk(consumer) if isinstance(n,ast.Subscript) and isinstance(n.value,ast.Name) and n.value.id=='request' and isinstance(n.slice,ast.Constant) and isinstance(n.slice.value,str)}
 assert required.issubset(produced) and produced['schema']==schema;checks.append('Actual producer request supplies every frozen consumer top-level field and exact schema90e')
 receipt={'status':'PASS_PURE_SYNTHETIC_S1_METADATA_FIXTURES_NOT_RUNTIME_OR_QC','checks':checks,'scientific_processes_genomes_models_or_current_state_used':False,'synthetic_workspace':root.relative_to(c.R).as_posix()};c.save(c.E/'source_budget_fixture_report.json',receipt);print(json.dumps(receipt))

if __name__=='__main__':main()
