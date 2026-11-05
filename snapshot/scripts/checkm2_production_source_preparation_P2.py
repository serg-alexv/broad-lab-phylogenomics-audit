"""Prepare an isolated P20 source/input contract; never dispatch science or WSL."""
from pathlib import Path
import argparse
import ast
import copy
import csv
import difflib
import importlib
import io
import json
import msvcrt
import os
import sys
import time
import tokenize
import traceback
import checkm2_production_preparation_P1 as p

R = p.R
E = R / 'evidence/checkm2_production_source_preparation_P2'
M = R / 'metadata/checkm2_phase_separated_P20_preparation'
ROLE = 'P20_SOURCE_INPUT_CONTRACT_PREPARATION_ONLY'
LAUNCH = R / 'state/launch_checkm2_production_source_preparation_P2.json'
EVENT = 'bf6561082c2faf9f9e53cba74c4bdcb5b5ec2f46c82469a4bde416b71f8d5ea1'
p.E = E
p.ROLE = ROLE
p.EVENT = EVENT

HISTORY_GATE = '''def history_gate(recipe):
 history=read(bind(recipe['history']));selected=read(bind(recipe['selected_inputs']));bind(recipe['queue']);bind(recipe['N1_closed_acceptance']);bind(recipe['N5_closed_acceptance']);bind(recipe['accepted_method_registry'])
 names=[x['accession']for x in recipe['inputs']];actuals=selected.get('actual_selected_FNAs')
 if history.get('unresolved_history')!=[]or len(names)!=20 or len(set(names))!=20 or len({x['species_taxid']for x in recipe['inputs']})!=20 or names!=[x['accession']for x in selected['inputs']]or names!=recipe['inference_order']or not isinstance(actuals,list)or len(actuals)!=20:raise RuntimeError('P20 exact20 distinct novel own inputs/order required')
 donors={x['FNA_sha256_from_receipt']for x in history['DNA_donors_from_receipts_only']}
 for item,actual in zip(recipe['inputs'],actuals):
  if item['accession']in history['excluded_prior_accessions_and_paired_aliases']or item['fasta_sha256']in donors or actual['accession']!=item['accession']or actual['FNA']['sha256']!=item['fasta_sha256']:raise RuntimeError('Previously claimed, DNA alias or changed P20 input')
  observed=read(bind(actual['integrity_observation']))
  if observed['status']!='HASHED_ONCE_SHA256_SIZE_MATCH'or observed['actual_sha256']!=item['fasta_sha256']or observed['actual_bytes']!=item['fasta_bytes']:raise RuntimeError('P20 own acquired FNA integrity observation absent')
 for record in history['claim_inventory']:bind(record['artifact'])
 import prepare_checkm2_phase_separated_history_N5 as index
 old_paths={x['artifact']['path']for x in history['claim_inventory']};current_paths={x[0]for x in index.inventory()}
 def own(n):return n.startswith(('analysis/checkm2_phase_separated_P20/','evidence/checkm2_phase_separated_P20/','state/checkm2_phase_separated_P20_launch_requests/'))or n=='state/launch_checkm2_phase_separated_P20.json'
 if {x for x in current_paths if not own(x)}!=old_paths:raise RuntimeError('P20 authoritative history inventory changed; no silent inventory omission or reselection')
 registry=read(bind(history['registry']));prior={x['accession']for x in registry['rows']}|{registry['additional_baseline']['accession']}
 if set(names)&prior:raise RuntimeError('Accepted/control donor row cannot replay')
 for key in('manifest','commit','genomes_tsv'):bind(recipe['nomenclature_type_hold_context'][key])
 return selected

'''


def publish(owner, detail, done, status='RUNNING', terminal=None):
    p.dispatcher.atomic(R / 'state/stages/04.json', {
        'id': '04', 'name': 'Independent biological QC', 'status': status,
        'started_utc': p.START, 'updated_utc': p.dispatcher.utc(), 'ended_utc': None,
        'pid': owner['pid'], 'creation_time_utc': owner['creation_time_utc'],
        'windows_creation_filetime_100ns': owner['windows_creation_filetime_100ns'],
        'operation': ROLE, 'done': done, 'total': 7, 'unit': 'P20 source/input preparation gates',
        'detail': detail, 'log_path': str(E / 'owner.stdout.txt'), 'terminal_receipt': terminal,
        'scientific_execution_authorized': False, 'whole_stage_QC_acceptance': False, 'production_panel_acceptance': False})


