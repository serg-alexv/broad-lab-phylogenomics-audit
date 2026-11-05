"""Bounded source-only preparation after a closed RSS failure; never starts science."""
from pathlib import Path
import argparse,ast,ctypes,gzip,json,os,shlex,shutil,sys,time,traceback,types
from functools import reduce
import local_tree2_dispatcher as b
import checkm2_production_preparation_P1 as p
R=Path(__file__).resolve().parents[1];E=R/'evidence/checkm2_phase_separated_P20/resource_exec_source_preparation_v001';W=R/'work/checkm2_P20_resource_exec_preparation_v001';K=b.Windows();OWNER=K.identity(ctypes.c_void_p(-1),os.getpid());START=time.monotonic();BEGAN=b.utc();EVENT='92ad2930fcd513be5cc9b39f74338d3dda74c9269b677c2507376f433b190b10'

PRODUCER=r'''"""HELD source-equivalent author query/argv, then exec the unchanged DIAMOND binary."""
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
'''

VALIDATOR=r'''"""HELD post-search full raw-artifact validation; starts only after observed search0."""
from pathlib import Path
import argparse,sys
import checkm2_P20_resource_repair_common_v001 as c
import checkm2_protein_helpers_v001 as h
import checkm2_phase_separated_artifacts_N1 as artifacts
from checkm2_P20_diamond_exec_producer_v001 import no_models,build_argv
def main(a):
 if a.observed_search_exit_code!=0:raise RuntimeError('Parent shell must observe actual search0')
 request=c.read(c.path(a.request))
 if c.sha(c.path(a.request))!=a.request_sha256:raise RuntimeError('Trusted request changed')
 plan,recipe,authority=c.request_gate(request);h.runtime_required();no_models();prefix=c.path(request['runtime_prefix'])
 if Path(sys.executable).resolve()!=(prefix/'bin/python').resolve():raise RuntimeError('Accepted runtime Python required')
 receipt=c.read(c.path(a.output).with_name('search_exec_prepared.json'))
 if receipt['request_sha256']!=a.request_sha256 or receipt['selected_faa']!=request['selected_faa'] or receipt['database']!=request['database'] or receipt['diamond_binary']!=request['diamond_binary']:raise RuntimeError('Prepared own-query/DB/binary request differs')
 query=c.bind(receipt['query']);faa=c.bind(request['selected_faa']);proteins=h.parse_fasta(faa.read_text(),h.AA);acc=request['accession'];output=c.path(request['resume_output'])
 defaults={'DIAMOND_QUERY_COVER':80,'DIAMOND_SUBJECT_COVER':80,'DIAMOND_PERCENT_ID':30,'DIAMOND_EVALUE':1e-5};expected=build_argv(c.bind(request['diamond_binary']),query,output/'diamond_output/DIAMOND_RESULTS.tsv',c.path(request['database']['path']),c.path(request['durable_scratch'])/'diamond_work',defaults)
 if receipt['argv']!=expected or receipt['no_model_modules']!=[]:raise RuntimeError('Exact original scientific argv/no-model provenance differs')
 raw=artifacts.validate_diamond(output/'diamond_output/DIAMOND_RESULTS.tsv',acc,{x['id']for x in proteins})
 if raw['rows']<=0:raise RuntimeError('Unannotated search is unavailable, never a negative')
 artifacts.exact_diamond_inventory(output/'diamond_output',raw);no_models()
 c.save(c.path(a.output),{'status':'P20_ORIGINAL_DIAMOND_ARTIFACTS_VALIDATED_PENDING_UNIT_CLOSURE','accession':acc,'request_sha256':a.request_sha256,'selected_faa':request['selected_faa'],'annotation_receipt':request['annotation_receipt'],'database':request['database'],'diamond_binary':request['diamond_binary'],'raw_diamond':raw,'forbidden_model_modules_loaded':no_models(),'actual_author_origins':receipt['actual_author_origins'],'actual_PATH':receipt['actual_PATH'],'actual_diamond_resolution':receipt['actual_diamond_resolution'],'block_size':0.5,'threads':1,'original_author_source_unchanged':True,'original_DiamondRunner_executed':False,'source_equivalent_author_query_and_full_argv':True,'search_exec_prepared':c.row(c.path(a.output).with_name('search_exec_prepared.json')),'actual_search_exit_observed_by_parent_shell':a.observed_search_exit_code,'ML_prediction_invoked':False,'unit_actual_exit_and_group_closure_pending':True})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--request',required=True);p.add_argument('--request-sha256',required=True);p.add_argument('--output',required=True);p.add_argument('--observed-search-exit-code',type=int,required=True);main(p.parse_args())
'''

