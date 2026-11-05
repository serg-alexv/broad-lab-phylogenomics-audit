"""Durable, file-only QC queue control. Emits intentions; never launches science or AI."""
from pathlib import Path
from contextlib import contextmanager
import argparse, hashlib, json, os, uuid

QUEUE_SCHEMA = 'TREE2_CANONICAL_QC_QUEUE_V001'
INTENT_SCHEMA = 'TREE2_DURABLE_QC_QUEUE_INTENT_V001'
REPAIR = {'SAVED_VALIDATION_PENDING_NO_UPSTREAM_REPLAY', 'RESERVED_P20_UNSTARTED'}
STATES = REPAIR | {'READY_FRESH_QC', 'HISTORICAL_DONOR_REVIEW_REUSE_ONLY', 'ACCEPTED_METHOD_REUSE_VERIFIED', 'NOT_RUN_SOURCE_HELD', 'NOT_ACQUIRED_OPTIONAL_MAIN_STRAIN'}


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode('utf-8')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def contained(root, name):
    value = Path(name); value = (value if value.is_absolute() else root / value).resolve()
    if not value.is_relative_to(root) or value.is_relative_to(root / 'work/local_continuation/codex_home'):
        raise RuntimeError('Queue-control artifact leaves permitted project data')
    return value


def bind(root, ref):
    value = contained(root, ref['path'])
    if value.is_symlink() or not value.is_file() or sha(value) != ref['sha256'] or value.stat().st_size != ref['bytes']:
        raise RuntimeError('Queue-control artifact binding changed: ' + str(value))
    return value


def row(root, path):
    return {'path': Path(path).relative_to(root).as_posix(), 'sha256': sha(path), 'bytes': Path(path).stat().st_size}


def create(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(encoded(value)); stream.flush(); os.fsync(stream.fileno())


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True); tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.partial')
    create(tmp, value); os.replace(tmp, path)


@contextmanager
def lock(path):
    import msvcrt
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as stream:
        if path.stat().st_size == 0:
            stream.write(b'0'); stream.flush()
        stream.seek(0); msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            yield
        finally:
            stream.seek(0); msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


def queue_gate(queue):
    if queue.get('schema') != QUEUE_SCHEMA or not isinstance(queue.get('rows'), list):
        raise RuntimeError('Canonical immutable queue required')
    ids = [r['queue_id'] for r in queue['rows']]; order = [r['frozen_order'] for r in queue['rows']]
    if len(ids) != len(set(ids)) or len(order) != len(set(order)) or any(type(n) is not int or n < 0 for n in order):
        raise RuntimeError('Duplicate queue identity/order or untyped frozen order')
    if any(not isinstance(n, str) or not n for n in ids):
        raise RuntimeError('Missing versioned queue member identity')
    if any(r.get('qc_execution_state') not in STATES or type(r.get('source_supported_scope')) is not bool for r in queue['rows']):
        raise RuntimeError('Unknown queue execution state/scope; never treat unknown as completed')
    if any(r['qc_execution_state'] == 'ACCEPTED_METHOD_REUSE_VERIFIED' and r.get('method_estimate_hashes_verified') is not True for r in queue['rows']):
        raise RuntimeError('An accepted queue seed requires verified method-result hashes')
    return {r['queue_id']: r for r in queue['rows']}


