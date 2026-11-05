# Bounded end-to-end control specification

Source-only specification,2026-10-26/27. No control execution, prediction, import, mount or runtime change is performed by this review. Run only after the current single-genome owner has closed; do not overlap scientific workers.

## Direct evidence and missing numerical reference

The pinned official CheckM2 archive SHA256 is `1af64d8c354104818d0b7d4fbc23c7c875e8a8b73f2541ecf1d39b90385f27d2`. Its `checkm2/main.py` SHA256 is `28bb95e55b3878f2f35f40231d0a254b45f9864c8490d547909616b74d015160`. Lines240–266 implement `testrun`: input checksums are checked, prediction runs, and a success message is printed when the report has more than one row. There is no expected numerical estimate or tolerance in this test. A logged failure in that final branch is not itself an explicit nonzero exit. The preserved Bioconda recipe tests only `checkm2 --help`.

Three bundled controls are source-bound in `evidence/checkm2_runtime/scaler_static_compatibility_review.json`:

| Input | Bytes | SHA256 |
|---|---:|---|
| TEST1.tst | 5,222,720 | f097f8a99ad692f26b758387c5374f426017eaf9251a41f35d5bf77e1bd8bc5a |
| TEST2.tst | 743,046 | a91663bb71937d539e3f55cedd0709be1cd4aaa3e1c95b30b985691108977acc |
| TEST3.tst | 1,132,615 | 53d80449105af334d523cda16803fc1ae9247f3f463468eed857f6ca466bfee2 |

No numerical truth/range was established from this inspected test branch, bundled controls or preserved recipe. This does not prove that no author reference exists elsewhere; the external author repository was not accessed under the project's NO GITHUB restriction. File integrity and row-count success do not supply missing biological ground truth. Do not use source NCBI CheckM values or an unsupported-version inference as truth.

## One proposed perturbation control

Use the already admitted, checksum-bound single-genome pilot input. Create one alternate FASTA by changing sequence-line wrapping only, retaining exact header text, record order and per-record sequence bytes. Before launching, prove equality of the normalized ordered header/sequence hashes and record/base counts; only newline positions may differ. Keep the same sample basename/identifier, exact effective runtime/bootstrap/model/database hashes, translation mode,2threads, supported low-memory options and all other parameters. Use new project-owned output/temp directories and preserve both inputs and all intermediate/output receipts. Never overwrite the completed baseline or rerun it unnecessarily.

This is one additional prediction with the existing600s prediction deadline,2GiB sampled owned-group RSS maximum,1GiB Linux headroom and40GiB disk reserve. A resource failure remains unresolved; do not increase budgets or retry automatically. No genome acquisition, altered biological content, model retraining, source patch or dependency change belongs to this control.

Predeclare the comparisons before execution:

- Normalized predicted protein identifiers/sequences and canonicalized DIAMOND records must match exactly. Raw feature vectors must also match exactly, with identical feature order, only if both artifacts were actually collected. The admitted baseline has `--debug` without `--dbg_vectors`; absent dumps must be reported `NOT_COLLECTED_NO_FEATURE_EQUIVALENCE_CLAIM`, not invented or obtained by silently rerunning the baseline. Canonicalize only output row ordering and explicitly variable run paths, never scientific values.
- Report schema, sample identifier, translation table and selected completeness-model label must match. Completeness and contamination must each differ by at most0.01 percentage point, a single reported two-decimal unit; preserve any higher-precision debug output and differences.
- Any missing/nonfinite value, unexpected warning, differing features/model choice, resource/closure failure or unmatched binding fails this control. Hash all committed evidence and prove clean namespace/loop closure and unchanged sealed image/overlay.

The tolerance is a predeclared engineering repeatability criterion, not a claim of biological accuracy or model error. Identical sequence input with different wrapping probes the parsing/staging/prediction path; it cannot validate absolute completeness/contamination, calibrate a taxon, replace version-matched numerical references or grant production acceptance. Even a pass leaves official numerical-ground-truth validation unresolved unless an independently trustworthy matching-version/database reference is obtained and reviewed.
