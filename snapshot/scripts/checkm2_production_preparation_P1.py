"""Bounded metadata-only production QC preparation after closed N5; no science dispatch."""
from pathlib import Path
from collections import Counter
import argparse
import ctypes
import datetime
import hashlib
import json
import msvcrt
import os
import shutil
import sys
import time
import traceback
import uuid
import local_tree2_dispatcher as dispatcher
import prepare_checkm2_phase_separated_history_N5 as history

R = Path(__file__).resolve().parents[1]
E = R / 'evidence/checkm2_production_preparation_P1'
OUT = R / 'metadata/checkm2_production_preparation_P1'
LAUNCH = R / 'state/launch_checkm2_production_preparation_P1.json'
ROLE = 'METADATA_ONLY_PRODUCTION_QC_PREPARATION_P1'
EVENT = '7d177a89d465b4b8badef6f8818e13a6187e8f121b43215d5507287fbb900779'
STARTED = time.monotonic()
START = dispatcher.utc()
PEAK_NATIVE_RSS = 0


class MemoryCounters(ctypes.Structure):
    _fields_ = [('cb', ctypes.c_ulong), ('PageFaultCount', ctypes.c_ulong),
                ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
                ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t)]


def native_rss():
    global PEAK_NATIVE_RSS
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(MemoryCounters), ctypes.c_ulong]
    value = MemoryCounters()
    value.cb = ctypes.sizeof(value)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(value), value.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    PEAK_NATIVE_RSS = max(PEAK_NATIVE_RSS, value.PeakWorkingSetSize, value.WorkingSetSize)
    if PEAK_NATIVE_RSS > 2 * 1024**3:
        raise RuntimeError('Native metadata owner RSS ceiling exceeded')
    return value.WorkingSetSize


def inside(value):
    p = Path(value)
    p = (p if p.is_absolute() else R / p).resolve()
    if not p.is_relative_to(R) or p.is_relative_to(R / 'work/local_continuation'):
        raise RuntimeError('Artifact outside public project scope')
    return p


def read(value):
    p = inside(value)
    if p.suffix != '.json':
        raise RuntimeError('Only JSON metadata may be parsed')
    return dispatcher.read(p)


def row(value):
    return dispatcher.row(R, inside(value))


def bind(value):
    p = inside(value['path'])
    if dispatcher.digest(p) != value['sha256'] or p.stat().st_size != value['bytes']:
        raise RuntimeError('Bound input changed: ' + value['path'])
    return p


def create(value, data):
    dispatcher.exclusive(inside(value), data)
    return row(value)


def gate(deadline):
    native_rss()
    if time.monotonic() > deadline:
        raise TimeoutError('Finite P1 preparation budget exhausted; no automatic retry')
    if any((R / 'state' / name).exists() for name in ('STOP', 'STOP_CHECKM2_PILOT', 'STOP_CHECKM2_PHASE_SEPARATED_N5')):
        raise InterruptedError('Project/biological STOP')
    if shutil.disk_usage(R).free < 40 * 1024**3:
        raise RuntimeError('Disk reserve below40GiB')


def affinity(win):
    k = win.k
    k.GetCurrentProcess.restype = ctypes.c_void_p
    k.GetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t)]
    k.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    allowed, system = ctypes.c_size_t(), ctypes.c_size_t()
    handle = k.GetCurrentProcess()
    if not k.GetProcessAffinityMask(handle, ctypes.byref(allowed), ctypes.byref(system)):
        raise ctypes.WinError(ctypes.get_last_error())
    mask = sum([1 << n for n in range(64) if allowed.value & (1 << n)][:2])
    if not mask or not k.SetProcessAffinityMask(handle, mask):
        raise ctypes.WinError(ctypes.get_last_error())
    return mask


def publish(owner, status, detail, done, total, terminal=None):
    value = {'id': '04', 'name': 'Independent biological QC', 'status': status,
             'started_utc': START, 'updated_utc': dispatcher.utc(), 'ended_utc': None,
             'pid': owner['pid'], 'creation_time_utc': owner['creation_time_utc'],
             'windows_creation_filetime_100ns': owner['windows_creation_filetime_100ns'],
             'operation': ROLE, 'done': done, 'total': total, 'unit': 'source-supported metadata ledger rows',
             'detail': detail, 'log_path': str(E / 'owner.stdout.txt'), 'terminal_receipt': terminal,
             'scientific_execution_authorized': False, 'whole_stage_QC_acceptance': False,
             'production_panel_acceptance': False, 'defence_unsearched_state': 'UNKNOWN'}
    dispatcher.atomic(R / 'state/stages/04.json', value)


