"""Bounded current-assembly metadata rescue for species coverage gaps.

Retains atypical/MAG reports so local QC can document their actual rejection
reasons. This never freezes or rewrites an acquisition panel.
"""
from __future__ import annotations
import collections
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import discover

MAX_RECORDS_PER_SPECIES = 5000
PARAMS = dict(discover.COMMON)


def make_plan():
    gap_path = ROOT / "metadata/species_gap_coverage_audit.json"
    audit = discover.read(gap_path)
    queue = {}
    for row in audit["known_species_without_acquisition_eligible_assembly"]:
        queue[row["taxid"]] = {"taxid": row["taxid"], "name": row["name"],
                              "reason": "KNOWN_ASSEMBLIES_METADATA_QC_EXCLUDED"}
    for row in audit["results"]:
        if row["status"] == "NO_CURRENT_ASSEMBLIES_AFTER_FILTERS":
            queue[row["taxid"]] = {"taxid": row["taxid"], "name": row["name"],
                                  "reason": "NO_REPORTS_AFTER_ATYPICAL_MAG_FILTERS"}
    return {"created_at": discover.now(), "species": [queue[key] for key in sorted(queue)],
            "planned_species": len(queue), "max_records_per_species": MAX_RECORDS_PER_SPECIES,
            "query_params": PARAMS, "source_audit_sha256": discover.sha(gap_path),
            "scope": "Bounded current-assembly rescue; no atypical/MAG exclusions at API layer; local QC still required.",
            "all_assembly_universe_census": False, "panel_modified": False}


def fetch_species(item):
    sid = item["taxid"]
    path = f"genome/taxon/{sid}/dataset_report"
    probe_target = f"metadata/species_rescue_probes/species_{sid}.json"
    probe = discover.get(path, {**PARAMS, "page_size": 1, "returned_content": "ASSM_ACC"}, probe_target)
    expected = int(probe.get("total_count", len(probe.get("reports", []))))
    if expected > MAX_RECORDS_PER_SPECIES:
        return {**item, "status": "UNRESOLVED_ABOVE_RECORD_BUDGET", "reported_total": expected,
                "records": 0, "probe": probe_target,
                "reason": f"{expected} current reports exceed the explicit {MAX_RECORDS_PER_SPECIES}-record/species bound; full metadata was not fetched or silently truncated."}
    token, page, seen, pages = "", 0, set(), []
    while True:
        target = f"metadata/catalogs/species_rescue/page_{sid}_{page:04d}.json"
        data = discover.get(path, {**PARAMS, **({"page_token": token} if token else {})}, target)
        reports = data.get("reports", [])
        full_count = int(data.get("total_count", len(reports)))
        if full_count > MAX_RECORDS_PER_SPECIES:
            raise RuntimeError("Full-report count changed above admitted per-species budget")
        if page == 0 and full_count != expected:
            raise RuntimeError(f"Probe/full report count changed {expected} -> {full_count}; audit before continuing")
        for record in reports:
            acc = record.get("accession")
            if not acc or acc in seen:
                raise RuntimeError("Missing or repeated accession during species pagination")
            seen.add(acc)
        pages.append({"path": target, "sha256": discover.sha(ROOT / target), "records": len(reports)})
        token = data.get("next_page_token", "")
        discover.atomic(ROOT / f"state/rescue_species_{sid}.json", {
            **item, "at": discover.now(), "page": page, "records": len(seen),
            "reported_total": expected, "complete": not bool(token), "pages": pages})
        if not token:
            break
        page += 1
    if len(seen) != expected:
        raise RuntimeError(f"Pagination count mismatch {len(seen)} != {expected}")
    return {**item, "status": "RETRIEVED" if seen else "NO_CURRENT_REPORTS",
            "reported_total": expected, "records": len(seen), "pages": pages,
            "reason": "" if seen else "Current/pair-deduplicated source query returned zero; taxonomy/source availability unresolved, not biological absence."}


def main():
    discover.admission()
    import msvcrt
    locks = []
    identity = {"pid": os.getpid(), "at": discover.now(), "host": os.environ.get("COMPUTERNAME"), "argv": sys.argv}
    status = "FAILED"
    try:
        for name in ["rescue_discovery.lock", "discovery.lock"]:
            lock = open(ROOT / "state" / name, "a+b")
            lock.seek(0); lock.write(b"0"); lock.flush(); lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                lock.close()
                raise RuntimeError("Another metadata controller holds " + name)
            locks.append(lock)
        discover.atomic(ROOT / "state/rescue_discovery_process.json", identity)
        plan_path = ROOT / "state/rescue_discovery_plan.json"
        plan = discover.read(plan_path) if plan_path.exists() else make_plan()
        if not plan_path.exists():
            discover.atomic(plan_path, plan)
        result_path = ROOT / "state/rescue_discovery_results.json"
        results = discover.read(result_path) if result_path.exists() else {}
        state_path = ROOT / "state/discovery_species_rescue.json"
        discover.event("rescue_start", planned_species=plan["planned_species"], pid=os.getpid())
        for item in plan["species"]:
            sid = str(item["taxid"])
            if sid in results and results[sid].get("status") != "UNRESOLVED_REQUEST":
                continue
            discover.admission()
            try:
                result = fetch_species(item)
            except InterruptedError:
                raise
            except Exception as error:
                result = {**item, "status": "UNRESOLVED_REQUEST", "error": repr(error), "records": 0,
                          "reason": "Request or source consistency failed; source/taxonomy remains unresolved."}
            results[sid] = result
            discover.atomic(result_path, results)
            discover.atomic(state_path, {"catalog": "species_rescue", "complete": False, "at": discover.now(),
                                        "planned_species": plan["planned_species"], "attempted_species": len(results),
                                        "records": sum(row.get("records", 0) for row in results.values())})
            discover.event("rescue_species", taxid=item["taxid"], name=item["name"], status=result["status"],
                           records=result["records"], attempted=len(results), planned=plan["planned_species"])
        unresolved = [row for row in results.values() if row["status"].startswith("UNRESOLVED")]
        audit = {**plan, "finished_at": discover.now(), "results": list(results.values()),
                 "records_total": sum(row.get("records", 0) for row in results.values()),
                 "status_counts": dict(collections.Counter(row["status"] for row in results.values())),
                 "unresolved_species": unresolved, "all_species_resolved": not bool(unresolved),
                 "post_taxonomy_refresh_and_local_qc_required": True,
                 "full_coverage_claim": False, "final_panel_freeze": "NOT_PERMITTED_BY_THIS_AUDIT"}
        audit_path = ROOT / "metadata/species_rescue_coverage_audit.json"
        discover.atomic(audit_path, audit)
        discover.atomic(state_path, {"catalog": "species_rescue", "complete": True, "at": discover.now(),
                                    "scope": "Bounded rescue pass attempted completely, not a complete assembly census or species-coverage claim.",
                                    "planned_species": plan["planned_species"], "attempted_species": len(results),
                                    "records": audit["records_total"], "unresolved_species_count": len(unresolved),
                                    "all_species_resolved": not bool(unresolved), "audit_sha256": discover.sha(audit_path)})
        status = "COMPLETED" if not unresolved else "COMPLETED_WITH_UNRESOLVED_SPECIES"
        discover.event("rescue_done", status=status, records=audit["records_total"], results=audit["status_counts"])
    except InterruptedError:
        status = "STOPPED"
        raise
    finally:
        discover.atomic(ROOT / "state/rescue_discovery_exit.json", {**identity, "ended_at": discover.now(), "status": status})
        for lock in reversed(locks):
            lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1); lock.close()


if __name__ == "__main__":
    main()
