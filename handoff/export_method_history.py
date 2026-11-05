"""Export exact public-method source history from the isolated local Tree2 Git."""
import argparse
from collections import Counter
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import zipfile

from package_policy import AA_CHARS, DNA_TOKEN, NT_CHARS, classify, prune_directory


BUNDLE = Path(__file__).resolve().parent
PROJECT = BUNDLE.parents[1]
DESTINATION = BUNDLE / 'method_history'
ROOT_METHODS = ('AGENTS.md', 'README.md', 'STATUS.md', 'STARTUP_REPORT.md', 'REBOOT_CHECKPOINT.md',
                '.gitattributes', '.gitignore')
METHOD_TREES = ('scripts', 'docs', 'config', 'patches')
SCOPES = METHOD_TREES + ROOT_METHODS
TEXT_SUFFIXES = {
    '.py', '.ps1', '.psm1', '.psd1', '.sh', '.bash', '.r', '.pl', '.awk', '.c', '.h', '.cpp', '.java',
    '.jl', '.patch', '.diff', '.md', '.rst', '.txt', '.json', '.toml', '.ini', '.cfg', '.conf', '.yaml',
    '.yml', '.xml', '.tsv', '.csv',
}
MAX_BLOB = 2 * 1024**2
MAX_ARCHIVE = 64 * 1024**2
GIT_ENV = {
    **os.environ, 'GIT_OPTIONAL_LOCKS': '0', 'GIT_NO_LAZY_FETCH': '1', 'GIT_TERMINAL_PROMPT': '0',
    'GIT_ALLOW_PROTOCOL': '', 'GIT_NO_REPLACE_OBJECTS': '1',
}
TOKEN = re.compile(
    rb'-----BEGIN [A-Z ]*PRIVATE KEY-----|'
    rb'(?<![A-Za-z0-9_])(?:github_pat_[A-Za-z0-9_]{24,}|gh[pousr]_[A-Za-z0-9]{28,}|'
    rb'sk-(?:(?:proj|svcacct)-)?[A-Za-z0-9_-]{26,}|AKIA[A-Z0-9]{16}|'
    rb'eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,})'
)
LITERAL_SECRET = re.compile(
    rb'\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|client[_-]?secret|authorization)'
    rb'["\']?\s*[:=]\s*["\'](?:Bearer\s+)?[A-Za-z0-9_+./=-]{18,}["\']', re.I
)
SECRET_NAME = re.compile(
    r'(?:private[_-]?invocation|credential|api[_-]?key|(?:^|[._-])auth(?:[._-]|$)|'
    r'(?:^|[._-])(?:access|refresh)[_-]?token(?:[._-]|$)|(?:^|[._-])session(?:[._-]|$))',
    re.I,
)


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def git(*args):
    return subprocess.run(['git', *args], cwd=PROJECT, env=GIT_ENV, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=True).stdout


def digest(data):
    return hashlib.sha256(data).hexdigest()


def row(path):
    with path.open('rb') as stream:
        return {'path': path.relative_to(BUNDLE).as_posix(), 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest(),
                'bytes': path.stat().st_size}


def source_path_reason(path):
    rel = PurePosixPath(path)
    if rel.is_absolute() or '..' in rel.parts or not rel.parts or prune_directory(rel.parent):
        return 'invalid_or_private_method_path'
    if any(SECRET_NAME.search(part) for part in rel.parts):
        return 'credential_or_private_runtime_named_path'
    if TOKEN.search(path.encode('utf-8')) or LITERAL_SECRET.search(path.encode('utf-8')):
        return 'credential_like_path_literal'
    if path in ROOT_METHODS:
        return None
    if rel.parts[0] not in METHOD_TREES or rel.suffix.casefold() not in TEXT_SUFFIXES:
        return 'outside_allowlisted_method_text_types'
    return None


