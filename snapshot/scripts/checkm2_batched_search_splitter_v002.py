"""Split one successful merged author-query search without changing any result fields.

Standalone future source only. This module never starts a search or imports models.
A published commit binds ONE search execution/debit for every shard together.
"""
from contextlib import ExitStack
from decimal import Decimal, InvalidOperation
from pathlib import Path
import hashlib, json, math, os, re, stat, uuid

ACCESSION = re.compile(r'GC[AF]_\d{9}\.\d+')
INTEGER = re.compile(r'[0-9]+')
COLUMNS = ('qseqid','sseqid','pident','length','mismatch','gapopen','qstart','qend','sstart','send','evalue','bitscore')
SEPARATOR = '\u03a9'


def _encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n').encode('utf-8')


def _digest(value):
    return hashlib.sha256(_encoded(value)).hexdigest()


def _contained(root, value):
    root = Path(root).resolve()
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root) or resolved == root:
        raise ValueError('Artifact/output must be strictly inside the project')
    # Refuse redirection through either POSIX symlinks or Windows reparse points.
    current = candidate
    while current != root and current.is_relative_to(root):
        if current.exists() or current.is_symlink():
            info = current.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise ValueError('Symlink/reparse artifacts are not accepted')
        current = current.parent
    return resolved


def _file_ref(root, path):
    path = _contained(root, path)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError('A regular file is required')
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    after = path.stat()
    identity = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns)
    if identity(before) != identity(after):
        raise ValueError('Artifact changed while hashing')
    return {'path': path.relative_to(Path(root).resolve()).as_posix(), 'sha256': digest.hexdigest(), 'bytes': after.st_size}


def _bind(root, reference):
    actual = _file_ref(root, reference['path'])
    if actual['sha256'] != reference['sha256'] or actual['bytes'] != reference['bytes']:
        raise ValueError('Bound source artifact changed')
    return _contained(root, reference['path'])


def _search_success(root, reference):
    receipt = json.loads(_bind(root, reference).read_text(encoding='utf-8-sig'))
    elapsed = receipt.get('elapsed_seconds')
    if (type(receipt.get('exit_code')) is not int or receipt['exit_code'] != 0
            or receipt.get('owned_group_empty') is not True
            or receipt.get('remaining_owned_processes') != []
            or type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0):
        raise ValueError('Observed search exit0, closed owned group and known debit are required')
    return elapsed


def query_inventory(root, query_fasta, declared_accessions):
    names = list(declared_accessions)
    if (not 1 <= len(names) <= 250 or len(set(names)) != len(names)
            or any(not isinstance(n, str) or not ACCESSION.fullmatch(n) for n in names)):
        raise ValueError('One to250 distinct versioned declared accessions are required')
    inventory = {}; by_accession = {name: [] for name in names}
    current = None; length = 0; sequence_hash = None
    def finish():
        if current is not None:
            if not length:
                raise ValueError('Empty query sequence')
            inventory[current] = {'accession': current.partition(SEPARATOR)[0], 'length': length,
                                  'sequence_sha256': sequence_hash.hexdigest()}
    with _bind(root, query_fasta).open(encoding='utf-8', newline='') as handle:
        for line_number, line in enumerate(handle, 1):
            body = line.rstrip('\r\n')
            if body.startswith('>'):
                finish(); current = body[1:]
                accession, separator, gene = current.partition(SEPARATOR)
                if (not separator or not gene or accession not in by_accession
                        or any(c.isspace() for c in current) or current in inventory):
                    raise ValueError('Unknown genome, malformed or duplicate query header at line' + str(line_number))
                by_accession[accession].append(current); length = 0; sequence_hash = hashlib.sha256()
            else:
                if current is None or not re.fullmatch(r'[A-Za-z*]+', body):
                    raise ValueError('Malformed author-query FASTA sequence at line' + str(line_number))
                sequence_hash.update(body.encode('ascii')); length += len(body)
    finish()
    if any(not ids for ids in by_accession.values()):
        raise ValueError('A declared input is missing from the actual query inventory')
    _bind(root, query_fasta)
    return names, inventory, by_accession


def validate_row(line, inventory):
    fields = line.rstrip('\r\n').split('\t')
    if len(fields) != 12 or any(not f or f != f.strip() for f in fields):
        raise ValueError('Exactly12 nonempty unmodified fields are required')
    if fields[0] not in inventory:
        raise ValueError('Unknown query/genome in merged results')
    try:
        pident, evalue, bitscore = (Decimal(fields[i]) for i in (2, 10, 11))
        if (not all(x.is_finite() for x in (pident, evalue, bitscore))
                or not 0 <= pident <= 100 or evalue < 0 or bitscore < 0):
            raise ValueError('Invalid finite numeric domain')
        if any(not INTEGER.fullmatch(fields[i]) for i in range(3, 10)):
            raise ValueError('Alignment count/coordinate field is not an integer')
        length, mismatch, gapopen, qstart, qend, sstart, send = map(int, fields[3:10])
        if (length <= 0 or not 0 <= mismatch <= length or not 0 <= gapopen <= length
                or not 1 <= qstart <= qend <= inventory[fields[0]]['length']
                or not 1 <= sstart <= send):
            raise ValueError('Invalid alignment counts/coordinates')
    except InvalidOperation as error:
        raise ValueError('Malformed numeric field') from error
    return inventory[fields[0]]['accession'], tuple(fields)


