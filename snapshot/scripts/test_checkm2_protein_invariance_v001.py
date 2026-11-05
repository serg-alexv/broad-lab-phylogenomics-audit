"""Synthetic dictionary fixtures only; no current biological artifact is opened."""
import copy,unittest
import checkm2_protein_invariance_v001 as c

class ReceiptFixtures(unittest.TestCase):
 def row(self):return {'Name':'GCF_013267415.1','Completeness':'95.00','Contamination':'1.10','Completeness_Model_Used':'Neural Network','Additional_Notes':''}
 def annotation(self):
  values=[11,0.9,1000.0,250.0,2000,50,0.4,2,1500];sequence={'records':2,'ordered_content_sha256':'a'*64,'records_manifest':[{'fixture':True}]}
  return {'status':'ORIGINAL_SEQUENTIAL_PRODIGAL_COMPLETED_NOT_GENOME_ACCEPTANCE','accession':'GCF_013267415.1','faa_sha256':'b'*64,'faa_bytes':200,'protein_sequences':copy.deepcopy(sequence),'source_DNA_sequences':copy.deepcopy(sequence),'independent_DNA_QC':dict(zip(c.DNA_QC_KEYS,['fixture',2000,2,1500,1500,{'A':1000,'T':1000},0,0.0,2000,True])),'all10_original_return_values':['GCF_013267415.1',*values],'original_measurements':dict(zip(c.RETURN_KEYS,values)),'original_source_sha256':'c'*64,'prodigal_program_sha256':'d'*64,'author_deletes_selected_GFF_and_FNA':True,'interception_or_author_patch':False,'ML_modules_loaded':[]}
 def feature(self):return {'status':'PROTEIN_FEATURE_VECTOR_SCHEMA_VALIDATED_NOT_FNA_EQUIVALENCE','accession':'GCF_013267415.1','raw_pickle_sha256':'a'*64,'schema_sha256':c.FEATURE_SCHEMA_SHA,'ordered_column_names_sha256':'b'*64,'dataframe_shape':[1,21242],'actual_ML_input_dtype':'float64','canonical_float64_le_row_sha256':'c'*64,'finite_numeric_input':True,'prediction_values_untouched':True,'measured_nucleotide_route_equivalence':False}
 def test_five_column_report_accepts_boundary_without_DNA_columns(self):
  row=self.row();out=c.compare_protein_rows(row,{**row,'Completeness':'95.01'});self.assertTrue(out['equal_within_declared_tolerance']);self.assertFalse(out['DNA_report_columns_required'])
  self.assertFalse(c.compare_protein_rows(row,{**row,'Completeness':'95.02'})['equal_within_declared_tolerance'])
  self.assertFalse(c.compare_protein_rows(row,{**row,'Completeness_Model_Used':'Other'})['equal_within_declared_tolerance'])
 def test_missing_or_nonfinite_report_is_not_evaluable(self):
  row=self.row();del row['Additional_Notes']
  with self.assertRaises(c.NotEvaluable):c.compare_protein_rows(row,row)
  with self.assertRaises(c.NotEvaluable):c.compare_protein_rows(self.row(),{**self.row(),'Contamination':'NaN'})
 def test_annotation_all10_values_selectedFAA_and_DNA_metrics_required(self):
  row=self.annotation();self.assertTrue(c.compare_annotation_receipts(row,copy.deepcopy(row))['equal']);changed=copy.deepcopy(row);changed['faa_sha256']='e'*64;self.assertFalse(c.compare_annotation_receipts(row,changed)['equal'])
  missing=copy.deepcopy(row);del missing['original_measurements']['author_N50']
  with self.assertRaises(c.NotEvaluable):c.compare_annotation_receipts(missing,missing)
 def test_annotation_return_map_mismatch_and_ML_import_stop(self):
  row=self.annotation();bad=copy.deepcopy(row);bad['all10_original_return_values'][1]=4
  with self.assertRaises(c.NotEvaluable):c.compare_annotation_receipts(row,bad)
  bad=copy.deepcopy(row);bad['ML_modules_loaded']=['tensorflow']
  with self.assertRaises(c.NotEvaluable):c.compare_annotation_receipts(row,bad)
 def test_full_feature_hash_required_pickle_bytes_may_differ(self):
  row=self.feature();same=copy.deepcopy(row);same['raw_pickle_sha256']='d'*64;self.assertTrue(c.compare_feature_receipts(row,same)['equal']);same['canonical_float64_le_row_sha256']='e'*64;self.assertFalse(c.compare_feature_receipts(row,same)['equal'])
 def test_missing_both_features_or_wrong_dimensions_not_evaluable(self):
  with self.assertRaises(c.NotEvaluable):c.compare_feature_receipts({}, {})
  row=self.feature();row['dataframe_shape']=[1,21241]
  with self.assertRaises(c.NotEvaluable):c.compare_feature_receipts(row,row)

if __name__=='__main__':unittest.main()
