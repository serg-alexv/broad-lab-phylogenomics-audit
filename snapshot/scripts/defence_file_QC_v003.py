"""Independent audit of saved defence phases, including C008 checkpoint recovery."""

from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import time

from defence_file_QC_sqlite_v001 import VerifiedFiles
import local_tree2_dispatcher as b
import marker_pilot_compute_v001 as g


PADLOC_R_SHA = "d21ba942e80720d80027aa1740d756322560feaeb168bfa2890640d88950d4c0"
# The frozen default DF/RM/CAS profile multiset independently matched in C001, C003, C005 and C007.
DF_PROFILE_MULTISET_SHA = "67bb7fbd1b685dd1d23fc378420fafc8915d94d75694f6f842b1c854bd1747d0"
PADLOC_COLUMNS = (
    "system.number", "seqid", "system", "target.name", "hmm.accession", "hmm.name",
    "protein.name", "full.seq.E.value", "domain.iE.value", "target.coverage",
    "hmm.coverage", "start", "end", "strand", "target.description", "relative.position",
    "contig.end", "all.domains", "best.hits",
)
PADLOC = "PADLOC"
DF = "DefenseFinder"
ENGINE_NAMES = {PADLOC: "PADLOC2_DB2", DF: "DefenseFinder3_models3.1_Cas3.1"}


def _stock_messages(stdout):
    messages = []
    for line in stdout.splitlines():
        match = re.fullmatch(r"\[[0-9]{2}:[0-9]{2}:[0-9]{2}\] >> (.+)", line)
        assert match, "Malformed or unexpected PADLOC stdout"
        messages.append(match.group(1))
    assert len(messages) >= 3
    assert messages[-3:-1] == [
        "Scanning padloc_canonical for defence system proteins",
        "Searching padloc_canonical for defence systems",
    ]
    return messages


def _complete_hmmer(path, domain_table=False):
    with path.open("rb") as stream:
        stream.seek(max(0, path.stat().st_size - 4096))
        footer = stream.read().splitlines()[-1:]
        expected = ([b"# [ok]"],) if domain_table else ([b"[ok]"], [b"# [ok]"])
        assert footer in expected, "Incomplete raw HMMER output"


def _read_csv(path, delimiter=",", expected_columns=None):
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter=delimiter, strict=True)
        if expected_columns is not None:
            assert tuple(reader.fieldnames or ()) == expected_columns
        rows = list(reader)
    assert all(None not in row and None not in row.values() for row in rows)
    return rows


