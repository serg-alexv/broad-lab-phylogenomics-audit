"""Pure P20 metadata projection; missing source context remains unavailable.

No I/O, scientific import, mutation, numerical validation or execution authority.
The exact bound P20 source item is retained, including every mask/pending reason.
"""
import copy

LEGACY_CONTEXT_FIELDS = ('accession', 'species', 'genus', 'family', 'role',
                         'metadata_qc', 'selection_status', 'source_disposition',
                         'source_holds_preserved', 'source_metadata_checkm',
                         'source_taxonomy_gates')
REQUIRED_P20_FIELDS = LEGACY_CONTEXT_FIELDS[:-2] + ('source_pending_reasons', 'source_masks')


def measured_row_with_original_P20_context(item, report):
    if any(name not in item for name in REQUIRED_P20_FIELDS):
        raise ValueError('Required bound P20 source fields are missing')
    if report['raw_report']['Name'] != item['accession']:
        raise ValueError('Report/source join must use exact accession, not position')
    unavailable = [name for name in LEGACY_CONTEXT_FIELDS if name not in item]
    availability = {
        name: {'status': 'PRESENT_IN_BOUND_SOURCE_ITEM' if name in item else 'NOT_PROVIDED_IN_BOUND_P20_SOURCE_SCHEMA',
               'value': copy.deepcopy(item[name]) if name in item else None}
        for name in LEGACY_CONTEXT_FIELDS[-2:]
    }
    return {
        'accession': item['accession'], 'Completeness': report['Completeness'],
        'Contamination': report['Contamination'],
        'raw_author_protein_report_row': copy.deepcopy(report['raw_report']),
        'original_source_context': copy.deepcopy(item),
        'source_context_availability': availability,
        'unavailable_legacy_source_context_fields': unavailable,
        'source_holds_preserved': copy.deepcopy(item['source_holds_preserved']),
        'source_hold_active': bool(item['source_holds_preserved']),
        'numeric_benchmark_status': 'MEASURED_ONLY_NOT_A_PANEL_PASS',
        'source_taxonomy_acceptance': 'NOT_GRANTED', 'production_acceptance': 'NOT_GRANTED',
    }
