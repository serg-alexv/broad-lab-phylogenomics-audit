"""Resumable per-species metadata discovery for gaps in prioritized catalogs.

No genomes or analyses are launched here. Raw API responses and request/hash
receipts use the same NCBI helper and policy as discover.py. An immutable plan
allows restart without losing the original missing-species denominator.
"""
from __future__ import annotations

import collections
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import discover
import select_panel


def source_snapshot():
    subtree_path = ROOT / "metadata/species_subtree.json"
    taxonomy_path = ROOT / "metadata/taxonomy_map.json"
    taxonomy = select_panel.load_taxonomy(taxonomy_path)
    subtree = discover.read(subtree_path)
    species = {int(key): value for key, value in subtree.get("edges", {}).items()
               if value.get("rank") == "SPECIES" and value.get("assembly_count", 0) > 0}
    named = {key: value for key, value in species.items()
             if not select_panel.UNIDENTIFIED.search(value.get("scientific_name", ""))
             and len(value.get("scientific_name", "").split()) >= 2}
    records = discover.load()
    raw_by_species = collections.defaultdict(list)
    eligible_by_species = collections.defaultdict(list)
    unresolved_org_taxids = []
    for record in records:
        normalized = select_panel.normalize(record, taxonomy, [])
        sid = normalized["species_taxid"]
        if sid:
            raw_by_species[sid].append(record["accession"])
            if normalized["metadata_qc"] != "EXCLUDED":
                eligible_by_species[sid].append(record["accession"])
        else:
            unresolved_org_taxids.append(record.get("organism", {}).get("tax_id"))
    missing = sorted(set(named) - set(raw_by_species))
    no_eligible = sorted(set(named) & set(raw_by_species) - set(eligible_by_species))
    return {
        "created_at": discover.now(), "plan_version": 1,
        "scope": "Missing named species with assemblies in current Lactobacillales filtered subtree; prioritized catalogs are not an exhaustive all-assembly search.",
        "species_with_assemblies_count": len(species), "named_species_with_assemblies_count": len(named),
        "unnamed_species_omitted": [{"taxid": key, "name": species[key].get("scientific_name", "")}
                                  for key in sorted(set(species) - set(named))],
        "discovered_record_count": len(records),
        "named_species_raw_covered_count": len(set(named) & set(raw_by_species)),
        "named_species_acquisition_eligible_count": len(set(named) & set(eligible_by_species)),
        "missing_named_species_count": len(missing),
        "missing_named_species": [{"taxid": key, "name": named[key]["scientific_name"],
                                   "subtree_assembly_count": named[key]["assembly_count"]} for key in missing],
        "known_species_without_acquisition_eligible_assembly": [{"taxid": key, "name": named[key]["scientific_name"],
                                                                "discovered_accessions": raw_by_species[key]} for key in no_eligible],
        "unresolved_organism_taxids": sorted(set(x for x in unresolved_org_taxids if x)),
        "raw_query": {"path_template": "genome/taxon/{taxid}/dataset_report",
                      "params": {**discover.COMMON, **discover.QUALITY}},
        "inputs": [{"path": str(p.relative_to(ROOT)), "sha256": discover.sha(p)}
                   for p in [subtree_path, taxonomy_path]],
        "selection_or_final_panel_modified": False,
    }


def fetch_species(item):
    sid = item["taxid"]
    seen = set()
    token = ""
    page = 0
    expected = None
    pages = []
    while True:
        params = {**discover.COMMON, **discover.QUALITY, **({"page_token": token} if token else {})}
        target = f"metadata/catalogs/species_gaps/page_{sid}_{page:04d}.json"
        data = discover.get(f"genome/taxon/{sid}/dataset_report", params, target)
        if "reports" not in data and int(data.get("total_count", 0)) != 0:
            raise RuntimeError("API response has no report list")
        reports = data.get("reports", [])
        if expected is None:
            expected = int(data.get("total_count", len(reports)))
        for report in reports:
            accession = report.get("accession")
            if not accession:
                raise RuntimeError("Missing assembly accession in successful response")
            if accession in seen:
                raise RuntimeError("Repeated accession in pagination: " + accession)
            seen.add(accession)
        pages.append({"path": target, "sha256": discover.sha(ROOT / target), "records": len(reports)})
        token = data.get("next_page_token", "")
        discover.atomic(ROOT / f"state/gap_species_{sid}.json", {
            **item, "at": discover.now(), "page": page, "records": len(seen),
            "reported_total": expected, "complete": not bool(token), "pages": pages,
        })
        if not token:
            break
        page += 1
    if len(seen) != expected:
        raise RuntimeError(f"Reported count mismatch for {sid}: {len(seen)} != {expected}")
    return {**item, "status": "RETRIEVED" if seen else "NO_CURRENT_ASSEMBLIES_AFTER_FILTERS",
            "records": len(seen), "reported_total": expected, "pages": pages,
            "reason": "" if seen else "All assemblies may be excluded by current/non-atypical/non-MAG filters or taxonomy/source availability changed; no biological absence inferred."}


