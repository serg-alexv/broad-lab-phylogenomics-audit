"""Generate source-only benchmark wrappers from exact accepted wrapper bytes."""
from pathlib import Path
import ast,hashlib,json
R=Path(__file__).resolve().parents[1]
def source(name,expected):
 p=R/'scripts'/name
 if hashlib.sha256(p.read_bytes()).hexdigest()!=expected:raise RuntimeError('Accepted source differs:'+name)
 return p.read_text()
def write(name,value):
 p=R/'scripts'/name;data=value.replace('\r\n','\n').encode()
 if p.exists():
  if p.read_bytes()!=data:raise RuntimeError('Refusing changed source overwrite:'+name)
 else:
  with p.open('xb') as f:f.write(data)
 if name.endswith('.py'):ast.parse(value)
 return {'path':p.relative_to(R).as_posix(),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
def main():
 entry=source('checkm2_format_entry_v002.py','e2fa404a30c80cb5fa0eddb5282ba0daa7b34e54bd5b5d04d73cad5743e7441f')
 entry=entry.replace('checkm2_format_common_v002','checkm2_benchmark10_common_v002').replace('checkm2_protein_format_invariance_v002','checkm2_benchmark10_protein_v002').replace('checkm2_format_inner_v002.py','checkm2_benchmark10_inner_v002.py').replace("deadline=time.monotonic()+2100","deadline=time.monotonic()+10200").replace("'unit': 'pilot genomes'","'unit': 'benchmark annotation commits'").replace("done=1, detail='Format-control outputs and namespace closed; actual native exit, leases and comparison pending'","done=inner.get('done',0), detail='Benchmark phase outputs and namespace closed; actual native exit/leases/root review pending'")
 entry=entry.replace("'status': 'PREPARING', 'done': 0, 'total': 1", "'status': 'PREPARING', 'done': previous.get('done',0) if previous.get('windows_launch_token')==launch['token'] else 0, 'total': 10")
 native=source('checkm2_format_native_v002_ENV1.py','c8991d486ef20439669e0655d60dc93026c422d9c2a030007edb1abeca5e44f0')
 native=native.replace('checkm2_format_common_v002','checkm2_benchmark10_common_v002').replace('checkm2_protein_format_invariance_v002','checkm2_benchmark10_protein_v002').replace('checkm2_format_native_v002.py','checkm2_benchmark10_native_v002.py').replace('checkm2_format_v002_LF1.sh','checkm2_benchmark10_protein_v002.sh').replace('c.v.','c.').replace("'total':1,'unit':'DNA-wrap61 format controls'","'total':10,'unit':'benchmark annotation commits'").replace("'operation':'FORMAT_CONTROL'","'operation':'BENCHMARK10'").replace("deadline=time.monotonic()+2700","deadline=time.monotonic()+10800").replace("min(1,int(step.get('done',0)))","min(10,int(step.get('done',0)))")
 start=native.index('def group_receipts_closed(run):');end=native.index('def main(a):',start)
 native=native[:start]+'def group_receipts_closed(run):\n return c.group_receipts_closed(run)\n\n'+native[end:]
 native=native.replace("with (c.E/'native_once_claim_ENV1.json').open('x') as f:","claims=c.E/'native_phase_claims';claims.mkdir(exist_ok=True)\n with (claims/(c.sha(c.ADMISSION)+'.json')).open('x') as f:")
 native=native.replace('One DNA-wrap61 format control admitted; runtime initialization pending','Root-admitted benchmark phase; runtime initialization pending').replace('CONTROL_OUTPUTS_NAMESPACE_CLOSED_PENDING_OBSERVED_OWNER_EXIT_COMPARISON','BENCHMARK_PHASE_OUTPUTS_CLOSED_PENDING_OBSERVED_OWNER_EXIT_REVIEW').replace("status.startswith('CONTROL_OUTPUTS_NAMESPACE_CLOSED')","status.startswith('BENCHMARK_PHASE_OUTPUTS_CLOSED')").replace('CONTROL_FAILED_OR_CLOSURE_UNPROVEN','BENCHMARK_FAILED_OR_CLOSURE_UNPROVEN').replace('Format-control outputs and namespace closed; actual owner exit, released leases and comparison still pending; benchmark not run','Benchmark phase outputs closed; external actual owner exit and released leases/root review pending').replace("pending',1,diagnostic_completion", "pending',int(envelope.get('inner_progress',{}).get('done',0)),diagnostic_completion")
 native=native.replace('Outer format limit','Outer benchmark limit').replace('the one DNA-wrap61 control','the admitted ten-genome benchmark phase').replace('Different control pending pointer','Different benchmark pending pointer').replace('Control target/groups/runtime','Benchmark target/groups/runtime').replace('Format control failed or closure unproven; original baseline remains preserved; no retry','Benchmark phase failed or closure unproven; committed units preserved; no retry').replace("'format_comparison':","'benchmark_review':")
 native=native.replace("if latest['input_plan_sha256']!=a.input_plan_sha256:raise RuntimeError('Different benchmark pending pointer')","if not c.pending_is_current(latest,TOKEN,a.input_plan_sha256,launch['protocol_admission_sha256'],envelope_path):raise RuntimeError('Current benchmark launch/protocol/namespace pointer absent or stale')")
 native=native.replace("'input_plan_sha256':a.input_plan_sha256,'stdout':", "'input_plan_sha256':a.input_plan_sha256,'protocol_admission_sha256':c.sha(c.ADMISSION),'phase':admitted['phase'],'stdout':")
 native=native.replace("  c.plan_gate(a.input_plan,a.input_plan_sha256)\n  status=", "  c.plan_gate(a.input_plan,a.input_plan_sha256)\n  if c.sha(c.ADMISSION)!=launch['protocol_admission_sha256']:raise RuntimeError('Benchmark phase Ready changed during owned execution')\n  status=")
 shell=source('checkm2_format_v002_LF1.sh','8defc60fde57332e6351cabdc48d4d5d38b1c7583f3f4dd27efc36287a6cba4a').replace('checkm2_format_entry_v002.py','checkm2_benchmark10_entry_v002.py')
 rows=[write('checkm2_benchmark10_entry_v002.py',entry),write('checkm2_benchmark10_native_v002.py',native),write('checkm2_benchmark10_protein_v002.sh',shell)]
 if b'\r' in (R/'scripts/checkm2_benchmark10_protein_v002.sh').read_bytes():raise RuntimeError('Executed benchmark shell contains CR')
 print(json.dumps({'status':'HELD_SOURCES_ONLY_NO_ENTRY_OR_HELPER_EXECUTION','sources':rows}))
if __name__=='__main__':main()
