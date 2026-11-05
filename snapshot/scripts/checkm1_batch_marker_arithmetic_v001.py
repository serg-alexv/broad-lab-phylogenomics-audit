"""File-only independent pilot arithmetic. Never imports CheckM or scans sequences."""
from pathlib import Path
from fractions import Fraction
import argparse
import ast
import csv
import hashlib
import json
import math
import os

ROOT = Path(__file__).resolve().parents[1]
PILOT = {'path':'metadata/checkm1_lactobacillales_full919_v001/queue_manifest.json','sha256':'5ef514a1a39776ab79281128a725c9188a787b054452804150a58d30079f116f','bytes':8605479}
MODEL_AUDIT = {"path": "metadata/checkm1_taxon_setup_v001/stock_clan_expansion_actual_v001.json",
               "sha256": "a3f951d6651153b7d96004fac15a8cb9df17678987fb68902b01d50ffd67260d", "bytes": 30180}
HEADER = ['Bin Id', 'Marker lineage', '# genomes', '# markers', '# marker sets',
          '0', '1', '2', '3', '4', '5+', 'Completeness', 'Contamination', 'Strain heterogeneity']


def path(value):
    candidate = Path(str(value).replace('\\', '/'))
    candidate = (candidate if candidate.is_absolute() else ROOT / candidate).resolve()
    if not candidate.is_relative_to(ROOT):
        raise ValueError('Artifact outside project')
    return candidate


def bind(row):
    candidate = path(row['path'])
    payload = candidate.read_bytes()
    if len(payload) != row['bytes'] or hashlib.sha256(payload).hexdigest() != row['sha256']:
        raise ValueError('Artifact hash/size changed: ' + str(candidate))
    return candidate


def literal_rows(candidate):
    result = {}
    for line in candidate.read_text().splitlines():
        name, payload = line.split('\t', 1)
        if not name or name in result:
            raise ValueError('Missing or duplicate bin in stored counts')
        value = ast.literal_eval(payload)
        if not isinstance(value, dict):
            raise ValueError('Stored per-bin counts are not a dictionary')
        result[name] = value
    return result


def weighted(groups, counts):
    """Exact independent set weighting; excess hits are retained without deduplication."""
    if not groups or any(not group for group in groups):
        raise ValueError('Empty marker-set denominator')
    markers = set().union(*groups)
    if set(counts) != markers or any(type(v) is not int or v < 0 for v in counts.values()):
        raise ValueError('Incomplete or invalid marker counts')
    comp = sum((Fraction(sum(counts[m] > 0 for m in group), len(group)) for group in groups), Fraction())
    cont = sum((Fraction(sum(max(counts[m] - 1, 0) for m in group), len(group)) for group in groups), Fraction())
    histogram = [sum(min(counts[m], 5) == i for m in markers) for i in range(6)]
    return float(100 * comp / len(groups)), float(100 * cont / len(groups)), histogram


def counts_from_filtered_stats(stats, markers):
    counts = dict.fromkeys(markers, 0)
    for gene, hits in stats.items():
        if not isinstance(gene, str) or not gene or not isinstance(hits, dict):
            raise ValueError('Invalid filtered gene entry')
        for marker, intervals in hits.items():
            if marker not in counts or not isinstance(intervals, list) or not intervals:
                raise ValueError('Unknown marker or empty retained-hit list')
            for pair in intervals:
                if not isinstance(pair, list) or len(pair) != 2 or any(type(v) is not int for v in pair) or not 1 <= pair[0] <= pair[1]:
                    raise ValueError('Invalid retained alignment interval')
            counts[marker] += len(intervals)
    return counts


def classify(comp, cont):
    return 'PASS' if comp >= 95 and cont <= 5 else 'FAIL'


