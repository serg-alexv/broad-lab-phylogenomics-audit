"""File-only bridge for genuinely closed original raw HMM searches, no binary call."""
from pathlib import Path
import hashlib
import json
import shutil

STATUS = 'REUSED_CLOSED_ORIGINAL_HMMSEARCH_RAW_NO_NEW_SEARCH'

def digest(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024**2), b''):
            h.update(block)
    return h.hexdigest()

def bound(root, row):
    p = (root / row['path']).resolve()
    if not p.is_relative_to(root.resolve()):
        raise RuntimeError('Raw reuse binding leaves project')
    if p.stat().st_size != row['bytes'] or digest(p) != row['sha256']:
        raise RuntimeError('Raw reuse binding changed: ' + str(p))
    return p

def options(args):
    # Only output, expanded-model and byte-identical original-query paths change.
    values = list(args[1:-2])
    index = values.index('--domtblout')
    del values[index:index + 2]
    return values

def restore(root, args, manifest_path, expected_manifest_sha):
    p = Path(manifest_path).resolve()
    if not p.is_relative_to(root.resolve()) or digest(p) != expected_manifest_sha:
        raise RuntimeError('Unbound raw reuse manifest')
    manifest = json.loads(p.read_text())
    closure = json.loads(bound(root, manifest['closed_parent_and_recovery']).read_text())
    if closure.get('all_old_and_recovery_groups_namespaces_IPC_FDs_closed') is not True or closure.get('all_3_QC_leases_reacquired_released_unchanged') is not True:
        raise RuntimeError('Original raw search context is not closed')
    raw = Path(args[args.index('--domtblout') + 1])
    acc = raw.parent.name
    if acc not in manifest['rows']:
        raise RuntimeError('No admitted original raw search for ' + acc)
    row = manifest['rows'][acc]
    original = json.loads(bound(root, row['actual_original_HMMER_receipt']).read_text())
    if original.get('actual_exit_code') != 0 or original.get('status') != 'ACTUAL_HMMER_EXIT_OBSERVED' or original.get('binary_handle_waited_and_reaped') is not True:
        raise RuntimeError('Original search lacks typed actual0/reap')
    checkpoint = row['raw_checkpoint']
    source = bound(root, checkpoint)
    if original.get('durable_raw_checkpoint') != checkpoint:
        raise RuntimeError('Original search/checkpoint binding differs')
    if digest(args[-1]) != checkpoint['query_faa_sha256'] or checkpoint['marker_file_sha256'] != manifest['marker_file_sha256']:
        raise RuntimeError('Original raw query/marker mismatch')
    if options(args) != options(original['argv']) or Path(args[0]).name != 'hmmsearch':
        raise RuntimeError('Scientific HMM search options changed')
    models = []
    terminators = 0
    with Path(args[-2]).open() as model:
        for line in model:
            if line.startswith('ACC '):
                models.append(line.split()[1])
            if line.rstrip() == '//':
                terminators += 1
    if len(models) != 1469 or terminators != 1469 or len(set(models)) != 1469 or set(models) != set(manifest['all1469_model_accessions']):
        raise RuntimeError('Full stock ancestor/clan expanded model inventory differs')
    if '# [ok]' not in source.read_text()[-4000:]:
        raise RuntimeError('Original raw HMM table incomplete')
    raw.parent.mkdir(parents=True, exist_ok=True)
    if raw.exists():
        raise RuntimeError('Refuse to overwrite existing raw output')
    shutil.copyfile(source, raw)
    if digest(raw) != checkpoint['sha256']:
        raise RuntimeError('Original raw copy changed')
    return {'status': STATUS, 'argv': args, 'actual_exit_code': None,
            'effective_original_search_exit_code': 0, 'no_new_HMMsearch_binary_started': True,
            'original_search_receipt': row['actual_original_HMMER_receipt'],
            'durable_raw_checkpoint': checkpoint, 'all1469_stock_model_inventory_verified': True,
            'reuse_manifest_sha256': expected_manifest_sha}
