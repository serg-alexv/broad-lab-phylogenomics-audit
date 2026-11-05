"""Separately reviewed V008 defence activation candidate. Importing this module launches nothing.

Frozen Tree2 V3 methods own worker-exit events, CLI continuation and all science
gates. This adapter adds source wiring, Root-only admission and attach-only
startup, and changes only optional dispatcher status publication after startup.
It never imports or implements a scientific launcher.
"""
import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time
import uuid

if __package__:
    from .tree2_status_io_v008 import optional_status_replace
    from .tree2_activation_common_v008 import exclusive_json
else:
    from tree2_status_io_v008 import optional_status_replace
    from tree2_activation_common_v008 import exclusive_json


HARNESS = Path(__file__).resolve().parents[2]
TREE2 = HARNESS
AUTHORITY = HARNESS / 'metadata/defence_C008_recovery_20261105/controller_v008/Root_authority.json'
SUPERVISOR_CLAIM = HARNESS / 'metadata/defence_C008_recovery_20261105/controller_v008/code_repair_launch_claim.json'
DISPATCHER_CLAIM = HARNESS / 'metadata/defence_C008_recovery_20261105/controller_v008/dispatcher_start_claim.json'
CUSTODIAN_CLAIM = HARNESS / 'metadata/defence_C008_recovery_20261105/controller_v008/supervisor_creation_claim.json'
OPERATOR_LAUNCHER = HARNESS / 'scripts/defence_controller_v008/tree2_controller_launcher_v008.py'
EVENT_PROMPT = HARNESS / 'scripts/defence_controller_v008/tree2_v008_event_prompt.txt'
EVENT_PROMPT_SHA256 = '88cbb7ae6ae40236052e2639e278415c057dcbb3f388207df2a78f7f23cdfefb'
CONFIG = TREE2 / 'metadata/defence_C008_recovery_20261105/controller_v008/config.json'
HANDOFF = TREE2 / 'state/local_continuation_v8/handoff.json'
STATE = TREE2 / 'state/local_continuation_v8'
SOURCE_PINS = {
    'local_tree2_dispatcher': 'd87584a33086593b773ef7f2478ae56a970eb62985b0c2a7161349e453bc32f1',
    'local_tree2_dispatcher_v002': '44a206588b463507ef3172ca2a19e7c6b8eed4599efc8b928bd57324c6b18ff2',
    'local_tree2_dispatcher_io_recovery_v001': '26c9a8c46f7ace411ccf37c37e2eaf3e63a17354451e3ca86b78fe6b1cb9d582',
    'local_tree2_dispatcher_v003': 'cd5008154b83335e9fbf4a6f3a1732ca75e4a63bdacb7e1f83d1ee7dfdce70bb',
    'checkm2_optional_telemetry_v001': '561164f65f9ee0dd312cb7fd365312cc0a46c86485a3218382add15b630903ef',
    'checkm2_optional_progress_S1R2': 'a11fdae344e9c869cfba2f3bfa23c4c83d6e2c282103aa13bb9b0a3d5e71da72',
    'local_tree2_dispatcher_supervisor_v003': 'a21c82187045a1ff8a4f629d934d72e4d6f907147cab5a4c7b90aa2ec9eda3ba',
}
CANDIDATE_NAMES = ('tree2_status_io_v008.py', 'tree2_dispatcher_v008.py',
                   'tree2_supervisor_v008.py')
EXISTING_PRIVATE_CONFIG = {
    'path': 'work/local_continuation/private_invocation_v003.json',
    'sha256': '94ef185c8750519f3b86de0ea34a673378e6f112f9ddcd401243e35c0267a7d2',
    'bytes': 3858}
PYTHON_RUNTIME = {
    'path': r'C:\Users\wheel\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe',
    'sha256': '17e6b9d2e702b43fd88154d9df419d32eab10728151f81d921bf32684ffd459e',
    'bytes': 107312}