def _padloc_stock_rows(root, folder, phase, plan, prepared, searched, artifacts, bound):
    """Reconstruct the outcome from stock bytes and typed exits, independent of V003."""
    unit = folder / "unit"
    stock = folder / "stock_output"
    report = stock / "padloc_canonical_padloc.csv"
    gff_report = stock / "padloc_canonical_padloc.gff"
    stdout = unit / "stdout.txt"
    domtbl = stock / "padloc_canonical.domtblout"
    execution = b.read(bound(phase["execution"]))
    assert execution["unit"] == "PADLOC_STOCK_FULL_PROTEIN_SCOPE"
    command = b.read(bound(artifacts[unit / "command.json"]))
    files = prepared["files"]
    assert command["unit"] == execution["unit"]
    assert command["inputs"] == [
        files["padloc_canonical.faa"], files["padloc_canonical.gff"], plan["PADLOC_compiled_manifest"],
    ]
    argv = command["argv"]
    assert argv[0] == "/usr/local/bin/padloc"
    assert argv[1::2] == ["--data", "--faa", "--gff", "--outdir", "--cpu"] and len(argv) == 11
    assert argv[-1] == str(plan["stock_threads"])
    query = Path(argv[4])
    assert query.name == "padloc_canonical.faa" and query.parent.name == prepared["accession"]
    assert Path(argv[6]) == query.with_name("padloc_canonical.gff")
    assert argv[8].endswith("/" + stock.relative_to(root).as_posix())
    assert len(searched) == 1
    hmm_ref, hmm = searched[0]
    assert hmm["argv"][-1] == argv[4]
    assert len(hmm["raw_outputs"]) == 1
    raw = hmm["raw_outputs"][0]
    assert raw["original_stock_output_path"] == argv[8] + "/padloc_canonical.domtblout"
    assert bound(raw).parent == bound(hmm_ref).parent
    domtbl_ref = artifacts[domtbl]
    assert (domtbl_ref["sha256"], domtbl_ref["bytes"]) == (raw["sha256"], raw["bytes"])
    _complete_hmmer(bound(domtbl_ref), domain_table=True)
    messages = _stock_messages(bound(artifacts[stdout]).read_text(encoding="utf-8"))

    evidence = phase.get("padloc_output_classification")
    if report.exists() or gff_report.exists():
        assert report.is_file() and gff_report.is_file() and gff_report.stat().st_size > 0
        assert report in artifacts and gff_report in artifacts
        assert messages[-1] == "Writing output to '" + argv[8] + "/padloc_canonical_padloc.csv'"
        assert "Nothing found for padloc_canonical" not in messages
        rows = _read_csv(bound(artifacts[report]), expected_columns=PADLOC_COLUMNS)
        assert rows, "Stock CSV exists without a system row"
        state = "STOCK_REPORT_PRESENT_VALIDATED"
        report_ref = artifacts[report]
    else:
        assert evidence is not None, "Absent PADLOC report requires an explicit evidence record"
        assert report not in artifacts and gff_report not in artifacts
        assert messages[-1] == "Nothing found for padloc_canonical"
        assert messages.count("Nothing found for padloc_canonical") == 1
        rows = []
        state = "STOCK_ZERO_SYSTEMS_NO_REPORT_VALIDATED"
        report_ref = None

    if evidence is not None:
        stock_r = evidence["stock_R_source"]
        assert stock_r["sha256"] == PADLOC_R_SHA and bound(stock_r).name == "padloc.R"
        assert stock_r == plan["PADLOC_stock_R"]
        assert evidence == {
            "state": state,
            "report": report_ref,
            "stdout": artifacts[stdout],
            "stock_R_source": stock_r,
            "stock_domtblout": domtbl_ref,
            "typed_HMMER_receipt": hmm_ref,
        }
    return rows, state


def _index(rows, field):
    result = {row[field]: row for row in rows}
    assert len(result) == len(rows), f"Duplicate {field} in saved output"
    return result


def _check_supplied_inputs(prepared, source, bound, read):
    assert prepared["input_request"] == source
    for value in source.values():
        if isinstance(value, dict) and {"path", "sha256", "bytes"} <= value.keys():
            bound(value)
    files = prepared["files"]
    for value in files.values():
        bound(value)
    canonical = g.fasta(bound(source["canonical_FAA"]))
    adapted_df = g.fasta(bound(files["defensefinder_gembase.faa"]))
    assert files["padloc_canonical.faa"]["sha256"] == source["canonical_FAA"]["sha256"]
    mapping = read(files["protein_identity_map.json"])
    by_id = _index(mapping, "canonical_id")
    by_df = _index(mapping, "DF_ID")
    coords = _index(read(source["protein_coordinate_map"]), "protein_id")
    assert set(canonical) == set(by_id) == set(coords)
    assert set(adapted_df) == set(by_df) and len(canonical) == len(adapted_df) == prepared["protein_count"]
    original_gff = bound(source["Prodigal_GFF"]).read_text().splitlines()
    fields = ("contig", "start", "end", "strand")
    for row in mapping:
        protein_id = row["canonical_id"]
        original = coords[protein_id]
        assert all(row[key] == original[key] for key in fields)
        assert row["original_Prodigal_ID"] == original["prodigal_gene_id"]
        aa = canonical[protein_id]
        assert aa == adapted_df[row["DF_ID"]]
        assert hashlib.sha256(aa.encode()).hexdigest() == row["AA_sha256"]
        original_index = row["source_GFF_line_number"] - 1
        assert 0 <= original_index < len(original_gff)
        assert hashlib.sha256(original_gff[original_index].encode()).hexdigest() == row["source_GFF_line_sha256"]
    adapted_gff = bound(files["padloc_canonical.gff"]).read_text().splitlines()
    seen = set()
    for line in adapted_gff:
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        assert len(parts) == 9
        attributes = dict(value.split("=", 1) for value in parts[8].split(";") if "=" in value)
        protein_id = attributes["ID"]
        assert protein_id not in seen
        seen.add(protein_id)
        assert (parts[0], int(parts[3]), int(parts[4]), parts[6]) == tuple(by_id[protein_id][key] for key in fields)
    assert seen == set(by_id)
    return by_id, by_df


