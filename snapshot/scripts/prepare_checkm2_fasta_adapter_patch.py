"""Generate a review-only adaptor; never edit or execute the active pilot files."""
from pathlib import Path
import ast,difflib,hashlib,json,os
import checkm2_fasta_invariance as c
R=c.R
EXPECTED={'checkm2_pilot.py':'9adce984f8451a0e963922abfb56ada3c84b96612187ada3f1788aebef0801e1','checkm2_pilot_image_entry.py':'e91d874563792e7b019d9c95eddad0df2a5cd140623e03dcf817da3667cdcb29','launch_checkm2_pilot.ps1':'3f945771e0d18199f8aa0ffc382704bc11e8b05185b785f8cd56de0bbe7ac29f'}

def replace_once(text,before,after):
 if text.count(before)!=1:raise RuntimeError('Expected exactly one adaptor site: '+before[:100])
 return text.replace(before,after,1)

def controller(text):
 text=replace_once(text,"MAX_RSS=2*1024**3;HEADROOM=1024**3;TIMEOUT=600", "MAX_RSS=2*1024**3;HEADROOM=1024**3;TIMEOUT=600\nSTOP_FILE=R/'state/STOP_CHECKM2_PILOT';LAUNCH_STATE=R/'state/launch_checkm2_pilot.json';OWNER_STATE=R/'state/checkm2_pilot_owner.json';NAMESPACE_ROOT=R/'evidence/checkm2_pilot/namespace_runs'")
 text=text.replace("(R/'state/STOP_CHECKM2_PILOT').exists()","STOP_FILE.exists()")
 text=replace_once(text,"def main(args):\n", "def main(args):\n global OUT,STATE,LAUNCH,STOP_FILE,LAUNCH_STATE,OWNER_STATE,NAMESPACE_ROOT\n control_plan=None\n if args.input_plan:\n  import checkm2_fasta_invariance as formatctl\n  STATE=R/formatctl.ROUTES['progress_path'];STOP_FILE=R/formatctl.ROUTES['stop_path'];LAUNCH_STATE=R/formatctl.ROUTES['native_launch_state_path'];OWNER_STATE=R/formatctl.ROUTES['owner_state_path'];NAMESPACE_ROOT=R/formatctl.ROUTES['namespace_runs_path']\n  if args.resume_from or args.mount_smoke:raise RuntimeError('One format control permits neither resume nor mount-only launch')\n  control_plan=formatctl.load_input_plan(R,args.input_plan,args.input_plan_sha256,True)\n  OUT=inside(control_plan['control_workspace'])\n")
 text=replace_once(text," plan=prepare()\n", " plan=control_plan or prepare()\n")
 text=replace_once(text," global LAUNCH\n","")
 text=replace_once(text,"  p=R/'state/launch_checkm2_pilot.json'", "  p=LAUNCH_STATE")
 text=replace_once(text," lock=open(R/'state/checkm2_pilot.lock','a+b');", " if control_plan and (LAUNCH.get('input_plan_sha256')!=args.input_plan_sha256 or LAUNCH.get('alternate_control_source_sha256')!=sha(formatctl.__file__) or LAUNCH.get('input_plan_handoff_sha256')!=sha(inside(control_plan['owner_handoff_required_path']))):raise RuntimeError('Immutable native control plan/handoff/source binding differs')\n lock=open(R/'state/checkm2_pilot.lock','a+b');")
 text=text.replace("R/'evidence/checkm2_pilot/namespace_runs'/(LAUNCH['token']", "NAMESPACE_ROOT/(LAUNCH['token']")
 text=replace_once(text,"  binding={'input':plan['input'],'runtime':runtime,'options':opts};key=binding_digest(binding)", "  binding={'input':plan['input'],'runtime':runtime,'options':opts}\n  if control_plan:\n   reference=control_plan['baseline']['binding']\n   if opts!=reference['options'] or binding_digest({**reference,'runtime':runtime,'options':opts})!=binding_digest(reference):raise RuntimeError('Format control runtime/IPC/bootstrap/database/options differ from baseline')\n   binding.update(experiment_role=formatctl.ROLE,input_plan_path=str(inside(args.input_plan)),input_plan_sha256=args.input_plan_sha256,original_acquisition_input=control_plan['original_input'])\n  key=binding_digest(binding)")
 text=replace_once(text,"   if completed.get('binding_sha256')==key:\n", "   if completed.get('binding_sha256')==key:\n    if control_plan:formatctl.verify_cached_control(R,control_plan,completed)\n")
 text=replace_once(text,"  run=OUT/'runs'/", "  if control_plan:formatctl.claim_once(R,control_plan)\n  run=OUT/'runs'/")
 text=replace_once(text,"  save(R/'state/checkm2_pilot_owner.json',", "  save(OWNER_STATE,")
 text=replace_once(text,"  try:result=prediction(run,binding,args.resume_from)", "  try:\n   result=prediction(run,binding,args.resume_from)\n   if control_plan:\n    comparison=formatctl.compare_runs(R,control_plan,run)\n    formatctl.save_new(OUT/'comparison.json',comparison)\n    if comparison['status']!='PASS_FORMAT_INVARIANCE_CONTROL_PIPELINE_ONLY':raise RuntimeError('FORMAT_CONTROL_INVARIANCE_FAILED: preserve output and production hold')")
 marker="   obj={'status':status,'ended_utc':utc()"
 text=replace_once(text,marker,"   if control_plan and isinstance(e,formatctl.NotEvaluable):status='CONTROL_NOT_EVALUABLE'\n   elif control_plan and 'FORMAT_CONTROL_INVARIANCE_FAILED' in str(e):status='CONTROL_DIAGNOSTIC_FAILED'\n"+marker)
 text=replace_once(text," finally:fcntl.flock(lock,fcntl.LOCK_UN);lock.close()", "  if control_plan:\n   latest=read(OUT/'latest.json');latest.update(experiment_role=formatctl.ROLE,input_plan_sha256=args.input_plan_sha256,comparison_path=str(OUT/'comparison.json'),comparison_sha256=sha(OUT/'comparison.json'));save(OUT/'latest.json',latest)\n finally:fcntl.flock(lock,fcntl.LOCK_UN);lock.close()")
 text=replace_once(text,"p.add_argument('--resume-from');args=p.parse_args()", "p.add_argument('--resume-from');p.add_argument('--input-plan');p.add_argument('--input-plan-sha256');args=p.parse_args()")
 text=text.replace("('FAILED_RUNTIME_OR_FIT','BLOCKED_RESOURCE','INTERRUPTED_BUDGET','STOPPED')", "('FAILED_RUNTIME_OR_FIT','BLOCKED_RESOURCE','INTERRUPTED_BUDGET','STOPPED','CONTROL_NOT_EVALUABLE','CONTROL_DIAGNOSTIC_FAILED')")
 return text

