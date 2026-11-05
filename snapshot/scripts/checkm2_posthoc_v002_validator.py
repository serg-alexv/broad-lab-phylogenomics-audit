"""One file-only validation of our immutable trusted04R1 output. No model imports."""
from pathlib import Path
import argparse,csv,hashlib,json,math,os,sys,time,uuid
R=Path(__file__).resolve().parents[1]
FORBIDDEN=('tensorflow','keras','lightgbm','sklearn','checkm2.main','checkm2.predictQuality','checkm2.modelProcessing')
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def inside(p):
 p=Path(p);p=(p if p.is_absolute() else R/p).resolve()
 if not p.is_relative_to(R):raise RuntimeError('Path escapes isolated project')
 return p
def save(p,value):
 p=inside(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+'.'+uuid.uuid4().hex+'.tmp')
 with t.open('w') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
 for attempt in range(20):
  try:os.replace(t,p);return
  except PermissionError:
   if attempt==19:raise
   time.sleep(.05)
def canonical(x):return hashlib.sha256(json.dumps(x,separators=(',',':'),sort_keys=True).encode()).hexdigest()
def no_models():
 found=[n for n in sys.modules if any(n==x or n.startswith(x+'.') for x in FORBIDDEN)]
 if found:raise RuntimeError('Model/scientific pipeline module imported:'+repr(found))
 return found
def bind(row):
 p=inside(row['path'])
 if sha(p)!=row['sha256'] or ('bytes' in row and p.stat().st_size!=row['bytes']):raise RuntimeError('Bound artifact/source changed:'+str(p))
 return p
def domain_valid(kind,values):
 values=[float(x) for x in values]
 if not all(math.isfinite(x) for x in values):return False
 if kind=='NONNEGATIVE_INTEGER':return all(x>=0 and x.is_integer() for x in values)
 if kind=='MEMBERSHIP_FRACTION':return all(0<=x<=1 for x in values)
 if kind=='NONNEGATIVE_REAL_COPY_COUNT_MEAN':return all(x>=0 for x in values)
 raise ValueError('Unreviewed logical feature domain')
def preflight(admission):
 if admission.get('schema')!='TREE2_POSTHOC_FILE_VALIDATION_V002' or admission.get('status')!='ADMITTED_ONE_FILE_ONLY_VALIDATION' or admission.get('genomes_or_models_authorized')!=0:raise RuntimeError('File-only admission absent/invalid')
 for row in admission['sources']:bind(row)
 for row in admission['artifacts'].values():bind(row)
 manifest_path=bind(admission['artifacts']['failure_manifest']);run=inside(admission['original_run']);manifest=read(manifest_path)
 if len(manifest['files'])!=31:raise RuntimeError('Original31artifact manifest differs')
 for row in manifest['files']:
  p=inside(run/row['path'])
  if not p.is_relative_to(run) or p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('Original failed-attempt artifact changed')
 for row in admission['v001_scientific_sources']:bind(row)
 closure=read(bind(admission['artifacts']['baseline_closure']))
 if closure.get('status')!='04R1_BIOLOGY_AND_NATIVE_IPC_IMAGE_CLOSED_VALIDATION_HELD' or closure.get('native_wsl_exit_code')!=1 or not all(closure.get(x) is True for x in ('native_wsl_original_absent','outer_original_absent','ipc_cleanly_closed','common_native_locks_reacquired_released','current_Linux_compute_lease_reacquired_released')):raise RuntimeError('Original04R1 lifecycle proof incomplete')
 return manifest_path
def validate_domains(schema,frame,np):
 if list(frame.columns)!=schema['ordered_dataframe_columns'] or frame.shape!=(1,21242) or frame.columns.has_duplicates:raise ValueError('Ordered feature schema/shape differs')
 if any(getattr(x,'kind','?') not in ('i','u','f') for x in frame.dtypes.iloc[1:]):raise ValueError('Feature storage is not real numeric')
 values=frame.iloc[:,1:].values.astype(float)
 if values.shape!=(1,21241) or not np.isfinite(values).all():raise ValueError('Nonfinite or wrong ML input shape')
 for group in schema['groups']:
  block=values[0,group['model_start_zero_based']:group['model_stop_exclusive']];kind=group['logical_type']
  valid=domain_valid(kind,block)
  if not valid:raise ValueError('Raw feature domain mismatch:'+group['name'])
 return values
