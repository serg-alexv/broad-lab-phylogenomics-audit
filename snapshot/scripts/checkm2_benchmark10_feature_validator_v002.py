"""HELD exact-ten saved-feature validator. No annotation, DIAMOND or model calls."""
from pathlib import Path
import argparse
import copy
import csv
import hashlib
import json
import math
import os
import re
import sys

R = Path(__file__).resolve().parents[1]
ACCEPTED_VALIDATOR_SHA = 'c820c9d9c9e5e86343f7a80f8fc853ae8dfb1684779ca9f0ef218973e95a01ff'
SCHEMA_SHA = '90e482515c6924386a888aa14a036f7659acf9ad0c49814cb08a3a7e1f76f5ee'
ORIGINAL_PLAN_SHA = '4ae7dc8d5dbae740cf5a09bfe152a412cde9007e243860535873e8a473c3a9f1'
STRATEGY_SHA = 'c0c3a2c65e3ba3a7d12d9d0ba2eeb9d600d3df9cf06343dade9e157bca90acdc'
RECIPE_SHA = '2e003f02e6b1886ebe65c4e4d7a9351d84e6ad404d09384ece668089ba3f5fce'
FORMAT_AUTHORITY_SHA = 'db8481172729aee547f00553bdfd5d53360ed2e2968ae2d5430fef5e77fafc6f'
CALLER_SHA = '4d962b423281b81edf3e9eec7ce3219388a0df8ae52c13cde883419826592b6f'
REPORT_COLUMNS = ['Name', 'Completeness', 'Contamination', 'Completeness_Model_Used', 'Additional_Notes']
if hashlib.sha256((R / 'scripts/checkm2_posthoc_v002_validator.py').read_bytes()).hexdigest() != ACCEPTED_VALIDATOR_SHA:
    raise RuntimeError('Accepted unchanged validator dependency differs')
import checkm2_posthoc_v002_validator as v


def exact_names(names, expected, label):
    if (len(expected) != 10 or len(set(expected)) != 10 or len(names) != 10 or
        any(not isinstance(name, str) for name in names) or
        len(set(names)) != 10 or set(names) != set(expected)):
        raise ValueError('Exact ten unique accession Names are required: ' + label)
    return {name: index for index, name in enumerate(names)}


def join_report_rows(fields, rows, expected):
    if fields != REPORT_COLUMNS:
        raise ValueError('Exactly five original protein report columns are required')
    for row in rows:
        if set(row) != set(REPORT_COLUMNS) or any(row[name] is None for name in REPORT_COLUMNS):
            raise ValueError('Extra, missing or unknown report cell')
    exact_names([row['Name'] for row in rows], expected, 'protein report')
    joined = {}
    for row in rows:
        if (not isinstance(row['Completeness_Model_Used'], str) or not row['Completeness_Model_Used'] or
            not isinstance(row['Additional_Notes'], str) or
            isinstance(row['Completeness'], bool) or isinstance(row['Contamination'], bool)):
            raise ValueError('Unknown report model, notes or numeric estimate')
        comp, cont = float(row['Completeness']), float(row['Contamination'])
        if not math.isfinite(comp) or not math.isfinite(cont) or not 0 <= comp <= 100 or cont < 0:
            raise ValueError('Missing or nonfinite report estimates are unresolved, not zero')
        joined[row['Name']] = {'raw_report': dict(row), 'Completeness': comp, 'Contamination': cont}
    return joined


def measured_row_with_original_holds(item, report):
    if report['raw_report']['Name'] != item['accession']:
        raise ValueError('Report/source join must use exact accession, not position')
    original_fields = ('accession', 'species', 'genus', 'family', 'role', 'metadata_qc',
                       'selection_status', 'source_disposition', 'source_holds_preserved',
                       'source_metadata_checkm', 'source_taxonomy_gates')
    return {'accession': item['accession'], 'Completeness': report['Completeness'],
            'Contamination': report['Contamination'], 'raw_author_protein_report_row': report['raw_report'],
            'original_source_context': {name: copy.deepcopy(item[name]) for name in original_fields},
            'source_holds_preserved': copy.deepcopy(item['source_holds_preserved']),
            'source_hold_active': bool(item['source_holds_preserved']),
            'numeric_benchmark_status': 'MEASURED_ONLY_NOT_A_PANEL_PASS',
            'source_taxonomy_acceptance': 'NOT_GRANTED', 'production_acceptance': 'NOT_GRANTED'}


def closed_unit(execution):
    if (execution.get('status') != 'UNIT_EXIT0_GROUP_CLOSED' or
        type(execution.get('exit_code')) is not int or execution['exit_code'] != 0 or
        execution.get('owned_group_empty') is not True or execution.get('remaining_owned_processes') != []):
        raise RuntimeError('An observed exit-zero, empty-group unit receipt is required')


