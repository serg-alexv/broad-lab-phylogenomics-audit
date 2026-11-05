"""New held format-control protocol gates; stdlib-only, no dispatcher on import."""
from pathlib import Path
import json,os
import checkm2_posthoc_v002_validator as v
import checkm2_fasta_invariance as fasta
R=v.R
ROLE='PROTEIN_PIPELINE_DNA_WRAP61_INVARIANCE'
PLAN_SCHEMA='TREE2_PROTEIN_FORMAT_INPUT_PLAN_V002'
ADMISSION=R/'state/checkm2_protein_format_protocol_ready_v002.json'
ROOT_ACCEPTANCE_SHA='0e80c5335a178d04a78864e650318c937af6030c03c2405b0ee272a4b2b27ae3'
LIMITS={'cpu_affinity_max':2,'sum_group_RSS_bytes':2147483648,'linux_available_minimum_bytes':1073741824,'disk_reserve_bytes':42949672960,'annotation_unit_seconds':600,'protein_quality_plus_feature_validation_unit_seconds':600}
OUT=R/'analysis/checkm2_protein_format_invariance_v002'
STATE=R/'state/checkm2_protein_format_invariance_v002_progress.json'
LAUNCH=R/'state/launch_checkm2_protein_format_invariance_v002.json'
E=R/'evidence/checkm2_protein_format_invariance_v002'
STOP=R/'state/STOP_CHECKM2_PROTEIN_FORMAT_V002'

def path(value):return fasta.inside(R,value)
def bind(row):
 p=path(row['path'])
 if v.sha(p)!=row['sha256'] or ('bytes' in row and p.stat().st_size!=row['bytes']):raise RuntimeError('Bound control artifact/source changed:'+str(p))
 return p
def stop():
 if (R/'state/STOP').exists() or STOP.exists() or (R/'state/STOP_CHECKM2_PILOT').exists():raise InterruptedError('Project or quality/control STOP requested')
def verify_manifest(folder,manifest):
 for row in manifest['files']:
  p=path(folder/row['path'])
  if not p.is_relative_to(folder) or v.sha(p)!=row['sha256'] or p.stat().st_size!=row['bytes']:raise RuntimeError('Immutable baseline/control manifest mismatch')
def baseline_gate(plan):
 b=plan['baseline'];objects={name:v.read(bind(row)) for name,row in b.items()}
 if b['root_acceptance']['sha256']!=ROOT_ACCEPTANCE_SHA:raise RuntimeError('Exact root method-baseline acceptance absent')
 a=objects['root_acceptance'];n=objects['native_closure'];x=objects['execution'];z=objects['validation']
 if a.get('status')!='ACCEPTED_AS_METHOD_BASELINE_FOR_ONE_FORMAT_CONTROL_PREPARATION' or a.get('format_control_execution_authorized') is not False:raise RuntimeError('Baseline authority scope differs')
 for key,name in [('validation_sha256','validation'),('execution_sha256','execution'),('full_native_closure_sha256','native_closure'),('closed_manifest_sha256','closed_manifest'),('latest_pointer_sha256','latest')]:
  if a.get(key)!=b[name]['sha256']:raise RuntimeError('Root method-baseline cross-binding differs:'+name)
 if x.get('status')!='PRESERVED_04R1_VALIDATION_V002_PASS_CLOSED' or x.get('wsl_child_exit_code')!=0 or not x.get('inside',{}).get('owned_group_empty'):raise RuntimeError('Closed recovered baseline execution required')
 if n.get('status')!='POSTHOC_V002_FULL_NATIVE_NAMESPACE_IMAGE_AND_COMMON_LEASE_CLOSURE_PROVEN' or n.get('native_controller_exit_code_observed')!=0 or n.get('native_WSL_child_exit_code')!=0 or n.get('common_native_byte_leases_reacquired_released') is not True or n.get('Linux',{}).get('compute_lease_reacquired_released') is not True:raise RuntimeError('Actual baseline native exits/lease closure absent')
 if n['execution_sha256']!=b['execution']['sha256'] or n['validation_sha256']!=b['validation']['sha256']:raise RuntimeError('Baseline closure references different output')
 if z.get('status')!='PRESERVED_04R1_FEATURES_AND_MEMBERSHIP_V002_PASS_PENDING_CLOSURE' or z.get('schema_v002_sha256')!='90e482515c6924386a888aa14a036f7659acf9ad0c49814cb08a3a7e1f76f5ee' or z.get('membership_mismatches')!=0:raise RuntimeError('Corrected full baseline feature validation absent')
 verify_manifest(bind(b['closed_manifest']).parent,objects['closed_manifest'])
 v.preflight(v.read(bind(plan['posthoc_admission'])))
 return objects
def plan_gate(plan_path,expected_sha,require_admission=True):
 stop();p=path(plan_path)
 if v.sha(p)!=expected_sha:raise RuntimeError('Immutable input-plan SHA differs')
 plan=v.read(p)
 if plan.get('schema')!=PLAN_SCHEMA or plan.get('role')!=ROLE or plan.get('transform')!={'width':61,'line_ending':'LF','headers_record_order_sequence_case_exact':True,'no_op_substitution_or_retry':False}:raise RuntimeError('Only declared DNA-wrap61 control is allowed')
 if plan.get('limits')!=LIMITS or plan.get('stock_resume_force_retry') is not False:raise RuntimeError('Control resources/retry scope differs')
 baseline=baseline_gate(plan)
 manifest=v.read(bind(plan['source_manifest']))
 for row in manifest['sources']:bind(row)
 if not require_admission:return plan,baseline,None
 if not ADMISSION.exists():raise RuntimeError('HELD_ROOT_CONTROL_PROTOCOL_ADMISSION_ABSENT')
 admitted=v.read(ADMISSION)
 if admitted.get('schema')!='TREE2_PROTEIN_FORMAT_CONTROL_ADMISSION_V002' or admitted.get('status')!='ADMITTED_ONE_FORMAT_CONTROL' or admitted.get('role')!=ROLE or admitted.get('max_attempts')!=1 or admitted.get('format_control_execution_authorized') is not True:raise RuntimeError('Control launch is not admitted')
 if admitted.get('input_plan_sha256')!=expected_sha or admitted.get('source_manifest_sha256')!=plan['source_manifest']['sha256'] or admitted.get('root_baseline_acceptance_sha256')!=ROOT_ACCEPTANCE_SHA or admitted.get('limits')!=LIMITS:raise RuntimeError('Root control admission binding differs')
 if admitted.get('monitor_standard_stage04_ready') is not True or admitted.get('source_math_GO') is not True or admitted.get('resource_lifecycle_GO') is not True:raise RuntimeError('Control source/monitor reviews pending')
 return plan,baseline,admitted
