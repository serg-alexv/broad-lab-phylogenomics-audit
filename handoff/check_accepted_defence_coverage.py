"""Check all accepted defence phase artifacts against the committed audit inventory."""

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import PurePosixPath
import re
import time

from check_coverage import (
    BUNDLE, PROJECT, LEDGER, EXPLICIT_ARTIFACT_OMISSIONS, MAX_EXAMPLES, MAX_TARGETS,
    Target, forbidden_reason, ndjson, path_key, pinned, project_relative, read_json, require,
)


ALLOWED_OMISSIONS = EXPLICIT_ARTIFACT_OMISSIONS | {
    "installed_runtime_tool_cache_or_unselected_database_payload",
    "ephemeral_scientific_runtime_directory",
}
ENGINE_NAMES = {"PADLOC": "PADLOC2_DB2", "DefenseFinder": "DefenseFinder3_models3.1_Cas3.1"}


def read_safe_reference(ref):
    path = project_relative(ref["path"])
    require(forbidden_reason(path) is None, f"Forbidden provenance reference: {path}")
    return pinned(ref)


def acceptance_packets():
    ledger = read_json(PROJECT / LEDGER)
    by_cohort = defaultdict(set)
    refs = {}
    for accession, row in ledger["entries"].items():
        if row["state"] != "CLOSED_PAIRED_PROTEIN_SCOPE_ACCEPTED":
            continue
        cohort = row.get("cohort_id") or "PILOT"
        by_cohort[cohort].add(accession)
        require(refs.setdefault(cohort, row["acceptance"]) == row["acceptance"],
                f"Conflicting acceptance references in {cohort}")
    require(len(ledger["entries"]) == 919 and ledger["closed_paired_protein_scope_genomes"] == 165,
            "This handoff checkpoint expects 165 of 919 accepted genomes")
    expected = {"PILOT": 5} | {f"C{index:03d}": 20 for index in range(1, 9)}
    require({key: len(value) for key, value in by_cohort.items()} == expected,
            "Accepted cohorts differ from the preserved handoff checkpoint")
    for cohort in expected:
        yield cohort, refs[cohort], by_cohort[cohort]


