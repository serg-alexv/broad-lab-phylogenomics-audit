"""Pure S1R2 source fixtures. Popen/kill/sleep mocked; no real child/runtime/data."""
from pathlib import Path
import copy,json,tempfile,unittest
from unittest.mock import patch
import checkm2_unit_observer_S1R2 as o
import checkm2_single_faa_common_S1R2 as c
import checkm2_single_faa_close_S1R2 as close

class FakeChild:
 pid=12345
 def __init__(self):self.returncode=None;self.polls=0
 def poll(self):
  self.polls+=1
  if self.polls>=2:self.returncode=0
  return self.returncode
 def wait(self,timeout=None):self.returncode=0;return 0

class SourceOnlyFixtures(unittest.TestCase):
 def setUp(self):
  root=c.R/'work/checkm2_S1R2_pure_fixtures';root.mkdir(parents=True,exist_ok=True)
  self.temp=tempfile.TemporaryDirectory(prefix='synthetic_',dir=root);self.folder=Path(self.temp.name)
  assert self.folder.resolve().is_relative_to(root.resolve())
 def tearDown(self):self.temp.cleanup()
 def save(self,p,value):
  p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value),encoding='utf-8')
 def execute(self,progress=lambda *a,**k:None,strict_error=None,terminal_error=False,initial_identity_missing=False):
  child=FakeChild();errors=[]
  def save(p,value):
   if terminal_error and Path(p).name=='execution.json':raise PermissionError(13,'fixture required terminal','/required/execution.json')
   self.save(p,value)
  def headroom():
   if strict_error:raise strict_error
   return 3*1024**3
  identity={'pid':child.pid,'parent_pid':999,'process_group':child.pid,'creation_ticks':7,'boot_id':'synthetic-boot','rss_bytes':1024}
  def stat(pid):
   if initial_identity_missing:child.returncode=0;raise FileNotFoundError('/proc synthetic initial identity')
   if child.returncode is not None:raise FileNotFoundError('/proc synthetic exited identity')
   return dict(identity)
  hooks={'save':save,'stop_gate':lambda:None,'stat':stat,'group':lambda p:([dict(identity)] if child.returncode is None else []),'mem_available':headroom,'progress':progress,'optional_error_sink':errors.append}
  with patch.object(o.subprocess,'Popen',return_value=child) as start,patch.object(o.time,'sleep'),patch.object(o.os,'killpg',create=True) as kill,patch.object(o.signal,'SIGKILL',9,create=True),patch.object(o.guard,'track_descendants',side_effect=lambda root,known:([dict(identity)] if child.returncode is None else [])),patch.object(o.guard,'current_matching',side_effect=lambda row:(dict(identity) if child.returncode is None else None)),patch.object(o.guard,'identity',side_effect=stat):
   try:receipt=o.run_unit('unit_quality',['synthetic-never-executed'],{},self.folder,5,hooks=hooks)
   except o.UnitFailure as error:receipt=error.receipt
   self.assertTrue(start.called);self.assertFalse(kill.called)
  return receipt,errors
 def test_optional_permission_keeps_real_unit_result(self):
  def display(*a,**k):raise PermissionError(13,'fixture optional STEP','/optional/STEP.json')
  receipt,errors=self.execute(display)
  self.assertEqual(receipt['status'],'UNIT_EXIT0_GROUP_CLOSED');self.assertTrue(receipt['durable_terminal_receipt']);self.assertEqual(receipt['optional_progress_error_count'],1);self.assertEqual(errors[0]['filename'],'/optional/STEP.json')
 def test_missing_initial_identity_cannot_be_scientific_success(self):
  receipt,_=self.execute(initial_identity_missing=True)
  self.assertEqual(receipt['status'],'UNIT_FAILED_OR_CLOSURE_UNPROVEN');self.assertIsNone(receipt['child_identity']);self.assertFalse(receipt['owned_group_empty']);self.assertEqual(receipt['error_details']['last_operation'],'required_child_identity')
 def test_required_observer_permission_is_original_failure(self):
  receipt,_=self.execute(strict_error=PermissionError(13,'fixture required observer','/proc/meminfo'))
  self.assertEqual(receipt['status'],'UNIT_FAILED_OR_CLOSURE_UNPROVEN');self.assertEqual(receipt['error_details']['filename'],'/proc/meminfo');self.assertEqual(receipt['error_details']['last_operation'],'required_linux_headroom');self.assertIn('PermissionError',receipt['error_details']['traceback']);self.assertTrue(receipt['owned_group_empty'])
 def test_non_io_progress_bug_remains_fatal(self):
  def display(*a,**k):raise ValueError('fixture programming error')
  receipt,_=self.execute(display);self.assertEqual(receipt['status'],'UNIT_FAILED_OR_CLOSURE_UNPROVEN');self.assertEqual(receipt['error_details']['type'],'ValueError')
 def test_required_terminal_failure_never_returns_success(self):
  receipt,_=self.execute(terminal_error=True);self.assertFalse(receipt['durable_terminal_receipt']);self.assertEqual(receipt['status'],'UNIT_FAILED_OR_CLOSURE_UNPROVEN');self.assertEqual(receipt['terminal_write_error']['filename'],'/required/execution.json')
 def make_unit(self,elapsed,acc=None,terminal=True):
  acc=acc or c.SECOND;folder=self.folder/'rows'/acc/'unit_quality';folder.mkdir(parents=True)
  self.save(folder/'command.json',{});self.save(folder.parent/'unit_quality_budget.json',{})
  if terminal:self.save(folder/'execution.json',{'elapsed_seconds':elapsed,'owned_group_empty':True,'remaining_owned_processes':[]})
  return folder
 def test_failed_second_new_cap_and_global_debit_are_carried(self):
  self.make_unit(599.056561);value=c.budget(self.folder)
  self.assertEqual(value['prior_T1_failed_quality_seconds'],104.24163487500482);self.assertEqual(value['prior_S1_actual_unit_seconds_debited'],284.5531904320087);self.assertEqual(value['new_seconds_debited'],599.056561);self.assertAlmostEqual(value['remaining_seconds'],3211.205174-599.056561)
 def test_second_cap_excess_fails(self):
  self.make_unit(599.056562)
  with self.assertRaises(RuntimeError):c.budget(self.folder)
 def test_unknown_terminal_debit_never_resets(self):
  self.make_unit(None,terminal=False)
  with self.assertRaises(RuntimeError):c.budget(self.folder)
 def test_preserved_accession_cannot_be_current_unit(self):
  self.make_unit(1,acc=c.PRESERVED)
  with self.assertRaises(RuntimeError):c.budget(self.folder)
 def composed(self):
  old={'accession':c.PRESERVED,'origin':'PRESERVED_ROOT_ACCEPTED_ORIGINAL_S1_ROW'};fresh=[{'accession':x,'origin':'FRESH_CURRENT_S1R2_ROW'} for x in c.TARGETS]
  return old,{'rows':[old,*fresh],'preserved_rows':[old],'fresh_rows':fresh,'completed_qc_rows':10,'preserved_count':1,'fresh_count':9}
 def test_compound_preserves_original_descriptor(self):
  old,result=self.composed();rows,fresh=close.compound_rows(result,old,c.TARGETS,{c.PRESERVED,*c.TARGETS});self.assertIs(rows[0],old);self.assertEqual(len(fresh),9)
 def test_preserved_row_cannot_be_faked_as_new(self):
  old,result=self.composed();result['fresh_rows'][0]=copy.deepcopy(old);result['rows']=[old,*result['fresh_rows']]
  with self.assertRaises(RuntimeError):close.compound_rows(result,old,c.TARGETS,{c.PRESERVED,*c.TARGETS})
 def test_missing_new_row_cannot_be_counter_only_success(self):
  old,result=self.composed();result['fresh_rows'].pop();result['rows']=[old,*result['fresh_rows']]
  with self.assertRaises(RuntimeError):close.compound_rows(result,old,c.TARGETS,{c.PRESERVED,*c.TARGETS})
 def test_failure_locator_works_without_optional_step(self):
  owned=self.folder/'owned';run=owned/'runs'/'new-run';run.mkdir(parents=True);token='synthetic-token';plan='p';protocol='a'
  self.save(run/'binding.json',{'launch':{'token':token,'input_plan_sha256':plan,'protocol_admission_sha256':protocol},'admission':{'sha256':protocol},'plan':{'_sha':plan,'session_identity_sha256':'s'}});self.save(run/'failure.json',{'status':'S1R2_FAILED_NO_AUTOMATIC_RETRY_OR_FALLBACK','annotation_invoked':False});self.save(run/'invocations.json',[])
  self.save(owned/'runs_by_token'/(token+'.json'),{'launch_token':token,'input_plan_sha256':plan,'protocol_admission_sha256':protocol,'run_directory':str(run),'binding':c.row(run/'binding.json')})
  with patch.object(c,'OUT',owned):self.assertEqual(c.current_failed_run(None,token,plan,protocol),run.resolve())

if __name__=='__main__':unittest.main(verbosity=2)
