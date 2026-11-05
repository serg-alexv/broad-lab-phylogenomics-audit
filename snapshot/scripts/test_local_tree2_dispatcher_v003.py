"""V3 pure tests plus one owned non-genomic completed-turn shutdown fixture."""
from pathlib import Path
import json, os, sys, tempfile, time, unittest, uuid
from unittest.mock import patch
import local_tree2_dispatcher as b
import local_tree2_dispatcher_v003 as v

R = Path(__file__).resolve().parents[1]


class Cases(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=R / 'work', prefix='dispatcher_v3_fixture_')
        self.root = Path(self.temp.name).resolve(); self.assertTrue(self.root.is_relative_to(R / 'work'))
        self.session = str(uuid.uuid4()); self.owner = None

    def tearDown(self):
        if self.owner and self.owner.handle is not None:
            self.owner.kernel.close(self.owner.handle)
        self.assertTrue(self.root.is_relative_to(R / 'work')); self.temp.cleanup()

    def owner_config(self):
        seed = self.root / 'old_session.json'; b.atomic(seed, {'session_id': self.session})
        config = {'schema': 'TREE2_EVENT_DISPATCHER_CONFIG_V1', 'project_root': str(self.root),
                  'state_directory': 'state/local_continuation_v3', 'handoff_path': 'state/local_continuation_v3/handoff.json',
                  'existing_session': b.row(self.root, seed), 'cli_timeout_seconds': 45,
                  'required_complete_outputs': ['tree2_full', 'tree2_representative']}
        cp = self.root / 'config.json'; b.atomic(cp, config)
        fake = self.root / 'owned_fake_cli.py'
        fake.write_text("import json,time,sys\nfrom pathlib import Path\n" +
                        f"sys.path.insert(0,{str(R / 'scripts')!r})\n" +
                        "import local_tree2_dispatcher as b\n" +
                        "root=Path.cwd();info=b.read(root/'event_location.json');sha=b.digest(info['path'])\n" +
                        "b.atomic(root/'state/local_continuation_v3/handoff.json',{'schema':b.SCHEMA,'status':'BLOCKED','reason':'Owned non-genomic fixture complete','revision':'fresh','responding_to_event_sha256':sha})\n" +
                        f"print(json.dumps({{'type':'thread.started','thread_id':{self.session!r}}}),flush=True)\n" +
                        "print(json.dumps({'type':'turn.completed'}),flush=True)\ntime.sleep(60)\n",
                        encoding='utf-8', newline='\n')
        environment = {name: str(self.root / name) for name in ('CODEX_HOME', 'CODEX_SQLITE_HOME', 'TEMP', 'TMP', 'XDG_CACHE_HOME')}
        environment['PYTHONDONTWRITEBYTECODE'] = '1'
        private = {'project_root': str(self.root), 'stdin_mode': 'utf8_prompt_file', 'executable': sys.executable,
                   'executable_sha256': b.digest(sys.executable), 'initial_argv': ['-B', str(fake)],
                   'resume_argv': ['-B', str(fake)], 'environment': environment, 'remove_environment_names': []}
        pp = self.root / 'private_fake.json'; b.atomic(pp, private)
        # Bind an identical source copy inside the synthetic project namespace.
        copied_source = self.root / 'fixture_core_source.py'
        copied_source.write_bytes(Path(v.__file__).read_bytes())
        with patch.object(v, '__file__', str(copied_source)):
            self.owner = v.Dispatcher(cp, pp)
        # The fixture executable is Python, which other test/science processes also use.
        # Production's exact Codex-executable guard is tested separately, never weakened in config.
        self.owner.assert_cli_absent = lambda: None
        return self.owner

    def test_real_completed_turn_waits30s_and_preserves_nonzero_native_exit(self):
        owner = self.owner_config(); path = owner.event('ROOT_REVIEWED_RECOVERY_EVENT', None, no_live_worker_claimed=True)
        b.atomic(self.root / 'event_location.json', {'path': str(path)})
        started = time.monotonic(); after = owner.dispatch_once(path); elapsed = time.monotonic() - started
        self.assertGreaterEqual(elapsed, 30); self.assertLess(elapsed, 44)
        result = b.read(path.parent / 'cli_result.json')
        self.assertEqual(result['actual_exit_code'], 130); self.assertTrue(result['semantic_turn_completed'])
        proof = b.read(b.bind(self.root, result['shutdown_recovery']))
        self.assertEqual(proof['actual_exit_code'], 130); self.assertFalse(proof['native_exit_zero_claimed'])
        self.assertEqual(after['status'], 'BLOCKED'); self.assertEqual(len(list(path.parent.glob('cli_attempt.json'))), 1)

    def test_nonzero_worker_failure_is_locally_queued_immediately(self):
        owner = self.owner_config(); owner.worker = {'pid': 123, 'windows_creation_filetime_100ns': 456}
        path = owner.failure_signal(2, {'synthetic_owned_exit': True})
        self.assertEqual(b.read(path)['status'], 'FAILURE_REPAIR_QUEUED')
        status = b.read(owner.status_file)
        self.assertEqual(status['status'], 'WORKER_FAILED_REPAIR_QUEUED'); self.assertEqual(status['actual_exit_code'], 2)
        self.assertFalse(b.read(path)['science_retry_authorized'])

    def test_incomplete_or_failed_model_turn_cannot_be_accepted(self):
        p = self.root / 'stdout.jsonl'; p.write_text(json.dumps({'type': 'thread.started', 'thread_id': self.session}) + '\n')
        self.assertFalse(v.terminal_turn(p, self.session))
        p.write_text(json.dumps({'type': 'turn.failed'}) + '\n' + json.dumps({'type': 'turn.completed'}) + '\n')
        with self.assertRaises(RuntimeError):
            v.terminal_turn(p, self.session)

    def test_unknown_cli_descendant_blocks_before_termination(self):
        owner = self.owner_config(); folder = self.root / 'synthetic'; folder.mkdir()
        stdout = folder / 'stdout.jsonl'; stdout.write_text(json.dumps({'type': 'thread.started', 'thread_id': self.session}) + '\n' + json.dumps({'type': 'turn.completed'}) + '\n')
        identity = {'pid': 123, 'windows_creation_filetime_100ns': 456, 'creation_time_utc': 'synthetic'}
        class Child:
            pid = 123; _handle = 123
        owner.kernel.identity = lambda *args: identity
        owner.accept_changed_handoff = lambda *args: {'status': 'BLOCKED'}
        with patch.object(v, 'descendants', return_value=[{'name': 'unknown.exe', 'pid': 999}]):
            with self.assertRaises(RuntimeError):
                owner.shutdown_completed_cli(Child(), identity, folder, 'a' * 64, None)
        self.assertFalse((folder / 'shutdown_recovery_requested.json').exists())

    def test_exact_cli_guard_blocks_existing_same_executable(self):
        owner = self.owner_config()
        # sys.executable is this currently alive owned Python test process.
        del owner.assert_cli_absent
        with self.assertRaisesRegex(RuntimeError, 'headless CLI'):
            owner.assert_cli_absent()


if __name__ == '__main__':
    unittest.main()
