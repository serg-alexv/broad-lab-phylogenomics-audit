"""Prepare/compare one format-only CheckM2 control; no predictor is launched here."""
from pathlib import Path
from collections import Counter
from decimal import Decimal,InvalidOperation
import argparse,base64,csv,datetime as dt,hashlib,json,math,os,re,shutil,uuid

R=Path(__file__).resolve().parents[1]
ROLE='FASTA_WRAP_INVARIANCE'
SCHEMA='TREE2_CHECKM2_ALTERNATE_INPUT_PLAN_V1'
SPEC='metadata/checkm2_end_to_end_control_spec.json'
class NotEvaluable(RuntimeError):pass
ROUTES={'progress_path':'state/checkm2_fasta_invariance_progress.json','native_launch_state_path':'state/launch_checkm2_fasta_invariance.json','native_waiter_state_path':'state/checkm2_fasta_invariance_waiter.json','native_exit_state_path':'state/checkm2_fasta_invariance_launcher_exit.json','owner_state_path':'state/checkm2_fasta_invariance_owner.json','namespace_runs_path':'evidence/checkm2_fasta_invariance/namespace_runs','stop_path':'state/STOP_CHECKM2_FASTA_INVARIANCE'}

def utc():return dt.datetime.now(dt.timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def inside(root,value):
 root=Path(root).resolve();s=str(value)
 if os.name=='nt' and re.match(r'^/mnt/[a-z]/',s):s=s[5].upper()+':/'+s[7:]
 elif os.name!='nt' and re.match(r'^[A-Za-z]:[\\/]',s):s='/mnt/'+s[0].lower()+'/'+s[3:].replace('\\','/')
 p=Path(s);p=(p if p.is_absolute() else root/p).resolve()
 if not p.is_relative_to(root):raise RuntimeError('Control path escapes isolated project')
 return p
def relative(root,p):return inside(root,p).relative_to(Path(root).resolve()).as_posix()
def save_new(path,value):
 path=Path(path)
 if path.exists():raise FileExistsError('Refusing to overwrite control artifact:'+str(path))
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.pending')
 with tmp.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 if path.exists():raise FileExistsError('Control artifact appeared while staging')
 os.replace(tmp,path)
def fasta_records(path,alphabet=None):
 header=None;parts=[]
 with Path(path).open('rb') as f:
  for line in f:
   line=line.rstrip(b'\r\n')
   if not line:continue
   if line.startswith(b'>'):
    if header is not None:
     sequence=b''.join(parts)
     if not sequence:raise NotEvaluable('Empty FASTA record')
     yield header,sequence
    if len(line)==1:raise NotEvaluable('Empty FASTA header')
    header=line;parts=[]
   else:
    if header is None:raise NotEvaluable('FASTA sequence precedes header')
    if any(c in line for c in b' \t\v\f') or any(c>127 for c in line):raise NotEvaluable('Sequence whitespace/non-ASCII requires review; no normalization')
    if alphabet is not None and not set(line).issubset(alphabet):raise NotEvaluable('Sequence alphabet requires review')
    parts.append(line)
 if header is None:raise NotEvaluable('No FASTA records')
 sequence=b''.join(parts)
 if not sequence:raise NotEvaluable('Empty final FASTA record')
 yield header,sequence
def semantic_fasta(path):
 rows=[];total=0;h=hashlib.sha256()
 for header,sequence in fasta_records(path):
  for value in (header,sequence):h.update(len(value).to_bytes(8,'big'));h.update(value)
  rows.append({'header_b64':base64.b64encode(header).decode(),'header_sha256':hashlib.sha256(header).hexdigest(),'sequence_bytes':len(sequence),'sequence_sha256':hashlib.sha256(sequence).hexdigest()});total+=len(sequence)
 return {'ordered_semantic_sha256':h.hexdigest(),'records':rows,'record_count':len(rows),'sequence_bytes':total}
def rewrap_new(source,destination,width=61):
 source=Path(source);destination=Path(destination)
 if width!=61:raise RuntimeError('Only the predeclared width61 control is allowed')
 if destination.exists():raise FileExistsError('Derived FASTA already exists')
 before=semantic_fasta(source);source_sha=sha(source);tmp=destination.with_suffix(destination.suffix+'.pending')
 with tmp.open('xb') as f:
  for header,sequence in fasta_records(source):
   f.write(header+b'\n')
   for start in range(0,len(sequence),61):f.write(sequence[start:start+61]+b'\n')
  f.flush();os.fsync(f.fileno())
 after=semantic_fasta(tmp)
 if before!=after or sha(source)!=source_sha:raise RuntimeError('Rewrap changed semantic input or original source')
 if sha(tmp)==source_sha:raise NotEvaluable('Rewrap is a no-op; no substitute perturbation/retry allowed')
 os.replace(tmp,destination)
 return {'original_sha256':source_sha,'derived_sha256':sha(destination),'derived_bytes':destination.stat().st_size,'original_semantics':before,'derived_semantics':after,'width':61,'source_unchanged':True}
def check_manifest(root,manifest):
 manifest=inside(root,manifest);base=manifest.parent
 for row in read(manifest)['files']:
  p=(base/row['path']).resolve()
  if not p.is_relative_to(base) or not p.is_file() or p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('Baseline/run artifact hash differs')
 return {'path':relative(root,manifest),'sha256':sha(manifest)}
def baseline_binding(root):
 root=Path(root).resolve();latest=inside(root,'analysis/checkm2_pilot/latest.json');last=inside(root,'analysis/checkm2_pilot/last_exit.json')
 x=read(latest);result_path=inside(root,x['result_path']);result=read(result_path)
 if read(last).get('status')!='COMPLETE_PILOT_ONLY' or result.get('status')!='RESOURCE_PILOT_COMPLETED_NOT_PRODUCTION_ACCEPTANCE':raise RuntimeError('Valid completed baseline resource pilot required')
 manifest=check_manifest(root,x['manifest_path']);run=result_path.parent
 if not result['execution'].get('owned_group_empty') or result['execution'].get('exit_code')!=0:raise RuntimeError('Baseline scientific group closure missing')
 envpath=inside(root,x['namespace_execution_receipt_path'])
 if sha(envpath)!=x.get('namespace_execution_receipt_sha256'):raise RuntimeError('Baseline namespace envelope hash missing/differs')
 envelope=read(envpath)
 if envelope.get('status')!='NAMESPACE_CLOSED_AND_VERIFIED' or envelope.get('helper_exit_code')!=0 or envelope.get('image_unchanged') is not True:raise RuntimeError('Baseline namespace/image closure missing')
 binding_path=run/'binding.json';binding=read(binding_path)
 if binding.get('input',{}).get('accession')!=result['accession']:raise RuntimeError('Baseline accession binding differs')
 return {'latest_path':relative(root,latest),'latest_sha256':sha(latest),'last_exit_path':relative(root,last),'last_exit_sha256':sha(last),'result_path':relative(root,result_path),'result_sha256':sha(result_path),'manifest':manifest,'binding_path':relative(root,binding_path),'binding_sha256':sha(binding_path),'run_directory':relative(root,run),'namespace_receipt_path':relative(root,envpath),'namespace_receipt_sha256':sha(envpath),'native_launch':envelope['native_windows_launch'],'binding':binding}
def check_handoff(root,plan,handoff):
 h=read(inside(root,handoff));b=plan['baseline']
 if h.get('status')!='BASELINE_CLOSED_CONTROL_HANDOFF' or h.get('baseline_launch_token')!=b['native_launch']['token'] or h.get('baseline_namespace_sha256')!=b['namespace_receipt_sha256'] or h.get('baseline_latest_sha256')!=b['latest_sha256']:raise RuntimeError('Explicit baseline-owner handoff differs')
 if h.get('native_baseline_closed') is not True or h.get('native_launcher_lock_released') is not True or h.get('compute_lock_released') is not True:raise RuntimeError('Baseline owner/OS/compute release not proved')
 if h.get('input_plan_sha256')!=sha(inside(root,plan['plan_path'])):raise RuntimeError('Owner handoff plan hash missing/differs')
 return h
def prepare_plan(root=R,version=1):
 root=Path(root).resolve();spec=read(inside(root,SPEC));base=baseline_binding(root);binding=base['binding'];source=inside(root,spec['reference']['fasta_path'])
 if version!=1:raise RuntimeError('Only one versioned control permitted; no automatic escalation')
 if binding['input']['accession']!=spec['reference']['accession'] or binding['input']['fasta_sha256']!=spec['reference']['fasta_sha256'] or sha(source)!=spec['reference']['fasta_sha256']:raise RuntimeError('Baseline/source/spec identity differs')
 b_runtime=binding['runtime'];required=spec['runtime']
 if b_runtime['effective_runtime']['manifest_sha256']!=required['effective_runtime_manifest_sha256'] or b_runtime['ready']['runtime_image']['sha256']!=required['image_sha256'] or b_runtime['database_path']!=required['database_path']:raise RuntimeError('Baseline effective runtime/DB differs from accepted control spec')
 workspace=inside(root,'analysis/checkm2_fasta_invariance/v001-'+base['binding_sha256'][:12]);workspace.mkdir(parents=True,exist_ok=False)
 inputdir=workspace/'derived_input';inputdir.mkdir();derived=inputdir/(binding['input']['accession']+'.fna');rewrap=rewrap_new(source,derived)
 save_new(workspace/'semantic_identity.json',rewrap);snapshot=workspace/'baseline_snapshot';snapshot.mkdir()
 copies=[]
 for name in ['latest_path','last_exit_path','result_path','binding_path','namespace_receipt_path']:
  p=inside(root,base[name]);q=snapshot/(name+'.json');shutil.copy2(p,q);copies.append({'original':base[name],'preserved':relative(root,q),'sha256':sha(q)})
 original_input=dict(binding['input']);item={**original_input,'fasta_path':str(derived),'fasta_sha256':rewrap['derived_sha256'],'fasta_bytes':rewrap['derived_bytes'],'experiment_role':ROLE,'original_acquisition_fasta_path':str(source),'original_acquisition_fasta_sha256':rewrap['original_sha256']}
 plan_path=workspace/'input_plan.json';plan={'schema':SCHEMA,'status':'PREPARED_NOT_EXECUTED_OWNER_HANDOFF_REQUIRED','experiment_role':ROLE,'version':1,'created_utc':utc(),'plan_path':relative(root,plan_path),'control_workspace':relative(root,workspace),**ROUTES,'owner_handoff_required_path':'state/checkm2_fasta_control_handoff.json','spec_path':SPEC,'spec_sha256':sha(inside(root,SPEC)),'baseline':base,'baseline_snapshots':copies,'input':item,'original_input':original_input,'semantic_identity_path':relative(root,workspace/'semantic_identity.json'),'semantic_identity_sha256':sha(workspace/'semantic_identity.json'),'options':binding['options'],'runtime_binding':required,'max_new_prediction_runs':1,'resume_allowed':False,'production_acceptance':False,'preparation_source_sha256':sha(__file__)}
 save_new(plan_path,plan);save_new(workspace/'preparation_receipt.json',{'status':'PREPARED_NOT_EXECUTED','plan_path':relative(root,plan_path),'plan_sha256':sha(plan_path),'derived_fasta_sha256':sha(derived),'original_unchanged':sha(source)==rewrap['original_sha256'],'owner_handoff_required':True,'production_acceptance':False})
 return plan
def load_input_plan(root,path,expected_sha,require_handoff=False):
 root=Path(root).resolve();p=inside(root,path)
 if sha(p)!=str(expected_sha).lower():raise RuntimeError('Immutable alternate input plan hash differs')
 plan=read(p)
 if plan.get('schema')!=SCHEMA or plan.get('experiment_role')!=ROLE or plan.get('max_new_prediction_runs')!=1 or plan.get('resume_allowed') is not False:raise RuntimeError('Alternate plan role/budget differs')
 if any(plan.get(k)!=v for k,v in ROUTES.items()) or plan.get('preparation_source_sha256')!=sha(__file__):raise RuntimeError('Control routing/preparation source differs')
 if relative(root,p)!=plan['plan_path'] or not plan['control_workspace'].startswith('analysis/checkm2_fasta_invariance/v001-'):raise RuntimeError('Alternate control workspace differs')
 current=baseline_binding(root)
 for key in ('latest_sha256','result_sha256','binding_sha256','namespace_receipt_sha256'):
  if current[key]!=plan['baseline'][key]:raise RuntimeError('Admitted baseline changed')
 if sha(inside(root,plan['spec_path']))!=plan['spec_sha256'] or sha(inside(root,plan['semantic_identity_path']))!=plan['semantic_identity_sha256']:raise RuntimeError('Control specification/semantic receipt changed')
 source=inside(root,plan['original_input']['fasta_path']);derived=inside(root,plan['input']['fasta_path'])
 if sha(source)!=plan['original_input']['fasta_sha256'] or sha(derived)!=plan['input']['fasta_sha256'] or source==derived or semantic_fasta(source)!=semantic_fasta(derived):raise RuntimeError('Derived/original FASTA binding differs')
 if require_handoff:check_handoff(root,plan,plan['owner_handoff_required_path'])
 return plan
def protein_digest(folder):
 files=sorted(Path(folder).glob('*'));rows=[]
 for p in files:
  if not p.is_file():continue
  for header,sequence in fasta_records(p):rows.append((header[1:].split(None,1)[0].decode('ascii'),sequence))
 if not rows or len({x[0] for x in rows})!=len(rows):raise NotEvaluable('Missing/duplicate protein identifiers')
 h=hashlib.sha256()
 for identifier,sequence in rows:
  for v in (identifier.encode(),sequence):h.update(len(v).to_bytes(8,'big'));h.update(v)
 return {'records':len(rows),'ordered_sha256':h.hexdigest()}
def diamond_digest(folder):
 paths=sorted(Path(folder).glob('DIAMOND_RESULTS*'));counts=Counter()
 for p in paths:
  with p.open('r',encoding='utf-8',newline='') as f:
   for line in f:
    parts=line.rstrip('\r\n').split('\t')
    try:valid=len(parts)==12 and all(math.isfinite(float(x)) for x in parts[2:])
    except ValueError:valid=False
    if not valid:raise NotEvaluable('Malformed/nonfinite DIAMOND row')
    counts[tuple(parts)]+=1
 if not counts:raise NotEvaluable('No preserved DIAMOND hits')
 h=hashlib.sha256()
 for row,count in sorted(counts.items()):h.update(json.dumps([row,count],ensure_ascii=False,separators=(',',':')).encode())
 return {'rows':sum(counts.values()),'unique_rows':len(counts),'multiset_sha256':h.hexdigest()}
def report_row(path):
 with Path(path).open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f,delimiter='\t'))
 if len(rows)!=1:raise NotEvaluable('Exactly one report row required')
 return rows[0]