def content_reason(data):
    if b'\0' in data or data.startswith((b'PK\x03\x04', b'\x1f\x8b', b'7z\xbc\xaf', b'%PDF', b'MZ')):
        return 'binary_or_archive_payload'
    try:
        data.decode('utf-8-sig')
    except UnicodeError:
        return 'non_UTF8_or_opaque_payload'
    if TOKEN.search(data) or LITERAL_SECRET.search(data):
        return 'credential_like_text_literal'
    if DNA_TOKEN.search(data):
        return 'long_nucleotide_like_text_literal'
    run = 0
    fasta_record = False
    fasta_bases = 0
    fasta_protein = False
    for line in data.splitlines():
        text = line.strip().upper()
        if text.startswith(b'>'):
            if fasta_record and fasta_bases >= 30 and not fasta_protein:
                return 'nucleotide_like_FASTA_record'
            fasta_record, fasta_bases, fasta_protein = True, 0, False
            run = 0
            continue
        symbols = set(text)
        if text and symbols <= NT_CHARS:
            run += len(text)
            if run >= 100:
                return 'wrapped_nucleotide_like_text_literal'
        else:
            run = 0
        if fasta_record and text:
            if symbols <= AA_CHARS:
                fasta_bases += len(text)
                fasta_protein |= bool((symbols - set(b'?.-')) - NT_CHARS)
            else:
                fasta_record = False
    if fasta_record and fasta_bases >= 30 and not fasta_protein:
        return 'nucleotide_like_FASTA_record'
    return None


def tree(commit):
    result = {}
    for record in git('ls-tree', '-r', '-z', '-l', '--full-tree', commit, '--', *SCOPES).split(b'\0'):
        if not record:
            continue
        header, name = record.split(b'\t', 1)
        mode, kind, oid, size = header.split()
        path = name.decode('utf-8', errors='strict')
        result[path] = (mode.decode(), kind.decode(), oid.decode(), int(size) if size != b'-' else None)
    return result


def current_members(entries):
    result = {}
    for path, (mode, kind, _, _) in entries.items():
        if source_path_reason(path) or mode not in {'100644', '100755'} or kind != 'blob':
            continue
        file = PROJECT / path
        if not file.is_file() or file.is_symlink() or file.stat().st_size > MAX_BLOB:
            continue
        if classify(PurePosixPath(path), file)[0] is None:
            continue
        data = file.read_bytes()
        if not content_reason(data):
            result.setdefault(digest(data), {'path': path, 'bytes': len(data)})
    return result


def object_bytes(process, object_id, size):
    process.stdin.write((object_id + '\n').encode('ascii'))
    process.stdin.flush()
    actual_oid, kind, count = process.stdout.readline().split()
    if actual_oid.decode() != object_id or kind != b'blob' or int(count) != size:
        raise RuntimeError('Unexpected local Git blob identity or size')
    data = process.stdout.read(size)
    if len(data) != size or process.stdout.read(1) != b'\n':
        raise RuntimeError('Short local Git blob read')
    return data


def put(stream, value):
    stream.write(json.dumps(value, ensure_ascii=True, separators=(',', ':')) + '\n')


def verify_archive(path, archives):
    with zipfile.ZipFile(path) as source:
        names = source.namelist()
        if len(names) != len(set(names)) or set(names) != {'lineage.ndjson', *archives}:
            raise RuntimeError('Historic method archive membership differs')
        for name, expected in archives.items():
            with source.open(name) as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            if actual != expected or source.getinfo(name).file_size > MAX_BLOB:
                raise RuntimeError('Historic method blob SHA256 or size differs')
        with source.open('lineage.ndjson') as stream:
            for line in stream:
                record = json.loads(line)
                if record.get('archive_path') and archives.get(record['archive_path']) != record['sha256']:
                    raise RuntimeError('Historic method lineage references an invalid blob')


