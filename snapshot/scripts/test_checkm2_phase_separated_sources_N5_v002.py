"""Focused N5 pure fixtures: no FNA/pickle/scientific import/process/runtime activity."""
from pathlib import Path,PurePosixPath
import ast,json,math,re,types,tempfile,unittest
R=Path(__file__).resolve().parents[1]
def tree(name):return ast.parse((R/'scripts'/name).read_text())
def extract(name,function,env):
 node=next(x for x in tree(name).body if isinstance(x,ast.FunctionDef)and x.name==function);exec(compile(ast.Module([node],type_ignores=[]),'<N5 pure fixture>','exec'),env);return env[function]
class Cases(unittest.TestCase):
 def test_unchanged_actual_N1_scientific_math(self):
  def block(name):
   f=next(x for x in tree(name).body if isinstance(x,ast.FunctionDef)and x.name=='main');body=f.body
   def assignment(n,x):return isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id==x for t in n.targets)
   a=next(i for i,n in enumerate(body)if assignment(n,'values'));z=next(i for i,n in enumerate(body)if assignment(n,'canonical'));return ast.dump(ast.Module(body[a:z+1],type_ignores=[]),include_attributes=False)
  self.assertEqual(block('checkm2_phase_separated_feature_validator_N1.py'),block('checkm2_phase_separated_feature_validator_N5.py'))
 def test_twenty_closed_phase_debits_unknown_and_caps(self):
  with tempfile.TemporaryDirectory(dir=R/'work',prefix='N5_pure_budget_')as temp:
   root=Path(temp);units={'unit_annotation':180,'unit_diamond':600,'unit_resume':600,'unit_feature_validation':30};budget=extract('checkm2_phase_separated_common_N5.py','budget',{'path':Path,'read':lambda p:json.loads(p.read_text()),'UNITS':units,'math':math})
   self.assertEqual(budget(root)['remaining_cohort_scientific_seconds'],7050)
   for acc in ('A','B','C','D','E'):
    for name,cap in units.items():
     folder=root/'rows'/acc/name;folder.mkdir(parents=True);(folder/'command.json').write_text('{}');(folder.parent/(name+'_budget.json')).write_text('{}');(folder/'execution.json').write_text(json.dumps({'elapsed_seconds':cap,'owned_group_empty':True,'remaining_owned_processes':[]}))
   actual=budget(root);self.assertEqual(actual['cohort_scientific_seconds_debited'],7050);self.assertEqual(set(actual['input_scientific_seconds'].values()),{1410})
   p=root/'rows/E/unit_feature_validation/execution.json';p.unlink()
   with self.assertRaises(RuntimeError):budget(root)
   for elapsed in (None,True,31):
    p.write_text(json.dumps({'elapsed_seconds':elapsed,'owned_group_empty':True,'remaining_owned_processes':[]}))
    with self.assertRaises(RuntimeError):budget(root)
 def test_shared_remaining_cannot_restart_each_invocation(self):
  with tempfile.TemporaryDirectory(dir=R/'work',prefix='N5_pure_invoke_')as temp:
   called=[];spent={'input_scientific_seconds':{'A':1400},'units_seconds_by_accession':{'A':{}},'remaining_cohort_scientific_seconds':5}
   fake=types.SimpleNamespace(UNITS={'unit_feature_validation':30},budget=lambda p:spent,save=lambda *a:None,read=lambda p:[],sha=lambda p:'SHA',ADMISSION='ready',unit_closed=lambda x:True)
   legacy=types.SimpleNamespace(stat=lambda x:{},mem_available=lambda:2**31);observer=types.SimpleNamespace(run_unit=lambda *a,**k:called.append(a),strict_group=lambda *a:[])
   fn=extract('checkm2_phase_separated_inner_N5.py','invoke',{'c':fake,'CURRENT_RUN':Path(temp),'stop':lambda:None,'HELPER_DEADLINE':100,'time':types.SimpleNamespace(monotonic=lambda:0),'observer':observer,'pilot':types.SimpleNamespace(legacy=legacy),'raw_progress':lambda *a:None,'note_optional':lambda *a:None})
   fn('unit_feature_validation',['no real executable'],{},Path(temp)/'A');self.assertEqual(called[0][4],5)
   spent['units_seconds_by_accession']['A']['unit_feature_validation']=1
   with self.assertRaises(RuntimeError):fn('unit_feature_validation',[],{},Path(temp)/'A')
 def test_exact_per_row_request_identity(self):
  f=extract('checkm2_phase_separated_inner_N5.py','request_base',{'c':types.SimpleNamespace(row=lambda p:{'path':p},ADMISSION='ready')});r=f({'_row':{'path':'plan'},'source_manifest':{'path':'sources'}},{'selected_inputs':{'path':'five'},'input':{'accession':'A'}},Path('/accepted'))
  self.assertEqual(r['accession'],'A');self.assertEqual(r['selected_inputs'],{'path':'five'});self.assertEqual(set(r),{'input_plan','source_manifest','protocol_admission','selected_inputs','accession','runtime_prefix'})
 def test_serial_phase_order_and_no_recovery_or_batch(self):
  source=(R/'scripts/checkm2_phase_separated_inner_N5.py').read_text();one=next(x for x in tree('checkm2_phase_separated_inner_N5.py').body if isinstance(x,ast.FunctionDef)and x.name=='one');names=[n.args[0].value for n in ast.walk(one)if isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id=='invoke'];self.assertEqual(names,['unit_annotation','unit_diamond','unit_resume','unit_feature_validation'])
  self.assertIn("for item in recipe['inputs']",source);self.assertNotIn('RECOVER_',source);self.assertNotIn('ThreadPool',source);self.assertIn('remaining_cohort_scientific_seconds',source);self.assertIn("request['cold_wall_deadline_unix']-640",source);self.assertIn('deadline-time.time()>7760.01',source)
 def test_cross_platform_invocation_normalization(self):
  def normalize(value):return PurePosixPath(str(value).replace('C:\\ROOT\\','/project/').replace('\\','/').replace('/mnt/c/ROOT/','/project/'))
  f=extract('checkm2_phase_separated_close_N5.py','normalized_invocations',{'c':types.SimpleNamespace(path=normalize)});names=['rows/'+a+'/'+u for a in('A','B','C','D','E')for u in('ann','dia','resume','feature')];saved=['/mnt/c/ROOT/'+n for n in names];expected={normalize('C:\\ROOT\\'+n)for n in names};self.assertEqual(len(f(saved,expected)),20)
  with self.assertRaises(RuntimeError):f(saved[:-1]+[saved[0]],expected)
 def test_history_unknown_schema_and_argv_veto(self):
  fn=extract('prepare_checkm2_phase_separated_history_N5.py','accessions',{'ACC':re.compile(r'GC[AF]_\d{9}\.\d+'),'FIELDS':{'accession'}});self.assertEqual(fn({'command':['tool','/raw/GCF_099999999.1/a.fna']}),{'GCF_099999999.1'})
  shape=extract('prepare_checkm2_phase_separated_history_N5.py','known_shape',{'Path':Path,'ACC':re.compile(r'GC[AF]_\d{9}\.\d+')})
  with self.assertRaises(RuntimeError):shape('analysis/checkm2_phase_separated_N1/requests/features.json',{'schema':'UNRECOGNIZED','command':['x']})
 def test_scope_limits_and_own_projection_preserved(self):
  recipe=json.loads((R/'metadata/checkm2_phase_separated_recipe_N5.json').read_text());authority=json.loads((R/'metadata/checkm2_N5_source_selection_implementation_authority_v001.json').read_text());self.assertEqual(recipe['limits'],authority['limits']);self.assertEqual(len(recipe['inputs']),5);self.assertEqual(len({x['species_taxid']for x in recipe['inputs']}),5)
  selected={x['accession']:x for x in json.loads((R/'metadata/checkm2_phase_separated_selected_inputs_N5_v002.json').read_text())['inputs']}
  for x in recipe['inputs']:
   self.assertEqual(x['source_metadata_checkm']['contamination'],selected[x['accession']]['candidate_record']['ncbi_checkm_contamination']);self.assertEqual(x['source_masks'],selected[x['accession']]['source_masks']);self.assertFalse(x['source_masks']['production_acceptance'])
  for p in(R/'scripts').glob('checkm2_phase_separated_*N5.py'):ast.parse(p.read_text())
 def test_bounded_project_import_closure(self):
  import hashlib
  for p in(R/'scripts').glob('*N5.py'):
   for node in ast.walk(ast.parse(p.read_text())):
    names=[x.name for x in node.names]if isinstance(node,ast.Import)else[node.module]if isinstance(node,ast.ImportFrom)else[]
    for name in names:
     if name and name.startswith('checkm2_'):self.assertTrue((R/'scripts'/(name+'.py')).is_file(),(p.name,name))
  for name in('diamond','feature_validator'):
   source=(R/('scripts/checkm2_phase_separated_'+name+'_N5.py')).read_text();self.assertIn('checkm2_phase_separated_artifacts_N1',source);self.assertNotIn('checkm2_phase_separated_artifacts_N5',source)
  self.assertEqual(hashlib.sha256((R/'scripts/checkm2_phase_separated_artifacts_N1.py').read_bytes()).hexdigest(),'20bf671558670a63cb94bf9ceed1f70d06a3a4072585d1446f7379f23ba89248')
if __name__=='__main__':unittest.main()
