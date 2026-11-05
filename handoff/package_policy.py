"""Tree2 audit package selection policy, version 1."""
from pathlib import Path, PurePosixPath
import gzip
import re
import sqlite3
import stat


PRIVATE_DIRS = {
    '.cache', '.codex', '.git', '.ssh', '__pycache__', '.mypy_cache', '.pytest_cache',
    '.ruff_cache', 'codex_home', 'codex_sqlite_home', 'node_modules', '.ipynb_checkpoints',
}
RAW_PROVENANCE = {
    'acquisition_receipt.json', 'md5sum.txt', 'readme.md', 'sequence_report.jsonl',
    'assembly_data_report.jsonl', 'dataset_catalog.json',
}
NUCLEOTIDE = {'.fna', '.ffn', '.frn', '.fsa_nt', '.gb', '.gbk', '.gbff', '.dna', '.nt', '.2bit', '.ab1', '.fastq', '.fq'}
FASTA = {'.fa', '.faa', '.fas', '.fasta', '.fsa', '.pep', '.a2m', '.a3m'}
ARCHIVES = {
    '.zip', '.tar', '.tgz', '.tbz', '.tbz2', '.gz', '.xz', '.bz2', '.zst', '.7z',
    '.sif', '.squashfs', '.sqsh', '.img', '.wim', '.vhd', '.vhdx', '.conda', '.whl', '.deb', '.rpm',
}
BINARIES = {
    '.dll', '.so', '.dylib', '.exe', '.pyd', '.pyc', '.o', '.a', '.class', '.jar', '.bin',
    '.pickle', '.pkl', '.npy', '.npz', '.rds', '.rdata', '.sra', '.bam', '.cram', '.dmp',
}
SOURCE = {'.py', '.ps1', '.psm1', '.sh', '.bash', '.r', '.pl', '.awk', '.c', '.h', '.cpp', '.java', '.jl', '.patch', '.diff'}
SCIENCE_ARTIFACT = {'.tree', '.tre', '.nwk', '.newick', '.treefile', '.contree', '.ufboot', '.bionj', '.iqtree', '.mldist', '.hmm', '.cm', '.sto'}
SCIENCE_TEXT = {'.txt', '.tsv', '.csv', '.json', '.jsonl', '.xml', '.yaml', '.yml', '.nex', '.nexus', '.aln', '.msa', '.clustal', '.phy', '.phylip'}
PRESENTATION = {'.svg', '.png', '.jpeg', '.jpg', '.pdf', '.webp'}
TOOL_MODELS = ('padloc_', 'defensefinder_', 'casfinder_', 'rfam')
CHECKM1_MODEL_FILES = {
    'tools/databases/checkm1_2015_01_16/reference/.dmanifest',
    'tools/databases/checkm1_2015_01_16/reference/taxon_marker_sets.tsv',
    'tools/databases/checkm1_2015_01_16/reference/selected_marker_sets.tsv',
    'tools/databases/checkm1_2015_01_16/reference/hmms/checkm.hmm',
}
NT_CHARS = frozenset(b'ACGTRYSWKMBDHVNU')
AA_CHARS = frozenset(b'ABCDEFGHIJKLMNOPQRSTUVWXYZ*?.-')
DNA_TOKEN = re.compile(rb'(?<![A-Za-z0-9])[ACGTRYSWKMBDHVNUacgtryswkmbdhvnu]{100,}(?![A-Za-z0-9])')
DNA_NEXUS = re.compile(rb'datatype\s*=\s*(?:DNA|RNA|NUCLEOTIDE)\b', re.I)
NOTICE_NAME = re.compile(r'^(?:license|licence|licensing|copying|notice|copyright|authors|citation)(?:[._-].*)?$')
QA_DIR = re.compile(r'defence_c\d{3}r?_file_qa_v\d{3}')
HM_RECEIPT = re.compile(r'[0-9a-f]{32}(?:_o\.raw|\.json)')
QA_COLUMNS = {
    'births': [('boot', 'TEXT'), ('pid', 'INTEGER'), ('ticks', 'INTEGER'), ('value', 'TEXT')],
    'files': [('path', 'TEXT'), ('sha', 'TEXT'), ('bytes', 'INTEGER')],
}


