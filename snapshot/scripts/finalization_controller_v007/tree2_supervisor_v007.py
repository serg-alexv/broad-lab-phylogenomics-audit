"""Versioned external supervisor wiring for the single reviewed status repair.

The byte-pinned V3 supervisor retains dispatcher handles and strict actual-exit
receipts. Its process-repair budget is exhausted at admission, independently of
root-cause hashes. Importing this module starts no process.
"""
import argparse
import os
from pathlib import Path
import uuid

if __package__:
    from . import tree2_dispatcher_v007 as wiring
else:
    import tree2_dispatcher_v007 as wiring


def make_supervisor_class(legacy, b):
    core_path = wiring.HARNESS / 'scripts/finalization_controller_v007/tree2_dispatcher_v007.py'

    def require_sources(core_source, config, private_config):
        # The sole external source exception is this exact reviewed candidate.
        wiring.require_row(core_source, core_path)
        if not hasattr(legacy, '_v007_admission'):
            raise RuntimeError('Source-bound V5 Root admission is unavailable')
        wiring.require_row(legacy._v007_admission_binding, wiring.AUTHORITY)
        wiring.require_runtime_sources(legacy._v007_admission)
        for item in (config, private_config):
            b.bind(wiring.TREE2, item)

    # This isolated, verified module's explicit versioned source-binding hook
    # replaces its hardcoded V3-only binding. Base/Tree2 source bytes stay intact.
    legacy.require_sources = require_sources

    class Supervisor(legacy.Supervisor):
        def __init__(self, args):
            self.args = args
            if getattr(args, 'allow_one_process_repair', False):
                raise RuntimeError('Historical process-repair budget is exhausted')
            self.admission = wiring.require_authority(args.config, args.cli_config, b)
            self.admission_binding = wiring.file_row(wiring.AUTHORITY)
            legacy._v007_admission = self.admission
            legacy._v007_admission_binding = wiring.file_row(wiring.AUTHORITY)
            self.kernel = b.Windows()
            self.custodian_handle, self.custodian_owner, self.custodian_claim = (
                wiring.require_custodian_parent(self.admission, self.kernel, b))
            try:
                self._initialize_admitted(args)
            except BaseException:
                if self.custodian_handle is not None:
                    self.kernel.close(self.custodian_handle)
                    self.custodian_handle = None
                raise

        def _initialize_admitted(self, args):
            self.config_path = b.inside(wiring.TREE2, args.config)
            self.private_path = b.inside(wiring.TREE2, args.cli_config)
            config = b.read(self.config_path)
            if Path(config['project_root']).resolve() != wiring.TREE2.resolve():
                raise RuntimeError('Supervisor project root differs')
            self.directory = b.inside(wiring.TREE2, config['state_directory'])
            if self.directory != wiring.STATE.resolve():
                raise RuntimeError('The unchanged V3 state namespace is required')
            self.core_path = core_path.resolve()
            if Path(args.core_source).resolve() != self.core_path:
                raise RuntimeError('Only the fixed reviewed V5 candidate may be supervised')
            self.core = wiring.file_row(self.core_path)
            if self.core['sha256'] != args.core_sha256:
                raise RuntimeError('Reviewed V5 candidate SHA differs')
            self.config = b.row(wiring.TREE2, self.config_path)
            self.private = b.row(wiring.TREE2, self.private_path)
            self.owner = self.kernel.identity(-1, os.getpid())
            self.token = uuid.uuid4().hex
            self.log_directory = wiring.HARNESS / 'work/finalization_controller_v007/supervisor_logs' / self.token
            self.log_directory.mkdir(parents=True, exist_ok=False)
            self.unresolved = self.directory / 'supervisor_unresolved_owner.json'
            self._run_entry = False
            self._child_launch_attempted = False
            if self.unresolved.exists():
                raise RuntimeError('Existing unresolved supervisor owner blocks relaunch')

        def run_child(self, failure_event=None):
            if (not self._run_entry or self._child_launch_attempted
                    or failure_event is not None):
                raise RuntimeError('One code-repair child creation only, through retained supervisor run')
            self._child_launch_attempted = True
            legacy.require_sources(self.core, self.config, self.private)
            if self.kernel.wait(self.custodian_handle, 0):
                raise RuntimeError('Native custodian ended; one-shot controller admission blocked')
            wiring.require_row(self.custodian_claim, wiring.CUSTODIAN_CLAIM)
            # Frozen run has acquired supervisor.lock before this callback.
            # Fixed path is never removed, even on create/receipt/child failure;
            # changing/reissuing authority cannot refill this V007 admission.
            b.exclusive(wiring.SUPERVISOR_CLAIM, {
                'schema': 'TREE2_V007_ONE_SHOT_FINALIZATION_ACTIVATION_SUPERVISOR_CLAIM',
                'authority': self.admission_binding,
                'supervisor_owner': self.owner,
                'custodian_creation_claim': self.custodian_claim,
                'custodian_owner': self.custodian_owner,
                'candidate_sources': self.admission['candidate_sources'],
                'event_prompt': self.admission['event_prompt'],
                'python_runtime': wiring.PYTHON_RUNTIME,
                'config': self.config, 'private_config': self.private,
                'expected_worker': self.admission['expected_worker'],
                'supervisor_lock_held_by_frozen_run': True,
                'max_supervisor_launches': 1, 'no_reissue': True,
                'claimed_utc': b.utc()})
            return super().run_child()

        def run(self):
            # Even a new temp filename/root-cause digest cannot refill this debit.
            self.args.allow_one_process_repair = False
            self._run_entry = True
            try:
                return super().run()
            finally:
                self._run_entry = False
                if self.custodian_handle is not None:
                    self.kernel.close(self.custodian_handle)
                    self.custodian_handle = None

    return Supervisor


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--cli-config', required=True)
    parser.add_argument('--core-source', required=True)
    parser.add_argument('--core-sha256', required=True)
    args = parser.parse_args(argv)
    wiring.require_python_runtime()
    args.allow_one_process_repair = False
    modules = wiring.load_reviewed_sources()
    return make_supervisor_class(
        modules['local_tree2_dispatcher_supervisor_v003'],
        modules['local_tree2_dispatcher'])(args).run()


if __name__ == '__main__':
    raise SystemExit(main())