def _padloc_scope(stock, scope, by_id, models, masks):
    expected = defaultdict(list)
    for row in stock:
        protein = by_id[row["target.name"]]
        assert (row["seqid"], int(row["start"]), int(row["end"]), row["strand"]) == (
            protein["contig"], protein["start"], protein["end"], protein["strand"],
        )
        expected[(row["seqid"], row["system.number"], row["system"])].append(row)
    assert scope["all_original_masks"] == masks
    keys = set()
    observed = set()
    for call in scope["calls"]:
        key = (call["contig"], call["stock_system_number"], call["model_id"])
        assert key in expected and key not in keys
        keys.add(key)
        assert call["stock_rows"] == expected[key]
        assert call["canonical_protein_IDs"] == sorted({row["target.name"] for row in expected[key]})
        model = models[call["model_id"]]
        observed.add(call["model_id"])
        rna = any(model["RNA_feature_roles"].values())
        eligible = model["registered_search_enabled"] and not rna and not any(
            model[field] for field in ("explicit_HEC_PDC_candidate", "relaxed_other_model", "module_or_non_antiphage_function_review_flag")
        )
        assert call["eligible_primary_predicted_protein_system"] == eligible
        assert call["inferred_HEC_PDC"] == model["explicit_HEC_PDC_candidate"]
        assert call["relaxed_model"] == model["relaxed_other_model"]
        assert call["feature_availability_state"] == (
            "UNKNOWN_RNA_FEATURES_UNAVAILABLE" if rna else "COMPLETE_PROTEIN_MODEL_PREDICTION"
        )
    assert keys == set(expected)
    states = _index(scope["model_states"], "model_id")
    assert set(states) == set(models)
    rna_unknown = 0
    for model_id, model in models.items():
        if not model["registered_search_enabled"]:
            state = "NOT_SEARCHED_UNREGISTERED"
        elif any(model["RNA_feature_roles"].values()):
            state = "UNKNOWN_RNA_FEATURES_UNAVAILABLE"
            rna_unknown += 1
        elif model_id in observed:
            state = "COMPLETE_PROTEIN_MODEL_PREDICTION"
        else:
            state = "NO_COMPLETE_PROTEIN_MODEL_CALL_AFTER_SUCCESS_NOT_BIOLOGICAL_ABSENCE"
        assert states[model_id]["availability_and_prediction_state"] == state
    assert rna_unknown == 51


def _defensefinder_scope(stock, scope, by_df, models, masks):
    assert [call["stock_call"] for call in scope["calls"]] == stock
    assert scope["source_masks"] == masks
    observed = set()
    for call in scope["calls"]:
        row = call["stock_call"]
        identifiers = row["protein_in_syst"].split(",")
        model = models[call["model_id"]]
        observed.add(call["model_id"])
        contigs = sorted({by_df[identifier]["contig"] for identifier in identifiers})
        repeated = len(identifiers) != len(set(identifiers))
        anti = model["namespace"] == "ADF" or model["functional_class"] == "ANTI_DEFENCE_EXCLUDED_FROM_ANTIPHAGE_RING"
        assert call["DF_IDs"] == identifiers
        assert call["canonical_protein_IDs"] == [by_df[identifier]["canonical_id"] for identifier in identifiers]
        assert call["original_contigs"] == contigs and len(identifiers) == int(row["genes_count"])
        eligible = not anti and not model["CAS_generic_cluster_requires_distinct_review"] and len(contigs) == 1 and not repeated
        assert call["eligible_primary_predicted_protein_system"] == eligible
        assert call["repeated_gene_ID_role_assignments_preserved_for_review"] == repeated
        assert call["cross_contig_review_required"] == (len(contigs) != 1)
        assert call["anti_defence_excluded"] == anti
    states = _index(scope["model_states"], "model_id")
    assert set(states) == set(models)
    for model_id, model in models.items():
        if model["namespace"] == "ADF":
            state = "EXCLUDED_ANTI_DEFENCE_SCOPE"
        elif model_id in observed:
            state = "COMPLETE_PROTEIN_MODEL_PREDICTION"
        else:
            state = "NO_COMPLETE_PROTEIN_MODEL_CALL_AFTER_SUCCESS_NOT_BIOLOGICAL_ABSENCE"
        assert states[model_id]["availability_and_prediction_state"] == state


