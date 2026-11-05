"""Close the original C008 reservation through one source-bound recovery."""

import collections
from contextlib import nullcontext
import hashlib
import json
import math
import os
from pathlib import Path
import uuid

import defence_campaign_ledger_v001 as original
import local_tree2_dispatcher as b


AUTHORITY_SCHEMA = "TREE2_DEFENCE_C008_CHECKPOINT_RECOVERY_AUTHORITY_V001"
AUTHORITY_STATUS = "ROOT_ADMITTED_C008_SAVED_PHASE_RECOVERY_ONCE"
RECOVERY_SCHEMA = "TREE2_DEFENCE_IMMUTABLE_C008_RECOVERY_RESERVATION_V001"
RECOVERY_STATUS = "RESERVED_SAME_C008_UNSTARTED_PHASES_ONLY"
ACTIVE_STATUS = "ACTIVE_RECOVERY_RESERVED_COHORT"


def _read(root, ref):
    return b.read(b.bind(root, ref))


def _serialized_row(root, path, data):
    payload = (json.dumps(data, indent=2) + "\n").encode("utf-8")
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
    }


def _publish_once(path, data):
    if path.exists():
        assert b.read(path) == data, f"Different immutable record at {path}"
    else:
        b.atomic(path, data)


def _archive(root, directory, path, before):
    archive = directory / "snapshots" / (before["sha256"] + ".json")
    if not archive.exists():
        archive.parent.mkdir(exist_ok=True)
        payload = path.read_bytes()
        assert hashlib.sha256(payload).hexdigest() == before["sha256"]
        pending = archive.with_name(archive.name + "." + uuid.uuid4().hex + ".partial")
        with pending.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(pending, archive)
    archived = b.row(root, archive)
    assert (archived["sha256"], archived["bytes"]) == (before["sha256"], before["bytes"])
    return archived


def _require_recovery_authority(root, authority_row):
    authority = _read(root, authority_row)
    assert authority["schema"] == AUTHORITY_SCHEMA and authority["status"] == AUTHORITY_STATUS
    assert authority["cohort_id"] == "C008" and authority["at_utc"]
    assert authority["remaining_unstarted_phases"] == 31 and authority["stock_threads"] == 4
    assert authority["replay_completed_phases"] is False
    failed = _read(root, authority["failed_disposition"])
    transaction = _read(root, authority["failed_transaction"])
    assert transaction["status"] == "C008_FAILED_UNKNOWN_COST_CONSUMED_ONCE_NO_ACCEPTANCE_OR_NEXT_RESERVATION"
    assert transaction["updated_ledger_observation"] == authority["failed_ledger"]
    assert transaction["failed_cohort_disposition"] == authority["failed_disposition"]
    assert failed["cohort_id"] == "C008" and failed["paired_genomes_accepted_from_this_cohort"] == 0
    assert failed["whole_owned_closure"] == authority["whole_closure"]
    assert failed["snapshot"] == authority["snapshot"]
    b.bind(root, authority["whole_closure"])
    b.bind(root, authority["snapshot"])
    manifest = _read(root, authority["inherited_phase_manifest"])
    assert manifest["schema"] == "TREE2_DEFENCE_INHERITED_PADLOC_PHASES_V003"
    assert manifest["status"] == "AUDITED_SAVED_PADLOC_PHASES_NO_SEARCH_REPLAY"
    assert manifest["source_plan"] == failed["source_plan"]
    selected = failed["selected_accessions"]
    assert len(selected) == len(set(selected)) == 20 and manifest["selected_accessions"] == selected
    rows = manifest["rows"]
    assert len(rows) == len({row["accession"] for row in rows})
    assert {row["accession"] for row in rows if row["phase"] is not None} == set(selected[:9])
    assert manifest["prior_scientific_seconds"] == failed["scientific_seconds_consumed"]
    assert manifest["prior_cold_seconds"] == failed["cold_seconds_consumed"]
    return authority, failed, transaction