RECOVERY_DIRECTORY = TREE2 / 'metadata/defence_C008_recovery_20261105'
PRODUCTION_CONSTRAINTS = {
    'cohort': 'C008', 'historical_accessions': 20,
    'saved_PADLOC_phases': 9, 'previously_unrun_PADLOC_phases': 11,
    'previously_unrun_DefenseFinder_phases': 20,
    'historical_C008_deadline_unix': 1793856598.2600183,
    'historical_C008_scientific_seconds': 891.1653609039786,
    'historical_C008_cold_seconds': 923.4845150530164,
    'previous_defence_cumulative_scientific_seconds': 68216.74891608392,
    'previous_defence_cumulative_cold_seconds': 100395.33115186603,
    'stock_threads': 4, 'cpu_affinity': [0, 1, 2, 3],
    'linux_RSS_plus_RAM_bytes': 1879048192, 'minimum_linux_available_bytes': 1342177280,
    'native_plus_WSL_RSS_bytes': 134217728, 'backing_disk_reserve_bytes': 42949672960,
    'full_panel_final_acceptance': False, 'automatic_controller_or_science_retry': False,
}
REQUIRED_HISTORICAL_RECORDS = (
    'state/local_continuation_v7/dispatcher_status.json',
    'state/local_continuation_v7/handoff.json',
    'state/local_continuation_v7/supervisor_attempts/89a29bf321fd4889a7997725c1e425d3_actual_exit.json',
    'metadata/finalization_recovery_20261103/controller_v007/actual/supervisor_terminal.json',
    'state/defence_campaign_v001/failed_transactions/C008.json',
    'work/defence_C008_failed_c2ad/Root_C008_whole_owned_failure_closure.json',
    'recovery/defence_C008_failed_c2ad/SNAPSHOT_COMMITTED.json',
)

def file_row(path):
    path = Path(path).resolve()
    content = path.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(content).hexdigest(),
            'bytes': len(content)}


def require_row(row, expected):
    if not isinstance(row, dict) or row != file_row(expected):
        raise RuntimeError('Exact reviewed source/artifact row differs')
    return Path(expected).resolve()


def require_project_row(row, expected, b):
    path = b.bind(TREE2, row)
    if path != Path(expected).resolve():
        raise RuntimeError('Exact existing Tree2 artifact path differs')
    return path


def require_python_runtime():
    if Path(sys.executable).resolve() != Path(PYTHON_RUNTIME['path']).resolve():
        raise RuntimeError('Only the exact pinned current core Python runtime is admitted')
    require_row(PYTHON_RUNTIME, sys.executable)
    return PYTHON_RUNTIME


def require_runtime_sources(admission):
    require_python_runtime()
    from tree2_activation_common_v008 import source_status
    source_status(TREE2)
    expected_sources = {name: file_row(HARNESS / 'scripts/defence_controller_v008' / name)
                        for name in CANDIDATE_NAMES}
    if admission.get('candidate_sources') != expected_sources:
        raise RuntimeError('Actual V5 adapter dependency sources changed')
    if admission.get('legacy_source_sha256') != SOURCE_PINS:
        raise RuntimeError('Frozen legacy semantic source pins differ')
    for name, expected_sha in SOURCE_PINS.items():
        if file_row(TREE2 / 'scripts' / (name + '.py'))['sha256'] != expected_sha:
            raise RuntimeError('Frozen Tree2 source changed: ' + name)
    require_row(admission['event_prompt'], EVENT_PROMPT)
    if admission['event_prompt']['sha256'] != EVENT_PROMPT_SHA256:
        raise RuntimeError('The fixed V008 actual-event prompt changed')
    require_row(admission['operator_launcher'], OPERATOR_LAUNCHER)