def _read_inheritance(plan, read):
    resume = plan.get("resume")
    if not resume:
        return None, {}, {}, 0.0, 0.0
    assert plan["cohort_id"] == "C008" and len(plan["selected_accessions"]) == 20
    original = read(resume["source_plan"])
    failed = read(resume["failed_disposition"])
    recovery = read(resume["recovery_reservation"])
    snapshot = read(resume["snapshot"])
    closure = read(resume["whole_closure"])
    assert snapshot["cohort_id"] == "C008" and snapshot["whole_closure"] == resume["whole_closure"]
    assert snapshot["archive_every_member_independently_hashed_and_paths_links_matched"] is True
    assert closure["all_native_WSL_stock_HMMER_captured_descendant_group_private_mount_IPC_R_binding_RAM_FD_and_fourlease_closure"] is True
    assert failed["source_plan"] == resume["source_plan"]
    assert failed["snapshot"] == resume["snapshot"] and failed["whole_owned_closure"] == resume["whole_closure"]
    assert read(failed["actual_native_exit"])["actual_exit_code"] == 1
    assert read(failed["actual_WSL_exit"])["actual_exit_code"] == 1
    assert recovery["inherited_phase_manifest"] == resume["inherited_phase_manifest"]
    assert recovery["original_reservation"] == original["reservation"] == plan["reservation"]
    for key in (
        "selected_accessions", "queue", "scope_sha256", "PADLOC_compiled_manifest",
        "PADLOC_HMM_sha256", "PADLOC_rules", "DF_model_manifest", "DF_rules",
        "DF_profile_SHA256", "cpu_affinity", "stock_threads", "native_reserved_bytes",
        "linux_RSS_plus_RAM_bytes", "minimum_linux_available_bytes",
        "unit_seconds", "science_seconds", "cold_seconds", "original_context_absolute_deadline_unix",
    ):
        assert original[key] == plan[key], f"Recovery changes original scientific field {key}"
    manifest = read(resume["inherited_phase_manifest"])
    assert manifest["schema"] == "TREE2_DEFENCE_INHERITED_PADLOC_PHASES_V003"
    assert manifest["status"] == "AUDITED_SAVED_PADLOC_PHASES_NO_SEARCH_REPLAY"
    assert manifest["source_plan"] == resume["source_plan"]
    assert manifest["selected_accessions"] == plan["selected_accessions"]
    rows = _index(manifest["rows"], "accession")
    phases = {accession: row["phase"] for accession, row in rows.items() if row["phase"] is not None}
    assert set(phases) == set(plan["selected_accessions"][:9])
    inputs = manifest.get("supplied_inputs_by_accession") or {
        accession: row["input_provenance"] for accession, row in rows.items()
    }
    assert set(inputs) == set(plan["selected_accessions"])
    assert all(row["input_provenance"] == inputs[accession] for accession, row in rows.items())
    science = manifest["prior_scientific_seconds"]
    cold = manifest["prior_cold_seconds"]
    assert science == failed["scientific_seconds_consumed"] == recovery["prior_scientific_seconds"]
    assert cold == failed["cold_seconds_consumed"] == recovery["prior_cold_seconds"]
    return original, phases, inputs, science, cold


