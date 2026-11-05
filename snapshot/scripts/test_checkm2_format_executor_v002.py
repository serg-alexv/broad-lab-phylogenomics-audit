"""Narrow source/control fixtures; no actual biological data or author imports."""
from pathlib import Path
from types import SimpleNamespace
import ast,json,sys,uuid
import checkm2_format_common_v002 as c
import checkm2_format_compare_closed_v002 as compare
R=c.R;folder=R/'work/checkm2_format_v002_fixtures'/uuid.uuid4().hex;folder.mkdir(parents=True);checks=[]
before={r['path']:c.v.sha(R/r['path']) for r in c.v.read(R/'metadata/checkm2_protein_implementation_v001.json')['sources']}
source=folder/'synthetic.txt';derived=folder/'synthetic_rewrapped.txt';source.write_text('>synthetic header\n'+'ACGT'*40+'\n')
receipt=c.fasta.rewrap_new(source,derived,61)
assert receipt['original_sha256']!=receipt['derived_sha256'] and receipt['original_semantics']==receipt['derived_semantics'];checks.append('Synthetic wrap61 changes bytes while retaining ordered header/sequence semantics')
try:c.fasta.rewrap_new(source,derived,61)
except FileExistsError:checks.append('An existing derived artifact cannot be silently replaced')
else:raise AssertionError('Derived overwrite accepted')
bad=folder/'wrong_role.json';c.v.save(bad,{'schema':c.PLAN_SCHEMA,'role':'OTHER'})
try:c.plan_gate(bad,c.v.sha(bad),require_admission=False)
except RuntimeError as ex:assert 'wrap61' in str(ex);checks.append('Wrong experiment rejected before baseline or variant access')
else:raise AssertionError('Wrong role accepted')
tree=ast.parse((R/'scripts/checkm2_format_native_v002.py').read_text())
def method(name,env):
 node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name);exec(compile(ast.Module(body=[node],type_ignores=[]),'<fixture>','exec'),env);return env[name]
run=folder/'run';(run/'unit01').mkdir(parents=True);c.v.save(run/'unit01/command.json',{});c.v.save(run/'unit01/execution.json',{'owned_group_empty':True});(run/'unit02').mkdir();c.v.save(run/'unit02/command.json',{})
closed=method('group_receipts_closed',{'c':c});assert not closed(run);checks.append('A later started unit without terminal receipt is not declared closed')
import checkm2_private_install_controller as base
fake=SimpleNamespace(E=folder,v=c.v,STATE=folder/'dedicated.json')
publish=method('progress',{'c':fake,'base':base,'R':folder,'START':base.START,'COMMAND':'fixture project command','TOKEN':'f'*32})
publish('RUNNING','Synthetic registration fixture')
registered=c.v.read(folder/'state/stages/04.json');assert registered['pid']==base.OWNER['pid'] and registered['creation_time_utc']==base.OWNER['creation_time_utc'] and registered['status']=='RUNNING'
publish('PENDING_NATIVE_EXIT_AND_COMPARISON','Awaiting externally observed exit',1,pid=None,creation_time_utc=None)
pending=c.v.read(folder/'state/stages/04.json');assert pending['status']!='COMPLETED' and 'pid' not in pending;checks.append('Standard stage04 carries actual owner and remains pending after core completion')
inner_tree=ast.parse((R/'scripts/checkm2_format_inner_v002.py').read_text());node=next(n for n in inner_tree.body if isinstance(n,ast.FunctionDef) and n.name=='progress')
env={'c':c,'STEP':folder/'inner_step.json','pilot':SimpleNamespace(legacy=SimpleNamespace(stat=lambda pid:{'pid':31415})),'os':SimpleNamespace(getpid=lambda:31415),'LAUNCH':{'token':'a'*32,'pid':base.OWNER['pid'],'creation_time_utc':base.OWNER['creation_time_utc']},'utc':base.utc}
exec(compile(ast.Module(body=[node],type_ignores=[]),'<handoff-fixture>','exec'),env);env['progress']('RUNNING','actual annotation unit')
inner_row=c.v.read(folder/'inner_step.json');entry_tree=ast.parse((R/'scripts/checkm2_format_entry_v002.py').read_text())
test=next(n.test for n in ast.walk(entry_tree) if isinstance(n,ast.If) and "current.get('windows_launch_token')" in ast.unparse(n.test))
assert eval(compile(ast.Expression(test),'<entry-handoff>','eval'),{'current':inner_row,'token':'a'*32,'os':SimpleNamespace(getpid=lambda:27182)})
assert inner_row['detail']=='actual annotation unit';checks.append('Bound inner launch token gives the scientific substep ownership over entry preflight text')
try:compare.closed_native_proof({'status':'FORMAT_CONTROL_NATIVE_GROUP_NAMESPACE_IMAGE_LEASE_CLOSED'}, {'native_owner':{}},'0'*64,'0'*64)
except RuntimeError:checks.append('A missing external actual-exit/lease proof cannot finalize comparison')
else:raise AssertionError('Incomplete native proof accepted')
for name in ('checkm2_format_common_v002.py','checkm2_format_inner_v002.py','checkm2_format_entry_v002.py','checkm2_format_native_v002.py','checkm2_format_compare_closed_v002.py','prepare_checkm2_format_executor_v002.py'):ast.parse((R/'scripts'/name).read_text())
assert before=={name:c.v.sha(R/name) for name in before}
assert not any(n in sys.modules for n in ('pandas','numpy','tensorflow','keras','lightgbm','sklearn','checkm2.prodigal'))
c.v.save(c.E/'source_fixture_report.json',{'status':'PASS_HELD_SOURCE_FIXTURES_NO_ACTUAL_VARIANT_OR_AUTHOR_RUN','checks':checks,'original_twelve_sources_unchanged':True,'actual_genome_FAA_pickle_or_model_parse':False});print(json.dumps({'status':'PASS','checks':len(checks)}))