def load_reviewed_sources():
    """Read only these seven public sources; verify bytes before compiling them.

    No sys.path addition or directory traversal. Private config/session/auth
    content is not read by this loader. Legacy runtime reads remain legacy code.
    """
    loaded = {}
    for name, expected_sha in SOURCE_PINS.items():
        path = (TREE2 / 'scripts' / (name + '.py')).resolve()
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != expected_sha:
            raise RuntimeError('Frozen Tree2 source changed: ' + name)
        previous = sys.modules.get(name)
        if previous is not None:
            if (Path(previous.__file__).resolve() != path
                    or getattr(previous, '_tree2_reviewed_sha256', None) != expected_sha):
                raise RuntimeError('Unreviewed module already loaded: ' + name)
            loaded[name] = previous
            continue
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        module._tree2_reviewed_sha256 = expected_sha
        sys.modules[name] = module
        try:
            exec(compile(content, str(path), 'exec'), module.__dict__)
        except BaseException:
            sys.modules.pop(name, None)
            raise
        loaded[name] = module
    return loaded


def require_authority(config_path, private_path, b):
    """Root creates this public packet only after independent admission review."""
    authority = b.read(AUTHORITY)
    require_python_runtime()
    if (authority.get('schema') != 'TREE2_CONTROLLER_FRESH_DEFENCE_ACTIVATION_V008'
            or authority.get('status') != 'ROOT_ADMITTED_ATTACH_SEPARATELY_ADMITTED_DEFENCE_WORKER_ONLY'
            or any(type(authority.get(key)) is not int or authority[key] != 0
                   for key in ('initial_AI_calls', 'initial_science_launches',
                               'process_repairs_remaining'))
            or type(authority.get('historical_process_repairs_consumed')) is not int
            or authority['historical_process_repairs_consumed'] < 1
            or authority.get('automatic_additional_repair') is not False):
        raise RuntimeError('Explicit exhausted-budget Root attach-only admission required')
    if authority.get('python_runtime') != PYTHON_RUNTIME:
        raise RuntimeError('Root runtime admission differs from the exact core Python pin')
    if authority.get('production_constraints') != PRODUCTION_CONSTRAINTS:
        raise RuntimeError('Preserved production debit/deadline/thread/unknown constraints differ')
    if Path(config_path).resolve() != CONFIG.resolve():
        raise RuntimeError('Only the fixed existing Tree2 public config is allowed')
    require_project_row(authority['config'], CONFIG, b)
    require_project_row(authority['handoff'], HANDOFF, b)
    require_runtime_sources(authority)
    # Metadata binding only; reading the private runtime config occurs solely
    # inside the unmodified inherited initializer after this public gate.
    private = authority['private_config']
    if private != EXISTING_PRIVATE_CONFIG:
        raise RuntimeError('Only the unchanged published opaque private config row is admitted')
    if Path(private['path']).is_absolute():
        expected_private = Path(private['path']).resolve()
    else:
        expected_private = b.inside(TREE2, private['path'])
    if Path(private_path).resolve() != expected_private:
        raise RuntimeError('Existing private config path binding differs')
    b.bind(TREE2, private)  # Opaque legacy binding is not relaxed or re-created.
    records = authority['historical_failure_records']
    if not isinstance(records, list) or tuple(row.get('path') for row in records) != REQUIRED_HISTORICAL_RECORDS:
        raise RuntimeError('Exact closed C008 and consumed V007 controller history is required')
    for item in records:
        b.bind(TREE2, item)
    require_row(authority['controller_reconciliation'],
        TREE2 / 'metadata/defence_C008_recovery_20261105/controller_v008/Root_controller_reconciliation.json')
    if authority.get('controller_exclusivity_reviewed') is not True:
        raise RuntimeError('Controller exclusivity reconciliation is required')
    handoff = b.validate_handoff(TREE2, b.read(HANDOFF),
                               b.read(CONFIG)['required_complete_outputs'])
    if handoff['status'] != 'WAITING_WORKER':
        raise RuntimeError('Initial action is attach to existing WAITING_WORKER only')
    if authority.get('expected_worker') != handoff['worker']:
        raise RuntimeError('Exact separately admitted C008R worker identity differs')
    if (authority.get('separately_admitted_fresh_controller_activation') is not True
            or authority.get('historical_controller_claims_preserved') is not True):
        raise RuntimeError('Fresh activation must preserve exhausted historical claims')
    plan_path = require_project_row(authority['scientific_plan'], RECOVERY_DIRECTORY / 'Root_plan.json', b)
    require_project_row(authority['scientific_admission'], RECOVERY_DIRECTORY / 'Root_scientific_admission.json', b)
    require_project_row(authority['scientific_source_review'], RECOVERY_DIRECTORY / 'Root_source_review.json', b)
    if (handoff.get('source_bound_plan') != authority['scientific_plan']
            or handoff.get('local_Root_scientific_admission') != authority['scientific_admission']
            or handoff.get('local_Root_source_review') != authority['scientific_source_review']):
        raise RuntimeError('Initial handoff and separately admitted C008R scientific bindings differ')
    plan = b.read(plan_path)
    if (plan.get('schema') != 'TREE2_DEFENCE_NOVEL_PRODUCTION_COHORT_PLAN_V003'
            or plan.get('stock_threads') != PRODUCTION_CONSTRAINTS['stock_threads']
            or plan.get('cpu_affinity') != PRODUCTION_CONSTRAINTS['cpu_affinity']):
        raise RuntimeError('Initial C008R recovery schema or reviewed CPU profile differs')
    return authority


