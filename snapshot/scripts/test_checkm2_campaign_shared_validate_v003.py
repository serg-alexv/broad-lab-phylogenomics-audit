"""Pure functions and tiny synthetic files; no target/common/ML/runtime imports."""
from pathlib import Path
import ast,hashlib,json,math,tempfile,unittest
import checkm2_batched_search_splitter_v002 as splitter
R=Path(__file__).resolve().parents[1]
SOURCE=R/'scripts/checkm2_campaign_index8_shared_validate_v003.py'
TREE=ast.parse(SOURCE.read_text(encoding='utf-8'))
NAMES=('require_binary_execution','expected_query_inventory','require_query_inventory','scan_merged_raw')
NS={'Path':Path,'hashlib':hashlib,'math':math,'splitter':splitter}
exec(compile(ast.Module(body=[x for x in TREE.body if isinstance(x,ast.FunctionDef)and x.name in NAMES],type_ignores=[]),'<actual shared validator pure functions>','exec'),NS)
A='GCF_000000001.1';B='GCA_000000002.2';Q=A+'\u03a9gene1';QB=B+'\u03a9gene1'

def unit():
 return {'status':'UNIT_EXIT0_GROUP_CLOSED','declared_unit':'unit_shared_diamond','exit_code':0,'owned_group_empty':True,'remaining_owned_processes':[],'elapsed_seconds':3.25,'child_identity':{'pid':17,'creation_ticks':100,'boot_id':'toy-boot'}}
def prepared():return {'producer_pid_before_exec':17,'producer_creation_identity':{'pid':17,'creation_ticks':100,'boot_id':'toy-boot'}}
def inputs():return [{'accession':A,'role':'FRESH'},{'accession':B,'role':'SEARCH_ONLY_CONTROL'}]
def proteins():return {A:[{'id':'gene1','sequence':'MAAAAAAAAK'}],B:[{'id':'gene1','sequence':'MCCCCCCCCK'}]}
def hit(q=Q,target='UniRef100_A~K00001',evalue='1.00e-20'):
 return '\t'.join((q,target,'90.00','10','1','0','1','10','3','12',evalue,'45.500'))+'\n'

class SharedValidation(unittest.TestCase):
 def setUp(self):
  self.parent=(R/'work/shared_raw_validator_toy_v003').resolve();self.parent.mkdir(exist_ok=True)
  self.temp=tempfile.TemporaryDirectory(dir=self.parent);self.root=Path(self.temp.name).resolve()
  assert self.root.is_relative_to(self.parent)and self.root!=self.parent
 def tearDown(self):
  assert self.root.is_relative_to(self.parent)and self.root!=self.parent and not self.root.is_symlink()
  self.temp.cleanup()
 def write(self,name,text):
  p=self.root/name;p.write_text(text,encoding='utf-8',newline='\n');return splitter._file_ref(self.root,p)
 def test_typed_binary_zero_closed_identity_and_unique_global_unit(self):
  self.assertEqual(NS['require_binary_execution'](unit(),prepared()),3.25)
  for change in({'exit_code':False},{'exit_code':None},{'exit_code':-15},{'owned_group_empty':False},{'remaining_owned_processes':[{'pid':3}]},{'elapsed_seconds':float('nan')},{'declared_unit':'unit_diamond'}):
   with self.assertRaises(RuntimeError):NS['require_binary_execution']({**unit(),**change},prepared())
  for key,value in(('pid',18),('creation_ticks',101),('boot_id','other')):
   p=prepared();p['producer_creation_identity'][key]=value
   with self.assertRaises(RuntimeError):NS['require_binary_execution'](unit(),p)
 def test_original_namespace_order_and_sequences_without_control_comparison(self):
  names,expected=NS['expected_query_inventory'](inputs(),proteins())
  self.assertEqual(names,[A,B]);self.assertEqual(list(expected),[Q,QB])
  self.assertEqual(expected[QB]['sequence_sha256'],hashlib.sha256(b'MCCCCCCCCK').hexdigest())
  NS['require_query_inventory'](expected,expected.copy())
 def test_duplicate_and_ambiguous_query_keys_fail_before_dictionary_merge(self):
  for entries,parsed in((inputs()+[inputs()[0]],proteins()),(inputs(),{A:[{'id':'bad\u03a9gene','sequence':'MA'}],B:proteins()[B]}),(inputs(),{A:proteins()[A]*2,B:proteins()[B]})):
   with self.assertRaises(RuntimeError):NS['expected_query_inventory'](entries,parsed)
 def test_changed_order_sequence_missing_or_extra_query_fail(self):
  _,expected=NS['expected_query_inventory'](inputs(),proteins())
  variants=[dict(reversed(list(expected.items()))),{Q:expected[Q]}, {**expected,'extra':expected[Q]}, {**expected,Q:{**expected[Q],'length':9}}]
  for actual in variants:
   with self.assertRaises(RuntimeError):NS['require_query_inventory'](expected,actual)
 def test_full12_fields_duplicate_multiplicity_one_debit_and_empty_control_shard(self):
  names,expected=NS['expected_query_inventory'](inputs(),proteins())
  query=self.write('query.faa','>'+Q+'\nMAAAAAAAAK\n>'+QB+'\nMCCCCCCCCK\n')
  rawtext=hit()+hit(target='OtherReference~NOT_A_KO')+hit()
  raw=self.write('raw.tsv',rawtext);execution=self.write('execution.json',json.dumps(unit()))
  self.assertEqual(NS['scan_merged_raw'](self.root/raw['path'],expected),3)
  commit=splitter.split_search(project_root=self.root,query_fasta=query,merged_tsv=raw,search_execution=execution,declared_accessions=names,destination='shards')
  value=json.loads((self.root/commit['path']).read_text())
  self.assertEqual((self.root/value['shards'][0]['artifact']['path']).read_text(),rawtext)
  self.assertEqual(value['search_debit']['actual_unit_count'],1)
  self.assertEqual(value['shards'][0]['duplicate_rows'],1)
  self.assertEqual(value['shards'][1]['availability'],'SEARCH_SUCCEEDED_NO_REPORTED_HITS')
  self.assertFalse(value['shards'][1]['QC_or_defence_negative'])
 def test_unknown_query_target_or_numeric_malformed_fail(self):
  _,expected=NS['expected_query_inventory'](inputs(),proteins())
  for text in(hit(target='NO_SEPARATOR'),hit(target='~K00001'),hit(target='Reference~'),hit(q=A+'\u03a9unknown'),hit(evalue='NaN')):
   ref=self.write('bad.tsv',text)
   with self.assertRaises((RuntimeError,ValueError)):NS['scan_merged_raw'](self.root/ref['path'],expected)
 def test_production_calls_split_once_no_reference_comparison_or_model_dispatch(self):
  main=next(x for x in TREE.body if isinstance(x,ast.FunctionDef)and x.name=='main');text=ast.unparse(main)
  calls=[x for x in ast.walk(main)if isinstance(x,ast.Call)]
  self.assertEqual(sum(isinstance(x.func,ast.Attribute)and x.func.attr=='split_search'for x in calls),1)
  self.assertNotIn('reference_raw_diamond',text)
  self.assertFalse(any(isinstance(x.func,ast.Attribute)and x.func.attr in('Popen','execve','predict')for x in calls))
  self.assertIn('NOT_PERFORMED_REQUIRES_FIRST_OWN_ML_FEATURE_CHECKPOINT',text)
if __name__=='__main__':unittest.main()
