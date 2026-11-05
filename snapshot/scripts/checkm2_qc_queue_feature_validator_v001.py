"""P20 own-FAA full-feature validation. Scientific body retained from accepted S1R2."""
from pathlib import Path
import argparse,hashlib,json,math,os,struct,sys
import checkm2_qc_queue_common_v001 as c
import checkm2_posthoc_v002_validator as v
import checkm2_membership_recompute_v002 as membership
import checkm2_protein_helpers_v001 as h
import checkm2_benchmark10_feature_validator_v002 as b
import checkm2_P20_metadata_ABI_projector_repair_v001 as source_context
import checkm2_phase_separated_artifacts_N1 as fresh
CALLER_SHA='4d962b423281b81edf3e9eec7ce3219388a0df8ae52c13cde883419826592b6f'
SCHEMA_SHA='90e482515c6924386a888aa14a036f7659acf9ad0c49814cb08a3a7e1f76f5ee'

def read_request(request_path,expected_sha):
 if v.sha(request_path)!=expected_sha:raise RuntimeError('P20 trusted feature request hash differs')
 return v.read(request_path)

def preflight(request):
 if request.get('request_schema')!='TREE2_CAMPAIGN_SHARED_ROW_FEATURE_REQUEST_V003':raise RuntimeError('Shared-search own-row feature request schema differs')
 plan,recipe,protocol=c.request_gate(request);item=recipe['input'];acc=item['accession']
 if request.get('accession')!=acc or request.get('scientific_recipe')!=plan['scientific_recipe'] or request.get('schema')!=plan['feature_schema']:raise RuntimeError('Shared-search own input/recipe/schema differs')
 artifacts=request.get('artifacts',{})
 expected={'raw_pickle','selected_faa','annotation_receipt','annotation_unit_execution','annotation_commit','quality_report','quality_unit_execution','shared_search_commit','global_search_execution','global_search_validation_execution','split_commit','raw_shard'}
 if set(artifacts)not in(expected,expected|{'batch_prediction_commit','batch_projection_commit','batch_projection_execution'}):raise RuntimeError('Shared-search required artifact set differs; no per-row search execution is invented')
 for artifact in artifacts.values():v.bind(artifact)
 if not c.annotation_execution_closed(v.read(v.bind(artifacts['annotation_unit_execution']))):raise RuntimeError('Original actual uniform annotation0 required')
 for key in ('quality_unit_execution','global_search_execution','global_search_validation_execution'):
  if not c.unit_closed(v.read(v.bind(artifacts[key]))):raise RuntimeError('Actual typed own annotation/quality and global search/validation0/group closure required')
 annotation_commit=v.read(v.bind(artifacts['annotation_commit']))
 if annotation_commit!=c.annotation_reuse_gate(plan,acc,item):raise RuntimeError('Own exact original uniform annotation/cache provenance differs')
 if 'batch_prediction_commit'in artifacts:c.batch_projection_gate(plan,request,artifacts)
 shared=v.read(v.bind(artifacts['shared_search_commit']))
 if shared.get('status')!='GLOBAL_SHARED_SEARCH_SPLIT_VALIDATED_PENDING_CONTEXT_CLOSURE' or shared.get('binary_execution')!=artifacts['global_search_execution'] or shared.get('validation_execution')!=artifacts['global_search_validation_execution'] or shared.get('split_commit')!=artifacts['split_commit']:raise RuntimeError('One global search/validation/split authority differs')
 # The common gate binds the exact merged request, selected FAA/query inventory,
 # original DB/binary/options, one global debit and this own split-commit member.
 # Controls can remain pending here: this first own row is still not Root accepted.
 shard=c.global_commit_gate(plan,request,artifacts)
 if shard.get('accession')!=acc or shard.get('artifact')!=artifacts['raw_shard']:raise RuntimeError('Own global-query shard association differs')
 faa=v.bind(artifacts['selected_faa']);proteins=h.parse_fasta(faa.read_text(),h.AA)
 actual=fresh.validate_diamond(v.bind(artifacts['raw_shard']),acc,{x['id']for x in proteins})
 if any(actual[k]!=artifacts['raw_shard'][k]for k in ('path','sha256','bytes')):raise RuntimeError('Own full12-field shard identity differs')
 if actual['rows']<=0:raise RuntimeError('Successful shared search has no reported hits for this input; QC is held, never a biological negative')
 if actual.get('query_genomes')!=[acc]:raise RuntimeError('Own shard query genome differs')
 resume=c.path(request['resume_output']);fresh.exact_faa_inventory(resume/'protein_files',acc,artifacts['selected_faa']['sha256'])
 copied=c.row(resume/'diamond_output/DIAMOND_RESULTS.tsv')
 if any(copied[k]!=artifacts['raw_shard'][k]for k in ('sha256','bytes')):raise RuntimeError('Stock resume copy differs from its exact global shard bytes')
 fresh.exact_diamond_inventory(resume/'diamond_output',copied)
 schema_path=v.bind(request['schema'])
 if v.sha(schema_path)!=SCHEMA_SHA:raise RuntimeError('Corrected feature schema differs')
 schema=v.read(schema_path);assets={}
 for row in schema['source_files_and_assets']:
  path=v.inside(row['runtime_project_relative_path'])
  if path.stat().st_size!=row['bytes'] or v.sha(path)!=row['sha256']:raise RuntimeError('Original runtime source/JSON asset differs')
  if path.suffix=='.json':assets[path.name]=v.read(path)
 return schema,assets,item,protocol

