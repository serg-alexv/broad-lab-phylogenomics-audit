# One non-genomic observer diagnostic

The single authorized dummy protocol passed on2026-10-27. Native8160, birth03:15:44.4697932Z, exited0 as observed by the foreground execution tool; its WSL client21528 also exited0. Native elapsed time was4.485seconds; the Linux protocol used4.010seconds, two affinity CPUs, observed maximum parent-plus-child-group RSS33,894,400bytes and minimum Linux available memory3,281,215,488bytes. The source limits were60seconds native/45seconds Linux,2GiB summed RSS,1GiB Linux headroom and40GiB disk reserve.

Two injected cases reproduced the source hazard. An unguarded optional JSON read raised FileNotFoundError or JSONDecodeError while its harmless sleeping child was still live. The external harness retained each handle and observed actual child exit0 and an empty process group. This demonstrates that the original loop can escape ownership; it does not prove the historical benchmark's missing-file cause or a DrvFS replacement race.

The candidate used the exact shared `scripts/checkm2_optional_telemetry_v001.py`, SHA `561164f65f9ee0dd312cb7fd365312cc0a46c86485a3218382add15b630903ef`. Its reader preserved only the matching owner cache, recorded full exception details, survived injected missing/malformed telemetry, accepted the later matching snapshot, and retained the child until an owned dummy STOP requested closure. The retained Popen handle observed SIGTERM exit-15 and an empty group. A separate required-evidence read remained fatal and likewise closed/reaped its harmless child; no missing required evidence was filled or accepted.

The helper's reusable interface is `read_optional_telemetry(path, expected_token, cached=None, token_field='windows_launch_token') -> (snapshot, diagnostic_or_None)`. It applies only to optional progress. It must not replace strict request, Ready, input, terminal-unit, manifest or closure reads. `structured_exception` records exception type/str/repr, errno, filename/filename2, operation path and full traceback. The diagnostic exercised these exact bytes using a distinct dummy-owner field.

No runtime image, private IPC, scientific runtime, genome, FAA, model or pickle was opened. There was no spontaneous filesystem stress test. The actual stage04, benchmark STEP and Ready hashes remained unchanged, as did all37 old source pins. No benchmark, annotation, model, recovery or retry was dispatched. A subsequent independent probe confirmed both Windows identities, the Linux owner and all four harmless-child identities/groups were absent.

Evidence folder: `evidence/observer_diagnostic_v001/d791d2f28bf2431a8909bb6721ca8b78`.

- `linux_result.json` SHA `7462b702797c98cd30950cc060e5f1e9a40c6af1893104453a024da04c91cecb`.
- `external_closure.json` SHA `a8f7cf635403eb083f0ebe13a843528eba87525c107d8e6b19c40ada5cd2a012`.
- `checkpoints/observer_diagnostic_closed_20261027T031600Z/receipt.json`,16files, SHA `6d63f6c965cdf2beedf7f7cc10464a96f9be5eed04fe4ec10234b58f83d4721f`.

The failed annotation remains uncommitted with unknown exit/debit evidence. This engineering result grants no scientific continuation or budget reset.
