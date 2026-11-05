#!/usr/bin/python3
"""Transparent HMMER command/actual-exit recorder; no output or argument changes."""
from pathlib import Path
import os,sys,subprocess,json,time,uuid,hashlib,shutil
root=Path(__file__).resolve().parents[1]
target=root/'tools/bioenv/bin'/Path(sys.argv[0]).name
if not target.is_file():raise RuntimeError('Pinned HMMER executable missing: '+str(target))
folder=Path(os.environ['TREE2_HMMER_RECEIPTS']);folder.mkdir(parents=True,exist_ok=True)
token=uuid.uuid4().hex;started=time.monotonic();args=[str(target),*sys.argv[1:]]
def save(data):
 p=folder/(token+'.json');t=p.with_suffix('.tmp');t.write_text(json.dumps(data,indent=2));os.replace(t,p)
save({'status':'STARTED_NOT_COMPLETED','argv':args,'started_unix':time.time(),'wrapper_pid':os.getpid()})
p=subprocess.Popen(args);code=p.wait()
observed={'status':'ACTUAL_HMMER_EXIT_OBSERVED_CHECKPOINT_PENDING','argv':args,'actual_exit_code':code,'probe_only':len(args)==1 or args[1:]in(['-h'],['--help']),'binary_pid':p.pid,'binary_handle_waited_and_reaped':True,'wrapper_pid':os.getpid(),'ended_unix':time.time()}
save(observed) # Preserve the actual binary outcome even if later checkpoint I/O fails.
checkpoint=None
if code==0 and '--domtblout' in args and os.environ.get('TREE2_HMMER_DURABLE_DIR'):
 raw=Path(args[args.index('--domtblout')+1]);destroot=Path(os.environ['TREE2_HMMER_DURABLE_DIR']);destroot.mkdir(parents=True,exist_ok=True)
 if not destroot.resolve().is_relative_to(root):raise RuntimeError('HMM checkpoint leaves project')
 dest=destroot/(raw.parent.name+'.domtbl');temp=dest.with_suffix('.tmp');shutil.copyfile(raw,temp)
 def digest(p):
  h=hashlib.sha256()
  with Path(p).open('rb')as f:
   for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
  return h.hexdigest()
 h=digest(raw)
 if digest(temp)!=h:raise RuntimeError('Per-bin raw HMM checkpoint copy differs')
 os.replace(temp,dest);checkpoint={'path':str(dest.relative_to(root)),'sha256':h,'bytes':dest.stat().st_size,'query_faa_sha256':digest(args[-1]),'marker_file_sha256':os.environ.get('TREE2_MARKER_FILE_SHA'),'complete_binary_exit0_raw_phase_only_not_genome_QC':True}

save({'status':'ACTUAL_HMMER_EXIT_OBSERVED','argv':args,'actual_exit_code':code,'durable_raw_checkpoint':checkpoint,'probe_only':len(args)==1 or args[1:]in(['-h'],['--help']),'elapsed_seconds':time.monotonic()-started,'binary_pid':p.pid,'binary_handle_waited_and_reaped':True,'wrapper_pid':os.getpid(),'ended_unix':time.time()})
raise SystemExit(code)
