# Independent review of the single ext4 recovery

Reviewed 2026-10-26 after the first private NTFS installation reached its one-hour deadline. This is a source/materialization and implementation review, not a filesystem capability proof, completed recovery, accepted runtime, or biological result. This reviewer has not formatted an image, configured a loop device, mounted a filesystem, or launched an installer.

## Source choice and measured footprint

Reuse the 133 accepted archives from `work/checkm2_resolution/channels/` and their fixed manifest SHA256 `a8cd65d5fc4d7294aa38d05412a41fc527530fa564b08cf8a6d0088abce70a52`. Feed the existing local explicit source list to Conda with a completely new image-owned package cache. Fresh extraction on ext4 avoids validating and copying the many-file partial NTFS cache. Do not accept an old prefix/cache merely because `info/index.json` or `info/repodata_record.json` exists; those files do not prove every payload member is complete and unmodified.

The accepted archive inventory records 55,551 regular members and 1,509 links. In particular:

| Package | Regular members | Unpacked regular bytes |
|---|---:|---:|
| libtensorflow_cc | 10,850 | 1,003,618,495 |
| tensorflow-base | 21,443 | 1,906,586,864 |

These two packages account for 32,293 files and 2.91GB of payload. This supports the observed DrvFS metadata/I/O explanation; improved ext4 performance remains an expectation until measured. Original archives contain 727,128,168 bytes; all unpacked regular members total 3,793,959,609 bytes. The conservative cache/extraction/prefix bound is 9,042,175,554 bytes. The already verified extracted database is 3,082,500,605 bytes, so their combined conservative footprint is 12,124,676,159 bytes. A 16GiB image has approximately 5.06GB remaining before filesystem metadata/reserved blocks. Admission must still measure internal free space and keep the existing 40GiB host-disk reserve.

## Reviewed draft layout and ownership

One setup owner proposes a new regular image `tools/checkm2_runtime_ext4.img`, created exclusively at 16GiB, and a new empty mountpoint `work/checkm2_runtime_mount`. Image subdirectories are `env/`, `pkgs/`, `tmp/` and `db/`. The image's env is privately bound onto the canonical Linux `tools/checkm2_env` path for both installation and reuse. This hides the preserved NTFS partial only inside the worker namespace and preserves Conda shebangs, library paths and CheckM2 defaults. The image database copy is privately bound read only onto its original canonical database file. Old project artifacts and host paths remain untouched underneath these private mounts.

The native driver must hold the sole recovery lock and verify the previous process identity/exit receipt, process-group closure and lock release. No second NTFS retry or simultaneous installer is authorized. Recovery uses the same accepted exact packages, official sources, original notices and database; no method/version substitution is introduced.

## Required image/device proof before execution

1. Resolve the exact project root and both proposed new paths. Reject symlink parents, existing image files, non-regular targets and multiply linked files. Create the image with exclusive/no-follow semantics and retain its open file descriptor. Record device/inode/size and verify them immediately before formatting. Format only this newly created verified regular image file, never a block device; keep the image descriptor open to detect replacement.
2. Configure only an existing device node whose opened descriptor is verified as loop major7. Use atomic `LOOP_CONFIGURE` with AUTOCLEAR and a zero-initialized structure. An occupied-device failure permits trying another existing free node, never clearing or changing an unrelated association. Keep the successfully configured loop descriptor open throughout the mount lifetime. Verify backing file device/inode, zero offset, bounded size, flags and actual block-device capacity, then verify the expected filesystem UUID/source/target after mounting. No device-node creation or global configuration change is part of this plan.
3. Run only after the existing private mount/network wrapper proves effective root/C/temp read-only mappings and the project/private registry mappings. The new image mountpoint must be empty and unmounted. Keep all cache, temporary, registry and model-library write paths inside the project/image. The source archives are reused by exact SHA256; newly materialized image-cache archives should match the same expected hashes/bytes.
4. Retain the original two-thread affinity, at least1GiB Linux headroom, at most2GiB sampled process-group RSS, host/internal disk checks, STOP handling, finite deadline and frequent native-identity progress. Preserve the old partial prefix/cache and failure receipts. A failed image recovery is preserved for diagnosis rather than silently formatted or retried.

The local Linux header `/usr/include/linux/loop.h` confirms LOOP_CONFIGURE0x4C0A, READ_ONLY1 and AUTOCLEAR4. Its structure layout is232 bytes for loop_info64 and304 bytes for loop_config on this host. No ioctl was issued by this review. The util-linux manual warns that a find-then-associate sequence is non-atomic, so an OS ownership lock and atomic configuration are preferable to relying on `losetup --find`. [losetup manual](https://man7.org/linux/man-pages/man8/losetup.8.html)

## Seal and subsequent read-only use

After all runtime/model gates and accepted manifests are complete, require ordinary successful unmount of the canonical bind mounts and image, followed by verified loop detachment. Lazy unmount or a successful detach command alone is not a clean-closure proof. Hash the image only after it is cleanly unmounted, and bind that final image SHA, UUID, exact image path, file identity, installed/model manifests and runtime receipt into READY. Native Windows streaming hashing can avoid DrvFS overhead; its progress must remain visible.

The first helper draft's read-only cleanup tried to unmount its raw-image file bind before closing the backing and loop descriptors. Those references hold that file mount busy. Required order is canonical env/database unmounts, ext4 filesystem unmount, loop/backing descriptor closure and verified AUTOCLEAR, then raw-image file-bind unmount. Both independent reviewers reported this to the owner before any image was executed. A read/write proof cannot validate this read-only teardown; include a sealed-image read-only open/close proof.

For each later pilot, verify the sealed image hash before attachment, protect the raw image path with a private read-only file bind, open its backing file read only, configure a read-only loop, and mount ext4 with `ro,noload,nodev,nosuid`. Keep execution enabled. Mounting ext4 with `ro` alone can still replay the journal and write; the kernel explicitly recommends `ro,noload` to prevent that. [Linux ext4 documentation](https://docs.kernel.org/admin-guide/ext4.html)

Re-establish the same canonical env/database paths, and verify effective mount flags, filesystem UUID/source, executables, all nine external assets, model/installed manifests and database inside that namespace. The Windows-visible old `tools/checkm2_env` directory is not this image runtime. READY must declare that a private image mount is required. Hash the image after pilot closure to verify it remained unchanged. Failure, missing metadata, unexecuted predictions and unresolved results remain distinct from biological absence.
