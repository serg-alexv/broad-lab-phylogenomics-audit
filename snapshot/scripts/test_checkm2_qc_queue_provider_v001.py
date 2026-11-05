"""Pure source/JSON/coordinator fixtures. No runtime, models or biological data."""
from pathlib import Path
import ast,copy,json,math,sys,tempfile,types,unittest

R=Path(__file__).resolve().parents[1]
NEW=['common','inner','observer','shared_producer','shared_validate','shared_controls','feature_validator','serial_provider','batch_project']

def source(short):return (R/'scripts'/('checkm2_qc_queue_'+short+'_v001.py')).read_text()
def function(short,name,namespace):
    tree=ast.parse(source(short));node=next(x for x in tree.body if isinstance(x,ast.FunctionDef)and x.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),'<extracted real provider>','exec'),namespace)
    return namespace[name]

class ProviderTests(unittest.TestCase):
    def test_local_import_closure_and_no_duplicate_functions(self):
        visited=set()
        def walk(path):
            if path in visited:return
            visited.add(path);tree=ast.parse(path.read_text());names=[n.name for n in tree.body if isinstance(n,ast.FunctionDef)]
            if path.name.startswith('checkm2_qc_queue_'):self.assertEqual(len(names),len(set(names)))
            for node in ast.walk(tree):
                modules=[x.name for x in node.names]if isinstance(node,ast.Import)else[node.module]if isinstance(node,ast.ImportFrom)and node.module else[]
                for name in modules:
                    if name.startswith(('checkm2_','prepare_checkm2_','local_tree2_')):
                        target=R/'scripts'/(name.split('.')[0]+'.py');self.assertTrue(target.is_file(),str(target));walk(target)
        for short in NEW:walk(R/'scripts'/('checkm2_qc_queue_'+short+'_v001.py'))
        self.assertNotIn('from checkm2_campaign_index8_shared_producer_v003',source('shared_validate'))

    def test_real_base_request_has_required_runtime_prefix(self):
        ns={'c':types.SimpleNamespace(row=lambda p:{'path':str(p)},ADMISSION='root-phase')}
        result=function('inner','base_request',ns)({'_row':1,'source_manifest':2,'selected_inputs':3,'method_amendment':4},{},Path('accepted-python'))
        self.assertEqual(result['runtime_prefix'],'accepted-python');self.assertEqual(result['resource_method_amendment'],4)

    def test_uniform_gate_returns_descriptor_not_original(self):
        fake=types.ModuleType('checkm2_uniform_annotation_cache_QC_v001');calls=[]
        fake.uniform_annotation_gate=lambda *a,**kw:calls.append(a)or{'original_uniform_receipt':True}
        previous=sys.modules.get(fake.__name__);sys.modules[fake.__name__]=fake
        descriptor={'selected_faa':{'sha256':'own'},'new_annotation_unit_created':False}
        try:
            ns={'read':lambda _:descriptor,'path':Path,'bind':lambda x:x}
            result=function('common','annotation_reuse_gate',ns)({'run_directory':'toy'},'GCF_000000001.1',{'source_masks':{}})
            self.assertIs(result,descriptor);self.assertEqual(len(calls),1)
        finally:
            if previous is None:sys.modules.pop(fake.__name__)
            else:sys.modules[fake.__name__]=previous

    def test_source_masks_and_holds_exact(self):
        masks={'production_acceptance':False,'unresolved':None};item={'accession':'own','source_masks':masks,'source_holds_preserved':['type_unknown'],'legacy_P20_source_context':{'extra':'preserved'}}
        f=function('common','canonical_source_masks',{});self.assertEqual(f(item),masks)
        projection=function('common','own_source_projection',{})(item,{'raw_report':{'Name':'own'}})
        self.assertEqual(projection['original_source_context'],item);self.assertTrue(projection['source_hold_active'])
        with self.assertRaises(RuntimeError):function('common','own_source_projection',{})(item,{'raw_report':{'Name':'other'}})

    def test_scientific_numeric_statements_unchanged(self):
        old=ast.parse((R/'scripts/checkm2_campaign_index8_feature_validator_v003.py').read_text());new=ast.parse(source('feature_validator'))
        def selected(tree):
            fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='main');wanted=[]
            targets={'values','joined','expected_aa','counts','expected','names','differences','canonical'}
            for n in fn.body:
                if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id in targets for t in n.targets):wanted.append(ast.dump(n,include_attributes=False))
                if isinstance(n,ast.If)and (isinstance(n.test,ast.Compare)and any(isinstance(x,ast.Name)and x.id=='expected_aa'for x in ast.walk(n.test))or isinstance(n.test,ast.Name)and n.test.id=='differences'):wanted.append(ast.dump(n,include_attributes=False))
            return wanted
        self.assertEqual(selected(old),selected(new));self.assertGreaterEqual(len(selected(new)),10)
        producer=ast.parse(source('shared_producer'));baseline=ast.parse((R/'scripts/checkm2_campaign_index8_shared_producer_v003.py').read_text())
        def body(t):return ast.dump(next(n for n in t.body if isinstance(n,ast.FunctionDef)and n.name=='build_argv'),include_attributes=False)
        self.assertEqual(body(producer),body(baseline))

    def test_global_batch_debit_once_and_no_fake_row_search(self):
        with tempfile.TemporaryDirectory(dir=R/'work',prefix='qc_provider_pure_')as td:
            run=Path(td);plan={'accessions':['a','b']};caps={'unit_feature_validation':120};shared_caps={'unit_shared_diamond':10800,'unit_stock_batch':600,'unit_batch_projection':1200}
            def put(folder,name,elapsed):
                p=run/folder/name;p.mkdir(parents=True);(p/'command.json').write_text('{}');(p/'execution.json').write_text(json.dumps({'elapsed_seconds':elapsed,'owned_group_empty':True,'remaining_owned_processes':[]}));(p.parent/(name+'_budget.json')).write_text('{}')
            put('shared','unit_shared_diamond',10);put('shared','unit_stock_batch',20);put('shared','unit_batch_projection',2);put('rows/a','unit_feature_validation',1);put('rows/b','unit_feature_validation',3)
            ns={'path':Path,'read':lambda p:plan if p=='PLAN'else json.loads(Path(p).read_text()),'PLAN_PATH':'PLAN','math':math,'SHARED_UNITS':shared_caps,'ROW_UNITS':caps,'LIMITS':{'per_input_scientific_seconds':900,'cohort_scientific_seconds':31620},'prior_debits':lambda _:1500.5}
            result=function('common','budget',ns)(run);self.assertEqual(result['cohort_scientific_seconds_debited'],36);self.assertEqual(result['shared_scientific_seconds'],32);self.assertEqual(result['prior_plus_new_actual_scientific_seconds'],1536.5)
            put('rows/a','unit_shared_diamond',1)
            with self.assertRaises(RuntimeError):ns['budget'](run)

    def test_control_first_then_one_own_then_batch(self):
        with tempfile.TemporaryDirectory(dir=R/'work',prefix='qc_coordinator_pure_')as td:
            events=[];run=Path(td);(run/'rows').mkdir();items=[{'accession':x}for x in('a','b','c')]
            fake=types.SimpleNamespace(save=lambda *a:None,row=lambda p:{'path':str(p)},shared_qualification_gate=lambda *a:events.append('qualified'),budget=lambda _:{})
            ns={'c':fake,'stop':lambda:None,'annotate_one':lambda p,r,t,f,i:{'accession':i['accession']},'shared_search':lambda *a:events.append('search')or{},'finish_controls':lambda *a:events.append('controls')or{},'predict_one':lambda *a:events.append('first-own')or{'commit':{}},'predict_batch':lambda *a:events.append(('batch',[x['accession']for x in a[4]]))or[{'accession':x['accession']}for x in a[4]],'progress':lambda *a,**kw:None}
            result=function('inner','execute_phases',ns)({'cohort_index':0,'campaign_authority':{},'controls':[]},{'inputs':items},{},run,{'results':[],'annotations':[]})
            self.assertLess(events.index('controls'),events.index('first-own'));self.assertEqual(events.count('first-own'),1);self.assertIn(('batch',['b','c']),events);self.assertEqual(len(result['results']),3)

    def test_batch_projection_hash_and_exit_before_unpickle(self):
        text=source('batch_project');self.assertLess(text.index('c.request_gate(request)'),text.index('pd.read_pickle(raw)'));self.assertLess(text.index("c.unit_closed(c.read(c.bind(commit['stock_batch_execution'])))"),text.index('pd.read_pickle(raw)'))
        text=source('inner');self.assertIn("'global_stock_batch_execution':batch['stock_batch_execution']",text)
        batch=text[text.index('def predict_batch('):];self.assertNotIn("invoke('unit_resume'",batch);self.assertIn("invoke('unit_stock_batch'",batch)

if __name__=='__main__':unittest.main()