def require_supervisor_parent(admission, kernel, b):
    """Reject direct/serial dispatcher launches; retain the exact live parent."""
    claim = b.read(SUPERVISOR_CLAIM)
    required = {'schema', 'authority', 'supervisor_owner', 'candidate_sources',
                'event_prompt', 'python_runtime', 'config', 'private_config',
                'expected_worker', 'supervisor_lock_held_by_frozen_run',
                'max_supervisor_launches', 'no_reissue', 'claimed_utc',
                'custodian_creation_claim', 'custodian_owner'}
    if (set(claim) != required
            or claim['schema'] != 'TREE2_V008_ONE_SHOT_DEFENCE_ACTIVATION_SUPERVISOR_CLAIM'
            or claim['authority'] != file_row(AUTHORITY)
            or claim['candidate_sources'] != admission['candidate_sources']
            or claim['event_prompt'] != admission['event_prompt']
            or claim['python_runtime'] != PYTHON_RUNTIME
            or claim['config'] != admission['config']
            or claim['private_config'] != EXISTING_PRIVATE_CONFIG
            or claim['expected_worker'] != admission['expected_worker']
            or claim['supervisor_lock_held_by_frozen_run'] is not True
            or type(claim['max_supervisor_launches']) is not int
            or claim['max_supervisor_launches'] != 1
            or claim['no_reissue'] is not True):
        raise RuntimeError('Immutable exact one-shot supervisor launch claim differs')
    require_row(claim['custodian_creation_claim'], CUSTODIAN_CLAIM)
    custodian = validate_custodian_claim(admission, b)
    if claim['custodian_owner'] != custodian['custodian_owner']:
        raise RuntimeError('Supervisor one-shot claim differs from its exact native custodian')
    parent = claim['supervisor_owner']
    if (not isinstance(parent, dict) or type(parent.get('pid')) is not int
            or os.getppid() != parent['pid']):
        raise RuntimeError('Dispatcher is not a child of its claimed exact supervisor')
    handle = kernel.open_worker(parent)
    custodian_handle = None
    try:
        if kernel.wait(handle, 0):
            raise RuntimeError('Claimed exact supervisor parent already exited; no direct attachment')
        custodian_handle = kernel.open_worker(claim['custodian_owner'])
        if kernel.wait(custodian_handle, 0):
            raise RuntimeError('Exact native custodian already exited; no dispatcher admission')
        return (handle, parent, file_row(SUPERVISOR_CLAIM),
                claim['custodian_creation_claim'], custodian_handle, claim['custodian_owner'])
    except BaseException:
        if custodian_handle is not None:
            kernel.close(custodian_handle)
        kernel.close(handle)
        raise


