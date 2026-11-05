"""One guarded full-cohort IQ-TREE production unit; no pilot/model-test queue."""
from pathlib import Path
import json, os, shutil, subprocess, time
import marker_pilot_compute_v001 as g
import stage08_owned_cleanup_v003 as own
from checkm1_owned_rss_sample_v001 import sample_owned_rss


class Runtime:
    def __init__(self, plan):
        self.p = plan; self.e = g.R / plan['work']; self.stop = g.R / plan['stop_path']
        self.owner = own.identity(os.getpid()); self.started = time.monotonic()
        self.science = 0.; self.peak = 0; self.last = 0; self.done = 0
        self.last_guard_sample = None; self.active_known = {}; self.unit_active = False
        self.native = g.read(self.e / 'native_owner.json')['native_owner']
        self.prefix = g.R / plan['prefix']
        g.save(self.e / 'linux_owner.json', self.owner)
        os.sched_setaffinity(0, {plan['cpu']})

    def guard(self, known=(), elapsed=0):
        if self.stop.exists() or (g.R / 'state/STOP').exists():
            raise InterruptedError('Scoped production/global STOP')
        if (time.time() > self.p['production_absolute_deadline_unix'] or
            time.monotonic() - self.started > self.p['cold_seconds'] or
            self.p['previous_production_scientific_seconds'] + elapsed > self.p['production_total_budget_seconds']):
            raise TimeoutError('Full production budget/deadline reached; checkpoint retained')
        if shutil.disk_usage(g.R).free < self.p['minimum_backing_disk_bytes']:
            raise RuntimeError('Backing disk below admitted reserve')
        if Path('/proc/sys/kernel/random/boot_id').read_text().strip() != self.owner['boot_id']:
            raise RuntimeError('Boot identity changed')
        rss = sample_owned_rss([self.owner, *known])
        ram = sum(shutil.disk_usage(p).used for p in (Path('/tmp'), Path('/dev/shm')))
        available = g.available(); self.peak = max(self.peak, rss + ram)
        self.last_guard_sample = {'summed_owned_Linux_RSS_bytes': rss, 'private_RAM_used_bytes': ram,
            'summed_RSS_plus_RAM_bytes': rss + ram, 'Linux_available_bytes': available, 'at_utc': g.utc()}
        reason = None
        if available < self.p['minimum_linux_available_bytes']: reason = 'Linux available below production headroom'
        if rss + ram > self.p['linux_RSS_plus_RAM_bytes']: reason = 'Owned Linux RSS plus private RAM exceeds production allocation'
        if reason:
            # Persist the actual offending sample before any cleanup can reduce RSS.
            g.save(self.e / 'offending_resource_sample.json', {'reason': reason, **self.last_guard_sample})
            raise MemoryError(reason)
        return rss, ram, available

    def observations(self):
        log = Path(str(self.prefix) + '.log'); text = ''
        try:
            with log.open('rb') as f:
                f.seek(max(0, log.stat().st_size - 8192)); text = f.read().decode('utf-8', errors='replace')
        except OSError: pass
        lines = [s.strip() for s in text.splitlines() if s.strip()]
        checkpoint = Path(str(self.prefix) + '.ckp.gz'); observed = {'exists': False}
        try:
            st = checkpoint.stat(); observed = {'exists': True, 'bytes': st.st_size,
                'mtime_unix': st.st_mtime, 'age_seconds': max(0, time.time() - st.st_mtime),
                'state': 'OBSERVATION_ONLY_ACTIVE_CHECKPOINT_NOT_HASH_ACCEPTED'}
        except OSError: pass
        return {'actual_IQTREE_log_tail': lines[-4:], 'checkpoint_observation': observed,
                'elapsed_scientific_seconds': self.science + (time.monotonic() - self.unit_started if self.unit_active else 0),
                'estimated_completion_time': None}

    def publish(self, detail, force=False, status='RUNNING', **extra):
        if not force and time.monotonic() - self.last < 30: return
        rss, ram, available = self.guard(self.active_known.values(),
            max(0, time.monotonic() - getattr(self, 'unit_started', time.monotonic())))
        row = {'id': '08', 'name': 'Full-panel phylogeny', 'status': status,
            'operation': 'PRODUCTION_ML_SEARCH_THEN1000_UFBOOT_1000_SHALRT', 'production_inference': True, 'detail': detail,
            'done': self.done, 'total': 1, 'unit': 'full900 supported production inference',
            'pid': self.native['pid'], 'creation_time_utc': self.native['creation_time_utc'],
            'model': self.p['model'], 'likelihood_partitioning': 'UNPARTITIONED_RESOURCE_STRATEGY',
            'input_matrix': 'unchanged accepted900x54x13071', 'owned_Linux_RSS_bytes': rss,
            'private_RAM_used_bytes': ram, 'Linux_available_bytes': available,
            'stock_memory_target': '700M', 'support_replicates_requested': {'UFBoot': 1000, 'SHaLRT': 1000},
            'all_source_taxonomy_type_QC_paralogy_and_composition_holds_preserved': True,
            'full_panel_tree_acceptance': False, 'updated_utc': g.utc(), **self.observations(), **extra}
        for target in (self.e / 'progress.json', g.R / 'state/stages/08.json'):
            try: g.save(target, row)
            except OSError as error:
                try:
                    with (self.e / 'optional_display_errors.jsonl').open('a') as f:
                        f.write(json.dumps({'error': repr(error), 'path': str(target), 'at_utc': g.utc()}) + '\n')
                except OSError: pass
        self.last = time.monotonic()

    def run(self, folder, args, inputs):
        folder.mkdir(parents=True, exist_ok=False); tmp = folder / 'tmp'; tmp.mkdir()
        g.save(folder / 'command.json', {'argv': args, 'inputs': inputs,
            'unit': 'FULL900_SUPPORTED_PRODUCTION', 'started_utc': g.utc()})
        p = None; identity = None; known = {}; self.active_known = known; error = None
        self.unit_started = time.monotonic(); self.unit_active = True; peak = 0; minimum = None
        env = {**os.environ, 'TMPDIR': str(tmp), 'XDG_CACHE_HOME': str(tmp / 'cache'),
            'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
        try:
            self.guard()
            with (folder / 'stdout.txt').open('xb') as out, (folder / 'stderr.txt').open('xb') as err:
                p = subprocess.Popen(args, cwd=folder, env=env, stdout=out, stderr=err, start_new_session=True)
                identity = own.identity(p.pid); known[p.pid] = identity
                while p.poll() is None:
                    own.track_descendants(identity, known); elapsed = time.monotonic() - self.unit_started
                    rss, ram, available = self.guard(known.values(), elapsed)
                    peak = max(peak, rss + ram); minimum = available if minimum is None else min(minimum, available)
                    self.publish('Real full900 ML search and1000/1000 support estimation; stock checkpoints retained',
                                 unit_peak_Linux_RSS_plus_RAM_bytes=peak)
                    time.sleep(.2)
                code = p.wait()
            if code != 0: raise RuntimeError('Production IQTREE actual exit ' + str(code))
        except BaseException as exc:
            error = repr(exc)
            if self.last_guard_sample:
                peak = max(peak, self.last_guard_sample['summed_RSS_plus_RAM_bytes'])
                minimum = self.last_guard_sample['Linux_available_bytes'] if minimum is None else min(minimum, self.last_guard_sample['Linux_available_bytes'])
            if p is not None:
                cleanup = own.cleanup_linux_helper(p, identity, known, self.stop,
                    'FULL900_PRODUCTION_' + str(os.getpid()), grace_seconds=0 if isinstance(exc, MemoryError) else 30)
                g.save(folder / 'failure_cleanup.json', {'caller_scope': 'FULL900_PRODUCTION',
                    'reviewed_legacy_cleanup_helper': 'stage08_owned_cleanup_v003.py', 'cleanup': cleanup})
            raise
        finally:
            left = [q for q in known.values() if own.current_matching(q) is not None]; members = []
            if identity is not None:
                for entry in Path('/proc').iterdir():
                    if not entry.name.isdigit(): continue
                    try:
                        q = own.identity(int(entry.name))
                        if q['process_group'] == identity['process_group']: members.append(q)
                    except (FileNotFoundError, ProcessLookupError): pass
            elapsed = time.monotonic() - self.unit_started; self.science += elapsed; self.unit_active = False
            g.save(folder / 'execution.json', {'unit': 'FULL900_SUPPORTED_PRODUCTION',
                'actual_exit_code': p.returncode if p is not None else None,
                'actual_child_waited_and_reaped': p is not None and p.poll() is not None,
                'child_identity': identity, 'captured_owned_identities': list(known.values()),
                'remaining_owned_identities': left, 'remaining_group_members': members,
                'group_closed': not left and not members, 'elapsed_seconds': elapsed,
                'peak_summed_owned_Linux_RSS_plus_private_RAM_bytes': peak,
                'minimum_Linux_available_bytes': minimum, 'error': error,
                'last_guard_sample': self.last_guard_sample, 'ended_utc': g.utc()})
            if (left or members) and error is None: raise RuntimeError('Production owned identities/groups remain')
        return g.ref(folder / 'execution.json')