class CohortCoverage:
    def __init__(self, cohort):
        self.cohort = cohort
        self.targets = {}
        self.splits = set()
        self.engine_refs = []
        self.reference_count = Counter()
        self.phase_count = Counter()
        self.errors = Counter()
        self.error_examples = []

    def error(self, reason, path):
        self.errors[reason] += 1
        if len(self.error_examples) < MAX_EXAMPLES:
            self.error_examples.append({"path": path, "reason": reason})

    def add(self, ref, *, artifact=False):
        relative = project_relative(ref["path"])
        path = relative.as_posix()
        size = ref["bytes"]
        require(type(size) is int and size >= 0 and re.fullmatch(r"[0-9a-f]{64}", ref["sha256"]),
                f"Malformed saved reference: {path}")
        if not artifact:
            require(forbidden_reason(relative) is None, f"Forbidden required provenance reference: {path}")
        key = path_key(path)
        prior = self.targets.get(key)
        if prior is not None:
            require(prior.size == size, f"Inconsistent artifact size in {self.cohort}: {path}")
            if not artifact:
                prior.policy_sensitive = False
                prior.path = path
            return
        require(len(self.targets) < MAX_TARGETS, f"Cohort exceeds bounded target index: {self.cohort}")
        category = "phase_artifact" if artifact else "essential_provenance"
        self.targets[key] = Target(category, size, artifact, None if artifact else path)
        if len(relative.parts) > 2 and relative.parts[0] in {"analysis", "recovery"}:
            self.splits.add(re.sub(r"[^a-zA-Z0-9_-]", "_", relative.parts[1]))

    def load(self, acceptance_ref, accessions):
        self.add(acceptance_ref)
        acceptance = read_safe_reference(acceptance_ref)
        require(acceptance["genomes"] == len(accessions), "Accepted cohort denominator differs")
        self.add(acceptance["source_result"])
        self.add(acceptance["source_plan"])
        for name in ("QA_commit", "verified_files_and_births", "validated_rows", "QA_native_actual_exit",
                     "science_whole_closure", "independent_file_validation", "validation_actual_exit"):
            if name in acceptance:
                self.add(acceptance[name])
        result = read_safe_reference(acceptance["source_result"])
        selected = result["selected_accessions"]
        require(len(selected) == len(accessions) and set(selected) == accessions, "Accepted cohort accession join differs")
        genome_refs = result["genome_commits"]
        require(len(genome_refs) == len(accessions), "Paired genome commit count differs")
        phases = {}
        for accession, genome_ref in zip(selected, genome_refs):
            self.add(genome_ref)
            genome = read_safe_reference(genome_ref)
            require(genome["accession"] == accession and set(genome["engines"]) == set(ENGINE_NAMES),
                    f"Paired genome evidence differs: {accession}")
            self.add(genome["input_provenance"])
            for ref in read_safe_reference(genome["input_provenance"])["files"].values():
                self.add(ref)
            for engine, phase_ref in genome["engines"].items():
                require(phase_ref["path"] not in phases, f"Reused engine phase reference in {self.cohort}")
                phases[phase_ref["path"]] = phase_ref
                self.engine_refs.append(phase_ref)
                self.add(phase_ref)
                phase = read_safe_reference(phase_ref)
                require(phase["accession"] == accession and phase["engine"] == ENGINE_NAMES[engine],
                        f"Engine phase identity differs: {accession} {engine}")
                self.phase_count[engine] += 1
                self.reference_count[engine] += len(phase["artifacts"])
                for name in ("execution", "calls", "cache_provenance", "model_cache_provenance", "runtime_cache_provenance"):
                    if name in phase:
                        self.add(phase[name])
                for ref in phase["artifacts"]:
                    self.add(ref, artifact=True)
        flat = result["engine_phase_commits"]
        require(len(flat) == len(phases) == 2 * len(accessions) and {ref["path"]: ref for ref in flat} == phases,
                f"Flat engine manifest does not match genome commits for {self.cohort}")

    def scan(self, spool, groups):
        selected = []
        for group in groups:
            require(re.fullmatch(r"[A-Za-z0-9_-]+", group), f"Malformed inventory group: {group}")
            _, separator, suffix = group.partition("--")
            if separator and suffix not in self.splits:
                continue
            selected.append(group)
            count = 0
            byte_count = 0
            for row in ndjson(spool / (group + ".ndjson")):
                path = project_relative(row["path"])
                count += 1
                require(type(row["bytes"]) is int and row["bytes"] >= 0, f"Invalid inventory byte count: {path}")
                byte_count += row["bytes"]
                target = self.targets.get(path_key(row["path"]))
                if target is None:
                    continue
                reason = forbidden_reason(path)
                if reason is not None:
                    self.error(reason, row["path"])
                target.hits += 1
                if target.hits != 1:
                    self.error("duplicate_included_reference", row["path"])
                if target.size != row["bytes"]:
                    self.error("bound_size_differs", row["path"])
            require(count == groups[group]["members"] and byte_count == groups[group]["unpacked_bytes"],
                    f"Committed inventory counters differ in {group}")
        return selected

    def note_omissions(self, spool):
        if all(target.hits for target in self.targets.values()):
            return
        parents = {}
        for row in ndjson(spool / "omissions.ndjson"):
            relative = project_relative(row["path"])
            if row["type"] == "directory":
                require(len(parents) < 100_000, "Directory omissions exceed bounded index")
                parents[relative.as_posix()] = row["reason"]
            target = self.targets.get(path_key(row["path"]))
            if target is not None:
                if target.hits:
                    self.error("included_and_omitted", row["path"])
                target.reason = row["reason"]
        for phase_ref in self.engine_refs:
            for ref in read_safe_reference(phase_ref)["artifacts"]:
                target = self.targets[path_key(ref["path"])]
                if not target.hits and target.path is None:
                    target.path = ref["path"]
        for target in self.targets.values():
            if not target.hits and target.reason is None and target.path is not None:
                for parent in PurePosixPath(target.path).parents:
                    reason = parents.get(parent.as_posix())
                    if reason is not None:
                        target.reason = reason
                        break

    def summarize(self):
        omitted = Counter()
        counts = Counter()
        omission_examples = []
        for target in self.targets.values():
            if target.hits:
                counts["included"] += 1
                continue
            if target.policy_sensitive and target.reason in ALLOWED_OMISSIONS:
                counts["documented_omissions"] += 1
                omitted[target.reason] += 1
                if len(omission_examples) < MAX_EXAMPLES:
                    omission_examples.append({"path": target.path, "reason": target.reason})
            else:
                counts["missing_required"] += 1
                self.error("missing_required_reference", target.path)
        require(sum(counts.values()) == len(self.targets), "Coverage counts do not balance")
        return {
            "engine_phase_counts": dict(self.phase_count),
            "declared_phase_artifact_references_by_engine": dict(self.reference_count),
            "unique_required_and_policy_sensitive_paths": len(self.targets),
            "unique_paths_included": counts["included"],
            "unique_paths_documented_omitted": counts["documented_omissions"],
            "unique_paths_missing_required": counts["missing_required"],
            "documented_omissions_by_reason": dict(omitted),
            "documented_omission_examples": omission_examples,
            "errors_by_reason": dict(self.errors),
            "error_examples": self.error_examples,
        }


