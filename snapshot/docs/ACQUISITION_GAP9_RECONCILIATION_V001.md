# Nine absent accession folders: local acquisition reconciliation

The nine missing folders are **unsubmitted balanced-strain selections, not nine missing species labels**. Every label already has a different acquired, source-supported representative in the bound provisional panel and the 824-genome DNA consistency screen. No input repair or download is required now for these labels' acquisition coverage. This finding does not grant biological quality or taxonomic acceptance.

Exact accession/species/source/receipt/version bindings, all acquired alternatives and preserved technical failures are in `metadata/acquisition_gap9_reconciliation_v001.json`. Only NEW Tree 2 WD project metadata were read. No network, S 1 runtime, caller, model, pickle, FAA or genomic sequence processing ran.

| Absent provisional accession | Source species label | Acquired source-supported panel/screen representative |
|---|---|---|
| GCF_039544835.1 | Alloiococcus otitis | GCF_900445205.1 |
| GCF_000407365.1 | Enterococcus asini | GCF_001885725.1 |
| GCF_001885995.1 | Enterococcus italicus | GCF_053761085.1 |
| GCF_000260755.1 | Streptococcus infantis | GCF_053205985.1 |
| GCF_001434465.1 | Limosilactobacillus oris | GCF_025311495.1 |
| GCF_053207465.1 | Streptococcus australis | GCF_900476055.1 |
| GCF_005405465.1 | Weissella thailandensis | GCF_001932615.1 |
| GCF_053203605.1 | Streptococcus pseudoporcinus | GCF_900637075.1 |
| GCF_007992055.1 | Companilactobacillus mindensis | GCF_001434275.1 |

All nine original IDs remain intact, with their locally recorded paired GCA `.1` IDs, BioSample/strain and `QC_METADATA_PASS` source assertions. None of the 1,170 audited acquisitions has the same numeric assembly accession under GCA/GCF or another version. Thus these are genuinely absent accession slots, not an acquired paired-representation/version alias or a folder-name lookup error. Current remote availability and latest versions were not queried and remain unknown.

## Why the folders are absent

All nine current selections have phase `SPECIES_BALANCED_ADDITION`. None appears in any recorded immutable acquisition list, acquisition terminal result or progress result. There is no matching raw/paired directory, staging folder, package/HTTP/partial object, rejection or quarantine entry for these exact IDs. Accordingly their local attempt state is **NO_RECORDED_ATTEMPT**, not FAILED, HTTP-unavailable, technically rejected or biologically absent.

The final bound panel selection was committed at 2026-10-26 T 17:03:08.364814 Z, after the last acquisition ended at 17:01:38.524286 Z. Its nine balanced additions were not backfilled into the recorded acquisition batches. This establishes a panel/queue scheduling mismatch; it does not establish the intent of an unlogged action. Existing `qc/current_panel_acquisition_coverage.json` independently records 991/1,000 exact panel accessions acquired and no panel species label without any acquired candidate.

The replacement-round audit also preserves decisions to retain already acquired alternate accessions for several of these labels. It did not select these nine IDs for replacement download. The full per-label join uses the current source audit, acquisition-validation result and receipt hashes, rather than assuming that matching a species-name string proves genome identity.

## Distinct measured rejections remain rejected

Five of these labels also have **different** historical accession versions rejected for measured genomic ambiguity above the acquisition 1% gate:

| Rejected accession | Label | Recorded ambiguity |
|---|---|---:|
| GCF_000315445.1 | Alloiococcus otitis |1.24765%|
| GCF_000393955.1 | Enterococcus asini |1.53799%|
| GCF_000185365.1 | Enterococcus italicus |4.44787%|
| GCF_000187465.1 | Streptococcus infantis |1.13758%|
| GCF_000186465.1 | Streptococcus australis |1.03613%|

Each has two preserved historical rejection receipts with the same ambiguity measurement. These are real technical failures of those particular assemblies, not failures of the nine never-submitted IDs or evidence that the species lacks a suitable genome. Do not retry unchanged rejected accessions, promote their partials or erase these states. The later stage 04 ambiguity target remains 0.5%; the acquisition 1% rejection rule does not replace that gate.

Three other acquired same-label alternatives are still source-held: GCF_023743875.1 (E. italicus), GCF_988228545.1 (S. infantis) and GCF_030053195.1 (L. oris). They are retained in the JSON with their unresolved-isolate-source holds; none is promoted by this review. The table above instead identifies the acquired, source-supported panel/screen representatives.

## Controlled next action

Keep the bound panel, immutable acquisition lists, source holds and all existing statuses unchanged. The nine exact-accession slots remain pending optional strain coverage. First evaluate the acquired same-label representatives through independent biological QC and the separate source/taxonomy gates; metadata and an ANI consistency screen cannot substitute for either.

Only if those later decisions leave an eligible label with no acceptable acquired representative is an input repair needed: separately bind one accession-specific controlled acquisition candidate from the local corpus, preserve the original ID/rejections, and review any required current-version/source query before network access. No such repair is required or authorized by this reconciliation. No species is dropped solely because a strain slot was never downloaded, and no failed/held/unsearched state becomes a biological or defence negative.
