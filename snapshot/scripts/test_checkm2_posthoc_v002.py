"""Small checksum/domain fixtures; no saved pickle, genome, FAA or models opened."""
from pathlib import Path
import ast,json,sys,uuid
import checkm2_posthoc_v002_validator as v
R=v.R;checks=[]
assert v.domain_valid('NONNEGATIVE_REAL_COPY_COUNT_MEAN',[0,1,2.5]);checks.append('Module raw-copy means above1 accepted without clipping')
assert not v.domain_valid('MEMBERSHIP_FRACTION',[1.1]);checks.append('Pathway/category upper bound remains1')
assert not v.domain_valid('NONNEGATIVE_INTEGER',[.5]);checks.append('Raw counts remain integral')
assert not v.domain_valid('NONNEGATIVE_REAL_COPY_COUNT_MEAN',[float('nan')]);checks.append('Unknown/nonfinite module value rejected')
folder=R/'work/checkm2_posthoc_v002_fixtures'/uuid.uuid4().hex;folder.mkdir(parents=True);p=folder/'synthetic.txt';p.write_text('not a pickle')
try:v.bind({'path':str(p),'sha256':'0'*64})
except RuntimeError:checks.append('Checksum failure rejects before any pickle/pandas import')
else:raise AssertionError('Wrong hash accepted')
assert v.no_models()==[] and 'pandas' not in sys.modules and 'numpy' not in sys.modules
tree=ast.parse((R/'scripts/checkm2_posthoc_v002_controller.py').read_text())
condition=next(node.value for node in ast.walk(tree) if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='stable' for t in node.targets))
def stable(inside,closure):return eval(compile(ast.Expression(condition),'<closure-fixture>','eval'),{'child_closed':True,'inside':inside,'closure':closure})
assert stable({'owned_group_empty':True},{'status':'CLEAN_UNMOUNT_AND_LOOP_DETACH','readonly':True})
assert not stable(None,None) and not stable({'owned_group_empty':False},{'status':'CLEAN_UNMOUNT_AND_LOOP_DETACH','readonly':True})
checks.append('Native client exit alone does not mark unproved guest outputs stable')
for p in (R/'scripts').glob('*posthoc_v002*.py'):ast.parse(p.read_text())
v.save(R/'evidence/checkm2_posthoc_v002/source_fixture_report.json',{'status':'PASS_SOURCE_FIXTURES_NO_ACTUAL_ARTIFACT_UNPICKLE','checks':checks,'model_or_real_genome_FAA_pickle_access':False,'validator_sha256':v.sha(Path(v.__file__))});print(json.dumps({'status':'PASS','checks':len(checks)}))
