#!/usr/bin/env bash
set -euo pipefail
ROOT='/mnt/c/Users/wheel/Documents/Codex/2026-10-26/referenced-chatgpt-conversation-this-is-an/outputs/TREE2_WD_20261026'
MODE="${1:-proof}"
PRIVATE="$ROOT/work/checkm2_private_registry"
EVIDENCE="$ROOT/evidence/checkm2_runtime"
if [[ "$MODE" == 'outer' ]]; then
  shift
  exec unshare --mount --net --propagation private /bin/bash "$ROOT/scripts/checkm2_private_setup_ns.sh" "$@"
fi
# All mounts below are private per-process VFS bind mounts. No filesystem
# superblock is remounted and no host mount configuration is changed.
mount --make-rprivate /
mount --bind / /
mount -o remount,bind,ro /
mount --bind /mnt/c /mnt/c
mount -o remount,bind,ro /mnt/c
mount --bind "$ROOT" "$ROOT"
mount -o remount,bind,rw "$ROOT"
mount --bind "$PRIVATE" /root/.conda
mount -o remount,bind,rw /root/.conda
for outside in /tmp /var/tmp /run; do
  mount --bind "$outside" "$outside"
  mount -o remount,bind,ro "$outside"
done
export CONDA_PKGS_DIRS="$ROOT/tools/checkm2_runtime_pkgs"
export CONDA_ENVS_PATH="$ROOT/tools/checkm2_runtime_envs"
export TMPDIR="$ROOT/work/checkm2_private_tmp" TMP="$ROOT/work/checkm2_private_tmp" TEMP="$ROOT/work/checkm2_private_tmp"
export XDG_CACHE_HOME="$ROOT/work/checkm2_private_xdg"
export PYTHONDONTWRITEBYTECODE=1
export CONDA_REGISTER_ENVS=false CONDA_REPORT_ERRORS=false CONDA_NOTIFY_OUTDATED_CONDA=false CONDA_AUTO_UPDATE_CONDA=false
export CONDA_NO_PLUGINS=true OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2
export TREE2_PRIVATE_NAMESPACE_VERIFIED=1
/usr/bin/python3 - "$ROOT" <<'PY'
import json,os,pathlib,subprocess,sys,time
r=pathlib.Path(sys.argv[1]);e=r/'evidence/checkm2_runtime'
mounts={}
for p in ('/','/mnt/c',str(r),'/root/.conda','/tmp','/var/tmp','/run'):
 v=subprocess.check_output(['findmnt','-T',p,'-n','-o','TARGET,VFS-OPTIONS'],text=True).strip()
 expected_ro=p not in (str(r),'/root/.conda')
 actual_ro=bool(os.statvfs(p).f_flag & os.ST_RDONLY)
 mounts[p]={'findmnt_stack':v,'effective_read_only':actual_ro}
 assert actual_ro==expected_ro,(p,actual_ro,expected_ro,v)
canary=pathlib.Path('/root/.conda/TREE2_PRIVATE_NAMESPACE_CANARY')
canary.write_text('private Tree2 registry mapping\n')
assert (r/'work/checkm2_private_registry/TREE2_PRIVATE_NAMESPACE_CANARY').read_bytes()==canary.read_bytes()
report={'status':'PASS_PRIVATE_MOUNT_MAPPING','created_unix':time.time(),'mount_namespace':os.readlink('/proc/self/ns/mnt'),'network_namespace':os.readlink('/proc/self/ns/net'),'mounts':mounts,'project_registry_canary':str(r/'work/checkm2_private_registry/TREE2_PRIVATE_NAMESPACE_CANARY'),'old_registry_hidden_by_private_bind':True,'root_and_C_read_only_project_and_private_registry_writable':True,'HOME_unchanged':os.environ.get('HOME')}
(e/'namespace_mapping.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
PY
if [[ "$MODE" == 'run' ]]; then
  SCRIPT="${2:?project-owned script path required}"
  case "$SCRIPT" in "$ROOT/"*) ;; *) echo 'Refusing non-project script' >&2; exit 4;; esac
  exec /bin/bash "$SCRIPT"
elif [[ "$MODE" != 'proof' ]]; then
  echo 'Unsupported private installer mode' >&2; exit 4
fi
