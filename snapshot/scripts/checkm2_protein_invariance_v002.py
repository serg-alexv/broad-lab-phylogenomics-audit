"""Held pure receipt adapter/comparators; no file I/O or execution entry point.

The future owner must verify every referenced artifact, manifest and lifecycle
proof before calling these functions. A target's pending-closure PASS alone is
insufficient. This module cannot create a variant, run a tool or admit a launch.
"""
import re
import checkm2_protein_invariance_v001 as previous

NotEvaluable = previous.NotEvaluable
compare_protein_rows = previous.compare_protein_rows
compare_annotation_receipts = previous.compare_annotation_receipts
FEATURE_SCHEMA_SHA = '90e482515c6924386a888aa14a036f7659acf9ad0c49814cb08a3a7e1f76f5ee'


def _check_closed_chain(closed_chain):
    previous.required(closed_chain, ('status', 'role', 'validation_sha256', 'manifest_sha256',
        'execution_sha256', 'native_and_lease_closure_sha256', 'owned_group_empty',
        'native_exit_observed', 'native_exit_code', 'ordinary_runtime_closed',
        'image_unchanged', 'common_leases_released', 'original_artifacts_unchanged',
        'root_authority_sha256'),
        'verified closed execution chain')
    if (closed_chain['status'] != 'HASH_VERIFIED_VALIDATION_AND_NATIVE_CLOSED' or
        closed_chain['role'] not in ('POSTHOC_BASELINE', 'FORMAT_CONTROL')):
        raise NotEvaluable('Pending target validation is not a closed baseline')
    for name in ('owned_group_empty', 'native_exit_observed', 'ordinary_runtime_closed',
                 'image_unchanged', 'common_leases_released', 'original_artifacts_unchanged'):
        if closed_chain[name] is not True:
            raise NotEvaluable('Required current lifecycle proof is absent: ' + name)
    if type(closed_chain['native_exit_code']) is not int or closed_chain['native_exit_code'] != 0:
        raise NotEvaluable('Current validation/control native exit must be observed zero')
    for name in ('validation_sha256', 'manifest_sha256', 'execution_sha256',
                 'native_and_lease_closure_sha256', 'root_authority_sha256'):
        previous.digest(closed_chain[name], name)


def feature_evidence_from_closed_validation(result, closed_chain):
    """Normalize a verified target result plus current execution/root authority.

    Hashes attest to files already verified by the future owner. Baseline root
    authority is its explicit acceptance; control authority is its protocol
    admission. No original failed outer launch is claimed to have exited zero.
    """
    previous.required(result, ('status', 'accession', 'raw_pickle_sha256',
        'schema_v002_sha256', 'source_FAA_sha256', 'ordered_dataframe_columns_sha256',
        'dataframe_shape', 'actual_ML_cast_dtype', 'canonical_float64_le_row_sha256',
        'finite_domain_features', 'exact_FAA_metadata_features',
        'independently_recomputed_membership_features', 'membership_mismatches'),
        'v002 feature validation result')
    _check_closed_chain(closed_chain)
    expected_status = ('PRESERVED_04R1_FEATURES_AND_MEMBERSHIP_V002_PASS_PENDING_CLOSURE'
        if closed_chain['role'] == 'POSTHOC_BASELINE' else
        'PROTEIN_CONTROL_FEATURES_V002_PASS_PENDING_CLOSURE')
    if result['status'] != expected_status:
        raise NotEvaluable('Required v002 target validation PASS/role is absent')
    if not isinstance(result['accession'], str) or not re.fullmatch(r'GC[AF]_\d{9}\.\d+', result['accession']):
        raise NotEvaluable('Exact versioned accession is required')
    for name in ('raw_pickle_sha256', 'schema_v002_sha256', 'source_FAA_sha256',
                 'ordered_dataframe_columns_sha256', 'canonical_float64_le_row_sha256'):
        previous.digest(result[name], name)
    if (result['schema_v002_sha256'] != FEATURE_SCHEMA_SHA or
        result['dataframe_shape'] != [1, 21242] or result['actual_ML_cast_dtype'] != 'float64' or
        result['finite_domain_features'] != 21241 or result['exact_FAA_metadata_features'] != 22 or
        result['independently_recomputed_membership_features'] != 1220 or
        result['membership_mismatches'] != 0):
        raise NotEvaluable('Full corrected feature validation is not established')
    return {'status': 'FEATURES_V002_WITH_VERIFIED_CLOSED_CHAIN',
            'accession': result['accession'], 'raw_pickle_sha256': result['raw_pickle_sha256'],
            'source_FAA_sha256': result['source_FAA_sha256'], 'schema_sha256': FEATURE_SCHEMA_SHA,
            'ordered_column_names_sha256': result['ordered_dataframe_columns_sha256'],
            'dataframe_shape': result['dataframe_shape'], 'actual_ML_input_dtype': 'float64',
            'canonical_float64_le_row_sha256': result['canonical_float64_le_row_sha256'],
            'finite_domain_features': result['finite_domain_features'],
            'exact_FAA_metadata_features': result['exact_FAA_metadata_features'],
            'independently_recomputed_membership_features': result['independently_recomputed_membership_features'],
            'membership_mismatches': result['membership_mismatches'],
            'closed_chain': dict(closed_chain), 'production_acceptance': False}


