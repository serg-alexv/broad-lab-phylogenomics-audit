"""Publish one immutable, source-supported QC review queue without launching it."""
from __future__ import annotations

import collections
import hashlib
import json
import os
from pathlib import Path
import tempfile

import discover
import select_panel

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_REVIEW_FAILURES = {
    "checkm_completeness_outside_threshold", "checkm_contamination_outside_threshold",
    "contigs_outside_threshold", "n50_outside_threshold",
}


def publish_new(path, content):
    """Atomic exclusive publication: an existing immutable artifact is an error."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".part", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temp, path)
    finally:
        os.unlink(temp)


def publish_json(path, content):
    publish_new(path, (json.dumps(content, indent=2, ensure_ascii=False) + "\n").encode())


def source_support(record, row):
    biosample = record.get("assembly_info", {}).get("biosample", {})
    attrs = {a.get("name", "").lower(): a.get("value", "") for a in biosample.get("attributes", [])}
    evidence = []
    if row["type_material"]:
        evidence.append({"field": "type_material", "value": record.get("type_material", {})})
    if attrs.get("sample_type", "").strip().lower() == "isolate":
        evidence.append({"field": "biosample.sample_type", "value": attrs["sample_type"]})
    culture = attrs.get("culture_collection", "").strip()
    if culture and culture.lower() not in {"missing", "unknown", "n/a", "na", "none"} and not culture.lower().startswith("not "):
        evidence.append({"field": "biosample.culture_collection", "value": culture})
    for model in biosample.get("models", []):
        if model.startswith("MIGS.ba") or model.startswith("Pathogen.cl"):
            evidence.append({"field": "biosample.models", "value": model})
    return evidence, {
        "biosample": biosample.get("accession", ""), "models": biosample.get("models", []),
        "package": biosample.get("package", ""), "sample_type": attrs.get("sample_type"),
        "culture_collection": attrs.get("culture_collection"), "isolation_source": attrs.get("isolation_source"),
        "metagenomic": attrs.get("metagenomic"), "derived_from": attrs.get("derived_from"),
    }


def main():
    protect = [ROOT / "metadata/provisional_panel.json", ROOT / "metadata/provisional_panel.tsv"]
    protect.extend(sorted((ROOT / "metadata").glob("acquisition_batch_*.json")))
    before = {str(path.relative_to(ROOT)): discover.sha(path) for path in protect}
    candidates_path = ROOT / "metadata/candidates_qc.json"
    gap_path = ROOT / "metadata/species_gap_coverage_audit.json"
    rows = discover.read(candidates_path)
    gap = discover.read(gap_path)
    original = {item["taxid"]: item for item in gap["known_species_without_acquisition_eligible_assembly"]}
    groups = collections.defaultdict(list)
    for row in rows:
        if row["species_taxid"] in original:
            groups[row["species_taxid"]].append(row)
    excluded = {sid for sid, values in groups.items() if all(row["metadata_qc"] == "EXCLUDED" for row in values)}
    raw = {record["accession"]: record for record in discover.load()}
    queue, held = [], []
    closed_species = 0
    for sid in sorted(excluded):
        closed = [row for row in groups[sid] if row["assembly_level"] in {"Complete Genome", "Chromosome"}]
        if not closed:
            continue
        closed_species += 1
        allowed, denied = [], []
        for row in closed:
            hard = sorted(set(row["exclusion_reasons"]) - ALLOWED_REVIEW_FAILURES)
            if row["species"].startswith("Candidatus "):
                hard.append("provisional_nomenclature_requires_separate_curation")
            evidence, details = source_support(raw[row["accession"]], row)
            if not evidence:
                hard.append("affirmative_isolate_or_culture_source_support_missing")
            if hard:
                denied.append({"accession": row["accession"], "hard_gate_reasons": hard,
                               "source_evidence": details, "original_exclusion_reasons": row["exclusion_reasons"]})
            else:
                allowed.append((row, evidence, details))
        if not allowed:
            held.append({"species_taxid": sid, "species": original[sid]["name"], "candidates": denied})
            continue
        allowed.sort(key=lambda item: select_panel.quality_key(item[0]))
        row, evidence, details = allowed[0]
        record = raw[row["accession"]]
        chosen = dict(row)
        chosen.update({
            "selection_status": "QC_REVIEW_ONLY", "selection_index": len(queue) + 1,
            "queue_role": "ANCILLARY_INDEPENDENT_QC_REVIEW_NOT_PRODUCTION_PANEL",
            "independent_biological_qc": "NOT_RUN", "production_eligible": False,
            "source_culture_support": evidence, "source_evidence": details,
            "ncbi_checkm_source": record.get("checkm_info", {}),
            "source_record_sha256": hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "review_reason": "Closed/chromosome source-supported anchor fails current metadata QC; investigate method sensitivity or genuine defects independently.",
            "promotion_gate": "CheckM2 or justified independent completeness/contamination validation, taxonomy and sequence QC; documented review. No automatic threshold relaxation.",
            "production_thresholds_unchanged": {"minimum_completeness": 95, "maximum_contamination": 5},
        })
        queue.append(chosen)
    panel = discover.read(ROOT / "metadata/provisional_panel.json")
    candidatus = [row for row in panel if row["species"].startswith("Candidatus ")]
    other_species = len({row["species_taxid"] for row in panel if not row["species"].startswith("Candidatus ")})
    audit = {
        "created_at": discover.now(), "queue_status": "IMMUTABLE_QC_REVIEW_ONLY_NOT_LAUNCHED",
        "original_excluded_species": len(original), "remaining_excluded_species": len(excluded),
        "closed_priority_species_before_hard_gates": closed_species, "queued_species": len(queue),
        "held_back_species": held, "hold_count": len(held),
        "queue_filter": "Current complete/chromosome; only metadata quality threshold failures; no known MAG/SAG, atypical, suppressed, ANI/taxonomy conflict, provisional nomenclature, or unresolved culture/isolate provenance.",
        "source_support_limit": "Culture/type/model metadata support is source evidence, not independent confirmation of culture or genome purity.",
        "production_thresholds": {"minimum_completeness": 95, "maximum_contamination": 5},
        "independent_biological_qc": "NOT_RUN", "acquisition_launched": False,
        "candidatus_pending_curation": [{"accession": row["accession"], "species_taxid": row["species_taxid"],
                                         "species": row["species"], "metadata_qc": row["metadata_qc"]} for row in candidatus],
        "other_selected_species_level_taxa": other_species,
        "input_sha256": {str(candidates_path.relative_to(ROOT)): discover.sha(candidates_path),
                         str(gap_path.relative_to(ROOT)): discover.sha(gap_path)},
        "protected_production_artifacts": before,
    }
    queue_path = ROOT / "metadata/acquisition_qc_review_only.json"
    audit_path = ROOT / "metadata/qc_review_selection_audit.json"
    publish_json(queue_path, queue)
    publish_json(audit_path, audit)
    held_lines = "\n".join(f"- {item['species']}: " + "; ".join(sorted({reason for c in item['candidates'] for reason in c['hard_gate_reasons']})) for item in held)
    queue_lines = "\n".join(f"| {row['species']} | {row['accession']} | {row['ncbi_checkm_completeness']} | {row['ncbi_checkm_contamination']} |" for row in queue)
    doc = f"""# Sampling review before production-panel freeze

