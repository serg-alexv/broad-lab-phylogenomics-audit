"""Held, pure receipt comparators; no genome, pickle, model or tool is opened."""
from decimal import Decimal,InvalidOperation
import math,re

PROTEIN_COLUMNS=('Name','Completeness','Contamination','Completeness_Model_Used','Additional_Notes')
RETURN_KEYS=('translation_table','coding_density','author_N50','mean_gene_length_AA','total_nucleotide_bases','CDS_count','author_GC_fraction','contig_count','max_contig_length')
DNA_QC_KEYS=('method','total_bases','contigs','max_contig_length','standard_contig_N50','base_counts','ambiguous_bases','GC_fraction_among_ACGT','GC_denominator_ACGT','not_author_quality_report_columns')
FEATURE_SCHEMA_SHA='2be7bda6589a445a8b70023d9cf84ffadc76a380db112b34a70ce0094fc53adb'
class NotEvaluable(RuntimeError):pass
def required(value,keys,label):
 if not isinstance(value,dict) or any(key not in value for key in keys):raise NotEvaluable('Missing required '+label)
def digest(value,label):
 if not isinstance(value,str) or not re.fullmatch('[a-f0-9]{64}',value):raise NotEvaluable('Missing/malformed '+label+' SHA256')
def number(value,label):
 if isinstance(value,bool):raise NotEvaluable('Boolean instead of '+label)
 try:out=Decimal(str(value))
 except (InvalidOperation,ValueError):raise NotEvaluable('Malformed '+label)
 if not out.is_finite():raise NotEvaluable('Nonfinite '+label)
 return out
def compare_protein_rows(reference,control):
 for row in (reference,control):
  required(row,PROTEIN_COLUMNS,'five-column protein report')
  if set(row)!=set(PROTEIN_COLUMNS):raise NotEvaluable('Protein report must retain its exact five columns')
 differences=[];deltas={}
 for key in ('Name','Completeness_Model_Used','Additional_Notes'):
  if not isinstance(reference[key],str) or not isinstance(control[key],str):raise NotEvaluable('Missing report text:'+key)
  if key!='Additional_Notes' and (not reference[key] or not control[key]):raise NotEvaluable('Empty report text:'+key)
  if reference[key]!=control[key]:differences.append(key)
 for key in ('Completeness','Contamination'):
  a,b=number(reference[key],key),number(control[key],key)
  if min(a,b)<0 or (key=='Completeness' and max(a,b)>100):raise NotEvaluable('Report score outside domain')
  delta=abs(a-b);deltas[key]=str(delta)
  if delta>Decimal('0.01'):differences.append(key)
 return {'equal_within_declared_tolerance':not differences,'differences':differences,'score_delta_percentage_points':deltas,'DNA_report_columns_required':False,'production_acceptance':False}
def compare_annotation_receipts(reference,control):
 keys=('status','accession','faa_sha256','faa_bytes','protein_sequences','source_DNA_sequences','independent_DNA_QC','all10_original_return_values','original_measurements','original_source_sha256','prodigal_program_sha256','author_deletes_selected_GFF_and_FNA','interception_or_author_patch','ML_modules_loaded')
 for row in (reference,control):
  required(row,keys,'original annotation receipt')
  if row['status']!='ORIGINAL_SEQUENTIAL_PRODIGAL_COMPLETED_NOT_GENOME_ACCEPTANCE' or row['interception_or_author_patch'] is not False or row['ML_modules_loaded']!=[] or row['author_deletes_selected_GFF_and_FNA'] is not True:raise NotEvaluable('Original model-free annotation route not established')
  for key in ('faa_sha256','original_source_sha256','prodigal_program_sha256'):digest(row[key],key)
  for key in ('protein_sequences','source_DNA_sequences'):
   required(row[key],('records','ordered_content_sha256','records_manifest'),key)
   digest(row[key]['ordered_content_sha256'],key)
  required(row['original_measurements'],RETURN_KEYS,'all nine original measurements')
  required(row['independent_DNA_QC'],DNA_QC_KEYS,'independent DNA measurements')
  values=row['all10_original_return_values']
  if not isinstance(values,list) or len(values)!=10 or values[0]!=row['accession']:raise NotEvaluable('All ten original return values required')
  for index,key in enumerate(RETURN_KEYS,1):
   a,b=number(values[index],key),number(row['original_measurements'][key],key)
   if a!=b:raise NotEvaluable('Original return list/measurement map disagree')
  if number(row['faa_bytes'],'FAA size')<=0:raise NotEvaluable('Empty selected FAA')
 differences=[]
 for key in ('accession','faa_sha256','faa_bytes','original_source_sha256','prodigal_program_sha256','protein_sequences','source_DNA_sequences','independent_DNA_QC','all10_original_return_values','original_measurements'):
  if reference[key]!=control[key]:differences.append(key)
 return {'equal':not differences,'differences':differences,'selected_FAA_bytes_required_identical':True,'all10_original_return_values_required':True,'DNA_metrics_from_separate_sidecars':True,'source_FNA_sha_intentionally_bound_elsewhere':True,'production_acceptance':False}
def compare_feature_receipts(reference,control):
 fields=('status','accession','raw_pickle_sha256','schema_sha256','ordered_column_names_sha256','dataframe_shape','actual_ML_input_dtype','canonical_float64_le_row_sha256','finite_numeric_input','prediction_values_untouched','measured_nucleotide_route_equivalence')
 for row in (reference,control):
  required(row,fields,'full raw feature receipt')
  if row['status']!='PROTEIN_FEATURE_VECTOR_SCHEMA_VALIDATED_NOT_FNA_EQUIVALENCE' or row['schema_sha256']!=FEATURE_SCHEMA_SHA or row['dataframe_shape']!=[1,21242] or row['actual_ML_input_dtype']!='float64' or row['finite_numeric_input'] is not True or row['prediction_values_untouched'] is not True or row['measured_nucleotide_route_equivalence'] is not False:raise NotEvaluable('Required finite 21241-feature raw input not established')
  for key in ('raw_pickle_sha256','schema_sha256','ordered_column_names_sha256','canonical_float64_le_row_sha256'):digest(row[key],key)
 compare=('accession','schema_sha256','ordered_column_names_sha256','dataframe_shape','actual_ML_input_dtype','canonical_float64_le_row_sha256')
 differences=[key for key in compare if reference[key]!=control[key]]
 return {'equal':not differences,'differences':differences,'all21241_raw_features_compared':True,'canonical_float64_le_row_hash_required_identical':True,'raw_pickle_serialization_byte_equality_required':False,'missing_both_feature_dumps_is_pass':False,'production_acceptance':False}
