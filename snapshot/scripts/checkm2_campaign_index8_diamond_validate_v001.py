"""HELD post-search full raw-artifact validation; starts only after observed search0."""
from pathlib import Path
import argparse,sys
import checkm2_campaign_index8_common_v001 as c
import checkm2_protein_helpers_v001 as h
import checkm2_phase_separated_artifacts_N1 as artifacts
from checkm2_campaign_index8_diamond_producer_v001 import no_models,build_argv
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
 c.save(c.path(a.output),{'status':'P20_ORIGINAL_DIAMOND_ARTIFACTS_VALIDATED_PENDING_UNIT_CLOSURE','accession':acc,'request_sha256':a.request_sha256,'selected_faa':request['selected_faa'],'annotation_receipt':request['annotation_receipt'],'database':request['database'],'diamond_binary':request['diamond_binary'],'raw_diamond':raw,'forbidden_model_modules_loaded':no_models(),'actual_author_origins':receipt['actual_author_origins'],'actual_PATH':receipt['actual_PATH'],'actual_diamond_resolution':receipt['actual_diamond_resolution'],'block_size':0.5,'threads':1,'original_author_source_unchanged':True,'original_DiamondRunner_executed':False,'source_equivalent_author_query_and_full_argv':False,'author_query_and_original_base_argv_unchanged':True,'resource_method_amendment':plan['method_amendment'],'index_chunks':8,'search_exec_prepared':c.row(c.path(a.output).with_name('search_exec_prepared.json')),'actual_search_exit_observed_by_parent_shell':a.observed_search_exit_code,'ML_prediction_invoked':False,'unit_actual_exit_and_group_closure_pending':True})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--request',required=True);p.add_argument('--request-sha256',required=True);p.add_argument('--output',required=True);p.add_argument('--observed-search-exit-code',type=int,required=True);main(p.parse_args())