def validate_custodian_claim(admission, b):
    claim = b.read(CUSTODIAN_CLAIM)
    required = {'schema', 'authority_sha256', 'custodian_owner',
                'supervisor_source', 'runtime', 'mode'}
    if (not required.issubset(claim)
            or claim['schema'] != 'TREE2_V008_SUPERVISOR_CREATION_CLAIM_V1'
            or claim['authority_sha256'] != file_row(AUTHORITY)['sha256']
            or claim['supervisor_source'] != admission['candidate_sources']['tree2_supervisor_v008.py']
            or claim['runtime'] != PYTHON_RUNTIME
            or claim['mode'] != 'ONE_REVIEWED_SUPERVISOR_CREATION'):
        raise RuntimeError('Exact Root native supervisor-creation claim differs')
    return claim


def require_custodian_parent(admission, kernel, b):
    """Supervisor may be created only by the exact retained native custodian."""
    claim = validate_custodian_claim(admission, b)
    parent = claim['custodian_owner']
    if (not isinstance(parent, dict) or type(parent.get('pid')) is not int
            or os.getppid() != parent['pid']):
        raise RuntimeError('Supervisor is not a child of its claimed exact native custodian')
    handle = kernel.open_worker(parent)
    try:
        if kernel.wait(handle, 0):
            raise RuntimeError('Exact native custodian already exited; no supervisor admission')
        return handle, parent, file_row(CUSTODIAN_CLAIM)
    except BaseException:
        kernel.close(handle)
        raise


