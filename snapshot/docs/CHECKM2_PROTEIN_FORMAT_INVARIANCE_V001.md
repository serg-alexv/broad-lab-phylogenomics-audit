# Held format-invariance draft for the 04R1 protein route

This is a new contract and pure-comparator draft. The old nucleotide v005 patch
remains preserved and unapplied. No active 04R1 source is edited; no actual DNA is
rewrapped and no biological control is launched. A successful fully closed 04R1
baseline is not yet bound to this draft. Its actual output manifest, numeric
result, namespace envelope, native exit and common-lock release must be observed
before integration is designed and admitted.

The predeclared transformation remains 61-column LF FASTA wrapping only. Header
bytes excluding line ending, record order and every sequence byte including case
must remain exact. The raw acquisition FASTA stays untouched. A future control
stages the derived file under the identical accession filename, calls the same
original sequential ProdigalRunner with the same automatic translation-table
rules, then uses the unchanged accepted protein-input CheckM2 options and runtime.
The raw FNA hashes must differ; a no-op stops without another perturbation.

Required future comparisons are specific to the protein route:

- Exact selected FAA bytes/SHA256, ordered protein identifiers and amino-acid
  sequences, original caller/program hashes, all ten original return values,
  their nine-measurement map and separate independent DNA-summary sidecars.
- Exact five-column protein report schema: Name, Completeness, Contamination,
  Completeness_Model_Used and Additional_Notes. Name, model and notes match;
  score differences are at most 0.01 percentage point. Translation table and
  DNA-derived measurements are compared in the original annotation sidecars.
  Missing DNA columns are never invented in the official protein report.
- The required raw 21,241-feature input: exact schema, ordered column-name hash,
  one-by-21,242 DataFrame shape including Name, finite float64 input and canonical
  little-endian float64 row hash. Serialized pickle hashes are preserved for
  provenance; pickle byte equality is not a substitute for numeric/schema
  equality. Missing feature evidence, including both dumps missing, is
  NOT_EVALUABLE. This differs deliberately from the unlaunched old no-dump draft.
- Exact normalized DIAMOND 12-column row multiset, ignoring output row order
  while preserving duplicates, and unchanged model/database/bootstrap/IPC/options
  bindings. Baseline and control manifests must verify independently.

`scripts/checkm2_protein_invariance_v001.py` currently contains pure dictionary
comparators only. Six small synthetic fixtures exercise report tolerance/schema,
required annotation metrics and model-free flags, required feature hashes and
missing-evidence handling. They open no genome, feature pickle or model. The
comparators alone are not an executable control driver or an admission gate.

The versioned metadata contract records the concrete adaptor interface needed
after a valid baseline: a separately hash-bound input plan; original acquisition
and derived semantic identities; dedicated native/progress/namespace/output paths;
the same common locks and two explicit 600-second units; one immutable attempt;
and a new root strategy/source/hold-transition admission. The monitor must read
the dedicated control progress before launch. No accepted source is patched or
dispatcher queued by this draft. Creating a speculative executable patch before
the actual baseline artifact chain exists is intentionally deferred.

A future pass would establish pipeline-format invariance only. It supplies no
independent biological truth, FNA-route numeric equivalence, genome acceptance or
production panel acceptance.