def entry(text):
 text=text.replace("R / 'state/launch_checkm2_pilot.json'","LAUNCH_STATE")
 text=text.replace("R / 'evidence/checkm2_pilot/namespace_runs'","NAMESPACE_FOLDER")
 text=replace_once(text,"STATE = R / 'state/checkm2_pilot_progress.json'", "STATE = R / 'state/checkm2_pilot_progress.json'\nLAUNCH_STATE = R / 'state/launch_checkm2_pilot.json'\nNAMESPACE_FOLDER = R / 'evidence/checkm2_pilot/namespace_runs'\nLATEST_PATH = R / 'analysis/checkm2_pilot/latest.json'\nSTOP_FILE = R / 'state/STOP_CHECKM2_PILOT'")
 text=text.replace("(R / 'state/STOP_CHECKM2_PILOT').exists()","STOP_FILE.exists()")
 text=replace_once(text,"def main():\n", "def main():\n    global STATE, LAUNCH_STATE, NAMESPACE_FOLDER, LATEST_PATH, STOP_FILE\n")
 marker="    request = read(R / 'state/checkm2_pilot_launch_requests' / (token + '.json'))"
 text=replace_once(text,marker,marker+"\n    alternate = None\n    if request.get('experiment_role') == 'FASTA_WRAP_INVARIANCE':\n        import checkm2_fasta_invariance as formatctl\n        STATE = R / formatctl.ROUTES['progress_path']\n        LAUNCH_STATE = R / formatctl.ROUTES['native_launch_state_path']\n        NAMESPACE_FOLDER = R / formatctl.ROUTES['namespace_runs_path']\n        STOP_FILE = R / formatctl.ROUTES['stop_path']\n        alternate = formatctl.load_input_plan(R, request['input_plan_path'], request['input_plan_sha256'], True)\n        if request.get('resume_from') or request.get('operation') != 'PREDICTION' or request.get('alternate_control_source_sha256') != sha(formatctl.__file__):\n            raise RuntimeError('Alternate control source/operation budget differs')\n        if request.get('input_plan_handoff_sha256') != sha(inside(alternate['owner_handoff_required_path'])):\n            raise RuntimeError('Alternate owner handoff changed after native admission')\n        LATEST_PATH = inside(alternate['control_workspace']) / 'latest.json'\n        CONTEXT['alternate_input_plan_sha256'] = request['input_plan_sha256']")
 text=replace_once(text,"    if request.get('resume_from'):\n", "    if alternate:\n        inner_command += ['--input-plan', str(inside(request['input_plan_path'])), '--input-plan-sha256', request['input_plan_sha256']]\n    if request.get('resume_from'):\n")
 text=replace_once(text,"    latest_path = R / 'analysis/checkm2_pilot/latest.json'", "    if alternate:\n        envelope.update(experiment_role='FASTA_WRAP_INVARIANCE', input_plan_sha256=request['input_plan_sha256'])\n        save(final_receipt, envelope)\n    latest_path = LATEST_PATH")
 text=replace_once(text,"    save(STATE, final)\n", "    if alternate:\n        final.update(experiment_role='FASTA_WRAP_INVARIANCE', input_plan_sha256=request['input_plan_sha256'])\n        if child.returncode == 0 and status == 'NAMESPACE_CLOSED_AND_VERIFIED':\n            final.update(detail='FASTA format invariance result and namespace closure verified; biological accuracy/production remain unvalidated')\n    save(STATE, final)\n")
 return text

