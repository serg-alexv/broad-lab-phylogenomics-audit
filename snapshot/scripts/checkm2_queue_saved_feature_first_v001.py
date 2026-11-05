"""First unit in an existing admitted RO session; no runtime or model launcher.

The owner supplies its existing guarded invoke callback. This module cannot
call stock prediction, annotation or DIAMOND and never promotes a registry.
"""
from pathlib import Path
import hashlib,json,math,os
R=Path(__file__).resolve().parents[1]
ACC='GCF_900636715.1'
REQUEST_SHA='e585a66ecf45d508294ae161024fdef1ee2c57bb55fd5e0f5f4fe3bcdd32621e'
FAILED_VALIDATION_SECONDS=6.108859692001715
REMAINING_SECONDS=120-FAILED_VALIDATION_SECONDS

def path(value):
    p=Path(value);text=str(p).replace('\\','/')
    linux='/mnt/c/Users/wheel/Documents/Codex/2026-10-26/referenced-chatgpt-conversation-this-is-an/outputs/TREE2_WD_20261026/'
    if os.name=='nt'and text.startswith(linux):p=R/text[len(linux):]
    p=(p if p.is_absolute()else R/p).resolve()
    if not p.is_relative_to(R):raise RuntimeError('Feature-first path escapes project')
    return p
def sha(value):
    h=hashlib.sha256()
    with path(value).open('rb')as f:
        for b in iter(lambda:f.read(65536),b''):h.update(b)
    return h.hexdigest()
def read(value):return json.loads(path(value).read_text(encoding='utf-8-sig'))
def row(value):
    p=path(value);return {'path':p.relative_to(R).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size}
def bind(ref):
    p=path(ref['path'])
    if sha(p)!=ref['sha256']or p.stat().st_size!=ref['bytes']:raise RuntimeError('Feature-first artifact binding differs')
    return p
def closed0(unit):
    return unit.get('status')=='UNIT_EXIT0_GROUP_CLOSED'and type(unit.get('exit_code'))is int and unit['exit_code']==0 and unit.get('owned_group_empty')is True and unit.get('remaining_owned_processes')==[]

def prepare(spec,runtime,folder):
    if spec['repaired_request']['sha256']!=REQUEST_SHA:raise RuntimeError('Only the actual one-field repaired request is permitted')
    request=read(bind(spec['repaired_request']));prefix=path(runtime['prefix']);output=path(folder)/'feature_validation_repaired.json'
    if request.get('accession')!=ACC or path(request['runtime_prefix'])!=prefix:raise RuntimeError('Exact own FAA/canonical accepted Python prefix required')
    old=read(bind(spec['failed_validation_execution']))
    if type(old.get('exit_code'))is not int or old['exit_code']!=1 or old.get('owned_group_empty')is not True or old.get('elapsed_seconds')!=FAILED_VALIDATION_SECONDS:raise RuntimeError('Original validator1 and exact actual debit must survive')
    if spec.get('original_feature_allowance_seconds')!=120 or spec.get('remaining_feature_seconds')!=REMAINING_SECONDS:raise RuntimeError('No feature allowance reset')
    stock=read(bind(request['artifacts']['quality_unit_execution']))
    if not closed0(stock):raise RuntimeError('Saved genuine stock0 must precede this file-only repair')
    if output.exists():raise RuntimeError('Do not overwrite a validation result or repeat this unit')
    validator=bind(spec['validator'])
    if validator!=R/'scripts/checkm2_saved_stock_features_v001.py':raise RuntimeError('Unchanged saved-feature validator required')
    command=[str(prefix/'bin/python'),'-B',str(validator),'--request',str(bind(spec['repaired_request'])),'--request-sha256',REQUEST_SHA,'--output',str(output)]
    return request,output,command

def run_saved_features(spec,runtime,folder,invoke,environment,save):
    """invoke(name,argv,env,folder,seconds) must persist actual exit/group evidence."""
    request,output,command=prepare(spec,runtime,folder)
    env=environment(path(runtime['prefix']))
    for key in('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','TF_NUM_INTRAOP_THREADS','TF_NUM_INTEROP_THREADS'):env[key]='1'
    unitname='unit_saved_feature_repair'
    invoke(unitname,command,env,path(folder),REMAINING_SECONDS)
    execution=row(path(folder)/unitname/'execution.json');unit=read(bind(execution));elapsed=unit.get('elapsed_seconds')
    if not closed0(unit)or type(elapsed)not in(int,float)or not math.isfinite(elapsed)or not 0<=elapsed<=REMAINING_SECONDS:raise RuntimeError('Actual new validation0/debit/owned closure required')
    features=read(output)
    if features.get('status')!='P20_FEATURES_PASS_PENDING_NATIVE_CLOSURE'or features.get('accession')!=ACC or features.get('row_count')!=1 or features.get('finite_domain_features')!=21241 or features.get('exact_FAA_metadata_features')!=22 or features.get('independently_recomputed_membership_features')!=1220 or features.get('membership_mismatches')!=0:raise RuntimeError('Every own feature must pass before any shared cohort starts')
    if features.get('raw_pickle_sha256')!=request['artifacts']['raw_pickle']['sha256']or features.get('source_FAA_sha256')!=request['artifacts']['selected_faa']['sha256']or features.get('quality_unit_execution_sha256')!=request['artifacts']['quality_unit_execution']['sha256']:raise RuntimeError('The exact saved stock/FAA/pickle association changed')
    checkpoint={'schema':'TREE2_SAVED_FEATURE_FIRST_PENDING_CONTEXT_V001','status':'SAVED_FEATURE_REPAIR_VALIDATED_PENDING_CONTEXT_CLOSURE','accession':ACC,'repaired_request':spec['repaired_request'],'feature_validation':row(output),'new_validation_execution':execution,'saved_stock_execution':request['artifacts']['quality_unit_execution'],'saved_annotation_commit':request['artifacts']['annotation_commit'],'saved_diamond_commit':request['artifacts']['diamond_commit'],'failed_validation_execution':spec['failed_validation_execution'],'previous_feature_seconds':FAILED_VALIDATION_SECONDS,'new_actual_feature_seconds':elapsed,'cumulative_feature_seconds':FAILED_VALIDATION_SECONDS+elapsed,'original_feature_allowance_seconds':120,'annotation_DIAMOND_or_ML_runs':0,'method_result_acceptance':'PENDING_REAL_OUTER_CONTEXT_CLOSURE','source_taxonomy_or_panel_acceptance':False}
    save(path(folder)/'saved_feature_checkpoint.json',checkpoint)
    return checkpoint