def make_dispatcher_class(v3, b):
    # The pinned V3 initializer hardcodes state/local_continuation_v3. Preserve
    # its exact base/session/identity setup locally and change only the namespace
    # guard; all inherited event/CLI/closure/transition methods remain pinned.
    v2 = v3.v2
    class ReviewedDispatcher(v3.Dispatcher):
        def __init__(self, config_path, private_path, kernel=None):
            if b.digest(Path(b.__file__)) != v2.BASE_SHA256:
                raise RuntimeError('Original dispatcher helpers changed')
            b.Dispatcher.__init__(self, config_path, private_path, kernel)
            if self.config['state_directory'] != 'state/local_continuation_v8' or self.config['handoff_path'] != 'state/local_continuation_v8/handoff.json':
                raise RuntimeError('V3 requires its new state namespace')
            seed = b.read(b.bind(self.root, self.config['existing_session']))
            existing = str(uuid.UUID(seed['session_id']))
            if self.session and self.session != existing:
                raise RuntimeError('Explicit retained CLI session mismatch')
            self.session = existing; self.early_event_sha = None; self.early_handoff_sha = None
            self.early_worker_exit = None; self.last_worker_actual_exit = None
            current = self.kernel.k.GetCurrentProcess; current.restype = ctypes.c_void_p
            self.owner = self.kernel.identity(current(), os.getpid())
            self.core_source = b.row(self.root, Path(__file__).resolve())
            self.config_binding = b.row(self.root, Path(config_path).resolve())
            self.last_operation = 'V3_INITIALIZE'

    class Dispatcher(ReviewedDispatcher):
        def __init__(self, config_path, private_path, kernel=None):
            self.admission = require_authority(config_path, private_path, b)
            self.admission_binding = file_row(AUTHORITY)
            kernel = kernel or b.Windows()
            (parent_handle, parent, claim_row, custodian_row,
             custodian_handle, custodian_owner) = require_supervisor_parent(self.admission, kernel, b)
            try:
                current = kernel.k.GetCurrentProcess
                current.restype = ctypes.c_void_p
                identity = kernel.identity(current(), os.getpid())
                b.exclusive(DISPATCHER_CLAIM, {
                    'schema': 'TREE2_V008_ONE_SHOT_DISPATCHER_START_CLAIM',
                    'authority': self.admission_binding, 'supervisor_launch_claim': claim_row,
                    'supervisor_owner': parent, 'dispatcher_owner': identity,
                    'initial_handoff': self.admission['handoff'],
                    'initial_handoff_payload': b.read(HANDOFF),
                    'python_runtime': PYTHON_RUNTIME, 'claimed_utc': b.utc(),
                    'max_dispatcher_starts': 1, 'no_reissue': True})
                self.dispatcher_claim_binding = file_row(DISPATCHER_CLAIM)
                super().__init__(config_path, private_path, kernel)
            except BaseException:
                kernel.close(parent_handle)
                kernel.close(custodian_handle)
                raise
            self.parent_handle, self.parent_identity = parent_handle, parent
            self.custodian_handle, self.custodian_identity = custodian_handle, custodian_owner
            self.supervisor_claim_binding = claim_row
            self.custodian_claim_binding = custodian_row
            self.core_source = file_row(HARNESS / 'scripts/defence_controller_v008/tree2_dispatcher_v008.py')
            self._initial_attachment = True
            self._status_degraded = None
            self._last_status_note = float('-inf')

        def status(self, status, **facts):
            if self.status_file.resolve() != (self.directory / 'dispatcher_status.json').resolve():
                raise RuntimeError('Optional dispatcher display path differs')
            if self._status_degraded is None:
                result = optional_status_replace(self.status_file,
                    {'status': status, 'updated_utc': b.utc(),
                     'dispatcher_pid': os.getpid(), 'AI_calls_during_wait': 0, **facts},
                    expected_path=self.directory / 'dispatcher_status.json')
                if result.published:
                    return result
                self._status_degraded = result
            now = time.monotonic()
            if now - self._last_status_note >= 30:
                self._last_status_note = now
                note = {'schema': 'TREE2_OPTIONAL_STATUS_DEGRADED_V008',
                    'at_utc': b.utc(), 'status': status,
                    'winerror': self._status_degraded.winerror,
                    'retry_attempts': self._status_degraded.attempts,
                    'status_publication_latched_off': True,
                    'worker_handle_retained': self.handle is not None,
                    'AI_calls_during_wait': 0, 'automatic_process_repair': False}
                try:
                    sys.stderr.write(json.dumps(note, sort_keys=True) + '\n')
                    sys.stderr.flush()
                except (OSError, ValueError):
                    # This explicit optional stderr observation cannot drop custody.
                    pass
            return self._status_degraded

        def attach(self, worker):
            initial = self._initial_attachment
            if initial and worker != self.admission['expected_worker']:
                raise RuntimeError('Initial worker changed after reviewed admission')
            super().attach(worker)
            if initial:
                if self.kernel.wait(self.handle, 0):
                    raise RuntimeError('Initial owner already exited; exact independent exit evidence required')
                acknowledgement = {'schema': 'TREE2_V008_EXACT_RETAINED_ATTACH_ACK',
                    'dispatcher_owner': self.owner, 'worker_identity': self.worker,
                    'retained_handle_identity_verified': True,
                    'handle_unsignaled_at_attachment': True,
                    'initial_AI_calls': 0, 'initial_science_launches': 0,
                    'core_source': self.core_source, 'config': self.config_binding,
                    'supervisor_owner': self.parent_identity,
                    'custodian_owner': self.custodian_identity,
                    'supervisor_launch_claim': self.supervisor_claim_binding,
                    'dispatcher_start_claim': self.dispatcher_claim_binding,
                    'supervisor_creation_claim': self.custodian_claim_binding,
                    'python_runtime': PYTHON_RUNTIME,
                    'authority': file_row(AUTHORITY), 'observed_utc': b.utc()}
                target = HARNESS / 'metadata/defence_C008_recovery_20261105/controller_v008/actual' / (
                    'dispatcher_' + str(self.owner['pid']) + '_' +
                    str(self.owner['windows_creation_filetime_100ns']) + '_attach.json')
                exclusive_json(target, acknowledgement)
                self._initial_attachment = False

        def dispatch_once(self, event_path):
            # A real native terminal event may continue only the actual reviewed
            # adapter+dependency source set, not V3's inherited __file__ alone.
            require_row(self.admission_binding, AUTHORITY)
            require_runtime_sources(self.admission)
            self.require_claim_bindings()
            if self.kernel.wait(self.parent_handle, 0):
                raise RuntimeError('Supervisor custody ended; no new CLI/science admission')
            self.require_custodian_live()
            return super().dispatch_once(event_path)

        def require_custodian_live(self):
            if self.kernel.wait(self.custodian_handle, 0):
                raise RuntimeError('Exact native custodian exited; custody UNKNOWN, no event/CLI/science admission')

        def require_claim_bindings(self):
            require_row(self.supervisor_claim_binding, SUPERVISOR_CLAIM)
            require_row(self.dispatcher_claim_binding, DISPATCHER_CLAIM)
            require_row(self.custodian_claim_binding, CUSTODIAN_CLAIM)

        def controller_context(self, event_path=None):
            require_row(self.admission_binding, AUTHORITY)
            require_runtime_sources(self.admission)
            self.require_claim_bindings()
            self.require_custodian_live()
            pointer_path = self.root / 'state/local_continuation_current_runtime.json'
            pointer_bytes = pointer_path.read_bytes()
            pointer = json.loads(pointer_bytes.decode('utf-8-sig'))
            exact_v5 = {'authority': self.admission_binding,
                'candidate_sources': self.admission['candidate_sources'],
                'event_prompt': self.admission['event_prompt'],
                'legacy_source_sha256': SOURCE_PINS,
                'python_runtime': PYTHON_RUNTIME,
                'operator_launcher': self.admission['operator_launcher'],
                'supervisor_creation_claim': self.custodian_claim_binding,
                'supervisor_launch_claim': self.supervisor_claim_binding,
                'dispatcher_start_claim': self.dispatcher_claim_binding}
            pointer_v5 = pointer.get('controller_repair_v008')
            if pointer_v5 is not None and pointer_v5 != exact_v5:
                raise RuntimeError('Current pointer claims a different V008 controller source/custody set')
            return {'schema': 'TREE2_V008_ACTUAL_EVENT_CONTEXT_V1',
                'source_roots': {'Tree2': str(self.root), 'fixed_harness': str(HARNESS)},
                **exact_v5,
                'controller_reconciliation': self.admission['controller_reconciliation'],
                'current_runtime_pointer': {'path': pointer_path.relative_to(self.root).as_posix(),
                    'sha256': hashlib.sha256(pointer_bytes).hexdigest(), 'bytes': len(pointer_bytes)},
                'runtime_pointer_state': ('V008_SOURCE_AND_CLAIMS_MATCH' if pointer_v5 is not None
                    else 'HISTORICAL_POINTER_AWAITING_ROOT_PUBLICATION'),
                'supervisor_owner': self.parent_identity, 'dispatcher_owner': self.owner,
                'custodian_owner': self.custodian_identity,
                'production_constraints': self.admission['production_constraints'],
                'initial_handoff': {'dated_mutable_path_observation': self.admission['handoff'],
                    'immutable_payload_in_dispatcher_start_claim': self.dispatcher_claim_binding},
                'current_handoff': b.row(self.root, self.handoff),
                'current_handoff_status': self.load_handoff()['status'],
                'event': b.row(self.root, event_path) if event_path is not None else None,
                'no_initial_AI_or_science_launch': True, 'no_controller_reissue': True}

        def event(self, kind, handoff_sha, **facts):
            # Keep the inherited event identity/key and strict writer; expose the
            # actual versioned source/authority context inside this real event.
            return super().event(kind, handoff_sha,
                v5_controller_context=self.controller_context(), **facts)

        def prompt(self, event_path, event_sha):
            if b.digest(event_path) != event_sha:
                raise RuntimeError('Exact native event changed before V008 prompt construction')
            context = self.controller_context(event_path)
            event = b.read(event_path)
            observed = event.get('v5_controller_context')
            variable = {'current_runtime_pointer', 'runtime_pointer_state', 'event'}
            if (not isinstance(observed, dict)
                    or set(observed) != set(context)
                    or observed.get('event') is not None
                    or any(observed[key] != value for key, value in context.items()
                           if key not in variable)):
                raise RuntimeError('Actual event V008 source/authority context differs')
            context['event_observed_v5_context'] = observed
            text = EVENT_PROMPT.read_text(encoding='utf-8')
            values = {'{{EVENT_PATH}}': str(event_path), '{{EVENT_SHA256}}': event_sha,
                '{{HANDOFF_PATH}}': str(self.handoff), '{{PROJECT_ROOT}}': str(self.root),
                '{{HARNESS_ROOT}}': str(HARNESS),
                '{{V5_CONTEXT_JSON}}': json.dumps(context, indent=2, sort_keys=True)}
            for marker, value in values.items():
                text = text.replace(marker, value)
            return text

        def run(self):
            # No recovery event, failure replay or initial-turn flags exist in V5.
            # V3 acquires both existing dispatcher locks and owns the same wait,
            # exact exit receipt/event, and downstream one-turn transition path.
            require_project_row(self.admission['handoff'], self.handoff, b)
            if self.kernel.wait(self.parent_handle, 0):
                raise RuntimeError('Exact supervisor parent must remain live at initial attachment')
            self.require_custodian_live()
            if self.load_handoff()['status'] != 'WAITING_WORKER':
                raise RuntimeError('Initial handoff must remain WAITING_WORKER')
            return super().run()

    return Dispatcher


