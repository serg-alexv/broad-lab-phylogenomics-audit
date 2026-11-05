"""Run one bounded native file audit with exact controller custody."""

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import shutil
import sys
import time

from checkm2_native_rss_guard_v001 import MemoryCounters
import local_tree2_dispatcher as b


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "TREE2_DEFENCE_READ_ONLY_QA_PLAN_V002"
NAMESPACE = "state/local_continuation_v8"
RSS_LIMIT = 134217728
WALL_LIMIT = 7200
DISK_RESERVE = 42949672960


def main():
    if not __debug__:
        raise RuntimeError("The independent defence audit requires assertions")
    plan_path = b.inside(ROOT, sys.argv[1])
    expected = sys.argv[2]
    assert os.name == "nt" and os.environ.get("COMPUTERNAME", "").upper() == "WD"
    assert b.digest(plan_path) == expected
    plan = b.read(plan_path)
    assert plan["schema"] == SCHEMA and Path(plan["project_root"]).resolve() == ROOT
    assert plan["native_RSS_limit_bytes"] == RSS_LIMIT and plan["native_affinity_CPUs"] == [2]
    assert plan["maximum_wall_seconds"] == WALL_LIMIT and plan["current_state_namespace"] == NAMESPACE
    total = plan["cohort_genomes"]
    assert type(total) is int and 1 <= total <= 20
    cohort = plan["cohort_id"]
    assert cohort.startswith("C") and len(cohort) == 4 and cohort[1:].isdigit()

    work = b.inside(ROOT, plan["work"])
    output = b.inside(ROOT, plan["output"])
    stop = b.inside(ROOT, plan["stop_path"])
    work.mkdir(exist_ok=True)
    kernel = b.Windows()
    current = ctypes.c_void_p(-1)
    owner = kernel.identity(current, os.getpid())
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
    kernel32.SetProcessAffinityMask.restype = wintypes.BOOL
    assert kernel32.SetProcessAffinityMask(current, 1 << 2)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(MemoryCounters), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    started = time.monotonic()
    peak = 0
    last = 0

    def guard():
        nonlocal peak
        if stop.exists() or (ROOT / "state/STOP").exists():
            raise InterruptedError("Scoped independent defence audit STOP")
        if time.monotonic() - started > WALL_LIMIT or time.time() > plan["absolute_deadline_unix"]:
            raise TimeoutError("Independent defence audit wall budget or deadline reached")
        if shutil.disk_usage(ROOT).free < DISK_RESERVE:
            raise OSError("Independent defence audit disk reserve below 40 GiB")
        counters = MemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        if not psapi.GetProcessMemoryInfo(current, ctypes.byref(counters), counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        peak = max(peak, counters.rss)
        if counters.rss > RSS_LIMIT:
            raise MemoryError("Independent defence audit exceeded 128 MiB native RSS")

    def publish(detail, done=0, target=total, force=False, status="RUNNING"):
        nonlocal last
        guard()
        if not force and time.monotonic() - last < 30:
            return
        row = {
            "id": "10", "name": "Independent defence output QC",
            "status": status, "detail": detail, "cohort_id": cohort,
            "pid": owner["pid"], "creation_time_utc": owner["creation_time_utc"],
            "done": done, "total": target, "unit": "independently audited paired genome rows",
            "native_RSS_peak_bytes": peak, "elapsed_QC_wall_seconds": time.monotonic() - started,
            "scientific_seconds_preserved": plan["scientific_seconds_preserved"],
            "no_scientific_inference_or_model_replay": True, "full_panel_final_acceptance": False,
            "updated_utc": b.utc(),
        }
        b.atomic(work / "progress.json", row)
        try:
            b.atomic(ROOT / "state/stages/10.json", row)
        except OSError as error:
            with (work / "optional_stage_display_errors.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({"error": str(error), "at_utc": b.utc()}) + "\n")
        last = time.monotonic()

    try:
        for ref in plan["sources"] + plan["bound_inputs"]:
            guard()
            b.bind(ROOT, ref)
        plan_ref = b.row(ROOT, plan_path)
        b.exclusive(work / "once_claim.json", {
            "plan": plan_ref, "native_owner": owner, "file_only_no_science_replay": True,
            "no_automatic_retry": True, "at_utc": b.utc(),
        })
        b.atomic(work / "native_owner.json", {
            "native_owner": owner, "input_plan_sha256": expected, "input_plan": plan_ref, "at_utc": b.utc(),
        })
        ack_path = work / "Root_companion_ack.json"
        until = time.monotonic() + 180
        while True:
            guard()
            ack = b.read(ack_path) if ack_path.exists() else {}
            if (
                ack.get("native_owner") == owner and ack.get("exact_handle_retained") is True
                and ack.get("input_plan_sha256") == expected and ack.get("current_state_namespace") == NAMESPACE
            ):
                attached = b.read(b.bind(ROOT, ack["current_namespace_ACK"]))
                assert attached["event_sha256"] == plan["current_event_sha256"]
                assert attached["exact_handle_retained"] is True
                assert all(attached["worker"][key] == owner[key] for key in owner)
                break
            if time.monotonic() > until:
                raise TimeoutError("Exact V008 retained custody ACK absent")
            time.sleep(0.2)
        output.mkdir(parents=True, exist_ok=False)
        publish("Preparing saved cohort audit: checking closure, source inputs and pinned model caches", force=True)
        from defence_file_QC_v002 import validate

        result = validate(ROOT, plan, output, guard, publish)
        guard()
        result.update(
            plan=plan_ref, native_owner=owner, peak_native_RSS_bytes=peak,
            QC_wall_seconds=time.monotonic() - started,
            file_QA_absolute_deadline_unix=plan["absolute_deadline_unix"],
            actual_native_exit="REQUIRES_EXTERNAL_RETAINED_HANDLE_EVENT",
            no_child_processes_or_private_Linux_namespace_created=True, at_utc=b.utc(),
        )
        b.exclusive(output / "COMMITTED.json", result)
        publish(
            "Saved-output audit passed. Waiting for exact native exit and cohort acceptance",
            total, total, True, "COMPUTED_QC_PASS_PENDING_EXTERNAL_NATIVE_EXIT_REVIEW",
        )
        b.atomic(work / "native_file_QC_guard.json", {
            "peak_native_RSS_bytes": peak, "limit_bytes": RSS_LIMIT,
            "elapsed_wall_seconds": time.monotonic() - started, "budget_seconds": WALL_LIMIT,
            "CPU_affinity": [2], "no_child_processes": True, "all_input_artifacts_read_only": True, "at_utc": b.utc(),
        })
        print(json.dumps({
            "status": result["status"], "commit": b.row(ROOT, output / "COMMITTED.json"),
            "native_exit_requires_retained_observer": True,
        }), flush=True)
        return 0
    except BaseException as error:
        failure = {
            "error": repr(error), "at_utc": b.utc(), "peak_native_RSS_bytes": peak,
            "elapsed_QC_wall_seconds": time.monotonic() - started, "scientific_outputs_unchanged": True,
            "failed_QC_is_not_biological_absence": True, "no_automatic_retry": True,
        }
        b.atomic(work / "failure.json", failure)
        try:
            b.atomic(ROOT / "state/stages/10.json", {
                "id": "10", "name": "Independent defence output QC",
                "status": "QC_VALIDATOR_FAILED_PENDING_EXACT_EXIT_REVIEW",
                "detail": str(error), "worker": owner, "failure": b.row(ROOT, work / "failure.json"),
                "full_panel_final_acceptance": False, "updated_utc": b.utc(),
            })
        except OSError:
            pass
        raise


if __name__ == "__main__":
    raise SystemExit(main())
