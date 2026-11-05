"""Private RAM/model/IPC view plus the accepted read-only project PADLOC R prefix."""
from pathlib import Path
import os,sys,json,subprocess,hashlib
R=Path(__file__).resolve().parents[1];p=Path(sys.argv[1]);assert hashlib.sha256(p.read_bytes()).hexdigest()==sys.argv[2];plan=json.loads(p.read_text());E=R/plan['work'];RAM=(R/plan['ram_scratch']).resolve();assert E.resolve().is_relative_to(R)and RAM.is_relative_to(R)
for target in('/tmp','/dev/shm'):subprocess.run(['mount','-t','tmpfs','-o','size=32m,mode=1777,nosuid,nodev','tmpfs',target],check=True)
RAM.mkdir();subprocess.run(['mount','-t','tmpfs','-o','size=1280m,mode=700,nosuid,nodev','tmpfs',str(RAM)],check=True)
runtime=(R/plan['PADLOC_runtime_root']).resolve();assert runtime.is_relative_to(R);subprocess.run(['mount','--bind',str(runtime),'/usr/local'],check=True);subprocess.run(['mount','-o','remount,bind,ro','/usr/local'],check=True)
(E/'private_namespace.json').write_text(json.dumps({'mount_namespace':os.readlink('/proc/self/ns/mnt'),'IPC_namespace':os.readlink('/proc/self/ns/ipc'),'private_RAM_root':str(RAM),'private_RAM_max_bytes':1342177280,'private_tmp_and_shm_max_bytes':67108864,'read_only_project_PADLOC_runtime_binding':str(runtime),'visible_prefix':'/usr/local','no_global_WSL_change':True,'all_used_private_RAM_is_part_of_combined_RSS_memory_gate':True},indent=2))
py=R/plan['python'];os.execv(str(py),[str(py),'-B',str(R/'scripts/defence_bulk_v001.py'),*sys.argv[1:]])
