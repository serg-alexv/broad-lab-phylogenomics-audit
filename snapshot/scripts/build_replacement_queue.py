"""One bounded, immutable replacement round after a full acquisition terminates.

Replacements restore opportunities for species coverage, never QC acceptance.
No acquisition is launched and no existing production panel is changed.
"""
from __future__ import annotations
import argparse
import collections
import contextlib
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

import acquire
import discover
import select_panel

ROOT = Path(__file__).resolve().parents[1]


@contextlib.contextmanager
def os_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = path.open("a+b")
    try:
        stream.seek(0); stream.write(b"0"); stream.flush(); stream.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        stream.close()


def publish_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".part", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False); stream.write("\n")
            stream.flush(); os.fsync(stream.fileno())
        try:
            os.link(temp, path)
        except FileExistsError:
            if discover.read(path) != value:
                raise RuntimeError("Immutable replacement artifact already differs: " + str(path))
    finally:
        os.unlink(temp)


def check_terminal(terminal, original, original_sha):
    if terminal.get("status") not in {"COMPLETE", "PARTIAL_FAILURE"}:
        raise ValueError("A fully finished COMPLETE/PARTIAL_FAILURE receipt is required")
    if not terminal.get("ended_utc") or terminal.get("process_lock_released") is not True:
        raise ValueError("Terminal receipt does not establish graceful lock release")
    if terminal.get("panel_sha256") != original_sha:
        raise ValueError("Terminal panel SHA256 differs from immutable original panel")
    results = terminal.get("results", [])
    if terminal.get("selected_count") != len(original) or len(results) != len(original):
        raise ValueError("Receipt is not a completed full original-panel attempt")
    accessions = [row["accession"] for row in original]
    if len(set(accessions)) != len(accessions) or {row.get("accession") for row in results} != set(accessions):
        raise ValueError("Original panel/result accession sets do not agree")
    has_failure = any(row.get("action") == "FAILED" for row in results)
    if (terminal["status"] == "PARTIAL_FAILURE") != has_failure:
        raise ValueError("Terminal status and per-accession failure results disagree")
    if any(row.get("replacement_round") or row.get("selection_status") == "REPLACEMENT_NOT_PRODUCTION_ACCEPTED" for row in original):
        raise ValueError("A replacement panel cannot generate another replacement round")


def eligible(row):
    if row.get("metadata_qc") not in {"QC_METADATA_PASS", "QC_PENDING"} or row.get("exclusion_reasons"):
        return False
    if row.get("order_taxid") != 186826 or not row.get("species_taxid") or not row.get("genus_taxid") or not row.get("family_taxid"):
        return False
    if row.get("assembly_status", "").lower() != "current":
        return False
    # Recheck known numeric limits rather than trusting a stale label. Missing
    # values may remain pending for acquisition; they never become a QC pass.
    limits = [("length_bp", lambda n: 500_000 <= n <= 10_000_000),
              ("contigs", lambda n: 0 < n <= 200), ("n50", lambda n: n >= 20_000),
              ("ncbi_checkm_completeness", lambda n: n >= 95),
              ("ncbi_checkm_contamination", lambda n: n <= 5)]
    for key, test in limits:
        value = row.get(key)
        if value is not None and not test(value):
            return False
    return True


def rank(row):
    return (row.get("metadata_qc") != "QC_METADATA_PASS",
            {"Complete Genome": 0, "Chromosome": 1, "Scaffold": 2, "Contig": 3}.get(row.get("assembly_level"), 4),
            not row.get("reference"), not row.get("type_material"),
            -(row.get("ncbi_checkm_completeness") or -1),
            row.get("ncbi_checkm_contamination") if row.get("ncbi_checkm_contamination") is not None else 100,
            row.get("contigs") or 10**9, -(row.get("n50") or 0), row["accession"])


