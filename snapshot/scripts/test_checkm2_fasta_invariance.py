"""Small format/comparison fixtures only; no real genome or scientific tool calls."""
from pathlib import Path
import tempfile,unittest
import checkm2_fasta_invariance as c

class FormatControlFixtures(unittest.TestCase):
 def setUp(self):
  parent=c.R/'work/checkm2_fasta_fixture_runs';parent.mkdir(parents=True,exist_ok=True)
  self.temp=tempfile.TemporaryDirectory(dir=parent);self.r=Path(self.temp.name)
 def tearDown(self):
  if not self.r.resolve().is_relative_to((c.R/'work/checkm2_fasta_fixture_runs').resolve()):raise RuntimeError('Fixture cleanup target escaped project')
  self.temp.cleanup()
 def write(self,name,data):p=self.r/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);return p
 def test_wrap_preserves_exact_case_header_and_order(self):
  source=self.write('source.fna',b'>id  desc\r\n'+b'AcgTN'*31+b'\r\n>second\r\nccGG\r\n');before=source.read_bytes();out=self.r/'derived.fna'
  receipt=c.rewrap_new(source,out)
  self.assertEqual(source.read_bytes(),before);self.assertEqual(c.semantic_fasta(source),c.semantic_fasta(out));self.assertNotEqual(c.sha(source),c.sha(out))
  self.assertEqual(out.read_bytes().splitlines()[1],(b'AcgTN'*31)[:61]);self.assertTrue(receipt['source_unchanged'])
 def test_overwrite_and_noop_refused(self):
  source=self.write('source.fna',b'>a\nACGT\n')
  with self.assertRaises(c.NotEvaluable):c.rewrap_new(source,self.r/'noop.fna')
  self.assertFalse((self.r/'noop.fna').exists())
  destination=self.write('existing.fna',b'preserved')
  with self.assertRaises(FileExistsError):c.rewrap_new(source,destination)
  self.assertEqual(destination.read_bytes(),b'preserved')
 def test_malformed_or_whitespace_input_stops(self):
  for number,data in enumerate((b'ACGT\n',b'>a\n',b'>\nAA\n',b'>a\nAC GT\n')):
   with self.assertRaises(c.NotEvaluable):list(c.fasta_records(self.write(str(number)+'.fna',data)))
 def test_protein_wrap_equivalent_but_order_and_case_count(self):
  a=self.r/'a';b=self.r/'b';a.mkdir();b.mkdir();(a/'x.faa').write_bytes(b'>g1 extra\nMA\nKE\n>g2\nTT\n');(b/'x.faa').write_bytes(b'>g1 changed description\nMAKE\n>g2\nTT\n')
  self.assertEqual(c.protein_digest(a),c.protein_digest(b));(b/'x.faa').write_bytes(b'>g2\nTT\n>g1\nMAKE\n');self.assertNotEqual(c.protein_digest(a),c.protein_digest(b))
  (b/'x.faa').write_bytes(b'>g1\nMAKE\n>g1\nTT\n')
  with self.assertRaises(c.NotEvaluable):c.protein_digest(b)
 def test_diamond_multiset_order_ignored_duplicates_retained(self):
  a=self.r/'a';b=self.r/'b';a.mkdir();b.mkdir();r1=b'q1\ts1\t99\t10\t0\t0\t1\t10\t1\t10\t1e-9\t42\n';r2=r1.replace(b'q1',b'q2')
  (a/'DIAMOND_RESULTS.tsv').write_bytes(r1+r2+r1);(b/'DIAMOND_RESULTS.tsv').write_bytes(r2+r1+r1);self.assertEqual(c.diamond_digest(a),c.diamond_digest(b))
  (b/'DIAMOND_RESULTS.tsv').write_bytes(r2+r1);self.assertNotEqual(c.diamond_digest(a),c.diamond_digest(b))
  (b/'DIAMOND_RESULTS.tsv').write_bytes(r1.replace(b'99',b'nan'))
  with self.assertRaises(c.NotEvaluable):c.diamond_digest(b)
 def test_decimal_boundary_and_model_translation_exact(self):
  row={'Name':'GCF_X','Completeness':'95.00','Contamination':'1.10','Completeness_Model_Used':'Neural Network','Translation_Table_Used':'11','Additional_Notes':'None','Genome_Size':'1000','Total_Contigs':'2','Total_Coding_Sequences':'50','Contig_N50':'700','Max_Contig_Length':'700'}
  self.assertTrue(c.compare_rows(row,{**row,'Completeness':'95.01'})['equal_within_declared_tolerance']);self.assertFalse(c.compare_rows(row,{**row,'Completeness':'95.02'})['equal_within_declared_tolerance'])
  self.assertFalse(c.compare_rows(row,{**row,'Translation_Table_Used':'4'})['equal_within_declared_tolerance'])
  with self.assertRaises(c.NotEvaluable):c.compare_rows(row,{**row,'Contamination':'NaN'})
  with self.assertRaises(c.NotEvaluable):c.compare_rows(row,{**row,'Genome_Size':'1.5'})
 def test_missing_integer_from_both_reports_is_unknown(self):
  row={'Name':'GCF_X','Completeness':'95.00','Contamination':'1.10','Completeness_Model_Used':'Neural Network','Translation_Table_Used':'11','Additional_Notes':'None'}
  with self.assertRaises(c.NotEvaluable):c.compare_rows(row,row)
 def test_path_escape_and_second_claim_stop(self):
  with self.assertRaises(RuntimeError):c.inside(self.r,self.r.parent/'outside')
  plan={'control_workspace':'control','plan_path':'plan.json'};c.save_new(self.r/'plan.json',{'fixture':True});(self.r/'control').mkdir();c.claim_once(self.r,plan)
  with self.assertRaises(FileExistsError):c.claim_once(self.r,plan)
 def test_baseline_cannot_be_its_own_control(self):
  reference=self.r/'baseline';reference.mkdir()
  with self.assertRaises(RuntimeError):c.compare_runs(self.r,{'baseline':{'run_directory':'baseline'},'control_workspace':'control'},reference)
 def test_cached_comparison_corruption_is_not_reused(self):
  c.save_new(self.r/'plan.json',{'fixture':True});plan={'plan_path':'plan.json'};path=self.r/'comparison.json'
  c.save_new(path,{'status':'PASS_FORMAT_INVARIANCE_CONTROL_PIPELINE_ONLY','plan_sha256':c.sha(self.r/'plan.json'),'production_acceptance':False})
  completed={'comparison_path':'comparison.json','comparison_sha256':c.sha(path)};c.verify_cached_control(self.r,plan,completed)
  path.write_text('{}')
  with self.assertRaises(RuntimeError):c.verify_cached_control(self.r,plan,completed)

if __name__=='__main__':unittest.main()
