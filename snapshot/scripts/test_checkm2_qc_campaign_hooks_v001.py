"""Pure metadata/predicate fixtures; no runtime, real FAA/pickle or subprocess."""
from pathlib import Path
import ast,copy,json,sys
import checkm2_qc_campaign_data_v001 as c
import checkm2_conditional_shared_profile_hook_v001 as h
import checkm2_queue_saved_feature_first_v001 as f

def data_fixture():
 accepted=[{'accession':f'A{i}','paired_accessions':[]}for i in range(16)]
 registry={'rows':accepted,'additional_baseline':{'accession':'OUTSIDE'},'accepted_unique_method_accessions':[x['accession']for x in accepted]+['OUTSIDE']}
 ids=['A0','A1',c.SAVED]+[f'R{i}'for i in range(17)];rows=[]
 for i,acc in enumerate([*[f'A{i}'for i in range(16)],c.SAVED,*[f'R{i}'for i in range(17)],*[f'F{i}'for i in range(880)],*[f'H{i}'for i in range(5)]]):
  state=c.ACCEPTED if acc.startswith('A')else c.FRESH if acc.startswith('F')else c.REVIEW if acc.startswith('H')else'RESERVED_P20_UNSTARTED'
  rows.append({'accession':acc,'source_supported_scope':True,'source_holds_preserved':[],'source_pending_reasons':[],'source_masks':{'not_accepted':True},'qc_execution_state':state,'frozen_order':i,'paired_accessions':[],'FNA_from_receipt':{'sha256':'x'}})
 q={'schema':'TREE2_CANONICAL_QC_QUEUE_V001','rows':rows};p={'exact_original20_queue_ids':ids,'ordered_actions':[{}, {'queue_ids':[f'R{i}'for i in range(17)]}]}
 return q,registry,p