def select_round(original, candidates, terminal, rejected, valid_raw):
    original_map = {row["accession"]: row for row in original}
    candidate_map = {row["accession"]: row for row in candidates}
    lookup = {**candidate_map, **original_map}
    failed = {row["accession"] for row in terminal["results"] if row.get("action") == "FAILED"}
    blocked = set(rejected) | failed
    biosamples = {row.get("biosample") for row in original if row.get("biosample")}
    biosamples.update(lookup[a].get("biosample") for a in valid_raw if a in lookup and lookup[a].get("biosample"))
    covered = {lookup[a].get("species_taxid") for a in valid_raw if a in lookup and eligible(lookup[a])}
    affected = collections.defaultdict(list)
    for accession in sorted(failed):
        row = original_map[accession]
        affected[row.get("species_taxid")].append(row)
    queue, decisions = [], []
    for sid, failed_rows in sorted(affected.items(), key=lambda item: item[0] or 0):
        name = failed_rows[0].get("species", "")
        decision = {"species_taxid": sid, "species": name,
                    "failed_original_accessions": [r["accession"] for r in failed_rows]}
        if not sid:
            decisions.append({**decision, "status": "UNRESOLVED_ORIGINAL_SPECIES"}); continue
        if sid in covered:
            decisions.append({**decision, "status": "ALREADY_ACQUIRED_OTHER_ACCESSION",
                              "coverage_limit": "Acquisition validity only; biological QC remains NOT_RUN"}); continue
        choices = [row for row in candidates if row.get("species_taxid") == sid and eligible(row)
                   and row["accession"] not in blocked and row["accession"] not in valid_raw
                   and row["accession"] not in original_map
                   and row.get("biosample") and row["biosample"] not in biosamples]
        if not choices:
            decisions.append({**decision, "status": "UNRESOLVED_NO_ELIGIBLE_ALTERNATE_IN_CORPUS",
                              "note": "A source-screening result, not evidence that no suitable genome exists."}); continue
        chosen = dict(min(choices, key=rank))
        biosamples.add(chosen["biosample"])
        chosen.update({"selection_status": "REPLACEMENT_NOT_PRODUCTION_ACCEPTED", "replacement_round": 1,
                       "replacement_for_accessions": decision["failed_original_accessions"],
                       "independent_biological_qc": "NOT_RUN", "production_accepted": False,
                       "sequence_qc": "NOT_RUN", "selection_index": len(queue) + 1,
                       "replacement_note": "One bounded alternate; original rejection evidence is preserved; no thresholds relaxed."})
        queue.append(chosen)
        decisions.append({**decision, "status": "REPLACEMENT_QUEUED", "replacement_accession": chosen["accession"]})
    return queue, decisions


def inventory(root):
    rejected, evidence, valid, invalid = set(), [], set(), []
    for path in sorted((root / "work/rejected").glob("**/rejection_receipt.json")):
        receipt = discover.read(path)
        if receipt.get("accession"):
            rejected.add(receipt["accession"])
        evidence.append({"path": str(path.relative_to(root)), "sha256": discover.sha(path)})
    for path in sorted((root / "raw").glob("*/acquisition_receipt.json")):
        accession = path.parent.name
        if acquire.verified_receipt(path.parent, accession):
            valid.add(accession)
        else:
            invalid.append({"accession": accession, "receipt_path": str(path.relative_to(root))})
    return rejected, evidence, valid, invalid


def fallback_metadata(root, key, decision, taxonomy):
    sid = decision["species_taxid"]
    base = f"metadata/replacement_discovery/{key}/species_{sid}"
    params = {**discover.COMMON, **discover.QUALITY}
    path = f"genome/taxon/{sid}/dataset_report"
    probe = discover.get(path, {**params, "page_size": 1, "returned_content": "ASSM_ACC"}, base + "/probe.json")
    count = int(probe.get("total_count", len(probe.get("reports", []))))
    if count > 5000:
        return [], {**decision, "fallback_status": "UNRESOLVED_ABOVE_5000_REPORT_BUDGET", "reported_total": count}
    records, seen, pages, token, page = [], set(), [], "", 0
    while True:
        target = base + f"/page_{page:04d}.json"
        data = discover.get(path, {**params, **({"page_token": token} if token else {})}, target)
        if int(data.get("total_count", len(data.get("reports", [])))) != count:
            raise RuntimeError("Fallback source count changed between probe/pages")
        for record in data.get("reports", []):
            if record["accession"] in seen:
                raise RuntimeError("Fallback pagination repeated an accession")
            seen.add(record["accession"]); records.append(record)
        pages.append(target)
        token = data.get("next_page_token", "")
        if not token:
            break
        page += 1
    if len(records) != count:
        raise RuntimeError("Fallback metadata pagination count mismatch")
    missing = sorted({int(record["organism"]["tax_id"]) for record in records
                      if str(record["organism"]["tax_id"]) not in taxonomy})
    for index in range(0, len(missing), 100):
        batch = missing[index:index + 100]
        data = discover.get("taxonomy/taxon/" + ",".join(map(str, batch)) + "/dataset_report",
                            {"page_size": 1000}, base + f"/taxonomy_{index:05d}.json")
        for report in data.get("reports", []):
            if "taxonomy" not in report:
                continue
            tax = report["taxonomy"]; taxonomy[str(tax["tax_id"])] = tax
            for alias in report.get("query", []):
                if str(alias).isdigit(): taxonomy[str(alias)] = tax
    normalized = [select_panel.normalize(record, taxonomy, pages) for record in records]
    normalized_path = root / base / "normalized_qc.json"
    select_panel.atomic_json(normalized_path, normalized)
    return normalized, {**decision, "fallback_status": "METADATA_RETRIEVED_AND_NORMALIZED",
                        "reported_total": count, "records": len(records), "pages": pages,
                        "normalized_path": str(normalized_path.relative_to(root)), "normalized_sha256": discover.sha(normalized_path),
                        "metadata_qc_counts": dict(collections.Counter(row["metadata_qc"] for row in normalized)),
                        "exclusion_reasons": dict(collections.Counter(reason for row in normalized for reason in row["exclusion_reasons"])),
                        "pending_reasons": dict(collections.Counter(reason for row in normalized for reason in row["pending_reasons"])),
                        "source_outcome_limit": "Current filtered source reports only; missing or rejected entries are not biological absence."}


