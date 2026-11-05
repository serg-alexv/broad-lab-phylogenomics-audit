"""No-network immutable-resume checks and an isolated tampered-copy rejection."""
from pathlib import Path
import contextlib
import datetime
import hashlib
import io
import json
import runpy
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    module = runpy.run_path(str(ROOT / 'scripts/review_ani_nomenclature_next3.py'))
    globals_ = module['main'].__globals__
    output = globals_['OUT']
    original_session = globals_['requests'].Session
    network_attempts = []

    def no_network(*args, **kwargs):
        network_attempts.append(True)
        raise AssertionError('HTTP is forbidden during committed resume verification')

    globals_['requests'].Session = no_network
    captured = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured):
            module['main']()
        first = runpy.run_path(str(ROOT / 'scripts/review_ani_nomenclature.py'))
        with contextlib.redirect_stdout(captured):
            first['main']()
        fixture = Path(tempfile.mkdtemp(prefix='ani_next3_resume_', dir=ROOT / 'work'))
        shutil.copytree(output, fixture / 'review')
        globals_['OUT'] = fixture / 'review'
        target = globals_['OUT'] / 'summary.json'
        target.write_bytes(target.read_bytes() + b'\n ')
        rejected = False
        try:
            module['main']()
        except RuntimeError as error:
            if 'Accepted source artifact differs:' not in str(error):
                raise
            rejected = True
            tamper_error = str(error)
        assert rejected and not network_attempts
        assert module['sha'](module['FIRST'] / 'manifest.json') == module['EXPECTED_FIRST']
    finally:
        globals_['requests'].Session = original_session
        globals_['OUT'] = output
    receipt = dict(status='PASS_SOURCE_ONLY_IMMUTABLE_RESUME_AND_TAMPER_REJECTION',
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        new_committed_review_resume=json.loads(captured.getvalue().splitlines()[0]),
        preserved_first3_resume=json.loads(captured.getvalue().splitlines()[1]),
        HTTP_factory_attempts=len(network_attempts),
        tampered_copy_rejected=True, tamper_error=tamper_error,
        isolated_fixture=fixture.relative_to(ROOT).as_posix(),
        controller_sha256=sha(ROOT/'scripts/review_ani_nomenclature_next3.py'),
        test_sha256=sha(Path(__file__)),
        biological_computation=False, biological_acceptance=False)
    module['save'](ROOT / 'evidence/ani_nomenclature_next3_resume_test.json', receipt)
    module['progress']('Three source-only component reviews committed; no-fetch resume and tampered-copy rejection passed; biological relations remain unresolved',
                       'SOURCE_ONLY_REVIEW_COMPLETE_WITH_UNRESOLVED_RELATIONS', 3)
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
