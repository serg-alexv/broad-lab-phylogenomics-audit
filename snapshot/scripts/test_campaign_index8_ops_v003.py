"""Pure source/request fixtures; never import OPS/science targets or create processes."""
from pathlib import Path
import ast,hashlib,json,types
R=Path(__file__).resolve().parents[1]
def tree(name):return ast.parse((R/'scripts'/name).read_text(encoding='utf-8-sig'))
def function(t,name):return next(x for x in t.body if isinstance(x,ast.FunctionDef) and x.name==name)
def pure(t,names,ns):
 exec(compile(ast.Module(body=[function(t,n) for n in names],type_ignores=[]),'<actual OPS pure functions>','exec'),ns)
 return ns
def main():
 n=tree('checkm2_campaign_index8_native_v004.py');e=tree('checkm2_campaign_index8_entry_v003.py')
 oldn=tree('checkm2_P20_resource_repair_native_v002.py');olde=tree('checkm2_P20_resource_repair_entry_v002.py')
 checks=[]
 for count in (1,19,20):
  c=types.SimpleNamespace(COUNT=count,LIMITS={'cold_session_seconds':33000})
  for target,ns in ((n,{'c':c,'COMMITTED_DONE':0}),(e,{'common':c,'CONTEXT':{}})):
   pure(target,('committed_done','require_core_result'),ns)
   good={'status':'P20_CORE_PENDING_NAMESPACE_NATIVE_CLOSURE','completed_qc_rows':count,'rows':[{} for _ in range(count)]}
   assert ns['require_core_result'](good)==count
   assert ns['committed_done'](count)==count and ns['committed_done'](0)==count and ns['committed_done'](count+1)==count
   for bad in ({**good,'completed_qc_rows':True},{**good,'rows':[]},{**good,'rows':[{} for _ in range(count+1)]},{**good,'completed_qc_rows':0},{**good,'status':'COMPLETE'}):
    try:ns['require_core_result'](bad)
    except RuntimeError:pass
    else:raise AssertionError('Malformed cohort result accepted')
 checks.append('typed_N_results_and_monotone_bounded_counts_for1_19_20')
 for target,alias,bound in ((n,'c','STEP'),(e,'common','STATE')):
  configured=next(x.lineno for x in target.body if isinstance(x,ast.Expr) and ast.unparse(x)==alias+'.configure_argv()')
  assigned=next(x.lineno for x in target.body if isinstance(x,ast.Assign) and any(isinstance(y,ast.Name) and y.id==bound for y in x.targets))
  assert configured<assigned
 checks.append('cohort_configured_before_path_and_counter_globals')
 for name in ('identity','linux','file_state','group_receipts_closed','common_locks','record_display_error'):
  assert ast.dump(function(n,name),include_attributes=False)==ast.dump(function(oldn,name),include_attributes=False),name
 for name in ('record_display_error','save_display','read','save','sha','inside','native_identity','linux_available_bytes','hash_closed_image'):
  assert ast.dump(function(e,name),include_attributes=False)==ast.dump(function(olde,name),include_attributes=False),name
 checks.append('exact_original_identity_partial_lock_optional_IO_and_posthash_guards_retained')
 locked=function(n,'locked_main');calls=[x for x in ast.walk(locked) if isinstance(x,ast.Call)]
 update=next(x for x in calls if isinstance(x.func,ast.Attribute) and isinstance(x.func.value,ast.Name) and x.func.value.id=='request' and x.func.attr=='update')
 keywords={x.arg:x.value for x in update.keywords}
 class Clock:
  @staticmethod
  def monotonic():return 100.0
  @staticmethod
  def time():return 2000.0
 for cold in (3000,33000,40800):
  ns={'c':types.SimpleNamespace(LIMITS={'cold_session_seconds':cold}),'time':Clock,'COLD_STARTED_MONOTONIC':10.0,'max':max}
  values={k:eval(compile(ast.Expression(v),'<actual request expression>','eval'),ns) for k,v in keywords.items()}
  assert values['cold_session_seconds']==cold and values['helper_max_seconds']==cold-1240
  assert values['prehelper_preflight_max_seconds']==600 and values['post_unmount_hash_max_seconds']==600 and values['fatal_cleanup_seconds']==40
  assert values['cold_wall_deadline_unix']==2000+cold-90
 checks.append('immutable_request_cold_helper_split_and_consumed_wall_time_not_reset')
 helper=next(x.value for x in ast.walk(function(e,'main')) if isinstance(x,ast.Assign) and any(isinstance(y,ast.Name) and y.id=='helper_seconds' for y in x.targets))
 value=eval(compile(ast.Expression(helper),'<actual helper budget expression>','eval'),{'common':types.SimpleNamespace(LIMITS={'cold_session_seconds':33000}),'CONTEXT':{'cold_monotonic_deadline':30000.0},'time':Clock,'min':min})
 assert value==min(31760,30000-100-640)
 checks.append('actual_entry_helper_deadline_clipped_by_remaining_cold_minus640')
 popen=next(x for x in calls if isinstance(x.func,ast.Attribute) and x.func.attr=='Popen')
 argv=ast.unparse(popen.args[0])
 assert argv.index("'/usr/bin/env'")<argv.index("'/bin/bash'")
 for key in ('TREE2_CHECKM2_PILOT_LAUNCH_TOKEN=','TREE2_QC_BATCH_PLAN=','TREE2_QC_BATCH_PLAN_SHA256=','--input-plan','--input-plan-sha256'):
  assert key in argv,key
 assert 'checkm2_campaign_index8_shell_v004.sh' in argv
 checks.append('explicit_Linux_token_plan_SHA_transport_and_exact_entry_arguments')
 raw=(R/'scripts/checkm2_campaign_index8_shell_v004.sh').read_bytes()
 assert b'\r' not in raw and raw.startswith(b'#!/bin/bash\n') and b'"$@"' in raw
 assert b'${TREE2_QC_BATCH_PLAN:?}' in raw and b'${TREE2_QC_BATCH_PLAN_SHA256:?}' in raw and b'"$#" == 4' in raw
 checks.append('LF_only_shell_exact_four_args_ENV_match_and_forwarding_no_runtime_bash')
 base=(R/'scripts/checkm2_campaign_index8_native_v003.py').read_bytes()
 new=(R/'scripts/checkm2_campaign_index8_native_v004.py').read_bytes()
 assert new.replace(b'checkm2_campaign_index8_common_v003',b'checkm2_campaign_index8_common_v002').replace(b'checkm2_campaign_index8_shell_v004.sh',b'checkm2_campaign_index8_shell_v003.sh')==base
 base=(R/'scripts/checkm2_campaign_index8_entry_v002.py').read_bytes()
 new=(R/'scripts/checkm2_campaign_index8_entry_v003.py').read_bytes()
 assert new.replace(b'checkm2_campaign_index8_common_v003',b'checkm2_campaign_index8_common_v002').replace(b'checkm2_campaign_index8_inner_v003.py',b'checkm2_campaign_index8_inner_v002.py')==base
 base=(R/'scripts/checkm2_campaign_index8_shell_v003.sh').read_bytes()
 assert raw.replace(b'checkm2_campaign_index8_entry_v003.py',b'checkm2_campaign_index8_entry_v002.py')==base
 assert b'if [[ \"$#\" == 0 ]]; then' in raw and b'set -- --input-plan \"${TREE2_QC_BATCH_PLAN:?}\"' in raw
 wrapper=(R/'scripts/checkm2_private_setup_ns.sh').read_bytes()
 assert hashlib.sha256(wrapper).hexdigest()=='0dce7c1d87e3f417e76c5d800a6ea8282d3cada8cf1ffbd31bad8ffb39c98f5a'
 assert b'exec /bin/bash \"$SCRIPT\"\n' in wrapper
 checks.append('exact_reversible_namespace_only_deltas_from_corrected_transport_and_zero_argv_bridge')
 text=ast.unparse(locked)
 assert "progress('RUNNING'" in text and text.index("progress('RUNNING'")<text.index('subprocess.Popen')
 assert 'ownership.scoped_stop' in text and 'ownership.immutable_handoff' in text and 'child.wait()' in text
 assert 'guest_cleanup_not_inferred_from_WSL_exit' in text and 'required_terminal_write_error' in text
 assert not any(isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr in ('kill','terminate','killpg','TerminateProcess') for x in ast.walk(n))
 checks.append('prelaunch_stage_registration_and_retained_actual_exit_unknown_handoff_preserved')
 assert "'diagnostic_only': False" in ast.unparse(function(n,'progress'))
 assert "'total': c.COUNT" in ast.unparse(function(n,'progress')) and "'total': common.COUNT" in ast.unparse(function(e,'publish'))
 checks.append('campaign_count_and_nonpilot_display_with_no_panel_acceptance')
 print(json.dumps({'status':'TEN_PURE_CAMPAIGN_V3_OPS_GROUPS_PASS','count':len(checks),'checks':checks,'target_imports_or_process_or_runtime_or_science':False},indent=2))
if __name__=='__main__':main()
