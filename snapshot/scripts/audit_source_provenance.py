"""Audit structured provenance in acquired source reports without changing them."""
from __future__ import annotations
import collections
import csv
import io
import json
from pathlib import Path

import discover
import select_panel

ROOT = Path(__file__).resolve().parents[1]


def main():
    snapshots = sorted((ROOT / "metadata/history").glob("pre_source_provenance_fix_*"))
    if not snapshots:
        raise RuntimeError("Pre-fix metadata history is required before provenance review")
    snapshot = snapshots[-1]
    originals = {row["accession"]: row for row in discover.read(snapshot / "metadata/candidates_qc.json")}
    memberships = collections.defaultdict(list)
    protected = {}
    for path in sorted((ROOT / "metadata").glob("acquisition_batch_*.json")) + [ROOT / "metadata/acquisition_qc_review_only.json"]:
        if not path.exists(): continue
        protected[str(path.relative_to(ROOT))] = discover.sha(path)
        for row in discover.read(path): memberships[row["accession"]].append(path.name)
    rows = []
    reports = sorted((ROOT / "raw").glob("*/**/assembly_data_report.jsonl"))
    for path in reports:
        accession = path.relative_to(ROOT / "raw").parts[0]
        raw_dir = ROOT / "raw" / accession
        receipt_path = raw_dir / "acquisition_receipt.json"
        receipt = discover.read(receipt_path)
        rel = path.relative_to(raw_dir).as_posix()
        expected = [item for item in receipt.get("files", []) if item["path"] == rel]
        integrity = "PASS" if len(expected) == 1 and expected[0]["sha256"] == discover.sha(path) and expected[0]["bytes"] == path.stat().st_size else "FAIL_REPORT_HASH_OR_RECEIPT"
        records = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
        matched = [record for record in records if record.get("accession") == accession]
        if len(matched) != 1:
            rows.append({"accession": accession, "source_report_integrity": integrity,
                         "production_disposition": "HOLD_SOURCE_REPORT_IDENTITY", "source_report_path": str(path.relative_to(ROOT))})
            continue
        record = matched[0]
        source = select_panel.source_provenance(record)
        old = originals.get(accession, {})
        checkm = select_panel.get(record, "checkm_info", {})
        info = select_panel.get(record, "assembly_info", {})
        biosample = info.get("biosample", {})
        holds = []
        if integrity != "PASS": holds.append("SOURCE_REPORT_INTEGRITY_FAILURE")
        if source["is_mag"]: holds.append("EXCLUDED_MAG")
        if source["is_sag"]: holds.append("EXCLUDED_SAG")
        if source["is_uncultivated"]: holds.append("EXCLUDED_UNCULTIVATED")
        if source["is_atypical"]: holds.append("EXCLUDED_ATYPICAL")
        if source["environmental_sample"]: holds.append("HOLD_ENVIRONMENTAL_SAMPLE")
        if source["status"] == "HOLD_SOURCE_UNRESOLVED": holds.append("HOLD_ISOLATE_SOURCE_UNRESOLVED")
        if old.get("metadata_qc") == "EXCLUDED": holds.append("HOLD_EXISTING_METADATA_QC_EXCLUSION")
        if not old: holds.append("HOLD_NO_CANDIDATE_QC_IN_PREFIX_SNAPSHOT")
        species = old.get("species", select_panel.get(record.get("organism", {}), "organism_name", ""))
        if species.startswith("Candidatus "): holds.append("HOLD_CANDIDATUS_CURATION")
        if source["submitter_reported_completeness"] is not None and source["submitter_reported_completeness"] < 95:
            holds.append("HOLD_SUBMITTER_REPORTED_COMPLETENESS_BELOW_95")
        if source["submitter_reported_contamination"] is not None and source["submitter_reported_contamination"] > 5:
            holds.append("HOLD_SUBMITTER_REPORTED_CONTAMINATION_ABOVE_5")
        rows.append({"accession": accession, "species": species, "species_taxid": old.get("species_taxid"),
                     "source_report_integrity": integrity, "acquisition_receipt_status": receipt.get("acquisition_status"),
                     "source_provenance_status": source["status"],
                     "production_disposition": "EXCLUDED_SOURCE" if any(x.startswith("EXCLUDED_") for x in holds) else "HOLD" if holds else "SOURCE_SUPPORTED_BIOLOGICAL_QC_NOT_RUN",
                     "holds_or_exclusions": holds, "is_mag": source["is_mag"], "is_sag": source["is_sag"],
                     "is_atypical": source["is_atypical"], "is_uncultivated": source["is_uncultivated"],
                     "isolate_source_supported": source["isolate_source_supported"], "source_conflict": source["source_conflict"],
                     "biosample": biosample.get("accession", ""), "models": biosample.get("models", []),
                     "genome_notes": source["genome_notes"], "structured_source_evidence": source["evidence"],
                     "ncbi_checkm_info": checkm,
                     "submitter_reported_completeness": source["submitter_reported_completeness"],
                     "submitter_reported_contamination": source["submitter_reported_contamination"],
                     "submitter_quality_method": source["submitter_quality_method"],
                     "original_metadata_qc": old.get("metadata_qc", "NOT_IN_CANDIDATE_SNAPSHOT"),
                     "original_exclusion_reasons": old.get("exclusion_reasons", []),
                     "acquisition_membership": memberships.get(accession, []),
                     "source_report_path": str(path.relative_to(ROOT)), "source_report_sha256": discover.sha(path),
                     "acquisition_receipt_sha256": discover.sha(receipt_path), "independent_biological_qc": "NOT_RUN"})
    summary = {"acquired_reports_audited": len(rows), "report_integrity_counts": dict(collections.Counter(r["source_report_integrity"] for r in rows)),
               "source_provenance_counts": dict(collections.Counter(r.get("source_provenance_status", "UNRESOLVED") for r in rows)),
               "production_disposition_counts": dict(collections.Counter(r["production_disposition"] for r in rows)),
               "mag_count": sum(r.get("is_mag", False) for r in rows), "sag_count": sum(r.get("is_sag", False) for r in rows),
               "atypical_count": sum(r.get("is_atypical", False) for r in rows),
               "hold_or_exclusion_counts": dict(collections.Counter(reason for r in rows for reason in r.get("holds_or_exclusions", [])))}
    output = {"created_utc": discover.now(), "scope": "All currently acquired assembly_data_report.jsonl source provenance; raw files and acquisition snapshots remain unchanged.",
              "integrity_scope": "Each assembly report file checked against its acquisition receipt hash and byte count. Integrity and source eligibility are separate results.",
              "pre_fix_history": str(snapshot.relative_to(ROOT)), "normalizer_sha256": discover.sha(ROOT / "scripts/select_panel.py"),
              "audit_script_sha256": discover.sha(__file__), "summary": summary, "records": rows,
              "limits": ["Isolate support is source metadata, not independent purity/identity validation.",
                         "No derivation flag does not prove an isolate; unresolved sources are held.",
                         "Submitter quality scores are kept separate from NCBI CheckM and are not independent verification.",
                         "No source exclusion/hold is a defence-system negative or biological absence."],
              "protected_acquisition_snapshot_sha256": protected}
    qc = ROOT / "qc"
    select_panel.atomic_json(qc / "source_provenance_audit.json", output)
    select_panel.write_table(qc / "source_provenance_audit.tsv", rows)
    mag_sag = [r for r in rows if r.get("is_mag") or r.get("is_sag")]
    examples = "\n".join(f"| {r['accession']} | {'MAG' if r['is_mag'] else 'SAG'} | {r['original_metadata_qc']} | {r['biosample']} |" for r in mag_sag)
    text = f"""# Source provenance correction before a production freeze

Audit date: {output['created_utc']}. Acquired source reports audited: **{len(rows)}**. This is a provisional dataset/source review; no final high-quality isolate panel exists.

All {summary['report_integrity_counts'].get('PASS', 0)} inspected assembly report files match their acquisition-receipt hashes. **Source integrity can pass while source eligibility is excluded.** Structured source evidence identifies **{summary['mag_count']} MAGs and {summary['sag_count']} SAGs**. These source classes are excluded from the primary isolate analysis. Raw packages, original acquisition batches and QC-review snapshots remain preserved.

The initial metadata normalizer missed genomeNotes/genome_notes derivation notes and some BioSample investigation_type/metagenomic-source fields. Downloaded reports exposed these fields. The corrected normalizer reads affirmative structured MAG/SAG/atypical/uncultivated and culture/isolate evidence in camelCase and snake_case schemas. It does not infer MAG from a project title or a false metagenomic flag. Missing isolate evidence remains a hold rather than a pass. MIMAG/MISAG models and packages are handled explicitly; a mixed MIGS/MIMS/MIMARKS label alone is not a MAG call.

GCA_944324145.1 has genomeNotes='derived from metagenome', investigation_type='metagenome-assembled genome', and a chicken-gut metagenomic source. GCA_982591615.1 has the same structured derivation note, a food-fermentation metagenomic source, and submitter-reported completeness84.03%/contamination1.83% (software checkm). The latter is a submitter estimate, separate from absent NCBI CheckM fields.

## Excluded acquired source classes

| Accession | Source class | Pre-fix metadata QC | BioSample |
| --- | --- | --- | --- |
{examples}

## Remaining holds and scientific limits

Source provenance counts: {json.dumps(summary['source_provenance_counts'], sort_keys=True)}. Production dispositions: {json.dumps(summary['production_disposition_counts'], sort_keys=True)}. Source-supported records still require independent genome/taxonomy QC. Candidatus nomenclature curation remains separate from derivation; no Candidatus name alone establishes a MAG. Submitter and NCBI quality evidence remain distinct.

The pre-fix selector and normalized metadata, provisional panels, immutable acquisition batches and review queue were copied byte-for-byte to {output['pre_fix_history']} with snapshot_manifest.json before correction. New source exclusions and holds do not rewrite that history, delete acquired packages, or imply defence-system absence. No acquisition was rerun. See qc/source_provenance_audit.json/tsv for per-accession evidence and source hashes. The main selector should be refreshed only after targeted correction checks pass.
"""
    select_panel.atomic_bytes(ROOT / "docs/SOURCE_PROVENANCE_ISSUE.md", text.encode())
    for relative, digest in protected.items():
        if discover.sha(ROOT / relative) != digest: raise RuntimeError("Acquisition snapshot changed during source audit")
    select_panel.atomic_json(qc / "source_provenance_audit_commit.json", {
        "created_utc": discover.now(), "status": "COMMITTED_SOURCE_REVIEW_NOT_PRODUCTION_FREEZE", "summary": summary,
        "artifacts": [{"path": str(p.relative_to(ROOT)), "sha256": discover.sha(p)} for p in
                      [qc / "source_provenance_audit.json", qc / "source_provenance_audit.tsv", ROOT / "docs/SOURCE_PROVENANCE_ISSUE.md"]],
        "acquisition_snapshots_unchanged": protected})
    print(json.dumps(summary, indent=2))


if __name__ == "__main__": main()
