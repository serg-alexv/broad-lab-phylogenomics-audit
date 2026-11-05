"""Only stdlib tiny-file and AST fixtures; no subprocess, Linux probe or scientific import."""
from pathlib import Path
import ast,errno,hashlib,importlib.util,json,math,os,tempfile
R=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('small_admission',R/'scripts/checkm2_saved_admission_read_v001.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def check():
 tests=[]
 with tempfile.TemporaryDirectory(dir=R/'work',prefix='saved_admission_pure_')as root:
  p=Path(root)/'admission.json';payload=b'{"strict":true}\n';p.write_bytes(payload);expected=hashlib.sha256(payload).hexdigest()
  assert m.admission_sha(p,expected)==expected;tests.append('exact current admission SHA')
  calls=[];errors=[]
  def transient(fd,size):
   calls.append(size)
   if len(calls)==1:raise OSError(errno.ENOMEM,'injected read failure')
   return os.read(fd,size)
  assert m.admission_sha(p,expected,read=transient,sleep=lambda _:None,error_sink=errors.append)==expected
  assert errors[0]['errno']==12 and all(x==4096 for x in calls);tests.append('ENOMEM-only bounded restart with all-byte rehash')
  count=[]
  def permanent(fd,size):count.append(1);raise OSError(errno.ENOMEM,'injected permanent error')
  try:m.admission_sha(p,expected,read=permanent,sleep=lambda _:None)
  except OSError as e:assert e.errno==12 and len(count)==3
  else:raise AssertionError('Permanent ENOMEM accepted')
  tests.append('third ENOMEM remains strict failure')
  count=[]
  def denied(fd,size):count.append(1);raise PermissionError(errno.EACCES,'injected')
  try:m.admission_sha(p,expected,read=denied,sleep=lambda _:None)
  except PermissionError:assert len(count)==1
  else:raise AssertionError('Other error retried or accepted')
  tests.append('non-ENOMEM is not swallowed or retried')
  try:m.admission_sha(p,'0'*64)
  except InterruptedError:pass
  else:raise AssertionError('Changed admission accepted')
  tests.append('SHA mismatch remains fatal')
 def function(text,name):return next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)and n.name==name)
 old=(R/'scripts/checkm2_campaign_index8_feature_validator_v004.py').read_text();new=(R/'scripts/checkm2_saved_stock_features_v001.py').read_text()
 assert ast.dump(function(old,'main'))==ast.dump(function(new,'main'));tests.append('all accepted numerical feature main AST unchanged')
 old=(R/'scripts/checkm2_campaign_index8_observer_v002.py').read_text();new=(R/'scripts/checkm2_parallel_saved_observer_v001.py').read_text()
 for name in('strict_group','owned_census'):
  assert ast.dump(function(old,name))==ast.dump(function(new,name))
 assert 'LIMIT=1543503872;HEADROOM=1879048192'in new and "hooks['controller_rows']()"in new
 tests.append('original owned census plus stricter complete Linux RSS/headroom')
 tree=ast.parse((R/'scripts/checkm2_saved_stock_recovery_v001.py').read_text())
 calls=[n for n in ast.walk(tree)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='run_unit']
 assert [n.args[0].value for n in calls]==['unit_resume','unit_feature_validation'];tests.append('only stock and file-feature units can dispatch')
 selected=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in('unit_closed','charged_unit')];ns={'math':math};exec(compile(ast.Module(body=selected,type_ignores=[]),'pure_debit','exec'),ns)
 good={'status':'UNIT_EXIT0_GROUP_CLOSED','exit_code':0,'owned_group_empty':True,'remaining_owned_processes':[],'elapsed_seconds':548.0189570170041}
 assert ns['charged_unit'](good,548.0189570170041)==548.0189570170041
 for bad in({**good,'elapsed_seconds':None},{**good,'elapsed_seconds':548.018958},{**good,'exit_code':False}):
  try:ns['charged_unit'](bad,548.0189570170041)
  except RuntimeError:pass
  else:raise AssertionError('Missing debit, exceeded cap or boolean exit accepted')
 tests.append('known prior cap and typed actual closed debit are strict')
 for name in('checkm2_saved_stock_recovery_v001.py','checkm2_saved_stock_features_v001.py','checkm2_parallel_saved_observer_v001.py'):
  ast.parse((R/'scripts'/name).read_text())
 return {'status':'PURE_SOURCE_FIXTURES_PASS','groups':len(tests),'tests':tests,'no_process_or_scientific_import_or_real_input':True}
if __name__=='__main__':print(json.dumps(check(),indent=2))