def native(text):
 text=replace_once(text,"param([switch]$WaitForReady,", "param([string]$InputPlanPath,[switch]$WaitForReady,")
 marker="if($env:COMPUTERNAME -ne 'WD'){throw 'WD-only launcher'}"
 setup=r'''
$controlPlan=$null;$controlPlanSha=$null;$controlPlanResolved=$null
$routeLaunch='state\launch_checkm2_pilot.json';$routeWaiter='state\checkm2_pilot_waiter.json';$routeExit='state\checkm2_pilot_launcher_exit.json';$routeProgress='state\checkm2_pilot_progress.json';$routeNamespace='evidence\checkm2_pilot\namespace_runs';$routeStop='state\STOP_CHECKM2_PILOT';$routeLog='checkm2_pilot'
if($InputPlanPath){
 if($ResumeFrom -or $MountSmoke){throw 'One format control permits neither resume nor mount-only launch'}
 $routeLaunch='state\launch_checkm2_fasta_invariance.json';$routeWaiter='state\checkm2_fasta_invariance_waiter.json';$routeExit='state\checkm2_fasta_invariance_launcher_exit.json';$routeProgress='state\checkm2_fasta_invariance_progress.json';$routeNamespace='evidence\checkm2_fasta_invariance\namespace_runs';$routeStop='state\STOP_CHECKM2_FASTA_INVARIANCE';$routeLog='checkm2_fasta_invariance'
 $controlPlanResolved=[IO.Path]::GetFullPath($(if([IO.Path]::IsPathRooted($InputPlanPath)){$InputPlanPath}else{Join-Path $projectRoot $InputPlanPath}))
 if(-not $controlPlanResolved.StartsWith($projectRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Control input plan escapes project'}
 $controlPlanSha=(Get-FileHash -LiteralPath $controlPlanResolved -Algorithm SHA256).Hash.ToLowerInvariant()
 $validator='C:\Users\wheel\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
 $validated=& $validator -B (Join-Path $projectRoot 'scripts/checkm2_fasta_invariance.py') validate --input-plan $controlPlanResolved --sha256 $controlPlanSha --require-handoff
 if($LASTEXITCODE -ne 0){throw 'Control plan or explicit baseline-owner handoff is invalid'}
 $controlPlan=($validated -join "`n") | ConvertFrom-Json
}
'''
 text=replace_once(text,marker,marker+setup)
 text=replace_once(text,r"(Join-Path $projectRoot 'state\checkm2_pilot_waiter.json')","(Join-Path $projectRoot $routeWaiter)")
 text=replace_once(text,r"$priorPath=Join-Path $projectRoot 'state\launch_checkm2_pilot.json'","$priorPath=Join-Path $projectRoot $routeLaunch")
 text=replace_once(text,r"('evidence\checkm2_pilot\namespace_runs\'+$prior.token+'.json')",r"($routeNamespace+'\'+$prior.token+'.json')")
 text=replace_once(text,r"(Join-Path $projectRoot 'state\STOP_CHECKM2_PILOT')","(Join-Path $projectRoot $routeStop)")
 marker=" if($ResumeFrom){\n"
 insertion=r''' if($controlPlan){
  $request.experiment_role='FASTA_WRAP_INVARIANCE'
  $request.input_plan_path=$linuxRoot+'/'+$controlPlan.plan_path
  $request.input_plan_sha256=$controlPlanSha
  $request.alternate_control_source_sha256=(Get-FileHash -LiteralPath (Join-Path $projectRoot 'scripts/checkm2_fasta_invariance.py') -Algorithm SHA256).Hash.ToLowerInvariant()
  $request.input_plan_handoff_sha256=(Get-FileHash -LiteralPath (Join-Path $projectRoot $controlPlan.owner_handoff_required_path) -Algorithm SHA256).Hash.ToLowerInvariant()
 }
'''
 text=replace_once(text,marker,insertion+marker)
 text=text.replace(r"('logs\checkm2_pilot_'+$stamp+", r"('logs\'+$routeLog+'_'+$stamp+")
 marker=r" Save-Receipt (Join-Path $projectRoot 'state\launch_checkm2_pilot.json') $launch"
 text=replace_once(text,marker,r''' if($controlPlan){
  $launch.experiment_role=$request.experiment_role;$launch.input_plan_path=$request.input_plan_path;$launch.input_plan_sha256=$request.input_plan_sha256;$launch.alternate_control_source_sha256=$request.alternate_control_source_sha256;$launch.input_plan_handoff_sha256=$request.input_plan_handoff_sha256
 }
 Save-Receipt (Join-Path $projectRoot $routeLaunch) $launch''')
 text=replace_once(text,r"(Join-Path $projectRoot 'state\checkm2_pilot_launcher_exit.json')","(Join-Path $projectRoot $routeExit)")
 text=replace_once(text,r"$progressPath=Join-Path $projectRoot 'state\checkm2_pilot_progress.json'","$progressPath=Join-Path $projectRoot $routeProgress")
 return text

