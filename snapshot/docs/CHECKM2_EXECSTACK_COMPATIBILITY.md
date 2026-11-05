# TensorFlow/glibc startup compatibility diagnosis

Static and loader-only evidence collected 2026-10-26. No TensorFlow import, image mount, installation, package patch or genome prediction was performed by this reviewer. This document proposes a bounded owner-only compatibility smoke; it does not accept the runtime.

The first image installation completed all 133 packages, but the first CheckM2 CLI import failed when glibc refused the executable-stack requirement of `libtensorflow_cc.so.2`. Independent inspection streamed ELF headers directly from the unchanged SHA256-verified official package archives:

| Exact source | Archive member | PT_GNU_STACK |
|---|---|---|
| libtensorflow_cc 2.19.1 cpu_ha812d39_5 | lib/libtensorflow_cc.so.2.19.1 | flags7: read/write/execute |
| Python 3.12.16 h5f976f7_0_cpython | bin/python3.12 | flags6: read/write |

The TensorFlow library member is 642,178,800 bytes. Its archive SHA256 is `324ca9745318b6ea5d4b208bfea2ac81005289cd339ddb0dcce850ceca61acbb`; Python's archive SHA256 is `a40188b47c3995bc42a33820be4d780af5c11cc295409413fb925549f0abfe92`. The audit binds ELF header hashes, exact versions/builds, machine architecture, host loader/libc hashes and commands in `evidence/checkm2_runtime/loader_compatibility_source_audit.json`.

The official GNU manual documents `glibc.rtld.execstack=2` as a process-start compatibility mode for dynamically loaded modules requiring executable stacks. The normal value1 follows initial ELF requirements; it does not make a non-executable initial stack eligible for this later dlopen requirement. The documented value2 establishes an executable stack at startup. [GNU dynamic-linking tunables](https://sourceware.org/glibc/manual/2.42/html_node/Dynamic-Linking-Tunables.html)

The authoring glibc commit explicitly describes the compatibility problem and the tradeoff: this mode relaxes executable-stack hardening for the selected process. It does not require changing the shared library or a system configuration file. [glibc implementation and tests, commit b861755a84eeccdd9183989ca71b3b1251c83a74](https://sourceware.org/pipermail/glibc-cvs/2025q2/087912.html)

Live host loader identification is Ubuntu GLIBC2.43-2ubuntu2.4. The loader's own `--list-tunables` reports `glibc.rtld.execstack:1 (min:0,max:2)` with the normal environment. A separate benign loader-only process started with `GLIBC_TUNABLES=glibc.rtld.execstack=2` reports value2. These observations verify recognition of the candidate on this host, not successful loading or scientific compatibility of TensorFlow.

The setting must be supplied before execution of every Python/CheckM2 process that requires it. Setting `os.environ` after Python has started cannot retroactively change its loader startup policy. Scope the environment override to the trusted smoke/prediction processes, record its child inheritance, and bind it into runtime/pilot provenance. Leave global loader configuration, package versions, source bytes and ELF permissions untouched. Do not clear an executable-stack bit or infer that it is unnecessary from this diagnostic alone.

The owner may reuse the completed exact package prefix for a new smoke-only continuation, with no second installation. First bind a new non-READY seal to the actual clean failed-install image closure; the old preparation seal describes different image bytes. Re-establish the proven private namespace, canonical env/database binds, existing resource limits, hash/version checks and warning retention. Then test the CLI/import/model/author-database gates with the startup-only environment override. Failure stays unresolved; success must still pass clean read-only persistence and the separate bounded scientific resource pilot before any production QC acceptance.
