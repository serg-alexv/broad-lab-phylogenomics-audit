"""HELD source-equivalent author query/argv, then exec the unchanged DIAMOND binary."""
from pathlib import Path
import argparse,os,shutil,sys
import checkm2_P20_resource_repair_common_v001 as c
import checkm2_protein_helpers_v001 as h
FORBIDDEN=('tensorflow','keras','lightgbm','sklearn','checkm2.main','checkm2.predictQuality','checkm2.modelProcessing')
def no_models():
 bad=[x for x in sys.modules if any(x==n or x.startswith(n+'.')for n in FORBIDDEN)]
 if bad:raise RuntimeError('Forbidden model import: '+repr(bad))
 return []
def build_argv(binary,query,output,database,scratch,defaults):
 return [str(binary),'blastp','--outfmt','6','--max-target-seqs','1','--query',str(query),'-o',str(output),'--threads','1','--db',str(database),'--query-cover',str(defaults['DIAMOND_QUERY_COVER']),'--subject-cover',str(defaults['DIAMOND_SUBJECT_COVER']),'--id',str(defaults['DIAMOND_PERCENT_ID']),'--evalue',str(defaults['DIAMOND_EVALUE']),'--block-size','0.5','--tmpdir',str(scratch),'--quiet']
def main(a):
 request=c.read(c.path(a.request))
 if c.sha(c.path(a.request))!=a.request_sha256:raise RuntimeError('Trusted request changed')
 plan,recipe,authority=c.request_gate(request);h.runtime_required();no_models();prefix=c.path(request['runtime_prefix'])
 if Path(sys.executable).resolve()!=(prefix/'bin/python').resolve():raise RuntimeError('Accepted runtime Python required')
 faa=c.bind(request['selected_faa']);acc=recipe['input']['accession'];annotation=c.read(c.bind(request['annotation_receipt']))
 if faa.name!=acc+'.faa' or annotation['accession']!=acc or annotation['faa_sha256']!=c.sha(faa) or not c.unit_closed(c.read(c.bind(request['annotation_unit_execution']))):raise RuntimeError('Exact successful own annotation must be reused')
 proteins=h.parse_fasta(faa.read_text(),h.AA)
 if h.sequence_receipt(proteins)!=annotation['protein_sequences']:raise RuntimeError('Own FAA sequence/header inventory differs')
 database=c.bind(request['database']);binary=c.bind(request['diamond_binary'])
 if binary!=prefix/'bin/diamond' or Path(shutil.which('diamond')or'').resolve()!=binary or os.environ.get('PATH','').split(os.pathsep)[0]!=str(prefix/'bin'):raise RuntimeError('Exact accepted DIAMOND path required')
 for source in recipe['author_sources']:
  module=prefix/'lib/python3.12/site-packages/checkm2'/Path(source['path']).name
  if c.sha(module)!=source['sha256']:raise RuntimeError('Pinned author source differs')
 from checkm2.sequenceClasses import SeqReader
 from checkm2.defaultValues import DefaultValues
 # This is the original one-FAA dictionary/header transform and unchanged author writer.
 parsed=SeqReader().read_nucleotide_sequences(str(faa));sequences=dict(('{}{}{}'.format(faa.stem,DefaultValues.DIAMOND_HEADER_SEPARATOR,k),v)for k,v in parsed.items())
 scratch=c.path(request['durable_scratch']);scratch.mkdir(parents=True,exist_ok=False);query=scratch/'original_author_query.faa';SeqReader().write_fasta(sequences,str(query));working=scratch/'diamond_work';working.mkdir()
 output=c.path(request['resume_output']);output.mkdir(parents=True,exist_ok=False);(output/'diamond_output').mkdir();raw=output/'diamond_output/DIAMOND_RESULTS.tsv'
 defaults={n:getattr(DefaultValues,n)for n in('DIAMOND_QUERY_COVER','DIAMOND_SUBJECT_COVER','DIAMOND_PERCENT_ID','DIAMOND_EVALUE')};argv=build_argv(binary,query,raw,database,working,defaults)
 if defaults!={'DIAMOND_QUERY_COVER':80,'DIAMOND_SUBJECT_COVER':80,'DIAMOND_PERCENT_ID':30,'DIAMOND_EVALUE':1e-5}:raise RuntimeError('Original scientific defaults differ')
 no_models();origins={name:str(Path(module.__file__).resolve())for name,module in list(sys.modules.items())if name.startswith('checkm2.')and getattr(module,'__file__',None)}
 if any(not Path(v).is_relative_to(prefix)for v in origins.values()):raise RuntimeError('Author module origin outside accepted prefix')
 c.save(c.path(a.output).with_name('search_exec_prepared.json'),{'status':'PREPARED_QUERY_AND_EXACT_ARGV_PENDING_ACTUAL_SEARCH_EXIT','request_sha256':a.request_sha256,'accession':acc,'query':c.row(query),'argv':argv,'database':request['database'],'diamond_binary':request['diamond_binary'],'selected_faa':request['selected_faa'],'original_author_sources':recipe['author_sources'],'actual_author_origins':origins,'actual_PATH':os.environ['PATH'],'actual_diamond_resolution':str(binary),'original_DiamondRunner_executed':False,'author_query_and_argv_equivalence_review_required':True,'no_model_modules':no_models(),'producer_pid_before_exec':os.getpid(),'resource_policy':'Same observed process group and unchanged RSS gate; exec removes the producer Python address space rather than relocating it.'})
 if c.sha(c.path(a.request))!=a.request_sha256:raise RuntimeError('Request changed before exec')
 os.execve(str(binary),argv,dict(os.environ))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--request',required=True);p.add_argument('--request-sha256',required=True);p.add_argument('--output',required=True);main(p.parse_args())
