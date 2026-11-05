"""Tiny authority fixtures only; no model/runtime/input files."""
import importlib.util,copy,unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('pure_policy',Path(__file__).with_name('checkm2_distinct_index8_profile_policy_v001.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Policy(unittest.TestCase):
 def setUp(self):
  self.q={'status':'ROOT_ACCEPTED_CLOSED_DISTINCT_INDEX8_OWN_ROW_FOR_BULK','scope':'METHOD_PROFILE_AND_MEASUREMENT_REUSE_ONLY','index_chunks':8,'block_size':.5,'threads':1,'actual_context_native_exit_code':2,'actual_context_WSL_exit_code':1,'actual_context_native_exit_receipt':'native','external_closed_context':'closed','reference_difference_evidence':'diff','closure_and_result_evidence':['proof'],'commit':'commit','feature_validation':'feature','accession':'A'}
  for k in('empirical_qualification_accepted','own_feature_math_verified','resource_gates_unchanged','all_owner_context_and_lease_closure_verified','failed_reference_gate_preserved','old_default4_estimates_preserved_with_parameter_tags','quality_thresholds_unchanged','independent_panel_QC_required','borderline_and_conflicting_evidence_held','all_prior_attempts_claims_and_actual_debits_preserved'):self.q[k]=True
  for k in('raw_output_equivalence_to_default4','full_model_input_equivalence_to_default4','old_estimates_overwritten','accepted_annotation_or_prediction_replayed','source_taxonomy_or_final_panel_acceptance'):self.q[k]=False
  self.data={'q':self.q,'native':{'native_exit_code_observed':2},'closed':{'all_owner_context_and_lease_closure_verified':True,'actual_native_exit_code':2,'actual_WSL_exit_code':1},'diff':{'raw_output_equivalent':False,'full_model_input_equivalent':False,'known_KO_input_differences':['K1']},'feature':{'accession':'A','finite_domain_features':21241,'exact_FAA_metadata_features':22,'independently_recomputed_membership_features':1220},'commit':{'accession':'A','feature_validation':'feature','unit_executions':{k:'unit'for k in('unit_annotation','unit_diamond','unit_saved_search_validation','unit_resume','unit_feature_validation')}},'unit':{'exit_code':0}}
 def gate(self):return m.qualification_gate('q',read=lambda r:self.data[r],bind=lambda r:r,unit_closed=lambda u:u['exit_code']==0,bound_evidence=lambda x:None)
 def test_failed_context_preserved_successful_own_row_is_separate(self):self.assertIs(self.gate(),self.q);self.assertEqual(self.q['actual_context_native_exit_code'],2)
 def test_equivalence_or_threshold_weakening_rejected(self):
  self.q['full_model_input_equivalence_to_default4']=True
  with self.assertRaises(RuntimeError):self.gate()
  self.q['full_model_input_equivalence_to_default4']=False;self.q['quality_thresholds_unchanged']=False
  with self.assertRaises(RuntimeError):self.gate()
 def test_failed_or_missing_own_phase_rejected(self):
  self.data['unit']['exit_code']=-15
  with self.assertRaises(RuntimeError):self.gate()
 def test_context_relabelled_native_zero_rejected(self):
  self.q['actual_context_native_exit_code']=0
  with self.assertRaises(RuntimeError):self.gate()
if __name__=='__main__':unittest.main()