def main():
    discover.admission()
    import msvcrt
    locks = []
    identity = {"pid": os.getpid(), "at": discover.now(), "host": os.environ.get("COMPUTERNAME"), "argv": sys.argv}
    try:
        for name in ["gap_discovery.lock", "discovery.lock"]:
            lock = open(ROOT / "state" / name, "a+b")
            lock.seek(0)
            lock.write(b"0")
            lock.flush()
            lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                lock.close()
                raise RuntimeError("Another metadata controller holds " + name)
            locks.append(lock)
        discover.atomic(ROOT / "state/gap_discovery_process.json", identity)
        plan_path = ROOT / "state/gap_discovery_plan.json"
        if plan_path.exists():
            plan = discover.read(plan_path)
        else:
            plan = source_snapshot()
            discover.atomic(plan_path, plan)
        discover.atomic(ROOT / "metadata/species_gap_coverage_audit.json", plan)
        result_path = ROOT / "state/gap_discovery_results.json"
        results = discover.read(result_path) if result_path.exists() else {}
        state_path = ROOT / "state/discovery_species_gaps.json"
        status = "FAILED"
        discover.event("gap_start", missing_species=plan["missing_named_species_count"], pid=os.getpid())
        try:
            for item in plan["missing_named_species"]:
                sid = str(item["taxid"])
                if sid in results and results[sid].get("status") != "UNRESOLVED_REQUEST":
                    continue
                discover.admission()
                try:
                    result = fetch_species(item)
                except InterruptedError:
                    raise
                except Exception as error:
                    result = {**item, "status": "UNRESOLVED_REQUEST", "error": repr(error),
                              "records": 0, "reason": "Request failed or taxid unavailable; taxonomy/biological state remains unresolved."}
                results[sid] = result
                discover.atomic(result_path, results)
                discover.atomic(state_path, {"catalog": "species_gaps", "complete": False, "at": discover.now(),
                                            "planned_species": len(plan["missing_named_species"]), "attempted_species": len(results),
                                            "records": sum(r.get("records", 0) for r in results.values())})
                discover.event("gap_species", taxid=item["taxid"], name=item["name"], status=result["status"],
                               records=result["records"], completed=len(results), planned=len(plan["missing_named_species"]))
            audit = {**plan, "finished_at": discover.now(), "results": list(results.values()),
                     "result_status_counts": dict(collections.Counter(r["status"] for r in results.values())),
                     "new_records_total": sum(r.get("records", 0) for r in results.values()),
                     "all_requests_resolved": all(r["status"] != "UNRESOLVED_REQUEST" for r in results.values()),
                     "post_taxonomy_refresh_required": True, "final_panel_freeze": "NOT_PERMITTED_BY_THIS_AUDIT"}
            discover.atomic(ROOT / "metadata/species_gap_coverage_audit.json", audit)
            unresolved = sum(r["status"] == "UNRESOLVED_REQUEST" for r in results.values())
            discover.atomic(state_path, {"catalog": "species_gaps", "complete": unresolved == 0, "at": discover.now(),
                                        "planned_species": len(plan["missing_named_species"]), "attempted_species": len(results),
                                        "unresolved_species": unresolved, "records": audit["new_records_total"],
                                        "audit_sha256": discover.sha(ROOT / "metadata/species_gap_coverage_audit.json")})
            status = "COMPLETED" if not unresolved else "COMPLETED_WITH_UNRESOLVED_REQUESTS"
            discover.event("gap_done", status=status, records=audit["new_records_total"], results=audit["result_status_counts"])
        except InterruptedError:
            status = "STOPPED"
            raise
        finally:
            discover.atomic(ROOT / "state/gap_discovery_exit.json", {**identity, "ended_at": discover.now(), "status": status})
    finally:
        for lock in reversed(locks):
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            lock.close()


if __name__ == "__main__":
    main()
