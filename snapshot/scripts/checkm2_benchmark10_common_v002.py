"""HELD benchmark gates and checkpoint primitives; no dispatcher on import."""
from pathlib import Path
import hashlib,json,os,uuid
R=Path(__file__).resolve().parents[1]
ROLE='BENCHMARK10_PROTEIN_METHOD_QC_ONLY'
STRATEGY_SHA='c0c3a2c65e3ba3a7d12d9d0ba2eeb9d600d3df9cf06343dade9e157bca90acdc'
LIMITS={'cpu_affinity_max':2,'stock_threads':1,'sum_group_RSS_bytes':2147483648,'linux_available_minimum_bytes':1073741824,'disk_reserve_bytes':42949672960,'annotation_unit_seconds':600,'max_annotation_units':10,'max_total_annotation_compute_seconds':6000,'protein_batch_plus_validation_seconds':3600}
PHASES=('BOUNDARY_AFTER_FIRST_ANNOTATION','CONTINUE','VALIDATE_COMMITTED_BATCH')
E=R/'evidence/checkm2_benchmark10_protein_v002'
OUT=R/'analysis/checkm2_benchmark10_protein_v002'
STATE=R/'state/checkm2_benchmark10_protein_v002_progress.json'
LAUNCH=R/'state/launch_checkm2_benchmark10_protein_v002.json'
STOP=R/'state/STOP_CHECKM2_BENCHMARK10_PROTEIN_V002'
ADMISSION=R/'state/checkm2_benchmark10_protein_protocol_ready_v002.json'
def path(value):
 p=Path(value)
 text=str(p).replace('\\','/')
 linux='/mnt/c/Users/wheel/Documents/Codex/2026-10-26/referenced-chatgpt-conversation-this-is-an/outputs/TREE2_WD_20261026/'
 if os.name=='nt' and text.startswith(linux):p=R/text[len(linux):]
 p=(p if p.is_absolute() else R/p).resolve()
 if not p.is_relative_to(R):raise RuntimeError('Benchmark path leaves project')
 return p
def sha(value):
 with path(value).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(value):return json.loads(path(value).read_text(encoding='utf-8-sig'))
def save(value,data):
 p=path(value);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.'+uuid.uuid4().hex+'.partial')
 with tmp.open('x',newline='\n') as f:json.dump(data,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,p)
def row(value):
 p=path(value);return {'path':p.relative_to(R).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size}
def bind(value):
 p=path(value['path'])
 if sha(p)!=value['sha256'] or ('bytes' in value and p.stat().st_size!=value['bytes']):raise RuntimeError('Bound benchmark artifact/source changed:'+str(p))
 return p
def stop():
 if any(p.exists() for p in (R/'state/STOP',STOP,R/'state/STOP_CHECKM2_PILOT')):raise InterruptedError('Benchmark/project/biological STOP; never cleared automatically')
def verify_manifest(folder,manifest):
 folder=path(folder)
 for item in manifest['files']:
  p=path(folder/item['path'])
  if not p.is_relative_to(folder) or sha(p)!=item['sha256'] or p.stat().st_size!=item['bytes']:raise RuntimeError('Committed benchmark artifact differs')
