# Private short IPC capability and launch contract

The first resource pilot failed before gene prediction because Python's Unix
socket address exceeded the platform limit. That failure and all source data are
preserved. This correction changes project plumbing only. It does not change the
accepted base image, matching sklearn overlay, author software, models, database,
or scientific options.

`checkm2_ipc_proof_controller.py` admits the closed baseline receipt, takes the
common native launcher and setup locks, and permits one finite capability proof.
The total namespace budget is 1,200 seconds; each primitive test has 30 seconds,
2 GiB sampled group RSS, and 1 GiB available-memory headroom. Host free-space
reserve remains 40 GiB. The proof uses the actual image Python 3.12 and no genome,
TensorFlow, sklearn, or model imports.

The primary strategy binds a new project-owned directory onto `/tmp` only inside
the existing private mount namespace. It verifies exact backing inode, marker and
canary mapping, writable/nodev/nosuid/noexec flags, AF_UNIX bind/connect, and a
real SyncManager dictionary round trip. Only an explicit socket-bind
EOPNOTSUPP/ENOSYS result admits one fallback: a 32 MiB, 1,024-inode tmpfs mounted
at a new project IPC mountpoint and privately bound onto `/tmp`. The tmpfs holds
ephemeral IPC only. Every scientific input, scratch file and output stays in the
durable project workspace. No system mount configuration or global `/tmp` is
changed.

Upstream `ChangeTempAction` assigns `tempfile.tempdir` when it parses `--tmpdir`.
Consequently, a short TMPDIR environment alone is insufficient. The added
project bootstrap calls `multiprocessing.util.get_temp_dir()` before invoking
the unchanged, accepted effective bootstrap with `runpy` in the same process.
This caches the short IPC path. The author CLI subsequently assigns its original
long, durable scientific scratch path. The capability test emulates that exact
assignment before starting Manager, and separately proves that ordinary
temporary files use durable project scratch while Manager uses its cached short
socket path. Socket paths must be shorter than 108 bytes; the long scientific
scratch path must retain at least 108 bytes in this proof.

Alias and backing mounts close with ordinary unmount, in that order. The original
private read-only `/tmp` mapping must be restored; backing directories must be
empty. The existing image/overlay context then unmounts and verifies loop
autoclear. The native controller rehashes the clean image, compares host registry
hash/mtime/size and outside `/tmp` inode/mount identity, and only then publishes
`evidence/checkm2_runtime/ipc_capability_proof.json` with status
`PRIVATE_SHORT_IPC_PROVEN`. This status is a plumbing capability result and grants
no biological or production acceptance. A separate owner closure receipt is
required before another pilot can use it.

Future guarded launch (all paths remain project-owned):

```text
image helper --readonly-exec /usr/bin/python3 -B checkm2_ipc_alias.py
  --receipt <token_ipc.json> --proof <ipc_capability_proof.json>
  --proof-sha256 <SHA256> --token <fresh32hex> --exec <guarded controller>

image-python -B checkm2_ipc_bootstrap.py
  --proof <ipc_capability_proof.json> --proof-sha256 <SHA256>
  --receipt <run/target_ipc.json> checkm2 predict <unchanged author arguments>
```

The immutable native request and stable scientific binding must freeze proof,
helper, target bootstrap, accepted effective-bootstrap hashes and selected mode.
Per-launch backing inode/token belong to the execution receipt. The controller
must independently verify the active alias and retain `--tmpdir=<run/tmp>`.
There is no automatic retry, install, model mutation, or alternative backend after
the stated primary and bounded unsupported-socket fallback.

The single capability proof closed on 2026-10-26 at 22:26:14 UTC. The project
filesystem rejected AF_UNIX with errno 95. The admitted 32 MiB tmpfs fallback
passed with Python 3.12.16: the actual Manager socket address was 36 bytes while
ordinary scientific scratch retained its 161-byte project path. The probe group
peaked at 23,982,080 bytes RSS. All probe processes, private mounts and loop
associations closed; the image SHA256, shared registry and outside `/tmp` mapping
were unchanged. The supervised WSL child exit code was 0. The detached outer
native process exit code was not captured and remains null; independent closure
receipts record its original PID and tracked children absent, empty stderr and
successful exclusive reacquisition of the native, setup and Linux compute locks.
These results establish IPC plumbing capability only.

The helper's `alias_mount` field preserves the first row returned by `findmnt`
for a stacked mount; it can describe the covered read-only mount. The effective
alias in the capability proof was independently verified by `statvfs`, exact
backing inode and canary mapping. Runtime consumers resolve the actual effective
mount with an open directory descriptor's kernel `mnt_id`, then read the matching
mountinfo entry. The original helper and proof bytes remain unchanged.