def main(a):
 admission_path=inside(a.admission)
 if sha(admission_path)!=a.admission_sha256:raise RuntimeError('Admission source changed')
 admission=read(admission_path);preflight(admission);no_models()
 if os.environ.get('TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED')!='1' or os.environ.get('TREE2_PRIVATE_NAMESPACE_VERIFIED')!='1':raise RuntimeError('Accepted private read-only runtime required')
 prefix=inside(admission['runtime_prefix'])
 if Path(sys.executable).resolve()!=prefix/'bin/python3.12' and Path(sys.executable).resolve()!=(prefix/'bin/python').resolve():raise RuntimeError('Validator not running in accepted prefixPython')
 # Hash/source admission happens before pandas import and before any unpickle.
 import numpy as np
 import pandas as pd
 if (sys.version_info[:3]!=(3,12,16) or np.__version__!='2.5.4' or pd.__version__!='3.1.0' or not Path(np.__file__).resolve().is_relative_to(prefix) or not Path(pd.__file__).resolve().is_relative_to(prefix)):raise RuntimeError('Pinned actual numpy/pandas/Python runtime differs')
 no_models();schema_path=bind(admission['artifacts']['schema']);schema=read(schema_path)
 if sha(schema_path)!='90e482515c6924386a888aa14a036f7659acf9ad0c49814cb08a3a7e1f76f5ee':raise RuntimeError('Reviewedv002 schema differs')
 assets={}
 for source_row in schema['source_files_and_assets']:
  p=inside(source_row['runtime_project_relative_path'])
  if p.stat().st_size!=source_row['bytes'] or sha(p)!=source_row['sha256']:raise RuntimeError('Actual frozen original source/JSON differs')
  if p.suffix=='.json':assets[p.name]=read(p)
 pickle_path=bind(admission['artifacts']['raw_pickle'])
 frame=pd.read_pickle(pickle_path);values=validate_domains(schema,frame,np);accession=admission['accession']
 if frame.iloc[0,0]!=accession:raise ValueError('Feature row accession/version differs')
 import checkm2_protein_helpers_v001 as old_helpers
 faa=bind(admission['artifacts']['selected_faa']);proteins=old_helpers.parse_fasta(faa.read_text(),old_helpers.AA);annotation=read(bind(admission['artifacts']['annotation_receipt']))
 if old_helpers.sequence_receipt(proteins)!=annotation['protein_sequences']:raise ValueError('All saved FAA records/headers/sequences must match annotationreceipt')
 joined=''.join(x['sequence'] for x in proteins);expected_aa=[joined.count(x) for x in schema['ordered_model_features'][:20]]+[len(joined),len(proteins)]
 if list(values[0,:22])!=expected_aa:raise ValueError('22FAA-derived metadata features differ')
 original_metrics=old_helpers.validate_author_return(annotation['all10_original_return_values'],accession)
 if original_metrics!=annotation['original_measurements']:raise ValueError('Original caller sidecar measurements changed')
 from checkm2_membership_recompute_v002 import recompute_membership_features
 raw_counts={name:frame[name].iloc[0] for name in schema['ordered_model_features'][22:20021]}
 expected=recompute_membership_features(raw_counts,assets['feature_ordering.json'],assets['kegg_path_category_mapping.json'],assets['module_definitions.json'])
 actual_names=schema['ordered_model_features'][20021:]
 if list(expected)!=actual_names or len(expected)!=1220:raise ValueError('Independentmembership output order/count differs')
 differences=[{'feature':name,'saved':float(values[0,20021+i]),'recomputed':float(expected[name])} for i,name in enumerate(actual_names) if float(values[0,20021+i])!=float(expected[name])]
 if differences:raise ValueError('Independent membership recomputation mismatch:'+repr(differences[:10]))
 report=bind(admission['artifacts']['quality_report']);row,comp,cont=old_helpers.parse_protein_report(report,accession)
 no_models();module_values=values[0,20437:21194];canonical_row=np.asarray(values,dtype='<f8',order='C')
 result={'status':'PRESERVED_04R1_FEATURES_AND_MEMBERSHIP_V002_PASS_PENDING_CLOSURE','scope':'FILE_ONLY_NO_PREDICTION_RERUN','accession':accession,'Completeness':comp,'Contamination':cont,'raw_author_protein_report_row':row,'original_failed_attempt_status_unchanged':True,'admission_sha256':a.admission_sha256,'raw_pickle_sha256':sha(pickle_path),'schema_v002_sha256':sha(schema_path),'source_FAA_sha256':sha(faa),'ordered_dataframe_columns_sha256':canonical(list(frame.columns)),'dataframe_shape':list(frame.shape),'actual_ML_cast_dtype':str(values.dtype),'canonical_float64_le_row_sha256':hashlib.sha256(canonical_row.tobytes()).hexdigest(),'finite_domain_features':21241,'exact_FAA_metadata_features':22,'independently_recomputed_membership_features':1220,'membership_comparison':'EXACT_FLOAT64_EQUALITY_NO_TOLERANCE_NO_CLIPPING','membership_mismatches':0,'module_features_above1':int(np.sum(module_values>1)),'module_feature_maximum':float(module_values.max()),'runtime':{'python':sys.version,'executable':sys.executable,'numpy':np.__version__,'numpy_origin':np.__file__,'pandas':pd.__version__,'pandas_origin':pd.__file__},'forbidden_model_modules_loaded':no_models(),'genomes_or_FAA_generated':0,'annotation_DIAMOND_or_ML_runs':0,'outer5664_exit_code':'UNKNOWN_NOT_CAPTURED','nucleotide_numeric_equivalence_measured':False,'production_acceptance':'NOT_GRANTED','format_control_acceptance':'NOT_GRANTED'}
 save(a.output,result)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--admission',required=True);p.add_argument('--admission-sha256',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 try:main(a)
 except BaseException as ex:
  save(inside(a.output).with_name('validation_failure.json'),{'status':'FILE_ONLY_POSTHOC_VALIDATION_FAILED','error':repr(ex),'no_prediction_rerun':True});raise
