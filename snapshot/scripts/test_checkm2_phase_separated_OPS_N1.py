"""Pure AST fixtures for N1 singleton/cold migration; imports no OPS/science module."""
from pathlib import Path
import ast,json,types
R=Path(__file__).resolve().parents[1]
def parse(name):return ast.parse((R/'scripts'/name).read_text(encoding='utf-8-sig'))
def function(tree,name):return next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name==name)
def main():
 native=parse('checkm2_phase_separated_native_N1.py');entry=parse('checkm2_phase_separated_entry_N1.py');checks=[]
 valid={'status':'N1_CORE_PENDING_NAMESPACE_NATIVE_CLOSURE','completed_qc_rows':1,'rows':[{'accession':'MOCK_ONLY'}]}
 invalid=[{**valid,'completed_qc_rows':True},{**valid,'completed_qc_rows':0},{**valid,'rows':{'one':'not a list'}},{**valid,'rows':[]},{**valid,'status':'S1R2_CORE_PENDING_NAMESPACE_NATIVE_CLOSURE'},{**valid,'completed_qc_rows':10,'preserved_count':1,'fresh_count':9,'rows':[{}]*10}]
 for label,tree in [('native',native),('entry',entry)]:
  namespace={};node=function(tree,'require_core_result')
  exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual singleton function AST>','exec'),namespace)
  assert namespace['require_core_result'](valid)==1
  for bad in invalid:
   try:namespace['require_core_result'](bad)
   except RuntimeError:pass
   else:raise AssertionError(label+' accepted invalid/inherited result')
  checks.append(label+'_singleton_valid_and_six_invalid_cases')
 request=next(call for call in ast.walk(native) if isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute) and isinstance(call.func.value,ast.Name) and call.func.value.id=='request' and call.func.attr=='update')
 fields={x.arg:ast.literal_eval(x.value) for x in request.keywords if isinstance(x.value,ast.Constant)}
 assert fields=={'cold_session_seconds':3000,'helper_max_seconds':1760,'prehelper_preflight_max_seconds':600,'post_unmount_hash_max_seconds':600,'fatal_cleanup_seconds':40}
 checks.append('native_3000_600_1760_600_40_request')
 main_node=function(entry,'main');names=('helper_seconds','helper_deadline','helper_deadline_unix')
 selected=[]
 for node in main_node.body:
  if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in node.targets):selected.append(node)
  if isinstance(node,ast.If) and isinstance(node.test,ast.Compare) and isinstance(node.test.left,ast.Name) and node.test.left.id=='helper_seconds':selected.append(node)
 for cold_end,expected in [(3100,1760),(900,160)]:
  namespace={'time':types.SimpleNamespace(monotonic=lambda:100,time=lambda:1000),'CONTEXT':{'cold_monotonic_deadline':cold_end}}
  exec(compile(ast.Module(body=selected,type_ignores=[]),'<actual helper deadline AST>','exec'),namespace)
  assert namespace['helper_seconds']==expected and namespace['helper_deadline']==100+expected and namespace['helper_deadline_unix']==1000+expected
 checks.append('helper_window_capped_by1760_and_remaining_cold_minus640')
 namespace={'time':types.SimpleNamespace(monotonic=lambda:100,time=lambda:1000),'CONTEXT':{'cold_monotonic_deadline':740}}
 try:exec(compile(ast.Module(body=selected,type_ignores=[]),'<zero helper window AST>','exec'),namespace)
 except TimeoutError:pass
 else:raise AssertionError('Zero helper window dispatched')
 checks.append('zero_remaining_helper_window_rejected')
 locked=function(native,'locked_main')
 first_progress=next(x for x in ast.walk(locked) if isinstance(x,ast.Call) and isinstance(x.func,ast.Name) and x.func.id=='progress' and len(x.args)>=3 and isinstance(x.args[1],ast.Constant) and str(x.args[1].value).startswith('Root-admitted N1'))
 assert ast.literal_eval(first_progress.args[2])==0
 checks.append('fresh_initial_counter_zero_no_inherited_row')
 original=parse('checkm2_single_faa_native_S1R2.py')
 for name in ('identity','common_locks'):
  assert ast.dump(function(native,name),include_attributes=False)==ast.dump(function(original,name),include_attributes=False)
 checks.append('accepted_native_identity_and_partial_lease_cleanup_AST_unchanged')
 shell=(R/'scripts/checkm2_phase_separated_N1.sh').read_bytes();assert b'\r' not in shell and shell.startswith(b'#!/bin/bash\n')
 checks.append('LF_shell_zero_CR_no_execution')
 print(json.dumps({'status':'PURE_AST_FIXTURES_PASS','checks':checks,'count':len(checks),'OPS_modules_imported':False,'runtime_transport_process_or_shell_execution':False},indent=2))
if __name__=='__main__':main()