def wait_for_v2(win, owner, spec):
    expected = spec['dispatcher_identity']
    handle = win.open_worker(expected)
    deadline = time.monotonic() + 180
    try:
        while True:
            gate(deadline)
            if win.wait(handle, 0):
                raise RuntimeError('Exact V2 dispatcher exited before attachment')
            status = read('state/local_continuation_v2/dispatcher_status.json')
            handoff = read('state/local_continuation_v2/handoff.json')
            if (status.get('status') == 'WAITING_WORKER' and status.get('exact_handle_retained') is True
                    and status.get('event_sha256') == EVENT and handoff.get('responding_to_event_sha256') == EVENT
                    and status.get('handoff_sha256') == dispatcher.digest(R / 'state/local_continuation_v2/handoff.json')
                    and all(status.get('worker', {}).get(k) == v and handoff.get('worker', {}).get(k) == v for k, v in owner.items())):
                create(E / 'V2_retained_owner_ack.json', {'observed_utc': dispatcher.utc(), 'native_owner': owner,
                       'dispatcher_identity': expected, 'status_observed': status, 'no_AI_polling': True})
                return
            time.sleep(0.1)
    finally:
        win.close(handle)


def n5_shape(relative, item, names):
    keys = set(item)
    name = Path(relative).name
    status = item.get('status')
    extracted = history.accessions(item)
    if extracted - names:
        raise RuntimeError('N5 history names outside its actual five inputs: ' + relative)
    if name == 'execution.json':
        valid = status == 'UNIT_EXIT0_GROUP_CLOSED' and type(item.get('exit_code')) is int and item['exit_code'] == 0 and item.get('owned_group_empty') is True and item.get('remaining_owned_processes') == []
    elif name == 'once_claim.json':
        valid = {'accession', 'input_plan_sha256', 'native_launch_token', 'phase_order'} <= keys or {'accessions', 'input_plan_sha256', 'native_launch_token', 'phase'} <= keys
    elif 'commit' in name:
        valid = status in {'N5_ANNOTATION_UNIT0_COMMITTED_PENDING_CONTEXT_CLOSURE', 'N5_DIAMOND_UNIT0_COMMITTED_PENDING_CONTEXT_CLOSURE', 'N5_STOCK_RESUME_EXIT0_FEATURE_VALIDATION_PENDING', 'N5_FRESH_PHASE_SEPARATED_ROW_VALIDATED_PENDING_NATIVE_CLOSURE'} and item.get('accession') in names
    elif name == 'original_preclaim_audit_failure.json':
        valid = status == 'N5_SUCCESS_AUDIT_HELD_NO_FINALIZER_OR_RETRY' and 'actual_children' in item
    else:
        # Unchanged structural readers handle shared commands, bindings and owner claims.
        return history.known_shape(relative, item)
    if not valid:
        raise RuntimeError('Unknown N5 history body: ' + relative)
    return {'reader': 'EXPLICIT_N5_CLOSED_RECEIPT_SHAPE_P1', 'status': status, 'keys': sorted(keys)}


