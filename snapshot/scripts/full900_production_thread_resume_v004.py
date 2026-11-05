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
    from full900_production_thread_resume_units_v004 import Runtime
    from fullpanel_gene_metrics_v001 import parse_newick
    def interrupted(number, frame): raise InterruptedError('Production signal ' + str(number))
    signal.signal(signal.SIGTERM, interrupted); signal.signal(signal.SIGINT, interrupted)
    assert g.sha(plan_path) == expected; p = g.read(plan_path)
    assert p['schema'] == 'TREE2_ROOT_FULL900_SUPPORTED_PRODUCTION_THREAD_RESUME_V004'
    for row in p['sources'] + p['bound_inputs']: g.bound(row)
    for row in p['tool_files']:
        tool = Path(row['path']); assert tool.stat().st_size == row['bytes'] and g.sha(tool) == row['sha256']
    scope = g.read(g.bound(p['scope_GO']))
    assert scope['status'] == 'ROOT_GO_FULL900_SUPPORTED_PRODUCTION_THREAD_RESUME'
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
    primary = p['compute_threads'] == 4
    assert p['compute_threads'] in (2, 4)
    assert p['attempt_id'] == ('attempt004_threads4' if primary else 'attempt005_threads2_fallback')
    assert p['work'] == ('work/full900_production_thread_resume_v004' if primary else 'work/full900_production_thread_resume_v004_fallback')
    assert p['resource_fallback_count'] == (0 if primary else 1)
    assert p['cpu_affinity'] == ([0, 1, 2, 3] if primary else [2, 3])
    assert scope['thread_count'] == p['compute_threads'] and scope['CPU_affinity'] == p['cpu_affinity']
    args = [p['iqtree'], '-s', str(alignment), '--seqtype', 'AA', '-m', p['model'], '-T', str(p['compute_threads']),
        '--mem', '700M', '--safe', '--seed', str(p['seed']), '--cptime', '30', '-B', '1000',
        '--alrt', '1000', '--bnni', '--boot-trees', '--prefix', str(prefix)]
    compatibility = hashlib.sha256(json.dumps({'argv': args, 'alignment': p['alignment'],
        'tools': p['tool_files']}, sort_keys=True).encode()).hexdigest()
    existing = sorted(prefix.parent.glob(prefix.name + '.*'))
    # Only an admitted thread delta may change the old actual scientific command.
    def pinned(row):
        path = g.bound(row); assert path.stat().st_size == row['bytes']; return path
    resume = g.read(pinned(p['resume_authority']))
    assert resume['status'] == 'ROOT_GO_PRODUCTION_THREAD_ONLY_RESUME'
    assert resume['change_kind'] == ('2_TO4' if primary else '4_TO2_RESOURCE_FALLBACK')
    assert resume['resource_fallback_count'] == p['resource_fallback_count']
    human = g.read(pinned(resume['human_thread_authority']))
    assert human['explicit_four_threads_and_bounded_two_thread_fallback'] is True
    preflight = g.read(pinned(resume['fresh_preflight']))
    assert preflight['status'] == 'ROOT_GO_THREAD_RESUME_PREFLIGHT'
    assert preflight['host'] == 'WD' and preflight['no_scientific_owner'] is True
    assert preflight['all_required_resume_gates_clear'] is True
    assert preflight['linux_boot_id'] == Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    assert time.time() < p['production_absolute_deadline_unix'], 'Original deadline expired; no extension'
    source_review = g.read(pinned(resume['independent_source_review']))
    assert source_review['status'] == 'PASS_THREAD_ONLY_RESUME_SOURCE_REVIEW'
    assert source_review['reviewed_sources'] == p['sources'][:3]
    closure = g.read(pinned(resume['prior_closure_receipt']))
    assert closure['status'] == 'ROOT_ACTUAL_THREAD_MIGRATION_FULL_OWNED_CLOSURE_VERIFIED'
    assert closure['all_owned_groups_namespaces_FDs_and_four_leases_closed'] is True
    assert closure['no_other_scientific_owner'] is True
    assert closure['actual_IQTREE_execution'] == resume['prior_execution']
    prior_plan = g.read(pinned(resume['prior_plan']))
    prior = g.read(pinned(resume['prior_compatibility']))
    prior_execution = g.read(pinned(resume['prior_execution']))
    prior_command = g.read(pinned(resume['prior_actual_command']))
    assert prior_plan['attempt_id'] == ('attempt003_reboot_resume' if primary else 'attempt004_threads4')
    assert prior_plan['compute_threads'] == (2 if primary else 4)
    assert prior_plan['resource_fallback_count'] == 0
    if not primary:
        assert prior_execution['error'] is not None
        trigger = resume['fallback_trigger_kind']
        if trigger == 'MEASURED_RESOURCE_GUARD':
            sample = g.read(pinned(resume['offending_resource_sample']))
            assert (sample['summed_RSS_plus_RAM_bytes'] > p['linux_RSS_plus_RAM_bytes'] or
                    sample['Linux_available_bytes'] < p['minimum_linux_available_bytes'])
        elif trigger == 'STOCK_T4_RESTORATION_INCOMPATIBILITY':
            review = g.read(pinned(resume['restoration_incompatibility_review']))
            assert review['status'] == 'ROOT_VERIFIED_T4_STOCK_RESTORATION_INCOMPATIBILITY_NO_RESET'
            assert review['actual_failed_execution'] == resume['prior_execution']
            assert review['fallback_checkpoint'] == resume['resume_checkpoint']
            assert review['no_checkpoint_reset_or_fresh_tree'] is True
            assert review['unmodified_pristine_checkpoint_preserved'] is True
            assert review['no_general_error_or_unknown_owner'] is True
            assert review['prefix_integrity_action'] in ('CURRENT_CLOSED_PREFIX_ACCEPTED', 'BYTE_EXACT_PRISTINE_PREFIX_RESTORED_AFTER_CLOSURE')
            pristine = review['pristine_checkpoint']; pinned(pristine)
            assert pristine['sha256'] == resume['resume_checkpoint']['sha256']
            assert pristine['bytes'] == resume['resume_checkpoint']['bytes']
            if review['prefix_integrity_action'] == 'BYTE_EXACT_PRISTINE_PREFIX_RESTORED_AFTER_CLOSURE':
                recovery = g.read(pinned(review['pristine_prefix_recovery_receipt']))
                assert recovery['status'] == 'ROOT_VERIFIED_BYTE_EXACT_PRISTINE_PREFIX_RECOVERY_AFTER_CLOSURE'
                assert recovery['all_original_prefix_bytes_match_immutable_pristine_snapshot'] is True
                assert recovery['no_owned_processes_at_recovery'] is True
                assert recovery['recovered_checkpoint'] == resume['resume_checkpoint']
        else:
            raise AssertionError('No fallback on general errors, unknown owners or unqualified failures')
    assert prior_command['argv'] == prior['argv']
    old_args = list(prior['argv']); assert old_args.count('-T') == 1
    thread_index = old_args.index('-T') + 1
    assert old_args[thread_index] == ('2' if primary else '4')
    changed_args = list(old_args); changed_args[thread_index] = str(p['compute_threads'])
    assert changed_args == args, 'Only the numeric -T value may change'
    assert prior_execution['actual_child_waited_and_reaped'] is True
    assert isinstance(prior_execution['actual_exit_code'], int) and prior_execution['actual_exit_code'] != 0
    assert prior_execution['group_closed'] is True
    assert not prior_execution['remaining_owned_identities'] and not prior_execution['remaining_group_members']
    assert prior['input_alignment'] == p['alignment'] and prior['tool_files'] == p['tool_files']
    assert prior['partition_provenance'] == p['partition_provenance'] and prior['likelihood_partitioning'] == 'UNPARTITIONED'
    for key in ('output','prefix','alignment','tool_files','model','seed','supports','IQTREE_memory_target',
                'linux_RSS_plus_RAM_bytes','minimum_linux_available_bytes','minimum_backing_disk_bytes','native_reserved_bytes'):
        assert prior_plan[key] == p[key], 'Unadmitted non-thread change: ' + key
    assert prior_plan['production_absolute_deadline_unix'] == p['production_absolute_deadline_unix'] == prior['production_absolute_deadline_unix'] == resume['production_absolute_deadline_unix'] == 1793887122.165764
    assert prior_plan['production_total_budget_seconds'] == p['production_total_budget_seconds'] == 604800
    prior_debit = prior_plan['previous_production_scientific_seconds'] + prior_execution['elapsed_seconds']
    assert p['previous_production_scientific_seconds'] == resume['previous_production_scientific_seconds'] == prior_debit
    old_signature = hashlib.sha256(json.dumps({'argv': old_args, 'alignment': prior['input_alignment'],
        'tools': prior['tool_files']}, sort_keys=True).encode()).hexdigest()
    assert old_signature == prior['compatibility_sha256'] == resume['prior_compatibility_sha256']
    assert compatibility == resume['new_compatibility_sha256']
    snapshot = g.read(pinned(resume['immutable_complete_prefix_snapshot']))
    assert snapshot['status'] == 'IMMUTABLE_THREAD_MIGRATION_RECOVERY_SNAPSHOT_COMMITTED'
    assert snapshot['checkpoint_state'] == resume['saved_checkpoint_state']
    assert len(snapshot['files']) >= 5
    assert {g.inside(row['original']['path']) for row in snapshot['files']} == set(existing)
    assert resume['preserved_prior_checkpoints'] == [row['copy'] for row in snapshot['files']]
    for row in snapshot['files']:
        original = pinned(row['original']); preserved = pinned(row['copy'])
        assert original.parent == prefix.parent and original.name == preserved.name
        assert preserved.parent == R / resume['snapshot_directory']
        assert preserved.is_relative_to(R / 'recovery/four_thread_resume_20261101')
        assert row['original']['sha256'] == row['copy']['sha256'] and row['original']['bytes'] == row['copy']['bytes']
    checkpoint = Path(str(prefix) + '.ckp.gz')
    assert pinned(resume['resume_checkpoint']) == checkpoint
    assert resume['resume_checkpoint'] == next(row['original'] for row in snapshot['files'] if row['original']['path'].endswith('.ckp.gz'))
    saved = g.read(pinned(resume['saved_checkpoint_state']))
    assert saved['gzip_full_stream_and_checkpoint_header_valid'] is True
    assert saved['cumulative_production_scientific_seconds'] == prior_debit
    assert saved['original_absolute_deadline_unix'] == p['production_absolute_deadline_unix']
    assert saved['saved_search_counter'] == resume['saved_search_counter'] >= 146
    counter = finished = refined_samples = None
    section = None; boot_count = 0; boot_digest = hashlib.sha256()
    with gzip.open(checkpoint, 'rb') as stream:
        assert stream.readline().startswith(b'--- # IQ-TREE Checkpoint')
        for line in stream:  # full gzip CRC; do not edit or rewrite checkpoint bytes
            if line and not line[:1].isspace():
                section = line.strip()[:-1] if re.fullmatch(rb'[A-Za-z0-9_]+:\s*', line) else None
            if section == b'UFBoot':
                match = re.fullmatch(rb'\s+refined_samples: (\d+)\s*', line)
                if match: refined_samples = int(match[1])
                if re.match(rb'\s+\d{3}: ', line):
                    boot_count += 1; boot_digest.update(line)
            match = re.fullmatch(rb'\s*curIteration: (\d+)\s*', line)
            if match: counter = int(match[1])
            match = re.fullmatch(rb'finished: (true|false)\s*', line)
            if match: finished = match[1]
    assert counter == saved['saved_search_counter'] and finished == b'false'
    assert isinstance(refined_samples, int) and 0 <= refined_samples <= 1000
    assert refined_samples == saved['saved_refined_samples'] == resume['saved_refined_samples']
    assert boot_count == saved['UFBoot_record_count'] == 1000
    assert boot_digest.hexdigest() == saved['UFBoot_records_sha256']
    # Search and BNNI/support progress are separate: the reviewed phase receipt is mandatory.
    phase_review = g.read(pinned(resume['checkpoint_phase_review']))
    assert phase_review['status'] == 'PASS_EXACT_CLOSED_CHECKPOINT_PHASE_RESUME'
    assert phase_review['checkpoint'] == resume['resume_checkpoint']
    assert phase_review['support_progress_not_inferred_from_log_sample_count'] is True
    assert phase_review['all_durable_support_records_preserved'] is True
    assert phase_review['saved_refined_samples'] == refined_samples
    attempt = out / 'attempts' / p['attempt_id']; attempt.mkdir(parents=True, exist_ok=False)
    common = (R / 'state/checkm2_pilot.lock').open('r+b'); fcntl.flock(common, fcntl.LOCK_EX | fcntl.LOCK_NB)
    lease = (out / 'queue.lock').open('a+b'); fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
    runtime = None
    try:
        with (attempt / 'once_claim.json').open('x') as f:
            json.dump({'plan_sha256': expected, 'compatibility_sha256': compatibility,
                'started_utc': g.utc(), 'no_automatic_retry': True,
                'thread_only_resume_authority': p['resume_authority'], 'compute_threads': p['compute_threads']}, f); f.flush(); os.fsync(f.fileno())
        g.save(attempt / 'compatibility.json', {'compatibility_sha256': compatibility,
            'argv': args, 'input_alignment': p['alignment'], 'tool_files': p['tool_files'],
            'production_absolute_deadline_unix': p['production_absolute_deadline_unix'],
            'likelihood_partitioning': 'UNPARTITIONED', 'partition_provenance': p['partition_provenance'],
            'prior_compatibility_sha256': old_signature, 'resume_authority': p['resume_authority'],
            'previous_production_scientific_seconds': p['previous_production_scientific_seconds'],
            'compute_threads': p['compute_threads'], 'cpu_affinity': p['cpu_affinity']})
        runtime = Runtime(p); runtime.publish('Resuming durable full900 ML/support checkpoint with ' + str(p['compute_threads']) + ' threads', True)
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