Review date: 2026-10-26. Source selection snapshot: {discover.read(ROOT / 'metadata/selection_summary.json')['created_utc']}. All selections remain provisional; no final high-quality panel or species coverage claim is made.

## Coverage and screening results

The refreshed corpus contains 11,355 versioned accessions. The provisional 1,000-genome panel represents 767 species-level taxids: **{other_species} other species-level taxa and {len(candidatus)} Candidatus taxa pending separate nomenclature/source curation**. Every selected Candidatus row is already QC_PENDING. These categories are not a claim that all remaining names or genomes have been independently verified.

The original priority catalogs left 113 species with only excluded candidates. Overlapping species-level reasons were completeness below 95% (74 species), contamination above 5% (49), more than 200 contigs (14), and N50 below 20kb (5); other reasons included source/taxonomy conflicts. Broader per-species retrieval recovered acquisition-eligible candidates for 8 species (6 with metadata passes and 2 with pending QC). **105 species still have no acquisition-eligible candidate under current screening.** None of these exclusions establishes biological absence.

Among those 105 species, **{closed_species} have complete/chromosome assemblies** and form a priority independent-QC review stratum. After hard source gates and an affirmative culture/isolate provenance requirement, the immutable review queue contains **{len(queue)} genomes, one per species**. The remaining {len(held)} species are held back for the reasons below. This is a conservative acquisition-review queue; it does not promote any genome into the production panel or alter its 95%/5% gates.

## Candidatus curation policy

