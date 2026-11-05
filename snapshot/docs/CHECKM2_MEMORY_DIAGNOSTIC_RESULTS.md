# Closed engineering memory observations

The single admitted protocol finished at 2026-10-26 23:32:07 UTC. Both arms used
the unchanged effective runtime, exact model initialization, default fork, two-CPU
affinity, 2 GiB summed-RSS stop and 1 GiB available-memory headroom. No genome,
FAA, author worker/writer, Prodigal, DIAMOND or model prediction was run.

| Engineering arm | Actual outcome | Peak summed RSS | Measurement time |
|---|---|---:|---:|
| Up to nine Managers after model load | Stopped at unchanged RSS gate after six Managers started | 2,226,548,736 B | 18.25 s |
| One Manager plus two stdlib held children | All declared four-process topology steps recorded | 1,360,785,408 B | 8.39 s |

The primary's last safe held snapshot, at five Managers plus the parent, had
1,932,972,032 B summed RSS and 482,101,248 B summed PSS for the same six PIDs.
The models-only parent had 464,683,008 B RSS and 463,089,664 B PSS. The comparison's
held four-PID snapshot had 1,346,547,712 B RSS and 476,033,024 B PSS. PSS/private
fields were complete at all eleven held steps. These observations support
substantial shared-page amplification of the summed RSS metric. Linux available
memory stayed above 2,907,783,168 B. PSS did not replace the original safety gate.
The peak totals include the bounded descriptive observer when it was active;
held same-PID snapshots precede that observer.

Both targets returned 0 with empty owned groups. The primary's resource stop was
explicitly an engineering outcome. The supervised WSL child and retained native
execution session 43159 returned actual exit code 0. All 22 observed Linux process
identities were independently absent, the image had no remaining loop association,
and the common native, setup and Linux compute locks were exclusively reacquired
and released. IPC, overlay and image ordinary unmount receipts passed. The clean
image SHA256 remained `c40e6918…`; the shared registry and biological STOP marker
were unchanged. The GUI's strict source-path matcher could not fully verify the
historical relative script argument; future launchers must use an absolute script
path. Actual native/WSL creation identities, exit codes, group and lock evidence
are preserved independently; the matcher was not relaxed.

Exact execution evidence is `evidence/checkm2_memory_diagnostic/execution.json`
(SHA256 `22f45d529208178f9134d043b5b89186e97e395e904d4825392e10f63873e96d`).
Same-PID held metrics are in `summary.json` (SHA256
`586240063bdd93039cf7783300d2d6271d9702233778f419d5f79424c2d77b2f`).
The native and Linux independent closure receipts are in that same directory.

The smaller process topology is a candidate for separate supported protein-route
validation. Actual metadata callbacks, nonempty genome data, DIAMOND/model-stage
peaks, real quality scores and full panel behavior remain unmeasured by this
protocol. No biological QC or production acceptance follows from these results.
The biological STOP marker remains in place. No forkserver, reducer/class patch,
extra protocol, budget increase or metric substitution was performed.
