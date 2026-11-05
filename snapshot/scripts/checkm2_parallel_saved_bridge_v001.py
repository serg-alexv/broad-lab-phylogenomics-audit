"""Glue existing admitted RO/IPC owner to exactly one saved-stock callable."""
from pathlib import Path
import argparse,os,time,json,traceback,types
import checkm2_parallel_saved_common_v001 as c
import checkm2_protein_pilot_v001 as pilot
from checkm2_optional_progress_S1R2 import safe_call
import sys,datetime

def main(a):
 plan,_,admission=c.plan_gate(a.input_plan,a.input_plan_sha256);launch=c.read(c.LAUNCH)
 if launch['token']!=a.launch_token or launch['input_plan_sha256']!=a.input_plan_sha256:raise RuntimeError('Exact Root companion launch differs')
 outer=c.read(c.E/'launch_requests'/(a.launch_token+'.json'))
 if not time.time()<a.helper_deadline_unix<=outer['cold_wall_deadline_unix']-640+.01:raise RuntimeError('Original outer deadline exceeded')
 pilot.LAUNCH=launch;pilot.legacy.LAUNCH=launch
 bridge_identity=pilot.legacy.stat(os.getpid())
 def raw_progress(status,detail,done=0,**extra):
  c.save(c.STEP,{'status':status,'detail':detail,'done':done,'total':1,'windows_launch_token':launch['token'],'pid':launch['pid'],'creation_time_utc':launch['creation_time_utc'],'native_linux_identity':bridge_identity,'run_directory':str(c.SCORE),'production_panel_acceptance':False,'updated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'started_utc':launch['started_utc'],**extra})
 def progress(*args,**kwargs):return safe_call(raw_progress,*args,error_sink=lambda error:print(json.dumps({'optional_bridge_progress_error':error}),file=sys.stderr,flush=True),**kwargs)
 pilot.legacy.progress=progress;pilot.legacy.STATE=c.STEP;pilot.legacy.OUT=c.OUT
 c.marker_and_exclusivity_gate();c.linux_guard();progress('PREPARING','Binding existing read-only runtime/DB/model hashes for saved stock scoring; no search')
 runtime=pilot.legacy.ready_gate(c.R/'state/checkm2_runtime_ready.json',require_effective=True);runtime['ipc_routing'],runtime['private_ipc_namespace']=pilot.legacy.ipc_runtime_gate(runtime)
 receipt=c.E/'runtime_bindings'/(a.launch_token+'.json');c.save(receipt,{'runtime':runtime,'mount_namespace':os.readlink('/proc/self/ns/mnt')})
 request={"request_schema":"TREE2_PARALLEL_SAVED_STOCK_REQUEST_V001","accession":"GCF_900636715.1","source_manifest":plan['source_manifest'],"protocol_admission":c.row(c.ADMISSION),"saved_phase_authority":plan['saved_phase_authority'],"runtime_binding_receipt":c.row(receipt),"companion_marker":plan['companion_marker'],"scoped_stop":admission['scoped_stop'],"helper_deadline_unix":min(a.helper_deadline_unix,time.time()+900),"output_root":admission['output_root']}
 packet=c.E/'core_requests'/(a.launch_token+'.json');c.save(packet,request);binding=c.E/'core_bindings'/(a.launch_token+'.json');c.save(binding,{'plan':c.row(c.path(a.input_plan)),'runtime':c.row(receipt),'request':c.row(packet),'launch':launch,'admission':c.row(c.ADMISSION)})
 def locator():
  c.save(c.OUT/'runs_by_token'/(a.launch_token+'.json'),{'run_directory':str(c.SCORE),'launch_token':a.launch_token,'input_plan_sha256':a.input_plan_sha256,'protocol_admission_sha256':c.sha(c.ADMISSION),'binding':c.row(binding)})
 try:
  progress('RUNNING','Saved exact stock --genes --resume scoring; annotation/search never replayed')
  import checkm2_saved_stock_recovery_v001 as core
  result=core.main(types.SimpleNamespace(request=str(packet),request_sha256=c.sha(packet),output=str(c.SCORE)),progress=progress)
  c.save(c.SCORE/'invocations.json',[str(p.parent)for p in sorted(c.SCORE.glob('unit_*/command.json'))]);locator();mf=c.manifest(c.SCORE,'outer_manifest.json');c.save(c.OUT/'latest_pending_native.json',{'status':result['status'],'run_directory':str(c.SCORE),'result_path':str(c.SCORE/'result.json'),'manifest_path':str(c.bind(mf)),'manifest_sha256':mf['sha256'],'input_plan_sha256':a.input_plan_sha256,'launch_token':a.launch_token,'protocol_admission_sha256':c.sha(c.ADMISSION),'namespace_execution_receipt_path':str(c.E/'namespace_runs'/(a.launch_token+'.json'))});progress('CORE_PENDING_CLOSURE','Scoring/features complete; actual namespace/native/lease closure remains pending',1)
 except BaseException:
  if c.SCORE.exists():
   c.save(c.SCORE/'invocations.json',[str(p.parent)for p in sorted(c.SCORE.glob('unit_*/command.json'))]);locator()
  progress('FAILED','Saved scoring stopped; original phases preserved; no automatic retry');raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input-plan',required=True);p.add_argument('--input-plan-sha256',required=True);p.add_argument('--launch-token',required=True);p.add_argument('--helper-deadline-unix',required=True,type=float);main(p.parse_args())
