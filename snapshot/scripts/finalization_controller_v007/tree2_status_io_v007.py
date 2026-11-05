"""Bounded OPTIONAL Tree2 dispatcher display publication; no control or receipt IO.

The legacy source/license notices remain in the byte-pinned source modules.
Only a caller's exact dispatcher_status.json destination is eligible here.
"""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import time
import uuid


RETRY_SECONDS = 2.0
RETRY_WINERRORS = frozenset((5, 32, 33))


@dataclass(frozen=True)
class Publication:
    published: bool
    attempts: int
    elapsed_seconds: float
    winerror: int | None = None


def optional_status_replace(path, value, *, expected_path, replace=None,
                            monotonic=None, sleep=None):
    """Stage once, then retry the SAME replacement for <=2 seconds.

    Only classified PermissionError from os.replace is optional. Staging,
    serialization, fsync, other destinations and other errors remain strict.
    The deadline bounds retry scheduling; an OS syscall cannot be preempted.
    """
    path, expected_path = Path(path).resolve(), Path(expected_path).resolve()
    if path != expected_path or path.name != 'dispatcher_status.json':
        raise ValueError('Only the exact optional dispatcher status is eligible')
    replace = os.replace if replace is None else replace
    monotonic = time.monotonic if monotonic is None else monotonic
    sleep = time.sleep if sleep is None else sleep
    started = monotonic()
    deadline = started + RETRY_SECONDS
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.partial')
    attempts, delay, created = 0, .05, False
    try:
        with temp.open('x', encoding='utf-8', newline='\n') as stream:
            created = True
            json.dump(value, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        while True:
            attempts += 1
            try:
                replace(temp, path)
                return Publication(True, attempts, monotonic() - started)
            except PermissionError as error:
                if getattr(error, 'winerror', None) not in RETRY_WINERRORS:
                    raise
                remaining = deadline - monotonic()
                if remaining <= 0:
                    return Publication(False, attempts, monotonic() - started,
                                       error.winerror)
                sleep(min(delay, remaining))
                delay = min(.25, delay * 2)
                if monotonic() >= deadline:
                    return Publication(False, attempts, monotonic() - started,
                                       error.winerror)
    finally:
        # This helper may remove only its own exclusively created sibling.
        if created:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
