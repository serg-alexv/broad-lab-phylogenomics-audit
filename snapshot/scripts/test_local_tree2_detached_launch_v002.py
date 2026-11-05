"""Pure detached-launch source fixtures; no controller/fixture/Win32 process is started."""
from pathlib import Path
import ast
import hashlib
import json

R=Path(__file__).resolve().parents[1]

def main():
    source=R/'scripts/local_tree2_detached_launch_v002.py'
    tree=ast.parse(source.read_text(encoding='utf-8-sig'))
    roles=('LOCAL_TREE2_RUNTIME_CONTROLLER','SCIENTIFIC_NATIVE_WORKER','BENIGN_PERSISTENCE_FIXTURE')
    ns={'Path':Path,'hashlib':hashlib,'json':json,'ROLES':roles}
    functions=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in ('argv_hash','validate_contract','relinquish_child_handle','isolation_verdict')]
    exec(compile(ast.Module(body=functions,type_ignores=[]),'<actual detached source pure AST>','exec'),ns)
    argv=['-B',str(R/'scripts/mock_only.py'),'--config',str(R/'work/path with spaces/config.json'),
      'literal $() ` " quotes', 'trailing\\', '\u03a9 sequence label']
    good={'schema':'TREE2_DETACHED_NATIVE_LAUNCH_CONTRACT_V001','project_root':str(R),
      'role':roles[0],'arguments':argv,'argument_vector_sha256':ns['argv_hash'](argv),
      'no_automatic_duplicate_or_retry':True}
    assert ns['validate_contract'](good,R)==roles[0]
    assert ns['argv_hash'](argv)==hashlib.sha256(json.dumps(argv,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    checks=['exact_full_argv_hash_preserves_spaces_quotes_backslashes_unicode_without_shell']
    bads=[{**good,'arguments':argv+['extra']},{**good,'role':'ANY_PROCESS'},
      {**good,'project_root':str(R.parent)},{**good,'no_automatic_duplicate_or_retry':False},
      {**good,'arguments':'not a list'},{**good,'role':'SCIENTIFIC_NATIVE_WORKER'}]
    for item in bads:
        try:ns['validate_contract'](item,R)
        except RuntimeError:pass
        else:raise AssertionError('Invalid source/role/argv/retry contract accepted')
    assert ns['validate_contract']({**good,'role':'SCIENTIFIC_NATIVE_WORKER','scientific_admission':{}},R)=='SCIENTIFIC_NATIVE_WORKER'
    checks.append('six_invalid_contracts_rejected_and_scientific_admission_required')
    launch=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='launch')
    calls=[x for x in ast.walk(launch) if isinstance(x,ast.Call)]
    popen=next(x for x in calls if isinstance(x.func,ast.Attribute) and x.func.attr=='Popen')
    keywords={x.arg:ast.unparse(x.value) for x in popen.keywords}
    assert keywords['creationflags']=='BREAKAWAY | NEW_PROCESS_GROUP | NO_WINDOW'
    assert keywords['cwd']=='R' and keywords['stdin']=='subprocess.DEVNULL' and 'shell' not in keywords
    assert keywords['stdout']=='out' and keywords['stderr']=='err'
    checks.append('explicit_breakaway_new_group_hidden_no_shell_no_parent_stdio_pipes')
    claim=next(x for x in calls if isinstance(x.func,ast.Attribute) and x.func.attr=='exclusive'
      and len(x.args)>0 and isinstance(x.args[0],ast.Name) and x.args[0].id=='claim')
    assert claim.lineno<popen.lineno
    text=ast.unparse(launch)
    assert "contract.get('status') != 'ROOT_ADMITTED_ONE_DETACHED_NATIVE_LAUNCH'" in text
    assert 'actual_child_exit' in text and 'UNKNOWN_UNTIL_SEPARATE_RETAINED_OS_OBSERVER' in text
    assert 'relinquish_child_handle(child)' in text
    checks.append('exclusive_once_claim_before_spawn_required_Root_grant_and_unknown_exit')
    class Handle:
        def __init__(self):self.count=0
        def Close(self):self.count+=1
    class Child:pass
    child=Child();handle=Handle();child._handle=handle;child._child_created=True;child.returncode=None
    ns['relinquish_child_handle'](child);ns['relinquish_child_handle'](child)
    assert child._handle is None and child._child_created is False and child.returncode is None and handle.count==1
    checks.append('detached_handle_closed_once_destructor_disabled_exit_stays_unknown_mock')
    assert not any(isinstance(x.func,ast.Attribute) and x.func.attr in ('kill','terminate','TerminateProcess','SetInformationJobObject') for x in calls)
    assert 'auth.json' not in source.read_text()
    fixture=ast.parse((R/'scripts/local_tree2_persistence_fixture_v002.py').read_text(encoding='utf-8-sig'))
    fixture_text=ast.unparse(fixture)
    assert '30 <= args.seconds <= 180' in fixture_text
    assert not any(isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr in ('Popen','kill','TerminateProcess') for x in ast.walk(fixture))
    checks.append('benign_fixture_bounded_self_expiry_no_spawn_kill_auth_or_science')
    isolated={'in_any_job':True,'process_list_complete':True,'process_ids':[101,102]}
    verdict=ns['isolation_verdict'](isolated,202,True,True)
    assert verdict['verified'] is True and verdict['all_ancestor_jobs_enumerated'] is False
    for job,alive in [({**isolated,'process_ids':[101,202]},True),({**isolated,'process_list_complete':False},True),({},True),(isolated,False)]:
        assert ns['isolation_verdict'](job,202,True,alive)['verified'] is False
    assert ns['isolation_verdict']({},202,False,True)['verified'] is True
    snapshot=ast.unparse(next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='current_job_snapshot'))
    assert 'values.assigned != values.listed' in snapshot and 'os.getpid() not in pids' in snapshot
    checks.append('nested_job_escape_uses_complete_caller_and_descendant_census_no_ancestor_claim')
    print(json.dumps({'status':'SEVEN_PURE_DETACHED_SOURCE_FIXTURE_GROUPS_PASS','count':len(checks),
      'checks':checks,'target_imports_process_or_AI_or_science_started':False},indent=2))

if __name__=='__main__':main()
