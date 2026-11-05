# CheckM2 Manager resource stop: source diagnosis only

The retry `20261026T223655Z-affb024a8930` was stopped by the controller's sampled sum-of-process-RSS guard. Its receipt records 3,114,455,040 bytes against a 2,147,483,648-byte threshold, minimum sampled Linux MemAvailable 2,864,295,936 bytes, exit −15, and an empty owned scientific group. There is no score or verified gene/DIAMOND checkpoint. This is evidence of a resource-policy stop, not evidence of a model prediction failure or a kernel out-of-memory kill. Full namespace/image/native closure remains the owner's separate gate.

## Fixed process overhead before gene work

In the verified original CheckM2 1.1.0 source:

| Source location | Consequence for one input bin |
|---|---|
| `predictQuality.py:87`, `modelProcessing.py:37–43` | Model construction precedes gene calling and loads both LightGBM models, the Keras model and the scaler. Keras/TensorFlow is already imported. |
| `predictQuality.py:388–396` | Nine separate `mp.Manager().dict()` calls start nine server processes. The count does not depend on bin count or `--threads`. |
| `predictQuality.py:401–415` | The gene phase additionally starts one progress writer and `total_threads` workers. At two threads, only one of those workers has the single bin; the other can consume a sentinel and exit. |
| `predictQuality.py:100–103,426,443–458` | The nine returned proxy objects remain referenced by the prediction workflow. The metadata phase creates one additional Manager plus its writer/workers. |
| CPython 3.12 `context.py:49–57,328`, `managers.py:555–562`, `popen_fork.py:66` | Each Manager starts a server using the multiprocessing context; the pinned Linux default is `fork`, whose implementation calls `os.fork`. |

The source-expected gene-phase topology is therefore the parent, nine Managers, one writer and one worker for `--threads 1`, or two workers for `--threads 2`: twelve or thirteen Python processes before transient external Prodigal/shell children. These are static maxima for that phase, not an observed per-PID census of the failed run. Queue feeder threads are not counted as extra processes. The later metadata phase can retain the original nine Manager proxies while adding another Manager and its workers/writer.

Under the pinned Linux default, these children can inherit the parent's already loaded ML address space. Summing their RSS can count shared resident pages repeatedly. That is a plausible explanation of the observed guard trip, not a measured diagnosis: the failed run retained no per-PID RSS/PSS/USS breakdown or actual start-method observation. Minimum system MemAvailable does not identify which pages were shared. The source alone cannot recover the missing physical-memory measurements.

## Supported options and their limits

`--threads 1` is the author's supported default and avoids one unnecessary gene worker for one bin. It leaves all nine Managers intact, so it is not a demonstrated solution to this stop. There is no advertised serial/in-process gene-caller option in the pinned argument parser or predictor code.

`--lowmem` changes the later DIAMOND block size from 2 to 0.5; it does not change this Manager/model-loading overhead. `--general` and `--specific` change final output selection but do not bypass model loading or both model computations in this source. `--ttable` can change Prodigal table selection but does not remove Managers. `--genes` is a supported protein-input route, not an equivalent switch for this nucleotide-input pilot; it bypasses gene calling and omits the nucleotide-derived report columns. `--resume` requires verified protein/DIAMOND intermediates that this failed run does not have. None should be silently substituted to evade the resource guard.

No source/binary/version/start-method change or resource-policy reinterpretation is admitted by this review. In particular, switching multiprocessing to spawn/forkserver is not an exposed CheckM2 option and would require a separate compatibility assessment.

## One bounded next diagnostic strategy for parent review

After full closure, consider one engineering-only reproduction of the original model preload and fixed Manager block under the same pinned runtime, IPC routing and unchanged 2 GiB summed-RSS stop rule. Read no genomes and call no Prodigal or DIAMOND. Record process creation identities, observed start method, per-PID RSS, PSS and private resident totals from `smaps_rollup` where available, with bounded reads and actual group closure. Stop at the existing guard even if all nine Managers have not started. Preserve unavailable measurements as unknown.

This would test the shared-page hypothesis without another biological prediction. Only those measurements could support a later explicit decision about process structure or memory accounting. Do not infer a lower physical-memory cost from the existing sum-RSS receipt, silently replace RSS with PSS, increase a budget, or automatically retry `--threads 1`. This paragraph is a proposed diagnostic, not authorization or execution.

The static audit receipt `evidence/checkm2_runtime/manager_resource_source_review.json` binds source hashes to cached official package payload metadata, Manager call counts, exact source locations and the failed execution receipt. The reviewer ran no scientific imports, mounts, models or predictions.
