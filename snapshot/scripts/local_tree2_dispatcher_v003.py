"""Local continuation V3: immediate failure signals and bounded semantic-turn teardown.

Only the dispatcher launches the one headless CLI. Scientific work remains the
agent's separately validated/admitted responsibility, never a process retry here.
"""
from pathlib import Path
import argparse, ctypes, hashlib, json, os, re, subprocess, time, uuid
from ctypes import wintypes
import local_tree2_dispatcher as b
import local_tree2_dispatcher_v002 as v2
import local_tree2_dispatcher_io_recovery_v001 as io


class ENTRY(ctypes.Structure):
    _fields_ = [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD),
                ('pid', wintypes.DWORD), ('heap', ctypes.c_size_t),
                ('module', wintypes.DWORD), ('threads', wintypes.DWORD),
                ('parent', wintypes.DWORD), ('priority', wintypes.LONG),
                ('flags', wintypes.DWORD), ('name', wintypes.WCHAR * 260)]


def process_rows(kernel):
    """Native metadata census; no command lines, credentials or private files."""
    k = kernel.k
    k.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    k.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    k.Process32FirstW.argtypes = [ctypes.c_void_p, ctypes.POINTER(ENTRY)]
    k.Process32NextW.argtypes = [ctypes.c_void_p, ctypes.POINTER(ENTRY)]
    handle = k.CreateToolhelp32Snapshot(2, 0)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    rows = []
    try:
        entry = ENTRY(); entry.dwSize = ctypes.sizeof(entry)
        ok = k.Process32FirstW(handle, ctypes.byref(entry))
        while ok:
            rows.append({'pid': int(entry.pid), 'parent_pid': int(entry.parent), 'name': entry.name})
            ok = k.Process32NextW(handle, ctypes.byref(entry))
        if ctypes.get_last_error() not in (0, 18):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.close(handle)
    return rows


def descendants(kernel, identity):
    rows = process_rows(kernel); parents = {identity['pid']}; result = []
    while True:
        added = [r for r in rows if r['parent_pid'] in parents and r['pid'] not in parents]
        if not added:
            return result
        for value in added:
            handle = kernel.k.OpenProcess(0x00100000 | 0x1000, False, value['pid'])
            if not handle:
                raise ctypes.WinError(ctypes.get_last_error())
            try:
                born = kernel.identity(handle, value['pid'])
            finally:
                kernel.close(handle)
            if born['windows_creation_filetime_100ns'] < identity['windows_creation_filetime_100ns']:
                # A pre-existing process cannot descend from this later PID incarnation.
                continue
            result.append({**value, **born}); parents.add(value['pid'])
        rows = [r for r in rows if r not in added]


def terminal_turn(path, session):
    if not Path(path).exists():
        return False
    with Path(path).open('rb') as stream:
        stream.seek(max(0, Path(path).stat().st_size - 8192))
        tail = stream.read()
    if b'"turn.completed"' not in tail:
        return False
    # Complete structured turn, same UUID and no error/failed event are mandatory.
    b.parse_cli_jsonl(path, session)
    return True