def _failed_cost(ledger, failed, failure_ref):
    cost = ledger["cohort_costs"]["C008"]
    assert cost["status"] == "FAILED_NOT_ACCEPTED_CONSUMED_NO_RETRY"
    assert cost["scientific_seconds"] == failed["scientific_seconds_consumed"]
    assert cost["cold_seconds"] == failed["cold_seconds_consumed"]
    assert cost["file_QA_wall_seconds_separate"] == failed["file_QA_wall_seconds_consumed"]
    assert cost["failure_disposition"] == failure_ref
    assert cost["all_nine_stock_unit_seconds_consumed_including_uncommitted_ninth"] is True
    return cost


def reserve_recovery(root, authority_row, *, dry_run=False):
    """Atomically reserve the same 20 IDs, leaving the original debit intact."""
    root = Path(root).resolve()
    directory = root / "state/defence_campaign_v001"
    path = directory / "ledger.json"
    recovery_path = directory / "recovery_reservations/C008.json"
    with (nullcontext() if dry_run else b.ByteLock(directory / "ledger_transaction.lock")):
        authority, failed, transaction = _require_recovery_authority(root, authority_row)
        ledger = b.read(path)
        if ledger["status"] == ACTIVE_STATUS:
            row = b.row(root, recovery_path)
            record = _read(root, row)
            assert ledger["cohort_id"] == "C008" and ledger["recovery_reservation"] == row
            assert record["authority"] == authority_row and record["selected_accessions"] == failed["selected_accessions"]
            assert ledger["closed_paired_protein_scope_genomes"] == transaction["accepted_pairs_unchanged"]
            assert ledger["known_cumulative_defence_scientific_seconds"] == transaction["known_cumulative_scientific_seconds"]
            assert ledger["known_cumulative_defence_cold_seconds"] == transaction["known_cumulative_cold_seconds"]
            _failed_cost(ledger, failed, authority["failed_disposition"])
            assert {acc for acc, entry in ledger["entries"].items() if entry["state"] == "RESERVED_RECOVERY"} == set(record["selected_accessions"])
            return row

        before = b.row(root, path)
        assert before == authority["failed_ledger"], "Exact failed C008 ledger required"
        assert ledger["status"] == "BLOCKED_FAILED_COHORT_NO_AUTOMATIC_RETRY" and ledger["cohort_id"] == "C008"
        assert ledger["failure_disposition"] == authority["failed_disposition"]
        assert ledger["reservation"] == failed["reservation"]
        _failed_cost(ledger, failed, authority["failed_disposition"])
        assert not (directory / "closed_transactions/C008.json").exists()
        assert not (directory / "reservations/C009.json").exists()
        selected = failed["selected_accessions"]
        previous_reservation = _read(root, ledger["reservation"])
        assert previous_reservation["selected_accessions"] == selected
        assert previous_reservation["source_queue"] == ledger["source_queue"]
        states = collections.Counter(row["state"] for row in ledger["entries"].values())
        assert states == {"CLOSED_PAIRED_PROTEIN_SCOPE_ACCEPTED": 145, "FAILED_UNKNOWN": 20, "NOT_RUN_UNKNOWN": 754}
        assert {acc for acc, entry in ledger["entries"].items() if entry["state"] == "FAILED_UNKNOWN"} == set(selected)
        assert ledger["known_cumulative_defence_scientific_seconds"] == transaction["known_cumulative_scientific_seconds"]
        assert ledger["known_cumulative_defence_cold_seconds"] == transaction["known_cumulative_cold_seconds"]
        for accession in selected:
            entry = ledger["entries"][accession]
            assert entry["cohort_id"] == "C008" and entry["reservation"] == ledger["reservation"]
            assert entry["failure_disposition"] == authority["failed_disposition"]
            assert entry["original_source_masks_unchanged"] is True
            assert entry["unavailable_failed_unrun_not_negative"] is True

        if dry_run:
            archived = dict(before, path=(directory / "snapshots" / (before["sha256"] + ".json")).relative_to(root).as_posix())
        else:
            archived = _archive(root, directory, path, before)
        record = {
            "schema": RECOVERY_SCHEMA,
            "status": RECOVERY_STATUS,
            "cohort_id": "C008",
            "source_queue": ledger["source_queue"],
            "selected_accessions": selected,
            "original_reservation": ledger["reservation"],
            "failed_ledger_snapshot": archived,
            "failed_transaction": authority["failed_transaction"],
            "failed_disposition": authority["failed_disposition"],
            "whole_closure": authority["whole_closure"],
            "snapshot": authority["snapshot"],
            "inherited_phase_manifest": authority["inherited_phase_manifest"],
            "authority": authority_row,
            "prior_scientific_seconds": failed["scientific_seconds_consumed"],
            "prior_cold_seconds": failed["cold_seconds_consumed"],
            "remaining_unstarted_phases": 31,
            "stock_threads": 4,
            "replay_completed_phases": False,
            "all_original_unknown_masks_preserved": True,
            "at_utc": authority["at_utc"],
        }
        row = _serialized_row(root, recovery_path, record)
        if recovery_path.exists():
            assert b.row(root, recovery_path) == row
        if dry_run:
            return row
        _publish_once(recovery_path, record)
        assert b.row(root, recovery_path) == row
        for accession in selected:
            ledger["entries"][accession].update(state="RESERVED_RECOVERY", recovery_reservation=row)
        ledger.update(
            status=ACTIVE_STATUS,
            recovery_reservation=row,
            revision="RECOVER_C008_" + authority_row["sha256"][:32],
            at_utc=authority["at_utc"],
        )
        b.atomic(path, ledger)
        return row