def manifest(folder,name='manifest.json'):
 folder=path(folder);items=[{'path':p.relative_to(folder).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(folder.rglob('*')) if p.is_file() and p.name not in (name,'commit.json')]
 save(folder/name,{'files':items,'closed_unit_files_only':True});return row(folder/name)
def unit_closed(execution):
 return execution.get('status')=='UNIT_EXIT0_GROUP_CLOSED' and type(execution.get('exit_code')) is int and execution['exit_code']==0 and execution.get('owned_group_empty') is True and execution.get('remaining_owned_processes')==[]
def group_receipts_closed(run):
 index=read(path(run)/'invocations.json')
 return bool(index) and all((path(x)/'command.json').exists() and (path(x)/'execution.json').exists() and read(path(x)/'execution.json').get('owned_group_empty') is True for x in index)
def pending_is_current(pending,token,plan_sha,protocol_sha,namespace):
 return pending.get('launch_token')==token and pending.get('input_plan_sha256')==plan_sha and pending.get('protocol_admission_sha256')==protocol_sha and path(pending.get('namespace_execution_receipt_path',''))==path(namespace)
def verify_budget_set(folder,bindings):
 folder=path(folder);live={p.resolve() for p in folder.glob('validation_*_budget.json')}|{p.resolve() for p in folder.glob('validation_*/execution.json')};expected={bind(x).resolve() for x in bindings}
 if live!=expected:raise RuntimeError('Prior validation budget/terminal live set differs from actual closed-phase authority; no debit reset')
def resume_proof(admission,session):
 proof=read(bind(admission['resume_authority']))
 if proof.get('status')!='BENCHMARK_PHASE_NATIVE_GROUP_NAMESPACE_IMAGE_LEASE_CLOSED' or type(proof.get('native_exit_code_observed')) is not int or proof.get('session_identity_sha256')!=session:raise RuntimeError('Actual closed prior benchmark phase required before continuation')
 if type(proof.get('wsl_exit_code_observed')) is not int:raise RuntimeError('Actual observed prior WSL exit required; UNKNOWN cannot resume')
 if admission['phase']=='CONTINUE' and (proof['native_exit_code_observed']!=0 or proof['wsl_exit_code_observed']!=0):raise RuntimeError('Boundary continuation requires actual prior native and WSL exits zero')
 if admission['phase']=='VALIDATE_COMMITTED_BATCH' and (proof.get('committed_prediction_exit0_group_closed') is not True or not isinstance(proof.get('prediction_commit_sha256'),str)):raise RuntimeError('File-only recovery needs proved committed prediction success, even if later validation failed')
 if any(proof.get(k) is not True for k in ('owned_unit_groups_empty','ordinary_runtime_closed','image_unchanged','common_leases_reacquired_released','original_artifacts_unchanged')):raise RuntimeError('Prior benchmark phase closure/leases incomplete')
 if not isinstance(proof.get('closed_native_launch_tokens'),list) or not proof['closed_native_launch_tokens']:raise RuntimeError('Exact closed prior launch tokens required before committed reuse')
 if not isinstance(proof.get('annotation_commit_sha256s'),dict) or not proof['annotation_commit_sha256s']:raise RuntimeError('Externally closed annotation commit hashes required')
 if not isinstance(proof.get('validation_budget_bindings'),list):raise RuntimeError('Explicit closed validation budget/terminal binding set required, including empty set at first boundary')
 snapshot=bind(proof['closed_snapshot_manifest']);verify_manifest(snapshot.parent,read(snapshot))
 return proof
def plan_gate(plan_path,expected_sha,require_admission=True):
 stop();p=path(plan_path)
 if sha(p)!=expected_sha:raise RuntimeError('Benchmark immutable plan SHA differs')
 plan=read(p)
 if plan.get('schema')!='TREE2_BENCHMARK10_PROTEIN_INPUT_PLAN_V002' or plan.get('role')!=ROLE or plan.get('limits')!=LIMITS:raise RuntimeError('Wrong benchmark scope/resources')
 strategy=read(bind(plan['strategy']))
 if plan['strategy']['sha256']!=STRATEGY_SHA or len(strategy['inputs'])!=10 or len({x['accession'] for x in strategy['inputs']})!=10:raise RuntimeError('Exact held ten-genome cohort required')
 original=read(bind(strategy['original_immutable_plan']))
 if original['inputs']!=strategy['inputs']:raise RuntimeError('Original ten-input cohort changed')
 recipe=read(bind(plan['recipe']))
 if recipe.get('inputs')!=strategy['inputs'] or recipe.get('limits')!=LIMITS:raise RuntimeError('Pinned recipe cohort/limits differ from strategy')
 for item in read(bind(plan['source_manifest']))['sources']:bind(item)
 if not require_admission:return plan,strategy,None
 if not ADMISSION.exists():raise RuntimeError('HELD_BENCHMARK_ADMISSION_ABSENT')
 a=read(ADMISSION)
 if a.get('schema')!='TREE2_BENCHMARK10_PROTEIN_ADMISSION_V002' or a.get('status')!='ADMITTED_ONE_BENCHMARK10_BATCH' or a.get('role')!=ROLE or a.get('benchmark_execution_authorized') is not True or a.get('max_batch_prediction_attempts')!=1 or a.get('phase') not in PHASES:raise RuntimeError('No explicit benchmark phase authority')
 if a.get('input_plan_sha256')!=expected_sha or a.get('source_manifest_sha256')!=plan['source_manifest']['sha256'] or a.get('recipe_sha256')!=plan['recipe']['sha256'] or a.get('limits')!=LIMITS:raise RuntimeError('Benchmark admission binding/resources differ')
 if any(a.get(k) is not True for k in ('format_control_gate_passed','monitor_standard_stage04_ready','source_math_GO','resource_lifecycle_GO')):raise RuntimeError('Benchmark control/source/monitor gates held')
 if plan.get('format_control_comparison') is None or plan.get('format_control_root_acceptance') is None:raise RuntimeError('HELD_FORMAT_CONTROL_PASS_AND_ROOT_ACCEPTANCE_UNBOUND')
 comparison=read(bind(plan['format_control_comparison']));authority=read(bind(plan['format_control_root_acceptance']))
 accepted_comparisons={x['sha256'] for x in authority.get('closed_chain',[]) if x['path'].endswith('/comparison.json')}
 if comparison.get('status')!='FORMAT_CONTROL_V002_PASS_CLOSED' or plan['format_control_comparison']['sha256'] not in accepted_comparisons or authority.get('status')!='ACCEPTED_FORMAT_CONTROL_FOR_TEN_GENOME_BENCHMARK_PREPARATION' or authority.get('benchmark_execution_authorized') is not False or authority.get('production_or_taxonomy_or_panel_acceptance') is not False or a.get('format_control_root_acceptance')!=plan['format_control_root_acceptance']:raise RuntimeError('Actual format-control PASS/root preparation-only authority absent')
 for item in authority['closed_chain']:bind(item)
 if a['phase']!='BOUNDARY_AFTER_FIRST_ANNOTATION':resume_proof(a,plan['session_identity_sha256'])
 return plan,strategy,a