def validate(commit_ref):
    commit_path = bind(commit_ref)
    commit = json.loads(commit_path.read_text())
    pilot = json.loads(bind(PILOT).read_text())
    names = commit['accessions']
    if sum(b['ordered_accessions'] == names for b in pilot['batches']) != 1:
        raise ValueError('Committed cohort differs from exact frozen919 queue')
    if commit.get('status') != 'CHECKM1_BATCH_MEASURED_VALIDATED' or commit.get('accessions') != names or [r['accession'] for r in commit['rows']] != names:
        raise ValueError('Not the exact committed queue cohort')
    artifact_refs = {path(r['path']): r for r in commit['artifacts']}
    if len(artifact_refs) != len(commit['artifacts']):
        raise ValueError('Duplicate artifact bindings')

    def required(relative):
        candidate = commit_path.parent / relative
        if candidate not in artifact_refs:
            raise ValueError('Required count/report/unit is not committed: ' + relative)
        return bind(artifact_refs[candidate])

    for unit in ('unit_analyze', 'unit_qa'):
        execution = json.loads(required(unit + '/execution.json').read_text())
        if type(execution.get('actual_exit_code')) is not int or execution['actual_exit_code'] != 0 or execution.get('group_closed') is not True or execution.get('remaining_owned_identities') != [] or execution.get('actual_child_waited_and_reaped') is not True:
            raise ValueError('Required actual command/group is not closed0')
    marker_path = bind(commit['marker_file'])
    audit = json.loads(bind(MODEL_AUDIT).read_text())
    if commit['marker_file'] != audit['marker_file']:
        raise ValueError('Committed marker file differs from actual stock expansion audit')
    fields = marker_path.read_text().splitlines()[1].split('\t')
    groups = ast.literal_eval(fields[5])
    markers = set().union(*groups)
    if fields[3] != 'Lactobacillales' or int(fields[4]) != 490 or len(markers) != 335 or sum(map(len, groups)) != 335 or len(groups) != 183:
        raise ValueError('Wrong selected order marker denominator')
    genes = literal_rows(required('checkm_output/storage/marker_gene_stats.tsv'))
    extended = literal_rows(required('checkm_output/storage/bin_stats_ext.tsv'))
    with required('quality.tsv').open(newline='') as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        if reader.fieldnames != HEADER:
            raise ValueError('Unexpected stock QA header')
        qa = list(reader)
    if any(set(row) != set(HEADER) or any(v is None for v in row.values()) for row in qa):
        raise ValueError('QA row width mismatch')
    report = {row['Bin Id']: row for row in qa}
    if len(report) != len(qa) or set(report) != set(names) or set(genes) != set(names) or set(extended) != set(names):
        raise ValueError('Missing/duplicate/extra queue bin')
    evidence = {r['accession']: r for r in pilot['rows']}
    results = []
    for acc in names:
        counts = counts_from_filtered_stats(genes[acc], markers)
        comp, cont, histogram = weighted(groups, counts)
        ext, q = extended[acc], report[acc]
        if ext['marker lineage'] != 'Lactobacillales' or int(ext['# genomes']) != 490 or int(ext['# markers']) != 335 or int(ext['# marker sets']) != 183 or q['Marker lineage'] != 'Lactobacillales (' + fields[2] + ')' or int(q['# genomes']) != 490 or int(q['# markers']) != 335 or int(q['# marker sets']) != 183:
            raise ValueError('Wrong stored marker lineage/domain')
        if not math.isfinite(float(q['Strain heterogeneity'])) or not 0 <= float(q['Strain heterogeneity']) <= 100:
            raise ValueError('Nonfinite/out-of-domain strain heterogeneity')
        for field, actual in [('Completeness', comp), ('Contamination', cont)]:
            if not math.isclose(float(ext[field]), actual, rel_tol=0, abs_tol=1e-9) or not math.isclose(float(q[field]), actual, rel_tol=0, abs_tol=0.005000001):
                raise ValueError('Independent weighted score disagrees: ' + acc + '/' + field)
        for i, field in enumerate(['0', '1', '2', '3', '4', '5+']):
            expected_ids = {os.path.splitext(m)[0] for m in markers if min(counts[m], 5) == i}
            listed = ext['GCN' + field]
            if ext[field] != histogram[i] or int(q[field]) != histogram[i] or len(listed) != len(set(listed)) or set(listed) != expected_ids:
                raise ValueError('Duplicate/missing marker-copy category: ' + acc + '/' + field)
        source = evidence[acc]
        comparison = source['CheckM2_diagnostic_comparator']
        diagnostic = None
        if comparison is not None:
            dc, dx = comp - comparison['Completeness'], cont - comparison['Contamination']
            diagnostic = {'completeness_difference_pp': dc, 'contamination_difference_pp': dx,
                          'large_completeness_difference_gt5pp': abs(dc) > 5,
                          'large_contamination_difference_gt3pp': abs(dx) > 3,
                          'classification_flip': classify(comp, cont) != classify(comparison['Completeness'], comparison['Contamination']),
                          'same_original_scoring_FAA_sha256': comparison.get('CheckM2_FAA_sha256') == source['CheckM1_scoring_FAA']['sha256'],
                          'exact_cross_method_agreement_required': False}
        results.append({'accession': acc, 'family': source['family'], 'independent_unrounded_Completeness': comp,
                        'independent_unrounded_Contamination': cont, 'marker_counts': counts,
                        'copy_histogram': histogram, 'unrounded_QC_95_5': classify(comp, cont),
                        'reported_QC_95_5': classify(float(q['Completeness']), float(q['Contamination'])),
                        'rounded_threshold_crossing_requires_review': classify(comp, cont) != classify(float(q['Completeness']), float(q['Contamination'])),
                        'cross_method_diagnostic_only': diagnostic, 'source_masks': source['source_masks'],
                        'source_holds_preserved': source['source_holds_preserved'], 'source_pending_reasons': source['source_pending_reasons'],
                        'source_taxonomy_or_final_panel_acceptance': False})
    return {'schema': 'TREE2_CHECKM1_INDEPENDENT_QUEUE_ARITHMETIC_V001',
            'status': 'INDEPENDENT_STOCK_MARKER_ARITHMETIC_PASS_OWNER_AND_FINAL_PANEL_CLOSURE_SEPARATE',
            'pilot_manifest': PILOT, 'model_inventory_audit': MODEL_AUDIT, 'batch_commit': commit_ref, 'rows': results,
            'completed_method_measurements': len(results), 'all_rows_95_5_pass_required_for_method_go': False,
            'original_CheckM2_results_unchanged': True, 'runtime_or_search_executed': False,
            'whole_owner_closure_proved_by_this_file_only_check': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--commit-sha256', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    candidate = path(args.commit)
    output = path(args.output)
    result = validate({'path': str(candidate.relative_to(ROOT)), 'sha256': args.commit_sha256, 'bytes': candidate.stat().st_size})
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


if __name__ == '__main__':
    main()