def decide(queue, events, batch_size):
    """Pure policy: resolve current failed P20 first, then fresh frozen-order cohorts."""
    members = queue_gate(queue)
    if type(batch_size) is not int or not 1 <= batch_size <= 20:
        raise RuntimeError('Reviewed cohort size must be in1..20')
    completed = set(); claimed = set(); opened = {}; failed = {}
    for event in events:
        kind = event['kind']; ids = event['queue_ids']
        if not ids or len(ids) != len(set(ids)) or not set(ids) <= set(members):
            raise RuntimeError('Ledger contains invalid/repeated/unknown queue members')
        if kind == 'RESERVED':
            if set(ids) & claimed:
                raise RuntimeError('Queue member claimed twice; no silent retry')
            claimed.update(ids); opened[event['proposal_sha256']] = event
        elif kind in ('ACCEPTED_CLOSED', 'FAILED_CLOSED'):
            key = event['proposal_sha256']
            original = opened.get(key) or failed.get(key)
            if original is None or original['queue_ids'] != ids:
                raise RuntimeError('Closed cohort does not match its exact reservation')
            if key in failed:
                if kind != 'ACCEPTED_CLOSED' or event.get('prior_failed_authority_sha256') != failed[key]['authority']['sha256'] or event.get('repaired_without_replaying_accepted_phases') is not True:
                    raise RuntimeError('Closed failure requires exact Root repair/retained-debit authority')
                del failed[key]
            else:
                del opened[key]
            if kind == 'ACCEPTED_CLOSED':
                completed.update(ids)
            else:
                failed[key] = event
        else:
            raise RuntimeError('Unknown queue ledger event')
    if opened:
        return {'status': 'ACTIVE_RESERVED_COHORT', 'action': 'OBSERVE_OWNED_COHORT_OR_RESOLVE_CLOSURE', 'reservations': list(opened.values()), 'queue_ids': [], 'science_execution_authorized': False}
    if failed:
        ids = [value for event in failed.values() for value in event['queue_ids']]
        return {'status': 'REPAIR_PENDING', 'action': 'REPAIR_CLOSED_LEDGER_COHORT', 'failed_cohorts': list(failed.values()), 'queue_ids': ids, 'rows': [members[value] for value in ids], 'explicit_Root_repair_admission_required': True, 'science_execution_authorized': False}
    ordered = sorted(members.values(), key=lambda r: r['frozen_order'])
    pending = [r for r in ordered if r['queue_id'] not in completed and r['qc_execution_state'] in REPAIR and r.get('source_supported_scope') is True]
    if pending:
        pending.sort(key=lambda r: r.get('reserved_P20_order', r['frozen_order']))
        return {'status': 'NEXT_ACTION_PROPOSED', 'action': 'REPAIR_CURRENT_P20', 'queue_ids': [r['queue_id'] for r in pending], 'rows': pending, 'upstream_phase_replay_authorized': False, 'fresh_science_admission_required': True, 'science_execution_authorized': False}
    fresh = [r for r in ordered if r['queue_id'] not in claimed and r['qc_execution_state'] == 'READY_FRESH_QC' and r.get('source_supported_scope') is True]
    if fresh:
        chosen = fresh[:batch_size]
        return {'status': 'NEXT_ACTION_PROPOSED', 'action': 'RUN_FRESH_COHORT', 'queue_ids': [r['queue_id'] for r in chosen], 'rows': chosen, 'fresh_remaining_before_reservation': len(fresh), 'fresh_science_admission_required': True, 'science_execution_authorized': False}
    historical = [r for r in ordered if r['queue_id'] not in completed and r['qc_execution_state'] == 'HISTORICAL_DONOR_REVIEW_REUSE_ONLY' and r.get('source_supported_scope') is True]
    if historical:
        return {'status': 'RECONCILIATION_PENDING', 'action': 'REVIEW_HISTORICAL_RESULTS_REUSE_ONLY', 'queue_ids': [r['queue_id'] for r in historical], 'rows': historical, 'upstream_phase_replay_authorized': False, 'science_execution_authorized': False}
    return {'status': 'CANDIDATE_QUEUE_DRAIN_REQUIRES_REGISTRY_RECONCILIATION', 'action': 'VERIFY_CURRENT_ACCEPTED_REGISTRY_AND_CLOSED_RESULTS', 'queue_ids': [], 'newly_closed_method_rows': len(completed), 'nonrunnable_inventory_rows': sum(r.get('source_supported_scope') is not True for r in ordered), 'tree_or_panel_completion_claimed': False, 'science_execution_authorized': False}