def _costs(accepted, qa, recovery, failed_transaction, ledger):
    for measure in ("scientific_seconds", "cold_seconds"):
        inherited = recovery["prior_" + measure]
        new = qa["attempt_" + measure]
        total = accepted[measure]
        assert qa["inherited_" + measure] == inherited
        assert 0 < new <= total and math.isclose(total, inherited + new, abs_tol=1e-6, rel_tol=0)
        already = failed_transaction["known_cumulative_" + measure]
        assert ledger["known_cumulative_defence_" + measure] == already
        baseline = ledger["known_prior_defence_" + measure] + sum(
            item[measure] for item in ledger["cohort_costs"].values()
        )
        assert math.isclose(baseline, already, abs_tol=1e-6, rel_tol=0)
        assert math.isclose(baseline - inherited + total, already + new, abs_tol=1e-6, rel_tol=0)


def _finish_close(root, directory, path, intent):
    """Finish the same deterministic file transaction after interruption."""
    before, after = intent["before"], intent["after"]
    b.bind(root, intent["receipt"]["previous_ledger"])
    assert after == _serialized_row(root, path, intent["ledger"])
    assert intent["receipt"]["updated_ledger_observation"] == after
    current = b.row(root, path)
    assert current in (before, after), "C008 transaction cannot replace a later ledger"
    next_path = b.inside(root, intent["receipt"]["automatic_next_reservation"]["path"])
    _publish_once(next_path, intent["next_reservation"])
    assert b.row(root, next_path) == intent["receipt"]["automatic_next_reservation"]
    if current == before:
        b.atomic(path, intent["ledger"])
    assert b.row(root, path) == after
    _publish_once(directory / "closed_transactions/C008.json", intent["receipt"])
    return intent["receipt"]


