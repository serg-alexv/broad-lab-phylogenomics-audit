"""Pure N5 OPS fixtures: source AST only, no controller/scientific imports."""
from pathlib import Path
import ast
import json
import types

R = Path(__file__).resolve().parents[1]

def parse(name):
    return ast.parse((R/'scripts'/name).read_text(encoding='utf-8-sig'))

def function(tree, name):
    return next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)

def extracted_function(tree, name, namespace=None):
    namespace = {} if namespace is None else namespace
    exec(compile(ast.Module(body=[function(tree, name)], type_ignores=[]), '<actual N5 function AST>', 'exec'), namespace)
    return namespace[name]

def main():
    native = parse('checkm2_phase_separated_native_N5.py')
    entry = parse('checkm2_phase_separated_entry_N5.py')
    prior_native = parse('checkm2_phase_separated_native_N1.py')
    prior_entry = parse('checkm2_phase_separated_entry_N1.py')
    checks = []
    valid = {'status':'N5_CORE_PENDING_NAMESPACE_NATIVE_CLOSURE', 'completed_qc_rows':5,
             'rows':[{'accession':f'MOCK_{n}'} for n in range(5)]}
    invalid = [
        {**valid, 'completed_qc_rows':True}, {**valid, 'completed_qc_rows':5.0},
        {**valid, 'completed_qc_rows':1}, {**valid, 'completed_qc_rows':0},
        {**valid, 'rows':[]}, {**valid, 'rows':[{}]*4}, {**valid, 'rows':[{}]*6},
        {**valid, 'rows':{'five':'not a list'}},
        {**valid, 'status':'N1_CORE_PENDING_NAMESPACE_NATIVE_CLOSURE'},
        {**valid, 'completed_qc_rows':10, 'rows':[{}]*10}]
    for label, tree in [('native',native), ('entry',entry)]:
        gate = extracted_function(tree, 'require_core_result')
        assert gate(valid) == 5
        for bad in invalid:
            try: gate(bad)
            except RuntimeError: pass
            else: raise AssertionError(label+' accepted invalid/inherited result')
        checks.append(label+'_typed_five_row_result_and_ten_rejections')

    for label, tree, namespace in [('native',native,{'COMMITTED_DONE':0}), ('entry',entry,{'CONTEXT':{}})]:
        counter = extracted_function(tree, 'committed_done', namespace)
        assert counter() == 0
        assert counter(3) == 3
        for bad in [True, 4.0, -1, 6, None, '5']: assert counter(bad) == 3
        assert counter(1) == 3 and counter(5) == 5
        checks.append(label+'_fresh_zero_monotonic_typed_counter_0_to_5')

    request = next(call for call in ast.walk(native) if isinstance(call,ast.Call)
        and isinstance(call.func,ast.Attribute) and isinstance(call.func.value,ast.Name)
        and call.func.value.id == 'request' and call.func.attr == 'update')
    fields = {x.arg:ast.literal_eval(x.value) for x in request.keywords if isinstance(x.value,ast.Constant)}
    assert fields == {'cold_session_seconds':9000, 'helper_max_seconds':7760,
        'prehelper_preflight_max_seconds':600, 'post_unmount_hash_max_seconds':600, 'fatal_cleanup_seconds':40}
    assert 600 + 7760 + 600 + 40 == fields['cold_session_seconds']
    checks.append('immutable_request_cold9000_split600_7760_600_40')

    main_node = function(entry,'main')
    selected = []
    for node in main_node.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in
                ('helper_seconds','helper_deadline','helper_deadline_unix') for t in node.targets): selected.append(node)
        if (isinstance(node,ast.If) and isinstance(node.test,ast.Compare) and isinstance(node.test.left,ast.Name)
                and node.test.left.id == 'helper_seconds'): selected.append(node)
    for cold_end, expected in [(9100,7760), (900,160)]:
        namespace = {'time':types.SimpleNamespace(monotonic=lambda:100,time=lambda:1000),
            'CONTEXT':{'cold_monotonic_deadline':cold_end}}
        exec(compile(ast.Module(body=selected,type_ignores=[]),'<actual N5 helper deadline AST>','exec'),namespace)
        assert namespace['helper_seconds'] == expected
        assert namespace['helper_deadline'] == 100+expected
        assert namespace['helper_deadline_unix'] == 1000+expected
    namespace = {'time':types.SimpleNamespace(monotonic=lambda:100,time=lambda:1000),
        'CONTEXT':{'cold_monotonic_deadline':740}}
    try: exec(compile(ast.Module(body=selected,type_ignores=[]),'<empty helper window AST>','exec'),namespace)
    except TimeoutError: pass
    else: raise AssertionError('Empty helper window dispatched')
    inner_command = next(n for n in main_node.body if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id == 'inner_command' for t in n.targets))
    assert '--helper-deadline-unix' in ast.literal_eval(ast.List(
        elts=[v for v in inner_command.value.elts if isinstance(v,ast.Constant)],ctx=ast.Load()))
    checks.append('helper_deadline_capped_and_required_inner_argument_no_reset')

    locked = function(native,'locked_main')
    publish = next(n for n in ast.walk(locked) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
        and n.func.id == 'progress' and len(n.args) >= 3 and isinstance(n.args[1],ast.Constant)
        and str(n.args[1].value).startswith('Root-admitted N5'))
    spawn = next(n for n in ast.walk(locked) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
        and isinstance(n.func.value,ast.Name) and n.func.value.id == 'subprocess' and n.func.attr == 'Popen')
    assert ast.literal_eval(publish.args[2]) == 0 and publish.lineno < spawn.lineno
    argv = ast.unparse(spawn.args[0])
    assert "'/usr/bin/env'" in argv and "'TREE2_CHECKM2_PILOT_LAUNCH_TOKEN=' + TOKEN" in argv
    progress = function(native,'progress')
    source = ast.unparse(progress)
    assert "R / 'state/stages/04.json'" in source and "'creation_time_utc'" in source and "'full_command_line'" in source
    checks.append('standard04_actual_native_owner_before_explicit_Linux_env_launch')

    for name in ('identity','common_locks'):
        assert ast.dump(function(native,name),include_attributes=False) == ast.dump(function(prior_native,name),include_attributes=False)
    for name in ('save_display','record_display_error','native_identity','hash_closed_image'):
        assert ast.dump(function(entry,name),include_attributes=False) == ast.dump(function(prior_entry,name),include_attributes=False)
    checks.append('accepted_identity_partial_leases_optional_display_posthash_AST_unchanged')
    shell = (R/'scripts/checkm2_phase_separated_N5.sh').read_bytes()
    assert b'\r' not in shell and shell.startswith(b'#!/bin/bash\n')
    assert shell == (R/'scripts/checkm2_phase_separated_N1.sh').read_bytes().replace(b'N1',b'N5')
    checks.append('LF_only_shell_exact_accepted_derivative_no_shell_execution')
    print(json.dumps({'status':'PURE_AST_FIXTURES_PASS','checks':checks,'count':len(checks),
        'OPS_or_scientific_modules_imported':False,'process_runtime_transport_or_shell_executed':False},indent=2))

if __name__ == '__main__':
    main()