def validation_phase(protocol):
    if protocol.get('phase') not in ('CONTINUE', 'VALIDATE_COMMITTED_BATCH'):
        raise RuntimeError('The first-annotation boundary phase cannot invoke batch feature validation')


def preflight(request):
    if request.get('request_schema') != 'TREE2_BENCHMARK10_FEATURE_REQUEST_V002':
        raise RuntimeError('Wrong benchmark feature request schema')
    manifest = v.read(v.bind(request['source_manifest']))
    sources = manifest.get('sources')
    if not isinstance(sources, list) or not sources:
        raise RuntimeError('Complete reviewed benchmark source manifest is required')
    required = {'scripts/checkm2_benchmark10_feature_validator_v002.py': v.sha(__file__),
                'scripts/checkm2_posthoc_v002_validator.py': ACCEPTED_VALIDATOR_SHA,
                'scripts/checkm2_membership_recompute_v002.py': 'e1a0216db7db3716102745f3a78c3ff65f14040601a6cbb6cffb9edc7e4d4efe',
                'scripts/checkm2_protein_helpers_v001.py': '1b04bd9906b19521cd87fc16cfb1a66e0a954f595c83920803f12b05a408baf6'}
    observed = {}
    for row in sources:
        relative = v.bind(row).relative_to(R).as_posix()
        if relative in observed:
            raise RuntimeError('Duplicate source-manifest entry')
        observed[relative] = row['sha256']
    if any(observed.get(name) != digest for name, digest in required.items()):
        raise RuntimeError('Required benchmark validation dependency is missing or changed')
    recipe_path = v.bind(request['recipe'])
    if v.sha(recipe_path) != RECIPE_SHA:
        raise RuntimeError('Frozen exact-ten recipe differs')
    recipe = v.read(recipe_path)
    original = v.bind(recipe['original_immutable_plan'])
    if v.sha(original) != ORIGINAL_PLAN_SHA or recipe['inputs'] != v.read(original)['inputs']:
        raise RuntimeError('Original cohort inputs, holds or context scores changed')
    if v.sha(v.bind(recipe['source_strategy'])) != STRATEGY_SHA or recipe['bridge_genome_enabled'] is not False:
        raise RuntimeError('Held strategy or no-extra-bridge policy differs')
    expected = recipe['expected_accessions']
    exact_names([item['accession'] for item in recipe['inputs']], expected, 'recipe')
    protocol = v.read(v.bind(request['protocol_admission']))
    if (protocol.get('schema') != 'TREE2_BENCHMARK10_PROTEIN_ADMISSION_V002' or
        protocol.get('status') != 'ADMITTED_ONE_BENCHMARK10_BATCH' or
        protocol.get('role') != 'BENCHMARK10_PROTEIN_METHOD_QC_ONLY' or
        protocol.get('benchmark_execution_authorized') is not True or
        protocol.get('max_batch_prediction_attempts') != 1 or
        protocol.get('input_plan_sha256') != request['input_plan_sha256'] or
        protocol.get('source_manifest_sha256') != request['source_manifest']['sha256'] or
        protocol.get('recipe_sha256') != RECIPE_SHA or protocol.get('limits') != recipe['limits']):
        raise RuntimeError('Matching finite one-batch root admission is required')
    validation_phase(protocol)
    for gate in ('format_control_gate_passed', 'monitor_standard_stage04_ready', 'source_math_GO', 'resource_lifecycle_GO'):
        if protocol.get(gate) is not True:
            raise RuntimeError('Required benchmark prerequisite is not established: ' + gate)
    if protocol['format_control_root_acceptance']['sha256'] != FORMAT_AUTHORITY_SHA:
        raise RuntimeError('Accepted format-method authority differs')
    authority = v.read(v.bind(protocol['format_control_root_acceptance']))
    if (authority.get('status') != 'ACCEPTED_FORMAT_CONTROL_FOR_TEN_GENOME_BENCHMARK_PREPARATION' or
        authority.get('benchmark_execution_authorized') is not False or
        authority.get('production_or_taxonomy_or_panel_acceptance') is not False):
        raise RuntimeError('Format acceptance grants a different scope')
    if protocol['format_control_comparison']['sha256'] != recipe['method_gates']['closed_format_control_comparison']['sha256']:
        raise RuntimeError('Accepted format-comparison binding differs')
    comparison = v.read(v.bind(protocol['format_control_comparison']))
    if comparison.get('status') != 'FORMAT_CONTROL_V002_PASS_CLOSED' or comparison.get('production_panel_acceptance') is not False:
        raise RuntimeError('Closed format-control method prerequisite is absent')
    if not isinstance(request['input_plan_sha256'], str) or not re.fullmatch('[a-f0-9]{64}', request['input_plan_sha256']):
        raise RuntimeError('Exact admitted input-plan SHA256 is required')
    schema_path = v.bind(request['schema'])
    if v.sha(schema_path) != SCHEMA_SHA:
        raise RuntimeError('Corrected feature schema differs')
    schema = v.read(schema_path)
    assets = {}
    for row in schema['source_files_and_assets']:
        path = v.inside(row['runtime_project_relative_path'])
        if path.stat().st_size != row['bytes'] or v.sha(path) != row['sha256']:
            raise RuntimeError('Actual original source/JSON asset differs')
        if path.suffix == '.json':
            assets[path.name] = v.read(path)
    members = request['members']
    exact_names([item['accession'] for item in members], expected, 'FAA/annotation member inventory')
    for item in members:
        for name in ('selected_faa', 'annotation_receipt', 'annotation_unit_execution'):
            v.bind(item[name])
        if 'annotation_commit' in item:
            v.bind(item['annotation_commit'])
        closed_unit(v.read(v.bind(item['annotation_unit_execution'])))
    for name in ('raw_pickle', 'quality_report', 'quality_unit_execution'):
        v.bind(request['artifacts'][name])
    closed_unit(v.read(v.bind(request['artifacts']['quality_unit_execution'])))
    with v.bind(request['artifacts']['quality_report']).open(newline='', encoding='utf-8') as handle:
        reader = csv.DictReader(handle, delimiter='\t')
        reports = join_report_rows(reader.fieldnames, list(reader), expected)
    return recipe, schema, assets, reports