def source_write(path, text):
    raw = text.encode('utf-8')
    if b'\r' in raw:
        raise RuntimeError('New source must contain explicit LF bytes')
    with path.open('xb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    return p.row(path)


def numbered(source, mapping):
    result = []
    changes = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.NUMBER and token.string in mapping:
            changes.append({'line': token.start[0], 'old': token.string, 'new': mapping[token.string]})
            token = token._replace(string=mapping[token.string])
        result.append(token)
    return tokenize.untokenize(result), changes


def once(source, old, new):
    if source.count(old) != 1:
        raise RuntimeError('Exact source adaptation occurrence differs: ' + old)
    return source.replace(old, new)


def derive(deadline):
    changes = []
    generated = []
    limits = {'5': '20', '7050': '28200', '9000': '33000'}
    maps = {'common': limits,
            'native': {'5': '20', '9000': '33000', '7760': '31760', '8960': '32960'},
            'entry': {'5': '20', '9000': '33000', '7760': '31760'},
            'inner': {'5': '20', '7050': '28200', '9000': '33000', '7760': '31760', '7760.01': '31760.01'},
            'close': {'5': '20', '20': '80', '106205': '424820', '110': '440', '6100': '24400'}}
    for name in ('common', 'native', 'entry', 'inner', 'annotation', 'diamond', 'feature_validator', 'close'):
        p.gate(deadline)
        original = R / f'scripts/checkm2_phase_separated_{name}_N5.py'
        old = original.read_text(encoding='utf-8-sig')
        new = old.replace('N5', 'P20').replace('FIVE', 'TWENTY').replace('five', 'twenty')
        new, numeric = numbered(new, maps.get(name, {}))
        extra = []
        if name == 'common':
            start = new.index('def history_gate(recipe):')
            end = new.index('def plan_gate(', start)
            new = new[:start] + HISTORY_GATE + new[end:]
            new = new.replace('n5_execution_authorized', 'p20_execution_authorized')
            extra.append('Replace immutable history/accepted-registry gate with P1 full311 history plus current source-owner receipt; no N5 inventory omissions')
        elif name == 'native':
            new = once(new, 'time.monotonic()-last>2:', 'time.monotonic()-last>30:')
            extra.append('Presentation interval30; retained handle/ownership polling remains0.3s')
        elif name == 'entry':
            new = once(new, 'time.monotonic() - last > 3:', 'time.monotonic() - last > 30:')
            new = once(new, 'def publish(launch, detail, cached=None, **extra):\n',
                       'def publish(launch, detail, cached=None, **extra):\n'
                       '    now = time.monotonic()\n'
                       "    if now - CONTEXT.get('presentation_last_monotonic', -1000) < 30:\n"
                       '        return\n'
                       "    CONTEXT['presentation_last_monotonic'] = now\n")
            extra.append('Presentation publishes30s; memory/STOP/hash checks and helper ownership census retain original cadence')
        elif name == 'close':
            new = new.replace('20 real units', '80 real units').replace('exact20 genuine', 'exact80 genuine').replace('actual20-unit', 'actual80-unit')
        if name in ('annotation', 'diamond', 'feature_validator'):
            expected = ast.dump(ast.parse(old.replace('N5', 'P20')), include_attributes=False)
            if ast.dump(ast.parse(new), include_attributes=False) != expected:
                raise RuntimeError('Original scientific body changed beyond new namespace: ' + name)
        ast.parse(new)
        target = R / f'scripts/checkm2_phase_separated_{name}_P20.py'
        generated.append(source_write(target, new))
        changes.append({'original': p.row(original), 'derived': p.row(target), 'numeric_constant_edits': numeric,
                        'namespace_and_scope_text_edits': ['N5 -> P20', 'five/FIVE -> twenty/TWENTY'], 'scoped_other_changes': extra,
                        'unified_diff': ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile=original.name, tofile=target.name))})
    shell = R / 'scripts/checkm2_phase_separated_N5.sh'
    target = R / 'scripts/checkm2_phase_separated_P20.sh'
    value = shell.read_text(encoding='utf-8-sig').replace('N5', 'P20')
    generated.append(source_write(target, value))
    if not target.read_bytes().startswith(b'#!/bin/bash\n') or b'\r' in target.read_bytes():
        raise RuntimeError('P20 shell LF bytes invalid')
    changes.append({'original': p.row(shell), 'derived': p.row(target), 'only_change': 'N5 -> P20 entry pathname; explicit LF bytes',
                    'actual_bash_n': 'NOT_RUN_REQUIRED_BEFORE_SHELL_ADMISSION'})
    return generated, changes


