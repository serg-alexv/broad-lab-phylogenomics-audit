"""Fixture-only negative/identity checks. No mount, image install or prediction."""
from pathlib import Path
import copy
import datetime
import importlib.util
import json
import os
import types
from unittest import mock

R = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pilot', R / 'scripts/checkm2_pilot.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
base = R / 'work/checkm2_image_gate_selftest'
base.mkdir(exist_ok=True)
tests = []


def reject(name, callback):
    try:
        callback()
    except RuntimeError as error:
        tests.append({'check': name, 'status': 'PASS_REJECTED', 'reason': str(error)})
    else:
        raise AssertionError(name)


saved_env = {key: os.environ.get(key) for key in
             ('TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED', 'TREE2_CHECKM2_RUNTIME_MOUNT_RECEIPT')}
saved = (p.R, p.ROOT, p.os.statvfs, p.live_loop_identity, p.mountinfo, p.subprocess.run)
try:
    os.environ.pop('TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED', None)
    reject('missing read-only marker', lambda: p.readonly_runtime_gate({}))
    os.environ['TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED'] = '1'
    reject('legacy READY cannot admit image runtime', lambda: p.readonly_runtime_gate({}))
    os.environ.pop('TREE2_CHECKM2_RUNTIME_MOUNT_RECEIPT', None)
    reject('marker alone cannot replace mount receipt',
           lambda: p.readonly_runtime_gate({'requires_private_image_mount': True}))

    p.R = p.ROOT = base
    image = base / 'tools/checkm2_runtime_ext4.img'
    image.parent.mkdir(exist_ok=True)
    image.write_bytes(b'fixture only; not a filesystem\n')
    prefix = base / 'tools/checkm2_env'
    prefix.mkdir(exist_ok=True)
    db = base / 'tools/database.dmnd'
    db.write_bytes(b'fixture only\n')
    mount = base / 'work/mount'
    mount.mkdir(parents=True, exist_ok=True)
    seal_path = base / 'seal.json'
    image_hash = p.sha(image)
    p.save(seal_path, {'status': 'SEALED_AFTER_CLEAN_UNMOUNT', 'sha256': image_hash})
    info = image.stat()
    identity = {'dev': info.st_dev, 'ino': info.st_ino, 'size': info.st_size, 'nlink': info.st_nlink}
    proof = {'status': 'READONLY_RUNTIME_MOUNT_VERIFIED', 'mount_namespace': os.readlink('/proc/self/ns/mnt'),
             'image_path': str(image), 'image_identity': identity, 'image_sha256': image_hash,
             'filesystem_uuid': 'fixture-uuid', 'prefix_linux': str(prefix), 'database_path': str(db),
             'mountpoint': str(mount), 'raw_image_readonly': True, 'canonical_prefix_readonly': True,
             'canonical_database_readonly': True, 'loop_node': '/dev/loop0', 'loop_readonly': True,
             'loop_autoclear': True, 'loop_flags': 5}
    receipt = base / 'mount.json'
    os.environ['TREE2_CHECKM2_RUNTIME_MOUNT_RECEIPT'] = str(receipt)
    ready = {'requires_private_image_mount': True, 'prefix_linux': str(prefix), 'database_path': str(db),
             'runtime_image': {'path': str(image), 'sha256': image_hash, 'bytes': info.st_size,
                               'filesystem_uuid': 'fixture-uuid', 'seal_receipt_path': str(seal_path),
                               'seal_receipt_sha256': p.sha(seal_path)}}
    p.save(receipt, {**proof, 'mount_namespace': 'mnt:[wrong-fixture]'} )
    reject('stale namespace ID', lambda: p.readonly_runtime_gate(ready))
    p.save(receipt, proof)
    # This uses the real ordinary fixture directory: no fake proof can make it read-only.
    reject('actual writable image path defeats forged read-only booleans', lambda: p.readonly_runtime_gate(ready))

    # Remaining cases simulate kernel observations only; they perform no mounts.
    loop = {'dev': info.st_dev, 'ino': info.st_ino, 'offset': 0, 'sizelimit': 0,
            'flags': 5, 'backing_path': str(image)}
    observations = {
        str(mount): {'root': '/', 'mountpoint': str(mount), 'source': '/dev/loop0', 'fstype': 'ext4',
                     'vfs_options': ['ro', 'nodev', 'nosuid'], 'fs_options': ['ro', 'norecovery']},
        str(prefix): {'root': '/env', 'mountpoint': str(prefix), 'source': '/dev/loop0', 'fstype': 'ext4',
                      'vfs_options': ['ro', 'nodev', 'nosuid'], 'fs_options': ['ro', 'norecovery']},
        str(db): {'root': '/db/uniref100.KO.1.dmnd', 'mountpoint': str(db), 'source': '/dev/loop0', 'fstype': 'ext4',
                  'vfs_options': ['ro', 'nodev', 'nosuid'], 'fs_options': ['ro', 'norecovery']}}
    flags = {str(base): 0}
    p.os.statvfs = lambda path: types.SimpleNamespace(f_flag=flags.get(str(path), os.ST_RDONLY))
    p.live_loop_identity = lambda node: copy.deepcopy(loop)
    p.mountinfo = lambda path: copy.deepcopy(observations[str(path)])
    observed_uuid = ['fixture-uuid']
    p.subprocess.run = lambda *args, **kwargs: types.SimpleNamespace(stdout='TYPE=ext4\nUUID=' + observed_uuid[0] + '\n')
    p.readonly_runtime_gate(ready)
    tests.append({'check': 'simulated complete read-only layout accepted as fixture only', 'status': 'PASS_FIXTURE_NO_MOUNT'})
    for key, value in [('flags', 4), ('offset', 1), ('ino', info.st_ino + 1)]:
        old = loop[key]
        loop[key] = value
        reject('actual loop mismatch: ' + key, lambda: p.readonly_runtime_gate(ready))
        loop[key] = old
    observed_uuid[0] = 'wrong-uuid'
    reject('actual loop filesystem UUID mismatch', lambda: p.readonly_runtime_gate(ready))
    observed_uuid[0] = 'fixture-uuid'
    old = observations[str(mount)]['fs_options']
    observations[str(mount)]['fs_options'] = ['ro']
    reject('read-only without journal-replay suppression', lambda: p.readonly_runtime_gate(ready))
    observations[str(mount)]['fs_options'] = old
    observations[str(prefix)]['root'] = '/other'
    reject('canonical prefix binds wrong image directory', lambda: p.readonly_runtime_gate(ready))
    observations[str(prefix)]['root'] = '/env'
    flags[str(prefix)] = os.ST_RDONLY | getattr(os, 'ST_NOEXEC', 8)
    reject('noexec runtime cannot be admitted', lambda: p.readonly_runtime_gate(ready))
    flags.pop(str(prefix))
    altered = copy.deepcopy(ready)
    altered['runtime_image']['seal_receipt_sha256'] = '0' * 64
    reject('READY image seal hash mismatch', lambda: p.readonly_runtime_gate(altered))

    binding = {'input': {'sha256': 'input'}, 'runtime': {'image_sha256': 'image',
                'private_readonly_runtime': {'namespace': 'one', 'loop': 0}}, 'options': {'threads': 2}}
    second = copy.deepcopy(binding)
    second['runtime']['private_readonly_runtime'] = {'namespace': 'two', 'loop': 7}
    assert p.binding_digest(binding) == p.binding_digest(second)
    tests.append({'check': 'fresh namespace/loop does not invalidate scientific resume identity', 'status': 'PASS'})
    second['runtime']['image_sha256'] = 'changed-image'
    assert p.binding_digest(binding) != p.binding_digest(second)
    tests.append({'check': 'changed runtime image invalidates scientific resume identity', 'status': 'PASS'})
    ipc = {'input': {'sha256': 'input'}, 'runtime': {'ipc_routing': {'proof_sha256': 'proven-route'},
           'private_ipc_namespace': {'namespace': 'first', 'inode': 1}}, 'options': {'threads': 2}}
    changed = copy.deepcopy(ipc)
    changed['runtime']['private_ipc_namespace'] = {'namespace': 'next', 'inode': 2}
    assert p.binding_digest(ipc) == p.binding_digest(changed)
    tests.append({'check': 'fresh private IPC namespace/inode preserves exact routing identity', 'status': 'PASS'})
    changed['runtime']['ipc_routing']['proof_sha256'] = 'another-route'
    assert p.binding_digest(ipc) != p.binding_digest(changed)
    tests.append({'check': 'changed proven IPC routing invalidates prior failure/resume identity', 'status': 'PASS'})
