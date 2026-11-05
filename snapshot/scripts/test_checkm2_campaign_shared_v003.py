"""Pure extracted-function/toy metadata tests; no target/scientific imports."""
import ast,hashlib,json,math,tempfile,types
from pathlib import Path
D=Path(__file__).resolve().parent

def extract(name,functions,env=None):
 tree=ast.parse((D/name).read_text(encoding='utf-8'));nodes=[x for x in tree.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef))and x.name in functions]
 scope={'__builtins__':__builtins__,**(env or{})};exec(compile(ast.Module(body=nodes,type_ignores=[]),name,'exec'),scope);return scope

def raises(call):
 try:call()
 except (RuntimeError,ValueError,FileExistsError):return
 raise AssertionError('Expected explicit hold')

passed=[]
merge=extract('checkm2_campaign_index8_shared_producer_v003.py',['merge_query_sequences'])['merge_query_sequences']
q={};merge(q,'GCF_111111111.1',{'gene1':'MA*'},'\u03a9');merge(q,'GCF_222222222.1',{'gene1':'MA*'},'\u03a9')
assert q=={'GCF_111111111.1\u03a9gene1':'MA*','GCF_222222222.1\u03a9gene1':'MA*'}
old=q.copy();raises(lambda:merge(q,'GCF_111111111.1',{'gene1':'DIFFERENT'},'\u03a9'));assert q==old
raises(lambda:merge(q,'GCF_333333333.1',{'bad\u03a9key':'MA*'},'\u03a9'));raises(lambda:merge(q,'GCF_333333333.1',{'bad key':'MA*'},'\u03a9'));passed.append('author_Omega_prefix_exact_duplicate_and_ambiguous_keys_rejected_before_overwrite')
# One real global search remains one debit even when every own row consumes a shard.
with tempfile.TemporaryDirectory(dir=D.parent/'work',prefix='shared_v3_toy_')as td:
 run=Path(td);data={};commands=[];terminal=[];alloc=[];names=['GCF_%09d.1'%i for i in range(1,21)]
 def add(scope,unit,seconds):
  folder=run/('shared'if scope=='shared'else'rows/'+scope)/unit;folder.mkdir(parents=True);command=folder/'command.json';end=folder/'execution.json';allocation=folder.parent/(unit+'_budget.json')
  for p in(command,end,allocation):p.write_text('{}')
  data[end]={'elapsed_seconds':seconds,'owned_group_empty':True,'remaining_owned_processes':[]}
 for name in names:
  for unit,seconds in [('unit_annotation',1),('unit_resume',2),('unit_feature_validation',3)]:add(name,unit,seconds)
 for unit,seconds in [('unit_shared_diamond',123),('unit_shared_search_validation',4),('unit_shared_control_comparison',5)]:add('shared',unit,seconds)
 plan=run/'dummy_plan.json';data[plan]={'accessions':names}
 env={'path':Path,'read':lambda p:data[p],'math':math,'PLAN_PATH':plan,'ROW_UNITS':{'unit_annotation':180,'unit_resume':600,'unit_feature_validation':3600},'SHARED_UNITS':{'unit_shared_diamond':10800,'unit_shared_search_validation':3600,'unit_shared_control_comparison':3600},'LIMITS':{'per_input_scientific_seconds':4380,'cohort_scientific_seconds':10000},'prior_debits':lambda p:1500.5498878960061}
 budget=extract('checkm2_campaign_index8_common_v003.py',['budget'],env)['budget'];value=budget(run)
 assert value['cohort_scientific_seconds_debited']==252 and value['shared_scientific_seconds']==132 and value['row_scientific_seconds']==120 and value['prior_plus_new_actual_scientific_seconds']==1752.5498878960061
 passed.append('shared_search_validation_controls_charged_once_for_20_rows_prior_debits_retained')
 end=run/'shared/unit_shared_diamond/execution.json';end.unlink();raises(lambda:budget(run));end.write_text('{}');passed.append('missing_global_terminal_is_unknown_and_blocks_no_budget_reset')
 add(names[0],'unit_diamond',10);raises(lambda:budget(run));passed.append('synthetic_per_row_DIAMOND_exit_or_debit_rejected')
# Execute the actual extracted sequencing function with toy jobs and durable checkpoints.
with tempfile.TemporaryDirectory(dir=D.parent/'work',prefix='shared_v3_sequence_')as td:
 run=Path(td);(run/'rows').mkdir();events=[];saves={};items=[{'accession':'A'},{'accession':'B'},{'accession':'C'}]
 def save(p,v):saves[p.name]=v;events.append(('save',p.name))
 def annotate(p,r,rt,folder,item):events.append(('ann',item['accession']));return{'accession':item['accession']}
 def shared(*args):events.append(('shared',));assert len([x for x in events if x[0]=='ann'])==3;return{'sha256':'shared'}
 def predict(p,r,rt,folder,item,ann,glob,qualification=None):events.append(('model',item['accession']));return{'accession':item['accession']}
 def controls(*args):
  events.append(('controls',));assert 'first_row_checkpoint_before_controls.json'in saves;raise RuntimeError('Deliberate raw multiset mismatch')
 c=types.SimpleNamespace(save=save,budget=lambda r:{},shared_qualification_gate=lambda *a:None)
 env={'c':c,'annotate_one':annotate,'shared_search':shared,'predict_one':predict,'finish_controls':controls,'stop':lambda:None,'progress':lambda *a:None}
 execute=extract('checkm2_campaign_index8_inner_v003.py',['execute_phases'],env)['execute_phases'];state={'annotations':[],'results':[],'shared_reference':None,'qualification':None}
 raises(lambda:execute({'controls':[]},{'inputs':items},{},run,state));assert [x for x in events if x[0]=='model']==[('model','A')]and state['results']==[{'accession':'A'}]and len(state['annotations'])==3
 passed.append('all_annotations_first_actual_first_row_checkpoint_precedes_control_failure_remaining_ML_never_called')
