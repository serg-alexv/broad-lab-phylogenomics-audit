"""Normalize NCBI catalog metadata and create a provisional acquisition panel.

This is metadata screening, not independent biological QC or a frozen panel.
Unknown QC values remain unknown. No network requests are made here.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import tempfile


ORDER_ID = 186826
MIN_LENGTH = 500_000
MAX_LENGTH = 10_000_000
MAX_CONTIGS = 200
MIN_N50 = 20_000
MIN_COMPLETENESS = 95.0
MAX_CONTAMINATION = 5.0
UNIDENTIFIED = re.compile(r"\b(?:sp\.?|spp\.?|bacterium|uncultured|unclassified|unidentified|metagenome)\b", re.I)
MAG = re.compile(r"metagenome.assembled|metagenome-derived|single.cell amplified|\bMAG\b|\bSAG\b|\bMIMAG\b|\bMISAG\b", re.I)


def utcnow():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def atomic_bytes(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".part", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def atomic_json(path, value):
    atomic_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode())


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def get(obj, snake, default=None):
    """Read API snake_case or downloaded-package camelCase, preserving zero."""
    if not isinstance(obj, dict):
        return default
    if snake in obj:
        return obj[snake]
    parts = snake.split("_")
    camel = parts[0] + "".join(p.title() for p in parts[1:])
    return obj.get(camel, default)


def number(value):
    if value is None or value == "":
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (ValueError, TypeError):
        return None


def taxid(value):
    value = number(value)
    return int(value) if value is not None else None


def source_provenance(record):
    """Use affirmative structured derivation fields, never a project title.

    NCBI catalog and downloaded-package schemas differ in case and in which
    BioSample details they expose. A false/absent flag never proves culture.
    """
    info = get(record, "assembly_info", {})
    biosample = info.get("biosample", {})
    def canon(value):
        return re.sub(r"[\s_-]+", " ", str(value).strip().lower())
    unknown = {"", "false", "no", "0", "missing", "unknown", "na", "n/a", "none", "not applicable", "not provided", "not collected", "not available"}
    def present(value):
        text = canon(value)
        return text not in unknown and not text.startswith("not ")
    def yes(value):
        return value is True or canon(value) in {"true", "yes", "1"}
    evidence = []
    def add(kind, field, value):
        evidence.append({"kind": kind, "field": field, "value": value})
    attrs = {}
    for item in biosample.get("attributes", []):
        name, value = canon(item.get("name", "")), item.get("value", "")
        attrs.setdefault(name, []).append(value)
        text = canon(value)
        if name == "metagenomic" and yes(value):
            add("MAG", "biosample.attributes.metagenomic", value)
        elif name == "investigation type":
            if "metagenome" in text or text in {"mag", "mimag"}:
                add("MAG", "biosample.attributes.investigation_type", value)
            if re.search(r"single (?:cell |cell amplified |amplified )genome|single cell|\b(?:sag|misag)\b", text):
                add("SAG", "biosample.attributes.investigation_type", value)
        elif name in {"metagenome source", "metagenomic source", "source metagenome biosample", "source metagenome bioproject"} and present(value):
            add("MAG", "biosample.attributes." + item.get("name", ""), value)
        elif name in {"derived from", "sample derived from"} and present(value):
            if "metagenome" in text or "metagenomic" in text:
                add("MAG", "biosample.attributes." + item.get("name", ""), value)
            if "single cell" in text or "single amplified genome" in text:
                add("SAG", "biosample.attributes." + item.get("name", ""), value)
        elif name == "environmental sample" and yes(value):
            add("ENVIRONMENTAL", "biosample.attributes." + item.get("name", ""), value)
        if (name == "cultured" and text in {"false", "no", "0"}) or (name in {"cultivation status", "culture status"} and text in {"uncultivated", "uncultured", "not cultured"}):
            add("UNCULTIVATED", "biosample.attributes." + item.get("name", ""), value)
        if name == "sample type" and text in {"isolate", "culture", "cultured isolate", "bacterial culture", "pure culture"}:
            add("ISOLATE_SUPPORT", "biosample.attributes.sample_type", value)
        if name == "culture collection" and present(value):
            add("ISOLATE_SUPPORT", "biosample.attributes.culture_collection", value)
    notes = get(info, "genome_notes", []) or []
    notes = [notes] if isinstance(notes, str) else notes
    for note in notes:
        text = canon(note)
        if text.startswith("not ") or text.startswith("no "):
            continue
        if re.search(r"derived from (?:a )?metagenom|metagenome assembled|\bmag\b", text):
            add("MAG", "assembly_info.genome_notes", note)
        if "single cell" in text or "single amplified genome" in text:
            add("SAG", "assembly_info.genome_notes", note)
    assembly_type = get(info, "assembly_type", "")
    if re.search(r"metagenom|\bmag\b", canon(assembly_type)):
        add("MAG", "assembly_info.assembly_type", assembly_type)
    if "single cell" in canon(assembly_type) or "single amplified" in canon(assembly_type):
        add("SAG", "assembly_info.assembly_type", assembly_type)
    models = [("biosample.models", model) for model in biosample.get("models", [])]
    if biosample.get("package"):
        models.append(("biosample.package", biosample["package"]))
    for field, model in models:
        if re.match(r"^(?:MIMAG|MIMS)(?:[.\s_-]|$)", model, re.I):
            add("MAG", field, model)
        if re.match(r"^MISAG(?:[.\s_-]|$)", model, re.I):
            add("SAG", field, model)
        if model.startswith("MIGS.ba") or model.startswith("Pathogen.cl"):
            add("ISOLATE_SUPPORT", field, model)
    if get(record, "type_material", {}):
        add("ISOLATE_SUPPORT", "type_material", get(record, "type_material"))
    atypical = info.get("atypical", {})
    if isinstance(atypical, dict) and (yes(get(atypical, "is_atypical", False)) or atypical.get("warnings")):
        add("ATYPICAL", "assembly_info.atypical", atypical)
    kinds = {item["kind"] for item in evidence}
    if "MAG" in kinds or "SAG" in kinds:
        status = "EXCLUDED_MAG_SAG"
    elif "UNCULTIVATED" in kinds:
        status = "EXCLUDED_UNCULTIVATED"
    elif "ATYPICAL" in kinds:
        status = "EXCLUDED_ATYPICAL"
    elif "ENVIRONMENTAL" in kinds:
        status = "HOLD_ENVIRONMENTAL_SOURCE"
    elif "ISOLATE_SUPPORT" in kinds:
        status = "ISOLATE_SOURCE_SUPPORTED_NOT_INDEPENDENTLY_VERIFIED"
    else:
        status = "HOLD_SOURCE_UNRESOLVED"
    def first_number(name):
        return next((number(value) for value in attrs.get(name, []) if number(value) is not None), None)
    return {"status": status, "is_mag": "MAG" in kinds, "is_sag": "SAG" in kinds,
            "is_uncultivated": "UNCULTIVATED" in kinds,
            "is_atypical": "ATYPICAL" in kinds, "environmental_sample": "ENVIRONMENTAL" in kinds,
            "isolate_source_supported": "ISOLATE_SUPPORT" in kinds,
            "source_conflict": bool(({"MAG", "SAG"} & kinds) and "ISOLATE_SUPPORT" in kinds),
            "evidence": evidence, "genome_notes": notes,
            "submitter_reported_completeness": first_number("completeness score"),
            "submitter_reported_contamination": first_number("contamination score"),
            "submitter_quality_method": attrs.get("completeness software", []),
            "limit": "Structured source metadata; absence of derivation flags is not proof of an isolate."}


def taxonomy_records(value):
    if isinstance(value, dict) and "reports" in value:
        for report in value["reports"]:
            tax = report.get("taxonomy", report)
            yield str(get(tax, "tax_id", report.get("tax_id", ""))), tax
    elif isinstance(value, dict):
        if "taxonomy" in value:
            tax = value["taxonomy"]
            yield str(get(tax, "tax_id", "")), tax
        else:
            for key, tax in value.items():
                if isinstance(tax, dict):
                    yield str(key), tax.get("taxonomy", tax)
    elif isinstance(value, list):
        for item in value:
            yield from taxonomy_records({"reports": [item]})


def load_taxonomy(path):
    return dict(taxonomy_records(json.loads(Path(path).read_text(encoding="utf-8-sig"))))


def ranked_taxon(tax, rank):
    classification = tax.get("classification", {})
    item = classification.get(rank, {})
    if str(tax.get("rank", "")).lower() == rank:
        name = get(tax, "current_scientific_name", {})
        return taxid(get(tax, "tax_id")), name.get("name", "") if isinstance(name, dict) else str(name)
    if isinstance(item, dict):
        return taxid(item.get("id", get(item, "tax_id"))), item.get("name", "")
    return None, ""


def normalize(record, taxonomy, source_paths):
    org = record.get("organism", {})
    info = get(record, "assembly_info", {})
    stats = get(record, "assembly_stats", {})
    checkm = get(record, "checkm_info", {})
    ani = get(record, "average_nucleotide_identity", {})
    organism_taxid = taxid(get(org, "tax_id"))
    tax = taxonomy.get(str(organism_taxid), {})
    order_taxid, order_name = ranked_taxon(tax, "order")
    family_taxid, family = ranked_taxon(tax, "family")
    genus_taxid, genus = ranked_taxon(tax, "genus")
    species_taxid, species = ranked_taxon(tax, "species")
    organism_name = get(org, "organism_name", "")
    length = number(get(stats, "total_sequence_length"))
    contigs = number(get(stats, "number_of_contigs"))
    n50 = number(get(stats, "contig_n50"))
    completeness = number(checkm.get("completeness"))
    contamination = number(checkm.get("contamination"))
    accession = record.get("accession", "")
    biosample = info.get("biosample", {})
    attrs = biosample.get("attributes", [])
    attrs_by_name = {str(a.get("name", "")).lower(): a.get("value", "") for a in attrs}
    inf = get(org, "infraspecific_names", {})
    status = get(info, "assembly_status", "")
    atypical = info.get("atypical", {})
    failures, pending = [], []

    if not re.fullmatch(r"GC[AF]_\d+\.\d+", accession):
        failures.append("invalid_versioned_accession")
    current = get(record, "current_accession", accession)
    if status.lower() != "current":
        failures.append("assembly_not_current_or_unknown")
    if current != accession:
        failures.append("superseded_accession")
    if not tax:
        pending.append("taxonomy_missing")
    elif order_taxid != ORDER_ID:
        failures.append("outside_lactobacillales_or_unresolved_order")
    if not species_taxid or not species or len(species.split()) < 2:
        failures.append("species_unresolved")
    elif UNIDENTIFIED.search(species):
        failures.append("unidentified_species")
    if str(tax.get("rank", "")).lower() == "species" and get(tax, "current_scientific_name_is_formal") is False:
        failures.append("species_name_not_formal")
    if not genus_taxid or not family_taxid:
        failures.append("genus_or_family_unresolved")
    if UNIDENTIFIED.search(organism_name):
        failures.append("unidentified_submitted_organism")
    provenance = source_provenance(record)
    if provenance["is_mag"] or provenance["is_sag"]:
        failures.append("mag_or_single_cell")
    if provenance["is_uncultivated"]:
        failures.append("uncultivated_source")
    if provenance["environmental_sample"]:
        failures.append("environmental_sample")
    if provenance["is_atypical"]:
        failures.append("ncbi_atypical")
    if provenance["status"] == "HOLD_SOURCE_UNRESOLVED":
        pending.append("isolate_source_unresolved")
    if get(info, "suppression_reason"):
        failures.append("suppression_reason")
    for label, value, test in [
        ("length", length, lambda x: MIN_LENGTH <= x <= MAX_LENGTH),
        ("contigs", contigs, lambda x: x <= MAX_CONTIGS),
        ("n50", n50, lambda x: x >= MIN_N50),
        ("checkm_completeness", completeness, lambda x: x >= MIN_COMPLETENESS),
        ("checkm_contamination", contamination, lambda x: x <= MAX_CONTAMINATION),
    ]:
        if value is None:
            pending.append(label + "_missing")
        elif not test(value):
            failures.append(label + "_outside_threshold")
    ani_status = get(ani, "taxonomy_check_status", "")
    if str(ani_status).lower() in {"failed", "fail", "mismatch", "not_match", "taxonomy_check_failed"}:
        failures.append("ncbi_ani_taxonomy_mismatch")
    elif str(ani_status).lower() not in {"ok", "taxonomy_check_status_ok"}:
        pending.append("ani_taxonomy_not_confirmed")
    type_material = get(record, "type_material", {})
    qc = "EXCLUDED" if failures else "QC_PENDING" if pending else "QC_METADATA_PASS"
    return {
        "accession": accession, "paired_accession": get(record, "paired_accession", ""),
        "current_accession": current, "source_database": get(record, "source_database", ""),
        "organism_taxid": organism_taxid, "organism_name": organism_name,
        "order_taxid": order_taxid, "order": order_name,
        "family_taxid": family_taxid, "family": family, "genus_taxid": genus_taxid, "genus": genus,
        "species_taxid": species_taxid, "species": species,
        "biosample": biosample.get("accession", ""), "bioproject": get(info, "bioproject_accession", ""),
        "strain": inf.get("strain", biosample.get("strain", "")),
        "assembly_level": get(info, "assembly_level", ""), "assembly_status": status,
        "type_material": bool(type_material), "type_material_label": get(type_material, "type_label", ""),
        "reference": get(info, "refseq_category", "").lower() == "reference genome",
        "release_date": get(info, "release_date", ""),
        "length_bp": int(length) if length is not None else None,
        "contigs": int(contigs) if contigs is not None else None, "n50": int(n50) if n50 is not None else None,
        "gc_percent": number(get(stats, "gc_percent")),
        "ncbi_checkm_completeness": completeness, "ncbi_checkm_contamination": contamination,
        "ncbi_checkm_version": get(checkm, "checkm_version", ""),
        "ncbi_ani_taxonomy_status": ani_status, "metadata_qc": qc,
        "source_provenance_status": provenance["status"], "source_provenance": provenance,
        "exclusion_reasons": sorted(set(failures)), "pending_reasons": sorted(set(pending)),
        "independent_biological_qc": "NOT_RUN", "selection_status": "NOT_SELECTED",
        "source_catalogs": sorted(source_paths),
    }


def quality_key(row):
    levels = {"Complete Genome": 0, "Chromosome": 1, "Scaffold": 2, "Contig": 3}
    return (row["metadata_qc"] != "QC_METADATA_PASS", levels.get(row["assembly_level"], 4),
            not row["type_material"], not row["reference"],
            -(row["ncbi_checkm_completeness"] if row["ncbi_checkm_completeness"] is not None else -1),
            row["ncbi_checkm_contamination"] if row["ncbi_checkm_contamination"] is not None else 100,
            row["contigs"] if row["contigs"] is not None else 10**9, -(row["n50"] or 0), row["accession"])


def breadth_order(rows):
    """Round-robin families, then genera, so a download prefix covers breadth."""
    groups = collections.defaultdict(lambda: collections.defaultdict(list))
    for row in rows:
        groups[row["family"]][row["genus"]].append(row)
    for genera in groups.values():
        for genus in genera:
            genera[genus].sort(key=quality_key)
    result = []
    family_keys = sorted(groups)
    genus_positions = collections.Counter()
    while any(any(v for v in g.values()) for g in groups.values()):
        for family in family_keys:
            genera = groups[family]
            keys = sorted(genera)
            for offset in range(len(keys)):
                i = (genus_positions[family] + offset) % len(keys)
                if genera[keys[i]]:
                    result.append(genera[keys[i]].pop(0))
                    genus_positions[family] = (i + 1) % len(keys)
                    break
    return result


def choose_panel(rows, target):
    eligible = sorted((r for r in rows if r["metadata_qc"] != "EXCLUDED"), key=quality_key)
    unique, samples, pairs, strain_keys = [], {}, {}, {}
    for row in eligible:
        sample = row["biosample"]
        pair = row["paired_accession"]
        strain = row["strain"].strip().lower()
        strain_key = (row["species_taxid"], strain) if strain and strain not in {"missing", "not applicable", "unknown"} else None
        previous = samples.get(sample) if sample else None
        previous = previous or pairs.get(row["accession"]) or (pairs.get(pair) if pair else None)
        previous = previous or (strain_keys.get(strain_key) if strain_key else None)
        if previous:
            row["selection_status"] = "DUPLICATE_BIOLOGICAL_SAMPLE"
            row["duplicate_of"] = previous
            continue
        unique.append(row)
        if sample:
            samples[sample] = row["accession"]
        pairs[row["accession"]] = row["accession"]
        if pair:
            pairs[pair] = row["accession"]
        if strain_key:
            strain_keys[strain_key] = row["accession"]
    by_species = collections.defaultdict(list)
    for row in unique:
        by_species[row["species_taxid"]].append(row)
    anchors = breadth_order([values.pop(0) for values in by_species.values()])
    panel = anchors[:]
    for row in anchors:
        row["selection_phase"] = "SPECIES_ANCHOR"
    while len(panel) < target:
        next_round = breadth_order([values.pop(0) for values in by_species.values() if values])
        if not next_round:
            break
        for row in next_round[:target - len(panel)]:
            row["selection_phase"] = "SPECIES_BALANCED_ADDITION"
            panel.append(row)
    for index, row in enumerate(panel, 1):
        row["selection_status"] = "PROVISIONAL_ACQUISITION_ONLY"
        row["selection_index"] = index
    return panel


def write_table(path, rows):
    columns = list(rows[0]) if rows else ["accession", "metadata_qc"]
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value
                         for key, value in row.items()})
    atomic_bytes(path, output.getvalue().encode("utf-8"))


def run(root, target=1000):
    root = Path(root).resolve()
    metadata = root / "metadata"
    taxonomy_path = metadata / "taxonomy_map.json"
    taxonomy = load_taxonomy(taxonomy_path)
    files = []
    # Accession-only universe indexes are census inputs, not full QC records.
    # Partial controller outputs are not admitted until their bounded pass ends.
    for catalog in ["references", "type_material", "closed", "species_gaps", "species_rescue"]:
        state_path = root / f"state/discovery_{catalog}.json"
        if not state_path.exists() or not json.loads(state_path.read_text(encoding="utf-8-sig")).get("complete"):
            continue
        allowed_pages = None
        if catalog in {"species_gaps", "species_rescue"}:
            result_path = root / ("state/gap_discovery_results.json" if catalog == "species_gaps" else "state/rescue_discovery_results.json")
            results = json.loads(result_path.read_text(encoding="utf-8-sig")) if result_path.exists() else {}
            allowed_pages = {Path(page["path"]).name for result in results.values()
                             if result.get("status") in {"RETRIEVED", "NO_CURRENT_REPORTS", "NO_CURRENT_ASSEMBLIES_AFTER_FILTERS"}
                             for page in result.get("pages", [])}
        files.extend(p for p in (metadata / "catalogs" / catalog).glob("page_*.json")
                     if not p.name.endswith(".receipt.json") and (allowed_pages is None or p.name in allowed_pages))
    files = sorted(files)
    if not files:
        raise RuntimeError("No catalog pages found; refusing to create a misleading empty panel")
    records, provenance = {}, collections.defaultdict(set)
    input_manifest = []
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        receipt_path = path.with_suffix(".json.receipt.json")
        if not receipt_path.exists():
            raise RuntimeError(f"Catalog lacks source receipt: {path}")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
        if receipt.get("sha256") != sha256(path):
            raise RuntimeError(f"Catalog hash does not match source receipt: {path}")
        # The API omits zero/default protobuf fields: a successful zero-match
        # request may be serialized as {}. Accept only this narrow empty shape
        # with a verified helper receipt, never arbitrary error objects.
        empty_success = set(data) <= {"total_count"} and int(data.get("total_count", 0)) == 0
        if "reports" not in data and not empty_success:
            raise RuntimeError(f"Catalog is not a successful reports response: {path}")
        input_manifest.append({"path": str(path.relative_to(root)), "sha256": sha256(path), "reports": len(data.get("reports", []))})
        for record in data.get("reports", []):
            accession = record.get("accession", "")
            if accession in records and records[accession] != record:
                # API snapshots can differ in incidental metadata; retain deterministic first record and all source paths.
                provenance[accession].add("MULTIPLE_SNAPSHOT_RECORDS")
            records.setdefault(accession, record)
            provenance[accession].add(str(path.relative_to(root)))
    rows = [normalize(records[a], taxonomy, provenance[a]) for a in sorted(records)]
    sequence_rejections = collections.defaultdict(list)
    for receipt_path in sorted((root / "work/rejected").glob("*/rejection_receipt.json")):
        rejection = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
        if rejection.get("acquisition_status") == "FAIL_SEQUENCE_QC":
            sequence_rejections[rejection["accession"]].append({
                "path": str(receipt_path.relative_to(root)), "sha256": sha256(receipt_path),
                "reason": rejection.get("error"), "sequence_qc": rejection.get("sequence_qc")})
    for row in rows:
        row["sequence_qc_rejection_evidence"] = sequence_rejections.get(row["accession"], [])
        if row["sequence_qc_rejection_evidence"]:
            row["metadata_qc"] = "EXCLUDED"
            row["exclusion_reasons"] = sorted(set(row["exclusion_reasons"] + ["known_versioned_sequence_qc_rejection"]))
    panel = choose_panel(rows, target)
    timestamp = utcnow()
    summary = {
        "created_utc": timestamp, "panel_state": "PROVISIONAL_ACQUISITION_ONLY_NOT_FROZEN",
        "target": target, "candidate_count": len(rows), "panel_count": len(panel),
        "metadata_qc_counts": dict(collections.Counter(r["metadata_qc"] for r in rows)),
        "panel_metadata_qc_counts": dict(collections.Counter(r["metadata_qc"] for r in panel)),
        "eligible_species": len({r["species_taxid"] for r in rows if r["metadata_qc"] != "EXCLUDED"}),
        "selected_species": len({r["species_taxid"] for r in panel}),
        "selected_genera": dict(collections.Counter(r["genus"] for r in panel)),
        "selected_families": dict(collections.Counter(r["family"] for r in panel)),
        "exclusion_reasons": dict(collections.Counter(reason for r in rows for reason in r["exclusion_reasons"])),
        "pending_reasons": dict(collections.Counter(reason for r in rows for reason in r["pending_reasons"])),
        "selection_status_counts": dict(collections.Counter(r["selection_status"] for r in rows)),
        "independent_biological_qc": "NOT_RUN", "sequence_diversity_selection": "NOT_RUN",
        "full_species_representation_interpretation": "PENDING_BEFORE_FINAL_FREEZE",
        "catalog_discovery_complete": False,
        "catalog_discovery_note": "Current closed/reference/type-material catalogs are a prioritized discovery tranche, not an exhaustive all-assembly universe.",
        "sampling_rule": "One anchor per acquisition-eligible resolved species, then balanced rounds; pending QC remains pending; target may expand to cover all eligible species.",
        "thresholds": {"min_length_bp": MIN_LENGTH, "max_length_bp": MAX_LENGTH, "max_contigs": MAX_CONTIGS,
                       "min_n50": MIN_N50, "min_ncbi_checkm_completeness": MIN_COMPLETENESS,
                       "max_ncbi_checkm_contamination": MAX_CONTAMINATION},
        "inputs": input_manifest + [{"path": str(taxonomy_path.relative_to(root)), "sha256": sha256(taxonomy_path)}],
        "script_sha256": sha256(__file__),
    }
    atomic_json(metadata / "selection_commit.json", {"created_utc": timestamp, "commit_state": "IN_PROGRESS"})
    atomic_json(metadata / "candidates_qc.json", rows)
    write_table(metadata / "candidates_qc.tsv", rows)
    atomic_json(metadata / "provisional_panel.json", panel)
    write_table(metadata / "provisional_panel.tsv", panel)
    atomic_json(metadata / "selection_summary.json", summary)
    artifact_paths = [metadata / name for name in ["candidates_qc.json", "candidates_qc.tsv", "provisional_panel.json", "provisional_panel.tsv", "selection_summary.json"]]
    atomic_json(metadata / "selection_commit.json", {"created_utc": timestamp, "commit_state": "COMPLETE",
                "artifacts": [{"path": str(p.relative_to(root)), "sha256": sha256(p), "bytes": p.stat().st_size} for p in artifact_paths]})
    print(json.dumps({key: summary[key] for key in ["candidate_count", "panel_count", "metadata_qc_counts", "panel_metadata_qc_counts", "selected_species", "selected_families"]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--target", type=int, default=1000)
    args = parser.parse_args()
    if args.target < 1:
        parser.error("target must be positive")
    run(args.root, args.target)
