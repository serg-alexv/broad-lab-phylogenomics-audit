"""Recover the current retained CLI once; tolerate sharing errors on public handoff reads only.

No CLI replay, credential inspection, science dispatch, or periodic AI polling.
"""
from pathlib import Path
import argparse
import ctypes
import os
import time
import local_tree2_dispatcher as b
import local_tree2_dispatcher_v002 as v2


def public_read(operation, handoff, seconds=5):
    deadline = time.monotonic() + seconds
    while True:
        try:
            return operation()
        except PermissionError as error:
            if not error.filename or Path(error.filename).resolve() != Path(handoff).resolve():
                raise
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.05)


class Dispatcher(v2.Dispatcher):
    def early_handoff(self, before, event, event_sha):
        try:
            return super().early_handoff(before, event, event_sha)
        except PermissionError as error:
            if not error.filename or Path(error.filename).resolve() != self.handoff.resolve():
                raise
            # Public presentation/attachment observation is optional until a valid handoff is readable.
            # All bound receipts, identities, required final admission and CLI outcomes remain strict.
            if time.monotonic() - getattr(self, '_last_public_share_note', -1000) >= 30:
                self._last_public_share_note = time.monotonic()
                self.log('PUBLIC_HANDOFF_SHARING_ERROR_OBSERVATION_DEFERRED', path=str(self.handoff), errno=error.errno)
            return None

    def accept_changed_handoff(self, before, event_sha):
        return public_read(lambda: super(Dispatcher, self).accept_changed_handoff(before, event_sha), self.handoff)

    def recover_current(self, grant_path, grant_sha):
        grant = b.read(b.bind(self.root, {'path': grant_path, 'sha256': grant_sha}))
        if grant['status'] != 'ROOT_ADMITTED_ONE_CURRENT_CLI_OS_RECOVERY_NO_AI_REPLAY':
            raise RuntimeError('Explicit current-CLI recovery admission required')
        event_path = b.bind(self.root, grant['current_event'])
        event = b.read(event_path); event_sha = b.digest(event_path)
        if grant['existing_session_id'] != self.session:
            raise RuntimeError('Retained session mismatch')
        for source in grant['bound_sources']:
            b.bind(self.root, source)
        with b.ByteLock(self.directory / 'dispatcher.lock'):
            self.owns_lock = True
            cli_handle = self.kernel.open_worker(grant['current_cli_identity'])
            process = self.kernel.k.GetCurrentProcess
            process.restype = ctypes.c_void_p
            identity = self.kernel.identity(process(), os.getpid())
            b.exclusive(self.directory / 'io_recovery_v001/launch.json', {
                'schema': 'TREE2_V2_PUBLIC_IO_RECOVERY_LAUNCH_V001', **identity, 'native_owner': identity,
                'script': str(Path(__file__).resolve()), 'source_sha256': b.digest(Path(__file__)),
                'grant_sha256': grant_sha, 'current_event_sha256': event_sha,
                'current_cli_identity': grant['current_cli_identity'], 'started_utc': b.utc()})
            before = grant['failed_P3_handoff_sha256']
            self.worker = event['worker_identity']
            self.status('AI_TURN_ACTIVE', event_sha256=event_sha, session_id=self.session,
                        recovery='Retaining the same current CLI; waiting for separately reviewed P4 owner; no AI replay')
            deadline = time.monotonic() + 7200
            try:
                while not self.kernel.wait(cli_handle, 0):
                    if time.monotonic() > deadline:
                        raise TimeoutError('Current retained CLI recovery deadline; no AI retry')
                    try:
                        candidate = b.read(self.handoff)
                        if candidate.get('worker', {}).get('role') == grant['required_next_worker_role']:
                            self.early_handoff(before, event, event_sha)
                            self.observe_early_exit(event_path.parent, event_sha)
                    except PermissionError as error:
                        if not error.filename or Path(error.filename).resolve() != self.handoff.resolve():
                            raise
                    self.kernel.wait(cli_handle, 250)
                actual_cli_exit = self.kernel.exit_code(cli_handle)
            finally:
                self.kernel.close(cli_handle)
            b.exclusive(event_path.parent / 'cli_actual_exit.json', {
                'identity': grant['current_cli_identity'], 'actual_exit_code': actual_cli_exit,
                'observed_utc': b.utc(), 'event_sha256': event_sha,
                'observer': 'Root-admitted recovery of the same original CLI retained handle; no CLI relaunch'})
            if actual_cli_exit != 0:
                self.drain_after_cli_error(event_path.parent, event_sha, RuntimeError('Recovered current CLI nonzero'))
                raise RuntimeError('Same original CLI exited nonzero; no retry')
            b.parse_cli_jsonl(event_path.parent / 'stdout.jsonl', self.session)
            after = self.accept_changed_handoff(before, event_sha)
            if after.get('worker', {}).get('role') != grant['required_next_worker_role'] or self.handle is None:
                raise RuntimeError('Required new owner not retained before current CLI completion')
            b.exclusive(event_path.parent / 'cli_result.json', {
                'status': 'CLI_TURN_ACCEPTED', 'event_sha256': event_sha, 'actual_exit_code': 0,
                'session_id': self.session, 'handoff_sha256': b.digest(self.handoff), 'accepted_utc': b.utc(),
                'same_current_CLI_recovered_without_replay': True, 'early_worker_actual_exit': self.early_worker_exit})
            self.log('CURRENT_CLI_RECOVERED_WITHOUT_REPLAY', event_sha256=event_sha)
            if not self.transition(after, event):
                return
            while True:
                self.status('WAITING_WORKER', worker=self.worker, session_id=self.session, AI_tokens_used_by_wait=0)
                if not self.kernel.wait(self.handle, 30000):
                    continue
                code = self.kernel.exit_code(self.handle)
                path = self.event('WINDOWS_WORKER_EXIT_OBSERVED', b.digest(self.handoff), actual_exit_code=code,
                                  launch_receipt=self.worker['launch_receipt'], retained_handle_identity_verified=True)
                self.log('WORKER_ACTUAL_EXIT', worker=self.worker, actual_exit_code=code, event_sha256=b.digest(path))
                self.early_event_sha = None; self.early_handoff_sha = None; self.early_worker_exit = None
                after = self.dispatch_once(path)
                if not self.transition(after, b.read(path)):
                    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--cli-config', required=True)
    parser.add_argument('--grant', required=True)
    parser.add_argument('--grant-sha256', required=True)
    args = parser.parse_args()
    controller = None
    try:
        controller = Dispatcher(args.config, args.cli_config)
        controller.recover_current(args.grant, args.grant_sha256)
    except BaseException as error:
        if controller and controller.owns_lock:
            controller.status('BLOCKED_UNKNOWN_NO_RETRY', reason=repr(error))
            controller.log('RECOVERY_CONTROLLER_STOPPED_NO_RETRY', reason=str(error), error_type=type(error).__name__)
        raise
    finally:
        if controller and controller.handle is not None:
            controller.kernel.close(controller.handle)