def run():
 tests=[];q,r,p=data_fixture();d=c.campaign_data(q,r,p)
 assert len(d['ordered_new_accessions'])==897 and len(d['cohorts'])==45 and len(d['cohorts'][0]['accessions'])==17 and all(len(x['accessions'])==20 for x in d['cohorts'][1:]);tests.append('17 then44 exact20 cohorts;919 reconciled with five review holds')
 bad=copy.deepcopy(q);bad['rows'][35]['source_holds_preserved']=['SOURCE_HOLD']
 try:c.campaign_data(bad,r,p)
 except RuntimeError:pass
 else:raise AssertionError('Source-held member silently selected')
 tests.append('source hold veto never becomes biological negative')
 bad=copy.deepcopy(p);bad['ordered_actions'][1]['queue_ids'].reverse()
 try:c.campaign_data(q,r,bad)
 except RuntimeError:pass
 else:raise AssertionError('Reserved order changed')
 tests.append('original17 order and no accepted or saved replay')
 # Reject an authority falsely claiming the old failed owner was successful.
 authority={'status':'ROOT_APPROVED_CONDITIONAL_SHARED_INDEX8_FROM_CLOSED_SERIAL_ROWS','supersedes_only_prior_whole_owner0_planning_prerequisite':True,'no_prior_whole_owner0_claim':True,'first_repaired_feature0_required':True,'first_own_complete_features_and_same8_fullraw_controls_before_remaining':True,'all_old_exits_and_debits_preserved':True,'no_accepted_annotation_or_ML_replay':True,'same_cohort_empirical_resource_fit_required':True,'fixed_author_filters_DB_models_and_feature_math':True,'source_and_unknown_masks_preserved':True,'default4_raw_and_model_input_equivalence':False,'source_taxonomy_or_panel_acceptance':False,'quality_thresholds':{'completeness_min':95,'contamination_max':5},'index_chunks':8,'block_size':.5,'threads':1,'closed_serial_row_authority':'serial'}
 serial={'status':'ROOT_ACCEPTED_CLOSED_DISTINCT_INDEX8_OWN_ROW_FOR_BULK','all_owner_context_and_lease_closure_verified':True,'own_feature_math_verified':True,'actual_context_native_exit_code':0,'actual_context_WSL_exit_code':1}
 values={'authority':authority,'serial':serial}
 try:h.conditional_baseline_gate({'conditional_shared_profile_authority':'authority'},read=lambda x:values[x],bind=lambda x:x,unit_closed=lambda x:True)
 except RuntimeError as e:assert '2/1'in str(e)
 else:raise AssertionError('Invented whole0 accepted')
 tests.append('conditional authority cannot relabel failed native2 as0')
 # Exercise the actual first-unit command producer with mocked JSON-only bindings.
 original_bind,original_read=f.bind,f.read
 try:
  root=Path(f.__file__).resolve().parents[1];prefix=root/'tools/checkm2_env';folder=root/'work/PURE_NOT_CREATED_feature_fixture'
  spec={'repaired_request':{'sha256':f.REQUEST_SHA},'failed_validation_execution':'failed','validator':'validator','original_feature_allowance_seconds':120,'remaining_feature_seconds':f.REMAINING_SECONDS}
  request={'accession':f.ACC,'runtime_prefix':str(prefix),'artifacts':{'quality_unit_execution':'stock'}}
  fixtures={'request':request,'failed':{'exit_code':1,'owned_group_empty':True,'elapsed_seconds':f.FAILED_VALIDATION_SECONDS},'stock':{'status':'UNIT_EXIT0_GROUP_CLOSED','exit_code':0,'owned_group_empty':True,'remaining_owned_processes':[]}}
  f.bind=lambda ref:'request'if isinstance(ref,dict)else root/'scripts/checkm2_saved_stock_features_v001.py'if ref=='validator'else ref
  f.read=lambda key:fixtures[key]
  req,out,argv=f.prepare(spec,{'prefix':str(prefix)},folder)
  assert req is request and argv[:2]==[str(prefix/'bin/python'),'-B']and argv[-2:] == ['--output',str(out)]and f.REQUEST_SHA in argv
 finally:f.bind,f.read=original_bind,original_read
 tests.append('actual saved-first producer has complete request/prefix/validator argv ABI')
 # Actual delegated cohort predicate, proving a parent grant does not admit another slice.
 authority={'status':'ROOT_ADMITTED_ONE_CONTINUOUS_QC_QUEUE_CONTEXT_V001','campaign_data':'data','ordered_new_accessions':d['ordered_new_accessions'],'historical_review_only':d['historical_review_only'],'source_manifest':'source','accepted_registry':'registry','conditional_shared_profile_authority':'conditional','saved_feature_repair':'repair'}
 for name in('saved_feature_repair_must_pass_first','all897_new_inputs_exact_ordered_and_once','same8_controls_and_first_own_features_before_remaining','all_completed_results_pending_real_outer_closure','no_per_cohort_fake_external_closure','all_prior_attempts_and_debits_preserved','no_accepted_annotation_search_or_ML_replay','source_taxonomy_unknown_masks_preserved'):authority[name]=True
 names=d['cohorts'][0]['accessions'];selected={'inputs':[{**d['source_rows'][acc],'canonical_queue_row':d['source_rows'][acc],'fasta_sha256':'x'}for acc in names]}
 plan={'campaign_data':'data','campaign_authority':'authority','source_manifest':'source','accepted_registry':'registry','conditional_shared_profile_authority':'conditional','saved_feature_repair':'repair','cohort_index':0,'accessions':names,'selected_inputs':'selected'};values={'data':d,'authority':authority,'selected':selected}
 assert c.campaign_cohort_gate(plan,read=lambda k:values[k],bind=lambda x:x)[2]==names
 try:c.campaign_cohort_gate({**plan,'accessions':names[::-1]},read=lambda k:values[k],bind=lambda x:x)
 except RuntimeError:pass
 else:raise AssertionError('Delegated slice order changed')
 tests.append('actual cohort gate binds parent scope and exact disjoint slice')
 assert f.REMAINING_SECONDS==113.89114030799828
 tree=ast.parse(Path(f.__file__).read_text());calls=[x for x in ast.walk(tree)if isinstance(x,ast.Call)and isinstance(x.func,ast.Name)and x.func.id=='invoke']
 assert len(calls)==1 and 'unit_saved_feature_repair'in Path(f.__file__).read_text();tests.append('one file-validator callback only; original120s debit retained')
 return {'status':'PURE_CAMPAIGN_HOOK_FIXTURES_PASS','groups':len(tests),'tests':tests,'no_runtime_tool_models_or_real_input':True}
if __name__=='__main__':print(json.dumps(run(),indent=2))