def compare_rows(reference,control):
 differences=[];deltas={}
 for key in ('Name','Completeness_Model_Used','Translation_Table_Used','Additional_Notes'):
  if key not in reference or key not in control:raise NotEvaluable('Missing required quality report column:'+key)
  if reference[key]!=control[key]:differences.append(key)
 for key in ('Completeness','Contamination'):
  try:a,b=Decimal(reference[key]),Decimal(control[key])
  except (KeyError,InvalidOperation):raise NotEvaluable('Malformed score:'+key)
  if not a.is_finite() or not b.is_finite() or a<0 or b<0 or (key=='Completeness' and (a>100 or b>100)):raise NotEvaluable('Nonfinite/out-of-domain score')
  delta=abs(a-b);deltas[key]=str(delta)
  if delta>Decimal('0.01'):differences.append(key)
 for key in ('Genome_Size','Total_Contigs','Total_Coding_Sequences','Contig_N50','Max_Contig_Length'):
  if key not in reference or key not in control:raise NotEvaluable('Required integer metric missing:'+key)
  try:a,b=Decimal(reference[key]),Decimal(control[key])
  except InvalidOperation:raise NotEvaluable('Malformed integer metric:'+key)
  if not a.is_finite() or not b.is_finite() or a<0 or b<0 or a!=a.to_integral_value() or b!=b.to_integral_value():raise NotEvaluable('Invalid integer metric:'+key)
  if a!=b:differences.append(key)
 return {'equal_within_declared_tolerance':not differences,'differences':differences,'score_differences_percentage_points':deltas}
