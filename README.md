# Broad-LAB phylogenomics and antiphage defence audit

This is the 5 November 2026 audit snapshot of the authoritative WD Tree 2 workspace. It preserves completed results, partial results, original production code, and the exact continuation evidence. The WD project remains the authoritative record until this snapshot has been audited.

| Stage | Saved checkpoint |
| --- | --- |
| Genome cohort | 1,170 versioned acquisitions. Source audit supports 919, holds 223, and excludes 28. All 919 source-supported genomes have CheckM1 records and uniform Prodigal annotations. The provisional 1,000-member selection, missing acquisitions, exclusions, and frozen 900-tip tree cohort are recorded. |
| Full-panel tree | 900 tips, 54 protein markers, 13,071 aligned amino-acid columns, LG+F+G4, 1,000 UFBoot and 1,000 SH-aLRT replicates. Saved tree, consensus and support passed computational validation. Taxonomy, orthology, model adequacy and rooting review remain open. |
| Defence | 165 independently accepted paired dispositions. The next 20 have both predictors saved with retained native and WSL exit 0 and await independent file QA. The remaining 734 are unsearched and unknown. Verified zero-complete-system outputs are separately identifiable. |
| Deliverables remaining | Defence cohort QA and searches, scientific panel and tree validation, final defence rings, and an independently inferred representative tree. |

## Where to start

- [Provenance and resume procedure](audit/PROVENANCE_AND_RESUME.md) and [checkpoint manifest](audit/CHECKPOINT_MANIFEST.json).
- [Cohort and defence status tables](audit/tables/README.md), including one row per acquired genome and one row per defence target.
- [Performance evidence](audit/performance/README.md), with per-genome and per-detector wall times, failed and recovered attempts, and resource measurements.
- [Exact dependencies and model pins](audit/DEPENDENCIES_AND_MODELS.json) and [original upstream notices](snapshot/docs/THIRD_PARTY_TOOL_NOTICES.md).
- [Original scripts](snapshot/scripts/), [decision log](snapshot/docs/DECISION_LOG.md), and [full-panel tree](snapshot/analysis/phylogeny/full900_production_v001/inference/full_tree.treefile). These copies retain their original bytes and historical host paths.
- [Package index](handoff/package_index.json), [release asset manifest](handoff/release-assets.json), [transfer verification](handoff/VERIFICATION.json), and [historical method sources](handoff/method_history/README.md).

## Download and verify

Clone or download this repository. Run the following from its root with Python 3.11 or later. The downloader verifies each asset's byte count and SHA-256 and reuses verified files on retry. Use a case-sensitive filesystem for the restore, such as the Linux home filesystem under WSL. The archive preserves two intentionally case-distinct files from a runtime probe. The restore directory must be new and its parent must exist.

```text
python download_snapshot.py ../tree2_bundle
python verify_and_restore.py ../tree2_bundle --restore ../tree2_restored
```

The [release](https://github.com/serg-alexv/broad-lab-phylogenomics-audit/releases/tag/tree2-audit-20261105) contains the full alignment and IQ-TREE outputs, resumable binary checkpoints, input protein and coordinate files, model definitions, intermediate results, and the complete available raw defence evidence. Consult `handoff/package_index.json` for exact download and unpacked byte counts. Restoring the many small files requires extra filesystem space.

The omission ledger records genome and coding DNA, installation caches and images, credentials, and other excluded payloads. One signed registry receipt is [represented by a sanitized copy](handoff/registry-receipt-sanitized.json). For nucleotide-dependent reproduction, obtain the original accession versions from NCBI and compare them to the saved acquisition checksums. Keep a restored snapshot read-only and use fresh host-specific paths and an independent QA work area. The saved C009 files permit file-only QA once historical closure and dependency hashes are reconciled.
