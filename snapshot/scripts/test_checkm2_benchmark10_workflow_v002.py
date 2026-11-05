"""Synthetic source/checkpoint regressions; no accepted helper/runtime calls."""
from pathlib import Path
import ast,hashlib,json,sys,uuid
import checkm2_benchmark10_common_v002 as c
folder=c.R/'work/benchmark10_source_fixtures'/uuid.uuid4().hex;folder.mkdir(parents=True);checks=[]
assert c.unit_closed({'status':'UNIT_EXIT0_GROUP_CLOSED','exit_code':0,'owned_group_empty':True,'remaining_owned_processes':[]})
for value in (None,False,0.0,2):assert not c.unit_closed({'status':'UNIT_EXIT0_GROUP_CLOSED','exit_code':value,'owned_group_empty':True,'remaining_owned_processes':[]})
checks.append('Only observed typed exit0 and empty owned group admit a unit; missing/unknown/false are not zero')
payload=folder/'payload.txt';payload.write_text('synthetic checkpoint');manifest=c.manifest(folder);c.verify_manifest(folder,c.read(c.bind(manifest)));payload.write_text('tampered')
try:c.verify_manifest(folder,c.read(c.bind(manifest)))
except RuntimeError:checks.append('Tampered committed payload rejected; no recomputation path invoked')
else:raise AssertionError('Tampered checkpoint reused')
pending={'launch_token':'a'*32,'input_plan_sha256':'b'*64,'protocol_admission_sha256':'c'*64,'namespace_execution_receipt_path':str(folder/'namespace.json')}
assert c.pending_is_current(pending,'a'*32,'b'*64,'c'*64,folder/'namespace.json')
assert not c.pending_is_current(pending,'d'*32,'b'*64,'c'*64,folder/'namespace.json');checks.append('A prior phase pending pointer cannot supply current group closure')
entry=ast.parse((c.R/'scripts/checkm2_benchmark10_entry_v002.py').read_text());publish_node=next(n for n in entry.body if isinstance(n,ast.FunctionDef) and n.name=='publish');step=folder/'step.json';launch={'token':'e'*32,'started_utc':'synthetic','pid':123,'creation_time_utc':'synthetic'}
env={'read':c.read,'save':c.save,'STATE':step,'utc':lambda:'synthetic','native_identity':lambda pid:{'pid':pid},'os':type('FakeOS',(),{'getpid':staticmethod(lambda:456)})}
exec(compile(ast.Module(body=[publish_node],type_ignores=[]),'<benchmark-counter-fixture>','exec'),env)
c.save(step,{'windows_launch_token':'e'*32,'done':10});env['publish'](launch,'closed-image hashing');assert c.read(step)['done']==10 and c.read(step)['total']==10
c.save(step,{'windows_launch_token':'f'*32,'done':10});env['publish'](launch,'new phase preflight');assert c.read(step)['done']==0;checks.append('Image sealing preserves only current-token verified annotation counts, never a prior phase count')
batch=folder/'batch';(batch/'validation_x').mkdir(parents=True);budget=batch/'validation_x_budget.json';terminal=batch/'validation_x/execution.json';c.save(budget,{'debit_before_start_seconds':123});c.save(terminal,{'elapsed_seconds':45});bindings=[c.row(budget),c.row(terminal)];c.verify_budget_set(batch,bindings);budget.unlink()
try:c.verify_budget_set(batch,bindings)
except (RuntimeError,FileNotFoundError):checks.append('Deleting a prior validation budget cannot reset the shared debit')
else:raise AssertionError('Deleted debit accepted')
run=folder/'run';run.mkdir();unit=folder/'unit';unit.mkdir();c.save(unit/'command.json',{});c.save(run/'invocations.json',[str(unit)])
assert not c.group_receipts_closed(run);checks.append('A started current invocation without terminal evidence stays unclosed')
inner=ast.parse((c.R/'scripts/checkm2_benchmark10_inner_v002.py').read_text());batch_fn=next(n for n in inner.body if isinstance(n,ast.FunctionDef) and n.name=='batch');branch=next(n for n in batch_fn.body if isinstance(n,ast.If) and ast.unparse(n.test)=="phase == 'VALIDATE_COMMITTED_BATCH'")
assert not any(isinstance(n,ast.Constant) and n.value=='unit_batch_quality' for node in branch.body for n in ast.walk(node));checks.append('Explicit validation-only branch contains no prediction invocation')
checkpoint=folder/'annotation_checkpoint';(checkpoint/'unit_annotation').mkdir(parents=True);faa=checkpoint/'selected.txt';faa.write_text('SYNTHETIC');c.save(checkpoint/'receipt.json',{'faa_sha256':c.sha(faa)});c.save(checkpoint/'unit_annotation/execution.json',{'status':'UNIT_EXIT0_GROUP_CLOSED','exit_code':0,'owned_group_empty':True,'remaining_owned_processes':[]});binding={'input':{'accession':'SYNTHETIC_ACCESSION'}}
commit={'status':'ANNOTATION_EXIT0_VALIDATED_ATOMIC_COMMIT','binding':binding,'native_launch_token':'prior','manifest':c.manifest(checkpoint),'annotation_receipt':c.row(checkpoint/'receipt.json'),'selected_faa':c.row(faa)};c.save(checkpoint/'commit.json',commit)
node=next(n for n in inner.body if isinstance(n,ast.FunctionDef) and n.name=='committed_annotation');env={'c':c,'LAUNCH':{'token':'current'},'CLOSED_TOKENS':{'prior'},'RESUME_PROOF':{'annotation_commit_sha256s':{'SYNTHETIC_ACCESSION':c.sha(checkpoint/'commit.json')}}};exec(compile(ast.Module(body=[node],type_ignores=[]),'<annotation-reuse-fixture>','exec'),env)
assert env['committed_annotation'](checkpoint,binding)==commit
c.save(checkpoint/'commit.json',{**commit,'native_launch_token':'other'})
try:env['committed_annotation'](checkpoint,binding)
except RuntimeError:checks.append('Reuse needs externally bound commit hash and prior launch token; commit-record tampering is rejected')
else:raise AssertionError('Changed commit accepted')
proof_path=folder/'prior_phase_proof.json';proof={'status':'BENCHMARK_PHASE_NATIVE_GROUP_NAMESPACE_IMAGE_LEASE_CLOSED','native_exit_code_observed':0,'session_identity_sha256':'synthetic'};c.save(proof_path,proof)
try:c.resume_proof({'phase':'CONTINUE','resume_authority':c.row(proof_path)},'synthetic')
except RuntimeError as error:assert 'WSL' in str(error);checks.append('Missing prior WSL exit cannot qualify as an actual closed resumable phase')
else:raise AssertionError('Unknown WSL exit admitted')
shell=(c.R/'scripts/checkm2_benchmark10_protein_v002.sh').read_bytes();assert b'\r' not in shell and shell.startswith(b'#!/bin/bash\n');native=(c.R/'scripts/checkm2_benchmark10_native_v002.py').read_text();assert "'/usr/bin/env','TREE2_CHECKM2_PILOT_LAUNCH_TOKEN='+TOKEN" in native;checks.append('New executed shell is LF-only and native keeps explicit Linux-side token transport')
assert not any(n in sys.modules for n in ('numpy','pandas','tensorflow','keras','lightgbm','sklearn','checkm2.prodigal'))
for p in (c.R/'scripts').glob('*benchmark10*v002.py'):ast.parse(p.read_text())
c.save(c.E/'workflow_source_fixture_report.json',{'status':'PASS_SYNTHETIC_SOURCE_FIXTURES_NOT_REAL_RESUME','checks':checks,'actual_FNA_FAA_pickle_models_helpers_or_phase_executed':False,'real_boundary_stop_resume_demonstrated':False});print(json.dumps({'status':'PASS_SOURCE_ONLY','checks':len(checks)}))
