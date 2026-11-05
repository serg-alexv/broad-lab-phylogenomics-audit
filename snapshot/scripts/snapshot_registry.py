from pathlib import Path
import datetime,hashlib,json,shutil
root=Path('/mnt/c/Users/wheel/Documents/Codex/2026-10-26/referenced-chatgpt-conversation-this-is-an/outputs/TREE2_WD_20261026')
p=Path('/root/.conda/environments.txt')
data=p.read_bytes()
out=root/'evidence/tooling/environment_registry_current.txt'
out.write_bytes(data)
record={'source':str(p),'copied_to':str(out.relative_to(root)),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'mtime_utc':datetime.datetime.fromtimestamp(p.stat().st_mtime,datetime.timezone.utc).isoformat(),'original_baseline_bytes':'NOT_SNAPSHOTTED','no_tree2_registration':str(root/'tools/bioenv') not in data.decode(),'limitation':'Timestamp changed during conda install preparation despite CONDA_REGISTER_ENVS=false. No byte-unchanged assertion or restoration. No old environment or scientific payload modified.'}
(root/'evidence/tooling/environment_registry_side_effect.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2))