"""Full raw12-field multiset comparison only; never annotation/model import."""
import argparse
import checkm2_campaign_index8_common_v002 as c
import checkm2_phase_separated_artifacts_N1 as artifacts
import checkm2_protein_helpers_v001 as h
from checkm2_campaign_index8_diamond_producer_v002 import no_models

def main(a):
 request=c.read(c.path(a.request))
 if c.sha(c.path(a.request))!=a.request_sha256:raise RuntimeError('Exact trusted control request required')
 plan,recipe,_=c.request_gate(request);spec=plan['search_only_control'];no_models()
 receipt=c.read(c.path(a.output));proteins=h.parse_fasta(c.bind(spec['selected_faa']).read_text(),h.AA);ids={x['id']for x in proteins}
 observed=artifacts.validate_diamond(c.bind(receipt['raw_diamond']),spec['accession'],ids);reference=artifacts.validate_diamond(c.bind(spec['reference_raw_diamond']),spec['accession'],ids)
 if any(observed[k]!=reference[k]for k in('rows','unique_rows','duplicate_rows','multiset_sha256','query_genomes')):raise RuntimeError('Complete real-reference raw12-field multiset mismatch; no rounding/filter/dedup permitted')
 c.save(c.path(a.output).with_name('reference_comparison.json'),{'status':'EXACT_FULL12_FIELD_REFERENCE_MULTISET_MATCH','accession':spec['accession'],'reference':spec['reference_raw_diamond'],'actual':receipt['raw_diamond'],'forbidden_model_modules_loaded':no_models(),'annotation_or_accepted_prediction_replayed':False,'scope':'THIS_EXACT_REFERENCE_QUERY_AND_DB_ONLY_NOT_UNIVERSAL_EQUIVALENCE'})
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for arg in('request','request-sha256','output'):p.add_argument('--'+arg,required=True)
 main(p.parse_args())