def fixtures(deadline):
    c = importlib.import_module('checkm2_phase_separated_common_P20')
    close = importlib.import_module('checkm2_phase_separated_close_P20')
    f = R / 'work/checkm2_P20_pure_source_fixtures_v001'
    f.mkdir(exist_ok=False)
    names = list(c.UNITS)
    for index in range(20):
        folder = f / 'rows' / f'SYNTHETIC_INPUT_{index:02d}'
        folder.mkdir(parents=True)
        for name in names:
            p.gate(deadline)
            unit = folder / name
            unit.mkdir()
            p.create(unit / 'command.json', {'SYNTHETIC_NOT_EXECUTED': True})
            p.create(unit / 'execution.json', {'elapsed_seconds': c.UNITS[name], 'owned_group_empty': True, 'remaining_owned_processes': []})
            p.create(folder / (name + '_budget.json'), {'SYNTHETIC_NOT_EXECUTED': True})
    budget = c.budget(f)
    if budget['cohort_scientific_seconds_debited'] != 28200 or budget['remaining_cohort_scientific_seconds'] != 0 or budget['new_allowance_seconds'] != 28200:
        raise RuntimeError('Independent new20-input allowance fixture failed')
    extra = f / 'rows/SYNTHETIC_INPUT_20'
    extra.mkdir()
    unit = extra / 'unit_annotation'
    unit.mkdir()
    p.create(unit / 'command.json', {'SYNTHETIC_NOT_EXECUTED': True})
    p.create(unit / 'execution.json', {'elapsed_seconds': 1, 'owned_group_empty': True, 'remaining_owned_processes': []})
    p.create(extra / 'unit_annotation_budget.json', {'SYNTHETIC_NOT_EXECUTED': True})
    try:
        c.budget(f)
    except RuntimeError:
        pass
    else:
        raise RuntimeError('21st input was not rejected')
    expected = {f / 'rows' / f'SYNTHETIC_INPUT_{index:02d}' / name for index in range(20) for name in names}
    close.normalized_invocations([str(x) for x in expected], expected)
    for invalid in ([str(x) for x in list(expected)[:-1]], [str(next(iter(expected)))] * 80):
        try:
            close.normalized_invocations(invalid, expected)
        except RuntimeError:
            pass
        else:
            raise RuntimeError('Missing/duplicate invocation fixture was accepted')
    if c.LIMITS['sum_group_RSS_bytes'] != 2147483648 or c.LIMITS['cpu_affinity_max'] != 2 or c.LIMITS['stock_threads'] != 1 or c.UNITS != {'unit_annotation': 180, 'unit_diamond': 600, 'unit_resume': 600, 'unit_feature_validation': 30}:
        raise RuntimeError('Unchanged per-input/resource ceilings differ')
    return {'status': 'PURE_SYNTHETIC_SOURCE_FIXTURES_PASS_NO_EXECUTABLE_OR_GENOME_RUN', 'cohort20_at_exact28200_pass': True,
            'twenty_first_input_rejected': True, 'exact80_distinct_phase_paths_required': True,
            'missing_and_duplicate_invocations_rejected': True, 'scientific_phase_bodies_namespace_only_AST_equivalence': True,
            'AA20_and_feature21241_22_1220_constants_unchanged': True, 'resource_and_per_input_limits_unchanged': True,
            'N1_N5_allowance_borrowed': False, 'fixture_directory': f.relative_to(R).as_posix()}


