# Held throughput extension: one shared index8 search

This is a later optimization proposal, after the current19-input V1 cohort is moving. V1 sources, claims, results and debits remain unchanged. Nothing here admits execution or establishes speedup, memory fit, biological accuracy or general numerical equivalence.

The pinned CheckM2 author code already concatenates FAA dictionaries and makes one blastp call for up to250 input FAA files (`diamond.py:61–71,127–143`; defaultValues.py:21,25). It uses an existing database, not makedb. The current per-row adapter repeats blastp process/database initialization. Its timing receipts do not separate initialization from alignment, so the removable overhead is unmeasured. A shared query may reduce that repeated cost while increasing query-side work and memory; the unchanged2GiB summed-RSS gate decides actual feasibility.

## Query and split contract

Use at most20 fresh members, plus one or two explicitly declared SEARCH_ONLY_CONTROL donors already accepted under the exact index8 profile. Controls are excluded from fresh-genome completion counters. Their accepted annotations/models are not rerun. All accessions, including controls, must be distinct. The total22 FAA files remain below the author's250-file boundary.

Every FAA keeps the exact versioned `ACCESSION.VERSION.faa` basename, original sequence order/bytes and annotation/FAA/ten-return-value bindings. Use the unchanged author SeqReader and writer. A query key is exactly `FAA_stem + Ω + original_primary_ID`; prove primary IDs unique within each FAA and full keys globally unique before dictionary merging, which otherwise silently overwrites duplicates. Reject ambiguous separator collisions. Pin an ordered member/query-key manifest and require the resulting query record/sequence inventory to equal the sum of the admitted FAA inventories. No header renaming, suffix removal or sequence normalization is introduced.

Keep the complete raw12-column TSV unchanged. Split by the exact namespace before Ω, verifying each primary ID against that member's query inventory. Unknown namespaces/IDs are fatal. Every original row must belong to exactly one split; reconstructing the duplicate-preserving multiset of all splits must reproduce the aggregate multiset exactly. Preserve all12 original field strings and duplicate counts, including full reference~annotation targets; do not deduplicate, round numbers, filter KOs or restrict copy-number features to0..1. The hit-query set is a subset of the input-query set: not every protein must have a hit. Preserve V1's nonempty valid per-genome search-availability gate; missing/empty results stay unavailable/QC_PENDING, never negative.

Each fresh member receives its own strict inventory with exactly its original versioned FAA and its split `diamond_output/DIAMOND_RESULTS.tsv`. Stock genes/resume and feature validation remain serial per member, with identical runtime/bootstrap, original models, database, source masks and numerical code. Control TSVs are compared and retained, then excluded from resume/ML and fresh method-row counts.

## One bounded measurement and accounting

Keep DIAMOND2.1.11/DB3, thread1, block0.5, index8 and the complete existing scientific argv: outfmt6, max-target-seqs1, query-cover80, subject-cover80, identity30, evalue1e-5. Keep2CPU affinity,2GiB summed group RSS,1GiB available-memory minimum and40GiB disk reserve. Durable scientific scratch remains outside the32MiB IPC mount. A model-free query producer execs the same binary; all construction, search, split/check processes remain in the one observed unit/group. No model is loaded during that unit.

Propose one initially900-second shared-search ceiling, including query preparation, search and split checks, reusing the current observer's admitted maximum. This is a new explicit allocation requiring Root review, not borrowed per-row time. Annotation180, resume600 and validation120 seconds remain per fresh row. Aggregate ceiling is900 shared seconds plus900 per fresh member, separately clipped by the actual cold/helper window; no control gets an additional hidden search allowance. Record one genuine shared execution receipt/debit, referenced by each row, never charged20 times or fabricated as20 independent search exits. Preserve all historical attempt/cold debits. First failure stops; no automatic split, retry or replay. Partial annotation/search artifacts need actual closure and separately scoped reuse authority.

Include one accepted index8 donor, optionally a second from a different admitted input size/lineage, in that same shared query. Compare its full12-field duplicate-preserving TSV multiset exactly with its already accepted single-query index8 artifact under identical FAA/binary/DB/argv bindings. Any difference blocks optimization acceptance; do not mask it with float tolerances. Equality establishes only those precise controls. If no matching accepted index8 artifact exists, this gate is held. Own-row feature checks are still required for every fresh genome and are not biological truth.

## Minimal versioned change map

| Boundary | Later V2 change |
|---|---|
| Plan/common/factory | Add separate fresh/control manifests, one shared-search allocation/claim and unique aggregate debit; preserve species-first selection and accepted exclusions. |
| Model-free producer and split binding | Extend the existing author query transform to the ordered list; retain build_argv unchanged; reuse the current12-field artifact checker and add a lossless partition receipt. |
| Inner scheduler and row bindings | Commit all necessary annotations, one shared search/control comparison, then serial per-row resume/features. Bind each row to its own split plus the shared closed unit. Reuse the existing numerical validator core; only provenance/request bindings change. |
| Native/entry/close | Carry forward existing ownership/resource/namespace/exit guards and one same-context session; recognize the one shared invocation when verifying manifests/debits. No per-row image remount, extra framework or cohort-specific source clone. |

A single independently reviewed V2 source cut and Root admission must precede this measurement. Frozen V1 remains the current route. Report actual phase durations/peak RSS and complete-control equality before deciding whether this optimization should replace it.
