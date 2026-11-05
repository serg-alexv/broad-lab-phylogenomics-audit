"""Read-only metadata/hash gate for the single matching-version diagnostic route."""
from pathlib import Path
import hashlib
import json
import math
import os

R = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def inside(value):
    path = Path(value)
    path = (path if path.is_absolute() else R / path).resolve()
    if not path.is_relative_to(R):
        raise RuntimeError('Effective-runtime path escapes project')
    return path


def bound(path, expected):
    path = inside(path)
    if not path.is_file() or sha(path) != expected:
        raise RuntimeError('Effective-runtime bound receipt/hash differs: ' + str(path))
    return path, read(path)


def finite(value):
    if isinstance(value, list):
        return bool(value) and all(finite(item) for item in value)
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def origins(proof, site):
    if proof.get('version') != '1.6.1' or proof.get('overlay_distribution_version') != '1.6.1':
        raise RuntimeError('Effective sklearn version was not proven')
    if not inside(proof['module_origin']).is_relative_to(site):
        raise RuntimeError('Effective sklearn origin escapes matching overlay')
    paths = list(proof.get('package_path', [])) + list(proof.get('imported_sklearn_origins', {}).values())
    if not paths or any(not inside(path).is_relative_to(site) for path in paths):
        raise RuntimeError('Mixed sklearn origins in diagnostic')


