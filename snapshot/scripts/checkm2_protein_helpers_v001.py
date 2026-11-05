"""Held protein-route helpers. Default imports are stdlib; no automatic biology."""
from pathlib import Path
import argparse,collections,hashlib,json,math,os,re,sys,uuid
R=Path(__file__).resolve().parents[1]
DNA=set('ACGTRYSWKMBDHVNacgtryswkmbdhvn');AA=set('ACDEFGHIKLMNPQRSTVWYXBZUOJ*')
FORBIDDEN=('tensorflow','keras','lightgbm','sklearn','checkm2.main','checkm2.predictQuality','checkm2.modelProcessing')
PROTEIN_COLUMNS=['Name','Completeness','Contamination','Completeness_Model_Used','Additional_Notes']
DNA_COLUMNS=['Translation_Table_Used','Coding_Density','Contig_N50','Average_Gene_Length','Genome_Size','GC_Content','Total_Coding_Sequences','Total_Contigs','Max_Contig_Length']

def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def inside(p):
 p=Path(p);p=(p if p.is_absolute() else R/p).resolve()
 if not p.is_relative_to(R):raise RuntimeError('Path outside isolated project')
 return p
def save(p,value):
 p=inside(p);p.parent.mkdir(parents=True,exist_ok=True);temp=p.with_name(p.name+'.'+uuid.uuid4().hex+'.tmp')
 with temp.open('w') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(temp,p)
