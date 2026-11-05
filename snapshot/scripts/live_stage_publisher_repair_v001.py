"""Tree2 presentation-only publisher with versioned custody evidence."""
from pathlib import Path
import ctypes
import msvcrt
import os
import time

import live_stage_publisher_reboot_v001 as prior
import local_tree2_dispatcher as state


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'metadata/monitor_publisher_repair_20261105'
INTERVAL = 30
LOCK = ROOT / 'state/live_publisher.lock'
STOP = ROOT / 'state/LIVE_PROGRESS_STOP'
JOURNAL = ROOT / 'state/live_stages.json'


def recovery_detail(stage, win):
    pointer = prior.read('state/local_continuation_current_runtime.json', {})
    if pointer.get('state_directory') != 'state/local_continuation_v8':
        return
    handoff = prior.read('state/local_continuation_v8/handoff.json', {})
    worker = handoff.get('worker', {})
    if (handoff.get('status') != 'WAITING_WORKER'
            or not worker.get('role', '').startswith('DEFENCE_C008R_')
            or stage.get('status') != 'RUNNING'
            or stage.get('pid') != worker.get('pid')
            or stage.get('creation_time_utc') != worker.get('creation_time_utc')):
        return
    try:
        handle = win.open_worker(worker)
    except (OSError, RuntimeError):
        return
    try:
        if win.wait(handle, 0):
            return
    finally:
        win.close(handle)
    done, total = stage.get('done'), stage.get('total')
    if type(done) is not int or total != 40 or not 9 <= done <= total:
        return
    accession = stage.get('current_profile')
    operation = str(stage.get('operation', '')).upper()
    engine = 'DefenseFinder' if 'DEFENSEFINDER' in operation else 'PADLOC' if 'PADLOC' in operation else 'defence'
    stage['detail'] = f'C008R {done}/40 phases (9 reused, {done - 9} new) | {engine} {accession or ""}'.rstrip()
    stage['unit'] = 'engine phases including nine saved PADLOC results'
    stage['presentation_exact_owner_verified'] = True


def main():
    if os.environ.get('COMPUTERNAME', '').upper() != 'WD' or STOP.exists():
        raise RuntimeError('WD presentation publisher is held')
    win = state.Windows()
    owner = win.identity(ctypes.c_void_p(-1), os.getpid())
    source = state.row(ROOT, Path(__file__).resolve())
    with LOCK.open('r+b') as lease:
        if len(lease.read()) != 1:
            raise RuntimeError('Established publisher lease byte is absent')
        lease.seek(0)
        msvcrt.locking(lease.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            state.exclusive(EVIDENCE / 'owner.json', {
                'identity': owner, 'source': source, 'refresh_seconds': INTERVAL,
                'role': 'PRESENTATION_ONLY_NO_SCIENCE_OR_MODEL_CALLS', 'at_utc': state.utc(),
            })
            while not STOP.exists():
                data = prior.build()
                recovery_detail(data['stages'][10], win)
                data['publisher_identity'] = owner
                data['publisher_refresh_seconds'] = INTERVAL
                prior.atomic(JOURNAL, data)
                time.sleep(INTERVAL)
        finally:
            lease.seek(0)
            msvcrt.locking(lease.fileno(), msvcrt.LK_UNLCK, 1)


if __name__ == '__main__':
    main()