def export(expected_head):
    head = git('rev-parse', 'HEAD').decode().strip()
    if head != expected_head:
        raise RuntimeError('Frozen main-package HEAD differs')
    refs = git('for-each-ref', '--format=%(refname) %(objectname)', 'refs/heads', 'refs/tags').decode().splitlines()
    ancestry = [line.split() for line in git('rev-list', '--reverse', '--topo-order', '--parents', head).decode().splitlines()]
    if not ancestry:
        raise RuntimeError('Tree2 local source history is empty')
    current = current_members(tree(head))
    DESTINATION.mkdir(exist_ok=False)
    temporary = DESTINATION / 'tree2_method_history.zip.partial'
    lineage = DESTINATION / 'lineage.ndjson.partial'
    output = DESTINATION / 'tree2_method_history.zip'
    stats, omissions = Counter(), Counter()
    by_oid = {}
    archives = {}
    parent_tree, previous = {}, None

    with subprocess.Popen(['git', 'cat-file', '--batch'], cwd=PROJECT, env=GIT_ENV,
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as objects:
        with zipfile.ZipFile(temporary, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=5) as archive:
            with lineage.open('x', encoding='utf-8', newline='\n') as stream:
                for commit, *parents in ancestry:
                    before = parent_tree if parents == [previous] else tree(parents[0]) if parents else {}
                    entries = tree(commit)
                    put(stream, {'kind': 'revision', 'commit': commit, 'parents': parents})
                    for path in sorted(set(before) | set(entries)):
                        prior, entry = before.get(path), entries.get(path)
                        if prior == entry:
                            continue
                        why = source_path_reason(path)
                        public_path = path if why != 'credential_like_path_literal' else 'PATH_SHA256:' + digest(path.encode())
                        if entry is None:
                            put(stream, {'kind': 'delete', 'commit': commit, 'path': public_path})
                            stats['deletions'] += 1
                            continue
                        mode, kind, oid, size = entry
                        if why is None and (kind != 'blob' or mode not in {'100644', '100755'}):
                            why = 'link_submodule_or_nonregular_git_object'
                        if why is None and (type(size) is not int or size > MAX_BLOB):
                            why = 'outside_per_blob_size_bound'
                        record = {'kind': 'version', 'commit': commit, 'path': public_path, 'mode': mode}
                        if why is None:
                            if oid not in by_oid:
                                data = object_bytes(objects, oid, size)
                                unsafe = content_reason(data)
                                if unsafe:
                                    by_oid[oid] = (None, unsafe)
                                else:
                                    sha = digest(data)
                                    keep = {'git_blob': oid, 'sha256': sha, 'bytes': size}
                                    if sha in current:
                                        keep['current_package_member'] = current[sha]['path']
                                        stats['unique_git_blob_aliases_to_main_package'] += 1
                                    else:
                                        target = 'blobs/' + sha
                                        if target not in archives:
                                            archive.writestr(target, data)
                                            archives[target] = sha
                                            stats['unique_historical_blob_bytes'] += size
                                        keep['archive_path'] = target
                                    by_oid[oid] = (keep, None)
                            payload, why = by_oid[oid]
                            if payload is not None:
                                record.update(payload)
                        if why:
                            record['omitted'] = why
                            omissions[why] += 1
                        else:
                            stats['retained_lineage_versions'] += 1
                        put(stream, record)
                    parent_tree, previous = entries, commit
                stream.flush()
                os.fsync(stream.fileno())
            archive.write(lineage, 'lineage.ndjson')
        objects.stdin.close()
        if objects.wait() != 0:
            raise RuntimeError('Local Git blob reader failed')
    if temporary.stat().st_size > MAX_ARCHIVE:
        raise RuntimeError('Compressed method source archive exceeded its bound')
    verify_archive(temporary, archives)
    os.rename(temporary, output)
    lineage.unlink()
    receipt = {
        'schema': 'TREE2_LOCAL_METHOD_SOURCE_HISTORY_V001', 'status': 'COMPLETE_ARCHIVE_VERIFIED',
        'source_HEAD': head, 'observed_local_head_and_tag_refs': refs, 'reachable_commits_covered': len(ancestry),
        'roots_scoped': list(SCOPES), 'maximum_raw_blob_bytes': MAX_BLOB, 'maximum_archive_bytes': MAX_ARCHIVE,
        'archive': row(output), 'counts': {**stats, 'unique_archived_sha256_blobs': len(archives)},
        'omitted_version_reasons': dict(omissions), 'main_package_manifest': 'files.ndjson',
        'current_alias_contract': 'Resolve current_package_member by exact SHA256 and byte count in the main package manifest.',
        'lineage_contract': 'All reachable commits, changes and deletions against each commit first parent. Safe source bytes use blobs/<SHA256>; omitted records give a reason without raw blob bytes.',
        'coverage_limits': 'Source-only allowlist, no .git objects, remotes, work/raw/analysis/state, private session data, commit messages, unreachable commits, uncommitted change history, or out-of-scope method helper versions.',
        'host_paths': 'Some exact source bytes contain WD-specific paths or process configuration. Historical source is evidence; machine-local state cannot be reused as live custody.',
        'verified_archive_blob_SHA256_and_lineage_references': True, 'created_utc': utc(),
    }
    with (DESTINATION / 'COMMITTED.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-head', required=True)
    export(parser.parse_args().expected_head)
