# Local continuation: verified CLI capabilities and held handoff

The installed CLI is version 0.162.1. Its PowerShell/npm launcher forwards the
native exit status, and the installed native executable is at
`C:/Users/wheel/AppData/Roaming/npm/node_modules/@openai/codex/node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc/bin/codex.exe`
(SHA256 `dd13bdb162a184fa04039488b234a8258ef9b76f84e926c505d5742b19249a6a`).
Six help-only commands returned actual integer zero: top-level help, exec help,
exec-resume help, interactive-resume help, login help and debug help. No AI turn,
login, refresh, credential copy, app chat, scientific tool or runtime probe ran.
The new project discovery home remained empty. The local help receipts are
`work/codex_cli_discovery_v001/receipt.json`.

The Root-authorized mode-only observation confirms existing **ChatGPT** file
authentication, a tokens object and no API-key value. Credential values were
neither printed nor persisted. The allowed configuration preferences are
`model=gpt-6.1-sol` and `model_reasoning_effort=ultra`. No auth environment name
was present during discovery. `git check-ignore -z --stdin` confirmed all four
proposed private auth/session/log/temp test paths are ignored. The first
text-mode observer had Windows CRLF path suffixes and is preserved as not
evaluable; the corrected NUL-delimited observer returned actual zero.

Authentication reuse is feasible under Root's explicit project-copy decision,
but has not been performed. Before copying, create
`work/local_continuation/codex_home` with inheritance disabled and Full Control
only for the current Windows SID (and SYSTEM if required), then verify the ACL
and Git exclusion. Require ChatGPT mode and a null API-key field again; refuse
an existing destination. Copy the existing file read-only into this private
home without hashing, logging, manifesting or committing its contents. Original
authentication remains untouched; the CLI may refresh the project copy during
use. Availability and token refresh are untested, so an authentication failure
must stop locally without login, API-key fallback or repeated token attempts.
[Official authentication documentation](https://learn.chatgpt.com/docs/auth)
distinguishes subscription and API access, describes file/keyring/ephemeral
stores and documents automatic ChatGPT refresh.

Use process-local child environment entries, without changing HOME or global
settings:

```text
CODEX_HOME=<project>/work/local_continuation/codex_home
CODEX_SQLITE_HOME=<project>/work/local_continuation/codex_home/sqlite
TEMP=<project>/work/local_continuation/tmp
TMP=<project>/work/local_continuation/tmp
XDG_CACHE_HOME=<project>/work/local_continuation/cache
PYTHONDONTWRITEBYTECODE=1
```

Keep TEMP as a sibling of CODEX_HOME. The help-only test placed HOME below its
TEMP directory and the CLI consequently refused helper aliases; this warning
did not prevent help, but should not be repeated in the continuation layout.
Explicitly remove API-key/access-token environment overrides before the future
child starts. Default file authentication belongs to CODEX_HOME; changing home
alone does not inherit the original file. The private copy is Root's authorized
bridge. Keyring was not probed or assumed to share credentials across homes.
[State/configuration documentation](https://learn.chatgpt.com/docs/config-file/config-advanced)
places history, cached state and configuration under CODEX_HOME.

The minimal first-turn argument vector, passed as separate subprocess arguments
rather than interpolated shell code, is:

```text
<absolute-native-executable>
--no-daemon -C <absolute-project> -a never -s danger-full-access
-c forced_login_method="chatgpt"
-c cli_auth_credentials_store="file"
-c model="gpt-6.1-sol" -c model_reasoning_effort="ultra"
-c check_for_update_on_startup=false
-c log_dir="<private-home>/log" -c sqlite_home="<private-home>/sqlite"
exec --ignore-user-config --json
--output-last-message <event-directory>/last-message.txt -
```

This explicitly carries the current local approval/sandbox preference; project
scope and no-GitHub restrictions remain mandatory instructions, not an OS
write boundary under that policy. Root must freeze the handoff prompt before
launch. Keep the new home free of inherited MCP/plugin/global configuration.
Use persistent sessions, not `--ephemeral`; capture JSONL stdout and stderr only
under the ignored continuation directory. Save the `thread.started` UUID, and
later use the same global options followed by
`exec resume --ignore-user-config --json --output-last-message <file> <UUID> -`.
Use an exact UUID, not `--last`. The installed help confirms these capabilities;
[non-interactive documentation](https://learn.chatgpt.com/docs/non-interactive-mode)
describes JSONL and explicit-session resume.

A small native watcher can retain/creation-check the scientific process handle
and wait for its exit, with plain local file notifications for attention
receipts. Ordinary waits invoke no model. A persistent event claim and one OS
lock admit one headless turn for each new terminal/attention event; unknown
ownership or already-consumed claims block dispatch. The event prompt points
to current receipts and constraints, never credentials. The turn either
prepares/launches the next authorized bounded unit and records its exact owner,
or leaves a local held reason. The watcher then waits again. It must not send
messages to the app chat or create a scheduled prompt. A future start needs
Root's explicit ownership handoff so the current app agent and local agent do
not operate concurrently. No watcher or headless model turn has been built or
started by this discovery task.

The remaining gates are private ACL/copy review, exact bounded dispatcher and
handoff-prompt review, then one retained authenticated child invocation with
actual exit/history/storage evidence. No new API purchase or login is needed
by the proposed route, and neither is authorized as a fallback.

## Root bootstrap and concrete configuration update

After this discovery, Root completed the private ACL/exclusion and ChatGPT-only
copy. Its metadata-only evidence is
`evidence/local_continuation/private_bootstrap_metadata.json`, status
`PRIVATE_CHATGPT_ONLY_PROJECT_AUTH_COPY_READY`; original auth metadata remained
unchanged. The source-discovery agent did not perform or repeat that copy.

The prepared private invocation configuration is
`work/local_continuation/cli_invocation.json`, SHA256
`2d4502cf954ddd74133c34dc5e555495e980d30311d1c036b916a3aeffb025bd`.
It contains argv/environment configuration and no credential values or hashes.
The public `config/local_continuation_dispatcher.json` binds
`config/local_continuation_prompt_v001.md`. The seed handoff at
`state/local_continuation/handoff.json` waits for exact N5 native 10248, birth
`2026-10-27T10:19:07.2151764Z`, with its existing launch artifact. The initial
useful CLI turn is restricted to read-only reconciliation and a changed
WAITING_WORKER acknowledgment for that same owner. Root owns review and actual
launch. No AI invocation was performed by the configuration writers.
