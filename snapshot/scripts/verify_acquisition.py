#!/usr/bin/env python3
"""Independent local acquisition verification; never modifies source objects.

Checks NCBI package MD5s, receipt SHA256s, catalog sizes, sequence/report identity,
and GFF coordinate/protein joins. This is not biological quality/taxonomy QC.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import csv
from urllib.parse import unquote
import uuid

ROOT = Path(__file__).resolve().parents[1]
ACCESSION = re.compile(r"GC[AF]_\d{9}\.\d+\Z")
GFF_DOCUMENTATION = "https://www.ncbi.nlm.nih.gov/datasets/docs/v2/reference-docs/file-formats/annotation-files/about-ncbi-gff3/"


def digest(path, algorithm="sha256"):
    h = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def safe_path(base, relative):
    """Source manifest names are POSIX paths; reject cross-platform traversal."""
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative or "\x00" in relative:
        raise ValueError(f"Unsafe manifest path: {relative!r}")
    relative = relative.removeprefix("./")
    rel = PurePosixPath(relative)
    if rel.is_absolute() or any(part in ("..", "") for part in rel.parts):
        raise ValueError(f"Unsafe manifest path: {relative!r}")
    destination = base.joinpath(*rel.parts)
    destination.resolve().relative_to(base.resolve())
    if destination.is_symlink() or not destination.is_file():
        raise ValueError(f"Missing, non-file or symlink source: {relative}")
    return destination


def jsonl(path):
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def fasta(path, alphabet=None):
    records, identifier, parts = [], None, []
    with path.open(encoding="ascii") as stream:
        for number, line in enumerate(stream, 1):
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if identifier is not None:
                    records.append((identifier, "".join(parts)))
                fields = line[1:].split()
                if not fields:
                    raise ValueError(f"Empty FASTA header at {path.name}:{number}")
                identifier, parts = fields[0], []
            else:
                if identifier is None or any(character.isspace() for character in line):
                    raise ValueError(f"Malformed FASTA at {path.name}:{number}")
                sequence = line.upper()
                if alphabet is not None and set(sequence) - alphabet:
                    raise ValueError(f"Invalid nucleotide symbols at {path.name}:{number}")
                parts.append(sequence)
    if identifier is not None:
        records.append((identifier, "".join(parts)))
    if not records or any(not sequence for _, sequence in records):
        raise ValueError(f"Empty FASTA record/file: {path}")
    return records


def n50(lengths):
    half = sum(lengths) / 2
    cumulative = 0
    for length in sorted(lengths, reverse=True):
        cumulative += length
        if cumulative >= half:
            return length
    return 0


def attributes(text):
    result = {}
    for field in text.split(";"):
        if "=" in field:
            key, value = field.split("=", 1)
            result[unquote(key)] = unquote(value)
    return result


def verify_one(folder):
    accession = folder.name
    errors, warnings, checks = [], [], []
    result = {"accession": accession, "errors": errors, "warnings": warnings, "checks": checks,
              "independent_biological_qc": "NOT_RUN", "taxonomy_sequence_validation": "NOT_RUN",
              "translation_validation": "NOT_RUN", "uniform_gene_calling": "NOT_RUN"}

    def check(name, passed, **details):
        checks.append({"check": name, "pass": bool(passed), **details})
        if not passed:
            errors.append(name)

    receipt_path = folder / "acquisition_receipt.json"
    receipt_start_hash = digest(receipt_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    result["receipt_sha256"] = receipt_start_hash
    check("receipt_accession", receipt.get("accession") == accession)
    check("receipt_acquisition_pass", receipt.get("acquisition_status") == "PASS")

    receipt_files = {}
    for item in receipt.get("files", []):
        name = item["path"]
        path = safe_path(folder, name)
        check("receipt_file_hash:" + name, digest(path) == item["sha256"], actual_bytes=path.stat().st_size)
        check("receipt_file_bytes:" + name, path.stat().st_size == item["bytes"])
        check("receipt_file_unique:" + name, name not in receipt_files)
        receipt_files[name] = item
    check("receipt_manifest_nonempty", bool(receipt_files))

    md5_path = safe_path(folder, "md5sum.txt")
    md5_entries = []
    for number, line in enumerate(md5_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        match = re.fullmatch(r"([0-9a-fA-F]{32}) [ *](.+)", line)
        if not match:
            raise ValueError(f"Malformed md5sum.txt line {number}")
        expected, relative = match.groups()
        relative = relative.removeprefix("./")
        path = safe_path(folder, relative)
        actual = digest(path, "md5")
        check("ncbi_md5:" + relative, actual == expected.lower(), expected=expected.lower(), actual=actual)
        check("md5_path_in_receipt:" + relative, relative in receipt_files)
        md5_entries.append(relative)
    check("ncbi_md5_manifest_nonempty", bool(md5_entries))
    check("ncbi_md5_unique_paths", len(md5_entries) == len(set(md5_entries)))
    result["source_md5_files_verified"] = len(md5_entries)
    result["source_md5_manifest_sha256"] = digest(md5_path)

    data = folder / "ncbi_dataset" / "data"
    reports = jsonl(safe_path(folder, "ncbi_dataset/data/assembly_data_report.jsonl"))
    check("one_assembly_report", len(reports) == 1)
    if len(reports) != 1:
        raise ValueError("Cannot uniquely identify assembly report")
    report = reports[0]
    check("report_accession", report.get("accession") == accession)
    check("report_current_accession", report.get("currentAccession", accession) == accession)
    result["source_taxid"] = report.get("organism", {}).get("taxId")
    result["source_organism_name"] = report.get("organism", {}).get("organismName")
    assembly_info = report.get("assemblyInfo", {})
    biosample_attrs = {item.get("name", ""): item.get("value")
                       for item in assembly_info.get("biosample", {}).get("attributes", [])}
    genome_notes = assembly_info.get("genomeNotes", [])
    result["source_assembly_context"] = {
        "genome_notes": genome_notes,
        "declared_metagenome_derived": any("derived from metagenome" in note.lower() for note in genome_notes),
        "investigation_type": biosample_attrs.get("investigation_type"),
        "submitter_completeness_score": biosample_attrs.get("completeness score"),
        "submitter_contamination_score": biosample_attrs.get("contamination score"),
        "submitter_completeness_software": biosample_attrs.get("completeness software"),
        "interpretation": "Source declarations only; independent biological QC remains NOT_RUN."
    }

    catalog = json.loads(safe_path(folder, "ncbi_dataset/data/dataset_catalog.json").read_text(encoding="utf-8"))
    type_paths = {}
    for assembly in catalog.get("assemblies", []):
        if assembly.get("accession"):
            check("catalog_accession", assembly["accession"] == accession)
        for entry in assembly.get("files", []):
            path = safe_path(data, entry["filePath"])
            expected_size = entry.get("uncompressedLengthBytes")
            if expected_size is not None:
                check("catalog_size:" + entry["filePath"], path.stat().st_size == int(expected_size))
            relative = path.relative_to(folder).as_posix()
            check("catalog_path_in_source_md5:" + entry["filePath"], relative in md5_entries)
            type_paths.setdefault(entry["fileType"], []).append(path)

    def single(kind):
        paths = type_paths.get(kind, [])
        check("one_catalog_file:" + kind, len(paths) == 1)
        if len(paths) != 1:
            raise ValueError("Missing/ambiguous catalog type: " + kind)
        return paths[0]

    nucleotides = fasta(single("GENOMIC_NUCLEOTIDE_FASTA"), set("ACGTRYSWKMBDHVN"))
    nucleotide_ids = [identifier for identifier, _ in nucleotides]
    check("unique_fna_ids", len(nucleotide_ids) == len(set(nucleotide_ids)))
    lengths = {identifier: len(sequence) for identifier, sequence in nucleotides}
    total = sum(lengths.values())
    ambiguity = sum(sum(count for base, count in Counter(sequence).items() if base not in "ACGT") for _, sequence in nucleotides)
    gap_contigs = [len(part) for _, sequence in nucleotides for part in re.split(r"N{10,}", sequence) if part]
    sequence_stats = {"total_bp": total, "fasta_records": len(nucleotides), "record_n50": n50(list(lengths.values())),
                      "ambiguous_bases": ambiguity, "ambiguous_fraction": ambiguity / total,
                      "record_lengths": lengths, "n10_gap_split_contigs": len(gap_contigs),
                      "n10_gap_split_n50": n50(gap_contigs),
                      "gap_split_definition": "Exploratory contigs split at N runs >=10; not presumed identical to NCBI contig definition."}
    result["fna"] = sequence_stats
    stats = report.get("assemblyStats", {})
    check("fna_total_matches_assembly_report", total == int(stats["totalSequenceLength"]))
    if "numberOfScaffolds" in stats:
        check("fna_records_match_report_scaffolds", len(nucleotides) == int(stats["numberOfScaffolds"]))
    if "scaffoldN50" in stats:
        check("fna_record_n50_matches_report_scaffold_n50", sequence_stats["record_n50"] == int(stats["scaffoldN50"]))
    sequence_stats["source_number_of_contigs"] = stats.get("numberOfContigs")
    sequence_stats["source_contig_n50"] = stats.get("contigN50")
    if stats.get("numberOfContigs") != len(nucleotides):
        warnings.append("FASTA record/scaffold count differs from source contig count; these are distinct metrics.")
    receipt_stats = receipt.get("sequence_qc", {})
    for metric, value in (("total_sequence_length", total), ("contigs", len(nucleotides)), ("ambiguous_bases", ambiguity)):
        if metric in receipt_stats:
            check("fna_matches_receipt:" + metric, receipt_stats[metric] == value)

    seq_reports = jsonl(single("SEQUENCE_REPORT"))
    seen_sequence_ids = []
    for item in seq_reports:
        check("sequence_report_assembly:" + str(item.get("refseqAccession", item.get("genbankAccession"))), item.get("assemblyAccession") == accession)
        alternatives = {item.get(key) for key in ("refseqAccession", "genbankAccession", "sequenceName") if item.get(key)}
        matching = alternatives.intersection(lengths)
        check("sequence_report_id_join:" + str(sorted(alternatives)), len(matching) == 1)
        if len(matching) == 1:
            identifier = matching.pop()
            check("sequence_report_length:" + identifier, lengths[identifier] == int(item["length"]))
            seen_sequence_ids.append(identifier)
    check("sequence_report_exact_fna_coverage", set(seen_sequence_ids) == set(nucleotide_ids) and len(seen_sequence_ids) == len(nucleotide_ids))

    # Requested annotation types are optional in unannotated NCBI packages.
    # Their absence does not invalidate an otherwise validated DNA object.
    protein_paths, gff_paths = type_paths.get("PROTEIN_FASTA", []), type_paths.get("GFF3", [])
    check("protein_catalog_not_ambiguous", len(protein_paths) <= 1)
    check("gff_catalog_not_ambiguous", len(gff_paths) <= 1)
    protein_present, gff_present = len(protein_paths) == 1, len(gff_paths) == 1
    source_annotation = receipt.get("source_annotation", {})
    for flag, present in (("protein_fasta_present", protein_present), ("gff_present", gff_present)):
        if flag in source_annotation:
            check("annotation_availability_matches_receipt:" + flag, source_annotation[flag] is present)
    result["source_annotation_availability"] = {
        "protein_fasta": "AVAILABLE" if protein_present else "UNAVAILABLE",
        "gff": "AVAILABLE" if gff_present else "UNAVAILABLE"
    }
    result["annotation_validation"] = "EVALUATED_SOURCE_JOINS" if protein_present and gff_present else "UNAVAILABLE"
    if not (protein_present and gff_present):
        warnings.append("Optional source FAA/GFF unavailable; annotation joins are UNAVAILABLE pending uniform gene calling, not negative predictions.")
    proteins = fasta(single("PROTEIN_FASTA")) if protein_present else []
    protein_ids = [identifier for identifier, _ in proteins]
    protein_set = set(protein_ids)
    duplicate_protein_ids = sorted(identifier for identifier, count in Counter(protein_ids).items() if count > 1)
    if duplicate_protein_ids:
        warnings.append("Duplicate source FAA identifiers require normalization before ordered downstream gene calls.")
    gff_path = single("GFF3") if gff_present else None
    rows, gff_accessions, regions = [], [], {}
    for number, line in enumerate(gff_path.read_text(encoding="utf-8").splitlines() if gff_path else [], 1):
        if line.startswith("##FASTA"):
            break
        if line.startswith("#!genome-build-accession"):
            gff_accessions += ACCESSION.findall(line.split(":", 1)[-1].strip())
        if line.startswith("##sequence-region "):
            parts = line.split()
            if len(parts) == 4:
                regions[unquote(parts[1])] = (int(parts[2]), int(parts[3]))
        if not line.strip() or line.startswith("#"):
            continue
        fields = line.rstrip("\r\n").split("\t")
        if len(fields) != 9:
            raise ValueError(f"Malformed GFF row {number}")
        fields[0] = unquote(fields[0])
        rows.append((number, fields, attributes(fields[8])))
    if gff_present:
        check("gff_assembly_accession", gff_accessions == [accession], observed=gff_accessions)
    circular = {fields[0] for _, fields, attrs in rows if fields[2] == "region" and attrs.get("Is_circular") == "true"}
    bad_coordinates, circular_virtual, cds_references, cds_unidentified = [], [], [], []
    gff_seqids = set()
    cds_rows = 0
    for number, fields, attrs in rows:
        identifier, feature = fields[0], fields[2]
        gff_seqids.add(identifier)
        start, end = int(fields[3]), int(fields[4])
        limit = lengths.get(identifier)
        if limit is None or start < 1 or end < start:
            bad_coordinates.append({"line": number, "seqid": identifier, "start": start, "end": end})
        elif end > limit:
            if identifier in circular and start <= limit and end - start + 1 <= limit:
                circular_virtual.append({"line": number, "seqid": identifier, "start": start, "end": end})
            else:
                bad_coordinates.append({"line": number, "seqid": identifier, "start": start, "end": end, "length": limit})
        if feature == "CDS":
            cds_rows += 1
            reference = attrs.get("protein_id") or attrs.get("Name")
            if reference:
                cds_references.append(reference)
            else:
                cds_unidentified.append({"line": number, "id": attrs.get("ID"), "pseudo": attrs.get("pseudo"), "exception": attrs.get("exception")})
    if gff_present:
        check("gff_seqids_exist_in_fna", gff_seqids.issubset(lengths), missing=sorted(gff_seqids - lengths.keys()))
        check("gff_coordinates_valid", not bad_coordinates, invalid=bad_coordinates)
    for identifier, (start, end) in regions.items():
        check("gff_sequence_region:" + identifier, identifier in lengths and start == 1 and end == lengths[identifier])
    missing_proteins = sorted(set(cds_references) - protein_set) if protein_present and gff_present else None
    unmatched_faa = sorted(protein_set - set(cds_references)) if protein_present and gff_present else None
    if protein_present and gff_present and (missing_proteins or unmatched_faa or cds_unidentified):
        warnings.append("Source CDS/FAA join is not exact; coverage is recorded for annotation normalization review, not asserted as a biological mismatch.")
    result["annotation_join"] = {"gff_feature_rows": len(rows), "gff_sequence_ids": sorted(gff_seqids),
                                "fna_ids_without_gff_features": sorted(lengths.keys() - gff_seqids),
                                "cds_rows": cds_rows, "cds_rows_with_protein_reference": len(cds_references),
                                "unique_cds_protein_references": len(set(cds_references)),
                                "faa_records": len(proteins), "unique_faa_ids": len(protein_set),
                                "duplicate_faa_ids": duplicate_protein_ids,
                                "unique_cds_protein_reference_coverage": len(set(cds_references) & protein_set) / len(set(cds_references)) if cds_references else None,
                                "faa_id_coverage_by_cds": len(set(cds_references) & protein_set) / len(protein_set) if protein_set and gff_present else None,
                                "cds_protein_ids_not_in_faa": missing_proteins, "faa_ids_not_in_cds": unmatched_faa,
                                "cds_without_protein_reference": cds_unidentified,
                                "circular_virtual_coordinate_rows": circular_virtual,
                                "circular_coordinate_policy_source": GFF_DOCUMENTATION}
    result["annotation_join"]["status"] = result["annotation_validation"]
    if not gff_present:
        for key in ("gff_feature_rows", "cds_rows", "cds_rows_with_protein_reference", "unique_cds_protein_references"):
            result["annotation_join"][key] = None
        result["annotation_join"]["fna_ids_without_gff_features"] = None
    if not protein_present:
        result["annotation_join"]["faa_records"] = None
        result["annotation_join"]["unique_faa_ids"] = None
    if not (gff_present and protein_present):
        result["annotation_join"]["unique_cds_protein_reference_coverage"] = None
        result["annotation_join"]["faa_id_coverage_by_cds"] = None
    check("receipt_unchanged_during_verification", digest(receipt_path) == receipt_start_hash)
    result["acquisition_validation"] = "FAIL" if errors else "PASS_WITH_NOTES" if warnings else "PASS"
    return result


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--retry-failed-from", type=Path,
                        help="Only reverify FAIL accessions from a preserved qc/history report and merge unchanged accepted records")
    parser.add_argument("--verify-new-from", type=Path,
                        help="Verify only newly committed accessions absent from a preserved all-PASS qc/history report; retain every old result unchanged")
    args = parser.parse_args()
    if args.retry_failed_from and args.verify_new_from:
        parser.error("Choose one incremental mode")
    root = args.root.resolve()
    if root != ROOT.resolve():
        parser.error("Verifier is scoped to this script's project root")
    previous, previous_hash, prior_report_path = None, None, None
    report_path = root / "qc" / "acquisition_validation.json"
    batch_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    script_hash = digest(Path(__file__))
    if args.retry_failed_from or args.verify_new_from:
        prior_report_path = (args.retry_failed_from or args.verify_new_from).resolve()
        try:
            prior_report_path.relative_to(root / "qc" / "history")
        except ValueError:
            parser.error("Incremental verification requires a preserved report inside this project's qc/history")
        previous_hash = digest(prior_report_path)
        if digest(report_path) != previous_hash:
            parser.error("Current report differs from preserved baseline; reconcile before incremental merge")
        previous = json.loads(prior_report_path.read_text(encoding="utf-8"))
        old_results = previous["results"]
        old_accessions = [item["accession"] for item in old_results]
        if len(old_accessions) != len(set(old_accessions)) or any(not ACCESSION.fullmatch(item) for item in old_accessions):
            parser.error("Preserved baseline contains duplicate/unsafe accessions")
        if args.verify_new_from:
            if any(item.get("acquisition_validation") not in ("PASS", "PASS_WITH_NOTES") for item in old_results):
                parser.error("New-only verification requires every preserved baseline result to be an accepted integrity PASS")
            old_set = set(old_accessions)
            folders = sorted(path for path in (root / "raw").iterdir()
                             if path.is_dir() and ACCESSION.fullmatch(path.name)
                             and path.name not in old_set and (path / "acquisition_receipt.json").is_file())
        else:
            failed = [item["accession"] for item in old_results if item["acquisition_validation"] == "FAIL"]
            if not failed:
                parser.error("Preserved report has no failed accessions to retry")
            folders = [root / "raw" / accession for accession in failed]
    else:
        folders = sorted(path for path in (root / "raw").iterdir()
                         if path.is_dir() and ACCESSION.fullmatch(path.name) and (path / "acquisition_receipt.json").is_file())
    run_dir = root / "qc" / "verification_runs" / batch_id
    run_dir.mkdir(parents=True, exist_ok=False)
    cohort = {"schema": "tree2-verification-cohort-v1", "batch_id": batch_id,
              "selected_utc": datetime.now(timezone.utc).isoformat(), "script_sha256": script_hash,
              "mode": "NEW_ONLY" if args.verify_new_from else "FAILED_ONLY" if previous else "FULL",
              "preserved_report": prior_report_path.relative_to(root).as_posix() if prior_report_path else None,
              "preserved_report_sha256": previous_hash, "accessions_to_verify": [path.name for path in folders],
              "prior_records_not_to_reverify": len(previous["results"]) if args.verify_new_from else None,
              "selection_rule": "Snapshot of committed raw directories with receipt; no network, no synthetic verification outcomes."}
    atomic_write(run_dir / "cohort.json", json.dumps(cohort, indent=2) + "\n")
    if args.verify_new_from and not folders:
        atomic_write(run_dir / "run_receipt.json", json.dumps({"status": "NO_NEW_COMMITTED_ACCESSIONS",
                     "cohort_sha256": digest(run_dir / "cohort.json"), "canonical_report_changed": False,
                     "canonical_report_sha256": previous_hash}, indent=2) + "\n")
        print(json.dumps({"new_accessions_verified": 0, "canonical_report_changed": False,
                          "prior_accepted_retained": len(previous["results"])}))
        return 0
    fresh_results = []
    for folder in folders:
        with (run_dir / "events.jsonl").open("a", encoding="utf-8") as events:
            events.write(json.dumps({"event": "VERIFY_START", "accession": folder.name,
                                     "utc": datetime.now(timezone.utc).isoformat()}) + "\n")
        try:
            fresh_results.append(verify_one(folder))
        except Exception as error:
            fresh_results.append({"accession": folder.name, "acquisition_validation": "FAIL", "errors": [f"{type(error).__name__}: {error}"],
                                  "independent_biological_qc": "NOT_RUN", "taxonomy_sequence_validation": "NOT_RUN"})
        fresh_results[-1]["verification_batch"] = {"id": batch_id, "script_sha256": script_hash,
                                                    "verified_utc": datetime.now(timezone.utc).isoformat()}
        with (run_dir / "events.jsonl").open("a", encoding="utf-8") as events:
            events.write(json.dumps({"event": "VERIFY_END", "accession": folder.name,
                                     "utc": datetime.now(timezone.utc).isoformat(),
                                     "status": fresh_results[-1]["acquisition_validation"],
                                     "receipt_sha256": fresh_results[-1].get("receipt_sha256"),
                                     "errors": fresh_results[-1].get("errors", [])}) + "\n")
    if previous:
        replacements = {item["accession"]: item for item in fresh_results}
        if args.verify_new_from:
            if set(replacements).intersection(item["accession"] for item in previous["results"]):
                raise RuntimeError("New-only cohort overlaps prior accepted records; merge refused")
            results = previous["results"] + fresh_results
        else:
            results = [replacements.get(item["accession"], item) for item in previous["results"]]
        unchanged = [item for item in previous["results"] if item["accession"] not in replacements]
        retained = [item for item in results if item["accession"] not in replacements]
        if unchanged != retained or len({item["accession"] for item in results}) != len(results):
            raise RuntimeError("Accepted-result preservation invariant failed")
        retained_digest = hashlib.sha256(json.dumps(retained, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    else:
        results, unchanged, retained_digest = fresh_results, [], None
    columns = ["accession", "acquisition_validation", "annotation_validation", "source_md5_files_verified", "total_bp", "fasta_records", "record_n50", "ambiguous_bases", "ambiguous_fraction", "faa_records", "cds_rows", "cds_protein_coverage", "faa_cds_coverage", "errors", "notes", "receipt_sha256", "independent_biological_qc", "taxonomy_sequence_validation"]
    table = io.StringIO(newline="")
    writer = csv.DictWriter(table, fieldnames=columns, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for result in results:
        seq, ann = result.get("fna", {}), result.get("annotation_join", {})
        writer.writerow({"accession": result["accession"], "acquisition_validation": result["acquisition_validation"],
                         "annotation_validation": result.get("annotation_validation", "EVALUATED_SOURCE_JOINS" if ann else "UNAVAILABLE"),
                         "source_md5_files_verified": result.get("source_md5_files_verified"),
                         **{key: seq.get(key) for key in ("total_bp", "fasta_records", "record_n50", "ambiguous_bases", "ambiguous_fraction")},
                         "faa_records": ann.get("faa_records"), "cds_rows": ann.get("cds_rows"),
                         "cds_protein_coverage": ann.get("unique_cds_protein_reference_coverage"),
                         "faa_cds_coverage": ann.get("faa_id_coverage_by_cds"), "errors": " | ".join(result.get("errors", [])),
                         "notes": " | ".join(result.get("warnings", [])), "receipt_sha256": result.get("receipt_sha256"),
                         "independent_biological_qc": "NOT_RUN", "taxonomy_sequence_validation": "NOT_RUN"})
    tsv = root / "qc" / "acquisition_validation.tsv"
    if previous and digest(report_path) != previous_hash:
        raise RuntimeError("Current report changed during incremental verification; merge refused")
    atomic_write(tsv, table.getvalue())
    atomic_write(run_dir / "fresh_results.json", json.dumps(fresh_results, ensure_ascii=False, indent=2) + "\n")
    summary = {"schema": "tree2-independent-acquisition-validation-v2", "created_utc": datetime.now(timezone.utc).isoformat(),
               "script_sha256": script_hash,
               "scope": "Incremental new-only verification; previous accepted result objects retained exactly" if args.verify_new_from else "Incremental failed-only verification with unchanged accepted records retained" if previous else "Committed raw accession directories at verifier start; source data read-only",
               "counts": dict(Counter(result["acquisition_validation"] for result in results)), "genomes_checked": len(results),
               "genomes_verified_this_run": len(fresh_results),
               "genomes_reverified_this_run": 0 if args.verify_new_from else len(fresh_results),
               "previous_accepted_records_retained": len(unchanged),
               "source_md5_checks": sum(result.get("source_md5_files_verified", 0) for result in results),
               "independent_biological_qc": "NOT_RUN", "taxonomy_sequence_validation": "NOT_RUN",
               "limitations": ["Protein translation and biological completeness/contamination are not evaluated.",
                               "Source scaffold record statistics and contig statistics are distinct.",
                               "CDS/FAA join coverage is reported without assuming one CDS row equals one protein.",
                               "Circular origin-spanning GFF coordinates are accepted only for declared circular records and a span <= one replicon length."],
               "tsv": {"path": tsv.relative_to(root).as_posix(), "sha256": digest(tsv)}, "results": results}
    if previous:
        summary["incremental_revision"] = {
            "batch_id": batch_id, "preserved_report": prior_report_path.relative_to(root).as_posix(),
            "previous_report_sha256": previous_hash, "previous_script_sha256": previous.get("script_sha256"),
            "changed_accessions": [] if args.verify_new_from else [item["accession"] for item in fresh_results],
            "added_accessions": [item["accession"] for item in fresh_results] if args.verify_new_from else [],
            "retained_result_objects_sha256": retained_digest,
            "preservation": "All accepted result objects retained exactly; their genome checks were not rerun.",
            "reason": "Verify newly committed cohort only; prior accepted checks/results not rerun or changed; biology remains NOT_RUN." if args.verify_new_from else "Corrected mandatory-annotation schema assumption: optional source FAA/GFF absence is UNAVAILABLE, not corrupted DNA. Mandatory integrity checks rerun only for prior failures; biology remains NOT_RUN.",
            "cohort": {"path": (run_dir / "cohort.json").relative_to(root).as_posix(),
                       "sha256": digest(run_dir / "cohort.json")},
            "new_results": {"path": (run_dir / "fresh_results.json").relative_to(root).as_posix(),
                            "sha256": digest(run_dir / "fresh_results.json")}
        }
    atomic_write(root / "qc" / "acquisition_validation.json", json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    atomic_write(run_dir / "run_receipt.json", json.dumps({"schema": "tree2-verification-run-receipt-v1",
                 "batch_id": batch_id, "cohort_sha256": digest(run_dir / "cohort.json"),
                 "fresh_results_sha256": digest(run_dir / "fresh_results.json"),
                 "events_sha256": digest(run_dir / "events.jsonl"),
                 "previous_report_sha256": previous_hash, "canonical_report_sha256": digest(report_path),
                 "canonical_tsv_sha256": digest(tsv), "verified_this_run": len(fresh_results),
                 "fresh_counts": dict(Counter(item["acquisition_validation"] for item in fresh_results)),
                 "prior_records_retained_exactly": len(unchanged), "retained_result_objects_sha256": retained_digest,
                 "independent_biological_qc": "NOT_RUN", "taxonomy_sequence_validation": "NOT_RUN"}, indent=2) + "\n")
    print(json.dumps({key: summary[key] for key in ("genomes_checked", "counts", "source_md5_checks", "independent_biological_qc", "taxonomy_sequence_validation")}))
    return 1 if any(result["acquisition_validation"] == "FAIL" for result in results) or not results else 0


if __name__ == "__main__":
    raise SystemExit(main())
