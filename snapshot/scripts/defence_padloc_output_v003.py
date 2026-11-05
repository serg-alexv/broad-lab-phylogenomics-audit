"""Validate the two terminal output branches of the pinned stock PADLOC."""
import csv
from pathlib import Path
import re

import marker_pilot_compute_v001 as g

STOCK_R_SHA256 = 'd21ba942e80720d80027aa1740d756322560feaeb168bfa2890640d88950d4c0'
STOCK_COLUMNS = (
    'system.number', 'seqid', 'system', 'target.name', 'hmm.accession', 'hmm.name',
    'protein.name', 'full.seq.E.value', 'domain.iE.value', 'target.coverage',
    'hmm.coverage', 'start', 'end', 'strand', 'target.description',
    'relative.position', 'contig.end', 'all.domains', 'best.hits',
)
UNIT = 'PADLOC_STOCK_FULL_PROTEIN_SCOPE'


def require(condition, reason):
    if not condition:
        raise RuntimeError('PADLOC output contract: ' + reason)


def bound(ref):
    path = g.bound(ref)
    require(path.stat().st_size == ref['bytes'], 'bound artifact length changed')
    return path


def terminal_message(line, message):
    # The pinned launcher/R runtime emits [HH:MM:SS] >> MESSAGE.
    return bool(re.fullmatch(r'\[\d{2}:\d{2}:\d{2}\] >> ' + re.escape(message), line))


def report_rows(report):
    with report.open(newline='', encoding='utf-8') as stream:
        reader = csv.DictReader(stream, strict=True)
        require(tuple(reader.fieldnames or ()) == STOCK_COLUMNS, 'unexpected CSV columns')
        rows = list(reader)
    require(bool(rows), 'stock report present but has no system rows')
    for row in rows:
        require(None not in row and all(value is not None for value in row.values()),
                'malformed stock system CSV row')
        require(all(row[field] for field in ('seqid', 'system', 'target.name', 'hmm.name'))
                and all(row[field].isdigit() and int(row[field]) > 0
                        for field in ('system.number', 'start', 'end'))
                and int(row['start']) <= int(row['end']) and row['strand'] in ('+', '-'),
                'invalid stock system identity or coordinates')
    return rows


def classify(folder, execution_ref, prepared, compiled_manifest_ref, expected_hmm_sha,
             stock_R_ref, stock_threads):
    """Return stock rows and evidence for a report or a proven zero-system branch."""
    folder = g.inside(folder)
    unit = folder / 'unit'
    output = folder / 'stock_output'
    stock_raw = output / 'padloc_canonical.domtblout'
    report = output / 'padloc_canonical_padloc.csv'
    gff_report = output / 'padloc_canonical_padloc.gff'
    stdout = unit / 'stdout.txt'
    require(bound(execution_ref) == unit / 'execution.json', 'wrong execution receipt path')
    execution = g.read(unit / 'execution.json')
    require(execution['unit'] == UNIT and type(execution['actual_exit_code']) is int
            and execution['actual_exit_code'] == 0 and execution['actual_child_waited_and_reaped'] is True
            and execution['group_closed'] is True and execution['error'] is None
            and execution['remaining_owned_identities'] == [] and execution['remaining_group_members'] == [],
            'missing successful and closed stock invocation')
    require(stock_R_ref['sha256'] == STOCK_R_SHA256 and bound(stock_R_ref).name == 'padloc.R',
            'unrecognized pinned stock R source')

    command = g.read(unit / 'command.json')
    query_ref = prepared['files']['padloc_canonical.faa']
    gff_ref = prepared['files']['padloc_canonical.gff']
    argv = command['argv']
    require(command['unit'] == UNIT and command['inputs'] == [query_ref, gff_ref, compiled_manifest_ref],
            'stock invocation does not bind the exact supplied inputs and model manifest')
    require(len(argv) == 11 and argv[0] == '/usr/local/bin/padloc'
            and argv[1::2] == ['--data', '--faa', '--gff', '--outdir', '--cpu']
            and Path(argv[4]).name == 'padloc_canonical.faa'
            and Path(argv[6]).name == 'padloc_canonical.gff'
            and Path(argv[4]).parent == Path(argv[6]).parent
            and Path(argv[4]).parent.name == prepared['accession']
            and argv[8].replace('\\', '/').endswith('/' + output.relative_to(g.R).as_posix())
            and argv[10] == str(stock_threads),
            'unexpected stock PADLOC argv')

    receipts = list((folder / 'HMMER_receipts').glob('*.json'))
    require(len(receipts) == 1, 'expected one full compiled-model HMMER receipt')
    hmm_path = receipts[0]
    hmm = g.read(hmm_path)
    require(hmm['status'] == 'ACTUAL_HMMER_EXIT_AND_RAW_CHECKPOINT_OBSERVED'
            and type(hmm['actual_exit_code']) is int and hmm['actual_exit_code'] == 0
            and hmm['binary_handle_waited_and_reaped'] is True and hmm['probe_only'] is False
            and hmm['no_argument_or_threshold_changes'] is True
            and hmm['query_faa_sha256'] == query_ref['sha256']
            and hmm['model_file_sha256'] == expected_hmm_sha
            and hmm['argv'][-1] == argv[4] and len(hmm['raw_outputs']) == 1,
            'missing exact successful scientific HMMER evidence')
    raw_ref = hmm['raw_outputs'][0]
    require(raw_ref['original_stock_output_path'] == argv[8] + '/padloc_canonical.domtblout'
            and bound(raw_ref).parent == hmm_path.parent and stock_raw.is_file(),
            'missing linked original and receipt-copy domain table')
    stock_raw_ref = g.ref(stock_raw)
    require(all(stock_raw_ref[key] == raw_ref[key] for key in ('bytes', 'sha256')),
            'original and receipt-copy domain table differ')
    with stock_raw.open('rb') as stream:
        stream.seek(max(0, stock_raw_ref['bytes'] - 4096))
        require(stream.read().splitlines()[-1:] == [b'# [ok]'], 'incomplete HMMER domain table')

    lines = stdout.read_text(encoding='utf-8').splitlines()
    require(len(lines) >= 3 and any(terminal_message(line, 'Searching padloc_canonical for defence systems')
                                    for line in lines[:-1]), 'missing stock rules invocation')
    zero = 'Nothing found for padloc_canonical'
    if report.exists() or gff_report.exists():
        require(report.is_file() and gff_report.is_file() and gff_report.stat().st_size > 0
                and not any(terminal_message(line, zero) for line in lines)
                and terminal_message(lines[-1], "Writing output to '" + argv[8] + "/padloc_canonical_padloc.csv'"),
                'stock report or terminal report message missing or contradictory')
        rows = report_rows(report)
        state, report_ref = 'STOCK_REPORT_PRESENT_VALIDATED', g.ref(report)
    else:
        require(terminal_message(lines[-1], zero)
                and sum(terminal_message(line, zero) for line in lines) == 1,
                'missing report without exact stock zero-system proof')
        rows, state, report_ref = [], 'STOCK_ZERO_SYSTEMS_NO_REPORT_VALIDATED', None

    return rows, {'state': state, 'report': report_ref, 'stdout': g.ref(stdout),
                  'stock_R_source': stock_R_ref, 'stock_domtblout': stock_raw_ref,
                  'typed_HMMER_receipt': g.ref(hmm_path)}
