"""HELD exact author merged Omega query, then one fixed-index8 direct exec. No models."""
from pathlib import Path
import argparse,os,shutil,sys
import checkm2_qc_queue_common_v001 as c
import checkm2_protein_helpers_v001 as h
FORBIDDEN=('tensorflow','keras','lightgbm','sklearn','checkm2.main','checkm2.predictQuality','checkm2.modelProcessing')

def no_models():
 bad=[x for x in sys.modules if any(x==n or x.startswith(n+'.')for n in FORBIDDEN)]
 if bad:raise RuntimeError('Forbidden model modules '+repr(bad))
 return []

def build_argv(binary,query,output,database,scratch,defaults):
 return [str(binary),'blastp','--outfmt','6','--max-target-seqs','1','--query',str(query),'-o',str(output),'--threads','1','--db',str(database),'--query-cover',str(defaults['DIAMOND_QUERY_COVER']),'--subject-cover',str(defaults['DIAMOND_SUBJECT_COVER']),'--id',str(defaults['DIAMOND_PERCENT_ID']),'--evalue',str(defaults['DIAMOND_EVALUE']),'--block-size','0.5','--tmpdir',str(scratch),'--quiet','--index-chunks','8']

def merge_query_sequences(target,stem,parsed,separator):
 # The original author prefix/dictionary transform, with explicit pre-merge vetoes.
 if any(separator in key or any(x.isspace()for x in key)for key in parsed):raise RuntimeError('Ambiguous primary query identifier')
 part=dict(('{}{}{}'.format(stem,separator,key),value)for key,value in parsed.items())
 if set(part)&set(target):raise RuntimeError('Duplicate full author query keys must not overwrite')
 target.update(part)

def main(a):
 request=c.read(c.path(a.request))
 if c.sha(c.path(a.request))!=a.request_sha256 or request.get('request_schema')!='TREE2_CAMPAIGN_SHARED_DIAMOND_REQUEST_V003':raise RuntimeError('Shared trusted request differs')
 plan,recipe,_=c.request_gate(request);h.runtime_required();no_models();prefix=c.path(request['runtime_prefix'])
 if Path(sys.executable).resolve()!=(prefix/'bin/python').resolve():raise RuntimeError('Accepted actual prefix Python required')
 database=c.bind(request['database']);binary=c.bind(request['diamond_binary'])
 if binary!=prefix/'bin/diamond'or Path(shutil.which('diamond')or'').resolve()!=binary or os.environ.get('PATH','').split(os.pathsep)[0]!=str(prefix/'bin'):raise RuntimeError('Pinned exact binary/PATH required')
 for source in recipe['author_sources']:
  if c.sha(prefix/'lib/python3.12/site-packages/checkm2'/Path(source['path']).name)!=source['sha256']:raise RuntimeError('Original author source changed')
 from checkm2.sequenceClasses import SeqReader
 from checkm2.defaultValues import DefaultValues
 reader=SeqReader();sequences={};selected={}
 for item in request['query_inputs']:
  faa=c.bind(item['selected_faa']);acc=item['accession'];annotation=c.read(c.bind(item['annotation_receipt']));proteins=h.parse_fasta(faa.read_text(),h.AA)
  if faa.name!=acc+'.faa':raise RuntimeError('Exact versioned FAA basename required')
  c.validate_query_annotation(plan,item,proteins)
  if any('\u03a9'in x['id']or any(y.isspace()for y in x['id'])for x in proteins):raise RuntimeError('Ambiguous original primary query key')
  parsed=reader.read_nucleotide_sequences(str(faa))
  if len(parsed)!=len(proteins):raise RuntimeError('Original reader primary query inventory differs')
  merge_query_sequences(sequences,faa.stem,parsed,DefaultValues.DIAMOND_HEADER_SEPARATOR);selected[acc]=item['selected_faa']
 scratch=c.path(request['durable_scratch']);scratch.mkdir(parents=True,exist_ok=False);query=scratch/'original_author_merged_query.faa';reader.write_fasta(sequences,str(query));working=scratch/'diamond_work';working.mkdir()
 output=c.path(request['search_output']);output.mkdir(parents=True,exist_ok=False);(output/'diamond_output').mkdir();raw=output/'diamond_output/DIAMOND_RESULTS.tsv'
 defaults={n:getattr(DefaultValues,n)for n in('DIAMOND_QUERY_COVER','DIAMOND_SUBJECT_COVER','DIAMOND_PERCENT_ID','DIAMOND_EVALUE')}
 if defaults!={'DIAMOND_QUERY_COVER':80,'DIAMOND_SUBJECT_COVER':80,'DIAMOND_PERCENT_ID':30,'DIAMOND_EVALUE':1e-5}:raise RuntimeError('Original scientific filters changed')
 argv=build_argv(binary,query,raw,database,working,defaults);no_models()
 origins={n:str(Path(m.__file__).resolve())for n,m in list(sys.modules.items())if n.startswith('checkm2.')and getattr(m,'__file__',None)}
 if any(not Path(v).is_relative_to(prefix)for v in origins.values()):raise RuntimeError('Author origin outside prefix')
 from checkm2_owned_cleanup_T1 import identity
 c.save(c.path(a.output).with_name('search_exec_prepared.json'),{'status':'MERGED_AUTHOR_QUERY_PREPARED_NO_SEARCH_EXIT_YET','request_sha256':a.request_sha256,'query':c.row(query),'query_inputs':request['query_inputs'],'selected_faas':selected,'argv':argv,'database':request['database'],'diamond_binary':request['diamond_binary'],'actual_author_origins':origins,'no_model_modules':no_models(),'producer_pid_before_exec':os.getpid(),'producer_creation_identity':identity(os.getpid()),'fresh_input_count':c.COUNT,'control_input_count':len(plan['controls']),'author_chunk_limit250_respected':len(request['query_inputs'])<=250,'single_query_equivalence_and_memory_fit':'NOT_ESTABLISHED'})
 if c.sha(c.path(a.request))!=a.request_sha256:raise RuntimeError('Shared request changed before exec')
 os.execve(str(binary),argv,dict(os.environ))
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for name in('request','request-sha256','output'):p.add_argument('--'+name,required=True)
 main(p.parse_args())