def validate(root, qa, output, guard, notify):
    """Audit every paired phase and all saved input/output hashes, without running tools."""
    started = time.monotonic()
    byte_count = 0
    summaries = []
    total = qa["cohort_genomes"]
    assert type(total) is int and 1 <= total <= 20
    cache = VerifiedFiles(output / "verified_files_and_births.sqlite")

    def bound(ref):
        nonlocal byte_count
        guard()
        path = b.inside(root, ref["path"])
        signature = (ref["sha256"], ref["bytes"])
        if path in cache:
            assert cache[path] == signature
        else:
            b.bind(root, ref)
            cache[path] = signature
            byte_count += ref["bytes"]
        return path

    def read(ref):
        return b.read(bound(ref))

    def publish(detail):
        guard()
        notify(detail, len(summaries), total)

    try:
        event = read(qa["event"])
        assert qa["event"]["sha256"] == qa["current_event_sha256"]
        handoff = read(qa["scientific_handoff"])
        assert qa["scientific_handoff"]["sha256"] == event["handoff_sha256"]
        assert event["actual_exit_code"] == 0 and event["retained_handle_identity_verified"] is True
        assert read(event["launch_receipt"])["native_owner"] == event["worker_identity"]
        assert read(event["actual_exit_receipt"])["actual_exit_code"] == 0
        for name in ("local_Root_scientific_admission", "local_Root_source_review", "source_bound_plan"):
            bound(handoff[name])
        plan = read(handoff["source_bound_plan"])
        assert plan["schema"] == "TREE2_DEFENCE_NOVEL_PRODUCTION_COHORT_PLAN_V003"
        assert plan["cohort_id"] == qa["cohort_id"]
        selected = plan["selected_accessions"]
        assert len(selected) == len(set(selected)) == total
        work = b.inside(root, plan["work"])
        result_path = b.inside(root, plan["output"]) / "COHORT_COMPLETE.json"
        result_ref = b.row(root, result_path)
        result = read(result_ref)
        assert result["source_plan"] == handoff["source_bound_plan"] and result["selected_accessions"] == selected
        assert result["no_complete_project_or_final_ring_acceptance"] is True
        assert read(qa["closed_cohort_manifest"])["source_result"] == result_ref
        bound(qa["whole_computation_closure"])

        wsl_ref = b.row(root, work / "WSL_actual_exit.json")
        wsl = read(wsl_ref)
        assert type(wsl["actual_exit_code"]) is int and wsl["actual_exit_code"] == 0
        assert wsl["exact_birth_handle_retained"] and wsl["waited_and_reaped"]
        memory = read(b.row(root, work / "native_RSS_guard.json"))
        assert memory["fatal_resource_reason"] is None
        assert memory["peak_native_plus_retained_WSL_RSS_bytes"] <= plan["native_reserved_bytes"]
        prior, inherited, inputs, inherited_seconds, inherited_cold = _read_inheritance(plan, read)
        for active_plan in (plan, prior):
            if active_plan is None:
                continue
            for ref in active_plan["sources"] + active_plan["bound_inputs"]:
                bound(ref)
        queue = _index(read(plan["queue"])["rows"], "accession")
        assert len(queue) == 919
        pad_models = _index(read(plan["PADLOC_rules"])["models"], "model_id")
        df_rules = read(plan["DF_rules"])["rows"]
        df_models = {"/".join((row["namespace"], row["family"], row["model"])): row for row in df_rules}
        assert len(pad_models) == 385 and len(df_models) == len(df_rules) == 710
        caches = {}
        for active_plan in (plan, prior):
            if active_plan is None:
                continue
            cache_names = ("cache_PADLOC_models.json", "cache_DF_models.json", "cache_DF_runtime.json")
            if active_plan is prior:
                cache_names = cache_names[:1]
            for name in cache_names:
                path = b.inside(root, active_plan["work"]) / name
                ref = b.row(root, path)
                for index, row in enumerate(read(ref)["cached_files"]):
                    bound(row["original_source"])
                    if index % 128 == 0:
                        publish("Preparation: verifying pinned cache " + name)
                caches[(active_plan["work"], name)] = ref

        total_seconds = 0.0
        new_seconds = 0.0
        old_seconds = 0.0
        peak = 0
        minimum = None
        raw_count = 0
        phase_refs = []
        absent_reports = []
        assert len(result["genome_commits"]) == total
        for accession, genome_ref in zip(selected, result["genome_commits"]):
            commit = read(genome_ref)
            source_row = queue[accession]
            source = source_row["supplied_gene_request"]
            assert commit["accession"] == accession and commit["source_queue_row"] == source_row
            assert commit["RNA_feature_models_remain_UNKNOWN"] is True
            assert commit["no_final_panel_or_ring_acceptance"] is True
            assert set(commit["engines"]) == {PADLOC, DF}
            assert b.inside(root, genome_ref["path"]) == result_path.parent / "rows" / accession / "COMMITTED.json"
            input_ref = commit["input_provenance"]
            if prior is not None:
                assert input_ref == inputs[accession]
            prepared = read(input_ref)
            assert prepared["accession"] == accession
            by_id, by_df = _check_supplied_inputs(prepared, source, bound, read)
            engines = {}
            for engine in (PADLOC, DF):
                phase_ref = commit["engines"][engine]
                phase = read(phase_ref)
                inherited_phase = engine == PADLOC and accession in inherited
                owner_plan = prior if inherited_phase else plan
                if inherited_phase:
                    assert phase_ref == inherited[accession]
                folder = bound(phase["execution"]).parent.parent
                assert folder == b.inside(root, owner_plan["output"]) / "rows" / accession / engine
                if "raw_phase_directory" in phase:
                    assert phase["raw_phase_directory"] == folder.relative_to(root).as_posix()
                if not inherited_phase or accession != selected[8]:
                    assert b.inside(root, phase_ref["path"]) == folder / "COMMITTED.json"
                assert phase["accession"] == accession and phase["engine"] == ENGINE_NAMES[engine]
                assert phase["source_queue_row"] == source_row
                assert phase["source_taxonomy_type_quality_holds_preserved"] is True
                execution = read(phase["execution"])
                assert type(execution["actual_exit_code"]) is int and execution["actual_exit_code"] == 0
                assert execution["actual_child_waited_and_reaped"] and execution["group_closed"]
                assert not execution["remaining_owned_identities"] and not execution["remaining_group_members"]
                assert execution["error"] is None
                for identity in execution["captured_owned_identities"]:
                    cache.identity(identity)
                rss = execution["peak_summed_owned_Linux_RSS_plus_private_RAM_bytes"]
                available = execution["minimum_Linux_available_bytes"]
                assert rss <= plan["linux_RSS_plus_RAM_bytes"] and available >= plan["minimum_linux_available_bytes"]
                peak = max(peak, rss)
                minimum = available if minimum is None else min(minimum, available)
                elapsed = execution["elapsed_seconds"]
                assert math.isfinite(elapsed) and 0 < elapsed <= owner_plan["unit_seconds"]
                total_seconds += elapsed
                if inherited_phase:
                    old_seconds += elapsed
                else:
                    new_seconds += elapsed
                artifacts = {}
                for ref in phase["artifacts"]:
                    path = bound(ref)
                    assert path not in artifacts
                    artifacts[path] = ref
                    publish(accession + " " + engine + " immutable saved files")
                assert phase["execution"] in artifacts.values() and phase["calls"] in artifacts.values()
                searches = []
                profile_paths = set()
                profiles = set()
                query_sha = prepared["files"]["padloc_canonical.faa" if engine == PADLOC else "defensefinder_gembase.faa"]["sha256"]
                for path in (folder / "HMMER_receipts").glob("*.json"):
                    ref = artifacts[path]
                    receipt = read(ref)
                    assert receipt["status"] == "ACTUAL_HMMER_EXIT_AND_RAW_CHECKPOINT_OBSERVED"
                    assert type(receipt["actual_exit_code"]) is int and receipt["actual_exit_code"] == 0
                    assert receipt["binary_handle_waited_and_reaped"]
                    cache.identity(receipt["binary_identity"])
                    if receipt["probe_only"]:
                        continue
                    assert receipt["query_faa_sha256"] == query_sha
                    assert receipt["no_argument_or_threshold_changes"] and receipt["raw_outputs"]
                    profile_paths.add(receipt["argv"][-2])
                    profiles.add(receipt["model_file_sha256"])
                    for raw in receipt["raw_outputs"]:
                        raw_path = bound(raw)
                        assert raw_path in artifacts
                        _complete_hmmer(raw_path, domain_table=engine == PADLOC)
                    searches.append((ref, receipt))
                assert len(searches) == phase["typed_scientific_HMMER_searches"]
                raw_count += len(searches)
                scope = read(phase["calls"])
                assert scope["all_stock_calls_preserved"] and scope["no_final_panel_or_ring_acceptance"]
                if engine == PADLOC:
                    assert profiles == {plan["PADLOC_HMM_sha256"]}
                    assert phase["cache_provenance"] == caches[(owner_plan["work"], "cache_PADLOC_models.json")]
                    pad_plan = dict(owner_plan, PADLOC_stock_R=plan["PADLOC_stock_R"])
                    stock, stock_state = _padloc_stock_rows(root, folder, phase, pad_plan, prepared, searches, artifacts, bound)
                    if not inherited_phase or accession == selected[8]:
                        assert phase.get("padloc_output_classification") is not None
                    if inherited_phase and accession == selected[8]:
                        assert stock_state == "STOCK_ZERO_SYSTEMS_NO_REPORT_VALIDATED"
                    if stock_state == "STOCK_ZERO_SYSTEMS_NO_REPORT_VALIDATED":
                        absent_reports.append(folder / "stock_output")
                    _padloc_scope(stock, scope, by_id, pad_models, source["source_masks"])
                else:
                    assert profiles <= set(plan["DF_profile_SHA256"])
                    inventory = Counter(receipt["model_file_sha256"] for _, receipt in searches)
                    inventory_bytes = json.dumps(sorted(inventory.items()), separators=(",", ":")).encode()
                    assert hashlib.sha256(inventory_bytes).hexdigest() == DF_PROFILE_MULTISET_SHA, (
                        "Default stock DF/RM/CAS profile multiset differs from independent accepted evidence"
                    )
                    assert phase["model_cache_provenance"] == caches[(plan["work"], "cache_DF_models.json")]
                    assert phase["runtime_cache_provenance"] == caches[(plan["work"], "cache_DF_runtime.json")]
                    reports = list((folder / "stock_output").glob("*_defense_finder_systems.tsv"))
                    assert len(reports) == 1
                    stock = _read_csv(bound(artifacts[reports[0]]), delimiter="\t")
                    _defensefinder_scope(stock, scope, by_df, df_models, source["source_masks"])
                    stock_state = "STOCK_DEFENSEFINDER_REPORT_VALIDATED"
                eligible = sum(call["eligible_primary_predicted_protein_system"] for call in scope["calls"])
                assert phase["model_relative_calls"] == len(scope["calls"])
                assert phase["eligible_primary_protein_predictions"] == eligible
                engines[engine] = {
                    "commit": phase_ref, "typed_HMMER0": len(searches),
                    "distinct_searched_profile_paths": len(profile_paths),
                    "stock_internal_repeated_profile_invocations_preserved": len(searches) - len(profile_paths),
                    "stock0_seconds": elapsed, "stock_model_relative_calls": len(scope["calls"]),
                    "eligible_primary_protein_predictions": eligible, "stock_output_state": stock_state,
                    "inherited_saved_phase": inherited_phase, "unavailable_is_UNKNOWN": True,
                    "no_biological_absence_or_final_ring_acceptance": True,
                }
                phase_refs.append(phase_ref)
            summaries.append({"accession": accession, "original_proteins": len(by_id), "engines": engines, "source_masks": source["source_masks"]})
            publish(accession + " both saved phases independently audited")

        def keys(refs):
            return {(ref["path"], ref["sha256"], ref["bytes"]) for ref in refs}

        assert len(phase_refs) == len(keys(phase_refs)) == len(result["engine_phase_commits"]) == 2 * total
        assert keys(phase_refs) == keys(result["engine_phase_commits"])
        assert result["inherited_PADLOC_phases"] == len(inherited)
        assert result["new_PADLOC_phases"] == total - len(inherited) and result["new_DefenseFinder_phases"] == total
        assert result["inherited_phase_manifest"] == ((plan.get("resume") or {}).get("inherited_phase_manifest"))
        assert math.isclose(old_seconds, inherited_seconds, abs_tol=1e-6, rel_tol=0)
        assert result["inherited_scientific_seconds"] == inherited_seconds
        assert result["inherited_cold_seconds"] == inherited_cold
        assert math.isclose(result["attempt_scientific_seconds"], new_seconds, abs_tol=1e-6, rel_tol=0)
        assert math.isclose(result["actual_scientific_seconds"], total_seconds, abs_tol=1e-6, rel_tol=0)
        assert math.isclose(result["actual_cold_seconds"], inherited_cold + result["attempt_cold_seconds"], abs_tol=1e-6, rel_tol=0)
        assert 0 < total_seconds <= plan["science_seconds"] and 0 < result["actual_cold_seconds"] <= plan["cold_seconds"]
        assert qa["scientific_seconds_preserved"] == result["actual_scientific_seconds"]
        cache.identity(read(b.row(root, work / "linux_owner.json")))
        if prior is not None:
            prior_owner = b.inside(root, prior["work"]) / "linux_owner.json"
            cache.identity(read(b.row(root, prior_owner)))
        cache.verify_all(root, guard, publish)
        file_count = len(cache)
        births = cache.birth_count()
        for stock_dir in absent_reports:
            assert not (stock_dir / "padloc_canonical_padloc.csv").exists()
            assert not (stock_dir / "padloc_canonical_padloc.gff").exists()
    finally:
        cache.close()

    rows_path = output / "validated_cohort_rows.json"
    b.exclusive(rows_path, {"rows": summaries, "all_masks_preserved": True, "no_prediction_search_annotation_replayed": True, "all919_still_required": True})
    summary = {
        "status": "SAVED_PAIRED_STOCK_PHASES_TYPED_RAW_EXITS_ORIGINAL_INPUTS_COMPLETE_SCOPE_AND_POSTHASH_VALIDATED_PENDING_QA_NATIVE_EXIT",
        "event": qa["event"], "source_plan": handoff["source_bound_plan"], "source_result": result_ref,
        "native_actual_exit": event["actual_exit_receipt"], "WSL_actual_exit": wsl_ref,
        "rows": b.row(root, rows_path), "verified_files_and_births": b.row(root, output / "verified_files_and_births.sqlite"),
        "actual0_stock_phases": len(phase_refs), "typed_HMMER0_searches": raw_count, "captured_Linux_births": births,
        "cohort_id": plan["cohort_id"], "genomes": total, "all_original_masks_preserved": True,
        "scientific_seconds": result["actual_scientific_seconds"], "cold_seconds": result["actual_cold_seconds"],
        "attempt_scientific_seconds": result["attempt_scientific_seconds"], "attempt_cold_seconds": result["attempt_cold_seconds"],
        "inherited_scientific_seconds": inherited_seconds, "inherited_cold_seconds": inherited_cold,
        "inherited_PADLOC_phases": len(inherited), "new_PADLOC_phases": total - len(inherited),
        "new_DefenseFinder_phases": total, "inherited_phase_manifest": result["inherited_phase_manifest"],
        "recovery_reservation": (plan.get("resume") or {}).get("recovery_reservation"),
        "stock_PADLOC_no_report_verified_count": len(absent_reports),
        "peak_Linux_RSS_plus_private_RAM_bytes": peak, "minimum_sampled_Linux_available_bytes": minimum,
        "native_peak_RSS_bytes": memory["peak_native_plus_retained_WSL_RSS_bytes"],
        "unique_files_hashed": file_count, "unique_source_and_output_bytes_hashed": byte_count,
        "unique_bytes_hashed": byte_count, "every_saved_file_independently_posthashed_again": True,
        "elapsed_file_QA_seconds": time.monotonic() - started, "whole_scientific_computation_closure": qa["whole_computation_closure"],
        "no_child_process_predictor_model_annotation_or_search_executed_by_QA": True,
        "no_biological_absence_inferred": True, "final_panel_ring_or_tree_acceptance": False,
        "retained_phylogeny_holds": plan["retained_phylogeny_scientific_holds"], "at_utc": b.utc(),
    }
    b.exclusive(output / "validation_summary.json", summary)
    return summary
