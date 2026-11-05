"""HELD S1R2 fresh-target saved-feature validator; no caller, DIAMOND or model calls.
Derived from accepted cc9b single-row math with exact-ten annotation/source gates.
Scientific imports and one owned unpickle occur only after all bound prerequisites.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re
import os
import sys

R = Path(__file__).resolve().parents[1]
ACCEPTED_VALIDATOR_SHA = 'c820c9d9c9e5e86343f7a80f8fc853ae8dfb1684779ca9f0ef218973e95a01ff'
SCHEMA_SHA = '90e482515c6924386a888aa14a036f7659acf9ad0c49814cb08a3a7e1f76f5ee'
CONTRACT_SHA = 'cf4102adf0399294c35b25ca53a113c74bc9470718cb467249cc9c2deaa8b598'
RECIPE_SHA = '2e003f02e6b1886ebe65c4e4d7a9351d84e6ad404d09384ece668089ba3f5fce'
CALLER_SHA = '4d962b423281b81edf3e9eec7ce3219388a0df8ae52c13cde883419826592b6f'
BENCHMARK_VALIDATOR_SHA = '221c04021d718960c7b736a5255c48bb5f7792e980ae512f2a6ef463ddcd933b'
if hashlib.sha256((R / 'scripts/checkm2_posthoc_v002_validator.py').read_bytes()).hexdigest() != ACCEPTED_VALIDATOR_SHA:
    raise RuntimeError('Accepted unchanged feature-validator dependency differs')
import checkm2_posthoc_v002_validator as v
if v.sha(R / "scripts/checkm2_benchmark10_feature_validator_v002.py") != BENCHMARK_VALIDATOR_SHA:
    raise RuntimeError("Unchanged source/hold projection dependency differs")
import checkm2_benchmark10_feature_validator_v002 as b


def read_request(path, expected_sha):
    path = v.inside(path)
    if v.sha(path) != expected_sha:
        raise RuntimeError('Single-FAA feature request SHA256 differs before any unpickle')
    request = v.read(path)
    if request.get('request_schema') != 'TREE2_SINGLE_FAA_FEATURE_REQUEST_S1R2':
        raise RuntimeError('Wrong control feature request schema')
    return request


def closed_quality_unit(execution):
    if (execution.get('status') != 'UNIT_EXIT0_GROUP_CLOSED' or
        type(execution.get('exit_code')) is not int or execution['exit_code'] != 0 or
        execution.get('owned_group_empty') is not True or
        execution.get('remaining_owned_processes') != []):
        raise RuntimeError('Stock protein-quality unit is not observed exit zero and group closed')


def annotation_authority(request, protocol, contract, expected):
    if protocol['annotation_reuse_authority']['sha256'] != contract['annotation_reuse_authority']['sha256']:
        raise RuntimeError('Exact accepted root annotation-only authority differs')
    authority = v.read(v.bind(protocol['annotation_reuse_authority']))
    if (authority.get('status') != 'ACCEPTED_TEN_ANNOTATIONS_AFTER_FAILED_T1_QUALITY_FOR_S1_PREPARATION' or
        authority.get('annotation_reuse_authorized') is not True or
        authority.get('prediction_execution_authorized') is not False or
        authority.get('whole_ten_quality_or_resource_benchmark_passed') is not False or
        authority.get('production_or_taxonomy_or_panel_acceptance') is not False):
        raise RuntimeError('Root annotation-only authority is required; failed T1 is not a QC pass')
    commits = authority.get('accepted_annotation_commit_sha256s')
    if not isinstance(commits, dict) or set(commits) != set(expected):
        raise RuntimeError('Exact ten accepted annotation commit hashes are required')
    if authority['failed_quality_unit']['sha256'] != contract['failed_T1_quality_unit']['sha256']:
        raise RuntimeError('Actual failed quality unit/debit differs')
    failed = v.read(v.bind(authority['failed_quality_unit']))
    v.bind(authority['failure_closure'])
    if (failed.get('failure_kind') != 'RESOURCE' or failed.get('exit_code') != -15 or
        failed.get('owned_group_empty') is not True or failed.get('remaining_owned_processes') != [] or
        failed.get('elapsed_seconds') != contract['prior_failed_quality_elapsed_seconds']):
        raise RuntimeError('Failed quality resource/exit/group/actual elapsed proof differs')
    # Original outer native exit can remain UNKNOWN; this is annotation-only reuse.
    artifacts = request['artifacts']; accession = request['accession']
    if commits[accession] != artifacts['annotation_commit']['sha256']:
        raise RuntimeError('This exact original annotation commit is not accepted for reuse')
    commit = v.read(v.bind(artifacts['annotation_commit']))
    if commit.get('status') != 'ANNOTATION_EXIT0_VALIDATED_ATOMIC_COMMIT':
        raise RuntimeError('Uncommitted partial annotation cannot become an accepted input')
    for committed, supplied in (('selected_faa', 'selected_faa'),
                               ('annotation_receipt', 'annotation_receipt'),
                               ('unit_execution', 'annotation_unit_execution')):
        v.bind(commit[committed])
        if commit[committed]['sha256'] != artifacts[supplied]['sha256']:
            raise RuntimeError('FAA/annotation/unit differs from accepted original commit')
    return authority


def preflight(request):
    manifest = v.read(v.bind(request['source_manifest']))
    sources = manifest.get('sources')
    if not isinstance(sources, list) or not sources:
        raise RuntimeError('A complete reviewed source manifest is required')
    required = {'scripts/checkm2_single_faa_feature_validator_S1R2.py': v.sha(__file__),
                'scripts/checkm2_posthoc_v002_validator.py': ACCEPTED_VALIDATOR_SHA,
                'scripts/checkm2_benchmark10_feature_validator_v002.py': BENCHMARK_VALIDATOR_SHA,
                'scripts/checkm2_membership_recompute_v002.py': 'e1a0216db7db3716102745f3a78c3ff65f14040601a6cbb6cffb9edc7e4d4efe',
                'scripts/checkm2_protein_helpers_v001.py': '1b04bd9906b19521cd87fc16cfb1a66e0a954f595c83920803f12b05a408baf6'}
    observed = {}
    for row in sources:
        relative = v.bind(row).relative_to(R).as_posix()
        if relative in observed:raise RuntimeError('Duplicate source-manifest entry')
        observed[relative] = row['sha256']
    if any(observed.get(name) != digest for name, digest in required.items()):
        raise RuntimeError('Required unchanged validation dependencies differ')
    contract_path = v.bind(request['cohort_contract'])
    if v.sha(contract_path) != CONTRACT_SHA:raise RuntimeError('Frozen single-FAA cohort/budget contract differs')
    contract = v.read(contract_path)
    recipe_path = v.bind(contract['scientific_recipe'])
    if v.sha(recipe_path) != RECIPE_SHA:raise RuntimeError('Original exact-ten scientific recipe differs')
    recipe = v.read(recipe_path); expected = contract['expected_accessions']
    if expected != recipe['expected_accessions'] or len(expected) != 10 or len(set(expected)) != 10:
        raise RuntimeError('Exact ten original logical inputs are required')
    if contract['expected_source_hold_accessions'] != recipe['expected_ancillary_hold_accessions']:
        raise RuntimeError('Original three source holds differ')
    if request['accession'] not in contract['fresh_target_accessions']:raise RuntimeError('Preserved or unknown accession cannot be recomputed by S1R2')
    item = next(x for x in recipe['inputs'] if x['accession'] == request['accession'])
    protocol = v.read(v.bind(request['protocol_admission']))
    if (protocol.get('schema') != 'TREE2_SINGLE_FAA_INFERENCE_ADMISSION_S1R2' or
        protocol.get('status') != 'ADMITTED_ONE_OPERATIONAL_REPAIR_NINE_FAA_SERIES' or
        protocol.get('role') != 'SINGLE_FAA_INFERENCE_ONLY_METHOD_QC_S1R2' or
        protocol.get('single_faa_execution_authorized') is not True or
        protocol.get('phase') not in ('RUN_FRESH_TARGETS',) or
        protocol.get('max_predictions_per_accession') != 1 or
        protocol.get('max_query_genomes_per_prediction') != 1 or
        protocol.get('input_plan_sha256') != request['input_plan_sha256'] or
        protocol.get('source_manifest_sha256') != request['source_manifest']['sha256'] or
        protocol.get('cohort_contract_sha256') != CONTRACT_SHA or protocol.get('limits') != contract['limits']):
        raise RuntimeError('Matching finite single-FAA series root admission is required')
    if not isinstance(request['input_plan_sha256'], str) or not re.fullmatch('[a-f0-9]{64}', request['input_plan_sha256']):
        raise RuntimeError('Exact admitted input-plan SHA256 is required')
    for gate in ('preserved_row_reuse_gate_passed', 'explicit_second_attempt_exception',
                 'annotation_reuse_gate_passed', 'prior_failure_context_closed',
                 'monitor_standard_stage04_ready', 'source_math_GO', 'resource_lifecycle_GO'):
        if protocol.get(gate) is not True:raise RuntimeError('Required source/resource/monitor gate is absent: ' + gate)
    if protocol['preserved_row_authority'] != contract['preserved_row_authority']:
        raise RuntimeError('Root preserved-row-only authority differs')
    preserved = v.read(v.bind(protocol['preserved_row_authority']))
    if (preserved.get('schema') != 'TREE2_ROOT_S1_CLOSED_ROW_ONLY_AUTHORITY' or
        preserved.get('method_estimate_reuse_authorized') is not True or
        preserved.get('recalculate_accepted_row_authorized') is not False or
        preserved.get('prediction_execution_authorized') is not False):
        raise RuntimeError('Accepted old row must be reused without new ML')
    artifacts = request['artifacts']
    for name in ('raw_pickle', 'selected_faa', 'annotation_receipt', 'annotation_unit_execution',
                 'annotation_commit', 'quality_report', 'quality_unit_execution'):
        v.bind(artifacts[name])
    member = next(x for x in contract['annotation_members'] if x['accession'] == request['accession'])
    for name in ('selected_faa', 'annotation_receipt', 'annotation_unit_execution', 'annotation_commit'):
        if artifacts[name]['sha256'] != member[name]['sha256']:
            raise RuntimeError('Exact cohort FAA/annotation member binding differs')
    closed_quality_unit(v.read(v.bind(artifacts['annotation_unit_execution'])))
    closed_quality_unit(v.read(v.bind(artifacts['quality_unit_execution'])))
    authority = annotation_authority(request, protocol, contract, expected)
    schema_path = v.bind(request['schema'])
    if v.sha(schema_path) != SCHEMA_SHA:raise RuntimeError('Corrected feature schema differs')
    schema = v.read(schema_path); assets = {}
    for row in schema['source_files_and_assets']:
        path = v.inside(row['runtime_project_relative_path'])
        if path.stat().st_size != row['bytes'] or v.sha(path) != row['sha256']:
            raise RuntimeError('Original runtime source/JSON asset differs')
        if path.suffix == '.json':assets[path.name] = v.read(path)
    return schema, assets, item, protocol


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
        'status': 'SINGLE_FAA_FEATURES_S1R2_PASS_PENDING_NATIVE_CLOSURE',
        'row_count': 1, 'cohort_contract_sha256': CONTRACT_SHA,
        'annotation_reuse_authority_sha256': protocol['annotation_reuse_authority']['sha256'],
        'annotation_commit_sha256': artifacts['annotation_commit']['sha256'],
        'annotation_receipt_sha256': artifacts['annotation_receipt']['sha256'],
        'annotation_unit_execution_sha256': artifacts['annotation_unit_execution']['sha256'],
        'independent_DNA_QC': dna, 'all10_original_return_values': annotation['all10_original_return_values'],
        **b.measured_row_with_original_holds(item, {'raw_report': row, 'Completeness': comp, 'Contamination': cont}),
        'scope': 'SINGLE_FAA_FEATURE_VALIDATION_ONLY_NO_BATCH_SUCCESS_OR_PANEL_GRANT',
        'accession': accession, 'Completeness': comp, 'Contamination': cont,
        'raw_author_protein_report_row': row, 'request_sha256': args.request_sha256,
        'input_plan_sha256': request['input_plan_sha256'],
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
        v.save(v.inside(args.output).with_name('single_faa_feature_validation_failure_S1R2.json'),
               {'status': 'SINGLE_FAA_FEATURE_VALIDATION_FAILED_OR_UNRESOLVED', 'error': repr(error),
                'validator_calls_no_annotation_DIAMOND_or_ML': True})
        raise
