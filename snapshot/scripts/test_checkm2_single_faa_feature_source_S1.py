"""Six small source/provenance fixtures. No real FAA, pickle, model or runtime."""
from pathlib import Path
import ast
import copy
import hashlib
import json
import sys
import uuid
import checkm2_single_faa_feature_validator_S1 as m

r=m.R;folder=r/'work/single_faa_S1_source_fixtures'/uuid.uuid4().hex;folder.mkdir(parents=True);checks=[]
request=folder/'request.json';request.write_text(json.dumps({'request_schema':'TREE2_SINGLE_FAA_FEATURE_REQUEST_S1'}));digest=hashlib.sha256(request.read_bytes()).hexdigest();assert m.read_request(request,digest)['request_schema']=='TREE2_SINGLE_FAA_FEATURE_REQUEST_S1'
try:m.read_request(request,'0'*64)
except RuntimeError:checks.append('Changed request hash is rejected before unpickle')
else:raise AssertionError('Changed request admitted')
valid={'status':'UNIT_EXIT0_GROUP_CLOSED','exit_code':0,'owned_group_empty':True,'remaining_owned_processes':[]};m.closed_quality_unit(valid)
for value in (None,False,0.0,-15):
 try:m.closed_quality_unit({**valid,'exit_code':value})
 except RuntimeError:pass
 else:raise AssertionError('Missing/false/nonzero exit treated as success')
checks.append('Each actual individual unit needs typed exit0 and an empty group')
expected=['SYNTHETIC_'+str(i) for i in range(10)];acc=expected[0];authority={'status':'ACCEPTED_TEN_ANNOTATIONS_AFTER_FAILED_T1_QUALITY_FOR_S1_PREPARATION','annotation_reuse_authorized':True,'prediction_execution_authorized':False,'whole_ten_quality_or_resource_benchmark_passed':False,'production_or_taxonomy_or_panel_acceptance':False,'accepted_annotation_commit_sha256s':dict.fromkeys(expected,'commitSHA'),'failed_quality_unit':{'path':'failed','sha256':'failedSHA'},'failure_closure':{'path':'closure','sha256':'closureSHA'},'original_native_exit':'UNKNOWN'}
failed={'failure_kind':'RESOURCE','exit_code':-15,'owned_group_empty':True,'remaining_owned_processes':[],'elapsed_seconds':104.24163487500482};commit={'status':'ANNOTATION_EXIT0_VALIDATED_ATOMIC_COMMIT','selected_faa':{'path':'FAA','sha256':'FAAsha'},'annotation_receipt':{'path':'annotation','sha256':'annSHA'},'unit_execution':{'path':'annunit','sha256':'unitSHA'}}
artifacts={'annotation_commit':{'path':'commit','sha256':'commitSHA'},'selected_faa':commit['selected_faa'],'annotation_receipt':commit['annotation_receipt'],'annotation_unit_execution':commit['unit_execution']};fake={'authority':authority,'failed':failed,'closure':{},'commit':commit}
original_read,original_bind=m.v.read,m.v.bind
try:
 m.v.bind=lambda row:row['path'];m.v.read=lambda path:copy.deepcopy(fake[path]);args=({'accession':acc,'artifacts':artifacts},{'annotation_reuse_authority':{'path':'authority','sha256':'authSHA'}},{'annotation_reuse_authority':{'sha256':'authSHA'},'failed_T1_quality_unit':{'sha256':'failedSHA'},'prior_failed_quality_elapsed_seconds':104.24163487500482},expected)
 assert m.annotation_authority(*args)['original_native_exit']=='UNKNOWN'
 fake['authority']['accepted_annotation_commit_sha256s'][acc]='otherSHA'
 try:m.annotation_authority(*args)
 except RuntimeError:pass
 else:raise AssertionError('Unaccepted annotation commit reused')