def prune_directory(relative: PurePosixPath) -> str | None:
    parts = tuple(part.casefold() for part in relative.parts)
    if not parts:
        return None
    if any(part in PRIVATE_DIRS for part in parts):
        return 'private_or_ephemeral_runtime_directory'
    if parts[0] == 'handoff':
        return 'packaging_output_directory'
    if len(parts) > 1 and parts[0] == 'state' and parts[1].startswith(('monitor_', 'live_publisher')):
        return 'volatile_presentation_state_directory'
    if parts[:2] == ('work', 'local_continuation'):
        return 'private_headless_invocation_runtime'
    if parts[0] == 'work' and (parts[-1] in {'home', 'tmp', 'temp', 'compiler_temp', 'emptylibs'}
            or 'ram_scratch' in parts[-1] or 'defence_bulk_ram_' in parts[-1]):
        return 'ephemeral_scientific_runtime_directory'
    if any(part in {'credentials', '.aws', '.gnupg'} for part in parts):
        return 'credential_directory'
    return None


def _protein_fasta(path: Path) -> bool:
    """Reject a mixed FASTA, nucleotide-like long records, and alphabet ambiguity."""
    records = 0
    count = 0
    distinct_protein = False
    record_protein = False
    seen_header = False
    with path.open('rb') as stream:
        for line in stream:
            line = line.strip()
            if not line or line.startswith(b';'):
                continue
            if line.startswith(b'>'):
                if seen_header and (not count or (count >= 100 and not record_protein)):
                    return False
                seen_header = True
                records += 1
                count = 0
                record_protein = False
                continue
            if not seen_header:
                return False
            seq = line.upper()
            symbols = set(seq)
            if not symbols <= AA_CHARS:
                return False
            residue_symbols = symbols - set(b'*?.-')
            count += sum(letter not in b'?.-' for letter in seq)
            record_protein |= bool(residue_symbols - NT_CHARS)
            distinct_protein |= record_protein
    return bool(records and count and distinct_protein and (count < 100 or record_protein))


def _inspect_text(path: Path, *, full: bool, gff: bool = False, nexus: bool = False) -> str | None:
    """Return an omission if text has an embedded sequence or opaque payload."""
    with path.open('rb') as stream:
        prefix = stream.read(8192)
        if b'\0' in prefix:
            return 'binary_or_opaque_text_payload'
        if prefix.startswith((b'PK\x03\x04', b'\x1f\x8b', b'7z\xbc\xaf', b'\xfd7zXZ', b'BZh', b'SQLite format 3')):
            return 'archive_or_database_disguised_as_text'
        if prefix.lstrip().startswith(b'>'):
            return None if _protein_fasta(path) else 'nucleotide_or_ambiguous_fasta_payload'
        if DNA_TOKEN.search(prefix):
            return 'long_nucleotide_payload'
        if not full:
            return None
        stream.seek(0)
        pure_dna_length = 0
        for line in stream:
            if b'\0' in line:
                return 'binary_or_opaque_text_payload'
            if gff and line.lstrip().upper().startswith(b'##FASTA'):
                return 'gff_embedded_fasta_payload'
            if nexus and DNA_NEXUS.search(line):
                return 'nucleotide_alignment_payload'
            if DNA_TOKEN.search(line):
                return 'long_nucleotide_payload'
            fragment = line.strip().upper()
            if fragment and set(fragment) <= NT_CHARS:
                pure_dna_length += len(fragment)
                if pure_dna_length >= 100:
                    return 'wrapped_nucleotide_payload'
            else:
                pure_dna_length = 0
    return None


def _qa_sqlite(relative: PurePosixPath, path: Path) -> bool:
    if (len(relative.parts) != 3 or relative.parts[0].casefold() != 'analysis'
            or not QA_DIR.fullmatch(relative.parts[1].casefold())
            or path.name.casefold() != 'verified_files_and_births.sqlite'):
        return False
    with sqlite3.connect(path.resolve().as_uri() + '?mode=ro&immutable=1', uri=True) as db:
        table_names = db.execute("select name from sqlite_master where type='table' order by name").fetchall()
        if table_names != [('births',), ('files',)]:
            return False
        if db.execute("select name from sqlite_master where type in ('view','trigger')").fetchall():
            return False
        return all([(row[1], row[2]) for row in db.execute(f'pragma table_info({table})')] == expected
                   for table, expected in QA_COLUMNS.items())


