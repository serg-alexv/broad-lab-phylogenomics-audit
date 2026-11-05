# CheckM2 IPC temp routing: independent static review

The first biological resource pilot failed before gene calling because its Python multiprocessing Manager tried to create a pathname Unix-domain socket under a long temporary path. Its failure is preserved; this review runs no imports of scientific tools, predictions, mounts or additional pilot attempts.

## Blocking interaction in the unchanged author code

The pinned CheckM2 1.1.0 `main.py`, lines 38–40, sets `tempfile.tempdir = newtmpdir` in the argparse action for `--tmpdir`. Consequently, setting `TMPDIR`, `TMP` and `TEMP` to a short alias before Python starts does not suffice while the unchanged `--tmpdir` points to a long durable project directory. The client also previously reset those environment variables to the long project path immediately before target Python; its owner must remove that integration conflict.

Redirecting all scientific temporary files to the permitted 32 MiB IPC tmpfs is also inadmissible. The pinned `diamond.py` uses `NamedTemporaryFile` and `TemporaryDirectory` for protein input and DIAMOND scratch and explicitly requires at least 500 MiB free in `tempfile.gettempdir()`. The pinned `prodigal.py` can use `mkdtemp` for compressed input. Durable `--tmpdir`, run outputs and scientific scratch must retain project storage.

The source audit binds eight cached CheckM2/CPython files to their package `info/paths.json` SHA/size records. The CheckM2 main source also matches the independently preserved hash `28bb95e55b3878f2f35f40231d0a254b45f9864c8490d547909616b74d015160`. This is a static source check, not a fresh archive rehash or a runtime pass. Evidence: `evidence/checkm2_runtime/ipc_temp_routing_source_review.json`.

## One narrow capability-tested route

CPython 3.12 `multiprocessing.util.get_temp_dir()` creates and caches an IPC directory separately in the current process configuration. `multiprocessing.connection.arbitrary_address(AF_UNIX)` explicitly requests its socket name within that cached directory. Prewarming this existing stdlib function in the target interpreter while `/tmp` is privately mapped can therefore separate short IPC names from the ordinary scientific `tempfile` directory that the unchanged author CLI sets later.

Prefer a new small process-local outer entry that validates the mapped IPC alias, performs that prewarm, and invokes the already validated effective bootstrap in the same interpreter with unchanged CheckM2 arguments. Keep the accepted bootstrap and its source hash unchanged. Bind the new entry, IPC proof and routing choice into a separate launch-plumbing record. No author code, binary, model, dependency version, global setting or immutable image needs to change. This is a proposed route until its real capability proof passes.

The proof must use the actual pinned Python 3.12 and execute the order that matters: prewarm under the short alias, then emulate the author's long durable `tempfile.tempdir` assignment, then perform a real Manager dictionary roundtrip. It must show the actual Manager socket remains under the short cached IPC directory while an ordinary temporary file lands in durable project scratch. A direct AF_UNIX bind/connect proof and a pathname bound of at most 107 encoded bytes are required as well.

Try the project-backed private `/tmp` alias first. Only the explicitly allowed unsupported-socket error from that direct bind test may admit the one 32 MiB private tmpfs fallback. The latter must be mounted at a new owned project mountpoint and privately bound over the existing `/tmp`, with `nodev,nosuid,noexec`. Other errors remain failures. All proof children and Managers must close, aliases must unmount in reverse order, original mount mappings must return, and the sealed read-only runtime must close with its image hash unchanged. No pilot retry follows merely from this static review.

## Draft admission review

The separate IPC alias, target outer bootstrap, Linux proof controller, native proof controller and shell entry were read without execution. Their draft normal path implements the separation described above, including the real Manager after a deliberately long scientific-temp override. The exact reviewed source hashes and conditional admission are recorded in `evidence/checkm2_runtime/ipc_alias_source_admission_review.json`.

Static decision: the owner may run the single bounded capability proof after the failed baseline's full closure is admitted. This is not a runtime pass or permission to skip any proof, closure, resource or unchanged-image gate. A genome retry still requires the successful capability receipt and separately reviewed consumer binding. The reviewer performed no mounts, tool imports or pilot executions.