def record_terminal(owner, error, b):
    """Same strict V3 terminal chain; no exception is converted into success."""
    cause = {'type': type(error).__name__, 'message': str(error),
             'filename': getattr(error, 'filename', None)}
    normalized = re.sub(r'\b[0-9a-fA-F]{32,64}\b', '<digest-or-token>', str(error))
    normalized = re.sub(r'\b\d{2,}\b', '<number>', normalized)
    rootcause = {'code': 'DISPATCHER_EXCEPTION', 'type': type(error).__name__,
        'last_operation': owner.last_operation,
        'operation_path': getattr(error, 'filename', None),
        'message_template': normalized}
    key = hashlib.sha256(json.dumps(rootcause, sort_keys=True).encode()).hexdigest()
    terminal = {'schema': 'TREE2_DISPATCHER_TERMINAL_ERROR_V3',
        'dispatcher_owner': owner.owner, 'core_source': owner.core_source,
        'config': owner.config_binding, 'error': cause, 'rootcause': rootcause,
        'rootcause_sha256': key, 'root_cause_sha256': key,
        'last_worker': owner.worker, 'last_worker_actual_exit': owner.last_worker_actual_exit,
        'no_science_retry': True, 'observed_utc': b.utc()}
    immutable = owner.directory / 'dispatcher_errors' / (
        str(owner.owner['pid']) + '_' +
        str(owner.owner['windows_creation_filetime_100ns']) + '.json')
    b.exclusive(immutable, terminal)
    b.atomic(owner.directory / 'dispatcher_terminal_error.json',
             {**terminal, 'immutable_terminal_error': b.row(owner.root, immutable)})
    owner.status('DISPATCHER_FAILURE_LOCAL_REPAIR_QUEUED', reason=repr(error),
                 root_cause_sha256=key)
    owner.log('DISPATCHER_STOPPED_NO_SCIENCE_RETRY', error=cause,
              root_cause_sha256=key)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--cli-config', required=True)
    args = parser.parse_args(argv)
    require_python_runtime()
    modules = load_reviewed_sources()
    b, v3 = (modules['local_tree2_dispatcher'],
             modules['local_tree2_dispatcher_v003'])
    owner = None
    try:
        owner = make_dispatcher_class(v3, b)(args.config, args.cli_config)
        owner.run()
    except BaseException as error:
        if owner and owner.owns_lock:
            record_terminal(owner, error, b)
        raise
    finally:
        if owner and owner.handle is not None:
            owner.kernel.close(owner.handle)
        if owner and owner.parent_handle is not None:
            owner.kernel.close(owner.parent_handle)
        if owner and owner.custodian_handle is not None:
            owner.kernel.close(owner.custodian_handle)


if __name__ == '__main__':
    main()
