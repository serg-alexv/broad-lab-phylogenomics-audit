# T1 exact fatal-cleanup guard: one non-genomic proof

The Root-admitted fixture ran once with frozen guard SHA `874abacc2035073cc5952301b51ca90b86909e4a4e446d18953a899034977b8f` and fixture SHA `48aac63b9852c5e96f19f1955aacfe4c122bd7a049ea0ee77beaa1cb7c185ce3`. Admission SHA was `0f25d0c43630f7fa1f18a0636d9602a6da51c1e66af913deff4b858f5601936c`. No scientific workflow was admitted or dispatched by this proof.

Native owner21880 (birth2026-10-27T03:44:43.6971543Z), WSL client23028 and the Linux fixture worker all exited0. The native exit was observed through retained foreground session72038, independently of its own pending-self-exit receipt. Native elapsed time was35.953seconds. The exact cleanup function ran35.203seconds, with first TERM at30.004474seconds and first KILL at35.000875seconds. It entered all three declared30/5/5second cleanup windows and returned as soon as the owned tasks closed.

The harmless helper and its descendant deliberately ignored dummy STOP and TERM. The descendant used a distinct Unix process group/session. Each TERM/KILL was sent leaf first through a pidfd opened for that task, after checking PID, boot ID and creation ticks against the captured identity. No name, stale process group or WSL-client signal was used. The retained helper handle was reaped with actual exit-9. The descendant's exact identity/group disappeared; its exit code was not directly observed because the fixture had no parent wait handle for it.

A sibling sentinel was supplied to the guard with deliberately mismatched creation ticks. The guard never signaled it; it survived the guard and its actual owner later reaped it with exit-15. A missing required dummy evidence file remained fatal, with full filename/errno/traceback retained. The forced path correctly kept ordinary scientific/runtime closure UNKNOWN and wrote an immutable dummy handoff plus a hard no-relaunch marker under the fixture's own workspace. Those are test artifacts, not actual T1 STOP or handoff files.

The Linux supervisor continuously checked the fixed workload. Peak summed RSS was85,225,472bytes, minimum Linux available memory3,242,852,352bytes, and minimum disk free162,653,192,192bytes. Two affinity CPUs and an inherited256MiB per-process address-space limit were applied; the declared group ceiling remained2GiB, headroom1GiB and disk reserve40GiB. Total budgets were60seconds native and50seconds Linux supervisor.

An external post-exit probe confirmed both original Windows identities, the Linux supervisor, worker, helper, descendant and sentinel identities/groups absent. A26-file checkpoint preserves source, commands, all dummy programs/markers, actual output and closure evidence. No image, private IPC, scientific runtime, model, genome, FAA, pickle, real STEP, Ready or T1 STOP was used. There was no repeated fixture or scientific retry.

The standard stage04 row was temporarily registered as NON_GENOMIC_FATAL_CLEANUP_DIAGNOSTIC with the actual native owner and null dummy counters. Its prior bytes were preserved. Only after actual closure was it replaced with PENDING_REPAIR_REVIEW,0/10 benchmark annotation commits and no PID. This proof does not promote the earlier uncommitted annotation or grant production, continuation or a new scientific attempt.

Evidence folder: `evidence/owned_cleanup_T1_fixture/3242aba302f04b098fca0a92c03cffbb`.

- `external_closure.json` SHA `fb0d06960f41b08b84359963d2de9c153adcf023a49b7673dd36f9337ae18f87`.
- `checkpoints/owned_cleanup_fixture_closed_20261027T034600Z/receipt.json` SHA `bfeb69bc47d3418d66d538b55f4f059d9de6ace646c7fbcfb817a0558d2439d3`.