# Scientific numeric body and fixed DIAMOND filtering stay exactly the accepted serial body.
def fn_ast(name,fn):return ast.dump(next(x for x in ast.parse((D/name).read_text()).body if isinstance(x,ast.FunctionDef)and x.name==fn),include_attributes=False)
assert fn_ast('checkm2_campaign_index8_shared_producer_v003.py','build_argv')==fn_ast('checkm2_campaign_index8_diamond_producer_v002.py','build_argv');passed.append('fixed_index8_scientific_argv_AST_identical_to_frozen_serial_V2')
assert fn_ast('checkm2_campaign_index8_feature_validator_v003.py','main')==fn_ast('checkm2_campaign_index8_feature_validator_v002.py','main');passed.append('all_numeric_main_AST_identical_to_frozen_21241_22_1220_body')
old=(D/'checkm2_campaign_index8_observer_v002.py').read_bytes();new=(D/'checkm2_campaign_index8_observer_v003.py').read_bytes()
assert new==old.replace(b'<=3600',b'<=10800').replace(b'within3600s',b'within10800s');passed.append('observer_only_declared_time_ceiling_changed_all_resource_identity_cleanup_bytes_unchanged')
# File-only finalization cannot grant its own future native exit, registry or queue acceptance.
text=(D/'checkm2_campaign_index8_close_v003.py').read_text();assert "type(proof.get('actual_native_exit_code'))is not int"in text and "'queue_ledger_or_registry_updated':False"in text;passed.append('separate_external_actual_native0_required_no_self_exit_or_panel_acceptance')
# Review regression: integer nonzero owner exits cannot become a closed-success baseline.
authority={'status':'ROOT_ACCEPTED_CLOSED_INDEX8_METHOD_FOR_BULK','actual_native_exit_code':0,'actual_WSL_exit_code':0,'all_owner_context_and_lease_closure_verified':True,'own_feature_math_verified':True,'index_chunks':8,'closure_and_result_evidence':['e']}
base=extract('checkm2_campaign_index8_common_v003.py',['baseline_gate'],{'read':lambda p:authority,'bind':lambda p:p,'bound_evidence':lambda x:None})['baseline_gate']
base({'serial_index8_baseline_acceptance':'b'});authority['actual_native_exit_code']=2;raises(lambda:base({'serial_index8_baseline_acceptance':'b'}));authority['actual_native_exit_code']=0;authority['actual_WSL_exit_code']=1;raises(lambda:base({'serial_index8_baseline_acceptance':'b'}));passed.append('typed_nonzero_native_or_WSL_exit_is_not_closed_serial_baseline_success')
# Review regression: a self-consistent different search cannot impersonate the accepted donor.
acc='GCF_111111111.1';spec={'accession':acc,'role':'SEARCH_ONLY_CONTROL','accepted_method_authority':'authority','serial_search_commit':'serial','annotation_commit':'ann','selected_faa':'faa','annotation_receipt':'annreceipt','annotation_unit_execution':'annunit','reference_raw_diamond':'raw','paired_accessions':[]}
values={'accepted':{'accession':acc,'diamond_commit':'serial','annotation_commit':'ann'},'ann':{'accession':acc,'selected_faa':'faa','annotation_receipt':'annreceipt','unit_execution':'annunit'},'serial':{'accession':acc,'selected_faa':'faa','raw_diamond':'raw','diamond_receipt':'dia','unit_execution':'binary','validation_unit_execution':'validated'},'dia':{'index_chunks':8,'block_size':.5,'threads':1,'database':'DB'},'annunit':{},'binary':{},'validated':{}}
gate=extract('checkm2_campaign_index8_common_v003.py',['controls_gate'],{'bind':lambda x:x,'read':lambda p:values[p],'unit_closed':lambda u:True})['controls_gate'];plan={'controls':[spec],'accessions':['GCF_222222222.1'],'runtime_binding':{'database':'DB'}};registry={'rows':[{'accession':acc,'authority':'authority','commit':'accepted'}],'additional_baseline':{'accession':'OTHER'}}
assert gate(plan,registry)==[acc];values['accepted']['diamond_commit']='different_but_self_consistent_search';raises(lambda:gate(plan,registry));values['accepted']['diamond_commit']='serial';values['accepted']['annotation_commit']='different_annotation';raises(lambda:gate(plan,registry));passed.append('control_search_and_annotation_must_join_actual_accepted_registry_row_not_just_self_consistent_FAA')
print(json.dumps({'status':'PURE_SOURCE_TOY_FIXTURES_PASS','groups':passed,'count':len(passed),'real_genome_runtime_model_or_OS_probe_used':False},indent=2))