def main():
 folder=R/'work/checkm2_fasta_adapter_preview_v005';folder.mkdir(exist_ok=False)
 patches=[];rows=[]
 for name,transform in [('checkm2_pilot.py',controller),('checkm2_pilot_image_entry.py',entry),('launch_checkm2_pilot.ps1',native)]:
  source=R/'scripts'/name
  if c.sha(source)!=EXPECTED[name]:raise RuntimeError('Active source changed; do not adapt a different basis: '+name)
  old_raw=source.read_bytes().decode('utf-8-sig');old=old_raw.replace('\r\n','\n');new=transform(old)
  if name.endswith('.py'):
   ast.parse(new,filename=name)
   if name=='checkm2_pilot.py':
    before=next(n for n in ast.parse(old).body if isinstance(n,ast.FunctionDef) and n.name=='prediction');after=next(n for n in ast.parse(new).body if isinstance(n,ast.FunctionDef) and n.name=='prediction')
    if ast.dump(before,include_attributes=False)!=ast.dump(after,include_attributes=False):raise RuntimeError('Scientific prediction body changed')
  # This repository explicitly pins raw bytes with '* -text'. Preserve CRLF
  # content lines, including diff contexts; do not rely on Git normalization.
  new_raw=new.replace('\n','\r\n')
  preview=folder/name;preview.write_bytes(new_raw.encode('utf-8'))
  patches.extend(difflib.unified_diff(old_raw.splitlines(keepends=True),new_raw.splitlines(keepends=True),fromfile='a/scripts/'+name,tofile='b/scripts/'+name))
  rows.append({'path':'scripts/'+name,'active_source_sha256':EXPECTED[name],'preview_path':preview.relative_to(R).as_posix(),'preview_sha256':c.sha(preview),'active_file_unchanged':c.sha(source)==EXPECTED[name]})
 patch=R/'patches/checkm2_fasta_invariance_input_plan_v005.patch';patch.parent.mkdir(exist_ok=True)
 if patch.exists():raise FileExistsError('Refusing to replace patch')
 patch.write_bytes(''.join(patches).encode('utf-8'))
 receipt={'status':'REVIEW_ONLY_NOT_APPLIED_NOT_EXECUTED','basis_source_checkpoint':'bacf134e4850a458af82ec16774d38c3dccae7534a27667e8a39e65501f','created_utc':c.utc(),'files':rows,'patch_path':patch.relative_to(R).as_posix(),'patch_sha256':c.sha(patch),'prediction_function_ast_unchanged':True,'real_genome_transformed':False,'scientific_programs_executed':False,'requires_fresh_baseline_owner_handoff':True}
 c.save_new(R/'metadata/checkm2_fasta_adapter_preview_v005.json',receipt);print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