def _iqtree_gzip(relative: PurePosixPath, path: Path) -> bool:
    root = relative.parts[:2]
    name = path.name.casefold()
    if not (root == ('analysis', 'phylogeny') or (
            relative.parts[0] == 'recovery' and len(root) == 2
            and root[1].startswith(('full900_', 'four_thread_resume_', 'reboot_pause_', 'reboot_resume_')))):
        return False
    if not re.fullmatch(r'(?:full_tree|pilot|host)\.(?:ckp|model|ufboot)\.gz', name):
        return False
    with gzip.open(path, 'rb') as stream:
        prefix = stream.read(128)
    if name.endswith('.ufboot.gz'):
        return prefix.lstrip().startswith(b'(')
    return prefix.startswith(b'--- # IQ-TREE Checkpoint')


def classify(relative: PurePosixPath, path: Path) -> tuple[str | None, str]:
    """Return a package group and inclusion reason, or an explicit omission."""
    if relative.is_absolute() or '..' in relative.parts or not relative.parts:
        return None, 'invalid_project_relative_path'
    folder_reason = prune_directory(relative.parent)
    if folder_reason:
        return None, folder_reason
    if path.is_symlink() or not stat.S_ISREG(path.lstat().st_mode):
        return None, 'link_or_nonregular_file'

    parts = tuple(part.casefold() for part in relative.parts)
    root, name = parts[0], parts[-1]
    ext = relative.suffix.casefold()
    all_ext = {suffix.casefold() for suffix in relative.suffixes}
    if root == 'state' and len(parts) == 2 and (
            name == 'live_stages.json' or name.startswith(('monitor_', 'live_publisher'))):
        return None, 'volatile_presentation_status_stream'
    if ('private_invocation' in name or name in {
            'auth.json', 'credentials.json', 'credential.json', '.env', '.netrc', '.npmrc',
            'cli_session.json', 'cli_session_seed.json', 'cookies.sqlite', 'session.sqlite',
            'id_rsa', 'id_ed25519', 'config.auth.json',
        } or ext in {'.key', '.pem', '.pfx', '.p12', '.kdbx'}):
        return None, 'credentials_or_private_invocation_or_session'
    if name in {'stdout.jsonl', 'last-message.txt', 'prompt.txt', 'session.jsonl'} and (
            'events' in parts or any('codex' in part or 'continuation' in part or 'cli' in part for part in parts[:-1])):
        return None, 'raw_headless_conversation_payload'
    if name == 'stderr.txt' and 'events' in parts and any('continuation' in part for part in parts):
        return None, 'raw_headless_conversation_payload'
    if ext in {'.lock', '.partial', '.tmp', '.pyc', '.wal', '.shm'} or name.endswith(('-wal', '-shm')):
        return None, 'transient_lock_or_temporary_file'
    if all_ext & NUCLEOTIDE:
        return None, 'nucleotide_genome_or_coding_sequence_payload'
    if name == 'checkm_hmm_info.pkl.gz':
        return None, 'opaque_CheckM_pickle_represented_by_marker_gene_stats_and_bin_stats'
    if ext in ARCHIVES:
        try:
            if ext == '.gz' and _iqtree_gzip(relative, path):
                return 'results', 'scope_verified_IQ_TREE_compressed_checkpoint_or_support'
        except (OSError, EOFError):
            pass
        return None, 'uninspected_archive_or_compressed_payload'
    if ext in {'.db', '.sqlite', '.sqlite3'}:
        try:
            if _qa_sqlite(relative, path):
                return 'evidence', 'known_read_only_scientific_file_and_birth_QA_database'
        except (OSError, sqlite3.Error):
            pass
        return None, 'opaque_database_or_runtime_store'
    if parts[:2] == ('metadata', 'taxonomy') and ext == '.dmp':
        reason = _inspect_text(path, full=True)
        return (None, reason) if reason else ('data_provenance', 'NCBI_taxonomy_text_dump')
    if ext in BINARIES or re.search(r'\.so(?:\.\d+)+$', name):
        return None, 'opaque_binary_or_installed_runtime_payload'

    if root == 'analysis' and len(parts) > 3 and parts[1].startswith(('defence_bulk_', 'defence_real_pilot_')):
        if 'hmmer_receipts' in parts and HM_RECEIPT.fullmatch(name):
            return 'results', 'scoped_protein_HMMER_raw_or_typed_search_receipt'
        if 'hmmer_results' in parts and ext in {'.out', '.err', '.res_hmm_extract'}:
            return 'results', 'scoped_protein_HMMER_profile_search_artifact'

    if root == 'raw':
        if name in RAW_PROVENANCE:
            reason = _inspect_text(path, full=True)
            return (None, reason) if reason else ('data_provenance', 'NCBI_accession_metadata_or_retrieval_receipt')
        if ext not in {'.faa', '.gff', '.gff3'}:
            return None, 'raw_payload_outside_metadata_protein_coordinate_allowlist'

    if root == 'tools':
        if relative.as_posix() in CHECKM1_MODEL_FILES:
            reason = _inspect_text(path, full=False)
            return (None, reason) if reason else ('data_provenance', 'pinned_CheckM1_HMM_and_taxon_marker_reference')
        if NOTICE_NAME.fullmatch(name):
            return 'tool_notices', 'original_upstream_authorship_or_license_notice'
        approved_model_tree = len(parts) > 2 and parts[1] == 'databases' and parts[2].startswith(TOOL_MODELS)
        explicit_provenance = name.endswith(('_receipt.json', '_manifest.json')) or name in {'acquisition_receipt.json', 'manifest.json'}
        if not explicit_provenance and not (
                approved_model_tree and ext in SCIENCE_TEXT | {'.hmm', '.cm', '.conf', '.cfg', '.toml'}):
            return None, 'installed_runtime_tool_cache_or_unselected_database_payload'
    if NOTICE_NAME.fullmatch(name):
        return 'tool_notices', 'original_upstream_authorship_or_license_notice'
    if ext in FASTA:
        return ('results', 'verified_amino_acid_FASTA') if _protein_fasta(path) else (None, 'nucleotide_or_ambiguous_fasta_payload')
    if ext in {'.gff', '.gff3'}:
        reason = _inspect_text(path, full=True, gff=True)
        return (None, reason) if reason else ('results', 'coordinate_only_GFF_without_embedded_sequence')
    if (ext in SOURCE or root in {'scripts', 'docs', 'patches', 'config'} or ext in {'.md', '.rst'}
            or name in {'.gitignore', '.gitattributes'}):
        reason = _inspect_text(path, full=False)
        return (None, reason) if reason else ('methods', 'project_method_source_documentation_or_configuration')
    if ext in PRESENTATION:
        return ('results', 'conventional_scientific_visual') if root in {'analysis', 'recovery', 'qc', 'evidence'} else (None, 'unscoped_presentation_binary')
    if ext in SCIENCE_ARTIFACT | SCIENCE_TEXT or root in {'analysis', 'recovery', 'qc', 'metadata', 'manifests', 'checkpoints', 'evidence', 'state', 'work', 'tools'}:
        suspicious_name = any(part in name for part in ('sequence', 'genome', 'nucleo', 'fasta', 'alignment', 'matrix', 'contig'))
        seq_format = ext in {'.nex', '.nexus', '.aln', '.msa', '.clustal', '.phy', '.phylip', '.sto'}
        full = seq_format or suspicious_name or (ext in {'', '.txt', '.tsv', '.csv'} and root in {'analysis', 'recovery', 'work'})
        reason = _inspect_text(path, full=full, nexus=ext in {'.nex', '.nexus'})
        if reason:
            return None, reason
        if root in {'analysis', 'recovery', 'qc'} or ext in SCIENCE_ARTIFACT:
            return 'results', 'analytical_output_or_preserved_scientific_checkpoint'
        if root in {'metadata', 'manifests', 'tools'}:
            return 'data_provenance', 'input_metadata_model_configuration_or_manifest'
        return 'evidence', 'operational_or_scientific_validation_receipt'
    return None, 'unclassified_outside_scoped_project_artifact_sets'
