"""Export compact Tree 2 timing evidence from local, saved execution receipts."""

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import statistics


QUEUE_STATE = "state/defence_campaign_v001/ledger.json"
CONTROLLER = "state/local_continuation_v8"
C008_META = "metadata/defence_C008_recovery_20261105"
C009_WORK = "work/defence_bulk_C009_v003"
ENGINES = ("PADLOC", "DefenseFinder")
ACCESSION = re.compile(r"GC[AF]_\d+\.\d+")
BULK = re.compile(r"defence_bulk_(C\d{3})(?:_recovery)?_v\d{3}")


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def safe(root, relative):
    text = str(relative).replace("\\", "/")
    path = PurePosixPath(text)
    require(not path.is_absolute() and ".." not in path.parts and ":" not in text,
            f"Outside project: {text}")
    require(not any(part.casefold() in {".codex", "codex_home", "codex_sqlite_home", "cli_home"} for part in path.parts),
            "Private runtime directory")
    result = (root / path).resolve()
    require(result.is_relative_to(root), f"Resolved path leaves project: {text}")
    return result


def read(root, path):
    return json.loads(safe(root, path).read_bytes())


def read_optional(root, path):
    return read(root, path) if safe(root, path).is_file() else {}


def sha(root, path):
    with safe(root, path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_bound(root, ref):
    data = safe(root, ref["path"]).read_bytes()
    require(len(data) == ref["bytes"] and hashlib.sha256(data).hexdigest() == ref["sha256"],
            f"Receipt differs: {ref['path']}")
    return json.loads(data)


def dt(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def duration(a, b):
    return (dt(b) - dt(a)).total_seconds() if a and b else None


def argument(command, flag):
    argv = command.get("argv", [])
    values = [argv[index + 1] for index, value in enumerate(argv[:-1]) if value == flag]
    return values[0] if len(values) == 1 else None


def accepted_cohorts(root, ledger):
    refs = {}
    members = defaultdict(set)
    for accession, entry in ledger["entries"].items():
        if entry["state"] == "CLOSED_PAIRED_PROTEIN_SCOPE_ACCEPTED":
            cohort = entry.get("cohort_id") or "PILOT"
            members[cohort].add(accession)
            require(refs.setdefault(cohort, entry["acceptance"]) == entry["acceptance"], "Inconsistent acceptance pointer")
    result = {}
    for cohort, ref in refs.items():
        acceptance = read_bound(root, ref)
        committed = read_bound(root, acceptance["source_result"])
        require(set(committed["selected_accessions"]) == members[cohort], "Acceptance membership mismatch")
        result[cohort] = (ref, acceptance, members[cohort])
    return result


def phase_rows(root, attempt, cohort, output, accepted_ids, original_c008, inherited_ids, state):
    rows = []
    for folder in sorted(safe(root, output + "/rows").iterdir()):
        if not folder.is_dir() or not ACCESSION.fullmatch(folder.name):
            continue
        for engine in ENGINES:
            unit = f"{output}/rows/{folder.name}/{engine}/unit"
            execution_path = unit + "/execution.json"
            execution = read_optional(root, execution_path)
            if not execution:
                continue
            require(type(execution["actual_exit_code"]) is int, "Unobserved stock exit cannot be exported as a measurement")
            elapsed = execution["elapsed_seconds"]
            require(math.isfinite(elapsed) and elapsed > 0, f"Invalid measured duration: {execution_path}")
            command_path = unit + "/command.json"
            command = read(root, command_path)
            if original_c008:
                accepted = folder.name in inherited_ids and engine == "PADLOC"
                phase_state = "accepted_via_C008_recovery" if accepted else "failed_attempt_saved_phase"
            else:
                accepted = folder.name in accepted_ids
                phase_state = "accepted_protein_scope" if accepted else state
            rows.append({
                "cohort": cohort, "attempt": attempt, "accession": folder.name, "detector": engine,
                "scope_state": phase_state, "accepted_protein_scope": accepted,
                "stock_actual_exit_code": execution["actual_exit_code"],
                "stock_elapsed_seconds": elapsed,
                "started_utc": command.get("started_utc"), "ended_utc": execution.get("ended_utc"),
                "stock_cpu_or_worker_argument": argument(command, "--cpu" if engine == "PADLOC" else "--workers"),
                "owned_linux_rss_plus_private_ram_peak_bytes": execution.get("peak_summed_owned_Linux_RSS_plus_private_RAM_bytes"),
                "linux_available_minimum_bytes": execution.get("minimum_Linux_available_bytes"),
                "group_closed": execution.get("group_closed"),
                "stock_error_present": execution.get("error") is not None,
                "command_receipt": command_path, "command_receipt_sha256": sha(root, command_path),
                "execution_receipt": execution_path, "execution_receipt_sha256": sha(root, execution_path),
            })
    return rows


def defence_attempts(root):
    ledger = read(root, QUEUE_STATE)
    accepted = accepted_cohorts(root, ledger)
    inherited = read(root, C008_META + "/inherited_PADLOC_phases.json")
    inherited_ids = {row["accession"] for row in inherited["rows"] if row["phase"] is not None}
    require(len(inherited_ids) == 9, "C008 recovery evidence must identify nine saved PADLOC phases")
    attempts, phases = [], []
    pending_count = 0
    for folder in sorted(safe(root, "analysis").iterdir()):
        output = "analysis/" + folder.name
        match = BULK.fullmatch(folder.name)
        if folder.name == "defence_real_pilot_v001":
            cohort = "PILOT"
        elif match:
            cohort = match.group(1)
        else:
            continue
        original_c008 = cohort == "C008" and "_recovery_" not in folder.name
        recovered = "_recovery_" in folder.name
        acceptance_ref, acceptance, accepted_ids = accepted.get(cohort, (None, {}, set()))
        if acceptance and not original_c008:
            plan_ref = acceptance["source_plan"]
            result_ref = acceptance["source_result"]
            plan = read_bound(root, plan_ref)
            result = read_bound(root, result_ref)
        else:
            plan_path = "metadata/" + folder.name + "/Root_plan.json"
            plan = read(root, plan_path)
            plan_ref = {"path": plan_path}
            result_ref = {"path": output + "/COHORT_COMPLETE.json"}
            result = read_optional(root, result_ref["path"])
        require(plan["output"] == output, f"Source plan/output mismatch for {folder.name}")
        work = plan["work"]
        failure = read_optional(root, work + "/failure.json")
        if original_c008:
            state = "failed_output_contract_saved_nine_phases"
            require(not result and failure, "Original C008 must retain its failed attempt")
        elif acceptance:
            state = "closed_accepted_protein_scope"
        elif result:
            state = "computed_pending_closure_and_file_QA"
            pending_count += len(result["selected_accessions"])
        else:
            state = "partial_or_not_yet_accepted"
        rows = phase_rows(root, folder.name, cohort, output, accepted_ids, original_c008, inherited_ids, state)
        phases.extend(rows)
        science = result.get("attempt_scientific_seconds", result.get("actual_scientific_seconds"))
        cold = result.get("attempt_cold_seconds", result.get("actual_cold_seconds"))
        if original_c008:
            science, cold = failure["known_scientific_debit_seconds"], failure["known_cold_debit_seconds"]
        if science is not None:
            require(math.isclose(science, sum(row["stock_elapsed_seconds"] for row in rows), abs_tol=1e-6, rel_tol=0),
                    f"Timing reconciliation failed for {folder.name}")
        wsl = read_optional(root, work + "/WSL_actual_exit.json")
        owner = read_optional(root, work + "/native_owner.json")
        native_guard = read_optional(root, work + "/native_RSS_guard.json")
        started = owner.get("native_owner", {}).get("creation_time_utc") or owner.get("started_utc")
        ended = wsl.get("observed_utc")
        accepted_at = acceptance.get("at_utc") if not original_c008 else None
        qa_seconds = acceptance.get("file_QA_wall_seconds_separate") if not original_c008 else None
        if cohort == "PILOT" and qa_seconds is None:
            audit = read_bound(root, acceptance["independent_file_validation"])
            qa_seconds = audit.get("QC_wall_seconds", audit.get("elapsed_file_QA_seconds"))
        rss = [row["owned_linux_rss_plus_private_ram_peak_bytes"] for row in rows]
        available = [row["linux_available_minimum_bytes"] for row in rows]
        attempts.append({
            "cohort": cohort, "attempt": folder.name, "scope_state": state,
            "planned_genomes": len(plan["selected_accessions"]),
            "actual_PADLOC_phases": sum(row["detector"] == "PADLOC" for row in rows),
            "actual_DefenseFinder_phases": sum(row["detector"] == "DefenseFinder" for row in rows),
            "inherited_PADLOC_phases": result.get("inherited_PADLOC_phases", 0),
            "stock_actual0_phases": sum(row["stock_actual_exit_code"] == 0 for row in rows),
            "WSL_actual_exit_code": wsl.get("actual_exit_code"),
            "native_creation_utc": started, "WSL_exit_observed_utc": ended,
            "native_birth_to_WSL_exit_wall_seconds": duration(started, ended),
            "predictor_phase_wall_seconds": science, "worker_cold_wall_seconds": cold,
            "worker_other_wall_seconds": cold - science if cold is not None and science is not None else None,
            "inherited_scientific_seconds": result.get("inherited_scientific_seconds", 0),
            "file_QA_wall_seconds": qa_seconds, "accepted_utc": accepted_at,
            "native_birth_to_acceptance_seconds": duration(started, accepted_at),
            "cohort_peak_linux_rss_plus_private_ram_bytes": result.get("peak_Linux_RSS_plus_private_RAM_bytes"),
            "phase_peak_linux_rss_plus_private_ram_bytes": max(rss, default=None),
            "phase_minimum_linux_available_bytes": min(available, default=None),
            "native_plus_WSL_peak_rss_bytes": native_guard.get("peak_native_plus_retained_WSL_RSS_bytes"),
            "configured_stock_threads": plan.get("stock_threads"),
            "observed_stock_thread_arguments": ",".join(sorted({row["stock_cpu_or_worker_argument"] for row in rows
                                                                if row["stock_cpu_or_worker_argument"] is not None})),
            "observed_resource_failure": native_guard.get("fatal_resource_reason") is not None,
            "source_plan": plan_ref["path"],
            "result_or_failure_receipt": result_ref["path"] if result else work + "/failure.json",
            "acceptance_receipt": acceptance_ref["path"] if acceptance_ref and not original_c008 else None,
        })
    require(len({row["execution_receipt"] for row in phases}) == len(phases), "An execution receipt was counted twice")
    require(sum(row["accepted_protein_scope"] for row in phases) == 2 * ledger["closed_paired_protein_scope_genomes"],
            "Accepted phase denominator differs from ledger")
    require(sum(row["attempt"] == "defence_bulk_C008_v002" for row in phases) == 9,
            "C008 original stock phases were not counted exactly once")
    return ledger, attempts, phases, pending_count


def tree_attempts(root):
    prefix = "analysis/phylogeny/full900_production_v001/attempts"
    rows = []
    for folder in sorted(safe(root, prefix).iterdir()):
        unit = f"{prefix}/{folder.name}/unit"
        ref = unit + "/execution.json"
        execution = read_optional(root, ref)
        if not execution:
            continue
        command = read_optional(root, unit + "/command.json")
        rows.append({
            "attempt": folder.name,
            "threads": argument(command, "-T"),
            "internal_cache_target": argument(command, "--mem"),
            "stock_actual_exit_code": execution.get("actual_exit_code"),
            "stock_elapsed_seconds": execution.get("elapsed_seconds"),
            "started_utc": command.get("started_utc"),
            "ended_utc": execution.get("ended_utc"),
            "peak_owned_linux_rss_plus_private_ram_bytes": execution.get("peak_summed_owned_Linux_RSS_plus_private_RAM_bytes"),
            "minimum_linux_available_bytes": execution.get("minimum_Linux_available_bytes"),
            "group_closed": execution.get("group_closed"),
            "error_present": execution.get("error") is not None,
            "execution_receipt": ref, "execution_receipt_sha256": sha(root, ref),
        })
    return rows


def snapshot(root, observe):
    hardware = read(root, "evidence/runtime_inventory.json")
    os_info = hardware["os"]
    disk = next(item for item in hardware["disks"] if item["DeviceID"] == "C:")
    preflight = read(root, "work/defence_C008R_accept_ccbf/fresh_C009_linux_v002.json")
    c009 = read(root, "metadata/defence_bulk_C009_v003/Root_plan.json")
    terminal = read(root, CONTROLLER + "/dispatcher_terminal_error.json")
    native_ref = terminal["last_worker_actual_exit"]
    native = read_bound(root, native_ref)
    wsl = read(root, C009_WORK + "/WSL_actual_exit.json")
    roles = read(root, C008_META + "/Root_current_runtime_roles_v008.json")
    status = {
        "snapshot_utc": datetime.now(timezone.utc).isoformat(),
        "hardware_inventory_observed_utc": hardware["timestamp_utc"],
        "processor": hardware["processors"],
        "physical_memory_bytes": hardware["computer_system"]["TotalPhysicalMemory"],
        "windows": {key: os_info[key] for key in ("Caption", "Version", "BuildNumber", "OSArchitecture")},
        "project_disk_startup": {key: disk[key] for key in ("FileSystem", "Size", "FreeSpace")},
        "wsl_startup": {"application_version": "3.0.3.0", "ubuntu": "26.04.1 LTS",
                        "linux_logical_CPUs": 4, "linux_mem_total_bytes": 3580444672,
                        "swap_total_bytes": 8589934592,
                        "source": "evidence/runtime_inventory_ubuntu.txt and evidence/runtime_inventory_wsl.txt"},
        "C009_preflight": {key: preflight[key] for key in ("CPU_affinity", "Linux_available_bytes", "disk_free_bytes")},
        "C009_hard_guards": {key: c009[key] for key in ("stock_threads", "cpu_affinity", "native_reserved_bytes",
                                                         "linux_RSS_plus_RAM_bytes", "minimum_linux_available_bytes",
                                                         "unit_seconds", "science_seconds", "cold_seconds")},
        "project_free_disk_floor_bytes": 42949672960,
        "C009_terminal": {"native_exit": native["actual_exit_code"], "WSL_exit": wsl["actual_exit_code"],
                          "exact_native_receipt": native_ref, "native_exit_observed_utc": native["observed_utc"],
                          "WSL_exit_observed_utc": wsl["observed_utc"],
                          "dispatcher_state": read(root, CONTROLLER + "/dispatcher_status.json")["status"],
                          "supervisor_state": read(root, CONTROLLER + "/supervisor_status.json")["status"]},
    }
    if observe:
        status["project_volume_free_bytes_at_snapshot"] = shutil.disk_usage(root).free
        owners = {role: roles[role] for role in ("custodian", "supervisor", "dispatcher")}
        owners["C009_native"] = native["worker_identity"]
        owners["C009_WSL"] = wsl["identity"]
        status["exact_windows_process_observations"] = observe_windows(owners)
    return status


def observe_windows(owners):
    require(os.name == "nt", "--observe-local requires Windows")
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.GetProcessTimes.restype = wintypes.BOOL
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    result = {}
    for role, owner in owners.items():
        row = {key: owner[key] for key in ("pid", "creation_time_utc", "windows_creation_filetime_100ns")}
        handle = kernel.OpenProcess(0x00101000, False, owner["pid"])
        if not handle:
            row.update(observation="could_not_open_exact_PID", winerror=ctypes.get_last_error())
        else:
            try:
                birth, ended, system, user = (wintypes.FILETIME() for _ in range(4))
                if kernel.GetProcessTimes(handle, ctypes.byref(birth), ctypes.byref(ended), ctypes.byref(system), ctypes.byref(user)):
                    actual = (birth.dwHighDateTime << 32) | birth.dwLowDateTime
                    row["birth_matches"] = actual == owner["windows_creation_filetime_100ns"]
                    row["wait0_result"] = kernel.WaitForSingleObject(handle, 0)
                else:
                    row.update(observation="creation_query_failed", winerror=ctypes.get_last_error())
            finally:
                kernel.CloseHandle(handle)
        result[role] = row
    return result


def summarize(ledger, attempts, phases, pending):
    standard = {row["cohort"]: row for row in attempts if row["scope_state"] == "closed_accepted_protein_scope"}
    original = next(row for row in attempts if row["attempt"] == "defence_bulk_C008_v002")
    newer = next(row for row in attempts if row["cohort"] == "C009")
    start_pairs = [(standard[f"C{n:03d}"], standard[f"C{n + 1:03d}"]) for n in (5, 6)] + [(standard["C007"], original)]
    cycle_times = [duration(a["native_creation_utc"], b["native_creation_utc"]) for a, b in start_pairs]
    v003_cycle = newer["worker_cold_wall_seconds"] + standard["C008"]["file_QA_wall_seconds"]
    c008_elapsed = standard["C008"]["native_birth_to_acceptance_seconds"] - standard["C008"]["native_birth_to_WSL_exit_wall_seconds"]
    c008_to_c009 = duration(standard["C008"]["accepted_utc"], newer["native_creation_utc"])
    v003_cycle += c008_elapsed - standard["C008"]["file_QA_wall_seconds"] + c008_to_c009
    unsearched = sum(entry["state"] == "NOT_RUN_UNKNOWN" for entry in ledger["entries"].values())
    states = Counter(row["scope_state"] for row in phases)
    return {
        "ledger_revision": ledger["revision"],
        "ledger_source_supported_genomes": len(ledger["entries"]),
        "closed_accepted_paired_genomes": ledger["closed_paired_protein_scope_genomes"],
        "computed_pending_acceptance_genomes": pending, "unsearched_genomes": unsearched,
        "distinct_stock_execution_receipts": len(phases),
        "stock_execution_rows_by_scope_state": dict(states),
        "historical_CPU4_C005_C006_C007_cycle_seconds": cycle_times,
        "historical_CPU4_mean_cycle_seconds_per20": statistics.mean(cycle_times),
        "illustrative_v003_cycle_seconds_per20": v003_cycle,
        "estimated_unsearched_work_days_historical_cycle": unsearched / 20 * statistics.mean(cycle_times) / 86400,
        "estimated_unsearched_work_days_v003_scenario": unsearched / 20 * v003_cycle / 86400,
        "C009_predictor_wall_seconds": newer["predictor_phase_wall_seconds"],
        "C009_worker_other_wall_seconds": newer["worker_other_wall_seconds"],
        "C009_worker_cold_wall_seconds": newer["worker_cold_wall_seconds"],
        "C009_native_birth_to_WSL_exit_wall_seconds": newer["native_birth_to_WSL_exit_wall_seconds"],
        "C009_independent_QA_wall_seconds": newer["file_QA_wall_seconds"],
        "timing_definition": "Per-stock execution elapsed wall time, not CPU time. Recovery attempt and inherited costs are separate.",
    }


def save_csv(path, rows):
    require(rows, f"No measurements for {path.name}")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--observe-local", action="store_true", help="Query the recorded Windows PIDs and local disk without touching owners")
    arguments = parser.parse_args()
    root = arguments.project.resolve()
    output = arguments.output.resolve()
    ledger, attempts, phases, pending = defence_attempts(root)
    tree = tree_attempts(root)
    info = snapshot(root, arguments.observe_local)
    summary = summarize(ledger, attempts, phases, pending)
    output.mkdir(parents=True, exist_ok=True)
    save_csv(output / "detector_phases.csv", phases)
    save_csv(output / "defence_attempts.csv", attempts)
    save_csv(output / "full900_attempts.csv", tree)
    save_json(output / "performance_summary.json", summary)
    save_json(output / "hardware_and_checkpoint.json", info)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