class Dispatcher(io.Dispatcher):
    def __init__(self, config_path, private_path, kernel=None):
        if b.digest(Path(b.__file__)) != v2.BASE_SHA256:
            raise RuntimeError('Original dispatcher helpers changed')
        b.Dispatcher.__init__(self, config_path, private_path, kernel)
        if self.config['state_directory'] != 'state/local_continuation_v3' or self.config['handoff_path'] != 'state/local_continuation_v3/handoff.json':
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

    def assert_cli_absent(self):
        expected = str(Path(self.private['executable']).resolve()).casefold()
        k = self.kernel.k
        k.QueryFullProcessImageNameW.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        for value in process_rows(self.kernel):
            if value['name'].casefold() != Path(self.private['executable']).name.casefold():
                continue
            handle = k.OpenProcess(0x1000, False, value['pid'])
            if not handle:
                raise RuntimeError('Cannot establish that a possible headless CLI has closed')
            try:
                size = wintypes.DWORD(32768); text = ctypes.create_unicode_buffer(size.value)
                if not k.QueryFullProcessImageNameW(handle, 0, text, ctypes.byref(size)):
                    raise ctypes.WinError(ctypes.get_last_error())
                if str(Path(text.value).resolve()).casefold() == expected:
                    raise RuntimeError('Another headless CLI is still live; no second AI process')
            finally:
                self.kernel.close(handle)

    def failure_signal(self, actual_exit, context):
        key = hashlib.sha256(json.dumps({'exit': actual_exit, 'context': context}, sort_keys=True).encode()).hexdigest()
        path = self.directory / 'failure_signals' / (key + '.json')
        if not path.exists():
            b.exclusive(path, {'schema': 'TREE2_LOCAL_FAILURE_SIGNAL_V3', 'status': 'FAILURE_REPAIR_QUEUED',
                               'observed_utc': b.utc(), 'actual_exit_code': actual_exit, 'context': context,
                               'science_retry_authorized': False, 'AI_calls_during_OS_wait': 0})
        b.atomic(self.directory / 'failure_pending.json', b.row(self.root, path))
        self.status('WORKER_FAILED_REPAIR_QUEUED', failure_event=b.row(self.root, path),
                    worker=self.worker, actual_exit_code=actual_exit, CLI_teardown_pending=True)
        return path

    def observe_early_exit(self, folder, event_sha):
        result = super().observe_early_exit(folder, event_sha)
        if result:
            self.last_worker_actual_exit = result
            proof = b.read(b.bind(self.root, result))
            if proof['actual_exit_code'] != 0 and getattr(self, '_signaled_early', None) != result['sha256']:
                self._signaled_early = result['sha256']
                self.failure_signal(proof['actual_exit_code'], {'worker_actual_exit': result, 'during_event_sha256': event_sha})
        return result

    def shutdown_completed_cli(self, child, identity, folder, event_sha, before):
        self.last_operation = 'COMPLETED_CLI_NATIVE_TEARDOWN'
        # The native Popen handle is retained; numeric PID lookup alone never authorizes a signal.
        if self.kernel.identity(int(child._handle), child.pid) != identity:
            raise RuntimeError('CLI exact creation identity changed before teardown')
        after = self.accept_changed_handoff(before, event_sha)
        if not terminal_turn(folder / 'stdout.jsonl', self.session):
            raise RuntimeError('Incomplete model turn cannot use shutdown recovery')
        children = descendants(self.kernel, identity)
        if any(value['name'].lower() != 'conhost.exe' for value in children):
            raise RuntimeError('CLI shutdown blocked by an unrelated/unknown live descendant')
        proof = {'schema': 'TREE2_BOUND_COMPLETED_CLI_SHUTDOWN_V3', 'identity': identity,
                 'semantic_turn_completed': True, 'session_id': self.session,
                 'event_sha256': event_sha, 'handoff_sha256': b.digest(self.handoff),
                 'validated_handoff_status': after['status'], 'descendants': children,
                 'only_console_descendants': True, 'grace_seconds': 30,
                 'actual_exit_code': None, 'native_exit_zero_claimed': False}
        b.exclusive(folder / 'shutdown_recovery_requested.json', proof)
        k = self.kernel.k; k.TerminateProcess.argtypes = [ctypes.c_void_p, wintypes.UINT]
        if not k.TerminateProcess(int(child._handle), 130):
            if not self.kernel.wait(int(child._handle), 0):
                raise ctypes.WinError(ctypes.get_last_error())
        if not self.kernel.wait(int(child._handle), 10000):
            raise RuntimeError('CLI exact teardown exit remains UNKNOWN')
        child.poll(); proof['actual_exit_code'] = child.returncode; proof['observed_utc'] = b.utc()
        b.exclusive(folder / 'shutdown_recovery_actual_exit.json', proof)
        return b.row(self.root, folder / 'shutdown_recovery_actual_exit.json')

    def _dispatch_once(self, event_path, event, event_sha, folder):
        self.last_operation = 'MEANINGFUL_EVENT_CLI_DISPATCH'
        result_path = folder / 'cli_result.json'
        before = b.digest(self.handoff) if self.handoff.exists() else None
        if result_path.exists():
            result = b.read(result_path)
            if result.get('status') != 'CLI_TURN_ACCEPTED' or result.get('event_sha256') != event_sha or result.get('session_id') != self.session or b.digest(self.handoff) != result.get('handoff_sha256'):
                raise RuntimeError('Prior result/handoff cannot be recovered')
            return self.load_handoff()
        self.assert_cli_absent()
        b.exclusive(folder / 'cli_attempt.json', {'claimed_utc': b.utc(), 'event_sha256': event_sha, 'session_id': self.session, 'no_unknown_attempt_retry': True})
        if b.digest(Path(self.private['executable'])) != self.private['executable_sha256']:
            raise RuntimeError('Pinned CLI executable changed')
        prompt = folder / 'prompt.txt'; prompt.write_text(self.prompt(event_path, event_sha), encoding='utf-8', newline='\n')
        env = os.environ.copy()
        for name in self.private['remove_environment_names']:
            env.pop(name, None)
        env.update(self.private['environment'])
        for key in ('CODEX_HOME', 'CODEX_SQLITE_HOME', 'TEMP', 'TMP', 'XDG_CACHE_HOME'):
            if not Path(env[key]).resolve().is_relative_to(self.root):
                raise RuntimeError('CLI writable path leaves project')
        self.status('AI_TURN_ACTIVE', event_sha256=event_sha, session_id=self.session)
        self.log('CLI_STARTING', event_sha256=event_sha, session_id=self.session)
        complete_at = None; shutdown = None
        with prompt.open('rb') as stdin, (folder / 'stdout.jsonl').open('wb') as stdout, (folder / 'stderr.txt').open('wb') as stderr:
            child = subprocess.Popen(b.cli_argv(self.private, self.session, folder / 'last-message.txt'), stdin=stdin, stdout=stdout, stderr=stderr, cwd=self.root, env=env, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            identity = self.kernel.identity(int(child._handle), child.pid)
            b.atomic(folder / 'cli_started.json', {'identity': identity, 'event_sha256': event_sha, 'started_utc': b.utc()})
            deadline = time.monotonic() + self.config['cli_timeout_seconds']
            while child.poll() is None:
                self.early_handoff(before, event, event_sha); self.observe_early_exit(folder, event_sha)
                if complete_at is None and terminal_turn(folder / 'stdout.jsonl', self.session):
                    self.accept_changed_handoff(before, event_sha); complete_at = time.monotonic()
                    b.exclusive(folder / 'semantic_turn_completed.json', {'observed_utc': b.utc(), 'event_sha256': event_sha, 'native_exit_pending': True})
                if complete_at is not None and time.monotonic() - complete_at >= 30:
                    shutdown = self.shutdown_completed_cli(child, identity, folder, event_sha, before); break
                if time.monotonic() >= deadline:
                    raise TimeoutError('CLI model-turn deadline; no duplicate or science termination')
                self.kernel.wait(int(child._handle), 250)
            child.poll(); code = child.returncode
            b.atomic(folder / 'cli_actual_exit.json', {'identity': identity, 'actual_exit_code': code, 'observed_utc': b.utc(), 'event_sha256': event_sha, 'shutdown_recovery': shutdown})
        self.early_handoff(before, event, event_sha); self.observe_early_exit(folder, event_sha)
        if type(code) is not int or (code != 0 and shutdown is None):
            raise RuntimeError('CLI actual failure without verified completed-turn shutdown recovery')
        b.parse_cli_jsonl(folder / 'stdout.jsonl', self.session); after = self.accept_changed_handoff(before, event_sha)
        if after['status'] != 'WAITING_WORKER' and self.early_event_sha == event_sha:
            # A terminal handoff must never discard a previously retained live owner.
            self.drain_after_cli_error(folder, event_sha, RuntimeError('Terminal handoff after early worker attachment'))
        session_file = self.directory / 'cli_session.json'
        if not session_file.exists():
            b.exclusive(session_file, {'session_id': self.session, 'existing_session_seed': self.config['existing_session']})
        b.exclusive(result_path, {'status': 'CLI_TURN_ACCEPTED', 'event_sha256': event_sha,
                                 'actual_exit_code': code, 'semantic_turn_completed': True,
                                 'shutdown_recovery': shutdown, 'session_id': self.session,
                                 'handoff_sha256': b.digest(self.handoff), 'accepted_utc': b.utc()})
        self.log('CLI_TURN_ACCEPTED', event_sha256=event_sha, actual_exit_code=code, shutdown_recovery=shutdown)
        return after

    def worker_exit(self):
        self.last_operation = 'RETAINED_WORKER_EXIT_CAPTURE'
        code = self.kernel.exit_code(self.handle)
        path = self.directory / 'worker_exits' / (str(self.worker['pid']) + '_' + str(self.worker['windows_creation_filetime_100ns']) + '.json')
        if not path.exists():
            b.exclusive(path, {'schema': 'TREE2_RETAINED_WORKER_ACTUAL_EXIT_V2', 'worker_identity': self.worker,
                               'actual_exit_code': code, 'exact_birth_handle_retained': True, 'observed_utc': b.utc()})
        self.last_worker_actual_exit = b.row(self.root, path)
        if code != 0:
            self.failure_signal(code, {'worker_actual_exit': self.last_worker_actual_exit})
        return code

    def run(self, recovery_path=None, recovery_sha=None, failure_path=None, failure_sha=None):
        with b.ByteLock(self.root / 'state/local_continuation_dispatcher.lock'), b.ByteLock(self.directory / 'dispatcher.lock'):
            self.owns_lock = True
            if failure_path:
                proof = b.read(b.bind(self.root, {'path': failure_path, 'sha256': failure_sha}))
                if proof.get('schema') != 'TREE2_LOCAL_DISPATCHER_PROCESS_FAILURE_EVENT_V003' or type(proof.get('actual_exit_code')) is not int or proof.get('retained_handle_reaped') is not True:
                    raise RuntimeError('Actual supervisor dispatcher-exit proof required')
                error = b.read(b.bind(self.root, proof['terminal_error']))
                self.assert_cli_absent()
                b.exclusive(self.directory / 'repair_claims' / (error['root_cause_sha256'] + '.json'), {'failure_event': b.row(self.root, Path(failure_path).resolve()), 'one_process_repair_only': True, 'no_science_retry': True})
                # Reattach a live exact owner; otherwise demand a genuinely retained exit receipt.
                after = self.load_handoff(); worker = after.get('worker')
                if worker:
                    try:
                        self.attach(worker)
                    except OSError:
                        last = error.get('last_worker_actual_exit')
                        if not last:
                            raise RuntimeError('Worker disappeared without actual exit; UNKNOWN, no process/science replay')
                        closed = b.read(b.bind(self.root, last))
                        if closed.get('exact_birth_handle_retained') is not True or type(closed.get('actual_exit_code')) is not int or b.worker_key(closed['worker_identity']) != b.worker_key(worker):
                            raise RuntimeError('Prior worker closure proof mismatch')
                        self.worker = worker
                        path = self.event('DISPATCHER_FAILURE_CLOSED_WORKER_RECOVERY', b.digest(self.handoff), actual_worker_exit=last, dispatcher_failure=b.row(self.root, Path(failure_path).resolve()))
                        if not self.transition(self.dispatch_once(path), b.read(path)):
                            return
                else:
                    raise RuntimeError('Missing recovery worker/context; explicit Root seed required')
            elif recovery_path:
                seed = v2.recovery_seed(self.root, recovery_path, recovery_sha, self.session)
                if self.checkpoint.exists():
                    raise RuntimeError('Recovery event already claimed')
                path = self.event('ROOT_REVIEWED_RECOVERY_EVENT', None, recovery_seed=b.row(self.root, Path(recovery_path).resolve()), reason=seed['reason'], no_live_worker_claimed=True)
                if not self.transition(self.dispatch_once(path), b.read(path)):
                    return
            else:
                after = self.load_handoff()
                if after['status'] != 'WAITING_WORKER':
                    self.status(after['status'], reason=after.get('reason')); return
                self.attach(after['worker'])
            while True:
                self.last_operation = 'PASSIVE_RETAINED_WORKER_WAIT'
                self.status('WAITING_WORKER', worker=self.worker, session_id=self.session, AI_tokens_used_by_wait=0)
                if not self.kernel.wait(self.handle, 30000):
                    continue
                code = self.worker_exit()
                path = self.event('WINDOWS_WORKER_EXIT_OBSERVED', b.digest(self.handoff), actual_exit_code=code, launch_receipt=self.worker['launch_receipt'], retained_handle_identity_verified=True, actual_exit_receipt=self.last_worker_actual_exit)
                self.log('WORKER_ACTUAL_EXIT', worker=self.worker, actual_exit_code=code, event_sha256=b.digest(path))
                self.early_event_sha = None; self.early_handoff_sha = None; self.early_worker_exit = None
                if not self.transition(self.dispatch_once(path), b.read(path)):
                    return


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--config', required=True); parser.add_argument('--cli-config', required=True)
    parser.add_argument('--recovery-event'); parser.add_argument('--recovery-event-sha256')
    parser.add_argument('--dispatcher-failure-event'); parser.add_argument('--dispatcher-failure-event-sha256')
    args = parser.parse_args(); owner = None
    try:
        owner = Dispatcher(args.config, args.cli_config)
        owner.run(args.recovery_event, args.recovery_event_sha256, args.dispatcher_failure_event, args.dispatcher_failure_event_sha256)
    except BaseException as error:
        if owner and owner.owns_lock:
            cause = {'type': type(error).__name__, 'message': str(error), 'filename': getattr(error, 'filename', None)}
            normalized = re.sub(r'\b[0-9a-fA-F]{32,64}\b', '<digest-or-token>', str(error))
            normalized = re.sub(r'\b\d{2,}\b', '<number>', normalized)
            rootcause = {'code': 'DISPATCHER_EXCEPTION', 'type': type(error).__name__, 'last_operation': owner.last_operation, 'operation_path': getattr(error, 'filename', None), 'message_template': normalized}
            key = hashlib.sha256(json.dumps(rootcause, sort_keys=True).encode()).hexdigest()
            terminal = {'schema': 'TREE2_DISPATCHER_TERMINAL_ERROR_V3', 'dispatcher_owner': owner.owner,
                        'core_source': owner.core_source, 'config': owner.config_binding,
                        'error': cause, 'rootcause': rootcause, 'rootcause_sha256': key, 'root_cause_sha256': key,
                        'last_worker': owner.worker, 'last_worker_actual_exit': owner.last_worker_actual_exit,
                        'no_science_retry': True, 'observed_utc': b.utc()}
            immutable = owner.directory / 'dispatcher_errors' / (str(owner.owner['pid']) + '_' + str(owner.owner['windows_creation_filetime_100ns']) + '.json')
            b.exclusive(immutable, terminal)
            b.atomic(owner.directory / 'dispatcher_terminal_error.json', {**terminal, 'immutable_terminal_error': b.row(owner.root, immutable)})
            owner.status('DISPATCHER_FAILURE_LOCAL_REPAIR_QUEUED', reason=repr(error), root_cause_sha256=key)
            owner.log('DISPATCHER_STOPPED_NO_SCIENCE_RETRY', error=cause, root_cause_sha256=key)
        raise
    finally:
        if owner and owner.handle is not None:
            owner.kernel.close(owner.handle)


if __name__ == '__main__':
    main()
