# Persistent native ownership outside a tool-turn job

The read-only 2026-10-27 13:44:54 UTC observation found the current direct
project Python process and its PowerShell parent in a Windows job. Querying its
144-byte extended job structure returned flags `0x2800`:
`KILL_ON_JOB_CLOSE | BREAKAWAY_OK`, without silent breakaway. This makes a
reviewed explicit breakaway launch possible. It does not establish the exit
codes or exact cause of the earlier disappeared controllers. Those exits stay
UNKNOWN. The three surviving monitors were freshly observed in some job;
equivalence to the current tool job was not inferred.

`scripts/local_tree2_detached_launch_v001.py` launches a single reviewed native
entry with `CREATE_BREAKAWAY_FROM_JOB | CREATE_NEW_PROCESS_GROUP |
CREATE_NO_WINDOW`. It uses a native argument list and project-owned stdout and
stderr files, never inherited tool pipes, a shell, scheduler or global setting.
It first binds the executable, project entry source, full argument-vector SHA,
separate caller grant and configuration artifacts. The current job must allow
explicit breakaway or no job must exist. A scientific role additionally needs
its separately bound scientific admission; the legacy entry's Ready/resource/
once-claim gates remain mandatory.

The source supports persistent runtime controllers and scientific native
workers. Applying detachment only to the headless controller is insufficient:
a scientific worker launched inside a CLI tool's close-on-job-exit job can
also disappear when the model turn ends. Every future persistent native worker
must use this reviewed route, register canonical `native_owner`/worker aliases
with PID, exact seven-digit UTC birth and FILETIME, and prove
`child_in_any_job_at_registration=false`. Bounded foreground work retained to
its observed completion does not require an unobserved background lifetime.

Registration does not invent a child exit. The launcher closes its process
handle and explicitly clears Popen's child-tracking flag without setting a
return code, preventing destructor polling of a relinquished handle. A separate
retained OS observer must establish any actual exit. Fast helpers need their
own ACK barrier or retained exit recorder; their disappearance is insufficient.
An exclusive contract claim prevents automatic duplicates. Failed or unproved
registration records an unresolved launch; it does not kill or retry a child.

Six pure source fixture groups passed after the final source edits, actual
exit 0 in tool chunk `b5a51d`. They cover full argv integrity, admission/role
gates, creation flags/project streams/no-shell behavior, claim-before-spawn,
handle relinquishment without fabricated exit and bounded benign fixture
behavior. No controller, scientific worker or actual breakaway fixture was
started by the source author.

The HELD benign proof templates are
`metadata/local_tree2_detached_launch_v001/fixture_caller_grant_TEMPLATE.json`
and `fixture_contract_TEMPLATE.json`. Root creates separate admitted copies;
it must not overwrite the templates or bypass the caller grant. The admitted
contract status is `ROOT_ADMITTED_ONE_DETACHED_NATIVE_LAUNCH`, and its caller
grant binds `detached_launch_authorized=true`, exact role/source/argv hashes.
Then invoke the launcher with `--contract`, `--contract-sha256` and `--execute`.

The fixture writes only small owner/job/heartbeat JSON files for 60 seconds and
then exits normally. It launches no process, reads no auth, runs no science and
uses no termination API. Root should observe exact creation/job identity after
the launching tool has returned, and retain an OS handle if it wants actual
fixture exit 0. Later heartbeat growth can demonstrate survival beyond the
launcher lifetime. Cross-chat-turn survival is only an observed result after
that boundary, not a label inferred from a same-turn PID check. The initial
direct-job observation is preserved at
`evidence/local_continuation_persistence/read_only_job_metadata_v001.json`.
