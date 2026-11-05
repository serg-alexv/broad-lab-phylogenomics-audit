#!/usr/bin/python3
"""Unmodified HMMER args/output; typed waited exits and durable per-search raw copies."""
from pathlib import Path
import os,sys,json,time,uuid,hashlib,subprocess,shutil
R=Path(__file__).resolve().parents[1];tool=R/'tools/bioenv/bin/hmmsearch';args=[str(tool),*sys.argv[1:]];O=Path(os.environ['TREE2_DEFENCE_SEARCH_RECEIPTS']);O.mkdir(parents=True,exist_ok=True);assert O.resolve().is_relative_to(R);token=uuid.uuid4().hex;started=time.monotonic()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for block in iter(lambda:f.read(8*1024**2),b''):h.update(block)
 return h.hexdigest()
def save(v):
 p=O/(token+'.json');t=p.with_suffix('.tmp')
 with t.open('w')as f:json.dump(v,f,indent=2);f.flush();os.fsync(f.fileno())
 os.replace(t,p)
p=subprocess.Popen(args);fields=Path('/proc/'+str(p.pid)+'/stat').read_text().rsplit(')',1)[1].split();birth={'pid':p.pid,'creation_ticks':int(fields[19]),'process_group':int(fields[2]),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()};code=p.wait();observed={'status':'ACTUAL_HMMER_EXIT_RAW_CHECKPOINT_PENDING','argv':args,'actual_exit_code':code,'binary_identity':birth,'binary_pid':p.pid,'binary_handle_waited_and_reaped':True,'wrapper_pid':os.getpid(),'ended_unix':time.time(),'probe_only':len(args)==2 and args[1]in('-h','--help')};save(observed)
raw=[]
if code==0:
 for flag in('--domtblout','--tblout','-o'):
  if flag not in args:continue
  source=Path(args[args.index(flag)+1]).resolve();assert source.is_relative_to(R)and source.is_file();dest=O/(token+flag.replace('-','_')+'.raw');shutil.copyfile(source,dest);s=sha(source);assert sha(dest)==s
  with dest.open('rb')as f:f.seek(max(0,dest.stat().st_size-4096));tail=f.read()
  if b'[ok]'not in tail:raise RuntimeError('HMMER binary0 raw output lacks complete terminator')
  raw.append({'path':str(dest.relative_to(R)),'sha256':s,'bytes':dest.stat().st_size,'original_stock_output_path':str(source)})
observed.update(status='ACTUAL_HMMER_EXIT_AND_RAW_CHECKPOINT_OBSERVED',raw_outputs=raw,elapsed_seconds=time.monotonic()-started)
if raw:observed.update(query_faa_sha256=sha(args[-1]),model_file_sha256=sha(args[-2]),no_argument_or_threshold_changes=True)
save(observed);raise SystemExit(code)