def _resume(root, destination, expected_sha, inputs, names):
    commit = destination / 'commit.json'
    if not expected_sha or _file_ref(root, commit)['sha256'] != expected_sha:
        raise FileExistsError('Existing output requires its exact externally retained commit SHA')
    value = json.loads(commit.read_text(encoding='utf-8'))
    if (value.get('status') != 'ONE_CLOSED_SEARCH_SPLIT_COMMITTED_NOT_GENOME_QC'
            or value['inputs'] != inputs or value['declared_accessions'] != names):
        raise ValueError('Resume source/identity binding differs')
    if {p.name for p in destination.iterdir()} != {'commit.json', *[n + '.tsv' for n in names]}:
        raise ValueError('Committed shard inventory changed')
    for shard in value['shards']:
        _bind(root, shard['artifact'])
        if shard['search_binding_id'] != value['search_binding_id']:
            raise ValueError('Shard lost its one-search parent binding')
    return _file_ref(root, commit)


def split_search(*, project_root, query_fasta, merged_tsv, search_execution,
                 declared_accessions, destination, expected_existing_commit_sha256=None):
    """Atomically publish files+commit; resume only a separately SHA-bound complete commit.

    Failed/unknown searches cannot publish shards. A valid zero-row shard means only
    that the successful search reported no hits; it is never a defence/QC negative.
    """
    root = Path(project_root).resolve()
    names, inventory, by_accession = query_inventory(root, query_fasta, declared_accessions)
    elapsed = _search_success(root, search_execution)
    _bind(root, merged_tsv)
    inputs = {'query_fasta': dict(query_fasta), 'merged_tsv': dict(merged_tsv), 'search_execution': dict(search_execution)}
    destination = _contained(root, destination)
    if destination.exists():
        return _resume(root, destination, expected_existing_commit_sha256, inputs, names)
    if expected_existing_commit_sha256:
        raise ValueError('Previously committed output is missing; do not silently reconstruct it')
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.with_name(destination.name + '.staging_' + uuid.uuid4().hex)
    staging.mkdir(exist_ok=False)
    counts = {name: 0 for name in names}; hits = {name: set() for name in names}; distinct = {name: set() for name in names}
    with ExitStack() as stack:
        outputs = {name: stack.enter_context((staging / (name + '.tsv')).open('w', encoding='utf-8', newline='\n')) for name in names}
        with _bind(root, merged_tsv).open(encoding='utf-8', newline='') as handle:
            for line in handle:
                accession, fields = validate_row(line, inventory)
                outputs[accession].write('\t'.join(fields) + '\n')
                counts[accession] += 1; hits[accession].add(fields[0]); distinct[accession].add(fields)
        for handle in outputs.values():
            handle.flush(); os.fsync(handle.fileno())
    # Do not promote output if any trusted input changed during parsing.
    for reference in inputs.values():
        _bind(root, reference)
    binding = _digest({'inputs': inputs, 'declared_accessions': names})
    destination.mkdir(exist_ok=False)  # Atomic reservation; never overwrite an old partial/complete output.
    shards = []
    for name in names:
        temporary = staging / (name + '.tsv'); target = destination / temporary.name
        os.link(temporary, target)  # Atomic create for each contained immutable shard.
        shards.append({'accession': name, 'artifact': _file_ref(root, target), 'search_binding_id': binding,
                       'query_count': len(by_accession[name]), 'reported_hit_query_count': len(hits[name]),
                       'unreported_query_count': len(by_accession[name]) - len(hits[name]),
                       'rows': counts[name], 'unique_rows': len(distinct[name]),
                       'duplicate_rows': counts[name] - len(distinct[name]),
                       'availability': 'SEARCH_SUCCEEDED_WITH_REPORTED_HITS' if counts[name] else 'SEARCH_SUCCEEDED_NO_REPORTED_HITS',
                       'QC_or_defence_negative': False})
    value = {'schema': 'TREE2_BATCHED_SEARCH_SHARDS_V002', 'status': 'ONE_CLOSED_SEARCH_SPLIT_COMMITTED_NOT_GENOME_QC',
             'inputs': inputs, 'declared_accessions': names, 'query_count': len(inventory), 'columns': list(COLUMNS),
             'search_binding_id': binding, 'search_debit': {'actual_unit_count': 1, 'actual_elapsed_seconds': elapsed,
             'per_row_debits_or_fake_unit_receipts_created': False}, 'shards': shards,
             'field_values_and_multiplicity_untouched': True, 'output_newlines': 'LF',
             'no_hit_is_not_failed_unknown_or_biological_negative': True,
             'genome_QC_or_model_validation_performed': False,
             'search_batching_memory_performance_or_single_query_equivalence_proven': False}
    temporary_commit = staging / 'commit.json'
    with temporary_commit.open('xb') as handle:
        handle.write(_encoded(value)); handle.flush(); os.fsync(handle.fileno())
    os.link(temporary_commit, destination / 'commit.json')  # Publish the parent authority LAST.
    return _file_ref(root, destination / 'commit.json')
