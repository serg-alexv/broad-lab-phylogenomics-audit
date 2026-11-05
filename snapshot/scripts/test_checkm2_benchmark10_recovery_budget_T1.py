"""Pure synthetic recovery-budget/ownership-gate fixtures; no live processes."""
from pathlib import Path
import ast,math,uuid
import checkm2_benchmark10_common_T1 as c
folder=c.R/'work/benchmark10_T1_budget_fixtures'/uuid.uuid4().hex;folder.mkdir(parents=True);checks=[]
source=ast.parse((c.R/'scripts/checkm2_benchmark10_inner_T1.py').read_text());node=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='new_annotation_budget');env={'c':c,'math':math};exec(compile(ast.Module(body=[node],type_ignores=[]),'<T1-budget-fixture>','exec'),env);budget=env['new_annotation_budget']
empty=budget(folder);assert empty['historical_debit_seconds']==600 and empty['new_remaining_seconds']==5400 and empty['total_physical_attempts']==1;checks.append('An empty new isolated session still carries the historical UNKNOWN attempt600s debit')
for index,seconds in enumerate((100.0,200.0)):
 unit=folder/'annotations'/('synthetic'+str(index))/'unit_annotation';unit.mkdir(parents=True);c.save(unit/'command.json',{});c.save(unit/'execution.json',{'elapsed_seconds':seconds,'owned_group_empty':True})
value=budget(folder);assert value['new_remaining_seconds']==5100 and value['new_physical_attempts']==2 and value['total_physical_attempts']==3;checks.append('Known new terminal elapsed debits once while ten logical inputs do not erase the extra historical physical attempt')
missing=folder/'annotations/synthetic1/unit_annotation/execution.json';missing.unlink()
try:budget(folder)
except RuntimeError as error:assert 'UNKNOWN' in str(error);checks.append('Missing new-session terminal elapsed blocks further annotation rather than resetting the allowance')
else:raise AssertionError('Unknown debit became zero')
original=c.UNRESOLVED_HANDOFF;c.UNRESOLVED_HANDOFF=folder/'unresolved.json';c.save(c.UNRESOLVED_HANDOFF,{'synthetic':'unresolved-owner'})
try:
 try:c.unresolved_ownership_gate()
 except RuntimeError as error:assert 'NO_RELAUNCH' in str(error);checks.append('Persistent unresolved ownership hard-blocks a new phase without separate bound external closure')
 else:raise AssertionError('Unresolved owner permitted relaunch')
 handoffs=folder/'unresolved_ownership';handoffs.mkdir();c.save(handoffs/'synthetic.json',{'synthetic':'immutable-owner'});c.UNRESOLVED_HANDOFF.unlink()
 try:c.unresolved_ownership_gate()
 except RuntimeError as error:assert 'NO_RELAUNCH' in str(error);checks.append('Deleting the mutable blocker does not bypass an immutable unresolved ownership record')
 else:raise AssertionError('Immutable unresolved owner bypassed after marker deletion')
finally:c.UNRESOLVED_HANDOFF=original
assert c.OUT.name=='checkm2_benchmark10_protein_recovery_T1' and 'recovery_T1' in c.ADMISSION.name;checks.append('Recovery workspace/Ready routes are isolated from the failed session and claims')
for name in ('checkm2_benchmark10_common_T1.py','checkm2_benchmark10_inner_T1.py','checkm2_benchmark10_close_T1.py'):ast.parse((c.R/'scripts'/name).read_text())
c.save(c.E/'budget_source_fixture_report.json',{'status':'PASS_PURE_SYNTHETIC_T1_BUDGET_GATES_NOT_A_REAL_RETRY','checks':checks,'live_processes_runtime_genomes_FAA_models_or_old_partials_used':False});print({'status':'PASS_SOURCE_ONLY','checks':len(checks)})
