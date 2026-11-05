"""Write a human-readable receipt from fresh stage evidence, never infer biology."""
from pathlib import Path
import datetime,json,os
R=Path(__file__).resolve().parents[1]
def read(p):return json.loads((R/p).read_text(encoding='utf-8-sig'))
now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).isoformat()
raw=list((R/'raw').glob('GC[AF]_*/acquisition_receipt.json'))
qc=read('qc/acquisition_validation.json');src=read('qc/source_provenance_audit.json')['summary'];sel=read('metadata/selection_summary.json');census=read('qc/census_validation.json')
pilot=read('analysis/pilot10/runs/20261026T161747Z-cluster-resume-f688a380/benchmark_summary.json')
rejected={json.loads(p.read_text(encoding='utf-8-sig'))['accession'] for p in (R/'work/rejected').glob('*/rejection_receipt.json')}
text=f'''# Tree 2 startup execution receipt

As of **{now} (Europe/Moscow)**. This is a new WD-only project, isolated from Tree1 and older scientific outputs. Execution began; this is not a finished phylogeny or a frozen high-quality panel.

| Stage | Actual evidence/result |
|---|---|
| Host/resources | WD, Windows11, i5-1240P,15.75GiB physical RAM; WSL3 application/Ubuntu WSL2 with4CPU,3584MB RAM,8GB swap. Docker clients installed; servers were unavailable and were not started. |
| Source census | **{census['unique_current_paired_deduplicated_accessions']:,}** current paired-deduplicated Lactobacillales accessions;277 page hashes, counts, schema and uniqueness checked. Full priority/rescue metadata:11,355 unique assemblies. |
| Acquisition | **{len(raw):,}** committed versioned genomes with atomic receipts and SHA256s. **{len(rejected)} unique assembly versions** rejected by sequence QC; original data/evidence retained. Source integrity is distinct from biological quality. |
| Independent integrity verification | **{qc['genomes_checked']:,}** genomes checked; **{qc['source_md5_checks']:,}** published NCBI MD5 checks; outcomes:{qc['counts']}. Optional annotation omissions remain UNAVAILABLE. Baseline1046 results were preserved during new-cohort verification. |
| Provenance audit | Audit denominator **{src['acquired_reports_audited']:,}** source reports. Dispositions:{src['production_disposition_counts']}. Explicit MAGs:{src['mag_count']}; SAGs:{src['sag_count']}. These are held/excluded from the primary isolate analysis, not deleted or converted to negative defence calls. |
| Current provisional selection | **{sel['panel_count']} genomes / {sel['selected_species']} species-level taxa**. Metadata screening:{sel['panel_metadata_qc_counts']}. It remains provisional; held taxonomy/source records and independent quality gates are unresolved. |
| Fresh exploratory marker pilot | Ten newly acquired genomes,**{pilot['proteins']:,}** fresh Prodigal proteins;**{pilot['clusters']:,}** clusters,**{pilot['single_copy_occupancy_10of10']}** single-copy in all10. One bounded indexing correction used about436MiB sampled RAM. Accepted annotations/input hashes were reused unchanged. No old105-marker set was imported; no broad marker set is accepted. |
| Production biology | Independent completeness/contamination,sequence taxonomy,final diversity selection,production alignments,full/representative trees and defence predictions: **NOT_RUN**. |

The source audit corrected missed structured MAG/SAG flags. Earlier candidate panels,raw data and rejection receipts remain preserved. Known versioned sequence-QC failures now feed back into selection. Whole-species coverage still requires independent validation; unresolved is not biological absence.

The independent verifier's optional-annotation assumption was corrected by rerunning only the10 affected entries while preserving1036 accepted entries. The checkpoint writer's Windows/Linux symlink issue was corrected with a Linux-aware manifest recording link targets without following them. Original failure evidence is retained.

Pinned isolated tools: Prodigal2.6.3,HMMER3.4,MMseqs2 18.8cc5c,skani0.4.0; executable/package/file hashes and original notices are preserved. No global WSL limit or Docker service was changed. Setup exception: conda changed the shared environment-list timestamp; current bytes/hash/mtime are retained, no Tree2 prefix was registered, and the old bytes were not captured. No old analysis/environment payload was modified.

**Defence models remain blocked under the no-GitHub rule:** inspected official program archives omit complete model catalogues, verified updaters require GitHub, and no permitted complete source has been verified. No updater or defence search was run. All unsearched states stay unknown.

All artifacts stay local. Local Git uses SHA256 objects and has **no remote**. No GitHub access/upload occurred. Checkpoint/manifests preserve source queries,tool versions,raw receipts,validation history and pilot outputs.3D work remains deferred.

Read docs/STAGE_PLAN.md for the detailed BUILD/VERIFY/DOC/CUT plan; docs/SAMPLING_REVIEW.md and docs/SOURCE_PROVENANCE_ISSUE.md for curation; qc/acquisition_validation.json and qc/source_provenance_audit.json for exact denominators; docs/MODEL_ACQUISITION.md for the model block. Check live process creation identities,locks and terminal receipts before resuming anything.
'''
p=R/'STARTUP_REPORT.md';tmp=p.with_suffix('.md.tmp');tmp.write_text(text,encoding='utf-8');os.replace(tmp,p)
print(json.dumps({'report':str(p),'committed':len(raw),'integrity_checked':qc['genomes_checked'],'source_audited':src['acquired_reports_audited']}))
