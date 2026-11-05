"""Bind accepted receipt metadata to a HELD control contract; no data generation."""
from pathlib import Path
import copy
import hashlib
import json
import os

R = Path(__file__).resolve().parents[1]
TEMPLATE_SHA = 'e081c8810736409c670bc8333f0dde3a271486d5622c1bae6d3e599742e67719'
ACCEPTANCE_SHA = '0e80c5335a178d04a78864e650318c937af6030c03c2405b0ee272a4b2b27ae3'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def pin(path, expected):
    path = Path(path).resolve()
    if not path.is_relative_to(R) or sha(path) != expected:
        raise RuntimeError('Accepted baseline receipt differs or leaves project')
    return {'path': path.relative_to(R).as_posix(), 'sha256': expected, 'bytes': path.stat().st_size}


def main():
    template_path = R / 'metadata/checkm2_protein_format_invariance_v002.json'
    pin(template_path, TEMPLATE_SHA)
    template = read(template_path)
    authority_path = R / 'evidence/checkm2_posthoc_v002/root_baseline_acceptance.json'
    authority_pin = pin(authority_path, ACCEPTANCE_SHA)
    authority = read(authority_path)
    if (authority['status'] != 'ACCEPTED_AS_METHOD_BASELINE_FOR_ONE_FORMAT_CONTROL_PREPARATION' or
        authority['format_control_execution_authorized'] is not False or
        authority['production_genome_or_panel_acceptance'] != 'NOT_GRANTED'):
        raise RuntimeError('Root accepted a different scope')
    pointer_pin = pin(R / authority['latest_pointer_path'], authority['latest_pointer_sha256'])
    pointer = read(R / pointer_pin['path'])
    if pointer['status'] != 'PRESERVED_04R1_VALIDATION_V002_PASS_CLOSED':
        raise RuntimeError('Accepted posthoc pointer is not closed')
    pairs = [('validation_target', 'validation_path', 'validation_sha256'),
             ('execution', 'execution_path', 'execution_sha256'),
             ('manifest', 'closed_manifest_path', 'closed_manifest_sha256'),
             ('native_and_lease_closure', 'full_native_closure_path', 'full_native_closure_sha256')]
    chain = copy.deepcopy(template['basis']['posthoc_accepted_baseline_chain'])
    chain['latest_pointer'] = pointer_pin
    for label, path_key, hash_key in pairs:
        if pointer[hash_key] != authority[hash_key]:
            raise RuntimeError('Root/pointer baseline binding mismatch: ' + hash_key)
        chain[label] = pin(pointer[path_key], authority[hash_key])
    chain['controller_manifest_before_independent_native_closure'] = pin(pointer['manifest_path'], pointer['manifest_sha256'])
    chain['root_baseline_acceptance'] = authority_pin
    chain['binding_status'] = 'ROOT_ACCEPTED_METHOD_BASELINE_BOUND_CONTROL_EXECUTION_HELD'
    chain['canonical_float64_le_row_sha256'] = authority['canonical_float64_le_row_sha256']
    chain['accepted_method_scores'] = {'Completeness': authority['Completeness'], 'Contamination': authority['Contamination'],
                                      'role': 'Method invariance reference only; not biological truth or production acceptance'}
    result = copy.deepcopy(template)
    result['status'] = 'ROOT_ACCEPTED_BASELINE_BOUND_HELD_NO_CONTROL_ADMISSION'
    result['unbound_template'] = pin(template_path, TEMPLATE_SHA)
    result['basis']['posthoc_accepted_baseline_chain'] = chain
    result['basis']['posthoc_source_contract_declared_artifact_pins'] = result['basis'].pop('original_failed_attempt_artifact_pins_from_source_contract_only')
    result['requirements']['source_runtime_model_DB_bootstrap_IPC_and_options'] = (
        'Same original author sources, runtime image/overlay, model and DB hashes, effective bootstrap, '
        'IPC routing and scientific options. Distinct source-reviewed control wrappers and their hashes '
        'are bound independently; run/output paths and wrapper provenance differ by role.')
    result['actual_saved_baseline_outputs_opened_for_preparation'] = 'Receipt metadata only after explicit root acceptance; no raw biological contents'
    result['saved_pickle_genome_FAA_or_model_contents_opened'] = False
    result['baseline_acceptance_allows_control_execution'] = False
    result['binding_builder'] = {'path': Path(__file__).relative_to(R).as_posix(), 'sha256': sha(__file__)}
    for row in result['basis']['original_executed_sources']:
        if sha(R / row['path']) != row['sha256']:
            raise RuntimeError('Original executed source changed')
    if (result['adaptor_contract']['root_control_protocol_admission_sha256'] is not None or
        result['transform']['derived_input_sha256'] is not None):
        raise RuntimeError('HELD binding cannot invent a control admission or input')
    out = R / 'metadata/checkm2_protein_format_invariance_v002_bound.json'
    data = (json.dumps(result, indent=2) + '\n').encode('utf-8')
    if out.exists():
        if out.read_bytes() != data:
            raise RuntimeError('Bound HELD source contract is immutable')
    else:
        pending = out.with_suffix('.pending')
        with pending.open('xb') as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
        os.replace(pending, out)
    print(json.dumps({'status': result['status'], 'path': out.relative_to(R).as_posix(),
                      'sha256': sha(out), 'actual_control_runs_or_variants': 0}))


if __name__ == '__main__':
    main()
