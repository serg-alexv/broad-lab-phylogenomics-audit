"""HELD operational recovery policy/controller copies; source and metadata only."""
from pathlib import Path
import ast,hashlib,json,os
R=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(name):
 p=R/name;return {'path':name,'sha256':sha(p),'bytes':p.stat().st_size}
def write(name,data):
 p=R/name;data=data.encode() if isinstance(data,str) else data
 if p.exists():
  if p.read_bytes()!=data:raise RuntimeError('Refusing changed held-source overwrite:'+name)
 else:
  with p.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 return pin(name)
def original(name):
 manifest_path=R/'metadata/checkm2_benchmark10_implementation_v002.json'
 if sha(manifest_path)!='ca7d48fc4ac927209cce4e4d3e2b4bbef9d9ecc99984d98aa4f30a94f5cb65f0':raise RuntimeError('Original37 manifest changed')
 manifest=json.loads(manifest_path.read_text());row=next(x for x in manifest['sources'] if x['path']=='scripts/'+name);p=R/row['path']
 if sha(p)!=row['sha256']:raise RuntimeError('Original bound source changed:'+name)
 return p.read_text()
def main():
 closure=pin('evidence/checkm2_benchmark10_protein_v002/boundary_failure_closure.json')
 if closure['sha256']!='ad6de26da985d250acaf202bc33bd3e7a0b8b32e7358cc29e5726c36cca357ea':raise RuntimeError('Prior failed-boundary closure differs')
 policy={'schema':'TREE2_BENCHMARK10_OPERATIONAL_RECOVERY_POLICY_T1','status':'HELD_OPERATIONAL_REPAIR_NO_RETRY_OR_EXECUTION_ADMISSION','original_scientific_recipe':pin('metadata/checkm2_benchmark10_protein_recipe_v002_bound.json'),'original_source_manifest':pin('metadata/checkm2_benchmark10_implementation_v002.json'),'original_execution_plan':pin('metadata/checkm2_benchmark10_execution_plan_v002.json'),'failed_boundary_closure':closure,'failed_protocol_admission_sha256':'ac3e4b1135556dd4dba99405662afbca6883cc46514f921ff94a60e16f04feb2','old_annotation_attempts':1,'old_accepted_annotation_commits':0,'old_annotation_exit':'UNKNOWN_MISSING_EXECUTION_RECEIPT','old_ordinary_unmount':'UNKNOWN_MISSING_RECEIPTS','original_annotation_compute_budget_seconds':6000,'historical_unknown_attempt_conservative_debit_seconds':600,'new_session_annotation_budget_seconds':5400,'per_physical_unit_max_seconds':600,'new_logical_genomes':10,'maximum_new_physical_annotation_attempts':10,'maximum_total_physical_annotation_attempts':11,'batch_prediction_attempts_before_recovery':0,'batch_prediction_plus_validation_seconds_remaining':3600,'workspace':'analysis/checkm2_benchmark10_protein_recovery_T1','old_partials_reused_promoted_deleted_or_overwritten':False,'new_complete_first_annotation_boundary_required_before_CONTINUE':True,'stock_fork_math_flags_10_inputs_and_all3_holds_unchanged':True,'optional_telemetry_helper':pin('scripts/checkm2_optional_telemetry_v001.py'),'new_runtime_probe_or_scientific_run_authorized':False,'root_repair_admission':None,'new_actual_outputs':None}
 if policy['original_scientific_recipe']['sha256']!='2e003f02e6b1886ebe65c4e4d7a9351d84e6ad404d09384ece668089ba3f5fce':raise RuntimeError('Scientific recipe changed')
 policy_row=write('metadata/checkm2_benchmark10_recovery_policy_T1.json',json.dumps(policy,indent=2)+'\n')
 common=original('checkm2_benchmark10_common_v002.py').replace('checkm2_benchmark10_protein_v002','checkm2_benchmark10_protein_recovery_T1').replace('STOP_CHECKM2_BENCHMARK10_PROTEIN_V002','STOP_CHECKM2_BENCHMARK10_RECOVERY_T1').replace('checkm2_benchmark10_protein_protocol_ready_v002.json','checkm2_benchmark10_protein_recovery_T1_ready.json')
 common=common.replace("def path(value):", "UNRESOLVED_HANDOFF=E/'unresolved_ownership_handoff.json'\n\ndef path(value):")
 additions='''
def unresolved_ownership_gate(admission=None):
 records=list((UNRESOLVED_HANDOFF.parent/'unresolved_ownership').glob('*.json'))
 if UNRESOLVED_HANDOFF.exists():records.append(UNRESOLVED_HANDOFF)
 if not records:return
 if not admission or not admission.get('unresolved_ownership_external_closure'):raise RuntimeError('HELD_UNRESOLVED_T1_OWNERSHIP_HANDOFF_NO_RELAUNCH')
 closure=read(bind(admission['unresolved_ownership_external_closure']))
 expected={bind(x).resolve() for x in closure.get('unresolved_handoff_bindings',[])}
 if {p.resolve() for p in records}!=expected or closure.get('status')!='T1_UNRESOLVED_OWNER_EXTERNALLY_CLOSED' or any(closure.get(k) is not True for k in ('all_recorded_identities_absent','all_groups_contexts_and_loops_closed','common_leases_released','image_unchanged')):raise RuntimeError('Any unresolved T1 ownership requires separately bound external closure of the exact complete handoff set')
def recovery_policy_gate(plan,admission=None):
 policy=read(bind(plan['operational_recovery_policy']))
 expected={'old_annotation_attempts':1,'old_accepted_annotation_commits':0,'original_annotation_compute_budget_seconds':6000,'historical_unknown_attempt_conservative_debit_seconds':600,'new_session_annotation_budget_seconds':5400,'per_physical_unit_max_seconds':600,'new_logical_genomes':10,'maximum_new_physical_annotation_attempts':10,'maximum_total_physical_annotation_attempts':11,'batch_prediction_attempts_before_recovery':0,'batch_prediction_plus_validation_seconds_remaining':3600}
 if any(policy.get(k)!=v for k,v in expected.items()) or policy.get('old_annotation_exit')!='UNKNOWN_MISSING_EXECUTION_RECEIPT' or policy.get('old_partials_reused_promoted_deleted_or_overwritten') is not False:raise RuntimeError('T1 prior attempt/debit/preservation policy differs')
 if policy['failed_boundary_closure']['sha256']!='ad6de26da985d250acaf202bc33bd3e7a0b8b32e7358cc29e5726c36cca357ea':raise RuntimeError('T1 prior failed closure differs')
 bind(policy['failed_boundary_closure'])
 if policy['original_scientific_recipe']['sha256']!=plan['recipe']['sha256'] or plan['recipe']['sha256']!='2e003f02e6b1886ebe65c4e4d7a9351d84e6ad404d09384ece668089ba3f5fce' or policy.get('workspace')!=OUT.relative_to(R).as_posix():raise RuntimeError('T1 scientific recipe or isolated workspace differs')
 if admission is not None and admission.get('operational_recovery_policy_sha256')!=plan['operational_recovery_policy']['sha256']:raise RuntimeError('T1 phase authority does not bind the historical debit/recovery policy')
 return policy
'''
 common+=additions
 common=common.replace("if not require_admission:return plan,strategy,None", "recovery_policy_gate(plan)\n if not require_admission:unresolved_ownership_gate();return plan,strategy,None")
 common=common.replace(" a=read(ADMISSION)\n", " a=read(ADMISSION)\n recovery_policy_gate(plan,a);unresolved_ownership_gate(a)\n")
 inner=original('checkm2_benchmark10_inner_v002.py').replace('checkm2_benchmark10_common_v002','checkm2_benchmark10_common_T1').replace('checkm2_benchmark10_protein_v002','checkm2_benchmark10_protein_recovery_T1')
 budget='''
def new_annotation_budget(session):
 units=list((session/'annotations').glob('*/unit_annotation/command.json'))
 if len(units)>10:raise RuntimeError('T1 physical annotation attempt cap exceeded')
 used=0.0
 for command in units:
  terminal=command.with_name('execution.json')
  if not terminal.exists():raise RuntimeError('T1 prior new-session annotation exit/debit UNKNOWN; no reset or re-execution')
  execution=c.read(terminal);elapsed=float(execution['elapsed_seconds'])
  if not math.isfinite(elapsed) or elapsed<0 or execution.get('owned_group_empty') is not True:raise RuntimeError('T1 annotation elapsed/closure unproved')
  used+=elapsed
 if used>5400:raise RuntimeError('T1 new-session5400s annotation allowance exhausted')
 return {'historical_debit_seconds':600,'new_annotation_seconds_debited':used,'new_remaining_seconds':5400-used,'original_total_seconds':6000,'new_physical_attempts':len(units),'total_physical_attempts':1+len(units)}
'''
 inner=inner.replace('def annotate(item,runtime,plan,session,run):',budget+'\ndef annotate(item,runtime,plan,session,run):')
 inner=inner.replace("source=pilot.verify_input(item);folder.mkdir", "budget=new_annotation_budget(session)\n if budget['new_remaining_seconds']<=0:raise TimeoutError('No remaining T1 annotation budget')\n source=pilot.verify_input(item);folder.mkdir")
 inner=inner.replace("],pilot.environment(Path(runtime['prefix'])),folder,run,600)","],pilot.environment(Path(runtime['prefix'])),folder,run,min(600,budget['new_remaining_seconds']))\n c.save(session/'annotation_budget_ledger.json',new_annotation_budget(session))")
 inner=inner.replace("'input_plan_sha256':a.input_plan_sha256,'namespace_execution_receipt_path'", "'input_plan_sha256':a.input_plan_sha256,'namespace_execution_receipt_path'")
 close=original('checkm2_benchmark10_close_v002.py').replace('checkm2_benchmark10_common_v002','checkm2_benchmark10_common_T1')
 close=close.replace("'production_or_full_panel_acceptance':False,", "'production_or_full_panel_acceptance':False,'operational_recovery_policy':plan['operational_recovery_policy'],'historical_unknown_annotation_debit_seconds':600,'new_session_annotation_ceiling_seconds':5400,")
 rows=[]
 for name,text in [('checkm2_benchmark10_common_T1.py',common),('checkm2_benchmark10_inner_T1.py',inner),('checkm2_benchmark10_close_T1.py',close)]:
  ast.parse(text);rows.append(write('scripts/'+name,text))
 print(json.dumps({'status':'HELD_SOURCE_AND_POLICY_ONLY','policy':policy_row,'new_controller_sources':rows,'original37_modified':False,'runtime_or_data_execution':False}))
if __name__=='__main__':main()
