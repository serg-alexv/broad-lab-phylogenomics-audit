"""Pure AST/guard fixtures only: no target imports, files, children or biology."""
from pathlib import Path,PurePosixPath as P
import tempfile,json,hashlib
from types import SimpleNamespace
import ast,math,re,unittest
D=Path(__file__).resolve().parent

def tree(name):return ast.parse((D/name).read_text())
def fn(name,target):return next(n for n in tree(name).body if isinstance(n,ast.FunctionDef)and n.name==target)
def literal(name,target):return ast.literal_eval(next(n.value for n in tree(name).body if isinstance(n,ast.Assign)and any(isinstance(x,ast.Name)and x.id==target for x in n.targets)))
COMMON='checkm2_campaign_index8_common_v002.py'
class Tests(unittest.TestCase):
 def test_unchanged_scientific_main_and_search_argv(self):
  for suffix in('annotation','diamond_producer','feature_validator','control_compare'):
   a=fn('checkm2_campaign_index8_'+suffix+'_v001.py','main');b=fn('checkm2_campaign_index8_'+suffix+'_v002.py','main')
   self.assertEqual(ast.dump(a),ast.dump(b),suffix)
  self.assertEqual(ast.dump(fn('checkm2_campaign_index8_diamond_producer_v001.py','build_argv')),ast.dump(fn('checkm2_campaign_index8_diamond_producer_v002.py','build_argv')))
 def configure(self,search=3600,validation=3600,rss=2147483648):
  limits={**literal(COMMON,'FIXED'),'per_input_annotation_seconds':180,'per_input_diamond_seconds':search,'per_input_saved_search_validation_seconds':validation,'per_input_resume_seconds':600,'per_input_validation_seconds':120,'per_input_scientific_seconds':8100,'cohort_scientific_seconds':16000,'cold_session_seconds':10000,'reference_control_seconds':0};limits['sum_group_RSS_bytes']=rss
  plan={'schema':'TREE2_CAMPAIGN_INDEX8_INPUT_PLAN_V002','cohort_id':'toy_phase_split','accessions':['GCF_000000001.1','GCF_000000002.1'],'limits':limits,'search_only_control':None}
  ns={'path':lambda p:p,'sha':lambda p:'sha','read':lambda p:plan,'math':math,'re':re,'R':P('/project'),'PLAN_SHA':None,'PLAN_PATH':None,'FIXED':literal(COMMON,'FIXED'),'PHASE_FIELDS':literal(COMMON,'PHASE_FIELDS'),'PHASE_MAX':literal(COMMON,'PHASE_MAX')}
  exec(compile(ast.fix_missing_locations(ast.Module(body=[fn(COMMON,'configure')],type_ignores=[])),'configure-bound-only','exec'),ns);ns['configure']('plan','sha');return ns
 def test_data_bound3600_and_cold_need_not_cover_theoretical_sum(self):
  ns=self.configure();self.assertEqual(ns['UNITS']['unit_diamond'],3600);self.assertEqual(ns['UNITS']['unit_saved_search_validation'],3600)
  self.assertEqual(ns['LIMITS']['cold_session_seconds'],10000);self.assertGreater(ns['LIMITS']['cohort_scientific_seconds'],10000)
  for value in(3600.001,0,float('nan'),float('inf')):
   with self.assertRaises(RuntimeError):self.configure(search=value)
  with self.assertRaises(RuntimeError):self.configure(validation=3600.1)
 def test_resources_cannot_change(self):
  with self.assertRaises(RuntimeError):self.configure(rss=3*1024**3)
 def test_binary0_checkpoint_precedes_postvalidator(self):
  events=[];c=SimpleNamespace(row=lambda p:{'path':str(p),'sha256':'sha'},bind=lambda r:r['path'],save=lambda p,v:events.append(('save',str(p),v)))
  ns={'Path':P,'c':c,'progress':lambda *a:None,'invoke':lambda name,cmd,*a:events.append(('unit',name,cmd)),'command_for':lambda prefix,module,request,output:[module]}
  exec(compile(ast.fix_missing_locations(ast.Module(body=[fn('checkm2_campaign_index8_inner_v002.py','search_phases')],type_ignores=[])),'order-only','exec'),ns)
  ns['search_phases']({}, {}, {'prefix':'/runtime'},P('/run'),P('/request'),P('/output/diamond_receipt.json'),{})
  self.assertEqual([x[1]for x in events],['unit_diamond','/run/binary_search_exit0.json','unit_saved_search_validation'])
  self.assertIn('--binary-execution',events[2][2]);self.assertIn('--binary-execution-sha256',events[2][2])
 def test_failed_binary_cannot_reach_postvalidator(self):
  events=[]
  def fail(*args):raise RuntimeError('actual nonzero search')
  c=SimpleNamespace(save=lambda *a:events.append(a))
  ns={'Path':P,'c':c,'progress':lambda *a:None,'invoke':fail,'command_for':lambda *a:[]}
  exec(compile(ast.fix_missing_locations(ast.Module(body=[fn('checkm2_campaign_index8_inner_v002.py','search_phases')],type_ignores=[])),'failure-order-only','exec'),ns)
  with self.assertRaises(RuntimeError):ns['search_phases']({}, {}, {'prefix':'/runtime'},P('/run'),P('/request'),P('/output/receipt'),{})
  self.assertEqual(events,[])
 def test_postvalidator_demands_actual_binary0_before_heavy_gate(self):
  body=fn('checkm2_campaign_index8_diamond_validate_v002.py','main').body;prefix=body[:next(i for i,n in enumerate(body)if isinstance(n,ast.Assign)and any(isinstance(x,ast.Name)and x.id=='request'for x in n.targets))]
  code=compile(ast.fix_missing_locations(ast.Module(body=prefix,type_ignores=[])),'binary-authority-only','exec')
  for exit_code,closed,accepted in((0,True,True),(-15,True,False),(None,True,False),(False,True,False),(0,None,False)):
   receipt={'exit_code':exit_code,'owned_group_empty':closed,'remaining_owned_processes':[]}
   c=SimpleNamespace(path=lambda p:p,sha=lambda p:'sha',read=lambda p:receipt,unit_closed=lambda r:type(r['exit_code'])is int and r['exit_code']==0 and r['owned_group_empty']is True)
   try:exec(code,{'a':SimpleNamespace(observed_search_exit_code=0,binary_execution='receipt',binary_execution_sha256='sha'),'c':c});outcome=True
   except RuntimeError:outcome=False
   self.assertEqual(outcome,accepted)
 def test_observer_only_finite_maximum_changed(self):
  old=(D/'checkm2_campaign_index8_observer_v001.py').read_text();new=(D/'checkm2_campaign_index8_observer_v002.py').read_text()
  self.assertEqual(new,old.replace('0<timeout<=900','0<timeout<=3600').replace('within900s required','within3600s required'))
 def test_all4_prior_failures_known_overshoot_and_separate_phase_provenance(self):
  common=(D/COMMON).read_text();inner=(D/'checkm2_campaign_index8_inner_v002.py').read_text();feature=(D/'checkm2_campaign_index8_feature_validator_v002.py').read_text()
  self.assertIn('len(failures)!=4',common);self.assertIn('actuals.append(n)',common);self.assertIn("'known_limit_exceeded':exceeded",common)
  self.assertIn("'diamond_validation_unit_execution'",inner);self.assertIn("'diamond_validation_unit_execution'",feature)
  self.assertNotIn('diamond_phase_v001.sh',inner);self.assertIn('actual_search_exit_observed_by_unit_owner',feature)
  self.assertNotIn('saved_binary_search_by_accession',common)

 def test_closed_binary_receipt_survives_failed_postvalidator_without_replay(self):
  parent=D.parent/'work/search_phase_split_toy_fixtures_v002';parent.mkdir(parents=True,exist_ok=True)
  with tempfile.TemporaryDirectory(dir=parent)as name:
   root=Path(name);self.assertTrue(root.resolve().is_relative_to(parent.resolve()));run=root/'run';row=run/'rows/GCF_002993975.1';row.mkdir(parents=True);calls=[]
   def save(path,value):path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value))
   def ref(path):path=Path(path);return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
   request=root/'request.json';save(request,{'fixture_only':True});output=root/'out/diamond_receipt.json';save(output.with_name('search_exec_prepared.json'),{'fixture_only':True,'producer_pid_before_exec':123})
   def invoke(unit,command,environment,folder):
    calls.append(unit);unit_dir=folder/unit;unit_dir.mkdir();save(unit_dir/'command.json',{'fixture_only':True});save(folder/(unit+'_budget.json'),{'fixture_only':True})
    save(unit_dir/'execution.json',{'fixture_only':True,'status':'UNIT_EXIT0_GROUP_CLOSED'if unit=='unit_diamond'else'UNIT_FAILED_OR_CLOSURE_UNPROVEN','exit_code':0 if unit=='unit_diamond' else 1,'owned_group_empty':True,'remaining_owned_processes':[],'elapsed_seconds':123.0 if unit=='unit_diamond' else 7.5})
    if unit!='unit_diamond':raise RuntimeError('injected file-only validator failure')
   c=SimpleNamespace(row=ref,bind=lambda r:r['path'],save=save)
   ns={'Path':Path,'c':c,'progress':lambda *a:None,'invoke':invoke,'command_for':lambda *a:[]}
   exec(compile(ast.fix_missing_locations(ast.Module(body=[fn('checkm2_campaign_index8_inner_v002.py','search_phases')],type_ignores=[])),'exact-provider-toy-I/O','exec'),ns)
   with self.assertRaises(RuntimeError):ns['search_phases']({}, {}, {'prefix':str(root/'runtime')},row,request,output,{})
   self.assertEqual(calls,['unit_diamond','unit_saved_search_validation'])
   checkpoint=json.loads((row/'binary_search_exit0.json').read_text());binary=json.loads((row/'unit_diamond/execution.json').read_text())
   self.assertEqual(binary['exit_code'],0);self.assertTrue(binary['owned_group_empty']);self.assertEqual(checkpoint['binary_execution'],ref(row/'unit_diamond/execution.json'))
   plan=root/'plan.json';save(plan,{'accessions':['GCF_002993975.1']})
   ns={'path':Path,'read':lambda p:json.loads(Path(p).read_text()),'PLAN_PATH':plan,'UNITS':{'unit_diamond':3600,'unit_saved_search_validation':3600},'LIMITS':{'cohort_scientific_seconds':10000},'prior_debits':lambda p:1500.5498878960061,'phase_cap':lambda *a:3600,'input_cap':lambda *a:10000,'math':math}
   exec(compile(ast.fix_missing_locations(ast.Module(body=[fn(COMMON,'budget')],type_ignores=[])),'known-debit-toy-I/O','exec'),ns)
   budget=ns['budget'](run);self.assertEqual(budget['cohort_scientific_seconds_debited'],130.5);self.assertAlmostEqual(budget['prior_plus_new_actual_scientific_seconds'],1631.0498878960061)

if __name__=='__main__':unittest.main()
