"""Pure source/ABI and tiny metadata-closure fixtures only; no OS/runtime call."""
from pathlib import Path
import ast,json,types,tempfile,math,time
D=Path(__file__).resolve().parent;passed=[]
for p in D.glob('checkm2_parallel_saved*.py'):ast.parse(p.read_text())
passed.append('all_new_OPS_AST_parse')
def assignment(file,name):
 tree=ast.parse((D/file).read_text());return next(x.value for x in tree.body if isinstance(x,ast.Assign)and any(isinstance(t,ast.Name)and t.id==name for t in x.targets))
a=eval(compile(ast.Expression(assignment('checkm2_saved_stock_recovery_v001.py','LIMITS')),'limits','eval'),{'STOCK_SECONDS':548.0189570170041});b=ast.literal_eval(assignment('checkm2_parallel_saved_common_v001.py','LIMITS'));assert a==b and a['fresh_launch_available_minimum_bytes']==3100000000 and a['total_owned_rss_bytes']==a['native_reserved_bytes']+a['linux_total_rss_bytes'];passed.append('Linux_provider_Windows_common_limits_match_no_fcntl_import_needed')
ns={};tree=ast.parse((D/'checkm2_parallel_saved_common_v001.py').read_text());fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef)and x.name=='group_receipts_closed')
with tempfile.TemporaryDirectory(dir=D.parent/'work',prefix='parallel_closure_toy_')as td:
 run=Path(td);data={};folders=[]
 for unit in('unit_resume','unit_feature_validation'):
  folder=run/unit;folder.mkdir();(folder/'command.json').write_text('{}');folders.append(folder);data[folder/'execution.json']={'exit_code':0,'owned_group_empty':True,'remaining_owned_processes':[]}
 data[run/'invocations.json']=[str(x)for x in folders];ns={'path':Path,'read':lambda p:data[p]};exec(compile(ast.Module(body=[fn],type_ignores=[]),'group','exec'),ns);assert ns['group_receipts_closed'](run)
 data[folders[0]/'execution.json']['exit_code']=-15;assert ns['group_receipts_closed'](run) # closure is separate from success
 data[folders[0]/'execution.json']['owned_group_empty']=False;assert ns['group_receipts_closed'](run)is False
 data[folders[0]/'execution.json']['owned_group_empty']=True;data[run/'invocations.json']=[]
 try:ns['group_receipts_closed'](run)
 except RuntimeError:pass
 else:raise AssertionError('Missing/false index accepted')
passed.append('exact_actual_started_two_unit_index_and_failure_closure_distinct_from_success')
for file in('checkm2_parallel_saved_native_v001.py','checkm2_parallel_saved_entry_v001.py'):
 t=ast.parse((D/file).read_text());f=next(x for x in t.body if isinstance(x,ast.FunctionDef)and x.name=='require_core_result');env={};exec(compile(ast.Module(body=[f],type_ignores=[]),file,'exec'),env)
 good={'status':'SAVED_STOCK_ROW_PENDING_NATIVE_CLOSURE','completed_qc_rows':1,'rows':[{}]};assert env['require_core_result'](good)==1
 try:env['require_core_result']({**good,'rows':[{},{}]})
 except RuntimeError:pass
 else:raise AssertionError('Extra/fake result accepted')
passed.append('provider_result_status_and_exact_one_row_native_entry_ABI')
native=(D/'checkm2_parallel_saved_native_v001.py').read_text();assert 'Root_companion_ack.json'in native and "marker_dispatcher_handoff_replaced')is False"in native and 'early_attach_ack'not in native and "'done':16,'total':919"in native and "'local_step_done':row['done']"in native;passed.append('own_Root_retained_ACK_no_marker_dispatcher_replacement_campaign16_919_preserved')
bridge=(D/'checkm2_parallel_saved_bridge_v001.py').read_text();assert 'safe_call(raw_progress'in bridge and 'bridge_identity=pilot.legacy.stat'in bridge and 'progress=progress)'in bridge and 'subprocess'not in bridge;passed.append('same_interpreter_callable_optional_publication_timestamp_and_metrics_no_new_controller')
# Compile EXACT generated Linux observer string, without executing it or importing target.
t=ast.parse((D/'checkm2_parallel_saved_preflight_v001.py').read_text());nodes=[]
for n in ast.walk(t):
 if isinstance(n,ast.Assign)and any(isinstance(x,ast.Name)and x.id=='source'for x in n.targets):nodes.append(n)
 elif isinstance(n,ast.AugAssign)and isinstance(n.target,ast.Name)and n.target.id=='source':nodes.append(n)
first=min(n.lineno for n in nodes if any(isinstance(x,ast.Constant)and isinstance(x.value,str)and x.value.startswith('from pathlib import Path\nimport sys')for x in ast.walk(n)));nodes=[n for n in nodes if n.lineno>=first];nodes.sort(key=lambda n:n.lineno);env={'linux_root':'/toy/TREE2','linux_plan':'/toy/plan','a':types.SimpleNamespace(input_plan_sha256='a'*64),'time':time,'started':time.monotonic()};exec(compile(ast.Module(body=nodes,type_ignores=[]),'source_builder','exec'),env);compile(env['source'],'generated_readonly_Linux_observer','exec');assert 'marker_and_exclusivity_gate'in env['source']and 'linux_guard(fresh=True)'in env['source']and 'signal.alarm'in env['source'];passed.append('actual_generated_Linux_preflight_code_compiles_no_execution_exact_marker_freshgate')
raw=(D/'checkm2_parallel_saved_v001.sh').read_bytes();assert b'\r'not in raw and b'checkm2_parallel_saved_entry_v001.py'in raw and b'NUM_THREADS=2'not in raw and b'TF_NUM_INTRAOP_THREADS=2'not in raw;passed.append('LF_shell_correct_entry_and_threads1')
print(json.dumps({'status':'PURE_OPS_FIXTURES_PASS','groups':len(passed),'tests':passed,'actual_OS_probe_runtime_science_or_target_import':False},indent=2))
