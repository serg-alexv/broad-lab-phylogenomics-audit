from pathlib import Path
import importlib.util,json,datetime,tempfile,os,types
R=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pilot',R/'scripts/checkm2_pilot.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
base=R/'work/checkm2_pilot_controller_selftest';base.mkdir(exist_ok=True);tests=[]
def assert_reject(name,call,expected_message=None):
 try:call()
 except Exception as e:
  if expected_message:assert expected_message in str(e)
  tests.append({'check':name,'status':'PASS_REJECTED','exception':type(e).__name__})
 else:raise AssertionError(name)
r=base/'quality.tsv';r.write_text('Name\tCompleteness\tContamination\nfixture\t97.2\t0.5\n');row,c,t=p.parse_quality_report(r,'fixture');assert(c,t)==(97.2,.5);tests.append({'check':'valid numeric one-row schema','status':'PASS'})
for name,body in [('missing-contamination','Name\tCompleteness\nfixture\t97\n'),('NaN-completeness','Name\tCompleteness\tContamination\nfixture\tnan\t0\n'),('infinite-contamination','Name\tCompleteness\tContamination\nfixture\t97\tinf\n'),('wrong-genome','Name\tCompleteness\tContamination\nother\t97\t1\n'),('empty-report','Name\tCompleteness\tContamination\n'),('negative-contamination','Name\tCompleteness\tContamination\nfixture\t97\t-1\n')]:
 r.write_text(body);assert_reject(name,lambda:p.parse_quality_report(r,'fixture'))
ready=base/'not_ready.json';ready.write_text(json.dumps({'status':'READY_FOR_RESOURCE_PILOT','import_smoke_passed':True,'model_load_smoke_passed':False}));assert_reject('model-smoke-false cannot launch',lambda:p.ready_gate(ready))
ready.write_text(json.dumps({'status':'READY_FOR_RESOURCE_PILOT','import_smoke_passed':True,'model_load_smoke_passed':True,'checkm2_version':'1.0.0','diamond_version':'2.1.11'}));assert_reject('unpinned-program-version cannot launch',lambda:p.ready_gate(ready))
pinned={'status':'READY_FOR_RESOURCE_PILOT','import_smoke_passed':True,'model_load_smoke_passed':True,'checkm2_version':'1.1.0','diamond_version':'2.1.11'}
ready.write_text(json.dumps({**pinned,'runtime_environment_overrides':{'LD_PRELOAD':'fixture-never-loaded'}}));assert_reject('arbitrary loader override is rejected',lambda:p.ready_gate(ready),'Unreviewed runtime environment control')
ready.write_text(json.dumps({**pinned,'runtime_environment_overrides':{'GLIBC_TUNABLES':'fixture-not-current-and-never-applied'}}));assert_reject('declared process control must match actual environment',lambda:p.ready_gate(ready),'actual process environment differs')
assert_reject('outside-project path rejected',lambda:p.inside('/tmp'))
saved_marker=os.environ.pop('TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED',None);saved_prepare=p.prepare;called=[]
def forbidden_prepare():
 called.append(True);raise AssertionError('Preparation/preflight must not start outside the verified image namespace')
p.prepare=forbidden_prepare
try:
 try:p.main(types.SimpleNamespace(run=True))
 except RuntimeError as error:assert 'WAITING_RUNTIME_NAMESPACE' in str(error)
 else:raise AssertionError('Bare execution unexpectedly admitted')
 assert not called
 tests.append({'check':'bare execution rejected before preparation or tool/model hashing','status':'PASS'})
finally:
 p.prepare=saved_prepare
 if saved_marker is not None:os.environ['TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED']=saved_marker
run=base/'intermediates';(run/'output/protein_files').mkdir(parents=True,exist_ok=True);(run/'output/diamond_output').mkdir(exist_ok=True)
(run/'output/protein_files/fixture.faa').write_text('>geneA\nMKKL\n');(run/'predict.stderr.txt').write_text('Finished Running DIAMOND\nProcessing DIAMOND output\n');tbl=run/'output/diamond_output/DIAMOND_RESULTS.tsv';tbl.write_text('')
binding={'input':{'accession':'fixture'}};x=p.collect_intermediates(run,binding);assert x['compatible_for_author_resume'] is False;tests.append({'check':'empty DIAMOND is not resumable despite completion-like text','status':'PASS'})
tbl.write_text('fixtureΩgeneA\tref~K00001\t99\t4\t0\t0\t1\t4\t1\t4\t1e-9\t40\n');x=p.collect_intermediates(run,binding);assert x['compatible_for_author_resume'] is True;tests.append({'check':'synthetic complete intermediate schema recognized only as fixture','status':'PASS'})
(run/'output/protein_files/fixture.faa').write_text('>geneA\n');x=p.collect_intermediates(run,binding);assert x['compatible_for_author_resume'] is False;tests.append({'check':'empty protein invalidates resumability','status':'PASS'})
result={'status':'PASS','fixture_only':True,'no_scientific_prediction_run':True,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tests':tests,'controller_sha256':p.sha(R/'scripts/checkm2_pilot.py')};p.save(R/'evidence/checkm2_pilot/controller_selftest.json',result);print(json.dumps(result))