class Control:
    def __init__(self, root, intent_path, intent_sha):
        self.root = Path(root).resolve(); intent_path = contained(self.root, intent_path)
        if sha(intent_path) != intent_sha:
            raise RuntimeError('Durable queue intent SHA changed')
        self.intent = read(intent_path); self.intent_ref = row(self.root, intent_path)
        if self.intent.get('schema') != INTENT_SCHEMA or self.intent.get('automatic_boundary_advancement_authorized') is not True or self.intent.get('science_execution_authorized') is not False:
            raise RuntimeError('Explicit queue-control intent required; this helper cannot admit science')
        self.queue_ref = self.intent['queue']; self.queue = read(bind(self.root, self.queue_ref)); queue_gate(self.queue)
        self.directory = contained(self.root, self.intent['state_directory']); self.events_dir = self.directory / 'events'; self.head_path = self.directory / 'HEAD.json'
        if self.directory != self.root / 'state/qc_campaign_queue_v1':
            raise RuntimeError('Queue-control ledger requires its separate reviewed namespace')
        self.batch_size = self.intent['max_fresh_cohort_size']

    def ledger(self):
        files = sorted(self.events_dir.glob('*.json')) if self.events_dir.exists() else []
        head = read(self.head_path) if self.head_path.exists() else None
        if not files:
            if head:
                raise RuntimeError('Missing ledger events under existing head')
            return [], None
        if not head or head['event'] != row(self.root, files[-1]):
            raise RuntimeError('Incomplete ledger commit; preserve and reconcile, no automatic replay')
        previous = None; events = []
        for index, path in enumerate(files, 1):
            event = read(path)
            if event['sequence'] != index or event['previous_sha256'] != previous or event['queue_sha256'] != self.queue_ref['sha256']:
                raise RuntimeError('Queue ledger chain/source binding changed')
            if path.name != f"{index:06d}_" + sha(path) + '.json':
                raise RuntimeError('Queue ledger filename/content SHA mismatch')
            if event['kind'] == 'RESERVED':
                proposal = read(bind(self.root, event['proposal']))
                if (event['proposal']['sha256'] != event['proposal_sha256']
                        or proposal.get('queue') != self.queue_ref or proposal.get('queue_ids') != event['queue_ids']):
                    raise RuntimeError('Stored reservation proposal no longer matches the queue')
            elif event['kind'] in ('ACCEPTED_CLOSED', 'FAILED_CLOSED'):
                authority = read(bind(self.root, event['authority']))
                expected = 'ROOT_ACCEPTED_CLOSED_COHORT_FOR_QUEUE_ADVANCE' if event['kind'] == 'ACCEPTED_CLOSED' else 'ROOT_FAILED_CLOSED_COHORT_REPAIR_REQUIRED'
                if (authority.get('queue_sha256') != self.queue_ref['sha256']
                        or authority.get('proposal_sha256') != event['proposal_sha256']
                        or authority.get('queue_ids') != event['queue_ids'] or authority.get('status') != expected
                        or not authority.get('closure_and_result_evidence')):
                    raise RuntimeError('Stored Root closure authority differs from its accepted ledger event')
                for evidence in authority['closure_and_result_evidence']:
                    bind(self.root, evidence)
            events.append(event); previous = sha(path)
        return events, previous

    def append(self, body):
        events, previous = self.ledger()
        event = {'schema': 'TREE2_QC_QUEUE_LEDGER_EVENT_V001', 'sequence': len(events) + 1, 'previous_sha256': previous, 'queue_sha256': self.queue_ref['sha256'], **body}
        digest = hashlib.sha256(encoded(event)).hexdigest(); path = self.events_dir / f"{len(events) + 1:06d}_{digest}.json"
        create(path, event); atomic(self.head_path, {'event': row(self.root, path)})
        return row(self.root, path)

    def reconcile(self):
        events, head = self.ledger(); decision = decide(self.queue, events, self.batch_size)
        registry_pointer = self.directory / 'registry_reconciliation.json'
        if decision['status'] == 'CANDIDATE_QUEUE_DRAIN_REQUIRES_REGISTRY_RECONCILIATION' and registry_pointer.exists():
            ref = read(registry_pointer); final = read(bind(self.root, ref))
            self.registry_gate(final, head)
            decision.update(status='ELIGIBLE_QC_QUEUE_EXHAUSTED_WITH_EXPLICIT_MASKS', action='ADVANCE_AFTER_FULL_QC_RECONCILIATION', final_registry_authority=ref)
        if decision['status'] == 'ACTIVE_RESERVED_COHORT':
            decision['launch_contexts'] = []
            for event in decision['reservations']:
                digest = hashlib.sha256(encoded(event)).hexdigest()
                event_ref = row(self.root, self.events_dir / f"{event['sequence']:06d}_{digest}.json")
                context = {'queue_intent': self.intent_ref, 'canonical_QC_queue': self.queue_ref,
                           'queue_proposal': event['proposal'], 'queue_reservation': event_ref, 'queue_ids': event['queue_ids']}
                context_path = self.directory / 'launch_contexts' / (event['proposal_sha256'] + '.json')
                if not context_path.exists():
                    create(context_path, context)  # Recover only missing metadata, never a scientific invocation.
                elif read(context_path) != context:
                    raise RuntimeError('Reserved launch context changed')
                decision['launch_contexts'].append(row(self.root, context_path))
        document = {'schema': 'TREE2_QC_QUEUE_NEXT_ACTION_V001', 'queue': self.queue_ref, 'intent': self.intent_ref, 'ledger_head_sha256': head, **decision}
        digest = hashlib.sha256(encoded(document)).hexdigest(); path = self.directory / 'proposals' / (digest + '.json')
        if not path.exists():
            create(path, document)
        ref = row(self.root, path); atomic(self.directory / 'pending_intent.json', {'status': decision['status'], 'action': decision['action'], 'proposal': ref, 'queue': self.queue_ref, 'science_execution_authorized': False})
        return ref, document

    def registry_gate(self, authority, head):
        expected = {r['queue_id'] for r in self.queue['rows'] if r['source_supported_scope'] is True}
        values = authority.get('verified_qc_queue_ids', [])
        if (authority.get('schema') != 'TREE2_ROOT_QC_QUEUE_REGISTRY_RECONCILIATION_V001'
                or authority.get('status') != 'ROOT_VERIFIED_ELIGIBLE_QC_QUEUE_DRAIN_WITH_MASKS'
                or authority.get('queue_sha256') != self.queue_ref['sha256']
                or authority.get('ledger_head_sha256') != head or set(values) != expected or len(values) != len(expected)
                or authority.get('scientific_validation_and_closed_receipts_reconciled') is not True
                or authority.get('source_taxonomy_and_unknown_masks_preserved') is not True
                or authority.get('tree_or_panel_completion_claimed') is not False):
            raise RuntimeError('Final current-registry/closed-receipt scope reconciliation missing or stale')
        bind(self.root, authority['current_accepted_registry'])
        if not authority.get('closure_validation_evidence'):
            raise RuntimeError('No actual registry/closure validation evidence')
        for ref in authority['closure_validation_evidence']:
            bind(self.root, ref)

    def finalize(self, authority_ref):
        _, decision = self.reconcile()
        if decision['status'] not in ('CANDIDATE_QUEUE_DRAIN_REQUIRES_REGISTRY_RECONCILIATION', 'ELIGIBLE_QC_QUEUE_EXHAUSTED_WITH_EXPLICIT_MASKS'):
            raise RuntimeError('Runnable or unresolved queue entries remain; no exhaustion')
        authority = read(bind(self.root, authority_ref)); self.registry_gate(authority, self.ledger()[1])
        atomic(self.directory / 'registry_reconciliation.json', authority_ref)
        return self.reconcile()

    def reserve(self, proposal_ref):
        proposal = read(bind(self.root, proposal_ref)); current_ref, current = self.reconcile()
        if proposal_ref != current_ref or proposal != current or proposal.get('status') not in ('NEXT_ACTION_PROPOSED', 'RECONCILIATION_PENDING'):
            raise RuntimeError('Proposal is stale/not reservable; no repeated claim')
        ids = proposal['queue_ids']
        reservation = self.append({'kind': 'RESERVED', 'proposal_sha256': proposal_ref['sha256'], 'proposal': proposal_ref, 'queue_ids': ids, 'action': proposal['action'], 'science_execution_authorized': False})
        context = {'queue_intent': self.intent_ref, 'canonical_QC_queue': self.queue_ref, 'queue_proposal': proposal_ref, 'queue_reservation': reservation, 'queue_ids': ids}
        path = self.directory / 'launch_contexts' / (proposal_ref['sha256'] + '.json'); create(path, context)
        self.reconcile()
        return row(self.root, path)

    def close(self, authority_ref):
        authority = read(bind(self.root, authority_ref))
        if authority.get('schema') != 'TREE2_ROOT_QC_QUEUE_COHORT_CLOSURE_V001' or authority.get('queue_sha256') != self.queue_ref['sha256']:
            raise RuntimeError('Root cohort closure authority bound to this queue required')
        if authority.get('owned_group_namespace_image_lease_closure_verified') is not True or authority.get('prior_claims_and_debits_preserved') is not True:
            raise RuntimeError('Missing actual closure/debit preservation; no next cohort')
        for ref in authority['closure_and_result_evidence']:
            bind(self.root, ref)
        if not authority['closure_and_result_evidence']:
            raise RuntimeError('Closure requires bound actual evidence')
        success = authority.get('status') == 'ROOT_ACCEPTED_CLOSED_COHORT_FOR_QUEUE_ADVANCE'
        if success:
            if authority.get('scientific_validation_passed') is not True or type(authority.get('actual_native_exit_code')) is not int or authority['actual_native_exit_code'] != 0:
                raise RuntimeError('No accepted cohort from missing/failed validation or unknown/native-nonzero exit')
        elif authority.get('status') != 'ROOT_FAILED_CLOSED_COHORT_REPAIR_REQUIRED':
            raise RuntimeError('Unknown Root queue closure disposition')
        events, _ = self.ledger()
        if any(e.get('authority', {}).get('sha256') == authority_ref['sha256'] for e in events):
            return self.reconcile()  # Idempotent same authority, never repeat a completed cohort.
        body = {'kind': 'ACCEPTED_CLOSED' if success else 'FAILED_CLOSED', 'proposal_sha256': authority['proposal_sha256'], 'queue_ids': authority['queue_ids'], 'authority': authority_ref, 'prior_failed_authority_sha256': authority.get('prior_failed_authority_sha256'), 'repaired_without_replaying_accepted_phases': authority.get('repaired_without_replaying_accepted_phases'), 'science_execution_authorized': False}
        # Validate the prospective transition before committing it.
        decide(self.queue, events + [body], self.batch_size)
        self.append(body)
        return self.reconcile()  # Concrete automatic next-cohort hook after an accepted event.


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--project-root', required=True); parser.add_argument('--intent', required=True); parser.add_argument('--intent-sha256', required=True)
    parser.add_argument('operation', choices=['next', 'reserve', 'close', 'finalize']); parser.add_argument('--artifact'); parser.add_argument('--artifact-sha256'); parser.add_argument('--artifact-bytes', type=int)
    args = parser.parse_args(); controller = Control(args.project_root, args.intent, args.intent_sha256)
    with lock(controller.directory / 'queue_control.lock'):
        ref = {'path': args.artifact, 'sha256': args.artifact_sha256, 'bytes': args.artifact_bytes}
        result = controller.reconcile() if args.operation == 'next' else controller.reserve(ref) if args.operation == 'reserve' else controller.close(ref) if args.operation == 'close' else controller.finalize(ref)
        if isinstance(result, tuple):
            ref, value = result
            print(json.dumps({'proposal': ref, 'status': value['status'], 'action': value['action'], 'queue_ids': value['queue_ids']}))
        else:
            print(json.dumps(result))


if __name__ == '__main__':
    main()
