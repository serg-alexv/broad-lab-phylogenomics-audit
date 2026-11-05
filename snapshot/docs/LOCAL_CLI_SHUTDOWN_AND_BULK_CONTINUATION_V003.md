# CLI shutdown boundary and bulk continuation

Root observed CLI 8084 emit its completed model turn at 12:24:37 UTC while the
native process remained alive with only a console child. The public retained
exit receipt records actual exit 130 at 12:56:10 UTC. This proves a post-turn
native shutdown problem; it does not identify the internal cause. The old
session/private log contents were not inspected by this source review.

The installed NGS plugin descriptor names `ngs-analysis-workbench`,
`ngs-compute` and `ngs-app`. Its Windows launcher can create a Python environment
and install dependencies before starting those services. These services are
unnecessary for this project's local filesystem/exec continuation. Their
startup is a source-supported opportunity to remove work, not a proved cause
of the old shutdown hang.

The chosen process-local fix is `--disable plugins` in both initial and resumed
CLI argument arrays. A bounded, empty-home, non-AI metadata command returned
actual 0 and `plugins stable false`, with no stderr. The new ignored config
`work/local_continuation/private_invocation_v003.json` has SHA256
`94ef185c8750519f3b86de0ea34a673378e6f112f9ddcd401243e35c0267a7d2`.
Removing those two added argument pairs exactly restores the previous config:
model, reasoning, authentication, environment paths and session preferences are
unchanged. No global plugin/configuration change or credential operation ran.

An earlier metadata-only attempt to add
`mcp_servers.node_repl.enabled=false` failed actual 1 because the isolated home
had no transport for that newly created server entry. That attempt is retained;
the incomplete override is excluded from the chosen config. No unsupported
server-identifier assumptions are needed. The installed feature flag and the
[official configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
support the selected disablement. The documented plugin-scoped server control
also exists, but was not used to guess a remote plugin policy key.

V3 separately bounds the native shutdown tail. A completed same-session JSONL
turn, changed event-matching validated handoff, exact retained CLI creation
identity and console-only descendant census are required before the 30-second
grace ends. A subsequent exact-handle teardown records its actual nonzero exit
130; it never relabels that exit as 0 or signals science. Unknown descendants,
incomplete model output, missing handoff or unknown closure stop recovery.
Disabling plugins is not substituted for this ownership boundary.

The new external supervisor owns only the V3 dispatcher child. It retains its
Popen/native handle, records the actual exit and closes that handle. One
explicitly enabled process repair requires an exact current-owner immutable
terminal error, source/config hashes and a stable structured root-cause claim.
The claim is persistent and at most one repair occurs in a supervisor lifetime.
The core then reattaches an exact live scientific worker or requires its prior
retained actual-exit receipt. PID disappearance never authorizes science replay.
Missing ownership/evidence leaves a local attention or unresolved-owner record.
The supervisor has no science, auth-read or process-kill route. Seven pure
source fixture groups passed; Root independently reviewed the authored
supervisor. The separate setup-agent review of the resolver-authored core is
independent; it explicitly excludes self-review of this supervisor.

Bulk work should continue through one sequential cohort queue using the proven
four-phase per-input method and the current accepted-result registry. Each
input's four real unit receipts and own-row feature result commit before the
next input. Completed accepted rows are reused by exact bindings, never rerun.
Each newly admitted cohort declares its own exact input set, remaining budget
and cold deadline; no prior unused allowance is borrowed. A failure stops the
cohort, preserves all phase/row commits and unknown debits, and emits one local
event for an operational repair decision after actual ownership closure. The
same dispatcher remains idle between meaningful events without model polling
or workchat prompts. This does not grant a new cohort or alter the active P20
sources/Ready. Source/taxonomy/pending masks and empirical coverage of missing
species labels remain mandatory; a numerical score cannot remove those holds.
