# 04R1 attempt: raw estimate produced; feature validation held

The one admitted stock protein-input pilot completed its annotation and CheckM2 computation under the unchanged resource limits. Its raw report contains **99.02% completeness and 0.35% contamination** for `GCF_013267415.1`. These estimates remain held because the v001 feature validator incorrectly restricted KO module means to 0–1. No quality, cohort, taxonomy, defence or production acceptance follows from this raw report.

| Declared work | Actual outcome | Elapsed | Peak summed RSS | Minimum Linux available |
|---|---|---:|---:|---:|
| Original sequential annotation | Exit 0, group closed | 10.297 s | 135,913,472 B | 3,084,562,432 B |
| Stock protein CheckM2 | Exit 0, group closed | 227.887 s | 1,813,958,656 B | 1,489,182,720 B |
| Feature validation within second-unit remaining budget | Exit 1, group closed | 2.239 s | 83,533,824 B | 3,099,324,416 B |

The annotation returned table 11, 1,837 CDS, one contig and 2,046,826 nucleotide bases; no ML modules were imported in that cold annotation interpreter. Selected FAA SHA256 is `49cc4512c4c9652bc7d77d135f6030fe09c8c990fae5fa90bff748bb7151c7f2`. All ten original return values and separate independent DNA measurements are retained. No GFF/FNA deletion was intercepted.

The failure is a source-schema error, not a failed model computation or an invalid genome observation. Original `keggData.py` creates a clipped presence/absence subset but calculates module features from original raw KO copy counts. Those module means can exceed one. Pathways/categories use the clipped subset and remain 0–1. Proposed source schema v002 corrects only this module domain; original v001 and the twelve executed source files remain preserved. No clipping, annotation, DIAMOND or model repeat was performed by this audit.

The actual run is `analysis/checkm2_protein_pilot_v001/runs/20261027T001421Z-1ae7a083d47d/`. Its raw `quality_report.tsv`, first raw feature pickle, annotation, exact commands, warnings and all unit receipts remain unchanged. All 31 failed-attempt manifest files and the original source FNA were rehashed after closure. Raw feature-pickle SHA256 is `ea944f44e47deebd93c9912c0b139758bfc634ebebff1d1466bd0f122d1c9e60`; failed-attempt manifest SHA256 is `1fc44944553f690651e7f4f680fd4232a21743ab92ec19e56c075a1a0ef1aff1`.

WSL launcher 5932 exited 1 at 00:22:56Z after ordinary IPC/image closure and complete post-unmount verification of unchanged sealed image `c40e6918688eaf2e1a9e4161e77a4b473c3f611de575b39a89bdc03fba224ad4`. Its original process and outer launcher 5664 are absent. Common native/install/Linux ownership leases were reacquired and released. The outer Windows launcher's exit code was not observed and remains UNKNOWN; root did not retain its process handle. Its disappearance does not establish an exit code.

Closure receipt: `evidence/checkm2_protein_pilot_v001/baseline_attempt_closure.json`, SHA256 `4c59dc516190017a735eb264c1a08d38e0cf80450b1e79981406ce778f3d19e7`. Immutable terminal-state snapshot: `evidence/checkm2_protein_pilot_v001/closed_attempts/00af8837b20c4bd3a06966f63800007e/manifest.json`, SHA256 `0920ab89a4f8855da0110b816ad41a04ef78beefcdc431bcd2b3f0aa415bd18b`.

Next admissible work is a separately reviewed, explicitly authorized feature-only validation of these preserved artifacts under the corrected schema, with its own evidence chain. Format invariance remains held until that baseline validation and final ownership proof are accepted. No biological retry, extra budget, workflow method substitution or automatic control run is authorized by this outcome document.
