"""One real full900 supported IQ-TREE inference, with source-bound input and resume gates."""
from pathlib import Path
import gzip, hashlib, json, math, os, re, signal, subprocess, sys, time
R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / 'scripts'))


def namespace_entry(plan_path, expected):
    assert hashlib.sha256(plan_path.read_bytes()).hexdigest() == expected
    p = json.loads(plan_path.read_text()); e = R / p['work']; assert e.resolve().is_relative_to(R)
    for target in ('/tmp', '/dev/shm'):
        subprocess.run(['mount', '-t', 'tmpfs', '-o', 'size=32m,mode=1777,nosuid,nodev', 'tmpfs', target], check=True)
    (e / 'private_namespace.json').write_text(json.dumps({'mount_namespace': os.readlink('/proc/self/ns/mnt'),
        'IPC_namespace': os.readlink('/proc/self/ns/ipc'), 'private_tmpfs_max_bytes': 67108864,
        'no_global_configuration_change': True, 'namespace_closure_requires_external_evidence': True}, indent=2))
    py = R / p['python']
    os.execv(str(py), [str(py), '-B', str(Path(__file__).resolve()), str(plan_path), expected])


def main(plan_path, expected):
    import fcntl
    import marker_pilot_compute_v001 as g
    from full900_production_resume_units_v002 import Runtime
    from fullpanel_gene_metrics_v001 import parse_newick
    def interrupted(number, frame): raise InterruptedError('Production signal ' + str(number))
    signal.signal(signal.SIGTERM, interrupted); signal.signal(signal.SIGINT, interrupted)
    assert g.sha(plan_path) == expected; p = g.read(plan_path)
    assert p['schema'] == 'TREE2_ROOT_FULL900_SUPPORTED_PRODUCTION_REBOOT_RESUME_V003'
    for row in p['sources'] + p['bound_inputs']: g.bound(row)
    for row in p['tool_files']:
        tool = Path(row['path']); assert tool.stat().st_size == row['bytes'] and g.sha(tool) == row['sha256']
    scope = g.read(g.bound(p['scope_GO']))
    assert scope['status'] == 'ROOT_GO_FULL900_SUPPORTED_PRODUCTION_REBOOT_RESUME'
    assert scope['alignment_sha256'] == p['alignment']['sha256']
    assert scope['model'] == p['model'] == 'LG+F+G4' and scope['full_support_replicates'] == 1000
    assert p['unpartitioned'] is True and p['production_total_budget_seconds'] <= 604800
    assert p['production_total_budget_seconds'] == 604800 and p['cold_seconds'] == 604800
    assert p['seed'] == 20261029 and p['IQTREE_memory_target'] == '700M'
    assert p['supports'] == {'UFBoot': 1000, 'SHaLRT': 1000, 'bnni': True, 'emit_bootstrap_trees': True}
    assert p['minimum_backing_disk_bytes'] == 42949672960
    assert p['linux_RSS_plus_RAM_bytes'] == 1879048192 and p['minimum_linux_available_bytes'] == 1342177280
    assert g.read(g.bound(p['matrix_acceptance']))['status'] == 'ROOT_ACCEPTED_CLOSED_COMPUTATIONAL_INPUT_QC_ONLY'
    alignment = g.bound(p['alignment']); labels = set(g.bound(p['accession_labels']).read_text().splitlines())
    records = g.fasta(alignment, aligned=True)
    assert len(records) == 900 and set(records) == labels and {len(x) for x in records.values()} == {13071}
    g.bound(p['partition_provenance'])  # retained evidence, deliberately not a likelihood partition argument
    out = g.inside(p['output']); out.mkdir(parents=True, exist_ok=True)
    prefix = g.inside(p['prefix']); assert prefix.parent == out / 'inference'; prefix.parent.mkdir(exist_ok=True)
    assert p['compute_threads'] == 2
    assert p['attempt_id'] == 'attempt003_reboot_resume'
    assert p['work'] == 'work/full900_production_reboot_resume_v003'
    assert p['resource_fallback_count'] == 0
    assert p['cpu_affinity'] == ([2, 3] if p['compute_threads'] == 2 else [2])
    assert scope['thread_count'] == p['compute_threads'] and scope['CPU_affinity'] == p['cpu_affinity']
    args = [p['iqtree'], '-s', str(alignment), '--seqtype', 'AA', '-m', p['model'], '-T', str(p['compute_threads']),
        '--mem', '700M', '--safe', '--seed', str(p['seed']), '--cptime', '30', '-B', '1000',
        '--alrt', '1000', '--bnni', '--boot-trees', '--prefix', str(prefix)]
    compatibility = hashlib.sha256(json.dumps({'argv': args, 'alignment': p['alignment'],
        'tools': p['tool_files']}, sort_keys=True).encode()).hexdigest()
    existing = sorted(prefix.parent.glob(prefix.name + '.*'))
    # Planned reboot: exact same scientific argv, no fresh start and no fallback debit.
    def pinned(row):
        path = g.bound(row); assert path.stat().st_size == row['bytes']; return path
    resume = g.read(pinned(p['resume_authority']))
    assert resume['status'] == 'ROOT_GO_PRODUCTION_SAME_T2_REBOOT_RESUME'
    assert resume['change_kind'] == 'PLANNED_REBOOT_SAME_THREADS_2_TO_2'
    assert resume['resource_fallback_count'] == p['resource_fallback_count'] == 0
    assert resume['future_single_resource_fallback_requires_separate_admission'] is True
    human = g.read(pinned(resume['human_resume_authority']))
    assert human['explicit_resume_after_reboot'] is True
    preflight = g.read(pinned(resume['reboot_preflight']))
    assert preflight['status'] == 'ROOT_GO_REBOOT_RESUME_PREFLIGHT'
    assert preflight['host'] == 'WD' and preflight['no_scientific_owner'] is True
    assert preflight['all_required_resume_gates_clear'] is True
    assert preflight['linux_boot_id'] == Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    assert time.time() < p['production_absolute_deadline_unix'], 'Original deadline expired; new resource admission required'
    source_review = g.read(pinned(resume['independent_source_review']))
    assert source_review['status'] == 'PASS_SAME_T2_REBOOT_RESUME_SOURCE_REVIEW'
    assert source_review['reviewed_sources'] == p['sources'][:2]
    closure = g.read(pinned(resume['prior_closure_receipt']))
    assert closure['status'] == 'ROOT_ACTUAL_USER_PAUSE_AND_FULL_OWNED_CLOSURE_VERIFIED'
    assert closure['all_owned_groups_namespaces_FDs_and_four_leases_closed'] is True
    assert closure['no_other_scientific_owner'] is True and closure['planned_pause_not_scientific_failure'] is True
    assert closure['actual_IQTREE_execution'] == resume['prior_execution']
    prior_plan = g.read(pinned(resume['prior_plan']))
    prior = g.read(pinned(resume['prior_compatibility']))
    prior_execution = g.read(pinned(resume['prior_execution']))
    prior_command = g.read(pinned(resume['prior_actual_command']))
    assert prior_plan['attempt_id'] == 'attempt002' and prior_plan['compute_threads'] == 2
    assert prior_plan['resource_fallback_count'] == 0
    assert prior_command['argv'] == prior['argv'] == args, 'Reboot requires exact unchanged actual argv'
    argv_bytes = lambda value: json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    assert argv_bytes(args) == argv_bytes(prior_command['argv']) == argv_bytes(prior['argv'])
    assert prior_execution['actual_child_waited_and_reaped'] is True
    assert isinstance(prior_execution['actual_exit_code'], int) and prior_execution['actual_exit_code'] != 0
    assert prior_execution['group_closed'] is True
    assert not prior_execution['remaining_owned_identities'] and not prior_execution['remaining_group_members']
    assert prior['input_alignment'] == p['alignment'] and prior['tool_files'] == p['tool_files']
    assert prior['partition_provenance'] == p['partition_provenance'] and prior['likelihood_partitioning'] == 'UNPARTITIONED'
    assert prior_plan['output'] == p['output'] and prior_plan['prefix'] == p['prefix']
    assert prior_plan['alignment'] == p['alignment'] and prior_plan['tool_files'] == p['tool_files']
    assert prior_plan['model'] == p['model'] and prior_plan['seed'] == p['seed']
    assert prior_plan['supports'] == p['supports'] and prior_plan['cpu_affinity'] == p['cpu_affinity'] == [2, 3]
    assert prior_plan['production_absolute_deadline_unix'] == p['production_absolute_deadline_unix'] == prior['production_absolute_deadline_unix'] == resume['production_absolute_deadline_unix'] == 1793887122.165764
    assert prior_plan['production_total_budget_seconds'] == p['production_total_budget_seconds'] == 604800
    prior_debit = prior_plan['previous_production_scientific_seconds'] + prior_execution['elapsed_seconds']
    assert p['previous_production_scientific_seconds'] == resume['previous_production_scientific_seconds'] == prior_debit == 147584.57248896497
    old_args = list(prior['argv']); assert old_args.count('-T') == 1 and old_args[old_args.index('-T') + 1] == '2'
    old_signature = hashlib.sha256(json.dumps({'argv': old_args, 'alignment': prior['input_alignment'],
        'tools': prior['tool_files']}, sort_keys=True).encode()).hexdigest()
    assert old_signature == prior['compatibility_sha256'] == resume['prior_compatibility_sha256']
    assert compatibility == old_signature == resume['new_compatibility_sha256']
    snapshot = g.read(pinned(resume['immutable_complete_prefix_snapshot']))
    assert snapshot['status'] == 'IMMUTABLE_USER_REBOOT_RECOVERY_SNAPSHOT_COMMITTED'
    assert snapshot['planned_pause_not_scientific_failure'] is True
    assert len(snapshot['files']) == 5 and snapshot['checkpoint_state'] == resume['saved_checkpoint_state']
    assert {g.inside(row['original']['path']) for row in snapshot['files']} == set(existing)
    assert len(resume['preserved_prior_checkpoints']) == 5
    assert resume['preserved_prior_checkpoints'] == [row['copy'] for row in snapshot['files']]
    for row in snapshot['files']:
        original = pinned(row['original']); preserved = pinned(row['copy'])
        assert original.parent == prefix.parent and original.name == preserved.name
        assert preserved.parent == R / 'recovery/reboot_pause_20261031/full900_attempt002_prefix'
        assert row['original']['sha256'] == row['copy']['sha256'] and row['original']['bytes'] == row['copy']['bytes']
    checkpoint = Path(str(prefix) + '.ckp.gz')
    assert pinned(resume['resume_checkpoint']) == checkpoint
    assert resume['resume_checkpoint'] == next(row['original'] for row in snapshot['files'] if row['original']['path'].endswith('.ckp.gz'))
    saved = g.read(pinned(resume['saved_checkpoint_state']))
    assert saved['saved_search_counter'] == resume['saved_search_counter'] == 146
    assert saved['gzip_full_stream_and_checkpoint_header_valid'] is True
    assert saved['cumulative_production_scientific_seconds'] == prior_debit
    assert saved['original_absolute_deadline_unix'] == p['production_absolute_deadline_unix']
    counter = finished = None
    with gzip.open(checkpoint, 'rb') as stream:
        assert stream.readline().startswith(b'--- # IQ-TREE Checkpoint')
        for line in stream:  # stream through gzip CRC; never rewrite or patch checkpoint bytes
            match = re.fullmatch(rb'\s*curIteration: (\d+)\s*', line)
            if match: counter = int(match[1])
            match = re.fullmatch(rb'\s*finished: (true|false)\s*', line)
            if match: finished = match[1]
    assert counter == 146 and finished == b'false', 'Expected saved unfinished search146'
    attempt = out / 'attempts' / p['attempt_id']; attempt.mkdir(parents=True, exist_ok=False)
    common = (R / 'state/checkm2_pilot.lock').open('r+b'); fcntl.flock(common, fcntl.LOCK_EX | fcntl.LOCK_NB)
    lease = (out / 'queue.lock').open('a+b'); fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
    runtime = None
    try:
        with (attempt / 'once_claim.json').open('x') as f:
            json.dump({'plan_sha256': expected, 'compatibility_sha256': compatibility,
                'started_utc': g.utc(), 'no_automatic_retry': True,
                'same_T2_reboot_resume_authority': p['resume_authority'], 'compute_threads': p['compute_threads']}, f); f.flush(); os.fsync(f.fileno())
        g.save(attempt / 'compatibility.json', {'compatibility_sha256': compatibility,
            'argv': args, 'input_alignment': p['alignment'], 'tool_files': p['tool_files'],
            'production_absolute_deadline_unix': p['production_absolute_deadline_unix'],
            'likelihood_partitioning': 'UNPARTITIONED', 'partition_provenance': p['partition_provenance'],
            'prior_compatibility_sha256': old_signature, 'resume_authority': p['resume_authority'],
            'previous_production_scientific_seconds': p['previous_production_scientific_seconds'],
            'compute_threads': p['compute_threads'], 'cpu_affinity': p['cpu_affinity']})
        runtime = Runtime(p); runtime.publish('Resuming saved146 in the same T2 full900 ML/support search', True)
        execution = runtime.run(attempt / 'unit', args, [p['alignment'], p['matrix_acceptance'], p['partition_provenance'], p['resume_authority']])
        tree = Path(str(prefix) + '.treefile'); consensus = Path(str(prefix) + '.contree')
        report = Path(str(prefix) + '.iqtree'); log = Path(str(prefix) + '.log'); boot = Path(str(prefix) + '.ufboot')
        parse_newick(tree.read_text(), labels); parse_newick(consensus.read_text(), labels)
        text = report.read_text(); assert 'Model of substitution: ' + p['model'] in text
        size = re.search(r'Input data: (\d+) sequences with (\d+) amino-acid sites', text)
        assert size and tuple(map(int, size.groups())) == (900, 13071)
        likelihood = re.search(r'Log-likelihood of the tree:\s*([^\s]+)', text)
        assert likelihood and math.isfinite(float(likelihood[1]))
        replicate_count = sum(1 for line in boot.open() if line.strip())
        assert replicate_count == 1000, 'Actual emitted UFBoot tree count differs from requested1000'
        support_lines = [line for line in (text + '\n' + log.read_text()).splitlines()
            if any(term in line for term in ('SH-aLRT', 'UFBoot', 'ultrafast', 'bootstrap', 'correlation'))]
        files = [q for q in prefix.parent.iterdir() if q.is_file() and q.name.startswith(prefix.name + '.')]
        commit = {'schema': 'TREE2_FULL900_SUPPORTED_PRODUCTION_COMPUTED_V001',
            'status': 'FULL900_SUPPORTED_TREE_COMPUTED_PENDING_EXTERNAL_CLOSURE_AND_INDEPENDENT_QC',
            'plan': g.ref(plan_path), 'execution': execution, 'compatibility_sha256': compatibility,
            'input_alignment': p['alignment'], 'matrix_acceptance': p['matrix_acceptance'],
            'partition_provenance': p['partition_provenance'], 'likelihood_partitioning': 'UNPARTITIONED',
            'model': p['model'], 'model_is_fixed_primary_choice_not_claimed_best_fit': True,
            'taxa': 900, 'columns': 13071, 'finite_log_likelihood': float(likelihood[1]),
            'actual_emitted_UFBoot_tree_count': replicate_count, 'SHaLRT_replicates_requested': 1000,
            'support_report_evidence_lines': support_lines, 'tree': g.ref(tree), 'consensus': g.ref(consensus),
            'artifacts': [g.ref(q) for q in files],
            'elapsed_scientific_seconds': runtime.science,
            'cumulative_production_scientific_seconds': p['previous_production_scientific_seconds'] + runtime.science,
            'previous_production_scientific_seconds': p['previous_production_scientific_seconds'],
            'elapsed_scientific_seconds_this_attempt': runtime.science, 'compute_threads': p['compute_threads'],
            'previous_compatibility_sha256': old_signature, 'resume_authority': p['resume_authority'],
            'peak_Linux_RSS_plus_private_RAM_bytes': runtime.peak,
            'all_known19_genome_3_marker_9_composition_holds_preserved': True,
            'final_orthology_taxonomy_model_adequacy_and_final_tree_acceptance': False,
            'computed_utc': g.utc()}
        g.save(out / 'COMPUTED.json', commit); g.save(attempt / 'COMMITTED.json', commit)
        runtime.done = 1
        runtime.publish('Full900 supported production tree computed; exact external closure and independent Stage09 QC next',
            True, status='COMPUTED_PENDING_EXTERNAL_CLOSURE')
    except BaseException as error:
        g.save(R / p['work'] / 'failure.json', {'error': repr(error), 'at_utc': g.utc(),
            'last_guard_sample': runtime.last_guard_sample if runtime else None,
            'actual_scientific_seconds_this_attempt': runtime.science if runtime else 0,
            'previous_production_scientific_seconds': p['previous_production_scientific_seconds'],
            'production_absolute_deadline_unix': p['production_absolute_deadline_unix'],
            'all_checkpoints_and_successful_units_preserved': True, 'no_automatic_retry': True,
            'failure_or_unsearched_is_not_biological_absence': True})
        raise
    finally:
        fcntl.flock(lease, fcntl.LOCK_UN); lease.close(); fcntl.flock(common, fcntl.LOCK_UN); common.close()


if __name__ == '__main__':
    if sys.argv[1] == '--namespace': namespace_entry(Path(sys.argv[2]), sys.argv[3])
    else: main(Path(sys.argv[1]), sys.argv[2])