def main(args):
    request_path = v.inside(args.request)
    request = read_request(request_path, args.request_sha256)
    schema, assets, item, protocol = preflight(request)
    v.no_models()
    if (os.environ.get('TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED') != '1' or
        os.environ.get('TREE2_PRIVATE_NAMESPACE_VERIFIED') != '1'):
        raise RuntimeError('Accepted private read-only runtime is required')
    prefix = v.inside(request['runtime_prefix'])
    if Path(sys.executable).resolve() != (prefix / 'bin/python').resolve():
        raise RuntimeError('Single-FAA feature validation is outside the accepted Python prefix')
    output = v.inside(args.output)
    if output.exists():
        raise RuntimeError('Refusing to overwrite a single-FAA feature receipt')
    import numpy as np
    import pandas as pd
    if (sys.version_info[:3] != (3, 12, 16) or np.__version__ != '2.5.4' or
        pd.__version__ != '3.1.0' or not Path(np.__file__).resolve().is_relative_to(prefix) or
        not Path(pd.__file__).resolve().is_relative_to(prefix)):
        raise RuntimeError('Pinned accepted Python, NumPy or pandas version/origin differs')
    v.no_models()
    artifacts = request['artifacts']
    pickle_path = v.bind(artifacts['raw_pickle'])
    frame = pd.read_pickle(pickle_path)
    values = v.validate_domains(schema, frame, np)
    accession = request['accession']
    if frame.iloc[0, 0] != accession:
        raise ValueError('Single-FAA feature accession/version differs')
    import checkm2_protein_helpers_v001 as old
    faa = v.bind(artifacts['selected_faa'])
    if faa.name != accession + '.faa':raise ValueError('Exact versioned supplied FAA basename is required')
    proteins = old.parse_fasta(faa.read_text(), old.AA)
    annotation = v.read(v.bind(artifacts['annotation_receipt']))
    if annotation.get('schema') != 'TREE2_PROVISIONAL_UNIFORM_ANNOTATION_ROW_V001' or annotation.get('accession') != accession:
        raise ValueError('Genuine own closed uniform annotation receipt required')
    uniform_plan = c.read(c.PLAN_PATH)
    c.annotation_reuse_gate(uniform_plan, accession, item)
    joined = ''.join(row['sequence'] for row in proteins)
    expected_aa = [joined.count(name) for name in schema['ordered_model_features'][:20]] + [len(joined), len(proteins)]
    if list(values[0, :22]) != expected_aa:
        raise ValueError('All 22 FAA metadata features are required unchanged')
    dna = {'source_FNA': annotation['fingerprint']['source_FNA'], 'coordinate_integrity': annotation['coordinate_integrity'], 'uniform_annotation_authority': uniform_plan['uniform_annotation_authority'], 'legacy_ten_return_values': 'NOT_COLLECTED_NOT_SYNTHESIZED'}
    from checkm2_membership_recompute_v002 import recompute_membership_features
    counts = {name: frame[name].iloc[0] for name in schema['ordered_model_features'][22:20021]}
    expected = recompute_membership_features(counts, assets['feature_ordering.json'],
                                             assets['kegg_path_category_mapping.json'], assets['module_definitions.json'])
    names = schema['ordered_model_features'][20021:]
    if list(expected) != names or len(expected) != 1220:
        raise ValueError('Independent membership order/count differs')
    differences = [name for index, name in enumerate(names) if float(values[0, 20021 + index]) != expected[name]]
    if differences:
        raise ValueError('Independent membership recomputation differs: ' + repr(differences[:10]))
    row, comp, cont = old.parse_protein_report(v.bind(artifacts['quality_report']), accession)
    for artifact in artifacts.values():
        v.bind(artifact)
    if v.sha(request_path) != args.request_sha256:
        raise RuntimeError('Single-FAA feature request changed during validation')
    v.no_models()
    canonical = np.asarray(values, dtype='<f8', order='C')
    result = {
        'status': 'P20_FEATURES_PASS_PENDING_NATIVE_CLOSURE',
        'row_count': 1, 'scientific_recipe_sha256': request['scientific_recipe']['sha256'],
        'original_uniform_annotation_unit_execution_sha256': artifacts['annotation_unit_execution']['sha256'],
        'annotation_commit_sha256': artifacts['annotation_commit']['sha256'],
        'annotation_receipt_sha256': artifacts['annotation_receipt']['sha256'],
        'annotation_unit_execution_sha256': artifacts['annotation_unit_execution']['sha256'],
        'independent_DNA_QC': dna, 'legacy_ten_return_values': 'NOT_COLLECTED_NOT_SYNTHESIZED', 'uniform_annotation_receipt': artifacts['annotation_receipt'],
        **c.own_source_projection(item, {'raw_report': row, 'Completeness': comp, 'Contamination': cont}),
        'source_pending_reasons':item['source_pending_reasons'],'source_masks':item['source_masks'],
        'scope': 'CONTINUOUS_QUEUE_OWN_ROW_ESTIMATE_PENDING_CONTEXT_CLOSURE_NO_PANEL_GRANT',
        'accession': accession, 'Completeness': comp, 'Contamination': cont,
        'raw_author_protein_report_row': row, 'request_sha256': args.request_sha256,
        'input_plan_sha256': request['input_plan']['sha256'],
        'source_manifest_sha256': request['source_manifest']['sha256'],
        'protocol_admission_sha256': request['protocol_admission']['sha256'],
        'quality_unit_execution_sha256': artifacts['quality_unit_execution']['sha256'],
        'raw_pickle_sha256': v.sha(pickle_path), 'schema_v002_sha256': SCHEMA_SHA,
        'source_FAA_sha256': v.sha(faa), 'ordered_dataframe_columns_sha256': v.canonical(list(frame.columns)),
        'dataframe_shape': list(frame.shape), 'actual_ML_cast_dtype': str(values.dtype),
        'canonical_float64_le_row_sha256': hashlib.sha256(canonical.tobytes()).hexdigest(),
        'finite_domain_features': 21241, 'exact_FAA_metadata_features': 22,
        'independently_recomputed_membership_features': 1220, 'membership_mismatches': 0,
        'membership_comparison': 'EXACT_FLOAT64_EQUALITY_NO_TOLERANCE_NO_CLIPPING',
        'forbidden_model_modules_loaded': v.no_models(),
        'genomes_or_FAA_generated_by_validator': 0, 'annotation_DIAMOND_or_ML_runs_by_validator': 0,
        'nucleotide_numeric_equivalence_measured': False, 'production_acceptance': 'NOT_GRANTED',
    }
    c.batch_feature_result_gate(request, result)
    v.save(output, result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', required=True)
    parser.add_argument('--request-sha256', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        main(args)
    except BaseException as error:
        v.save(v.inside(args.output).with_name('phase_separated_feature_validation_failure_P20.json'),
               {'status': 'SINGLE_FAA_FEATURE_VALIDATION_FAILED_OR_UNRESOLVED', 'error': repr(error),
                'validator_calls_no_annotation_DIAMOND_or_ML': True})
        raise
