"""Compare1/2 already-produced control shards; never run accepted annotation/models/search again."""
import argparse
import checkm2_campaign_index8_common_v003 as c
import checkm2_phase_separated_artifacts_N1 as raw
import checkm2_protein_helpers_v001 as h
from checkm2_campaign_index8_shared_producer_v003 import no_models

def main(a):
 request=c.read(c.path(a.request))
 if c.sha(c.path(a.request))!=a.request_sha256 or request.get('request_schema')!='TREE2_CAMPAIGN_SHARED_CONTROL_REQUEST_V003':raise RuntimeError('Exact control comparison request required')
 plan,recipe,_=c.request_gate(request);shared=c.read(c.bind(request['shared_search_commit']));split=c.read(c.bind(shared['split_commit']));no_models()
 if not c.unit_closed(c.read(c.bind(shared['binary_execution'])))or not c.unit_closed(c.read(c.bind(shared['validation_execution']))):raise RuntimeError('One global successful search/split required')
 matches=[]
 for spec in plan['controls']:
  acc=spec['accession'];shard=next(x for x in split['shards']if x['accession']==acc);proteins=h.parse_fasta(c.bind(spec['selected_faa']).read_text(),h.AA);ids={x['id']for x in proteins}
  actual=raw.validate_diamond(c.bind(shard['artifact']),acc,ids);reference=raw.validate_diamond(c.bind(spec['reference_raw_diamond']),acc,ids)
  if any(actual[k]!=reference[k]for k in('rows','unique_rows','duplicate_rows','multiset_sha256','query_genomes')):raise RuntimeError('Full raw12-field control mismatch; remaining ML remains held')
  matches.append({'accession':acc,'reference':spec['reference_raw_diamond'],'actual_shared_shard':shard['artifact'],'full12field_multiplicity_match':True,'multiset_sha256':actual['multiset_sha256']})
 c.save(c.path(a.output),{'status':'ALL_ACCEPTED_SERIAL_CONTROL_RAW_MULTISET_MATCHES','matches':matches,'shared_search_commit':request['shared_search_commit'],'accepted_annotation_or_model_or_standalone_control_search_replayed':False,'forbidden_model_modules_loaded':no_models(),'scope':'THESE_EXACT_ACCEPTED_SERIAL_INDEX8_CONTROLS_ONLY_NOT_UNIVERSAL_EQUIVALENCE'})
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for name in('request','request-sha256','output'):p.add_argument('--'+name,required=True)
 main(p.parse_args())
