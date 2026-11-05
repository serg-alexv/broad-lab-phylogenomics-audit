"""Only private volatile IPC mounts; no disk image or global mount/config changes."""
from pathlib import Path
import os,sys,json,subprocess
R=Path(__file__).resolve().parents[1];plan=json.loads(Path(sys.argv[1]).read_text());e=R/plan['work']
if not e.resolve().is_relative_to(R):raise RuntimeError('Namespace evidence leaves project')
before=os.readlink('/proc/self/ns/mnt')
subprocess.run(['mount','-t','tmpfs','-o','size=32m,mode=1777,nosuid,nodev','tmpfs','/tmp'],check=True)
subprocess.run(['mount','-t','tmpfs','-o','size=32m,mode=1777,nosuid,nodev','tmpfs','/dev/shm'],check=True)
e.mkdir(exist_ok=True);p=e/'private_namespace.json';p.write_text(json.dumps({'mount_namespace':before,'IPC_namespace':os.readlink('/proc/self/ns/ipc'),'private_tmpfs_bytes':2*32*1024**2,'no_image_or_global_config_change':True,'final_namespace_lifetime_requires_retained_entry_exit':True},indent=2))
py=str(R/plan['python']);os.execv(py,[py,'-B',str(R/'scripts/checkm1_order_queue_v001.py'),*sys.argv[1:]])
