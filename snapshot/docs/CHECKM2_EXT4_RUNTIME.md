# CheckM2 project-owned image recovery

The first NTFS installation attempt timed out with all inputs preserved. One
bounded recovery uses `tools/checkm2_runtime_ext4.img`, a 16 GiB ext4 filesystem
stored entirely inside this WD project. All 133 package versions and source
archives are identical to the accepted CPU-only resolution; no scientific
program, model, method, or resource limit is changed.

The image has the NTFS sparse attribute, but the original Python truncation
physically allocated its full 17,179,869,184 bytes. This was measured directly.
Host free space after allocation was 163.50 GB, above the 40 GiB reserve. The
mounted filesystem admitted 16,710,995,968 free bytes against a conservative
16,284,403,482-byte bound including package cache, environment, database,
prefix-rewrite temporary files and a 2 GiB internal reserve. No mounted-image
compaction was attempted.

## Preserved inputs and canonical paths

The original archives, old extracted NTFS cache, verified database and incomplete
NTFS prefix remain untouched. Prior receipts/logs are copied with SHA256s into
`evidence/checkm2_runtime/history/ntfs_attempt_20261026T194928Z/`.

Inside a private namespace, the image mounts at `work/checkm2_runtime_mount`.
Its `env/` directory binds over the canonical Linux `tools/checkm2_env` path.
The old incomplete NTFS directory still occupies that path outside the namespace;
those outside bytes are not the accepted runtime. `pkgs/` and `tmp/` reside in
the image. The verified database is copied into `db/` and privately bound
read-only over its original canonical database filename. Original database
receipts and archive directory visibility remain unchanged.

Future checks must enter the private image namespace before inspecting binaries,
models or installed file manifests. Native Windows checks of the preserved
outside prefix cannot establish runtime readiness.

## Creation, attachment and persistence proof

Creation used exclusive new-file semantics, a random marker, a held native file
descriptor, and matching Linux device/inode/size/link-count identity. Only this
new regular project file was passed directly to `mkfs.ext4`; no block device was
ever a formatting target.

The helper atomically configures only an already existing major-7 loop node
using `LOOP_CONFIGURE` and `AUTOCLEAR`. It holds the loop descriptor throughout
mount lifetime and verifies backing path/device/inode, offset zero, unlimited
size, exact 16 GiB capacity, read-only flag and filesystem UUID. It creates no
device nodes, changes no global WSL settings and keeps mounts private.

Preparation passed at 20:24:36 UTC on 2026-10-26. One thousand new files and
case-distinct names were created in 1.915 seconds. Their hashes and the complete
3,082,500,605-byte database persisted across clean RW unmount, image sealing and
an independent RO remount. The filesystem UUID is
`18c07801-b8f4-4c2b-95a9-3c7bd6ccfdc8`. Both mounts closed and their owned loop
associations automatically detached; shared host registry bytes/hash/timestamp
remained unchanged. Preparation is not runtime readiness.

## Bounds and acceptance

The single recovery claim is exclusive and flushed before installation.
An existing claim is rejected before inspecting any possibly active image.
The closed prepared image is rehashed against its accepted seal before that
claim. Conda retains its 3600-second command deadline. The outer Linux lifecycle
is bounded to 5400 seconds; each CLI/model smoke and each image hash is bounded
to 600 seconds. Linux work uses two CPU cores, a sampled 2 GiB process-tree RSS
ceiling, at least 1 GiB available memory, and the disk reserves above.

The same accepted archives are extracted afresh into the image; the old NTFS
payload cache and incomplete prefix are never used as accepted software. All
133 image-cache archives are verified again before acceptance. Every installed
file and model is manifested, then verified again after clean unmount/sealing
and a read-only remount. CLI, imports, models and strict author database checks
must pass under that read-only mount. Four missing entries in the upstream
author model hash table remain explicit; all nine assets must match the
unchanged official package payload SHA256s.

The read-only path binds the raw image file RO before verifying its sealed hash,
uses an RO backing descriptor and RO loop device, and mounts ext4 with
`ro,noload,nodev,nosuid` while retaining execution. Teardown unbinds the database
and prefix, unmounts ext4, closes descriptors and verifies AUTOCLEAR, then
unmounts the raw-file bind. Whole-image sealing happens only after clean RW
unmount/detach. Readiness is committed last, after process closure and the
outside-registry audit; no genome is predicted by tool setup.

## Pilot interface

