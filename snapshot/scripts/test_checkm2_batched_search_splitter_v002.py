"""Toy files only, under project/work. No tools, models or real genome data."""
from pathlib import Path
import json, tempfile, unittest
from unittest.mock import patch
import checkm2_batched_search_splitter_v002 as s

A='GCF_000000001.1';B='GCA_000000002.2'
Q1=A+'\u03a9gene1';Q2=A+'\u03a9gene2';QB=B+'\u03a9gene1'

def hit(query=Q1,target='UniRef100_A~K00001',evalue='1.000e-20',bits='45.500'):
 return '\t'.join((query,target,'90.00','10','1','0','1','10','3','12',evalue,bits))+'\n'

class Splitter(unittest.TestCase):
 def setUp(self):
  parent=Path(__file__).resolve().parents[1]/'work/batched_search_splitter_toy_fixtures_v002';parent.mkdir(parents=True,exist_ok=True)
  self.work_parent=parent.resolve();self.temp=tempfile.TemporaryDirectory(dir=parent);self.root=Path(self.temp.name)
  assert self.root.resolve().is_relative_to(self.work_parent)
  self.query=self.write('query.faa','>'+Q1+'\nMAAAAAAAAK\n>'+Q2+'\nMBBBBBBBBK\n>'+QB+'\nMCCCCCCCCK\n')
  self.tsv=self.write('merged.tsv',hit());self.execution=self.write('execution.json',json.dumps({'exit_code':0,'owned_group_empty':True,'remaining_owned_processes':[],'elapsed_seconds':123.125}))
 def tearDown(self):
  assert self.root.resolve().is_relative_to(self.work_parent)
  self.temp.cleanup()
 def write(self,name,value):
  p=self.root/name;p.write_text(value,encoding='utf-8',newline='\n');return s._file_ref(self.root,p)
 def split(self,**kwargs):
  values={'project_root':self.root,'query_fasta':self.query,'merged_tsv':self.tsv,'search_execution':self.execution,'declared_accessions':[A,B],'destination':'shards'};values.update(kwargs);return s.split_search(**values)
 def test_full_fields_order_ties_multiplehits_and_multiplicity(self):
  raw=hit()+hit(target='UniRef100_B~K99999')+hit();self.tsv=self.write('merged.tsv',raw)
  result=self.split();commit=json.loads((self.root/result['path']).read_text());row=commit['shards'][0]
  self.assertEqual((self.root/row['artifact']['path']).read_text(),raw)
  self.assertEqual((row['rows'],row['unique_rows'],row['duplicate_rows']), (3,2,1))
  self.assertEqual(row['query_count'],2);self.assertEqual(row['reported_hit_query_count'],1)
  self.assertEqual(commit['search_debit']['actual_unit_count'],1);self.assertEqual(commit['search_debit']['actual_elapsed_seconds'],123.125)
  self.assertTrue(all('search_execution'not in x and 'elapsed_seconds'not in x for x in commit['shards']))
 def test_no_hit_is_explicit_successful_search_not_biological_negative(self):
  result=self.split();commit=json.loads((self.root/result['path']).read_text());row=commit['shards'][1]
  self.assertEqual(row['availability'],'SEARCH_SUCCEEDED_NO_REPORTED_HITS');self.assertFalse(row['QC_or_defence_negative'])
  self.assertEqual((self.root/row['artifact']['path']).read_bytes(),b'');self.assertEqual(row['unreported_query_count'],1)
 def test_failed_unknown_or_live_search_never_publishes(self):
  for change in({'exit_code':-15},{'exit_code':None},{'exit_code':False},{'owned_group_empty':None},{'remaining_owned_processes':[{'pid':1}]},{'elapsed_seconds':None}):
   execution={'exit_code':0,'owned_group_empty':True,'remaining_owned_processes':[],'elapsed_seconds':123.125};execution.update(change)
   ref=self.write('bad_execution.json',json.dumps(execution))
   with self.assertRaises(ValueError):self.split(search_execution=ref)
   self.assertFalse((self.root/'shards').exists())
 def test_unknown_query_and_genome_rejected(self):
  for query in(A+'\u03a9UNKNOWN','GCF_999999999.1\u03a9gene1'):
   self.tsv=self.write('merged.tsv',hit(query))
   with self.assertRaises(ValueError):self.split()
   self.assertFalse((self.root/'shards').exists())
 def test_duplicate_query_headers_and_missing_declared_inputs(self):
  query=self.write('duplicate.faa','>'+Q1+'\nMAAAAAAAAK\n>'+Q1+'\nMAAAAAAAAK\n>'+QB+'\nMCCCCCCCCK\n')
  with self.assertRaises(ValueError):self.split(query_fasta=query)
  query=self.write('missing.faa','>'+Q1+'\nMAAAAAAAAK\n')
  with self.assertRaises(ValueError):self.split(query_fasta=query)
  with self.assertRaises(ValueError):self.split(declared_accessions=[A,A])
 def test_malformed_fields_numeric_domains_and_coordinates(self):
  baseline=hit().rstrip('\n').split('\t')
  for fields in([*baseline,'EXTRA'],baseline[:-1]):
   self.tsv=self.write('merged.tsv','\t'.join(fields)+'\n')
   with self.assertRaises(ValueError):self.split()
  for column,bad in((2,'NaN'),(2,'101'),(10,'Infinity'),(10,'-1e-10'),(11,'-1'),(3,'10.5'),(8,'0'),(7,'11')):
   fields=baseline.copy();fields[column]=bad;self.tsv=self.write('merged.tsv','\t'.join(fields)+'\n')
   with self.assertRaises(ValueError):self.split()
 def test_float_spelling_never_coerced_or_deduplicated(self):
  raw=hit(evalue='1.0e-10',bits='4.5500E+1')+hit(evalue='0.0000000001',bits='45.50');self.tsv=self.write('merged.tsv',raw)
  self.split();self.assertEqual((self.root/'shards'/ (A+'.tsv')).read_text(),raw)
 def test_exact_resume_does_not_rewrite_and_no_overwrite(self):
  ref=self.split();p=self.root/ref['path'];before=p.stat().st_mtime_ns
  with self.assertRaises(FileExistsError):self.split()
  self.assertEqual(self.split(expected_existing_commit_sha256=ref['sha256']),ref)
  self.assertEqual(p.stat().st_mtime_ns,before)
  with self.assertRaises(FileExistsError):self.split(expected_existing_commit_sha256='0'*64)
  self.write('shards/extra.tsv','unexpected')
  with self.assertRaises(ValueError):self.split(expected_existing_commit_sha256=ref['sha256'])
 def test_interrupted_publication_has_no_commit_and_cannot_auto_resume(self):
  actual_link=s.os.link
  def interrupted(source,target):
   if Path(target).name==B+'.tsv':raise OSError('injected publication failure')
   return actual_link(source,target)
  with patch.object(s.os,'link',side_effect=interrupted):
   with self.assertRaises(OSError):self.split()
  self.assertFalse((self.root/'shards/commit.json').exists())
  with self.assertRaises(FileExistsError):self.split()
 def test_input_hash_and_output_containment_fail_closed(self):
  (self.root/'merged.tsv').write_text(hit(target='ALTERED'))
  with self.assertRaises(ValueError):self.split()
  self.tsv=self.write('merged.tsv',hit())
  with self.assertRaises(ValueError):self.split(destination=self.root.parent/'outside')
if __name__=='__main__':unittest.main()