def canonical(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def parse_fasta(text,alphabet):
 records=[];ids=set();current=None;sequence=[]
 def finish():
  if current is not None:
   seq=''.join(sequence)
   if not seq or not set(seq).issubset(alphabet):raise ValueError('Empty or invalid sequence')
   records.append({'header':current,'id':current.split()[0],'sequence':seq})
 for line in text.splitlines():
  line=line.strip()
  if not line:continue
  if line.startswith('>'):
   finish();current=line[1:].strip();sequence=[]
   if not current or current.split()[0] in ids:raise ValueError('Empty or duplicate sequence identifier')
   ids.add(current.split()[0])
  else:
   if current is None:raise ValueError('Sequence before first FASTA header')
   if any(c.isspace() for c in line):raise ValueError('Internal sequence whitespace')
   sequence.append(line)
 finish()
 if not records:raise ValueError('No FASTA records')
 return records
def sequence_receipt(records):
 return {'records':len(records),'case_preserved':True,'ordered_identifiers':[x['id'] for x in records],
  'records_manifest':[{'id':x['id'],'header_sha256':hashlib.sha256(x['header'].encode()).hexdigest(),'length':len(x['sequence']),'sequence_sha256':hashlib.sha256(x['sequence'].encode()).hexdigest()} for x in records],
  'ordered_content_sha256':canonical([(x['header'],x['sequence']) for x in records])}
def dna_statistics(records):
 lengths=sorted((len(x['sequence']) for x in records),reverse=True);counts=collections.Counter(''.join(x['sequence'].upper() for x in records));total=sum(lengths);acc=0;n50=None
 for length in lengths:
  acc+=length
  if acc*2>=total:n50=length;break
 acgt=sum(counts[x] for x in 'ACGT')
 return {'method':'independent_stdlib_assembly_summary_v001','total_bases':total,'contigs':len(lengths),'max_contig_length':max(lengths),'standard_contig_N50':n50,'base_counts':dict(sorted(counts.items())),'ambiguous_bases':total-acgt,'GC_fraction_among_ACGT':(counts['G']+counts['C'])/acgt if acgt else None,'GC_denominator_ACGT':acgt,'not_author_quality_report_columns':True}
def validate_author_return(values,accession):
 if len(values)!=10 or values[0]!=accession:raise ValueError('Original runner must return exact bin identifier plus9measurements')
 names=['translation_table','coding_density','author_N50','mean_gene_length_AA','total_nucleotide_bases','CDS_count','author_GC_fraction','contig_count','max_contig_length']
 numeric=[x.item() if hasattr(x,'item') else x for x in values[1:]]
 if not all(type(x) in (int,float) and math.isfinite(x) for x in numeric):raise ValueError('Nonfinite/nonreal original runner measurement')
 result=dict(zip(names,numeric))
 for name in ('translation_table','total_nucleotide_bases','CDS_count','contig_count','max_contig_length'):
  if not isinstance(result[name],int) and not result[name].is_integer():raise ValueError('Noninteger count/table')
 if result['translation_table'] not in (4,11) or min(result[x] for x in ('author_N50','mean_gene_length_AA','total_nucleotide_bases','CDS_count','contig_count','max_contig_length'))<=0:raise ValueError('Empty/invalid annotation metrics')
 if not 0<=result['coding_density']<=1 or not 0<=result['author_GC_fraction']<=1:raise ValueError('Fraction outside0..1')
 return result
def parse_protein_report(path,accession):
 import csv
 with Path(path).open(newline='') as f:
  reader=csv.DictReader(f,delimiter='\t');fields=reader.fieldnames;rows=list(reader)
 if fields!=PROTEIN_COLUMNS or len(rows)!=1 or rows[0]['Name']!=accession:raise ValueError('Supported auto protein report schema/row/name mismatch')
 row=rows[0]
 if set(row)!=set(PROTEIN_COLUMNS) or any(row[x] is None for x in PROTEIN_COLUMNS):raise ValueError('Extra or missing report data cells')
 comp=float(row['Completeness']);cont=float(row['Contamination'])
 if not math.isfinite(comp) or not math.isfinite(cont) or not 0<=comp<=100 or cont<0:raise ValueError('Invalid numeric quality estimate')
 if not row['Completeness_Model_Used'] or row['Additional_Notes'] is None:raise ValueError('Missing author model/notes field')
 return row,comp,cont

def runtime_required():
 if os.environ.get('TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED')!='1' or os.environ.get('TREE2_CHECKM2_PRIVATE_IPC_VERIFIED')!='1':raise RuntimeError('Accepted read-only image and private IPC required')
def validate_feature_contract(schema,columns,names,values,storage_kinds):
 if columns!=schema['ordered_dataframe_columns'] or len(set(columns))!=len(columns) or len(names)!=1 or len(values)!=21241 or len(storage_kinds)!=21241:raise ValueError('Feature column order/shape differs')
 if any(kind not in ('i','u','f') for kind in storage_kinds):raise ValueError('Feature storage must be real numeric, not bool/object/string/complex')
 numeric=[float(x) for x in values]
 if not all(math.isfinite(x) for x in numeric):raise ValueError('Missing/nonfinite raw feature')
 for group in schema['groups']:
  block=numeric[group['model_start_zero_based']:group['model_stop_exclusive']]
  if group['logical_type']=='NONNEGATIVE_INTEGER':
   if any(x<0 or not x.is_integer() for x in block):raise ValueError('Nonintegral/negative count feature')
  elif group['logical_type']=='MEMBERSHIP_FRACTION':
   if any(not 0<=x<=1 for x in block):raise ValueError('Membership fraction outside0..1')
  else:raise ValueError('Unreviewed feature group type')
 return numeric
def annotate(plan_path,output):
 runtime_required();plan=read(inside(plan_path));item=plan['input'];out=inside(output);out.mkdir(exist_ok=False)
 source=inside(item['staged_fna']);prefix=inside(plan['runtime_prefix'])
 if not re.fullmatch(r'GC[AF]_\d{9}\.\d+',item['accession']) or source.name!=item['accession']+'.fna':raise RuntimeError('Exact versioned accession FNA basename required')
 if not re.fullmatch(r'[A-Za-z0-9_./-]+',str(source)) or not re.fullmatch(r'[A-Za-z0-9_./-]+',str(out)):raise RuntimeError('Original unquoted shell runner requires controlled whitespace-free paths')
 if sha(source)!=item['fasta_sha256']:raise RuntimeError('Staged FNA hash differs')
 dna=parse_fasta(source.read_text(),DNA);independent=dna_statistics(dna)
 if independent['GC_denominator_ACGT']==0:raise RuntimeError('No unambiguous DNA; measurement held')
 before=[x for x in sys.modules if any(x==n or x.startswith(n+'.') for n in FORBIDDEN)]
 if before:raise RuntimeError('Annotation interpreter already imported ML modules')
 expected_module=prefix/'lib/python3.12/site-packages/checkm2/prodigal.py'
 if sha(expected_module)!=plan['original_prodigal_source_sha256']:raise RuntimeError('Original ProdigalRunner differs before import')
 import checkm2.prodigal as original
 module=Path(original.__file__).resolve()
 if not module.is_relative_to(prefix) or sha(module)!=plan['original_prodigal_source_sha256']:raise RuntimeError('Original ProdigalRunner source differs')
 after=[x for x in sys.modules if any(x==n or x.startswith(n+'.') for n in FORBIDDEN)]
 if after:raise RuntimeError('Model-free annotation imported ML modules')
 if sha(prefix/'bin/prodigal')!=plan['prodigal_program_sha256']:raise RuntimeError('Prodigal executable differs')
 runner=original.ProdigalRunner(str(out),str(source));returned=runner.run(str(source),supplied_coding_table=None)
 metrics=validate_author_return(returned,item['accession']);faa=out/(item['accession']+'.faa');proteins=parse_fasta(faa.read_text(),AA)
 if metrics['CDS_count']!=len(proteins) or metrics['total_nucleotide_bases']!=independent['total_bases'] or metrics['contig_count']!=independent['contigs'] or metrics['max_contig_length']!=independent['max_contig_length']:raise RuntimeError('Original and independent sequence/count measurements disagree')
 if sha(source)!=item['fasta_sha256']:raise RuntimeError('Staged source changed during annotation')
 save(out/'annotation_receipt.json',{'status':'ORIGINAL_SEQUENTIAL_PRODIGAL_COMPLETED_NOT_GENOME_ACCEPTANCE','accession':item['accession'],'source_fna_sha256':sha(source),'faa_path':str(faa),'faa_sha256':sha(faa),'faa_bytes':faa.stat().st_size,'protein_sequences':sequence_receipt(proteins),'source_DNA_sequences':sequence_receipt(dna),'independent_DNA_QC':independent,'all10_original_return_values':[returned[0],*[metrics[x] for x in ('translation_table','coding_density','author_N50','mean_gene_length_AA','total_nucleotide_bases','CDS_count','author_GC_fraction','contig_count','max_contig_length')]],'original_measurements':metrics,'original_source_sha256':sha(module),'prodigal_program_sha256':sha(prefix/'bin/prodigal'),'notices_unchanged':True,'author_deletes_selected_GFF_and_FNA':True,'interception_or_author_patch':False,'ML_modules_loaded':after,'gene_annotation_is_QC_input_only':True,'production_acceptance':'NOT_GRANTED'})

def validate_features(plan_path,output):
 runtime_required();plan=read(inside(plan_path));out=inside(output);schema_path=inside(plan['schema_path'])
 if sha(schema_path)!=plan['schema_sha256']:raise RuntimeError('Feature schema changed')
 schema=read(schema_path);expected=schema['ordered_dataframe_columns'];files=list(inside(plan['quality_output']).glob('feature_vectors_*.pkl'))
 if len(files)!=1 or files[0].name!='feature_vectors_1.pkl':raise ValueError('Exactly the first declared feature-vector chunk required for one genome')
 import numpy as np
 import pandas as pd
 frame=pd.read_pickle(files[0])
 if list(frame.columns)!=expected or len(frame)!=1 or frame.iloc[0,0]!=plan['accession'] or frame.columns.has_duplicates:raise ValueError('Feature column order/shape/name differs')
 validate_feature_contract(schema,list(frame.columns),list(frame.iloc[:,0]),list(frame.iloc[0,1:]),[getattr(x,'kind','UNKNOWN') for x in frame.dtypes.iloc[1:]])
 vector=frame.iloc[:,1:].values.astype(float)
 if vector.shape!=(1,21241) or not np.isfinite(vector).all():raise ValueError('Actual ML input dimensions/nonfinite value')
 faa=inside(plan['selected_faa_path'])
 if sha(faa)!=plan['selected_faa_sha256']:raise ValueError('Admitted FAA changed before feature validation')
 proteins=parse_fasta(faa.read_text(),AA);joined=''.join(x['sequence'] for x in proteins);aa_expected=[joined.count(x) for x in schema['ordered_model_features'][:20]]+[len(joined),len(proteins)]
 if list(vector[0,:22])!=aa_expected:raise ValueError('All22AAmetadata features disagree with exact selected FAA')
 canonical_vector=np.asarray(vector,dtype='<f8',order='C')
 save(out,{'status':'PROTEIN_FEATURE_VECTOR_SCHEMA_VALIDATED_NOT_FNA_EQUIVALENCE','accession':plan['accession'],'raw_pickle_path':str(files[0]),'raw_pickle_sha256':sha(files[0]),'schema_path':str(schema_path),'schema_sha256':sha(schema_path),'ordered_column_names_sha256':canonical(expected),'dataframe_shape':list(frame.shape),'storage_dtypes':{str(k):str(v) for k,v in frame.dtypes.items()},'actual_ML_input_dtype':str(vector.dtype),'canonical_float64_le_row_sha256':hashlib.sha256(canonical_vector.tobytes()).hexdigest(),'finite_numeric_input':True,'prediction_values_untouched':True,'measured_nucleotide_route_equivalence':False})

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('operation',choices=['annotate','validate-features']);p.add_argument('--plan',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 annotate(a.plan,a.output) if a.operation=='annotate' else validate_features(a.plan,a.output)