def check():
    inventory_path = BUNDLE / "inventory/COMMITTED.json"
    inventory = read_json(inventory_path)
    spool = (BUNDLE / project_relative(inventory["spool"])).resolve()
    require(spool.is_dir() and spool.is_relative_to(BUNDLE / "inventory"), "Invalid inventory spool location")
    totals = Counter()
    cohorts = {}
    for cohort, acceptance_ref, accessions in acceptance_packets():
        started = time.monotonic()
        audit = CohortCoverage(cohort)
        audit.load(acceptance_ref, accessions)
        groups = audit.scan(spool, inventory["groups"])
        audit.note_omissions(spool)
        row = audit.summarize()
        row.update(accepted_genomes=len(accessions), acceptance=acceptance_ref, inventory_groups_scanned=groups,
                   elapsed_seconds=round(time.monotonic() - started, 3))
        cohorts[cohort] = row
        totals["genomes"] += len(accessions)
        totals["engine_phases"] += sum(row["engine_phase_counts"].values())
        totals["declared_phase_artifact_references"] += sum(row["declared_phase_artifact_references_by_engine"].values())
        for field in ("unique_paths_included", "unique_paths_documented_omitted", "unique_paths_missing_required"):
            totals["sum_of_cohort_" + field] += row[field]
        print(f"{cohort}: {row['unique_paths_included']:,} included, {row['unique_paths_documented_omitted']:,} omitted, "
              f"{row['unique_paths_missing_required']:,} missing ({row['elapsed_seconds']:.1f} s)", flush=True)
        del audit
    require(totals["genomes"] == 165 and totals["engine_phases"] == 330, "Accepted totals differ")
    passed = all(not row["errors_by_reason"] for row in cohorts.values())
    return {
        "status": "PASS_ACCEPTED_DEFENCE_RAW_COVERAGE" if passed else "FAIL_ACCEPTED_DEFENCE_RAW_COVERAGE",
        "inventory_sha256": hashlib.sha256(inventory_path.read_bytes()).hexdigest(),
        "inventory_spool": inventory["spool"], "totals": dict(totals), "cohorts": cohorts,
        "omission_examples_limit_per_cohort": MAX_EXAMPLES,
        "verification_scope": "Membership and bound sizes of accepted phase artifacts. Per-file archive hashes are verified separately.",
    }


def main():
    started = time.monotonic()
    try:
        report = check()
    except (OSError, ValueError, KeyError, TypeError) as error:
        report = {"status": "FAIL_ACCEPTED_DEFENCE_INPUT_OR_STRUCTURE", "error": str(error)}
    report["checked_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["elapsed_seconds"] = round(time.monotonic() - started, 3)
    path = BUNDLE / "accepted_defence_coverage_report.json"
    temporary = path.with_suffix(".json.partial")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    print(f"{report['status']} {path}")
    return 0 if report["status"] == "PASS_ACCEPTED_DEFENCE_RAW_COVERAGE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
