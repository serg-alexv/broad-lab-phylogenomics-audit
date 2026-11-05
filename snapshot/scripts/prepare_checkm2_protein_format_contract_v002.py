"""Freeze a HELD template from source/metadata only; never prepare real input."""
from pathlib import Path
import copy
import hashlib
import json
import os

R = Path(__file__).resolve().parents[1]
OUT = R / 'metadata/checkm2_protein_format_invariance_v002.json'
V001_SHA = '91ad21abcc2476d7c033ca179abcf1fca57974faafbaae8eae026950dc991dc5'
SCHEMA_SHA = '90e482515c6924386a888aa14a036f7659acf9ad0c49814cb08a3a7e1f76f5ee'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def pin(relative):
    path = R / relative
    return {'path': relative, 'sha256': sha(path), 'bytes': path.stat().st_size}


def main():
    original = R / 'metadata/checkm2_protein_format_invariance_v001.json'
    if sha(original) != V001_SHA:
        raise RuntimeError('Preserved v001 contract changed')
    prior = read(original)
    schema = R / 'metadata/checkm2_feature_schema_v002.json'
    if sha(schema) != SCHEMA_SHA:
        raise RuntimeError('Corrected schema differs')
    implementation = R / 'metadata/checkm2_protein_implementation_v001.json'
    if sha(implementation) != '87ce9cec98b7d109f2d34df3ac1671941ceec01e64bfe0b4a64fa2389707ed47':
        raise RuntimeError('Original implementation contract changed')
    executed_sources = read(implementation)['sources']
    for row in executed_sources:
        if sha(R / row['path']) != row['sha256']:
            raise RuntimeError('An original executed pilot source changed')
    posthoc = read(R / 'metadata/checkm2_posthoc_v002_source_contract.json')
    evidence = 'evidence/checkm2_posthoc_v002/'
    future = {
        'binding_status': 'HELD_UNTIL_ROOT_ACCEPTS_ACTUAL_POSTHOC_AND_NATIVE_CLOSURE',
        'latest_pointer': {'path': 'state/checkm2_posthoc_v002_latest.json', 'sha256': None},
        'validation_target': {'path': evidence + 'v001/validation.json', 'sha256': None},
        'execution': {'path': evidence + 'execution.json', 'sha256': None},
        'manifest': {'path': evidence + 'manifest.json', 'sha256': None},
        'native_and_lease_closure': {'path': evidence + 'native_and_lease_closure.json', 'sha256': None},
        'root_baseline_acceptance': {'path': None, 'sha256': None},
        'required_execution_status': 'PRESERVED_04R1_VALIDATION_V002_PASS_CLOSED',
        'target_status_may_remain': 'PRESERVED_04R1_FEATURES_AND_MEMBERSHIP_V002_PASS_PENDING_CLOSURE',
        'current_native_exit_zero_and_common_lease_closure_required': True,
        'original_failed_outer_exit_remains': 'UNKNOWN_NOT_CAPTURED',
        'original_failed_attempt_or_result_rewritten': False,
        'original_successful_result_json_required': False,
    }
    requirements = copy.deepcopy(prior['requirements'])
    requirements['feature_schema_sha256'] = SCHEMA_SHA
    requirements['independently_recomputed_membership_features'] = 1220
    requirements['corrected_module_domain'] = 'Finite nonnegative raw copy-count mean; values above 1 are valid'
    requirements['pathway_category_domains'] = 'Finite within [0,1], using clipped presence counts'
    requirements['normalized_DIAMOND_rows'] = 'All 12 original field strings as a sorted multiset; preserve duplicate multiplicity and ignore only row order'
    requirements['DIAMOND_missing_even_both'] = 'NOT_EVALUABLE'
    requirements['baseline_as_control_or_shared_execution_closure'] = 'NOT_EVALUABLE'
    requirements['cross_receipt_accession_FAA_and_source_bindings'] = 'Required consistent within each role before comparison'
    requirements['raw_pickle_hashes'] = 'Required individually; serialized pickle bytes need not match when the canonical full float64 row is identical'
    adaptor = copy.deepcopy(prior['adaptor_contract'])
    adaptor.update({
        'status': 'HELD_INTERFACE_AND_PURE_RECEIPT_ADAPTER_ONLY_NO_RUNNABLE_EXECUTOR',
        'output_root': 'analysis/checkm2_protein_format_invariance_v002',
        'progress_path': 'state/checkm2_protein_format_invariance_v002_progress.json',
        'native_launch_path': 'state/launch_checkm2_protein_format_invariance_v002.json',
        'namespace_root': 'evidence/checkm2_protein_format_invariance_v002/namespace_runs',
        'stop_path': 'state/STOP_CHECKM2_PROTEIN_FORMAT_V002',
        'input_plan_schema': 'TREE2_PROTEIN_FORMAT_INPUT_PLAN_V002',
        'experiment_role': 'PROTEIN_PIPELINE_DNA_WRAP61_INVARIANCE',
        'baseline_outputs_and_progress_preserved': True,
        'successful_original_result_json_not_required': True,
        'root_baseline_acceptance_required_before_variant_preparation': True,
        'root_control_protocol_admission_path': None,
        'root_control_protocol_admission_sha256': None,
        'new_source_manifest_path': None,
        'new_source_manifest_sha256': None,
        'owned_hold_transition': None,
        'runnable_execution_adaptor_prepared': False,
        'execution_adaptor_deferral_reason': 'The frozen pilot executor calls the failed v001 feature validator. A separate versioned executor must use a corrected generic validator without editing the twelve original sources.',
        'corrected_validator_interface': {
            'inputs': ['Bound raw pickle', 'Bound selected FAA', 'Bound original annotation receipt',
                       'Schema v002 path and SHA256', 'Exact versioned accession',
                       'Bound original source and JSON asset hashes'],
            'outputs': ['21,241 finite ordered feature inputs', '22 exact FAA metadata features',
                        '1,220 independently recomputed membership features',
                        'Canonical full little-endian float64 row SHA256', 'Unmodified five-column stock report'],
            'control_target_status': 'PROTEIN_CONTROL_FEATURES_V002_PASS_PENDING_CLOSURE',
            'quality_and_validation_share_existing_600_second_unit': True,
            'model_free_validation_and_no_clipping_or_author_patch': True,
        },
    })
    adaptor['immutable_request_fields'] = [
        'plan_path', 'plan_sha256', 'posthoc_latest_sha256', 'posthoc_validation_sha256',
        'posthoc_execution_sha256', 'posthoc_manifest_sha256', 'posthoc_native_lease_closure_sha256',
        'root_baseline_acceptance_sha256', 'root_control_protocol_admission_sha256',
        'source_manifest_sha256', 'original_input_sha256', 'derived_input_sha256',
        'semantic_identity_sha256', 'feature_schema_v002_sha256']
    template = {
        'schema': 'TREE2_PROTEIN_FORMAT_INVARIANCE_V002',
        'status': 'HELD_TEMPLATE_NOT_BOUND_TO_ROOT_ACCEPTED_CLOSED_BASELINE',
        'prepared_date': '2026-10-27',
        'preserved_v001_contract': pin('metadata/checkm2_protein_format_invariance_v001.json'),
        'basis': {
            'original_pilot_implementation': pin('metadata/checkm2_protein_implementation_v001.json'),
            'original_executed_sources': executed_sources,
            'original_root_strategy_sha256': prior['basis']['baseline_strategy_sha256'],
            'original_attempt_namespace_token': prior['basis']['prospective_native_launch_token'],
            'original_saved_run_path': posthoc['original_run'],
            'original_failed_attempt_artifact_pins_from_source_contract_only': posthoc['artifacts'],
            'posthoc_source_contract': pin('metadata/checkm2_posthoc_v002_source_contract.json'),
            'corrected_feature_schema': pin('metadata/checkm2_feature_schema_v002.json'),
            'posthoc_accepted_baseline_chain': future,
        },
        'reference_input_from_metadata_only': prior['reference_input_from_metadata_only'],
        'transform': {**prior['transform'],
                      'actual_DNA_read_or_transformed_for_this_draft': False,
                      'derived_input_path': None, 'derived_input_sha256': None,
                      'semantic_identity_receipt_sha256': None,
                      'on_no_op_or_failure': 'STOP_NOT_EVALUABLE_NO_SUBSTITUTION_OR_RETRY'},
        'requirements': requirements,
        'adaptor_contract': adaptor,
        'pure_receipt_adapter': {
            'module': pin('scripts/checkm2_protein_invariance_v002.py'),
            'feature_projection': 'feature_evidence_from_closed_validation(result, verified_closed_chain)',
            'feature_comparison': 'compare_feature_receipts(reference, control)',
            'report_and_annotation_comparisons_reused_unchanged': pin('scripts/checkm2_protein_invariance_v001.py'),
            'DIAMOND_receipt_comparison': 'compare_diamond_receipts(reference, control)',
            'future_rewrap_and_DIAMOND_digest_helpers': pin('scripts/checkm2_fasta_invariance.py'),
            'real_rewrap_or_digest_helpers_called_during_preparation': False,
            'verified_closed_chain_root_authority': 'Root acceptance for POSTHOC_BASELINE; root control-protocol admission for FORMAT_CONTROL',
            'all_referenced_hashes_and_cross_receipt_bindings_verified_by_future_owner': True,
            'module_has_no_file_IO_no_cli_and_no_dispatch': True,
        },
        'builder': pin('scripts/prepare_checkm2_protein_format_contract_v002.py'),
        'human_summary': pin('docs/CHECKM2_PROTEIN_FORMAT_INVARIANCE_V002.md'),
        'new_fixture_source': pin('scripts/test_checkm2_protein_invariance_v002.py'),
        'preserved_v001_fixture_source': pin('scripts/test_checkm2_protein_invariance_v001.py'),
        'active_twelve_pilot_sources_unchanged': True,
        'actual_saved_baseline_outputs_opened_for_preparation': False,
        'variant_FAA_genome_or_model_generation': False,
        'launch_admission_created': False,
        'pipeline_invariance_only': True,
        'biological_truth_or_FNA_numeric_equivalence_claim': False,
        'production_acceptance': False,
    }
    if any(value['sha256'] is not None for value in future.values() if isinstance(value, dict)):
        raise RuntimeError('A source-only template cannot invent successful baseline hashes')
    data = (json.dumps(template, indent=2) + '\n').encode('utf-8')
    if OUT.exists():
        if OUT.read_bytes() != data:
            raise RuntimeError('Held template is immutable; create a separate bound plan later')
    else:
        pending = OUT.with_suffix('.pending')
        with pending.open('xb') as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
        os.replace(pending, OUT)
    if sha(original) != V001_SHA:
        raise RuntimeError('The original v001 contract changed during preparation')
    print(json.dumps({'status': template['status'], 'path': OUT.relative_to(R).as_posix(),
                      'sha256': sha(OUT), 'actual_variants_or_runs': 0}))


if __name__ == '__main__':
    main()
