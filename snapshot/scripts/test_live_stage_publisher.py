"""Narrow fixtures for terminal QC/setup display, without touching live state."""
from pathlib import Path
import importlib.util,unittest
from unittest.mock import patch
source=Path(__file__).with_name('live_stage_publisher.py')
spec=importlib.util.spec_from_file_location('publisher_fixture',source)
publisher=importlib.util.module_from_spec(spec);spec.loader.exec_module(publisher)

class StageStatusFixtures(unittest.TestCase):
 def build(self,status,source='state/tool_setup_progress.json',extra=None):
  records={source:{'status':status,'detail':'fixture terminal reason','log_path':'/mnt/c/fixture/failure.log','pid':123,'done':2,'total':6},**(extra or {})}
  with patch.object(publisher,'read',side_effect=lambda name,default=None:records.get(name,default)):
   return publisher.build()['stages'][4]
 def test_setup_terminal_failures_are_attention(self):
  for status in ('FAILED','ERROR','RESOURCE_LIMIT','TIMEOUT'):
   with self.subTest(status=status):
    row=self.build(status);self.assertEqual(row['status'],'ATTENTION')
    self.assertEqual(row['attention_sources'][0]['source'],'tool_setup')
    self.assertIn('fixture terminal reason',row['detail']);self.assertEqual(row['log_path'],'C:\\fixture\\failure.log')
    self.assertFalse(row['requires_user_input']);self.assertEqual(row['done'],2)
 def test_real_extended_pilot_failures_are_attention(self):
  for status in ('FAILED_PRECHECK','FAILED_RUNTIME_OR_FIT','FAILED_RUNTIME_NAMESPACE_CLOSURE','BLOCKED_RESOURCE','INTERRUPTED_BUDGET','HELD_PREVIOUS_ATTEMPT'):
   with self.subTest(status=status):self.assertEqual(self.build(status,'state/checkm2_pilot_progress.json')['status'],'ATTENTION')
 def test_database_failure_is_not_pending(self):
  self.assertEqual(self.build('ERROR','state/completeness_db_progress.json')['status'],'ATTENTION')
 def test_running_setup_stays_running(self):
  self.assertEqual(self.build('RUNNING')['status'],'RUNNING')
 def test_recovery_planning_does_not_claim_os_worker(self):
  for status in ('AUTO_REPAIR_PENDING','RECOVERY_PLANNING','RECOVERY_PREPARED','COMPLETE'):
   with self.subTest(status=status):self.assertEqual(self.build(status)['status'],'AUTO_SETUP_PENDING')
 def test_explicit_stop_is_distinct_from_failure_and_pending(self):
  self.assertEqual(self.build('STOPPED')['status'],'STOPPED')
 def test_failure_is_not_masked_by_other_running_substep(self):
  row=self.build('FAILED',extra={'state/sequence_qc_progress.json':{'status':'RUNNING'}})
  self.assertEqual(row['status'],'ATTENTION');self.assertEqual(len(row['attention_sources']),1)
 def protein_records(self,admitted=True,protein_status='RUNNING'):
  records={'state/checkm2_pilot_progress.json':{'status':'BLOCKED_RESOURCE','detail':'old FNA RSS stop','pid':111},
           'state/checkm2_protein_pilot_v001_progress.json':{'status':protein_status,'detail':'protein unit active','done':0,'total':1,'unit':'protein genomes'},
           'state/launch_checkm2_protein_pilot_v001.json':{'pid':222,'creation_time_utc':'2026-10-27T00:01:00Z'}}
  if admitted:records['state/checkm2_protein_strategy_ready_v001.json']={'schema':'TREE2_SUPPORTED_PROTEIN_STRATEGY_V1','status':'ROOT_ACCEPTED_FOR_ONE_RESOURCE_PILOT','biological_dispatch_authorized':True}
  return records
 def build_records(self,records):
  with patch.object(publisher,'read',side_effect=lambda name,default=None:records.get(name,default)):
   return publisher.build()['stages'][4]
 def test_admitted_protein_running_retires_only_old_resource_failure(self):
  row=self.build_records(self.protein_records())
  self.assertEqual(row['status'],'RUNNING');self.assertEqual(row['pid'],222)
  self.assertEqual((row['done'],row['total'],row['unit']),(0,1,'protein genomes'))
  self.assertEqual(row['attention_sources'],[])
  self.assertEqual(row['historical_attention_sources'][0]['source'],'checkm2_pilot')
  self.assertTrue(row['historical_attention_sources'][0]['historical'])
  self.assertEqual(row['substeps']['checkm2_pilot']['status'],'BLOCKED_RESOURCE')
  self.assertEqual(row['substeps']['checkm2_protein_pilot_v001']['status'],'RUNNING')
  self.assertIn('Historical: old FNA RSS stop',row['detail'])
 def test_current_protein_failure_remains_attention(self):
  row=self.build_records(self.protein_records(protein_status='FAILED_RUNTIME_OR_SCHEMA'))
  self.assertEqual(row['status'],'ATTENTION');self.assertEqual(row['pid'],222)
  self.assertEqual([x['source'] for x in row['attention_sources']],['checkm2_protein_pilot_v001'])
 def test_without_admission_old_resource_failure_remains_current(self):
  for admission in (None,{'schema':'TREE2_SUPPORTED_PROTEIN_STRATEGY_V1','status':'ROOT_ACCEPTED_FOR_ONE_RESOURCE_PILOT','biological_dispatch_authorized':False}):
   records=self.protein_records(admitted=False)
   if admission:records['state/checkm2_protein_strategy_ready_v001.json']=admission
   with self.subTest(admission=admission):
    row=self.build_records(records);self.assertEqual(row['status'],'ATTENTION')
    self.assertEqual([x['source'] for x in row['attention_sources']],['checkm2_pilot'])
    self.assertEqual(row['historical_attention_sources'],[])
 def test_current_setup_benchmark_and_other_fna_failures_not_retired(self):
  for path,status in (('state/tool_setup_progress.json','FAILED'),('state/checkm2_benchmark_progress.json','BLOCKED_RESOURCE'),('state/checkm2_pilot_progress.json','FAILED_RUNTIME_NAMESPACE_CLOSURE')):
   records=self.protein_records();records[path]={'status':status,'detail':'current failure'}
   with self.subTest(path=path):
    row=self.build_records(records);self.assertEqual(row['status'],'ATTENTION')
    self.assertEqual(len(row['attention_sources']),1)
    self.assertEqual(row['attention_sources'][0]['status'],status)
 def test_posthoc_uses_actual_native_owner_instead_of_retired_protein_launch(self):
  records=self.protein_records()
  posthoc={'status':'RUNNING','detail':'Saved-output validation only; no prediction rerun','done':0,'total':1,'unit':'saved-output feature validations','pid':333,'creation_time_utc':'2026-10-27T00:31:00Z','scope':'FILE_ONLY_POSTHOC_V002_NO_PREDICTION_RERUN','log_path':'/mnt/c/fixture/posthoc.log'}
  records['state/checkm2_protein_pilot_v001_progress.json']=dict(posthoc)
  records['state/checkm2_posthoc_v002_progress.json']=posthoc
  records['state/launch_checkm2_posthoc_v002.json']={'native_owner':{'pid':333,'creation_time_utc':'2026-10-27T00:31:00Z'},'wsl_child':{'pid':444,'creation_time_utc':'2026-10-27T00:31:01Z'},'script':'C:\\fixture\\checkm2_posthoc_v002_controller.py','scope':'FILE_ONLY_NO_PREDICTION_RERUN'}
  row=self.build_records(records)
  self.assertEqual(row['pid'],333);self.assertNotIn(row['pid'],(222,444))
  self.assertEqual(row['creation_time_utc'],'2026-10-27T00:31:00Z')
  self.assertEqual((row['done'],row['total'],row['unit']),(0,1,'saved-output feature validations'))
  self.assertEqual(row['log_path'],'C:\\fixture\\posthoc.log')
  self.assertIn('Saved-output validation only',row['detail']);self.assertFalse(row['requires_user_input'])

if __name__=='__main__':unittest.main()
