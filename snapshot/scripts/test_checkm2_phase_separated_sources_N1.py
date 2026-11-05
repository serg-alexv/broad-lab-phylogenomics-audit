"""Pure source/request/budget fixtures; no real inputs, science imports, children or runtime."""
from pathlib import Path
import ast,json,math,sys,tempfile,types,unittest
R=Path(__file__).resolve().parents[1]
def tree(name):return ast.parse((R/'scripts'/name).read_text())
def extract(name,function,env):
 node=next(x for x in tree(name).body if isinstance(x,ast.FunctionDef) and x.name==function)
 exec(compile(ast.Module([node],type_ignores=[]),'<pure N1 fixture>','exec'),env);return env[function]
class Tests(unittest.TestCase):
 def test_identical_scientific_body(self):
  def block(name):
   main=next(x for x in tree(name).body if isinstance(x,ast.FunctionDef) and x.name=='main');nodes=main.body
   def target(node,name):return isinstance(node,ast.Assign) and any(isinstance(x,ast.Name) and x.id==name for x in node.targets)
   first=next(i for i,x in enumerate(nodes) if target(x,'values'));last=next(i for i,x in enumerate(nodes) if target(x,'canonical'))
   return ast.dump(ast.Module(nodes[first:last+1],type_ignores=[]),include_attributes=False)
  self.assertEqual(block('checkm2_single_faa_feature_validator_S1R2.py'),block('checkm2_phase_separated_feature_validator_N1.py'))
 def test_budget_closed_units_no_unknown_reset(self):
  with tempfile.TemporaryDirectory(dir=R/'work',prefix='N1_pure_budget_') as folder:
   root=Path(folder);units={'unit_annotation':180,'unit_diamond':600,'unit_resume':600,'unit_feature_validation':30}
   budget=extract('checkm2_phase_separated_common_N1.py','budget',{'path':Path,'read':lambda p:json.loads(p.read_text()),'math':math,'UNITS':units})
   self.assertEqual(budget(root)['remaining_scientific_seconds'],1410)
   for name,cap in units.items():
    (root/name).mkdir();(root/name/'command.json').write_text('{}');(root/(name+'_budget.json')).write_text('{}');(root/name/'execution.json').write_text(json.dumps({'elapsed_seconds':cap,'owned_group_empty':True,'remaining_owned_processes':[]}))
   self.assertEqual(budget(root)['remaining_scientific_seconds'],0)
   last=root/'unit_feature_validation/execution.json';last.unlink()
   with self.assertRaises(RuntimeError):budget(root)
   last.write_text(json.dumps({'elapsed_seconds':True,'owned_group_empty':True,'remaining_owned_processes':[]}))
   with self.assertRaises(RuntimeError):budget(root)
   last.write_text(json.dumps({'elapsed_seconds':31,'owned_group_empty':True,'remaining_owned_processes':[]}))
   with self.assertRaises(RuntimeError):budget(root)
 def test_runtime_abi_rejects_interchangeable_request(self):
  ready={'checkm2_version':'1.1.0','diamond_version':'2.1.11','runtime_image':{'sha256':'IMAGE'},'prefix_linux':'/accepted','database_path':'/accepted-db'}
  recipe={'accepted_runtime_ready_receipt':{'path':'ready'},'runtime_binding':{'canonical_prefix':'/accepted','effective_manifest':{'path':'effective'},'image_sha256':'IMAGE','required_environment':{'CONTROL':'yes'},'database':{'path':'/accepted-db','sha256':'DB','bytes':1},'tools':{'diamond':{'path':'/accepted/bin/diamond','sha256':'BINARY','bytes':2}}}}
  calls=[];fake=types.ModuleType('checkm2_pilot');fake.readonly_runtime_gate=lambda r:calls.append(r);old=sys.modules.get('checkm2_pilot');sys.modules['checkm2_pilot']=fake
  try:
   gate=extract('checkm2_phase_separated_common_N1.py','runtime_gate',{'path':Path,'read':lambda p:ready,'bind':lambda r:r['path'],'os':types.SimpleNamespace(environ={'CONTROL':'yes'})})
   request={'runtime_prefix':'/accepted','database':recipe['runtime_binding']['database'],'diamond_binary':recipe['runtime_binding']['tools']['diamond']}
   self.assertEqual(gate(request,recipe),Path('/accepted'));self.assertEqual(len(calls),1)
   for field in ('database','diamond_binary'):
    changed={**request,field:{**request[field],'sha256':'UNACCEPTED'}}
    with self.assertRaises(RuntimeError):gate(changed,recipe)
   with self.assertRaises(RuntimeError):gate({**request,'runtime_prefix':'/other'},recipe)
  finally:
   if old is None:sys.modules.pop('checkm2_pilot',None)
   else:sys.modules['checkm2_pilot']=old
 def test_producer_request_and_phase_interface(self):
  base=extract('checkm2_phase_separated_inner_N1.py','request_base',{'c':types.SimpleNamespace(row=lambda p:{'path':str(p)},ADMISSION=Path('admission'))})
  actual=base({'_row':{'path':'plan'},'source_manifest':{'path':'sources'}},{'selected_input':{'path':'selected'}},Path('/accepted'))
  self.assertEqual(set(actual),{'input_plan','source_manifest','protocol_admission','selected_input','runtime_prefix'})
  source=(R/'scripts/checkm2_phase_separated_inner_N1.py').read_text();self.assertIn("'--resume'",source);self.assertNotIn('RECOVER_CLOSED',source)
  for name in ('unit_annotation','unit_diamond','unit_resume','unit_feature_validation'):self.assertEqual(source.count("invoke('"+name+"'"),1)
 def test_feature_adapter_request_and_fresh_status(self):
  nodes=tree('checkm2_phase_separated_feature_validator_N1.py');names={n.id for n in ast.walk(nodes) if isinstance(n,ast.Name)}
  self.assertNotIn('CONTRACT_SHA',names);source=(R/'scripts/checkm2_phase_separated_feature_validator_N1.py').read_text()
  self.assertNotIn('annotation_reuse_authority',source);self.assertIn('N1_FEATURES_PASS_PENDING_NATIVE_CLOSURE',source)
  self.assertIn("request['input_plan']['sha256']",source);self.assertIn("'source_pending_reasons':item['source_pending_reasons']",source)
 def test_syntax_and_finite_boundaries(self):
  for path in (R/'scripts').glob('checkm2_phase_separated_*N1.py'):ast.parse(path.read_text())
  source=(R/'scripts/checkm2_phase_separated_inner_N1.py').read_text()
  self.assertIn("request['cold_wall_deadline_unix']-640",source);self.assertIn('deadline-time.time()>1760.01',source)
  self.assertIn("except BaseException:\n  lock.close();raise",source);self.assertIn('fcntl.LOCK_UN',source)
if __name__=='__main__':unittest.main()
