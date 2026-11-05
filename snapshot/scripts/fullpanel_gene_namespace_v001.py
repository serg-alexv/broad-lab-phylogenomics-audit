"""Only project stage work and private temporary IPC; no images/global mounts."""
from pathlib import Path
import os,sys,json,subprocess,hashlib
R=Path(__file__).resolve().parents[1];p=Path(sys.argv[1]);assert hashlib.sha256(p.read_bytes()).hexdigest()==sys.argv[2];plan=json.loads(p.read_text());e=R/plan['work'];assert e.resolve().is_relative_to(R)
for target in('/tmp','/dev/shm'):subprocess.run(['mount','-t','tmpfs','-o','size=32m,mode=1777,nosuid,nodev','tmpfs',target],check=True)
(e/'private_namespace.json').write_text(json.dumps({'mount_namespace':os.readlink('/proc/self/ns/mnt'),'IPC_namespace':os.readlink('/proc/self/ns/ipc'),'private_tmpfs_max_bytes':67108864,'no_image_or_global_configuration_change':True,'namespace_closure_requires_external_evidence':True},indent=2))
py=R/plan['python'];os.execv(str(py),[str(py),'-B',str(R/'scripts/fullpanel_gene_assessment_v001.py'),*sys.argv[1:]])
