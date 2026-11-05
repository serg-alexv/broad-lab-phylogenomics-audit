"""One real full900 supported IQ-TREE inference, with source-bound input and resume gates."""
from pathlib import Path
import hashlib, json, math, os, re, signal, subprocess, sys, time
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
    from full900_production_units_v001 import Runtime
    from fullpanel_gene_metrics_v001 import parse_newick
    def interrupted(number, frame): raise InterruptedError('Production signal ' + str(number))
    signal.signal(signal.SIGTERM, interrupted); signal.signal(signal.SIGINT, interrupted)
    assert g.sha(plan_path) == expected; p = g.read(plan_path)
    assert p['schema'] == 'TREE2_ROOT_FULL900_SUPPORTED_PRODUCTION_V001'
    for row in p['sources'] + p['bound_inputs']: g.bound(row)
    for row in p['tool_files']:
        tool = Path(row['path']); assert tool.stat().st_size == row['bytes'] and g.sha(tool) == row['sha256']
    scope = g.read(g.bound(p['scope_GO']))
    assert scope['status'] == 'ROOT_GO_FULL900_SUPPORTED_PRODUCTION_INFERENCE'
    assert scope['alignment_sha256'] == p['alignment']['sha256']
    assert scope['model'] == p['model'] == 'LG+F+G4' and scope['full_support_replicates'] == 1000
    assert p['unpartitioned'] is True and p['production_total_budget_seconds'] <= 604800
    assert p['production_total_budget_seconds'] > 9000 and p['cold_seconds'] > 9000
    assert p['linux_RSS_plus_RAM_bytes'] == 1879048192 and p['minimum_linux_available_bytes'] == 1342177280
    assert g.read(g.bound(p['matrix_acceptance']))['status'] == 'ROOT_ACCEPTED_CLOSED_COMPUTATIONAL_INPUT_QC_ONLY'
    alignment = g.bound(p['alignment']); labels = set(g.bound(p['accession_labels']).read_text().splitlines())
    records = g.fasta(alignment, aligned=True)
    assert len(records) == 900 and set(records) == labels and {len(x) for x in records.values()} == {13071}
    g.bound(p['partition_provenance'])  # retained evidence, deliberately not a likelihood partition argument
    out = g.inside(p['output']); out.mkdir(parents=True, exist_ok=True)
    prefix = g.inside(p['prefix']); assert prefix.parent == out / 'inference'; prefix.parent.mkdir(exist_ok=True)
    args = [p['iqtree'], '-s', str(alignment), '--seqtype', 'AA', '-m', p['model'], '-T', '1',
        '--mem', '700M', '--safe', '--seed', str(p['seed']), '--cptime', '30', '-B', '1000',
        '--alrt', '1000', '--bnni', '--boot-trees', '--prefix', str(prefix)]
    compatibility = hashlib.sha256(json.dumps({'argv': args, 'alignment': p['alignment'],
        'tools': p['tool_files']}, sort_keys=True).encode()).hexdigest()
    existing = sorted(prefix.parent.glob(prefix.name + '.*'))
    if p.get('resume_authority'):
        resume = g.read(g.bound(p['resume_authority']))
        assert resume['status'] == 'ROOT_GO_EXACT_PRODUCTION_CHECKPOINT_RESUME'
        assert resume['compatibility_sha256'] == compatibility
        assert resume['production_absolute_deadline_unix'] == p['production_absolute_deadline_unix']
        assert resume['typed_actual_exit_group_namespace_and_lease_closure_verified'] is True
        for row in resume['preserved_prior_checkpoints']: g.bound(row)
        assert any(q.name == prefix.name + '.ckp.gz' for q in existing)
    else:
        assert not existing, 'Production prefix already contains work; explicit Root resume authority required'
        assert p['previous_production_scientific_seconds'] == 0
    attempt = out / 'attempts' / p['attempt_id']; attempt.mkdir(parents=True, exist_ok=False)
    common = (R / 'state/checkm2_pilot.lock').open('r+b'); fcntl.flock(common, fcntl.LOCK_EX | fcntl.LOCK_NB)
    lease = (out / 'queue.lock').open('a+b'); fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
    runtime = None
    try:
        with (attempt / 'once_claim.json').open('x') as f:
            json.dump({'plan_sha256': expected, 'compatibility_sha256': compatibility,
                'started_utc': g.utc(), 'no_automatic_retry': True}, f); f.flush(); os.fsync(f.fileno())
        g.save(attempt / 'compatibility.json', {'compatibility_sha256': compatibility,
            'argv': args, 'input_alignment': p['alignment'], 'tool_files': p['tool_files'],
            'production_absolute_deadline_unix': p['production_absolute_deadline_unix'],
            'likelihood_partitioning': 'UNPARTITIONED', 'partition_provenance': p['partition_provenance']})
        runtime = Runtime(p); runtime.publish('Starting real full900 ML search and1000/1000 branch supports', True)
        execution = runtime.run(attempt / 'unit', args, [p['alignment'], p['matrix_acceptance'], p['partition_provenance']])
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
            'artifacts': [g.ref(q) for q in files], 'elapsed_scientific_seconds': runtime.science,
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