def build(spec, owner, deadline):
    registry = read(bind(spec['accepted_registry']))
    accepted_rows = registry['rows'] + [registry['additional_baseline']]
    accepted = {x['accession']: x for x in accepted_rows}
    if len(accepted) != 17 or len(accepted_rows) != 17:
        raise RuntimeError('Expected17 unique accepted method estimates including baseline')
    all_sources = read(bind(spec['source_audit']))['records']
    supported = [x for x in all_sources if x['production_disposition'] == 'SOURCE_SUPPORTED_BIOLOGICAL_QC_NOT_RUN']
    if len(supported) != 919:
        raise RuntimeError('Source-supported denominator changed')
    candidates = {x['accession']: x for x in read(bind(spec['candidates']))}
    scope = read(bind(spec['scope95']))
    priority_accessions = set(scope['deferred95_accessions'])
    priority_taxids = set(scope['priority92_species_taxids'])
    if len(priority_accessions) != 95 or len(priority_taxids) != 92:
        raise RuntimeError('Priority95/92 scope changed')
    n5 = read(bind(spec['N5_acceptance']))
    n5_names = {x['accession'] for x in n5['rows']}
    old_history = read(bind(spec['N5_history']))
    prior_inputs = set(old_history['accepted_method_accessions']) | set(old_history['prior_annotation_only_accessions']) | n5_names
    excluded = set(old_history['excluded_prior_accessions_and_paired_aliases']) | set(accepted) | prior_inputs
    pilot = set()
    for record in old_history['prior_pilot10_plans']:
        pilot.update(read(bind(record))['accessions'])
    cohort = set(read('metadata/checkm2_accepted_method_result_registry_v001.json')['accepted_unique_cohort_accessions'])
    groups = {'pilot': pilot, 'baseline': {registry['additional_baseline']['accession']}, 'n1': {'GCF_900636575.1'}, 'cohort': cohort}
    records = []
    for relative, namespace in history.inventory():
        gate(deadline)
        item = read(relative)
        extracted = history.accessions(item)
        if namespace == 'checkm2_phase_separated_N5':
            shape = n5_shape(relative, item, n5_names)
            bounded = n5_names
            kind = 'CLOSED_N5_EXACT_FIVE_PRESERVED'
        elif namespace in history.GENOMIC:
            shape = history.known_shape(relative, item)
            bounded = groups[history.GENOMIC[namespace]]
            kind = 'PREVIOUS_SCIENTIFIC_INPUT_HISTORY_PRESERVED'
        elif namespace in history.ENGINEERING:
            shape = history.known_shape(relative, item)
            bounded = set()
            kind = 'KNOWN_ENGINEERING_NAMESPACE_NO_NEW_GENOME'
        elif namespace == 'checkm2_N5_event_closure_owner_v001':
            if item.get('schema') != 'TREE2_N5_EVENT_CLOSURE_OWNER_LAUNCH_V001' or item.get('audit_scientific_work_authorized') is not False or extracted:
                raise RuntimeError('Historical operational owner shape changed')
            shape = {'reader': 'EXPLICIT_HISTORICAL_EMPTY_AUDIT_OWNER', 'historical_native_exit': 'UNKNOWN_PRESERVED', 'no_audit_child_started': True}
            bounded = set()
            kind = 'ROOT_RECOVERED_EMPTY_OPERATIONAL_OWNER_NO_SCIENCE'
        elif namespace == 'checkm2_production_preparation_P1':
            if item.get('role') != ROLE or item.get('scientific_execution_authorized') is not False or item.get('native_owner') != owner or extracted:
                raise RuntimeError('Own source-only launch shape changed')
            shape = {'reader': 'EXACT_CURRENT_METADATA_ONLY_OWNER'}
            bounded = set()
            kind = 'CURRENT_METADATA_ONLY_OWNER_NOT_A_SCIENTIFIC_CLAIM'
        else:
            raise RuntimeError('Unknown historical namespace blocks selection: ' + namespace)
        if extracted - excluded - n5_names:
            raise RuntimeError('Unreconciled historical accession: ' + relative)
        excluded.update(extracted | bounded)
        records.append({'artifact': row(relative), 'namespace': namespace, 'shape': shape, 'classification': kind,
                        'schema_field_accessions': sorted(extracted), 'conservatively_bound_inputs': sorted(bounded)})
    for accession in list(excluded):
        if candidates.get(accession, {}).get('paired_accession'):
            excluded.add(candidates[accession]['paired_accession'])
    dna = {}
    donor_rows = []
    for accession in sorted(prior_inputs):
        gate(deadline)
        p = f'raw/{accession}/acquisition_receipt.json'
        acquisition = read(p)
        files = [x for x in acquisition['files'] if x['path'].endswith('_genomic.fna') and 'cds_from' not in x['path']]
        if len(files) != 1:
            raise RuntimeError('Historical donor FNA receipt ambiguous')
        dna[accession] = files[0]['sha256']
        donor_rows.append({'accession': accession, 'acquisition_receipt': row(p), 'FNA_sha256_from_receipt': files[0]['sha256']})
    ledger = []
    families = Counter(candidates[a]['family'] for a in accepted)
    genera = Counter(candidates[a]['genus'] for a in accepted)
    measured_labels = {candidates[a]['species_taxid'] for a in accepted}
    for number, source in enumerate(sorted(supported, key=lambda x: x['accession'])):
        gate(deadline)
        accession = source['accession']
        item = candidates[accession]
        acquisition_path = f'raw/{accession}/acquisition_receipt.json'
        acquisition = read(acquisition_path)
        if row(acquisition_path)['sha256'] != source['acquisition_receipt_sha256'] or acquisition['acquisition_status'] != 'PASS':
            raise RuntimeError('Committed acquisition/source binding changed')
        files = [x for x in acquisition['files'] if x['path'].endswith('_genomic.fna') and 'cds_from' not in x['path']]
        if len(files) != 1:
            raise RuntimeError('Own acquired genomic FNA receipt ambiguous')
        fna = {'path': f'raw/{accession}/' + files[0]['path'], 'sha256': files[0]['sha256'], 'bytes': files[0]['bytes']}
        measured = accepted.get(accession)
        historical = accession in excluded or item.get('paired_accession') in excluded or fna['sha256'] in dna.values()
        ledger.append({'accession': accession, 'species': item['species'], 'species_taxid': item['species_taxid'],
                       'family': item['family'], 'genus': item['genus'], 'assembly_level': item['assembly_level'],
                       'metadata_qc': item['metadata_qc'], 'priority95_lane': accession in priority_accessions,
                       'priority92_label': item['species_taxid'] in priority_taxids,
                       'empirical_status': 'ACCEPTED_METHOD_ESTIMATE_FOR_REUSE_ONLY' if measured else 'UNKNOWN_NOT_MEASURED_OR_NOT_ACCEPTED',
                       'Completeness': measured['Completeness'] if measured else None,
                       'Contamination': measured['Contamination'] if measured else None,
                       'historical_input_or_DNA_alias_excluded_from_fresh_batch': historical,
                       'acquisition_receipt': row(acquisition_path), 'FNA_from_receipt': fna,
                       'source_holds_preserved': source['holds_or_exclusions'], 'source_pending_reasons': item['pending_reasons'],
                       'source_masks': {'source_ANI_status': item['ncbi_ani_taxonomy_status'], 'independent_taxonomy': 'UNRESOLVED_NOT_ACCEPTED',
                                        'source_type_assertion_not_independently_accepted': item.get('type_material', False), 'production_acceptance': False},
                       'production_panel_acceptance': False, 'defence_status': 'UNKNOWN_UNSEARCHED'})
        if number % 200 == 0:
            publish(owner, 'RUNNING', f'Building source-supported empirical coverage ledger: {number + 1}/919 metadata rows; no FASTA parse or science', number + 1, 919)
    if {x['accession'] for x in ledger if x['priority95_lane']} != priority_accessions:
        raise RuntimeError('Every supported priority95 input must remain represented')
    eligible = [x for x in ledger if not x['historical_input_or_DNA_alias_excluded_from_fresh_batch'] and x['empirical_status'].startswith('UNKNOWN')]
    rank = {'Complete Genome': 0, 'Chromosome': 1, 'Scaffold': 2, 'Contig': 3}
    selected = []
    selected_labels = set()
    while len(selected) < 20:
        remaining = [x for x in eligible if x['species_taxid'] not in selected_labels and x['species_taxid'] not in measured_labels]
        if not remaining:
            raise RuntimeError('Fewer than20 distinct fresh unmeasured species labels')
        chosen = min(remaining, key=lambda x: (not x['priority95_lane'], not x['priority92_label'], families[x['family']], genera[x['genus']],
                                               x['family'].casefold(), x['genus'].casefold(), x['species_taxid'], rank.get(x['assembly_level'], 4), x['accession']))
        selected.append(chosen)
        selected_labels.add(chosen['species_taxid'])
        families[chosen['family']] += 1
        genera[chosen['genus']] += 1
    gate(deadline)
    OUT.mkdir(exist_ok=False)
    history_ref = create(OUT / 'history.json', {'schema': 'TREE2_PRODUCTION_QC_BOUNDED_HISTORY_P1_V001',
        'accepted_registry': spec['accepted_registry'], 'N5_closed_authority': spec['N5_acceptance'], 'inventory': records,
        'excluded_prior_accessions_and_paired_aliases': sorted(excluded), 'DNA_donors_from_receipts_only': donor_rows,
        'unresolved_history': [], 'old_empty_helper_actual_exit': 'UNKNOWN_PRESERVED_NO_SCIENTIFIC_CHILD',
        'original_claims_debits_unchanged': True, 'raw_FNA_content_opened': False})
    accepted_supported = [x for x in ledger if x['empirical_status'].startswith('ACCEPTED')]
    summary = {'source_supported': 919, 'accepted_unique_method_estimates_all_sources': len(accepted),
               'accepted_method_estimates_source_supported': len(accepted_supported), 'priority95_total': 95,
               'priority95_accepted_method_estimates': sum(x['priority95_lane'] for x in accepted_supported),
               'priority95_unknown': sum(x['priority95_lane'] and x['empirical_status'].startswith('UNKNOWN') for x in ledger),
               'fresh_unmeasured_candidates': len(eligible), 'next_proposed_distinct_species_inputs': 20,
               'final_panel_acceptance': False, 'whole_stage_biological_QC_complete': False}
    ledger_ref = create(OUT / 'coverage_and_queue.json', {'schema': 'TREE2_PRODUCTION_QC_COVERAGE_QUEUE_P1_V001',
        'summary': summary, 'history': history_ref, 'rows': ledger, 'next_proposed_accessions': [x['accession'] for x in selected],
        'other_source_dispositions_preserved_for_separate_review': [
            {'accession': x['accession'], 'production_disposition': x['production_disposition'],
             'holds_or_exclusions': x['holds_or_exclusions'], 'empirical_status': 'UNKNOWN_OR_SEPARATE_ACCEPTED_METHOD_CONTEXT_NOT_SOURCE_ACCEPTANCE',
             'defence_status': 'UNKNOWN_UNSEARCHED'} for x in all_sources if x not in supported],
        'selection_policy': 'Fresh distinct unmeasured species first; priority95/92 lane; dynamic accepted-plus-selected family/genus balancing; assembly preference; deterministic accession tie break',
        'numeric_metadata_scores_used_for_selection': False, 'unknown_failed_unrun_as_negative': False})
    design_ref = create(OUT / 'next_batch_design_HELD.json', {'schema': 'TREE2_NEXT_PHASE_SEPARATED_QC_BATCH_DESIGN_P1_V001',
        'status': 'HELD_CONCRETE_SOURCE_AND_INPUT_PREPARATION_NO_SCIENTIFIC_ADMISSION', 'queue': ledger_ref, 'history': history_ref,
        'inputs': selected, 'maximum_fresh_inputs': 20, 'maximum_scientific_units': 80,
        'strategy': 'Accepted N5 four serial original phases per own input; original annotation180s, model-free DIAMOND600s, stock genes/resume600s, full own-row validation30s; one input per ML invocation',
        'proposed_new_scientific_seconds': 28200, 'proposed_new_cold_seconds': 33000,
        'existing_N5_or_N1_remaining_allowance_borrowed': False,
        'resource_limits': {'cpu_affinity_max': 2, 'stock_threads': 1, 'sum_owned_RSS_bytes': 2147483648,
                            'linux_available_minimum_bytes': 1073741824, 'disk_reserve_bytes': 42949672960},
        'required_before_science': ['New immutable history-aware source/input recipe and manifest', 'Scientific ABI/own-row/no-replay and lifecycle/budget review',
                                   'New LF shell no-CR and bash-n checks plus explicit env direct observer', 'Fresh resource/exclusivity/lease preflight and separate Root scientific admission'],
        'old_sources_claims_debits_and_accepted_rows_must_remain_unchanged': True,
        'first_failure_STOP_preserve_all_partial_phase_commits': True, 'automatic_retry_fallback_or_accepted_row_recalculation': False,
        'source_taxonomy_or_panel_acceptance': False, 'raw_FNA_integrity_read': 'NOT_PERFORMED_IN_THIS_METADATA_ONLY_WORKER'})
    return summary, [history_ref, ledger_ref, design_ref]