def build(root, terminal_path, original_path, candidates_path, allow_fallback=True):
    root = root.resolve()
    if root != ROOT:
        raise ValueError("Production replacement root must match this isolated Tree2 workspace")
    original_sha = discover.sha(original_path)
    terminal = discover.read(terminal_path); original = discover.read(original_path)
    check_terminal(terminal, original, original_sha)
    key = original_sha[:16]
    state_path = root / f"state/replacement_round_{key}.json"
    if state_path.exists():
        done = discover.read(state_path)
        if done.get("terminal_sha256") != discover.sha(terminal_path):
            raise RuntimeError("A replacement round already exists for a different terminal receipt")
        if done.get("status") == "COMMITTED":
            for artifact in done["artifacts"]:
                if discover.sha(root / artifact["path"]) != artifact["sha256"]:
                    raise RuntimeError("Committed replacement artifact hash mismatch")
            return done
    with os_lock(root / "state/replacements.lock"), os_lock(root / "state/acquire.lock"), os_lock(root / "state/discovery.lock"):
        inputs = {"terminal_sha256": discover.sha(terminal_path), "original_panel_sha256": original_sha,
                  "candidates_sha256": discover.sha(candidates_path),
                  "taxonomy_sha256": discover.sha(root / "metadata/taxonomy_map.json"), "script_sha256": discover.sha(__file__),
                  "metadata_fallback_enabled": allow_fallback}
        plan_path = root / f"state/replacement_round_{key}.plan.json"
        if plan_path.exists():
            plan = discover.read(plan_path)
            if plan.get("inputs") != inputs:
                raise RuntimeError("Replacement-round inputs changed after its immutable plan")
        else:
            plan = {"inputs": inputs, "created_utc": discover.now()}
            publish_new(plan_path, plan)
        candidates = discover.read(candidates_path)
        rejected, rejection_evidence, valid_raw, invalid_raw = inventory(root)
        queue, decisions = select_round(original, candidates, terminal, rejected, valid_raw)
        fallbacks, new_rows = [], []
        if allow_fallback:
            taxonomy = select_panel.load_taxonomy(root / "metadata/taxonomy_map.json")
            for decision in decisions:
                if decision["status"] != "UNRESOLVED_NO_ELIGIBLE_ALTERNATE_IN_CORPUS": continue
                try:
                    added, receipt = fallback_metadata(root, key, decision, taxonomy)
                    new_rows.extend(added); fallbacks.append(receipt)
                except Exception as error:
                    fallbacks.append({**decision, "fallback_status": "UNRESOLVED_METADATA_OR_TAXONOMY_REQUEST",
                                      "error": repr(error), "note": "No incomplete fallback records admitted."})
            if new_rows:
                merged = {row["accession"]: row for row in candidates}
                # Existing normalized QC decisions take precedence for known accessions.
                for row in new_rows: merged.setdefault(row["accession"], row)
                queue, decisions = select_round(original, list(merged.values()), terminal, rejected, valid_raw)
        ended = dt.datetime.fromisoformat(terminal["ended_utc"].replace("Z", "+00:00"))
        stamp = ended.astimezone(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + key[:8]
        queue_path = root / f"metadata/acquisition_replacements_{stamp}.json"
        audit_path = root / f"metadata/acquisition_replacements_{stamp}_audit.json"
        audit = {"created_utc": plan["created_utc"], "round": 1, "maximum_replacement_rounds": 1,
                 "terminal_path": str(terminal_path), "original_panel_path": str(original_path), **inputs,
                 "failed_accessions": [row["accession"] for row in terminal["results"] if row.get("action") == "FAILED"],
                 "replacement_count": len(queue), "decisions": decisions, "fallback_metadata": fallbacks,
                 "rejection_evidence": rejection_evidence, "invalid_raw_receipts_not_counted_as_coverage": invalid_raw,
                 "known_rejected_accessions": sorted(rejected), "verified_raw_accessions_count": len(valid_raw),
                 "thresholds_unchanged": {"maximum_sequence_ambiguous_fraction": 0.01,
                                          "minimum_known_checkm_completeness": 95, "maximum_known_checkm_contamination": 5},
                 "ranking": ["metadata_pass", "closed_assembly", "reference", "type_material", "quality_statistics", "accession"],
                 "biosample_policy": "Do not reuse any original-panel or verified-raw BioSample; one alternate per uncovered affected species.",
                 "independent_biological_qc": "NOT_RUN", "production_accepted": False,
                 "acquisition_launched": False, "no_eligible_alternate_is_not_biological_absence": True,
                 "script_sha256": discover.sha(__file__)}
        publish_new(queue_path, queue); publish_new(audit_path, audit)
        artifacts = [{"path": str(path.relative_to(root)), "sha256": discover.sha(path)} for path in [queue_path, audit_path]]
        result = {"status": "COMMITTED", "terminal_sha256": inputs["terminal_sha256"], "replacement_count": len(queue),
                  "queue_path": str(queue_path), "audit_path": str(audit_path), "artifacts": artifacts,
                  "bounded_round": 1, "acquisition_launched": False}
        publish_new(state_path, result)
        return result


def self_test():
    def row(acc, sid, bio, level="Contig", qc="QC_METADATA_PASS", **kw):
        return {"accession": acc, "species_taxid": sid, "species": "Fixture species" + str(sid), "biosample": bio,
                "order_taxid": 186826, "genus_taxid": 1, "family_taxid": 1, "assembly_status": "current",
                "metadata_qc": qc, "exclusion_reasons": [], "assembly_level": level,
                "ncbi_checkm_completeness": 98, "ncbi_checkm_contamination": 1,
                "length_bp": 2_000_000, "contigs": 10, "n50": 200_000, **kw}
    original = [row("failed1", 1, "original1"), row("failed2", 2, "original2"), row("covered2", 2, "other2"), row("failed3", 3, "original3")]
    terminal = {"status": "PARTIAL_FAILURE", "ended_utc": "2026-10-26T16:00:00+00:00", "process_lock_released": True,
                "panel_sha256": "fixture", "selected_count": 4,
                "results": [{"accession": r["accession"], "action": "ACQUIRED" if r["accession"] == "covered2" else "FAILED"} for r in original]}
    check_terminal(terminal, original, "fixture")
    candidates = [row("draft", 1, "newdraft"), row("closed", 1, "newclosed", "Complete Genome"),
                  row("rejected", 1, "newrejected", "Complete Genome"), row("samebio", 1, "original1", "Complete Genome"),
                  row("bad95", 1, "bad95", "Complete Genome", ncbi_checkm_completeness=94), row("alternate2", 2, "new2")]
    queue, decisions = select_round(original, candidates, terminal, {"rejected"}, {"covered2"})
    assert [r["accession"] for r in queue] == ["closed"]
    assert {d["status"] for d in decisions} == {"REPLACEMENT_QUEUED", "ALREADY_ACQUIRED_OTHER_ACCESSION", "UNRESOLVED_NO_ELIGIBLE_ALTERNATE_IN_CORPUS"}
    assert queue[0]["independent_biological_qc"] == "NOT_RUN" and queue[0]["production_accepted"] is False
    for mutation in [{**terminal, "status": "STOPPED"}, {**terminal, "panel_sha256": "wrong"}]:
        try: check_terminal(mutation, original, "fixture")
        except ValueError: pass
        else: raise AssertionError("Invalid terminal receipt admitted")
    try: check_terminal({**terminal, "selected_count": 1}, original, "fixture")
    except ValueError: pass
    else: raise AssertionError("Partial run admitted")
    result = {"status": "PASS", "fixture_only": True, "created_utc": discover.now(),
              "checks": ["terminal hash/full-count/status gates", "covered species skipped", "best closed alternate selected",
                         "rejected/failed/original Biosamples excluded", "95 percent gate preserved", "unresolved species explicit", "no production acceptance"],
              "script_sha256": discover.sha(__file__)}
    select_panel.atomic_json(ROOT / "checkpoints/replacement_builder_selftest.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--terminal", type=Path)
    parser.add_argument("--original-panel", type=Path)
    parser.add_argument("--candidates", type=Path, default=ROOT / "metadata/candidates_qc.json")
    parser.add_argument("--no-metadata-fallback", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test()))
    else:
        if not args.terminal or not args.original_panel:
            parser.error("--terminal and --original-panel are required")
        print(json.dumps({"kind": "replacement_build_start", "at_utc": discover.now()}), flush=True)
        print(json.dumps(build(args.root, args.terminal.resolve(), args.original_panel.resolve(), args.candidates.resolve(), not args.no_metadata_fallback)))