def effective_gate(ready_path, *, mounted=False, mount_proof=None):
    ready_path = inside(ready_path)
    ready = read(ready_path)
    gate_path = R / 'state/checkm2_forward_ready.json'
    if not gate_path.exists():
        raise RuntimeError('WAITING_RUNTIME_FORWARD: bound matching-version diagnostic sidecar absent')
    gate = read(gate_path)
    if gate.get('status') != 'FORWARD_DIAGNOSTIC_PASS_RESOURCE_ONLY' or gate.get('production_acceptance') is not False:
        raise RuntimeError('WAITING_RUNTIME_FORWARD: resource-only diagnostic not accepted')
    if gate.get('candidate_ready_sha256') != sha(ready_path) or gate.get('image_sha256') != ready['runtime_image']['sha256'] or gate.get('models_manifest_sha256') != ready['models_manifest_sha256']:
        raise RuntimeError('Forward diagnostic differs from current base/image/models')
    path, spec = bound(gate['effective_runtime_manifest_path'], gate['effective_runtime_manifest_sha256'])
    if spec.get('schema') != 'TREE2_EFFECTIVE_RUNTIME_VALIDATED_V1' or spec.get('status') != 'MATCHING_RUNTIME_CONTROLS_PASS_RESOURCE_ONLY' or spec.get('production_acceptance') != 'NOT_GRANTED':
        raise RuntimeError('Static or production-promoted manifest cannot authorize resource pilot')
    if spec.get('effective_import_provenance_and_native_runtime_tested') is not True or spec.get('scaler_equivalence_tested') != 'SYNTHETIC_AFFINE_FIXTURES_ALL21241_COLUMNS':
        raise RuntimeError('Matching import/scaler controls were not accepted')
    if spec['base_ready_receipt']['sha256'] != sha(ready_path) or spec['base_image']['sha256'] != ready['runtime_image']['sha256'] or spec['base_models_manifest']['sha256'] != ready['models_manifest_sha256']:
        raise RuntimeError('Effective manifest base binding differs')
    overlay = spec['overlay']
    root = inside(overlay['root_linux'])
    site = inside(overlay['site_packages_linux'])
    if root != R / 'tools/sklearn161_overlay' or site != root / 'site-packages' or overlay['effective_version'] != '1.6.1':
        raise RuntimeError('Only the approved complete matching-version overlay is eligible')
    manifest_path, payload = bound(overlay['manifest_path'], overlay['manifest_sha256'])
    if gate.get('overlay_manifest_sha256') != overlay['manifest_sha256'] or inside(gate['overlay_manifest_path']) != manifest_path:
        raise RuntimeError('Forward overlay binding differs')
    wheel = inside(overlay['wheel_path'])
    if wheel.stat().st_size != overlay['wheel_bytes'] or sha(wheel) != overlay['wheel_sha256'] or payload.get('wheel_sha256') != overlay['wheel_sha256']:
        raise RuntimeError('Official matching wheel integrity differs')
    protocol = spec['launch_protocol']
    if protocol.get('bootstrap_required') is not True or protocol.get('bootstrap_status') != 'PRELOAD_POST_MAIN_ORIGINS_CLI_AND_CONTROLS_VERIFIED' or protocol.get('author_entrypoint_source_modified') is not False:
        raise RuntimeError('Unchanged-entrypoint preload route was not validated')
    bootstrap = inside(protocol['bootstrap_path'])
    if sha(bootstrap) != protocol['bootstrap_sha256'] or gate.get('bootstrap_sha256') != protocol['bootstrap_sha256'] or inside(gate['bootstrap_path']) != bootstrap:
        raise RuntimeError('Audited workflow bootstrap changed')
    controls = spec['required_runtime_environment']
    if set(controls) != {'GLIBC_TUNABLES', 'PYTHONPATH', 'PYTHONNOUSERSITE', 'PYTHONDONTWRITEBYTECODE'} or controls['PYTHONPATH'] != str(site) or controls['PYTHONNOUSERSITE'] != '1' or controls['PYTHONDONTWRITEBYTECODE'] != '1' or controls['GLIBC_TUNABLES'] != ready['runtime_environment_overrides']['GLIBC_TUNABLES'] or gate.get('runtime_environment_overrides') != controls:
        raise RuntimeError('Effective process controls differ from tested route')
    execution_path, execution = bound(gate['receipt_path'], gate['receipt_sha256'])
    if execution_path != inside(spec['runtime_validation_receipt_path']) or gate['receipt_sha256'] != spec['runtime_validation_receipt_sha256'] or execution.get('status') != 'MATCHING_RUNTIME_CONTROLS_PASS_RESOURCE_ONLY' or execution.get('host_registry_unchanged') is not True or execution.get('production_acceptance') is not False or execution.get('genome_inputs_used') != 0 or execution.get('inside_result', {}).get('all_owned_smoke_groups_closed') is not True:
        raise RuntimeError('Diagnostic execution/closure gate differs')
    closure_path, closure = bound(gate['closure_proof_path'], gate['closure_proof_sha256'])
    if closure.get('status') != 'CLEAN_UNMOUNT_AND_LOOP_DETACH' or closure.get('readonly') is not True or closure.get('errors'):
        raise RuntimeError('Diagnostic read-only namespace closure not proven')
    control_path, control = bound(spec['control_receipt_path'], spec['control_receipt_sha256'])
    if control.get('status') != 'MATCHING_VERSION_FORWARD_CONTROLS_PASS_RESOURCE_ONLY' or control.get('effective_sklearn_version') != '1.6.1' or control.get('scaler_saved_version') != '1.6.1' or control.get('inconsistent_version_warnings') or control.get('production_acceptance') is not False or control.get('genome_inputs_used') != 0 or control.get('all_original_model_assets_verified') is not True:
        raise RuntimeError('Matching-version forward controls were not accepted')
    if control.get('runtime_environment_overrides') != controls or control.get('bootstrap_sha256') != protocol['bootstrap_sha256']:
        raise RuntimeError('Control execution route differs')
    for proof in (control['import_proof']['before'], control['import_proof']['after'], control['post_control_provenance']):
        origins(proof, site)
    oracle = control['scaler_oracle']
    if oracle.get('columns_tested') != 21241 or oracle.get('all_columns_within_tolerance') is not True or oracle.get('rtol') != 1e-12 or oracle.get('atol') != 1e-12 or not finite(oracle['maximum_absolute_difference']):
        raise RuntimeError('Full-column scaler formula diagnostic incomplete')
    dims = control['feature_dimensions']
    if dims.get('general') != 21241 or dims.get('contamination') != 21241 or dims.get('specific_sequence') != 20021 or dims.get('specific_channels') != 1:
        raise RuntimeError('Forward dimensions differ')
    output = control['synthetic_outputs']
    rows = oracle.get('rows')
    if not isinstance(rows, int) or rows < 4 or any(len(output[name]) != rows or not finite(output[name]) for name in ('general', 'contamination', 'specific_unscaled')):
        raise RuntimeError('Forward diagnostic output is missing/nonfinite')
    choices = control.get('selection_fixtures', [])
    if len(choices) != 5 or any(row['actual'] != row['expected'] or not finite(row['synthetic_value']) for row in choices) or control.get('sparse_cosine_zero_norm_fixture') != 'PASS' or control.get('upstream_specific_composition') != 'MATCH_FOR_SYNTHETIC_FIXTURES_ONLY':
        raise RuntimeError('Cosine/selection/composition diagnostic incomplete')
    if mounted:
        accepted = (mount_proof or {}).get('validated_effective_runtime_manifest', {})
        if accepted.get('sha256') != gate['effective_runtime_manifest_sha256'] or inside(accepted['path']) != path or os.environ.get('TREE2_EFFECTIVE_RUNTIME_MANIFEST_SHA256') != gate['effective_runtime_manifest_sha256'] or inside(os.environ['TREE2_EFFECTIVE_RUNTIME_MANIFEST']) != path:
            raise RuntimeError('Mounted effective-runtime manifest does not match validated route')
        if any(os.environ.get(key) != value for key, value in controls.items()):
            raise RuntimeError('Actual startup environment differs from matching diagnostic')
        proof = (mount_proof or {}).get('effective_overlay', {})
        if proof.get('readonly') is not True or proof.get('manifest_sha256') != overlay['manifest_sha256'] or inside(proof['root']) != root or not os.statvfs(root).f_flag & os.ST_RDONLY:
            raise RuntimeError('Actual matching overlay is not bound read-only')
        rows = payload['files']
        if len(rows) != 894 or proof.get('files_verified') != len(rows):
            raise RuntimeError('Complete overlay coverage differs')
        for row in rows:
            member = inside(root / row['path'])
            if not member.is_relative_to(root) or member.stat().st_size != row['bytes'] or sha(member) != row['sha256']:
                raise RuntimeError('Read-only overlay member changed')
    return {'manifest_path': str(path), 'manifest_sha256': gate['effective_runtime_manifest_sha256'],
        'sidecar_path': str(gate_path), 'sidecar_sha256': sha(gate_path),
        'required_environment': controls, 'overlay_root': str(root), 'overlay_manifest_sha256': overlay['manifest_sha256'],
        'bootstrap_path': str(bootstrap), 'bootstrap_sha256': protocol['bootstrap_sha256'],
        'diagnostic_execution_path': str(execution_path), 'control_receipt_path': str(control_path),
        'compatibility_status': gate['compatibility_status'], 'production_acceptance': 'NOT_GRANTED',
        'official_numeric_controls_tested': False, 'wheel_sha256': overlay['wheel_sha256']}
