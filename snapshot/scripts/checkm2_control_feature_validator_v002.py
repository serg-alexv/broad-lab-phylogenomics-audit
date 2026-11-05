"""HELD generic saved-feature validator for a separately admitted format control.

No caller, DIAMOND or model is invoked. All imports at module load are stdlib
or the unchanged stdlib-only accepted validator; scientific imports occur only
after request/source/artifact/protocol and closed quality-unit verification.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import sys

R = Path(__file__).resolve().parents[1]
ACCEPTED_VALIDATOR_SHA = 'c820c9d9c9e5e86343f7a80f8fc853ae8dfb1684779ca9f0ef218973e95a01ff'
SCHEMA_SHA = '90e482515c6924386a888aa14a036f7659acf9ad0c49814cb08a3a7e1f76f5ee'
ROOT_BASELINE_SHA = '0e80c5335a178d04a78864e650318c937af6030c03c2405b0ee272a4b2b27ae3'
if hashlib.sha256((R / 'scripts/checkm2_posthoc_v002_validator.py').read_bytes()).hexdigest() != ACCEPTED_VALIDATOR_SHA:
    raise RuntimeError('Accepted unchanged feature-validator dependency differs')
import checkm2_posthoc_v002_validator as v


def read_request(path, expected_sha):
    path = v.inside(path)
    if v.sha(path) != expected_sha:
        raise RuntimeError('Control feature request SHA256 differs before any unpickle')
    request = v.read(path)
    if request.get('request_schema') != 'TREE2_CONTROL_FEATURE_REQUEST_V002':
        raise RuntimeError('Wrong control feature request schema')
    return request


def closed_quality_unit(execution):
    if (execution.get('status') != 'UNIT_EXIT0_GROUP_CLOSED' or
        type(execution.get('exit_code')) is not int or execution['exit_code'] != 0 or
        execution.get('owned_group_empty') is not True or
        execution.get('remaining_owned_processes') != []):
        raise RuntimeError('Stock protein-quality unit is not observed exit zero and group closed')


def preflight(request):
    source_path = v.bind(request['source_manifest'])
    manifest = v.read(source_path)
    sources = manifest.get('sources')
    if not isinstance(sources, list) or not sources:
        raise RuntimeError('A complete reviewed source manifest is required')
    required = {
        'scripts/checkm2_control_feature_validator_v002.py': v.sha(__file__),
        'scripts/checkm2_posthoc_v002_validator.py': ACCEPTED_VALIDATOR_SHA,
        'scripts/checkm2_membership_recompute_v002.py': 'e1a0216db7db3716102745f3a78c3ff65f14040601a6cbb6cffb9edc7e4d4efe',
        'scripts/checkm2_protein_helpers_v001.py': '1b04bd9906b19521cd87fc16cfb1a66e0a954f595c83920803f12b05a408baf6',
    }
    observed = {}
    for row in sources:
        path = v.bind(row)
        relative = path.relative_to(R).as_posix()
        if relative in observed:
            raise RuntimeError('Duplicate source-manifest entry')
        observed[relative] = row['sha256']
    if any(observed.get(name) != expected for name, expected in required.items()):
        raise RuntimeError('Required reviewed validation dependencies are missing or changed')
    protocol = v.read(v.bind(request['protocol_admission']))
    if (protocol.get('schema') != 'TREE2_PROTEIN_FORMAT_CONTROL_ADMISSION_V002' or
        protocol.get('status') != 'ADMITTED_ONE_FORMAT_CONTROL' or
        protocol.get('format_control_execution_authorized') is not True or
        protocol.get('role') != 'PROTEIN_PIPELINE_DNA_WRAP61_INVARIANCE' or
        protocol.get('max_attempts') != 1 or
        protocol.get('input_plan_sha256') != request['input_plan_sha256'] or
        protocol.get('source_manifest_sha256') != request['source_manifest']['sha256'] or
        protocol.get('root_baseline_acceptance_sha256') != ROOT_BASELINE_SHA):
        raise RuntimeError('A matching one-shot root control-protocol admission is required')
    for gate in ('monitor_standard_stage04_ready', 'source_math_GO', 'resource_lifecycle_GO'):
        if protocol.get(gate) is not True:
            raise RuntimeError('Required reviewed control gate is absent: ' + gate)
    root_path = R / 'evidence/checkm2_posthoc_v002/root_baseline_acceptance.json'
    if v.sha(root_path) != ROOT_BASELINE_SHA:
        raise RuntimeError('Accepted method-baseline authority changed')
    schema_path = v.bind(request['schema'])
    if v.sha(schema_path) != SCHEMA_SHA:
        raise RuntimeError('Corrected feature schema differs')
    schema = v.read(schema_path)
    artifacts = request['artifacts']
    for name in ('raw_pickle', 'selected_faa', 'annotation_receipt', 'quality_report', 'quality_unit_execution'):
        v.bind(artifacts[name])
    closed_quality_unit(v.read(v.bind(artifacts['quality_unit_execution'])))
    assets = {}
    for row in schema['source_files_and_assets']:
        path = v.inside(row['runtime_project_relative_path'])
        if path.stat().st_size != row['bytes'] or v.sha(path) != row['sha256']:
            raise RuntimeError('Bound original runtime source or JSON asset changed')
        if path.suffix == '.json':
            assets[path.name] = v.read(path)
    return schema, assets


def main(args):
    request_path = v.inside(args.request)
    request = read_request(request_path, args.request_sha256)
    schema, assets = preflight(request)
    v.no_models()
    if (os.environ.get('TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED') != '1' or
        os.environ.get('TREE2_PRIVATE_NAMESPACE_VERIFIED') != '1'):
        raise RuntimeError('Accepted private read-only runtime is required')
    prefix = v.inside(request['runtime_prefix'])
    if Path(sys.executable).resolve() != (prefix / 'bin/python').resolve():
        raise RuntimeError('Control feature validation is outside the accepted Python prefix')
    output = v.inside(args.output)
    if output.exists():
        raise RuntimeError('Refusing to overwrite a control feature receipt')
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
        raise ValueError('Control feature accession/version differs')
    import checkm2_protein_helpers_v001 as old
    faa = v.bind(artifacts['selected_faa'])
    proteins = old.parse_fasta(faa.read_text(), old.AA)
    annotation = v.read(v.bind(artifacts['annotation_receipt']))
    if annotation['accession'] != accession or old.sequence_receipt(proteins) != annotation['protein_sequences']:
        raise ValueError('All selected FAA identifiers, headers and sequences must match the original caller receipt')
    joined = ''.join(row['sequence'] for row in proteins)
    expected_aa = [joined.count(name) for name in schema['ordered_model_features'][:20]] + [len(joined), len(proteins)]
    if list(values[0, :22]) != expected_aa:
        raise ValueError('All 22 FAA metadata features are required unchanged')
    measurements = old.validate_author_return(annotation['all10_original_return_values'], accession)
    if measurements != annotation['original_measurements']:
        raise ValueError('All ten original caller values must agree with their preserved measurement map')
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
    for item in artifacts.values():
        v.bind(item)
    if v.sha(request_path) != args.request_sha256:
        raise RuntimeError('Control feature request changed during validation')
    v.no_models()
    canonical = np.asarray(values, dtype='<f8', order='C')
    result = {
        'status': 'PROTEIN_CONTROL_FEATURES_V002_PASS_PENDING_CLOSURE',
        'scope': 'CONTROL_FEATURE_VALIDATION_ONLY_NO_CALLER_DIAMOND_OR_MODEL_INVOCATION',
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
        v.save(v.inside(args.output).with_name('control_feature_validation_failure.json'),
               {'status': 'CONTROL_FEATURE_VALIDATION_FAILED', 'error': repr(error),
                'validator_calls_no_annotation_DIAMOND_or_ML': True})
        raise