def compare_runs(root,plan,control_run):
 root=Path(root).resolve();control_run=inside(root,control_run);reference=inside(root,plan['baseline']['run_directory'])
 if control_run==reference or not control_run.is_relative_to(inside(root,plan['control_workspace'])/'runs'):raise RuntimeError('Control run must be separate from the baseline and inside its new workspace')
 bound=read(control_run/'binding.json')
 if bound.get('experiment_role')!=ROLE or bound.get('input_plan_sha256')!=sha(inside(root,plan['plan_path'])) or bound.get('input')!=plan['input'] or bound.get('original_acquisition_input')!=plan['original_input'] or bound.get('options')!=plan['options']:raise RuntimeError('Control run input/options/role binding differs')
 def stable_runtime(value):
  value=json.loads(json.dumps(value));value.pop('private_readonly_runtime',None);value.pop('private_ipc_namespace',None);return value
 if stable_runtime(bound['runtime'])!=stable_runtime(plan['baseline']['binding']['runtime']):raise RuntimeError('Control/base runtime bindings differ')
 check_manifest(root,plan['baseline']['manifest']['path']);check_manifest(root,control_run/'manifest.json')
 execution=read(control_run/'execution_receipt.json')
 if not execution.get('owned_group_empty') or execution.get('exit_code')!=0:raise RuntimeError('Control group not successfully closed')
 p0,p1=protein_digest(reference/'output/protein_files'),protein_digest(control_run/'output/protein_files');d0,d1=diamond_digest(reference/'output/diamond_output'),diamond_digest(control_run/'output/diamond_output');table=compare_rows(report_row(reference/'output/quality_report.tsv'),report_row(control_run/'output/quality_report.tsv'))
 f0,f1=sorted((reference/'output').glob('feature_vectors_*.pkl')),sorted((control_run/'output').glob('feature_vectors_*.pkl'))
 feature='NOT_COLLECTED'
 if f0 or f1:
  if len(f0)!=len(f1) or not f0:raise NotEvaluable('Feature dump collection differs')
  if [sha(p) for p in f0]!=[sha(p) for p in f1]:raise NotEvaluable('Feature dumps differ; semantic comparison under effective runtime required before any pass')
  feature='IDENTICAL_SERIALIZED_FEATURE_ARTIFACTS'
 passed=p0==p1 and d0==d1 and table['equal_within_declared_tolerance']
 return {'status':'PASS_FORMAT_INVARIANCE_CONTROL_PIPELINE_ONLY' if passed else 'FAIL_FORMAT_INVARIANCE_DIAGNOSTIC_KEEP_PRODUCTION_HOLD','compared_utc':utc(),'plan_sha256':sha(inside(root,plan['plan_path'])),'baseline_run':relative(root,reference),'control_run':relative(root,control_run),'protein_reference':p0,'protein_control':p1,'diamond_reference':d0,'diamond_control':d1,'quality_table':table,'feature_vectors':feature,'production_acceptance':False,'biological_accuracy_truth':False,'ncbi_source_scores_used_as_truth':False}