finally:m.v.read,m.v.bind=original_read,original_bind
checks.append('Annotation-only reuse preserves old UNKNOWN native exit and rejects an unaccepted commit')
item={'accession':'SYNTHETIC','species':'example','genus':'example','family':'example','role':'ANCILLARY_REVIEW','metadata_qc':'EXCLUDED','selection_status':'QC_REVIEW_ONLY','source_disposition':'HOLD','source_holds_preserved':['HOLD_SOURCE'],'source_metadata_checkm':{'completeness':None,'role':'CONTEXT_ONLY'},'source_taxonomy_gates':'UNRESOLVED'};before=copy.deepcopy(item)
row=m.b.measured_row_with_original_holds(item,{'raw_report':{'Name':'SYNTHETIC'},'Completeness':100.0,'Contamination':0.0});assert row['source_hold_active'] and row['source_holds_preserved']==['HOLD_SOURCE'] and row['production_acceptance']=='NOT_GRANTED';assert item==before
checks.append('Ideal numeric scores preserve original source holds, unknown context and no panel grant')
old=ast.parse((r/'scripts/checkm2_control_feature_validator_v002.py').read_text());new=ast.parse((r/'scripts/checkm2_single_faa_feature_validator_S1.py').read_text())
def assignments(tree):
 main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main');return {n.targets[0].id:ast.dump(n.value,include_attributes=False) for n in main.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name)}
a,b=assignments(old),assignments(new)
for name in ('values','joined','expected_aa','counts','expected','names','differences','canonical'):assert a[name]==b[name],name
assert sum(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='read_pickle' for n in ast.walk(new))==1
checks.append('One owned pickle load and unchanged finite-domain/FAA/raw-KO membership/canonical-row math expressions')
main_node=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='main');rehash=next(n for n in main_node.body if isinstance(n,ast.For) and ast.unparse(n.iter)=='artifacts.values()');environment={'item':copy.deepcopy(item),'artifacts':{'one':{'path':'synthetic1','sha256':'a'},'two':{'path':'synthetic2','sha256':'b'}},'v':type('FakeBind',(),{'bind':staticmethod(lambda value:value)})};exec(compile(ast.Module(body=[rehash],type_ignores=[]),'<source-row-survival-fixture>','exec'),environment);projected=m.b.measured_row_with_original_holds(environment['item'],{'raw_report':{'Name':'SYNTHETIC'},'Completeness':100.0,'Contamination':0.0});assert environment['item']==item and projected['accession']=='SYNTHETIC' and projected['source_hold_active']
checks.append('Actual final artifact rehash loop preserves the original accession/source row for hold projection')
contract=json.loads((r/'metadata/checkm2_single_faa_cohort_contract_S1_bound.json').read_text());assert len(contract['expected_accessions'])==10 and len(contract['annotation_members'])==10 and len(set(contract['inference_order']))==10;assert contract['inference_order']==[x['accession'] for x in sorted(contract['annotation_members'],key=lambda x:(-x['selected_faa']['bytes'],x['accession']))];assert contract['annotation_reuse_authority']['sha256']=='c9d163bb4a47b4ee5c54d205427b4f8f3e098311931b08f0dd5ad509ff9184f7' and contract['root_execution_admission'] is None and contract['actual_prediction_validation_or_cohort_outputs'] is None
assert contract['aggregate_contract']['genuine_quality_unit_receipts']==10 and contract['aggregate_contract']['genuine_validation_unit_receipts']==10 and contract['aggregate_contract']['synthetic_successful_batch_execution_receipt_forbidden']
assert not any(name in sys.modules for name in ('numpy','pandas','tensorflow','keras','lightgbm','sklearn','checkm2.prodigal'))
checks.append('Largest-first exact-ten contract remains HELD and requires20 genuine unit receipts, no synthetic batch')
report={'status':'PASS_PURE_SOURCE_FIXTURES_NOT_RUNTIME_OR_MATH_VALIDATION','checks':checks,'actual_FAA_pickle_model_or_runtime_used':False,'self_independent_math_review_claimed':False};path=r/'evidence/checkm2_single_faa_S1/source_fixture_report.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':'PASS_SOURCE_ONLY','checks':len(checks)}))
