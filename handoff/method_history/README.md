# Historic method sources

`tree2_method_history.zip` contains the method path history of all 272 commits reachable from the frozen Tree 2 HEAD. `COMMITTED.json` records the archive SHA256, the exact revision, coverage, and filter rules.

Start with `lineage.ndjson` inside the ZIP. A revision record identifies the commit and its parents. Version and deletion records describe method path changes against the first parent. Each retained version records the original Git blob ID, SHA256 of the exact source bytes, byte count and either an archive path or a main-package alias.

Archived blobs are stored once under `blobs/<SHA256>`. An alias under `current_package_member` points to the same bytes in the main audit package. Resolve it against the combined `files.ndjson` by path, SHA256 and byte count. If a distribution omits that combined file, use the ordered per-group manifests referenced by `package_index.json`. Those manifests supply the same member records.

Coverage includes `scripts/`, `docs/`, `config/`, `patches/` and named root method records. The export retains original bytes, including Windows paths and line endings where present. It does not export the Git database, commit messages, unreachable commits, private/runtime material or histories of helpers outside those roots. These historical sources describe earlier runs and require the pinned inputs and a fresh execution environment to reproduce them.

The exporter re-read the ZIP and checked each archived blob and lineage reference. The main package verifier checks the distributed copies of the alias targets.