def claim_once(root,plan):
 path=inside(root,plan['control_workspace'])/'prediction_once_claim.json';save_new(path,{'created_utc':utc(),'experiment_role':ROLE,'plan_sha256':sha(inside(root,plan['plan_path'])),'one_attempt_no_retry':True});return path
def verify_cached_control(root,plan,completed):
 p=inside(root,completed.get('comparison_path',''))
 if not p.is_file() or sha(p)!=completed.get('comparison_sha256'):raise RuntimeError('Cached control comparison artifact missing/changed')
 comparison=read(p)
 if comparison.get('status')!='PASS_FORMAT_INVARIANCE_CONTROL_PIPELINE_ONLY' or comparison.get('plan_sha256')!=sha(inside(root,plan['plan_path'])) or comparison.get('production_acceptance') is not False:raise RuntimeError('Cached control diagnostic/plan binding not accepted')
 return comparison
def main():
 ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='op',required=True);sub.add_parser('prepare');v=sub.add_parser('validate');v.add_argument('--input-plan',required=True);v.add_argument('--sha256',required=True);v.add_argument('--require-handoff',action='store_true');c=sub.add_parser('compare');c.add_argument('--input-plan',required=True);c.add_argument('--sha256',required=True);c.add_argument('--control-run',required=True);a=ap.parse_args()
 if a.op=='prepare':print(json.dumps(prepare_plan(),indent=2))
 elif a.op=='validate':print(json.dumps(load_input_plan(R,a.input_plan,a.sha256,a.require_handoff),indent=2))
 else:
  plan=load_input_plan(R,a.input_plan,a.sha256,True);result=compare_runs(R,plan,a.control_run);save_new(inside(R,plan['control_workspace'])/'comparison.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