def close(root, acceptance_row):
    """Accept recovered C008 exactly once. Delegate ordinary cohorts to V001."""
    root = Path(root).resolve()
    acceptance = _read(root, acceptance_row)
    if acceptance["cohort_id"] != "C008":
        return original.close(root, acceptance_row)

    directory = root / "state/defence_campaign_v001"
    path = directory / "ledger.json"
    closed_path = directory / "closed_transactions/C008.json"
    intent_path = directory / "recovery_transactions/C008_close_intent.json"
    with b.ByteLock(directory / "ledger_transaction.lock"):
        if closed_path.exists():
            closed = b.read(closed_path)
            assert closed["acceptance"] == acceptance_row
            return closed
        if intent_path.exists():
            intent = b.read(intent_path)
            assert intent["schema"] == "TREE2_DEFENCE_C008_RECOVERY_CLOSE_INTENT_V001"
            assert intent["receipt"]["acceptance"] == acceptance_row
            return _finish_close(root, directory, path, intent)

        ledger = b.read(path)
        before = b.row(root, path)
        assert ledger["status"] == ACTIVE_STATUS and ledger["cohort_id"] == "C008"
        recovery_ref = ledger["recovery_reservation"]
        recovery = _read(root, recovery_ref)
        assert recovery["schema"] == RECOVERY_SCHEMA and recovery["status"] == RECOVERY_STATUS
        accepted, rows = original.closed_acceptance(root, acceptance_row)
        assert accepted["reservation"] == ledger["reservation"] == recovery["original_reservation"]
        assert accepted["source_queue"] == ledger["source_queue"] == recovery["source_queue"]
        assert accepted["selected_accessions"] == recovery["selected_accessions"]
        assert accepted["genomes"] == len(rows) == 20
        plan = _read(root, accepted["source_plan"])
        assert plan["resume"]["recovery_reservation"] == recovery_ref
        assert plan["resume"]["inherited_phase_manifest"] == recovery["inherited_phase_manifest"]
        qa = _read(root, accepted["QA_commit"])
        assert qa["recovery_reservation"] == recovery_ref
        assert qa["inherited_phase_manifest"] == recovery["inherited_phase_manifest"]
        assert qa["inherited_PADLOC_phases"] == 9 and qa["new_PADLOC_phases"] == 11
        assert qa["new_DefenseFinder_phases"] == 20 and qa["actual0_stock_phases"] == 40
        assert qa["all_original_masks_preserved"] is True
        failed = _read(root, recovery["failed_disposition"])
        failed_cost = _failed_cost(ledger, failed, recovery["failed_disposition"])
        failure_tx = _read(root, recovery["failed_transaction"])
        _costs(accepted, qa, recovery, failure_tx, ledger)

        queue = _read(root, ledger["source_queue"])
        by_accession = {row["accession"]: row for row in queue["rows"]}
        assert len(by_accession) == len(queue["rows"]) == 919
        assert set(ledger["entries"]) == set(by_accession)
        for accession in accepted["selected_accessions"]:
            entry = ledger["entries"][accession]
            assert entry["state"] == "RESERVED_RECOVERY" and entry["recovery_reservation"] == recovery_ref
            ledger["entries"][accession] = {
                "state": "CLOSED_PAIRED_PROTEIN_SCOPE_ACCEPTED",
                "cohort_id": "C008",
                "acceptance": acceptance_row,
                "previous_failure_disposition": recovery["failed_disposition"],
                "recovery_reservation": recovery_ref,
                "original_source_masks_unchanged": True,
                "RNA_unavailable_models": "UNKNOWN_NOT_NEGATIVE",
                "final_QC_taxonomy_panel_or_ring_acceptance": False,
            }
        ledger["cohort_costs"]["C008"] = {
            "scientific_seconds": accepted["scientific_seconds"],
            "cold_seconds": accepted["cold_seconds"],
            "file_QA_wall_seconds_separate": accepted["file_QA_wall_seconds_separate"],
            "inherited_scientific_seconds_already_debited": recovery["prior_scientific_seconds"],
            "inherited_cold_seconds_already_debited": recovery["prior_cold_seconds"],
            "recovery_attempt_scientific_seconds": qa["attempt_scientific_seconds"],
            "recovery_attempt_cold_seconds": qa["attempt_cold_seconds"],
            "original_failed_debit": failed_cost,
            "acceptance": acceptance_row,
        }
        for measure in ("scientific_seconds", "cold_seconds"):
            ledger["known_cumulative_defence_" + measure] += qa["attempt_" + measure]
        ledger["known_closed_cohort_file_QA_wall_seconds_separate"] += accepted["file_QA_wall_seconds_separate"]

        next_ids = original.selected_next(ledger, queue["rows"])
        assert len(next_ids) == 20
        next_path = directory / "reservations/C009.json"
        next_record = {
            "schema": "TREE2_DEFENCE_IMMUTABLE_COHORT_RESERVATION_V001",
            "status": "RESERVED_NOVEL_INPUTS_NOT_YET_SCIENTIFICALLY_ADMITTED",
            "cohort_id": "C009",
            "source_queue": ledger["source_queue"],
            "source_population": 919,
            "selected_accessions": next_ids,
            "selection": "Round-robin source-family queues in frozen position order; only NOT_RUN_UNKNOWN",
            "selected_family_counts": dict(collections.Counter(by_accession[acc]["family"] for acc in next_ids)),
            "prior_closed_acceptance": acceptance_row,
            "all_holds_preserved": True,
            "scientific_admission_still_required": True,
            "at_utc": accepted["at_utc"],
        }
        next_ref = _serialized_row(root, next_path, next_record)
        for accession in next_ids:
            assert ledger["entries"][accession]["state"] == "NOT_RUN_UNKNOWN"
            ledger["entries"][accession] = {"state": "RESERVED", "cohort_id": "C009", "reservation": next_ref}
        ledger["C008_closed_recovery_reservation"] = ledger.pop("recovery_reservation")
        ledger.update(
            status="ACTIVE_RESERVED_COHORT",
            cohort_id="C009",
            reservation=next_ref,
            revision="CLOSE_C008_RECOVERY_" + acceptance_row["sha256"][:32],
            closed_paired_protein_scope_genomes=165,
            not_exhausted=True,
            at_utc=accepted["at_utc"],
        )
        assert sum(e["state"] == "CLOSED_PAIRED_PROTEIN_SCOPE_ACCEPTED" for e in ledger["entries"].values()) == 165
        previous = _archive(root, directory, path, before)
        after = _serialized_row(root, path, ledger)
        receipt = {
            "schema": "TREE2_DEFENCE_LEDGER_CLOSED_COHORT_TRANSACTION_V001",
            "closed_cohort": "C008",
            "acceptance": acceptance_row,
            "previous_ledger": previous,
            "updated_ledger_observation": after,
            "closed_paired_protein_scope_genomes": 165,
            "automatic_next_reservation": next_ref,
            "known_cumulative_scientific_seconds": ledger["known_cumulative_defence_scientific_seconds"],
            "known_cumulative_cold_seconds": ledger["known_cumulative_defence_cold_seconds"],
            "original_failed_transaction": recovery["failed_transaction"],
            "recovery_reservation": recovery_ref,
            "incremental_recovery_scientific_seconds": qa["attempt_scientific_seconds"],
            "incremental_recovery_cold_seconds": qa["attempt_cold_seconds"],
            "complete_system_rings_or_final_tree_acceptance": False,
            "not_exhausted_until_finalize": True,
            "at_utc": accepted["at_utc"],
        }
        intent = {
            "schema": "TREE2_DEFENCE_C008_RECOVERY_CLOSE_INTENT_V001",
            "before": before,
            "after": after,
            "ledger": ledger,
            "next_reservation": next_record,
            "receipt": receipt,
        }
        _publish_once(intent_path, intent)
        return _finish_close(root, directory, path, intent)


finalize = original.finalize