def build(spec, owner, deadline):
    authority = p.read(p.bind(spec['P20_source_authority']))
    design = p.read(p.bind(spec['P1_design']))
    old_history = p.read(p.bind(spec['P1_history']))
    registry = p.read(p.bind(spec['accepted_registry']))
    names = [x['accession'] for x in design['inputs']]
    if names != authority['input_selection_frozen_to'] or len(names) != 20 or len(set(names)) != 20:
        raise RuntimeError('P1 selected20 immutable order differs')
    if set(names) & set(old_history['excluded_prior_accessions_and_paired_aliases']):
        raise RuntimeError('Prior scientific input selected for replay')
    M.mkdir(exist_ok=False)
    p.create(M / 'selection_claim.json', {'source_authority': spec['P20_source_authority'], 'accessions': names,
             'FNA_receipt_rows': [x['FNA_from_receipt'] for x in design['inputs']], 'scientific_execution_authorized': False})
    publish(owner, 'Frozen source-only20-input selection; preserving all311 original claim/debit receipts and17 accepted method estimates', 1)
    actual = []
    for member in design['inputs']:
        p.gate(deadline)
        expected = member['FNA_from_receipt']
        observation = M / (member['accession'] + '_integrity.json')
        p.create(observation, {'status': 'HASH_IN_PROGRESS_NO_AUTOMATIC_RETRY', 'expected': expected})
        file = p.inside(expected['path'])
        digest = p.dispatcher.digest(file)
        if digest != expected['sha256'] or file.stat().st_size != expected['bytes']:
            raise RuntimeError('Selected acquired FNA checksum/size changed')
        p.dispatcher.atomic(observation, {'status': 'HASHED_ONCE_SHA256_SIZE_MATCH', 'expected': expected,
            'actual_sha256': digest, 'actual_bytes': file.stat().st_size, 'FNA_sequence_parsed': False,
            'scientific_annotation_search_prediction_or_model_import': False})
        actual.append({'accession': member['accession'], 'FNA': expected, 'integrity_observation': p.row(observation)})
    publish(owner, 'All20 acquired FNA hashes match their original receipts; deriving isolated P20 source namespace with unchanged scientific bodies', 2)
    generated, changes = derive(deadline)
    derivation = p.create(E / 'source_derivation.json', {'changes': changes, 'historical_source_overwritten': False})
    publish(owner, 'Eight P20 Python components and explicit-LF shell derived; full changes recorded; no new executable invoked', 3)
    current = dict(p.history.inventory())
    old_paths = {x['artifact']['path'] for x in old_history['inventory']}
    own_launch = LAUNCH.relative_to(R).as_posix()
    if set(current) != old_paths | {own_launch}:
        raise RuntimeError('Unexpected current scientific/operational inventory change')
    launch = p.read(LAUNCH)
    if launch['native_owner'] != owner or launch['scientific_execution_authorized'] is not False:
        raise RuntimeError('Current source-only owner receipt differs')
    history_value = {'schema': 'TREE2_P20_COMPLETE_NOVELTY_HISTORY_V001', 'registry': spec['accepted_registry'],
        'parent_P1_history': spec['P1_history'], 'claim_inventory': old_history['inventory'] + [
            {'artifact': p.row(LAUNCH), 'namespace': 'checkm2_production_source_preparation_P2', 'classification': 'SOURCE_ONLY_CURRENT_OWNER_NO_SCIENCE'}],
        'excluded_prior_accessions_and_paired_aliases': old_history['excluded_prior_accessions_and_paired_aliases'],
        'DNA_donors_from_receipts_only': old_history['DNA_donors_from_receipts_only'], 'unresolved_history': [],
        'historical_unknown_exit_preserved': True, 'new_scientific_claim_or_debit_consumed': False}
    history_ref = p.create(M / 'history.json', history_value)
    recipe = copy.deepcopy(p.read('metadata/checkm2_phase_separated_recipe_N5.json'))
    type_context = recipe['nomenclature_type_hold_context']
    with p.bind(type_context['genomes_tsv']).open(encoding='utf-8-sig', newline='') as handle:
        hold_rows = {x['accession']: x for x in csv.DictReader(handle, delimiter='\t')}
    inputs = []
    for member in design['inputs']:
        fna = member['FNA_from_receipt']
        masks = dict(member['source_masks'])
        masks.update(source_holds=member['source_holds_preserved'], independent_biology='NOT_PREDICTED_BY_PRIOR_HISTORY',
                     nomenclature_type_hold_record=hold_rows.get(member['accession']), production_acceptance=False)
        inputs.append({'accession': member['accession'], 'species': member['species'], 'species_taxid': member['species_taxid'],
            'family': member['family'], 'genus': member['genus'], 'fasta_path': fna['path'], 'fasta_sha256': fna['sha256'],
            'fasta_bytes': fna['bytes'], 'role': 'NOVEL_PHASE_SEPARATED_P20_SERIAL_QUALIFICATION', 'metadata_qc': member['metadata_qc'],
            'selection_status': 'PROVISIONAL_ACQUISITION_ONLY', 'source_disposition': 'SOURCE_SUPPORTED_BIOLOGICAL_QC_NOT_RUN',
            'source_holds_preserved': member['source_holds_preserved'], 'source_pending_reasons': member['source_pending_reasons'], 'source_masks': masks})
    type_context['selected_recorded_crosswalk_hold_by_accession'] = {x: x in hold_rows for x in names}
    selected_ref = p.create(M / 'selected_inputs.json', {'schema': 'TREE2_P20_SELECTED_INPUTS_V001',
        'status': 'TWENTY_FRESH_INPUTS_INTEGRITY_BOUND_SOURCE_ONLY', 'inputs': inputs, 'actual_selected_FNAs': actual,
        'selection_claim': p.row(M / 'selection_claim.json'), 'scientific_execution_authorized': False})
    recipe.update(schema='TREE2_PHASE_SEPARATED_P20_RECIPE_V001', status='HELD_SOURCE_ONLY_NO_EXECUTION',
        role='PHASE_SEPARATED_P20_SERIAL_FEASIBILITY_ONLY', scope_authority=spec['P20_source_authority'],
        selected_inputs=selected_ref, history=history_ref, queue=spec['P1_queue'], inputs=inputs, inference_order=names,
        limits=authority['limits'], accepted_method_registry=spec['accepted_registry'], N5_closed_acceptance=spec['N5_acceptance'],
        maximum_scientific_units=80, scientific_execution_admission=None, unused_N5_or_N1_allowance_not_borrowed=True)
    recipe_ref = p.create(R / 'metadata/checkm2_phase_separated_recipe_P20.json', recipe)
    publish(owner, 'New20-input recipe/history masks and immutable selection bound; exercising synthetic80-unit budget and replay-guard fixtures', 4)
    fixture_ref = p.create(E / 'pure_source_fixtures.json', fixtures(deadline))
    publish(owner, 'Synthetic80-unit/28200s budget,21st-input and duplicate-path rejections passed; freezing source manifest and held plan', 5)
    old_source = p.read(p.bind(spec['N5_source_manifest']))
    sources = {x['path']: x for x in old_source['sources']}
    for value in sources.values():
        p.gate(deadline)
        p.bind(value)
    extras = [*generated, p.row(Path(__file__).resolve()), p.row(R / 'scripts/checkm2_production_preparation_P1.py'),
              spec['P20_source_authority'], spec['P1_acceptance'], spec['accepted_registry'], spec['N5_acceptance'],
              spec['P1_design'], spec['P1_history'], spec['P1_queue'], history_ref, selected_ref, recipe_ref, derivation, fixture_ref,
              *[p.row(x) for x in M.glob('*_integrity.json')], p.row(M / 'selection_claim.json')]
    for value in extras:
        p.bind(value)
        sources[value['path']] = value
    manifest_ref = p.create(R / 'metadata/checkm2_phase_separated_implementation_P20.json', {
        'schema': 'TREE2_PHASE_SEPARATED_P20_SOURCE_MANIFEST_V001', 'status': 'HELD_FROZEN_SOURCE_ONLY_NO_SCIENTIFIC_GRANT',
        'created_utc': p.dispatcher.utc(), 'accepted_N5_manifest': spec['N5_source_manifest'],
        'all_historical146_bytes_unchanged': True, 'sources': list(sources.values()), 'scope_authority': spec['P20_source_authority'],
        'derivation': derivation, 'pure_source_fixtures': fixture_ref, 'scientific_execution_authorized': False})
    session = p.hashlib.sha256(json.dumps({'source': manifest_ref['sha256'], 'recipe': recipe_ref['sha256'], 'accessions': names,
                                          'scope_authority': spec['P20_source_authority']['sha256']}, sort_keys=True).encode()).hexdigest()
    plan_ref = p.create(R / 'metadata/checkm2_phase_separated_execution_plan_P20.json', {
        'schema': 'TREE2_PHASE_SEPARATED_P20_INPUT_PLAN_V001', 'status': 'HELD_SOURCE_ONLY_NO_SCIENTIFIC_GRANT',
        'role': recipe['role'], 'scientific_recipe': recipe_ref, 'source_manifest': manifest_ref, 'selected_inputs': selected_ref,
        'feature_schema': recipe['schema_v002'], 'scope_authority': recipe['scope_authority'], 'limits': recipe['limits'],
        'session_identity_sha256': session, 'accessions': names, 'inputs': inputs, 'strict_serial_four_phases_per_input': True,
        'scientific_execution_authorized': False, 'actual_annotation_search_prediction_or_feature_outputs': None})
    template_ref = p.create(R / 'metadata/checkm2_phase_separated_admission_TEMPLATE_P20.json', {
        'schema': 'TREE2_PHASE_SEPARATED_P20_ADMISSION_V001', 'status': 'HELD_NOT_ADMITTED', 'role': recipe['role'],
        'p20_execution_authorized': False, 'phase': 'RUN_FRESH_SERIAL_TWENTY_ONCE', 'max_inputs': 20,
        'input_plan_sha256': plan_ref['sha256'], 'source_manifest_sha256': manifest_ref['sha256'], 'recipe_sha256': recipe_ref['sha256'],
        'limits': recipe['limits'], 'novel_selection_history_GO': None, 'source_math_ABI_GO': None, 'resource_lifecycle_GO': None,
        'monitor_standard_stage04_ready': False, 'actual_Root_scientific_authority': None, 'actual_prelaunch': None})
    publish(owner, 'P20 source/input contract frozen with20 masks,80-unit maximum and separate new budgets; shell syntax/transport and fresh OPS remain required', 6)
    c = importlib.import_module('checkm2_phase_separated_common_P20')
    c.history_gate(recipe)
    if c.LIMITS != recipe['limits']:
        raise RuntimeError('Generated code versus held plan resource/budget mismatch')
    for value in spec['bound_inputs']:
        p.gate(deadline)
        p.bind(value)
    return {'status': 'P20_SOURCES_AND_TWENTY_INPUT_CONTRACT_FROZEN_PENDING_ROOT_REVIEW_AND_ACTUAL_PREFLIGHT',
        'source_manifest': manifest_ref, 'plan': plan_ref, 'recipe': recipe_ref, 'selected_inputs': selected_ref,
        'history': history_ref, 'source_derivation': derivation, 'pure_source_fixtures': fixture_ref, 'admission_TEMPLATE_only': template_ref,
        'source_count': len(sources), 'selected_inputs_count': 20, 'maximum_scientific_units': 80,
        'actual_FNA_integrity_hashes_completed': 20, 'actual_FNA_sequence_parses': 0,
        'new_shell_CR_bytes': 0, 'actual_bash_n': 'NOT_RUN_REQUIRED_BEFORE_ADMISSION',
        'actual_env_transport_observer': 'NOT_RUN_REQUIRED_BEFORE_ADMISSION',
        'fresh_resource_exclusivity_and_common_leases': 'NOT_RUN_REQUIRED_BEFORE_SCIENTIFIC_ADMISSION',
        'scientific_Ready_issued': False, 'scientific_execution_authorized': False, 'runtime_model_search_annotation_pickle_or_WSL_executed': False,
        'new_cohort_scientific_seconds_proposed': 28200, 'new_cold_seconds_proposed': 33000,
        'prior_N1_N5_other_claims_debits_and_results_unchanged': True, 'source_type_taxonomy_masks_preserved': True}