Candidatus is a nomenclature status and does not by itself establish that a genome is MAG, SAG, uncultivated, or poor quality. Some selected records explicitly describe isolates: GCF_017316025.1 / [SAMN18075559](https://www.ncbi.nlm.nih.gov/biosample/SAMN18075559) (Enterococcus myersii, sample_type=isolate, sand filtrate); GCF_017315945.1 / [SAMN18075572](https://www.ncbi.nlm.nih.gov/biosample/SAMN18075572) (Enterococcus courvalinii, sample_type=isolate); and GCF_017316105.1 / [SAMN18075568](https://www.ncbi.nlm.nih.gov/biosample/SAMN18075568) (Enterococcus ikei, sample_type=isolate). Other source descriptions are ambiguous, such as GCF_017316185.1 / [SAMN09399635](https://www.ncbi.nlm.nih.gov/biosample/SAMN09399635) (water; no explicit sample_type) and GCF_009933175.1 / [SAMN05199424](https://www.ncbi.nlm.nih.gov/biosample/SAMN05199424) (Whole organism).

Keep these {len(candidatus)} taxa in an ancillary pending-curation stratum. Preserve existing acquisition snapshots and downloaded files. Before a production freeze, curate nomenclature, culture/derivation provenance, taxonomic identity and independent genome QC; reject demonstrated MAG/SAG/uncultivated or unresolved production entries under the primary isolate contract. Do not label Candidatus as biological absence or silently count the group as formally curated species. The API formal-name flag is omitted for the inspected examples and cannot supply affirmative nomenclature evidence here.

## Method-sensitive cutoff risks

Closed assembly status is not an independent quality guarantee, and a CheckM estimate is not a direct measurement of missing DNA. Examples requiring review include complete Lactococcus protaetiae GCF_006965445.1 (83.87% completeness; genus marker set), Acetilactobacillus jinshanensis GCF_055764315.1 (91.98%; family marker set), and Melissococcus plutonius GCF_059745495.1 (94.05%; family marker set, contamination field omitted). The CheckM paper describes lineage-related estimation limitations, including underestimation in reduced lineages. This establishes a potential method-sensitivity mechanism, **not its cause in these LAB genomes**. [Parks et al., 2015](https://pmc.ncbi.nlm.nih.gov/articles/PMC4484387/).

Use CheckM2 or another justified independent completeness/contamination method, sequence-derived QC, taxonomic checks and marker-level review to distinguish estimator behavior from actual defects. CheckM2 provides a different prediction approach; agreement or disagreement still requires interpretation. [Chklovski et al., 2023](https://pubmed.ncbi.nlm.nih.gov/37500759/). Keep omitted contamination values unknown. Do not lower production cutoffs silently, substitute a complete label for QC, or declare excluded species absent. Fragmentation cutoffs also affect defence-system detectability and should be treated as explicit methodological choices.

## QC-review queue

Queue: metadata/acquisition_qc_review_only.json. Status: QC_REVIEW_ONLY; independent_biological_qc=NOT_RUN; acquisition not launched by this review. Original exclusion reasons and NCBI CheckM source/version/marker-rank evidence are retained per entry. Source support consists of type/culture-collection metadata, an explicit isolate field, or a cultured/clinical BioSample model; it is not independent proof of purity.

| Species | Review accession | NCBI completeness % | NCBI contamination % |
| --- | --- | ---: | ---: |
{queue_lines}

## Held-back closed-assembly species

{held_lines}

Existing provisional panels and acquisition batches are preserved byte-for-byte. This review creates only an ancillary immutable queue, audit and document; it launches no acquisition or scientific computation.
"""
    doc_path = ROOT / "docs/SAMPLING_REVIEW.md"
    publish_new(doc_path, doc.encode("utf-8"))
    after = {str(path.relative_to(ROOT)): discover.sha(path) for path in protect}
    if before != after:
        raise RuntimeError("Protected production artifact changed during review publication")
    files = [queue_path, audit_path, doc_path]
    publish_json(ROOT / "manifests/qc_review_queue_commit.json", {
        "created_at": discover.now(), "status": "COMMITTED_REVIEW_ONLY_NOT_LAUNCHED",
        "queued_species": len(queue), "script_sha256": discover.sha(__file__),
        "protected_production_artifacts_unchanged": before,
        "artifacts": [{"path": str(path.relative_to(ROOT)), "sha256": discover.sha(path), "bytes": path.stat().st_size} for path in files],
    })
    print(json.dumps({"queued": len(queue), "held_back": len(held), "closed_priority": closed_species,
                      "remaining_excluded_species": len(excluded), "production_artifacts_unchanged": before == after}, indent=2))


if __name__ == "__main__":
    main()
