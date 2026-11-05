"""Check the committed inventory against independent Tree 2 scientific references."""

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re


BUNDLE = Path(__file__).resolve().parent
PROJECT = BUNDLE.parents[1]
MAX_TARGETS = 250_000
MAX_JSON_BYTES = 20 * 1024**2
MAX_EXAMPLES = 60
MATRIX = "analysis/phylogeny/full900_conservative54_v001"
TREE = "analysis/phylogeny/full900_production_v001"
C009 = "analysis/defence_bulk_C009_v003"
LEDGER = "state/defence_campaign_v001/ledger.json"
QUEUE = "metadata/defence_preparation_queue_20261029/input_queue.json"
PANEL = "metadata/panel_critical_path_review_20261029"
ACCESSION = re.compile(r"GC[AF]_\d+\.\d+")
PRIVATE_DIRS = {
    ".git", ".codex", ".ssh", ".aws", ".gnupg", ".cache", "credentials",
    "codex_home", "codex_sqlite_home", "cli_home", "__pycache__",
}
PRIVATE_NAMES = {
    "auth.json", "credentials.json", "credential.json", "config.auth.json",
    ".env", ".netrc", ".npmrc", "id_rsa", "id_ed25519",
    "cli_session.json", "cli_session_seed.json", "session.sqlite", "cookies.sqlite",
}
DNA_SUFFIXES = {
    ".fna", ".ffn", ".frn", ".fsa_nt", ".gbff", ".gbk", ".gb", ".genbank",
    ".dna", ".nt", ".2bit", ".fastq", ".fq", ".ab1", ".bam", ".cram", ".sra",
}
KEY_SUFFIXES = {".key", ".pem", ".pfx", ".p12", ".kdbx"}
EXPLICIT_ARTIFACT_OMISSIONS = {
    "nucleotide_genome_or_coding_sequence_payload", "nucleotide_or_ambiguous_fasta_payload",
    "gff_embedded_fasta_payload", "long_nucleotide_payload", "wrapped_nucleotide_payload",
    "nucleotide_alignment_payload", "opaque_binary_or_installed_runtime_payload",
    "binary_or_opaque_text_payload", "archive_or_database_disguised_as_text",
    "uninspected_archive_or_compressed_payload", "opaque_database_or_runtime_store",
    "link_not_dereferenced", "link_or_nonregular_file", "transient_lock_or_temporary_file",
}
ANCHORS = {
    "methods": ("docs/STAGE_PLAN.md", "docs/DECISION_LOG.md", "docs/THIRD_PARTY_TOOL_NOTICES.md"),
    "source_provenance": (
        "metadata/selection_summary.json", "metadata/provisional_panel.tsv",
        "qc/source_provenance_audit.json", "qc/source_provenance_audit.tsv",
        "metadata/acquisition_gap9_reconciliation_v001.json",
        "analysis/sequence_qc/d64e016face251f1/commit.json",
    ),
    "biological_qc": (
        "metadata/checkm1_accepted_method_results_v001.json", "qc/checkm1_lactobacillales_all919_v001.tsv",
        "state/checkm1_method_review_holds_v001.json",
        "work/checkm1_close_7bbd/Root_closed_method_acceptance.json",
        "work/checkm1_close_7bbd/independent919_measurements.json",
    ),
    "markers_and_panel": (
        "analysis/marker_discovery/full919_screen_v001/result.json",
        "analysis/marker_discovery/full919_alignment_v001/result.json",
        "analysis/marker_discovery/full919_gene_assessment_v001/result.json",
        PANEL + "/cohort_accessions_v001.txt", PANEL + "/cohort_manifest_v001.json",
        PANEL + "/held19_manifest_v001.json", PANEL + "/species_rescue_candidates_v001.json",
    ),
    "defence_ledger": (
        LEDGER, QUEUE, "state/defence_campaign_v001/current.json",
        "state/defence_campaign_v001/closed_transactions/C008.json",
        "state/defence_campaign_v001/failed_transactions/C008.json",
        "metadata/defence_C008_recovery_20261105/inherited_PADLOC_phases.json",
    ),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def project_relative(value):
    require(isinstance(value, str) and value and not any(c in value for c in ("\\", ":", "\0")), "Unsafe inventory path")
    path = PurePosixPath(value)
    require(bool(path.parts) and not path.is_absolute() and ".." not in path.parts and path.as_posix() == value,
            f"Unsafe relative path {value!r}")
    return path


def path_key(path):
    return hashlib.sha256(path.encode("utf-8")).digest()


def read_json(path, expected=None):
    require(path.is_file() and not path.is_symlink(), f"Missing or linked JSON evidence {path}")
    require(path.stat().st_size <= MAX_JSON_BYTES, f"JSON exceeds bounded reader: {path}")
    payload = path.read_bytes()
    if expected is not None:
        require(len(payload) == expected["bytes"] and hashlib.sha256(payload).hexdigest() == expected["sha256"],
                f"Scientific reference has changed: {expected['path']}")
    return json.loads(payload)


def pinned(ref):
    path = PROJECT / project_relative(ref["path"])
    require(path.resolve().is_relative_to(PROJECT), f"Scientific reference leaves project: {ref['path']}")
    return read_json(path, ref)


def ndjson(path):
    require(path.is_file() and not path.is_symlink(), f"Missing or linked inventory spool {path}")
    with path.open("rb") as stream:
        for line_number, line in enumerate(stream, 1):
            require(len(line) <= 1024**2, f"Excessive inventory row at {path}:{line_number}")
            row = json.loads(line)
            require(isinstance(row, dict), f"Malformed inventory row at {path}:{line_number}")
            yield row


def forbidden_reason(relative):
    parts = tuple(part.casefold() for part in relative.parts)
    name = parts[-1]
    if PRIVATE_DIRS.intersection(parts) or parts[:2] == ("work", "local_continuation"):
        return "private_path"
    if name in PRIVATE_NAMES or "private_invocation" in name or relative.suffix.casefold() in KEY_SUFFIXES:
        return "private_file"
    if "events" in parts and name in {"stdout.jsonl", "stderr.txt", "last-message.txt", "prompt.txt", "session.jsonl"}:
        return "private_conversation_payload"
    if DNA_SUFFIXES.intersection(s.casefold() for s in relative.suffixes):
        return "nucleotide_suffix"
    if "packages" in parts and re.fullmatch(r"gc[af]_\d+\.\d+\.zip", name):
        return "ncbi_genome_package"
    if name == "padloc2_biocontainer_environment_layer.tar.gz":
        return "runtime_archive_with_verified_genome_member"
    return None


@dataclass(slots=True)
class Target:
    category: str
    size: int | None
    policy_sensitive: bool
    path: str | None
    hits: int = 0
    size_changed: bool = False
    reason: str | None = None


class Coverage:
    def __init__(self):
        self.targets = {}
        self.external = []
        self.science = {}
        self.c009_engine_refs = []
        self.errors = Counter()
        self.error_examples = []

    def error(self, kind, value):
        self.errors[kind] += 1
        if len(self.error_examples) < MAX_EXAMPLES:
            self.error_examples.append({"kind": kind, "path": value})

    def target(self, category, value, *, policy_sensitive=False, compact=False):
        ref = value if isinstance(value, dict) else None
        path = ref["path"] if ref is not None else value
        if path.startswith("/") or re.match(r"^[a-zA-Z]:", path):
            require(policy_sensitive, f"External required project artifact: {path}")
            if len(self.external) < MAX_EXAMPLES:
                self.external.append({"path": path, "reason": "external_host_dependency", "reference": ref})
            return
        path = project_relative(path).as_posix()
        size = ref["bytes"] if ref is not None and (not policy_sensitive or category == "C009_phase_artifacts") else None
        key = path_key(path)
        current = self.targets.get(key)
        if current is not None:
            if size is not None:
                require(current.size in (None, size), f"Conflicting immutable references for {path}")
                current.size = size
            if not policy_sensitive:
                current.policy_sensitive = False
            return
        require(len(self.targets) < MAX_TARGETS, "Target references exceed the bounded coverage index")
        self.targets[key] = Target(category, size, policy_sensitive, None if compact else path)

    def inspect_sources(self):
        for category, paths in ANCHORS.items():
            for path in paths:
                self.target(category, path)
        source = read_json(PROJECT / "qc/source_provenance_audit.json")
        require(len(source["records"]) == 1170, "Source provenance denominator changed")
        require(Counter(row["production_disposition"] for row in source["records"]) ==
                {"SOURCE_SUPPORTED_BIOLOGICAL_QC_NOT_RUN": 919, "HOLD": 223, "EXCLUDED_SOURCE": 28},
                "Source disposition counts changed")
        checkm = read_json(PROJECT / "metadata/checkm1_accepted_method_results_v001.json")
        require(len(checkm["entries"]) == 919, "CheckM1 registry is incomplete")
        queue = read_json(PROJECT / QUEUE)
        accessions = {row["accession"] for row in queue["rows"]}
        require(len(queue["rows"]) == len(accessions) == 919, "Defence queue accessions are incomplete or duplicated")
        for row in queue["rows"]:
            source = row["supplied_gene_request"]
            for name in ("canonical_FAA", "Prodigal_GFF", "protein_coordinate_map"):
                self.target("canonical_" + name, source[name])
            for name in ("uniform_annotation_commit", "closed_annotation_acceptance"):
                self.target("annotation_provenance", source[name])
        for category in ("canonical_canonical_FAA", "canonical_Prodigal_GFF", "canonical_protein_coordinate_map"):
            require(sum(target.category == category for target in self.targets.values()) == 919,
                    f"Unexpected reused or missing per-accession artifact: {category}")
        self.science.update(acquired_source_records=1170, checkm1_method_records=919, queue_genomes=919)
        self.inspect_tree()
        self.inspect_defence(accessions)

    def inspect_tree(self):
        accepted_path = "metadata/stage07_conservative900_54_v001/Root_ACCEPTED_COMPUTATIONAL_MATRIX.json"
        acceptance = read_json(PROJECT / accepted_path)
        require((acceptance["genomes"], acceptance["markers"], acceptance["amino_acid_columns"]) == (900, 54, 13071),
                "Stage 07 matrix dimensions differ")
        self.target("matrix", accepted_path)
        for name in ("matrix_commit", "independent_validation", "independent_composition_review"):
            self.target("matrix", acceptance[name])
        matrix = pinned(acceptance["matrix_commit"])
        require(len(matrix["locus_commits"]) == 54, "Stage 07 lacks 54 locus commits")
        for ref in matrix["locus_commits"] + matrix["artifacts"]:
            self.target("matrix", ref)
        expected = (PROJECT / PANEL / "cohort_accessions_v001.txt").read_text(encoding="utf-8-sig").split()
        require(len(expected) == len(set(expected)) == 900, "Tree cohort labels differ")
        observed = []
        length = 0
        with (PROJECT / MATRIX / "supermatrix.faa").open(encoding="utf-8") as stream:
            for line in stream:
                if line.startswith(">"):
                    require(not observed or length == 13071, "Matrix row length differs")
                    observed.append(line[1:].split()[0])
                    length = 0
                else:
                    length += len(line.strip())
        require(length == 13071 and Counter(observed) == Counter(expected), "Matrix labels or columns differ")
        self.target("matrix", MATRIX + "/supermatrix.faa")
        self.target("matrix", MATRIX + "/partitions.nex")
        computed_path = TREE + "/COMPUTED.json"
        computed = read_json(PROJECT / computed_path)
        require(computed["taxa"] == 900 and computed["actual_emitted_UFBoot_tree_count"] == 1000,
                "Tree output counts differ")
        self.target("tree_outputs", computed_path)
        for ref in computed["artifacts"]:
            self.target("tree_outputs", ref)
        for suffix in ("treefile", "contree", "iqtree", "log", "ufboot", "splits.nex", "bionj", "mldist", "ckp.gz"):
            self.target("tree_outputs", TREE + "/inference/full_tree." + suffix)
        for name in ("tree", "consensus"):
            ref = computed[name]
            data = (PROJECT / project_relative(ref["path"])).read_bytes()
            require(len(data) == ref["bytes"] and hashlib.sha256(data).hexdigest() == ref["sha256"],
                    f"Saved {name} hash differs")
            require(Counter(ACCESSION.findall(data.decode())) == Counter(expected), f"Saved {name} tips differ")
        with gzip.open(PROJECT / TREE / "inference/full_tree.ckp.gz", "rb") as stream:
            require(stream.read(24).startswith(b"--- # IQ-TREE Checkpoint"), "Tree checkpoint header differs")
        stage09_pointer = "state/stage09_full900_validation_current.json"
        current = read_json(PROJECT / stage09_pointer)
        self.target("tree_validation", stage09_pointer)
        self.target("tree_validation", current["acceptance"])
        validated = pinned(current["acceptance"])
        self.target("tree_validation", validated["independent_validation_commit"])
        self.target("tree_validation", validated["production_native_WSL_IQTREE_all_owned_closure"])
        self.target("tree_validation", validated["unchanged_entire_completed_prefix_snapshot"])
        self.target("tree_outputs", computed["execution"])
        self.target("tree_outputs", computed["plan"])
        tree_plan = pinned(computed["plan"])
        for ref in tree_plan["tool_files"]:
            self.target("runtime_and_plan_dependencies", ref, policy_sensitive=True)
        self.science.update(tree_tips=900, matrix_loci=54, matrix_columns=13071, reported_bootstrap_trees=1000)

    def inspect_defence(self, queue_accessions):
        ledger = read_json(PROJECT / LEDGER)
        require(set(ledger["entries"]) == queue_accessions, "Ledger differs from frozen queue")
        grouped = defaultdict(set)
        refs = {}
        reserved = set()
        states = Counter()
        for accession, entry in ledger["entries"].items():
            states[entry["state"]] += 1
            if entry["state"] == "CLOSED_PAIRED_PROTEIN_SCOPE_ACCEPTED":
                ref = entry["acceptance"]
                grouped[ref["path"]].add(accession)
                require(refs.setdefault(ref["path"], ref) == ref, "Conflicting ledger acceptance reference")
            elif entry["state"] == "RESERVED" and entry["cohort_id"] == "C009":
                reserved.add(accession)
        require(states == {"CLOSED_PAIRED_PROTEIN_SCOPE_ACCEPTED": 165, "RESERVED": 20, "NOT_RUN_UNKNOWN": 734}
                and ledger["cohort_id"] == "C009" and len(grouped) == 9, "Defence handoff checkpoint has moved")
        self.target("defence_ledger", ledger["reservation"])
        for path, genomes in grouped.items():
            ref = refs[path]
            self.target("accepted_defence", ref)
            packet = pinned(ref)
            require(packet["genomes"] == len(genomes), f"Acceptance denominator differs in {path}")
            computed = pinned(packet["source_result"])
            require(set(computed["selected_accessions"]) == genomes, f"Accepted accessions differ in {path}")
            for name in (
                "source_plan", "source_result", "validated_rows", "QA_commit", "QA_native_actual_exit",
                "verified_files_and_births", "science_whole_closure", "independent_file_validation", "validation_actual_exit",
            ):
                if name in packet:
                    self.target("accepted_defence", packet[name])
            for ref in computed["genome_commits"] + computed["engine_phase_commits"]:
                self.target("accepted_defence", ref)
        self.science.update(accepted_defence_genomes=165, distinct_acceptance_packets=9, unsearched_defence_genomes=734)
        self.inspect_c009(reserved)

    def inspect_c009(self, reserved):
        result_path = C009 + "/COHORT_COMPLETE.json"
        result = read_json(PROJECT / result_path)
        selected = result["selected_accessions"]
        require(len(selected) == len(reserved) == 20 and set(selected) == reserved, "C009 has unexpected accessions")
        self.target("C009_checkpoint", result_path)
        self.target("C009_checkpoint", result["source_plan"])
        for name in ("Root_scientific_admission.json", "Root_source_review.json"):
            self.target("C009_checkpoint", "metadata/defence_bulk_C009_v003/" + name)
        current = read_json(PROJECT / "state/local_continuation_v8/dispatcher_terminal_error.json")
        self.target("C009_checkpoint", "state/local_continuation_v8/dispatcher_terminal_error.json")
        exit_ref = current["last_worker_actual_exit"]
        native = pinned(exit_ref)
        require(native["worker_identity"]["role"].startswith("NOVEL_C009") and native["actual_exit_code"] == 0
                and native["exact_birth_handle_retained"], "Missing exact successful C009 native exit")
        self.target("C009_checkpoint", exit_ref)
        wsl_path = "work/defence_bulk_C009_v003/WSL_actual_exit.json"
        require(read_json(PROJECT / wsl_path)["actual_exit_code"] == 0, "Missing successful C009 WSL exit")
        self.target("C009_checkpoint", wsl_path)
        phases = {}
        require(len(result["genome_commits"]) == 20, "C009 genome commit count differs")
        for accession, ref in zip(selected, result["genome_commits"]):
            self.target("C009_genomes", ref)
            genome = pinned(ref)
            require(genome["accession"] == accession and set(genome["engines"]) == {"PADLOC", "DefenseFinder"},
                    f"Incomplete paired result for {accession}")
            self.target("C009_genomes", genome["input_provenance"])
            for prepared in pinned(genome["input_provenance"])["files"].values():
                self.target("C009_genomes", prepared)
            for engine, phase_ref in genome["engines"].items():
                require(phase_ref["path"] not in phases, "Duplicate C009 engine reference")
                phases[phase_ref["path"]] = phase_ref
                self.target("C009_engine_commits", phase_ref)
                phase = pinned(phase_ref)
                require(phase["accession"] == accession and engine.casefold() in phase["engine"].casefold(),
                        f"Incorrect engine phase provenance for {accession}")
                for name in ("execution", "calls", "cache_provenance", "model_cache_provenance", "runtime_cache_provenance"):
                    if name in phase:
                        self.target("C009_engine_evidence", phase[name])
                for artifact in phase["artifacts"]:
                    self.target("C009_phase_artifacts", artifact, policy_sensitive=True, compact=True)
        committed = {ref["path"]: ref for ref in result["engine_phase_commits"]}
        require(len(result["engine_phase_commits"]) == len(committed) == 40 and committed == phases,
                "C009 has incomplete or inconsistent engine commits")
        self.c009_engine_refs = list(phases.values())
        plan = pinned(result["source_plan"])
        for name in ("ready_packet", "PADLOC_compiled_manifest", "PADLOC_rules", "DF_model_manifest", "DF_rules", "DF_runtime_manifest"):
            self.target("defence_model_provenance", plan[name])
        for ref in plan["sources"] + plan["bound_inputs"]:
            self.target("runtime_and_plan_dependencies", ref, policy_sensitive=True)
        self.science.update(C009_computed_genomes=20, C009_engine_commits=40, C009_independent_QA_accepted=False)

    def scan_groups(self, spool, groups):
        summaries = {}
        for group, expected in groups.items():
            require(re.fullmatch(r"[A-Za-z0-9_-]+", group) is not None, f"Invalid group name {group!r}")
            count = 0
            size = 0
            for row in ndjson(spool / (group + ".ndjson")):
                path = project_relative(row["path"])
                require(type(row["bytes"]) is int and row["bytes"] >= 0, f"Invalid byte count for {path}")
                count += 1
                size += row["bytes"]
                reason = forbidden_reason(path)
                if reason is not None:
                    self.error(reason, path.as_posix())
                target = self.targets.get(path_key(row["path"]))
                if target is not None:
                    target.hits += 1
                    if target.hits > 1:
                        self.error("duplicate_required_inventory_path", row["path"])
                    if target.size is not None and target.size != row["bytes"]:
                        target.size_changed = True
                        self.error("required_inventory_size_differs", row["path"])
            require(count == expected["members"] and size == expected["unpacked_bytes"], f"Group counters differ: {group}")
            summaries[group] = {"members": count, "unpacked_bytes": size}
        actual = {path.stem for path in spool.glob("*.ndjson")} - {"omissions"}
        require(actual == set(groups), "Unexpected or missing inventory group files")
        return summaries

    def match_omissions(self, spool):
        directory_reasons = {}
        for row in ndjson(spool / "omissions.ndjson"):
            relative = project_relative(row["path"])
            if row["type"] == "directory":
                require(len(directory_reasons) < 100_000, "Too many pruned directories")
                directory_reasons[relative.as_posix()] = row["reason"]
            target = self.targets.get(path_key(row["path"]))
            if target is not None:
                if target.hits:
                    self.error("path_both_included_and_omitted", row["path"])
                target.reason = row["reason"]

        def apply_parent(path, target):
            if target.reason is None:
                for parent in PurePosixPath(path).parents:
                    if parent.as_posix() in directory_reasons:
                        target.reason = directory_reasons[parent.as_posix()]
                        break

        for target in self.targets.values():
            if target.path is not None and not target.hits:
                apply_parent(target.path, target)
        for ref in self.c009_engine_refs:
            for artifact in pinned(ref)["artifacts"]:
                target = self.targets[path_key(artifact["path"])]
                if target.path is None and not target.hits:
                    target.path = artifact["path"]
                    apply_parent(target.path, target)

    def results(self):
        coverage = defaultdict(Counter)
        omissions = Counter()
        omitted_examples = []
        missing_examples = []
        for target in self.targets.values():
            counters = coverage[target.category]
            counters["referenced"] += 1
            if target.hits:
                counters["included"] += 1
                continue
            permitted = target.policy_sensitive and bool(target.reason)
            if target.category == "C009_phase_artifacts":
                permitted = permitted and target.reason in EXPLICIT_ARTIFACT_OMISSIONS
            example = {"path": target.path, "category": target.category, "reason": target.reason or "missing_without_omission_record"}
            if permitted:
                counters["documented_policy_omissions"] += 1
                omissions[example["reason"]] += 1
                if len(omitted_examples) < MAX_EXAMPLES:
                    omitted_examples.append(example)
            else:
                counters["missing_required"] += 1
                self.errors["missing_required_coverage"] += 1
                if len(missing_examples) < MAX_EXAMPLES:
                    missing_examples.append(example)
        return {
            "scientific_checkpoint": self.science, "coverage_by_category": dict(coverage),
            "documented_omissions_by_reason": dict(omissions),
            "documented_omission_examples": omitted_examples, "required_missing_examples": missing_examples,
            "external_host_dependencies": self.external,
            "integrity_errors_by_kind": dict(self.errors), "integrity_error_examples": self.error_examples,
            "example_limit_per_list": MAX_EXAMPLES,
        }


def check():
    source = BUNDLE / "inventory/COMMITTED.json"
    inventory = read_json(source)
    spool = (BUNDLE / project_relative(inventory["spool"])).resolve()
    require(spool.is_relative_to(BUNDLE / "inventory") and spool.is_dir(), "Invalid inventory spool path")
    audit = Coverage()
    audit.inspect_sources()
    groups = audit.scan_groups(spool, inventory["groups"])
    audit.match_omissions(spool)
    report = audit.results()
    report.update(
        status="PASS_INVENTORY_COVERAGE" if not audit.errors else "FAIL_REQUIRED_COVERAGE_OR_POLICY",
        inventory_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        inventory_source_snapshot_utc=inventory["source_snapshot_utc"],
        spool=inventory["spool"], inventory_groups=groups,
        verification_scope="Inventory membership, group counts, immutable reference dimensions and path safety. Archive bytes are checked separately.",
    )
    return report


def main():
    try:
        report = check()
    except (OSError, ValueError, KeyError, TypeError) as error:
        report = {"status": "FAIL_COVERAGE_INPUT_OR_STRUCTURE", "error": str(error)}
    report["checked_at_utc"] = datetime.now(timezone.utc).isoformat()
    path = BUNDLE / "coverage_report.json"
    temporary = path.with_suffix(".json.partial")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    print(f"{report['status']} {path}")
    return 0 if report["status"] == "PASS_INVENTORY_COVERAGE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
