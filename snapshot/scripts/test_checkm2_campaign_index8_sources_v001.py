"""Pure source/guard fixtures: no target imports, biology, processes or real inputs."""
import ast,math,unittest
from pathlib import Path
D=Path(__file__).resolve().parent

def tree(name):return ast.parse((D/name).read_text())
def function(name,target):return next(x for x in tree(name).body if isinstance(x,ast.FunctionDef)and x.name==target)
def same(a,b,target):return ast.dump(function(a,target),include_attributes=False)==ast.dump(function(b,target),include_attributes=False)
class Checks(unittest.TestCase):
 def test_scientific_bodies_unchanged(self):
  for old,new in [('checkm2_P20_continue19_annotation_v001.py','checkm2_campaign_index8_annotation_v001.py'),('checkm2_P20_diamond_exec_producer_v002.py','checkm2_campaign_index8_diamond_producer_v001.py'),('checkm2_P20_diamond_exec_validate_v002.py','checkm2_campaign_index8_diamond_validate_v001.py'),('checkm2_P20_resource_repair_feature_validator_v002.py','checkm2_campaign_index8_feature_validator_v001.py')]:self.assertTrue(same(old,new,'main'),new)
  self.assertTrue(same('checkm2_P20_diamond_exec_producer_v002.py','checkm2_campaign_index8_diamond_producer_v001.py','build_argv'))
 def test_no_hidden_old_phase_gate(self):
  for p in D.glob('checkm2_campaign_index8_*.py'):
   if p.name.endswith(('common_v001.py','observer_v001.py','inner_v001.py','entry_v001.py','native_v001.py')):continue
   imports=[x.module for x in ast.walk(ast.parse(p.read_text()))if isinstance(x,ast.ImportFrom)]+[v.name for x in ast.walk(ast.parse(p.read_text()))if isinstance(x,ast.Import)for v in x.names]
   self.assertFalse(any('continue19_common'in str(x)or'resource_repair_common'in str(x)for x in imports),p.name)
 def test_observer_only_time_admission_changed(self):
  old=(D/'checkm2_unit_observer_S1R2.py').read_text();new=(D/'checkm2_campaign_index8_observer_v001.py').read_text()
  self.assertEqual(new,old.replace('0<timeout<=600','0<timeout<=900').replace('within600s required','within900s required'))
  guard=function('checkm2_campaign_index8_observer_v001.py','run_unit').body[0]
  code=compile(ast.fix_missing_locations(ast.Module(body=[guard],type_ignores=[])),'bound-only','exec')
  for value,accepted in [(900,True),(900.001,False),(0,False),(float('nan'),False)]:
   try:exec(code,{'timeout':value});actual=True
   except ValueError:actual=False
   self.assertEqual(actual,accepted)
 def test_fresh_limits_and_inner_consistent(self):
  common=(D/'checkm2_campaign_index8_common_v001.py').read_text();inner=(D/'checkm2_campaign_index8_inner_v001.py').read_text()
  self.assertIn("'unit_diamond':900",common);self.assertIn("'unit_feature_validation':120",common)
  self.assertIn('0<=done<=c.COUNT',inner);self.assertIn('seconds<=c.UNITS[name]',inner)
  for stale in('1410-used','<=600',"'cohort_scientific_seconds':26790"):self.assertNotIn(stale,inner)
 def test_factory_publication_is_not_dispatch(self):
  source=(D/'prepare_checkm2_campaign_index8_cohort_v001.py').read_text()
  self.assertIn('os.link(temporary,p)',source);self.assertIn('re.fullmatch',source)
  self.assertNotIn('subprocess',source);self.assertNotIn('Popen',source)
 def test_old_successful_rows_excluded_and_masks_exact(self):
  source=(D/'checkm2_campaign_index8_common_v001.py').read_text()
  self.assertIn("qualification.get('accession') not in accepted",source)
  self.assertIn("item.get('canonical_queue_row')!=q",source)
  self.assertIn("or(not closed_finalization and claim['native_launch_token']!=token)",source)

 def test_known_timeout_elapsed_is_charged_not_unknown(self):
  from pathlib import PurePosixPath as P
  from types import SimpleNamespace
  cmd=P('/rows/GCF_002993975.1/unit_diamond/command.json');terminal=cmd.with_name('execution.json');allocation=cmd.parent.parent/'unit_diamond_budget.json'
  class Run:
   def glob(self,pattern):return {'rows/*/unit_*/command.json':[cmd],'rows/*/unit_*/execution.json':[terminal],'rows/*/unit_*_budget.json':[allocation]}.get(pattern,[])
  values={'plan':{'accessions':['GCF_002993975.1']},terminal:{'elapsed_seconds':900.25,'exit_code':-15,'owned_group_empty':True,'remaining_owned_processes':[]}}
  ns={'path':lambda x:x,'read':lambda p:values[p],'PLAN_PATH':'plan','UNITS':{'unit_diamond':900},'LIMITS':{'cohort_scientific_seconds':1800},'prior_debits':lambda p:600.238615762,'math':math}
  exec(compile(ast.fix_missing_locations(ast.Module(body=[function('checkm2_campaign_index8_common_v001.py','budget')],type_ignores=[])),'actual-debit-only','exec'),ns)
  result=ns['budget'](Run())
  self.assertTrue(result['known_limit_exceeded']);self.assertEqual(result['cohort_scientific_seconds_debited'],900.25)
  self.assertAlmostEqual(result['prior_plus_new_actual_scientific_seconds'],1500.488615762)
 def test_conditional_first_gate_and_original_reuse(self):
  source=(D/'checkm2_campaign_index8_common_v001.py').read_text();inner=(D/'checkm2_campaign_index8_inner_v001.py').read_text()
  self.assertIn("len(failures)!=3",source);self.assertIn("new_search_allowance_is_additional_not_reset",source)
  self.assertIn("actuals.append(n)",source);self.assertIn("if acc in plan['annotation_reuse_by_accession']",inner)
  self.assertIn("input_index==0",inner);self.assertIn("conditional_profile_promotion.json",inner)
  self.assertIn("first_complete_feature_checked_row_before_remaining_inputs",source)
if __name__=='__main__':unittest.main()