finally:
    p.R, p.ROOT, p.os.statvfs, p.live_loop_identity, p.mountinfo, p.subprocess.run = saved
    for key, value in saved_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

stack = ['42 1 0:99 / /tmp rw,nodev,nosuid,noexec - tmpfs private-ipc rw,size=32768k',
         '9000 1 8:0 /tmp /tmp ro - ext4 /dev/sdd rw']
with mock.patch.object(Path, 'read_text', return_value='\n'.join(stack)):
    reject('stacked alias is ambiguous without effective kernel mount identity', lambda: p.mountinfo('/tmp'))
    assert p.mountinfo('/tmp', mount_id=42)['fstype'] == 'tmpfs'
with mock.patch.object(Path, 'read_text', return_value='\n'.join(reversed(stack))):
    assert p.mountinfo('/tmp', mount_id=42)['fstype'] == 'tmpfs'
tests.append({'check': 'explicit kernel mount ID selects effective IPC alias independently of order/maximum', 'status': 'PASS'})

report = {'status': 'PASS', 'fixture_only': True, 'no_mount_operations': True,
          'no_prediction': True, 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'tests': tests, 'controller_sha256': p.sha(R / 'scripts/checkm2_pilot.py')}
p.save(R / 'evidence/checkm2_pilot/image_gate_selftest.json', report)
print(json.dumps(report))
