# Prepared FASTA wrapping control implementation

Status: source prepared and tested; adaptor not applied; real input not transformed;
no control prediction executed. The required successful, fully closed baseline
does not exist. The latest resource pilot stopped at the declared memory gate
without a quality report. This control remains held.

`metadata/checkm2_end_to_end_control_spec.json` preserves the accepted specification.
`scripts/checkm2_fasta_invariance.py` provides prepare, validate and compare commands
using only the standard library. Preparation accepts a successful baseline only
after its output manifest and namespace/image closure hashes verify. It snapshots
the baseline pointers and receipts, exclusively creates one `v001-<binding>`
workspace under `analysis/checkm2_fasta_invariance`, and derives a new 61-column,
LF-terminated FASTA. Original header bytes, record order and concatenated sequence
bytes including case must match per record and as an ordered digest. The original
acquisition FASTA is never edited. A no-op transformation stops without choosing
another perturbation. The implementation workspace follows the owner's newer
dedicated-path instruction; the original specification remains unchanged.

The final review-only adaptor is
`patches/checkm2_fasta_invariance_input_plan_v005.patch`. Its basis is the exact
three active files from checkpoint `bacf134`; their hashes and preview hashes are
in `metadata/checkm2_fasta_adapter_preview_v005.json`. It has not been applied.
The repository pins raw bytes with `* -text`, so the patch preserves the original
CRLF context lines. Default `git apply --check`, Python parsing and PowerShell
parsing pass. The scientific `prediction()` function's AST is unchanged.

The adaptor adds native `-InputPlanPath`, freezes the plan/helper/handoff hashes
in the immutable token request, and forwards `--input-plan` plus its hash to the
same guarded controller. It uses the original accession filename, unchanged
effective bootstrap, models, database, IPC routing, two CPUs, 600-second prediction
bound, 2 GiB sampled group RSS, 1 GiB headroom and 40 GiB disk reserve. Runtime and
options must equal the baseline after excluding per-launch mount/IPC identities.
Native and Linux compute locks remain common to baseline and control. Control
progress, native launch/exit state, namespace receipts and results use dedicated
paths; the baseline analysis and state remain preserved. One immutable prediction
claim forbids another attempt, resume, overwrite or resource escalation.

The future baseline owner must first prove native process/descendant closure and
exclusive lock release, then review the generated plan and write the atomic
`state/checkm2_fasta_control_handoff.json` with these bound fields:

```json
{
  "status": "BASELINE_CLOSED_CONTROL_HANDOFF",
  "baseline_launch_token": "<successful baseline token>",
  "baseline_namespace_sha256": "<verified envelope SHA256>",
  "baseline_latest_sha256": "<preserved latest pointer SHA256>",
  "native_baseline_closed": true,
  "native_launcher_lock_released": true,
  "compute_lock_released": true,
  "input_plan_sha256": "<reviewed immutable plan SHA256>"
}
```

No such success handoff has been created. Integration and execution require the
owner's post-closure review. The monitor publisher must observe the dedicated
`state/checkm2_fasta_invariance_progress.json` before a future control launch.

Comparison requires a distinct control run in its declared workspace, the exact
derived/original input bindings, equal runtime/options, exit code 0, closed group,
and valid baseline/control manifests. Ordered protein identifiers and amino-acid
sequences must match exactly after FASTA line-wrap normalization. DIAMOND's full
12-column row multiset must match, ignoring row order and retaining duplicates.
Name, selected model, translation table, notes and all five required integer metrics must
match. Completeness and contamination may differ by at most 0.01 percentage point.
Both absent feature-vector dumps are explicitly `NOT_COLLECTED`; no feature-layer
equivalence is inferred. Missing, malformed or unmatched evidence holds the
diagnostic. Cached success also requires the comparison artifact's SHA256, plan
binding and status to verify; corruption cannot trigger a prediction retry.

Ten meaningful synthetic fixtures pass: exact-case/header/order preservation,
61-column formatting, overwrite/no-op refusal, malformed input rejection, protein
order/duplicate handling, DIAMOND row-order/multiplicity/nonfinite handling,
Decimal tolerance/model/table checks, path/second-attempt guards, baseline-as-own-
control rejection, missing integer metrics from both reports, and cached-comparison corruption rejection. These fixtures use
project-owned temporary files only. They call no scientific program or real genome.

A passing future control establishes parsing/pipeline repeatability. It supplies
no independent biological truth, source-score calibration, genome acceptance or
production panel acceptance.
