"""Enter the same private PADLOC runtime, IPC and bounded RAM view as V002."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
plan_path = Path(sys.argv[1]).resolve()
assert plan_path.is_relative_to(ROOT)
assert hashlib.sha256(plan_path.read_bytes()).hexdigest() == sys.argv[2]
plan = json.loads(plan_path.read_text())
assert plan["schema"] == "TREE2_DEFENCE_NOVEL_PRODUCTION_COHORT_PLAN_V003"
work = (ROOT / plan["work"]).resolve()
ram = (ROOT / plan["ram_scratch"]).resolve()
runtime = (ROOT / plan["PADLOC_runtime_root"]).resolve()
assert all(path.is_relative_to(ROOT) for path in (work, ram, runtime))
for target in ("/tmp", "/dev/shm"):
    subprocess.run(["mount", "-t", "tmpfs", "-o", "size=32m,mode=1777,nosuid,nodev", "tmpfs", target], check=True)
ram.mkdir()
subprocess.run(["mount", "-t", "tmpfs", "-o", "size=1280m,mode=700,nosuid,nodev", "tmpfs", str(ram)], check=True)
subprocess.run(["mount", "--bind", str(runtime), "/usr/local"], check=True)
subprocess.run(["mount", "-o", "remount,bind,ro", "/usr/local"], check=True)
(work / "private_namespace.json").write_text(json.dumps({
    "mount_namespace": os.readlink("/proc/self/ns/mnt"),
    "IPC_namespace": os.readlink("/proc/self/ns/ipc"),
    "private_RAM_root": str(ram), "private_RAM_max_bytes": 1342177280,
    "private_tmp_and_shm_max_bytes": 67108864,
    "read_only_project_PADLOC_runtime_binding": str(runtime), "visible_prefix": "/usr/local",
    "no_global_WSL_change": True, "all_used_private_RAM_is_part_of_combined_RSS_memory_gate": True,
}, indent=2))
python = (ROOT / plan["python"]).resolve()
assert python.is_relative_to(ROOT)
os.execv(str(python), [str(python), "-B", str(ROOT / "scripts/defence_bulk_v003.py"), *sys.argv[1:]])