def main(args):
    request_path = v.inside(args.request)
    if v.sha(request_path) != args.request_sha256:
        raise RuntimeError('Request SHA256 mismatch before imports or unpickle')
    request = v.read(request_path)
    recipe, schema, assets, reports = preflight(request)
    v.no_models()
    if (os.environ.get('TREE2_PRIVATE_NAMESPACE_VERIFIED') != '1' or
        os.environ.get('TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED') != '1'):
        raise RuntimeError('Accepted private read-only runtime is required')
    prefix = v.inside(request['runtime_prefix'])
    if Path(sys.executable).resolve() != (prefix / 'bin/python').resolve():
        raise RuntimeError('Benchmark validator is outside the accepted Python prefix')
    output = v.inside(args.output)
    if output.exists():
        raise RuntimeError('Refusing to overwrite an existing benchmark feature receipt')
    import numpy as np
    import pandas as pd
    if (sys.version_info[:3] != (3, 12, 16) or np.__version__ != '2.5.4' or pd.__version__ != '3.1.0' or
        not Path(np.__file__).resolve().is_relative_to(prefix) or not Path(pd.__file__).resolve().is_relative_to(prefix)):
        raise RuntimeError('Pinned accepted Python, NumPy or pandas version/origin differs')
    v.no_models()
    pickle_path = v.bind(request['artifacts']['raw_pickle'])
    frame = pd.read_pickle(pickle_path)  # Exactly one load of this owned, hash-pinned batch dump.
    if list(frame.columns) != schema['ordered_dataframe_columns'] or frame.shape != (10, 21242) or frame.columns.has_duplicates:
        raise ValueError('Exact ten-row ordered full feature schema is required')
    positions = exact_names(list(frame.iloc[:, 0]), recipe['expected_accessions'], 'feature dump')
    member_map = {item['accession']: item for item in request['members']}
    source_map = {item['accession']: item for item in recipe['inputs']}
    import checkm2_protein_helpers_v001 as old
    from checkm2_membership_recompute_v002 import recompute_membership_features
    program_sha = v.sha(prefix / 'bin/prodigal')
    results = []
    for accession in recipe['expected_accessions']:
        index = positions[accession]
        values = v.validate_domains(schema, frame.iloc[[index], :], np)
        member = member_map[accession]
        faa = v.bind(member['selected_faa'])
        if faa.name != accession + '.faa':
            raise ValueError('Exact versioned supplied FAA basename is required')
        annotation = v.read(v.bind(member['annotation_receipt']))
        item = source_map[accession]
        if (annotation.get('status') != 'ORIGINAL_SEQUENTIAL_PRODIGAL_COMPLETED_NOT_GENOME_ACCEPTANCE' or
            annotation.get('accession') != accession or annotation.get('source_fna_sha256') != item['fasta_sha256'] or
            annotation.get('faa_sha256') != v.sha(faa) or annotation.get('original_source_sha256') != CALLER_SHA or
            annotation.get('prodigal_program_sha256') != program_sha or annotation.get('ML_modules_loaded') != [] or
            annotation.get('interception_or_author_patch') is not False or annotation.get('author_deletes_selected_GFF_and_FNA') is not True):
            raise ValueError('Exact original model-free source/FAA/caller provenance is required')
        proteins = old.parse_fasta(faa.read_text(), old.AA)
        if old.sequence_receipt(proteins) != annotation['protein_sequences']:
            raise ValueError('FAA records/headers/sequences differ from annotation receipt')
        measurements = old.validate_author_return(annotation['all10_original_return_values'], accession)
        if measurements != annotation['original_measurements'] or measurements['CDS_count'] != len(proteins):
            raise ValueError('All ten original returned measurements must remain exact')
        dna = annotation['independent_DNA_QC']
        if (measurements['total_nucleotide_bases'] != dna['total_bases'] or
            measurements['contig_count'] != dna['contigs'] or measurements['max_contig_length'] != dna['max_contig_length']):
            raise ValueError('Original caller and separately preserved DNA metrics disagree')
        joined = ''.join(item['sequence'] for item in proteins)
        expected_aa = [joined.count(name) for name in schema['ordered_model_features'][:20]] + [len(joined), len(proteins)]
        if list(values[0, :22]) != expected_aa:
            raise ValueError('FAA metadata and exact accession feature row disagree')
        counts = {name: frame[name].iloc[index] for name in schema['ordered_model_features'][22:20021]}
        expected_memberships = recompute_membership_features(counts, assets['feature_ordering.json'],
            assets['kegg_path_category_mapping.json'], assets['module_definitions.json'])
        names = schema['ordered_model_features'][20021:]
        if list(expected_memberships) != names or len(expected_memberships) != 1220:
            raise ValueError('Independent membership feature order/count differs')
        if any(float(values[0, 20021 + offset]) != expected_memberships[name] for offset, name in enumerate(names)):
            raise ValueError('Independent membership recomputation differs for ' + accession)
        row = measured_row_with_original_holds(item, reports[accession])
        canonical = np.asarray(values, dtype='<f8', order='C')
        row.update(feature_row_position=index, canonical_float64_le_row_sha256=hashlib.sha256(canonical.tobytes()).hexdigest(),
                   selected_FAA_sha256=v.sha(faa), annotation_receipt_sha256=member['annotation_receipt']['sha256'],
                   annotation_unit_execution_sha256=member['annotation_unit_execution']['sha256'],
                   annotation_commit_sha256=member.get('annotation_commit', {}).get('sha256'),
                   independent_DNA_QC=annotation['independent_DNA_QC'],
                   all10_original_return_values=annotation['all10_original_return_values'],
                   finite_numeric_features=21241, exact_FAA_metadata_features=22,
                   independently_recomputed_membership_features=1220, membership_mismatches=0)
        results.append(row)
    for row in request['artifacts'].values():
        v.bind(row)
    for member in request['members']:
        for name in ('selected_faa', 'annotation_receipt', 'annotation_unit_execution'):
            v.bind(member[name])
        if 'annotation_commit' in member:
            v.bind(member['annotation_commit'])
    if v.sha(request_path) != args.request_sha256:
        raise RuntimeError('Request changed during validation')
    v.no_models()
    result = {'status': 'BENCHMARK10_FEATURES_V002_PASS_PENDING_NATIVE_CLOSURE',
              'scope': 'EXACT_TEN_METHOD_BENCHMARK_ONLY_NO_PANEL_GRANT',
              'input_plan_sha256': request['input_plan_sha256'], 'request_sha256': args.request_sha256,
              'recipe_sha256': RECIPE_SHA, 'source_manifest_sha256': request['source_manifest']['sha256'],
              'protocol_admission_sha256': request['protocol_admission']['sha256'],
              'raw_pickle_sha256': v.sha(pickle_path), 'pickle_loads': 1,
              'row_count': 10,
              'schema_v002_sha256': SCHEMA_SHA, 'dataframe_shape': list(frame.shape),
              'ordered_dataframe_columns_sha256': v.canonical(list(frame.columns)),
              'actual_feature_row_order': list(frame.iloc[:, 0]), 'validated_accessions': recipe['expected_accessions'],
              'finite_numeric_features': 212410, 'exact_FAA_metadata_features': 220,
              'independently_recomputed_membership_features': 12200, 'membership_mismatches': 0,
              'canonical_accession_row_hashes_sha256': v.canonical([(row['accession'], row['canonical_float64_le_row_sha256']) for row in results]),
              'source_hold_accessions_preserved': recipe['expected_ancillary_hold_accessions'], 'rows': results,
              'forbidden_model_modules_loaded': v.no_models(), 'unknown_as_negative': False,
              'validator_annotation_DIAMOND_or_ML_runs': 0, 'production_or_panel_acceptance': 'NOT_GRANTED'}
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
        v.save(v.inside(args.output).with_name('benchmark10_feature_validation_failure.json'),
               {'status': 'BENCHMARK10_VALIDATION_FAILED_OR_UNRESOLVED', 'error': repr(error),
                'scores_inferred_for_missing_rows': None, 'unknown_as_negative': False,
                'production_or_panel_acceptance': 'NOT_GRANTED'})
        raise
