"""Run one source-bound defence context after the current controller retains it."""
from pathlib import Path
import ctypes
import json
import msvcrt
import os
import subprocess
import sys
import time

import local_tree2_dispatcher as dispatcher
import marker_pilot_compute_v001 as files
from checkm2_native_rss_guard_v001 import summed_native_rss
from defence_cpu_configuration_v002 import configuration

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = "state/local_continuation_v8"
SCHEMA = "TREE2_DEFENCE_NOVEL_PRODUCTION_COHORT_PLAN_V003"


def linux_path(path):
    path = path.resolve()
    assert path.drive.upper() == "C:"
    return "/mnt/c/" + path.relative_to(path.anchor).as_posix()


def check_custody(plan, plan_path, expected, owner, ack, win):
    if not (
        ack.get("native_owner") == owner
        and ack.get("exact_handle_retained") is True
        and ack.get("input_plan_sha256") == expected
        and ack.get("current_state_namespace") == NAMESPACE
    ):
        return False
    if "initial_controller_attach_ACK" in ack:
        assert plan.get("resume") and plan.get("initial_controller_attach") is True
        authority_path = dispatcher.bind(ROOT, ack["initial_controller_authority"])
        authority = dispatcher.read(authority_path)
        attached = dispatcher.read(dispatcher.bind(ROOT, ack["initial_controller_attach_ACK"]))
        pointer = dispatcher.read(ROOT / "state/local_continuation_current_runtime.json")
        assert pointer["state_directory"] == NAMESPACE
        assert dispatcher.bind(ROOT, pointer["controller_repair_v008"]["authority"]) == authority_path
        assert dispatcher.bind(ROOT, authority["scientific_plan"]) == plan_path
        assert attached["schema"] == "TREE2_V008_EXACT_RETAINED_ATTACH_ACK"
        assert attached["worker_identity"] == authority["expected_worker"]
        assert all(attached["worker_identity"][key] == owner[key] for key in owner)
        handle = win.open_worker(attached["dispatcher_owner"])
        try:
            assert not win.wait(handle, 0)
        finally:
            win.close(handle)
    else:
        assert plan.get("initial_controller_attach") is not True
        attached = dispatcher.read(dispatcher.bind(ROOT, ack["current_namespace_ACK"]))
        assert attached["event_sha256"] == plan["current_event_sha256"]
        assert attached["exact_handle_retained"] is True
        assert all(attached["worker"][key] == owner[key] for key in owner)
    return True