def guard():
 if time.monotonic()-START>270 or shutil.disk_usage(R).free<40*1024**3:raise RuntimeError('Source-preparation time/disk bound')
 if any((R/x).exists()for x in('state/STOP','state/STOP_CHECKM2_PILOT')):raise InterruptedError('STOP')
 p.native_rss()
def stage(detail,done,status='RUNNING',terminal=None):
 b.atomic(R/'state/stages/04.json',{'id':'04','name':'Independent biological QC','status':status,'operation':'P20_RESOURCE_EXEC_SOURCE_PREPARATION_ONLY','detail':detail,'done':done,'total':5,'unit':'resource-repair source and review artifacts','pid':OWNER['pid'],'creation_time_utc':OWNER['creation_time_utc'],'windows_creation_filetime_100ns':OWNER['windows_creation_filetime_100ns'],'started_utc':BEGAN,'updated_utc':b.utc(),'log_path':str(E/'stdout.txt'),'terminal_receipt':terminal,'scientific_execution_authorized':False,'production_panel_acceptance':False})
def main(a):
 guard();grant=b.read(b.bind(R,{'path':a.admission,'sha256':a.admission_sha256}));assert grant['status']=='ROOT_ADMITTED_ONE_RESOURCE_EXEC_SOURCE_PREPARATION_ONLY' and grant['event_sha256']==EVENT and grant['scientific_execution_authorized']is False
 for ref in grant['bound_sources_and_evidence']:b.bind(R,ref)
 mask=p.affinity(K);b.exclusive(E/'owner_launch.json',{'native_owner':OWNER,'source':b.row(R,Path(__file__)),'admission':b.row(R,Path(a.admission)),'maximum_seconds':270,'maximum_ACK_wait_seconds':180,'affinity_mask':mask,'no_science_or_runtime_mount':True})
 stage('Preparing source-equivalent exec pipeline; waiting for exact current-namespace ACK',0)
 directory=R/b.read(R/'state/local_continuation_current_runtime.json')['state_directory']
 while True:
  guard()
  try:
   ack=b.read(directory/'early_attach_ack.json')
   if ack.get('event_sha256')==EVENT and ack.get('exact_handle_retained')is True and all(ack['worker'].get(k)==v for k,v in OWNER.items()):break
  except FileNotFoundError:pass
  if time.monotonic()-START>180:raise TimeoutError('No exact retained-handle ACK; no source worker replay')
  time.sleep(.25)
 W.mkdir(exist_ok=False);staged=W/'staged';staged.mkdir();fixtures=W/'synthetic_fixtures';fixtures.mkdir();producer=staged/'checkm2_P20_diamond_exec_producer_v001.py';validator=staged/'checkm2_P20_diamond_exec_validate_v001.py';producer.write_bytes(PRODUCER.encode());validator.write_bytes(VALIDATOR.encode());compile(PRODUCER,str(producer),'exec');compile(VALIDATOR,str(validator),'exec')
 root='/mnt/c/'+str(R)[3:].replace('\\','/');shell=staged/'checkm2_P20_diamond_exec_phase_v001.sh';body='#!/bin/bash\nset -euo pipefail\nROOT='+shlex.quote(root)+'\nPREFIX="$1"\nREQUEST="$2"\nREQUEST_SHA="$3"\nOUTPUT="$4"\nset +e\n"$PREFIX/bin/python" -B "$ROOT/scripts/checkm2_P20_diamond_exec_producer_v001.py" --request "$REQUEST" --request-sha256 "$REQUEST_SHA" --output "$OUTPUT"\nsearch_exit=$?\nset -e\nif [[ "$search_exit" -ne 0 ]]; then exit "$search_exit"; fi\nexec "$PREFIX/bin/python" -B "$ROOT/scripts/checkm2_P20_diamond_exec_validate_v001.py" --request "$REQUEST" --request-sha256 "$REQUEST_SHA" --output "$OUTPUT" --observed-search-exit-code "$search_exit"\n';shell.write_bytes(body.encode());assert b'\r'not in shell.read_bytes();stage('Three held source files written; checking exact author query and scientific argv',3)
 source=R/'tools/checkm2_runtime_pkgs/checkm2-1.1.0-pyhdfd78af_2/site-packages/checkm2';author=source/'diamond.py';seq=source/'sequenceClasses.py';defaults_source=source/'defaultValues.py';refs={Path(x['path']).name:x for x in grant['author_sources']}
 for f in(author,seq,defaults_source):assert b.digest(f)==refs[f.name]['sha256']
 defaults={}
 for node in ast.walk(ast.parse(defaults_source.read_text())):
  if isinstance(node,ast.Assign)and len(node.targets)==1 and isinstance(node.targets[0],ast.Name)and node.targets[0].id in('DIAMOND_QUERY_COVER','DIAMOND_SUBJECT_COVER','DIAMOND_PERCENT_ID','DIAMOND_EVALUE','DIAMOND_HEADER_SEPARATOR'):defaults[node.targets[0].id]=ast.literal_eval(node.value)
 fn=next(x for x in ast.parse(PRODUCER).body if isinstance(x,ast.FunctionDef)and x.name=='build_argv');namespace={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'<pure-new-argv>','exec'),namespace)
 author_tree=ast.parse(author.read_text());command=next(n.value for n in ast.walk(author_tree)if isinstance(n,ast.Assign)and any(isinstance(x,ast.Name)and x.id=='cmd'for x in n.targets));example={'temp_diamond_input':types.SimpleNamespace(name='/project/query.faa'),'diamond_output':'/project/DIAMOND_RESULTS.tsv','self':types.SimpleNamespace(threads=1,diamond_location='/project/accepted_db.dmnd',blocksize=.5),'DefaultValues':types.SimpleNamespace(**defaults),'diamond_working_dir':types.SimpleNamespace(name='/project/scratch')};expected=shlex.split(eval(compile(ast.Expression(body=command),'<pinned-author-format-only>','eval'),example));actual=namespace['build_argv']('diamond','/project/query.faa','/project/DIAMOND_RESULTS.tsv','/project/accepted_db.dmnd','/project/scratch',defaults);assert actual==expected
 klass=next(x for x in ast.parse(seq.read_text()).body if isinstance(x,ast.ClassDef)and x.name=='SeqReader');ns={'gzip':gzip};exec(compile(ast.Module(body=[klass],type_ignores=[]),'<pinned-author-sequence-fixture-only>','exec'),ns);reader=ns['SeqReader']()
 concatenator=next(x for x in ast.walk(author_tree)if isinstance(x,ast.FunctionDef)and x.name=='__concatenate_proteins');scope={'os':os,'reduce':reduce,'sequenceClasses':types.SimpleNamespace(SeqReader=ns['SeqReader'])};exec(compile(ast.Module(body=[concatenator],type_ignores=[]),'<pinned-author-concat-fixture-only>','exec'),scope)
 fixture=fixtures/'GCF_000000001.1.faa';fixture.write_text('>p1 description\nMACK\n>p2 another header\nTVWY\n',encoding='utf-8');old_sequences=scope['__concatenate_proteins'](types.SimpleNamespace(separator=defaults['DIAMOND_HEADER_SEPARATOR']),[str(fixture)]);parsed=reader.read_nucleotide_sequences(str(fixture));new_sequences=dict(('{}{}{}'.format(fixture.stem,defaults['DIAMOND_HEADER_SEPARATOR'],k),v)for k,v in parsed.items());assert old_sequences==new_sequences
 x=fixtures/'author_query.faa';y=fixtures/'exec_query.faa';reader.write_fasta(old_sequences,str(x));reader.write_fasta(new_sequences,str(y));assert x.read_bytes()==y.read_bytes();stage('Exact full author argv and query-byte fixtures passed; writing bounded repair review',4)
 output={'schema':'TREE2_P20_DIAMOND_EXEC_SOURCE_PREPARATION_V001','status':'HELD_SOURCE_READY_REQUIRES_ROOT_REVIEW_FRESH_PREFLIGHT_AND_NEW_ADMISSION','at_utc':b.utc(),'new_sources':[b.row(R,z)for z in(producer,validator,shell)],'author_sources':[refs[f.name]for f in(author,seq,defaults_source)],'exact_full_author_argv_fixture_equal':True,'exact_author_query_dictionary_and_writer_bytes_equal':True,'synthetic_fixture_only_no_actual_FAA_query_generated':True,'scientific_defaults':defaults,'block_size':.5,'threads':1,'observed_failed_group_peak_bytes':2149838848,'RSS_ceiling_bytes':2147483648,'observed_wrapper_RSS_bytes':27639808,'observed_DIAMOND_RSS_bytes':2120290304,'resource_hypothesis':'Remove the co-resident producer Python address space with exec; a small shell waits, then is replaced by the post-validator only after search finishes. All members remain in the same observed group. The RSS gate and scientific argv/query are unchanged. Future DIAMOND peak remains unproven; allow at most one explicitly reviewed repaired-unit attempt.','no_PSS_substitution_or_process_relocation':True,'new_runtime_common_and_recovery_inner_validator_NOT_YET_IMPLEMENTED':True,'required_future_module':'checkm2_P20_resource_repair_common_v001','required_recovery_contract':'Reuse GCF_002993975.1 annotation0 without replay; carry its36.038043572s and failed DIAMOND110.389590322s, first saved row43.283077190s and original340.575203s. Failed DIAMOND may use only remaining489.610409678s of original600. Reconcile all partial phase/source bindings before stock resume or full-feature validation, then18untouched inputs in reserved order. Preserve first accepted row and existing registry. New source-specific Root admission and source-pinned detached worker required.','bound_failed_queue_authority':grant['failed_queue_authority'],'bound_repair_proposal':grant['repair_proposal'],'scientific_execution_authorized':False,'runtime_mount_model_caller_DIAMOND_or_pickle_invoked':False,'bash_n_and_direct_env_probe_still_required_before_actual_shell_admission':True,'source_preparation_owner':OWNER,'native_exit':'NOT_YET_OBSERVABLE_BY_SELF','elapsed_seconds':time.monotonic()-START}
 guard();b.exclusive(E/'result.json',output);stage('Source-equivalent memory-lifetime repair prepared; fresh Root review/admission required',5,'WAITING_REVIEW',b.row(R,E/'result.json'));print(json.dumps({'status':output['status'],'result':b.row(R,E/'result.json'),'native_owner':OWNER}),flush=True)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--admission',required=True);a.add_argument('--admission-sha256',required=True);args=a.parse_args()
 try:main(args)
 except BaseException as error:
  b.exclusive(E/'FAILED.json',{'status':'RESOURCE_EXEC_SOURCE_PREPARATION_FAILED_NO_AUTOMATIC_RETRY','native_owner':OWNER,'error':repr(error),'traceback':traceback.format_exc(),'no_science_or_runtime_mount':True,'at_utc':b.utc()});stage('Source preparation held: '+repr(error),0,'FAILED',b.row(R,E/'FAILED.json'));raise
