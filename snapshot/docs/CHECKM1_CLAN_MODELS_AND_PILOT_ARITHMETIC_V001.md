# CheckM1 marker domains and independent pilot arithmetic

The actual 140,559,553-byte temporary HMM contains 1,469 unique, complete HMMER3 records. This matches unchanged stock expansion exactly; it must not be reduced to the reported marker count.

| Domain | Count | Meaning |
|---|---:|---|
| Selected Lactobacillales markers | 335 | Markers used for the completeness/contamination calculation |
| Selected collocated marker sets | 183 | Denominator for the weighted calculation; derived from 490 reference genomes |
| Marker union across four ancestors | 367 | Lactobacillales, Bacilli, Firmicutes and Bacteria candidate marker IDs |
| Spanned PFAM clans | 59 | Clans containing one or more candidate markers |
| Additional clan competitors | 1,102 | Models needed for stock overlapping-clan best-hit filtering |
| Actual searched HMMs | 1,469 | Exact union of the 367 candidates and 1,102 competitors |

The source chain is `BinMarkerSets.getMarkerGenes()` → `MarkerSetParser._createMarkerHMMs()` → `PFAM.genesInSameClan()`. The parser subsequently applies `PFAM.filterHitsFromSameClan()` before adjacent-ORF correction. The actual-model audit rederived the union from the generated marker file and bound PFAM metadata, then compared every ACC header, record and terminator in one completed temporary model. Its Windows read allowed delete sharing so stock cleanup was not blocked. No genomic scan or scientific tool was invoked. See `metadata/checkm1_taxon_setup_v001/stock_clan_expansion_actual_v001.json`.

Stock creates and reads these temporary models for each bin, and the progress writer parses and removes each completed model. Root's observed NTFS/9P waits are consistent with this repeated I/O. Moving exact working files to private RAM changes storage placement, not the marker set or scoring algorithm. Its speed and memory fit remain to be measured.

`scripts/checkm1_pilot_marker_arithmetic_v001.py` is a prepared file-only checker for the completed pilot18 commit. It uses stored **post-filter/correction** hit intervals, preserving every retained interval, to reconstruct all 335 copy counts. It independently calculates the 183-set weighted presence and excess-copy scores, verifies all six copy-count categories/GCN lists, compares unrounded stored scores and the rounded QA report, and keeps all source holds. Four synthetic metadata-only test groups passed; the actual pilot has not been checked by this source publication.

After the actual pilot commit exists, Root may run:

```text
python -B scripts/checkm1_pilot_marker_arithmetic_v001.py --commit analysis/checkm1_lactobacillales_full919_v001/batch_000/COMMITTED.json --commit-sha256 ACTUAL_COMMIT_SHA --output metadata/checkm1_taxon_setup_v001/pilot18_independent_actual_arithmetic_v001.json
```

The 13 CheckM2 comparisons are diagnostics. Differences above 5 completeness points, 3 contamination points, or a 95/5 classification flip are reported, without requiring numerical identity between methods. Original scoring-FAA hash comparability is explicit. A valid low-quality measurement remains completed QC; rounded boundary crossings require review. The checker grants neither native-owner closure nor taxonomy/final-panel acceptance. Root retains the actual pilot method review and full-queue authorization.