def main(args):
    if os.name != 'nt' or os.environ.get('COMPUTERNAME', '').upper() != 'WD':
        raise RuntimeError('WD-only preparation owner')
    if dispatcher.digest(inside(args.admission)) != args.admission_sha256:
        raise RuntimeError('Preparation authority SHA mismatch')
    spec = read(args.admission)
    if spec['status'] != 'ROOT_ADMITTED_ONE_METADATA_ONLY_PRODUCTION_QC_PREPARATION_P1' or spec['event_sha256'] != EVENT:
        raise RuntimeError('Exact preparation authority absent')
    for value in spec['bound_inputs']:
        bind(value)
    win = dispatcher.Windows()
    mask = affinity(win)
    owner = win.identity(win.k.GetCurrentProcess(), os.getpid())
    lock = (R / 'state/checkm2_production_preparation_P1.lock').open('a+b')
    if lock.tell() == 0:
        lock.write(b'0')
        lock.flush()
    lock.seek(0)
    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    result = None
    error = None
    code = 2
    try:
        create(LAUNCH, {'schema': 'TREE2_PRODUCTION_PREPARATION_P1_LAUNCH_V001', 'native_owner': owner, **owner,
            'role': ROLE, 'script': str(Path(__file__).resolve()), 'source': row(Path(__file__).resolve()),
            'admission': row(args.admission), 'started_utc': START, 'affinity_mask': mask,
            'attach_timeout_seconds': 180, 'metadata_work_timeout_seconds': 120,
            'scientific_execution_authorized': False, 'no_subprocess_runtime_model_or_raw_sequence_reads': True,
            'stdout': str(E / 'owner.stdout.txt'), 'stderr': str(E / 'owner.stderr.txt')})
        publish(owner, 'WAITING_DISPATCHER_ATTACH', 'Preparing empirical coverage for919 supported genomes after accepted N5; waiting for exact V2 retained owner acknowledgment', 0, 919)
        wait_for_v2(win, owner, spec)
        deadline = time.monotonic() + 120
        for value in spec['bound_inputs']:
            gate(deadline)
            bind(value)
        summary, artifacts = build(spec, owner, deadline)
        for value in spec['bound_inputs']:
            gate(deadline)
            bind(value)
        result = {'status': 'P1_METADATA_COVERAGE_HISTORY_AND_NEXT_BATCH_DESIGN_READY_FOR_ROOT_REVIEW',
                  'summary': summary, 'artifacts': artifacts, 'scientific_execution_authorized': False}
        create(E / 'result.json', result)
        code = 0
    except BaseException as failure:
        error = {'type': type(failure).__name__, 'error': str(failure), 'traceback': traceback.format_exc()}
    finally:
        try:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            lock.close()
        terminal = {'schema': 'TREE2_PRODUCTION_PREPARATION_P1_TERMINAL_V001',
                    'status': result['status'] if result else 'FAILED_PREPARATION_PRESERVE_NO_RETRY',
                    'native_owner': owner, 'actual_native_exit': 'PENDING_V2_RETAINED_HANDLE_EVENT',
                    'ended_utc': dispatcher.utc(), 'elapsed_seconds': time.monotonic() - STARTED,
                    'result': row(E / 'result.json') if result else None, 'error': error,
                    'own_native_lease_released_descriptor_closed': True, 'child_processes_started': 0,
                    'maximum_native_owned_RSS_bytes': PEAK_NATIVE_RSS, 'RSS_metric': 'Peak native owner working set; this worker has no children',
                    'Linux_headroom': 'NOT_MEASURED_NO_LINUX_WORK_STARTED',
                    'runtime_mounts_models_search_annotation_or_pickle_reads': False,
                    'accepted_results_or_original_claims_debits_modified': False, 'whole_stage_QC_or_panel_acceptance': False}
        create(E / 'terminal.json', terminal)
        publish(owner, 'PENDING_PREPARATION_NATIVE_EXIT_AND_ROOT_REVIEW' if code == 0 else 'FAILED_PREPARATION',
                'Empirical coverage/history ledger and concrete next20-input design frozen; source implementation, fresh gates and separate scientific admission remain pending' if code == 0 else 'Metadata preparation failed; preserve exact error and outputs; no automatic retry or science',
                919 if code == 0 else 0, 919, row(E / 'terminal.json'))
        print(json.dumps(terminal), flush=True)
    return code


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--admission', required=True)
    p.add_argument('--admission-sha256', required=True)
    raise SystemExit(main(p.parse_args()))
