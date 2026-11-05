#!/usr/bin/python3
"""Transparent HMMER command/actual-exit recorder; no output or argument changes."""
from pathlib import Path
import os,sys,subprocess,json,time,uuid,hashlib
root=Path(__file__).resolve().parents[1]
target=root/'tools/bioenv/bin'/Path(sys.argv[0]).name
if not target.is_file():raise RuntimeError('Pinned HMMER executable missing: '+str(target))
folder=Path(os.environ['TREE2_HMMER_RECEIPTS']);folder.mkdir(parents=True,exist_ok=True)
token=uuid.uuid4().hex;started=time.monotonic();args=[str(target),*sys.argv[1:]]
def save(data):
 p=folder/(token+'.json');t=p.with_suffix('.tmp');t.write_text(json.dumps(data,indent=2));os.replace(t,p)
save({'status':'STARTED_NOT_COMPLETED','argv':args,'started_unix':time.time(),'wrapper_pid':os.getpid()})
p=subprocess.Popen(args);code=p.wait()
save({'status':'ACTUAL_HMMER_EXIT_OBSERVED','argv':args,'actual_exit_code':code,'probe_only':len(args)==1 or args[1:]in(['-h'],['--help']),'elapsed_seconds':time.monotonic()-started,'binary_pid':p.pid,'binary_handle_waited_and_reaped':True,'wrapper_pid':os.getpid(),'ended_unix':time.time()})
raise SystemExit(code)
