# CheckM2 CPU dependency resolution

Resolution completed2026-10-26T18:03:57Z. This is an audited software dependency plan, not an installed environment and not a genome-quality result.

The successful plan has133 packages totaling727,128,168 compressed bytes. Every exact official-channel URL, version, build, dependency record, license label and SHA256 is retained in `evidence/checkm2_runtime/resolved_packages.json`; its SHA256 is `a8cd65d5fc4d7294aa38d05412a41fc527530fa564b08cf8a6d0088abce70a52`. The explicit source list is `checkm2_cpu_explicit_sources.txt` in the same folder. This source list is not an offline-install file until package bytes are cached and verified. Unpacked size has not been measured.

The solver ran only inside the verified private mount and network namespace. Windows fetched a bounded set of missing historical metadata from official Anaconda release APIs; no GitHub request, model upload, virtual-CPU override or GPU dependency was used. The host conda registry hash, size, modification timestamp and canary absence matched before/after every attempt. `resolve_execution_receipt.json` records the successful native worker and closure.

Actual host virtual architecture is `__archspec=1=skylake`; AVX2/v3 feature support was independently checked. The selected TensorFlow2.19.1 baseline CPU build5 explicitly requires microarchitecture level>=1. The package-provider pin `3=5_skylake` matches the real CPU and prevents any level4-only dependency. Hardware metadata compatibility is not a runtime-test result.

Earlier attempts are retained: cold `--offline` mode skipped uncached file-channel metadata; current_repodata omitted TensorBoard/libtensorflow historical dependencies; and current metadata omitted level3 providers while retaining level4 providers. No scientific method/version substitution or CPU spoof was used to correct these engineering problems. Exact historical CPU records and source-response hashes are retained in `metadata_supplement.json` and `work/checkm2_resolution/anaconda_api/`.

## Exact principal pins

- _x86_64-microarch-level: `3 5_skylake`
- checkm2: `1.1.0 pyhdfd78af_2`
- diamond: `2.1.11 h5ca1c30_2`
- keras: `3.15.1 pyh753f3f9_0`
- lightgbm: `4.7.0 cpu_py_h6f8b580_8`
- numpy: `2.5.4 py312he827f4e_0`
- pandas: `3.1.0 np2py312h91ec553_0`
- python: `3.12.16 h5f976f7_0_cpython`
- scikit-learn: `1.9.1 np2py312h91ec553_1`
- scipy: `1.18.1 py312h106c528_2`
- tensorflow: `2.19.1 cpu_py312h3336143_5`
- tensorflow-base: `2.19.1 cpu_py312h9edca52_5`

## Next gates

Download only these exact URLs through Windows, verify expected SHA256 and bytes, inspect unpacked sizes/path safety and retain every original notice. Install only through the proven project-private namespace and project prefix/cache; no unguarded conda entrypoint. Then verify tool/model loads before the documented bounded one-genome CheckM2 resource pilot. Current Keras/NumPy/scikit-learn versions are solver-compatible with package metadata but pretrained-model/runtime compatibility is still untested. Do not call an accepted dependency solve a ready runtime or biological QC pass.
