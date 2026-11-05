"""Pure source fixtures; imports no supervisor, creates no process or handle."""
from pathlib import Path
import ast
import hashlib
import json
import re

R=Path(__file__).resolve().parents[1]

def main():
    source=R/'scripts/local_tree2_dispatcher_supervisor_v003.py'
    tree=ast.parse(source.read_text(encoding='utf-8-sig'))
    names={'cause_hash','exact_owner','terminal_gate','may_repair','close_popen_handle'}
    functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    ns={'hashlib':hashlib,'json':json,'re':re}
    exec(compile(ast.Module(body=functions,type_ignores=[]),'<actual supervisor pure AST>','exec'),ns)
    owner={'pid':1234,'windows_creation_filetime_100ns':134000000000000007,
        'creation_time_utc':'2026-10-27T13:00:00.0000007Z'}
    core={'path':'scripts/local_tree2_dispatcher_v003.py','sha256':'a'*64,'bytes':99}
    config={'path':'config/local_continuation_dispatcher_v003.json','sha256':'b'*64,'bytes':98}
    cause={'code':'DISPATCHER_EXCEPTION','type':'PermissionError','last_operation':'V3_EVENT_LOOP','operation_path':None,'message_template':'denied optional file'}
    key=ns['cause_hash'](cause)
    good={'schema':'TREE2_DISPATCHER_TERMINAL_ERROR_V3','dispatcher_owner':owner,
        'core_source':core,'config':config,'rootcause':cause,'rootcause_sha256':key,
        'root_cause_sha256':key,'no_science_retry':True}
    assert ns['terminal_gate'](good,owner,core,config)==(cause,key)
    checks=['exact_current_owner_source_config_structured_cause_gate']
    bads=[{**good,'dispatcher_owner':{**owner,'windows_creation_filetime_100ns':8}},
        {**good,'dispatcher_owner':None},{**good,'core_source':{**core,'sha256':'c'*64}},
        {**good,'config':{**config,'sha256':'d'*64}},
        {**good,'rootcause_sha256':'e'*64},{**good,'root_cause_sha256':'e'*64},
        {**good,'no_science_retry':False},{**good,'rootcause':{**cause,'message':'not a fixed cause key'}},
        {**good,'rootcause':{**cause,'operation_path':123}}]
    for bad in bads:
        try:ns['terminal_gate'](bad,owner,core,config)
        except RuntimeError:pass
        else:raise AssertionError('Stale/mismatched terminal accepted')
    checks.append('nine_stale_or_malformed_terminal_rejections')
    assert ns['exact_owner'](owner,dict(owner)) is True
    assert ns['exact_owner']({**owner,'pid':True},owner) is False
    assert ns['exact_owner']({**owner,'creation_time_utc':'2026-10-27T13:00:00Z'},owner) is False
    checks.append('typed_PID_filetime_and_exact_seven_digit_birth')
    assert ns['may_repair'](True,0,2,False) is True
    for args in [(False,0,2,False),(True,1,2,False),(True,0,0,False),
                 (True,0,True,False),(True,False,2,False),(True,0,2,True)]:
        assert ns['may_repair'](*args) is False
    checks.append('one_explicit_process_repair_only_and_no_claim_reuse')
    class Handle:
        def __init__(self):self.closed=0
        def Close(self):self.closed+=1
    class Child:pass
    child=Child(); handle=Handle(); child._handle=handle
    ns['close_popen_handle'](child);ns['close_popen_handle'](child)
    assert handle.closed==1 and child._handle is None
    checks.append('retained_Popen_handle_closed_exactly_once_mock')
    calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)]
    assert not any(isinstance(n.func,ast.Attribute) and n.func.attr in
        ('kill','terminate','TerminateProcess','killpg') for n in calls)
    assert sum(isinstance(n.func,ast.Attribute) and n.func.attr=='Popen' for n in calls)==1
    assert not any(isinstance(n,ast.Constant) and isinstance(n.value,str) and
        ('checkm2_phase_separated_native_' in n.value or 'auth.json' in n.value) for n in ast.walk(tree))
    checks.append('single_dispatcher_spawn_source_no_science_or_auth_or_kill_route')
    run=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='run')
    text=ast.unparse(run)
    assert "b.exclusive(claim" in text and 'repairs += 1' in text and 'b.validate_handoff' in text
    assert "immutable_terminal = terminal['immutable_terminal_error']" in text
    assert 'terminal_error=immutable_terminal' in text and 'b.bind(R, immutable_terminal)' in text
    checks.append('persistent_per_cause_claim_and_validated_final_output_handoff_required')
    print(json.dumps({'status':'PURE_SUPERVISOR_SOURCE_FIXTURES_PASS','count':len(checks),
        'checks':checks,'supervisor_imported':False,'actual_process_or_probe_or_AI_run':False},indent=2))

if __name__=='__main__':main()
