"""P20 own-FAA full-feature validation. Scientific body retained from accepted S1R2."""
from pathlib import Path
import argparse,hashlib,json,math,os,struct,sys
import checkm2_saved_stock_recovery_v001 as c
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
 plan,context,protocol=c.feature_context(request);item=context['input'] if 'input'in context else context.get('item')
 # The saved context's exact original scientific recipe owns this specimen.
 item=next(x for x in c.read(c.bind(plan['scientific_recipe']))['inputs']if x['accession']==c.ACC)
 artifacts=request['artifacts'];search=c.read(c.bind(artifacts['diamond_receipt']))
 if search.get('index_chunks')!=8 or search.get('block_size')!=.5 or search.get('threads')!=1 or search.get('actual_search_exit_observed_by_unit_owner')!=0 or search.get('actual_binary_execution')!=artifacts['diamond_unit_execution']:raise RuntimeError('Saved explicit index8 actual binary0 required')
 faa=c.bind(artifacts['selected_faa']);proteins=h.parse_fasta(faa.read_text(),h.AA)
 actual=fresh.validate_diamond(c.bind(search['raw_diamond']),c.ACC,{x['id']for x in proteins})
 if actual!=search['raw_diamond']or actual['rows']<=0:raise RuntimeError('Saved full-field raw search differs or no reported hits; no negative call')
 resume=c.path(request['resume_output']);fresh.exact_faa_inventory(resume/'protein_files',c.ACC,artifacts['selected_faa']['sha256'])
 copied={**search['raw_diamond'],'path':(resume/'diamond_output/DIAMOND_RESULTS.tsv').relative_to(c.R).as_posix()}
 fresh.exact_diamond_inventory(resume/'diamond_output',copied)
 if c.path(artifacts['raw_pickle']['path'])!=resume/'feature_vectors_1.pkl'or c.path(artifacts['quality_report']['path'])!=resume/'quality_report.tsv':raise RuntimeError('New own stock output join differs')
 schema_path=c.bind(request['schema'])
 if c.sha(schema_path)!=SCHEMA_SHA:raise RuntimeError('Corrected feature schema differs')
 schema=c.read(schema_path);assets={}
 for item in schema['source_files_and_assets']:
  p=c.path(item['runtime_project_relative_path'])
  if p.stat().st_size!=item['bytes']or c.sha(p)!=item['sha256']:raise RuntimeError('Original runtime model-input source/JSON differs')
  if p.suffix=='.json':assets[p.name]=c.read(p)
 item=next(x for x in c.read(c.bind(plan['scientific_recipe']))['inputs']if x['accession']==c.ACC)
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
    if (annotation.get('status') != 'ORIGINAL_SEQUENTIAL_PRODIGAL_COMPLETED_NOT_GENOME_ACCEPTANCE' or
        annotation.get('source_fna_sha256') != item['fasta_sha256'] or annotation.get('faa_sha256') != v.sha(faa) or
        annotation.get('original_source_sha256') != CALLER_SHA or annotation.get('prodigal_program_sha256') != v.sha(prefix / 'bin/prodigal') or
        annotation.get('ML_modules_loaded') != [] or annotation.get('interception_or_author_patch') is not False or
        annotation.get('author_deletes_selected_GFF_and_FNA') is not True):
        raise ValueError('Exact original model-free FAA/caller provenance is required')
    if annotation['accession'] != accession or old.sequence_receipt(proteins) != annotation['protein_sequences']:
        raise ValueError('All selected FAA identifiers, headers and sequences must match the original caller receipt')
    joined = ''.join(row['sequence'] for row in proteins)
    expected_aa = [joined.count(name) for name in schema['ordered_model_features'][:20]] + [len(joined), len(proteins)]
    if list(values[0, :22]) != expected_aa:
        raise ValueError('All 22 FAA metadata features are required unchanged')
    measurements = old.validate_author_return(annotation['all10_original_return_values'], accession)
    if measurements != annotation['original_measurements'] or measurements['CDS_count'] != len(proteins):
        raise ValueError('All ten original caller values must agree with their preserved measurement map')
    dna = annotation['independent_DNA_QC']
    if (measurements['total_nucleotide_bases'] != dna['total_bases'] or measurements['contig_count'] != dna['contigs'] or
        measurements['max_contig_length'] != dna['max_contig_length']):raise ValueError('Original and independent DNA sidecars disagree')
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
        'fresh_annotation_unit_execution_sha256': artifacts['annotation_unit_execution']['sha256'],
        'annotation_commit_sha256': artifacts['annotation_commit']['sha256'],
        'annotation_receipt_sha256': artifacts['annotation_receipt']['sha256'],
        'annotation_unit_execution_sha256': artifacts['annotation_unit_execution']['sha256'],
        'independent_DNA_QC': dna, 'all10_original_return_values': annotation['all10_original_return_values'],
        **source_context.measured_row_with_original_P20_context(item, {'raw_report': row, 'Completeness': comp, 'Contamination': cont}),
        'source_pending_reasons':item['source_pending_reasons'],'source_masks':item['source_masks'],
        'scope': 'P20_PHASE_SEPARATED_FEASIBILITY_ONLY_NO_PRODUCTION_GRANT',
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