def main():
    plan_path = dispatcher.inside(ROOT, sys.argv[1])
    expected = sys.argv[2]
    assert os.name == "nt" and os.environ.get("COMPUTERNAME", "").upper() == "WD"
    assert dispatcher.digest(plan_path) == expected
    plan = dispatcher.read(plan_path)
    assert plan["schema"] == SCHEMA and plan["current_state_namespace"] == NAMESPACE
    configuration(dict(plan, schema="TREE2_DEFENCE_NOVEL_PRODUCTION_COHORT_PLAN_V002"))
    dispatcher.bind(ROOT, plan["cpu_upgrade_authority"])
    for row in plan["sources"] + plan["bound_inputs"]:
        dispatcher.bind(ROOT, row)

    debit = 0.0
    deadline = plan["original_context_absolute_deadline_unix"]
    if plan.get("resume"):
        saved = dispatcher.read(dispatcher.bind(ROOT, plan["resume"]["failed_disposition"]))
        previous = dispatcher.read(dispatcher.bind(ROOT, plan["resume"]["source_plan"]))
        assert plan["original_context_absolute_deadline_unix"] == previous["original_context_absolute_deadline_unix"]
        assert all(plan[key] == previous[key] for key in ("science_seconds", "cold_seconds", "unit_seconds"))
        debit = saved["cold_seconds_consumed"]
        deadline = plan["recovery_operational_deadline_unix"]
        assert 0 < debit < plan["cold_seconds"]
        assert 0 < deadline - time.time() <= plan["cold_seconds"] - debit

    work = dispatcher.inside(ROOT, plan["work"])
    work.mkdir(exist_ok=True)
    win = dispatcher.Windows()
    owner = win.identity(ctypes.c_void_p(-1), os.getpid())
    locks = []
    started = time.monotonic()
    try:
        for name in ("checkm2_pilot_launcher.lock", "checkm2_install.lock"):
            lease = (ROOT / "state" / name).open("r+b")
            lease.seek(0)
            msvcrt.locking(lease.fileno(), msvcrt.LK_NBLCK, 1)
            locks.append(lease)
        files.save(work / "native_owner.json", {
            "native_owner": owner, "input_plan_sha256": expected, "input_plan": files.ref(plan_path),
            "started_utc": files.utc(), "method": "DEFENCE_STOCK_PROTEIN_SUPPORTED_COHORT_V003",
        })
        ack_path = work / "Root_companion_ack.json"
        while True:
            if time.monotonic() - started > 180 or time.time() > deadline:
                raise TimeoutError("Exact retained V008 custody is required before WSL science")
            assert summed_native_rss() <= plan["native_reserved_bytes"]
            if ack_path.exists() and check_custody(plan, plan_path, expected, owner, dispatcher.read(ack_path), win):
                break
            time.sleep(0.2)

        entry = linux_path(ROOT / "scripts/defence_bulk_namespace_v003.py")
        args = [
            "wsl", "-d", "Ubuntu", "--exec", "unshare", "--mount", "--ipc", "--propagation",
            "private", "/usr/bin/python3", "-B", entry, linux_path(plan_path), expected,
        ]
        files.save(work / "WSL_command.json", {"argv": args, "source_bound_plan": files.ref(plan_path)})
        with (work / "WSL.stdout.txt").open("xb") as out, (work / "WSL.stderr.txt").open("xb") as err:
            child = subprocess.Popen(args, stdout=out, stderr=err)
            identity = win.identity(int(child._handle), child.pid)
            files.save(work / "WSL_owner.json", {"identity": identity, "argv_role": "DEFENCE_PRIVATE_IPC_RAM_READONLY_R_RUNTIME"})
            failure = None
            stop_started = None
            peak = 0
            while child.poll() is None:
                rss = summed_native_rss(child)
                peak = max(peak, rss)
                if (
                    rss > plan["native_reserved_bytes"]
                    or time.time() > deadline
                    or debit + time.monotonic() - started > plan["cold_seconds"] + 180
                ):
                    failure = "Native RSS or finite cohort wall/deadline guard exceeded"
                    if stop_started is None:
                        stop_started = time.monotonic()
                        files.save(ROOT / plan["stop_path"], {
                            "reason": failure, "native_owner": owner, "no_blind_retry": True,
                        })
                if stop_started is not None and time.monotonic() - stop_started > 180:
                    files.save(work / "unresolved_WSL_ownership.json", {
                        "identity": identity, "actual_exit_code": None, "error": failure, "no_relaunch": True,
                    })
                    raise RuntimeError("Owned WSL cleanup unresolved; closure remains UNKNOWN")
                time.sleep(0.5)
            code = child.wait()
        files.save(work / "native_RSS_guard.json", {
            "peak_native_plus_retained_WSL_RSS_bytes": peak, "reservation_bytes": plan["native_reserved_bytes"],
            "fatal_resource_reason": failure,
        })
        files.save(work / "WSL_actual_exit.json", {
            "actual_exit_code": code, "identity": identity, "exact_birth_handle_retained": True,
            "waited_and_reaped": True, "observed_utc": files.utc(),
        })
        print(json.dumps({"WSL_actual_exit": code, "native_owner_actual_exit": "REQUIRES_EXTERNAL_RETAINED_HANDLE"}), flush=True)
        if failure:
            raise RuntimeError(failure)
        return code
    finally:
        for lease in reversed(locks):
            lease.seek(0)
            msvcrt.locking(lease.fileno(), msvcrt.LK_UNLCK, 1)
            lease.close()


if __name__ == "__main__":
    raise SystemExit(main())