def compare_feature_receipts(reference, control):
    fields = ('status', 'accession', 'raw_pickle_sha256', 'source_FAA_sha256',
              'schema_sha256', 'ordered_column_names_sha256', 'dataframe_shape',
              'actual_ML_input_dtype', 'canonical_float64_le_row_sha256', 'closed_chain',
              'finite_domain_features', 'exact_FAA_metadata_features',
              'independently_recomputed_membership_features', 'membership_mismatches')
    for row in (reference, control):
        previous.required(row, fields, 'complete v002 feature evidence')
        if (row['status'] != 'FEATURES_V002_WITH_VERIFIED_CLOSED_CHAIN' or
            row['schema_sha256'] != FEATURE_SCHEMA_SHA or row['dataframe_shape'] != [1, 21242] or
            row['actual_ML_input_dtype'] != 'float64' or row['finite_domain_features'] != 21241 or
            row['exact_FAA_metadata_features'] != 22 or
            row['independently_recomputed_membership_features'] != 1220 or row['membership_mismatches'] != 0):
            raise NotEvaluable('Corrected full feature evidence is required')
        for name in ('raw_pickle_sha256', 'source_FAA_sha256', 'schema_sha256',
                     'ordered_column_names_sha256', 'canonical_float64_le_row_sha256'):
            previous.digest(row[name], name)
        _check_closed_chain(row['closed_chain'])
    if (reference['closed_chain']['role'] != 'POSTHOC_BASELINE' or
        control['closed_chain']['role'] != 'FORMAT_CONTROL' or
        reference['closed_chain']['execution_sha256'] == control['closed_chain']['execution_sha256'] or
        reference['closed_chain']['native_and_lease_closure_sha256'] == control['closed_chain']['native_and_lease_closure_sha256']):
        raise NotEvaluable('A distinct executed control and its own closure are required')
    names = ('accession', 'source_FAA_sha256', 'schema_sha256', 'ordered_column_names_sha256',
             'dataframe_shape', 'actual_ML_input_dtype', 'canonical_float64_le_row_sha256')
    differences = [name for name in names if reference[name] != control[name]]
    return {'equal': not differences, 'differences': differences,
            'all_21241_canonical_features_compared': True,
            'raw_pickle_serialization_byte_equality_required': False,
            'missing_both_feature_dumps_is_pass': False, 'production_acceptance': False}


def compare_diamond_receipts(reference, control):
    names = ('rows', 'unique_rows', 'multiset_sha256')
    for row in (reference, control):
        previous.required(row, names, 'full DIAMOND multiset evidence')
        if (type(row['rows']) is not int or type(row['unique_rows']) is not int or
            not 0 < row['unique_rows'] <= row['rows']):
            raise NotEvaluable('Missing or invalid preserved DIAMOND rows')
        previous.digest(row['multiset_sha256'], 'full DIAMOND multiset')
    differences = [name for name in names if reference[name] != control[name]]
    return {'equal': not differences, 'differences': differences,
            'all_12_columns_preserved': True, 'duplicate_rows_preserved': True,
            'row_order_ignored': True, 'missing_both_is_pass': False,
            'production_acceptance': False}