def main(args):
    if os.name != 'nt' or os.environ.get('COMPUTERNAME', '').upper() != 'WD':
        raise RuntimeError('WD-only source preparation')
    if p.dispatcher.digest(p.inside(args.admission)) != args.admission_sha256:
        raise RuntimeError('Source preparation authority hash mismatch')
    spec = p.read(args.admission)
    if spec['status'] != 'ROOT_ADMITTED_ONE_P20_SOURCE_INPUT_PREPARATION_P2' or spec['event_sha256'] != EVENT:
        raise RuntimeError('Separate P2 source-only admission absent')
    for value in spec['bound_inputs']:
        p.bind(value)
    win = p.dispatcher.Windows()
    mask = p.affinity(win)
    owner = win.identity(win.k.GetCurrentProcess(), os.getpid())
    lock = (R / 'state/checkm2_production_source_preparation_P2.lock').open('a+b')
    if lock.tell() == 0:
        lock.write(b'0'); lock.flush()
    lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    code = 2
    result = None
    error = None
    try:
        p.create(LAUNCH, {'schema': 'TREE2_P20_SOURCE_PREPARATION_P2_LAUNCH_V001', 'native_owner': owner, **owner,
            'role': ROLE, 'script': str(Path(__file__).resolve()), 'source': p.row(Path(__file__).resolve()), 'admission': p.row(args.admission),
            'started_utc': p.START, 'affinity_mask': mask, 'attach_timeout_seconds': 180, 'source_work_timeout_seconds': 180,
            'scientific_execution_authorized': False, 'stdout': str(E / 'owner.stdout.txt'), 'stderr': str(E / 'owner.stderr.txt')})
        publish(owner, 'Source-only P20 preparation waiting for exact V2 retained-handle acknowledgment; no science', 0, 'WAITING_DISPATCHER_ATTACH')
        p.wait_for_v2(win, owner, spec)
        result = build(spec, owner, time.monotonic() + 180)
        p.create(E / 'result.json', result)
        code = 0
    except BaseException as failure:
        error = {'type': type(failure).__name__, 'error': str(failure), 'traceback': traceback.format_exc()}
    finally:
        try:
            lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            lock.close()
        terminal = {'schema': 'TREE2_P20_SOURCE_PREPARATION_P2_TERMINAL_V001',
            'status': result['status'] if result else 'FAILED_SOURCE_PREPARATION_PRESERVE_PARTIALS_NO_RETRY',
            'native_owner': owner, 'actual_native_exit': 'PENDING_V2_RETAINED_HANDLE_EVENT', 'ended_utc': p.dispatcher.utc(),
            'elapsed_seconds': time.monotonic() - p.STARTED, 'error': error, 'result': p.row(E / 'result.json') if result else None,
            'owner_lease_descriptor_released': True, 'child_processes_started': 0,
            'maximum_native_owned_RSS_bytes': p.PEAK_NATIVE_RSS, 'scientific_execution_authorized': False,
            'original_sources_claims_Ready_debits_or_accepted_results_modified': False}
        p.create(E / 'terminal.json', terminal)
        publish(owner, 'New P20 sources/20-input plan await native exit, Root review, actual LF/bash/env and fresh OPS admission' if code == 0 else 'P20 source preparation failed; preserve partials and claims; no retry or science',
                7 if code == 0 else 0, 'PENDING_SOURCE_NATIVE_EXIT_AND_ROOT_REVIEW' if code == 0 else 'FAILED_SOURCE_PREPARATION', p.row(E / 'terminal.json'))
        print(json.dumps(terminal), flush=True)
    return code


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--admission', required=True)
    parser.add_argument('--admission-sha256', required=True)
    raise SystemExit(main(parser.parse_args()))
