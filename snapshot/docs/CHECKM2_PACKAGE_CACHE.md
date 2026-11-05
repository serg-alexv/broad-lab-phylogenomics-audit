# Exact CheckM2 runtime source cache

Completed 2026-10-26T18:38:50Z. This is source acquisition and archive inspection; it does not establish that the runtime loads, that pretrained models are compatible, or that any genome passed independent quality control.

The fixed 133-package closure was acquired from the exact official conda-forge/Bioconda HTTPS URLs in `evidence/checkm2_runtime/resolved_packages.json` (SHA256 `a8cd65d5fc4d7294aa38d05412a41fc527530fa564b08cf8a6d0088abce70a52`). Each archive's compressed byte count, SHA256 and MD5 were verified. No redirect was followed, no GitHub source was fetched, and no conda entrypoint or installer was invoked by the cache worker.

| Measurement | Bytes |
|---|---:|
| Compressed archives | 727,128,168 |
| Unpacked regular members, including original info | 3,793,959,609 |
| Conservative cache + extraction + prefix footprint | 9,042,175,554 |

Archives live under `work/checkm2_resolution/channels/<channel>/<subdir>/`. The offline explicit list is `evidence/checkm2_runtime/checkm2_cpu_explicit_offline.txt`, SHA256 `895a41298b388db770693c258c87d982f0e9b4b0e1d8ea8c73f2aba059424bdc`. `cache_handoff.json` binds that list, the resolved manifest, package-cache receipt and full size/notice manifest by SHA256. The notices manifest is `package_size_and_notices.json`, SHA256 `d1e3ddd1627380c50af1a02486168b0c4bd5c9906fb74566a118e3d99b4bfec7`.

Every original `info/*` regular member and detected payload license, copyright, COPYING and NOTICE file is preserved byte-for-byte under `tools/checkm2_package_notices/<archive>/objects/`. Per-package `inspection.json` maps each original path to its object, byte count and SHA256. The complete member inventory preserves original paths, modes and link targets; original archives retain every source byte. No package payload was extracted into an environment. Independently reading the preserved original `info/index.json` found all 133 identities and dependency lists equal to the solved records; `cache_independent_audit.json` records this check.

There are zero links outside the package prefix, and three real case-only filename pairs in ncurses: `share/terminfo/68/hp70092a`/`hp70092A`, `share/terminfo/68/hp2621a`/`hp2621A`, and `share/terminfo/32/2621a`/`2621A`. The installer must prove case-sensitive project-owned extraction and prefix directories before linking these packages. Source notices use content objects, so these source filenames were not collapsed during inspection.

The Windows controller uses one worker, a native process identity, an OS-held lock, atomic partial-to-archive publication, disk-reserve checks and the project's STOP flag. HTTP range continuation requires a matching ETag and Content-Range; those HTTP interruption branches were implemented but not exercised by this run. A real failed-stage resume was exercised: the first controller finished all downloads before its inspection script had been saved, closed FAILED, and preserved its error receipt. The second controller reused all 133 archives only after SHA256 checks, performed no network redownload, and completed inspection. The first receipt remains `cache_execution_receipt.initial_cache_only.json`; the successful final worker was PID12820, creation2026-10-26T18:35:58.5854102Z, closed2026-10-26T18:38:50.667691Z. The append-only event journal retains both attempts.

The cache handoff permits only the next engineering gate: installation through the proven private mount/network namespace, with the measured footprint and case-sensitive paths. Runtime imports, exact versions, model/scaler loading, warning review and the bounded scientific pilot remain separate gates. Source caching must never be treated as an accepted environment or a biological negative call.