The unchanged outer namespace entry is
`scripts/checkm2_private_setup_ns.sh outer run <project-owned bash script>`.
That script invokes `checkm2_runtime_image.py --receipt <absolute project JSON>
--readonly-exec /usr/bin/python3 -B <pilot> ...`. The receipt option must precede
the remainder argument. The helper exports
`TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED=1` and
`TREE2_CHECKM2_RUNTIME_MOUNT_RECEIPT=<receipt>`.

The final READY object requires the private image mount and binds the image
path/hash/bytes/UUID/seal receipt, installed manifests, models, database and
environment receipt. Mount receipts additionally identify the current namespace,
loop mapping and effective RO state for raw image, canonical prefix and database.
The scientific pilot's task-specific hold remains until these gates pass.

## Completed installation and loader compatibility check

The identical 133-package closure installed successfully from 20:32:55 to
20:39:33 UTC (397.8 seconds). The Conda process group closed with exit 0 and a
sampled peak of 1,934,925,824 bytes. The first CLI import then exposed a runtime
loader incompatibility: the official TensorFlow shared library requests an
executable stack, while the Python executable requests a non-executable stack.
The host uses glibc 2.43. No library bytes or ELF flags were patched.

The [GNU dynamic-linking manual](https://sourceware.org/glibc/manual/latest/html_node/Dynamic-Linking-Tunables.html)
documents `GLIBC_TUNABLES=glibc.rtld.execstack=2` as a process-start compatibility
mode for this situation. It permits an executable stack in those launched
processes. It does not change a global WSL or system setting. Exact official
archive ELF headers, loader hashes, supported tunable values and source links
are retained in `loader_compatibility_source_audit.json`.

A separate bounded post-install check seals the cleanly closed installed image,
mounts it read-only and tests the unchanged CLI/models with this value present
before target Python startup. It invokes no installer, solver or genome
prediction. The original failed CLI logs are retained in immutable history.
Passing requires the actual CLI, model, payload, database, resource and closure
checks; source documentation alone is not a pass. Any final READY, environment
receipt and actual smoke report must contain the same
`runtime_environment_overrides` map, which the scientific pilot must enforce
before launching its Python processes.

## Matching-version resource-only acceptance

The base environment's scaler was serialized with scikit-learn 1.6.1; loading
it with the base 1.9.1 emitted the retained unsupported cross-version warning.
That load-only result was never a production-compatibility pass. An exact
official 1.6.1 wheel was prepared as a separate 894-file project overlay; no
base-image or original model bytes changed. Both image and overlay are privately
bound read-only for the effective runtime.

The unchanged CheckM2 main prepends its base site-packages path. Therefore the
declared PYTHONPATH alone is insufficient. The audited workflow bootstrap loads
and verifies overlay sklearn before importing that main module, checks origins
again after its path prepend, then executes the unchanged original entrypoint.
Generic dist-info discovery still finds the preserved base 1.9.1; explicit
overlay metadata and actual module origins establish the effective 1.6.1.

The single matching control run closed at 21:29:59 UTC on 2026-10-26. Effective
1.6.1 was verified before main, after main and after controls; all 99 imported
sklearn modules stayed in the overlay. No version warning occurred. All 21,241
scaler columns across six characterization fixtures (including saved extrema)
matched the affine computation with zero difference. A separate 60-digit Decimal
calculation checked 84,964 scalar values; its maximum floating-point difference
was 1.1102230246251565e-16. These fixtures characterize arithmetic, not biology.

Both 21,241-feature boosted models and the 20,021-by-1 neural input produced
finite, correctly shaped synthetic outputs. The unchanged upstream scale/slice/
reshape/output composition, five model-selection fixtures and a sparse cosine
zero-norm fixture passed. All nine original model/data hashes remained correct.
Native BLAS and both observed OpenMP runtimes reported two threads. The largest
control process group sampled 541,855,744 bytes; all three groups exited 0 and
closed. Image/overlay mounts closed cleanly, AUTOCLEAR detached the owned loop,
native PID3240 exited, and the shared registry remained unchanged.

`sklearn161_effective_runtime_validated.json` and
`state/checkm2_forward_ready.json` grant only a diagnostic resource pilot. They
bind the base candidate, image, models, overlay, bootstrap, actual effective
environment, control receipts and closure. Production acceptance remains false;
end-to-end controls and input/QC acceptance remain separate requirements. The
unlaunched baseline forward drafts were preserved in `work/source_drafts/` and
were folded into the matching controls without a redundant runtime run.
