"""Cache only multiprocessing's IPC directory before unchanged author CLI parsing."""
from pathlib import Path
import argparse,json,multiprocessing.util,os,runpy,sys,tempfile
import checkm2_ipc_alias as ipc

def prewarm():
 if os.environ.get('TREE2_CHECKM2_PRIVATE_IPC_VERIFIED')!='1':raise RuntimeError('Private IPC alias guard missing')
 receipt=ipc.project(os.environ['TREE2_CHECKM2_PRIVATE_IPC_RECEIPT']);active=ipc.read(receipt)
 if active['status']!='PRIVATE_SHORT_IPC_ACTIVE' or active['mount_namespace']!=os.readlink('/proc/self/ns/mnt') or active['helper_sha256']!=ipc.sha(ipc.__file__):raise RuntimeError('Active private IPC receipt differs')
 if active['alias']!='/tmp' or ipc.identity('/tmp')!=active['backing_identity']:raise RuntimeError('Actual IPC alias inode differs')
 if tempfile.gettempdir()!='/tmp' or any(os.environ.get(k)!='/tmp' for k in ('TMPDIR','TMP','TEMP')):raise RuntimeError('IPC environment must precede target Python startup')
 cached=multiprocessing.util.get_temp_dir()
 if not cached.startswith('/tmp/pymp-') or len(os.fsencode(cached+'/listener-12345678'))>=108:raise RuntimeError('Multiprocessing IPC cache path not admissibly short')
 return {'status':'MULTIPROCESSING_IPC_DIRECTORY_PREWARMED','cached_ipc_directory':cached,'maximum_example_listener_bytes':len(os.fsencode(cached+'/listener-12345678')),'prewarm_tempfile_directory':tempfile.gettempdir(),'active_ipc_receipt_path':str(receipt),'active_ipc_receipt_sha256':ipc.sha(receipt),'target_python':sys.executable,'target_python_sha256':ipc.sha(sys.executable),'bootstrap_sha256':ipc.sha(__file__)}

def main():
 p=argparse.ArgumentParser();p.add_argument('--proof',required=True);p.add_argument('--proof-sha256',required=True);p.add_argument('--receipt',required=True);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
 proofpath=ipc.project(a.proof);receipt=ipc.project(a.receipt)
 if ipc.sha(proofpath)!=a.proof_sha256:raise RuntimeError('IPC source/proof binding differs')
 proof=ipc.read(proofpath)
 if proof['status']!='PRIVATE_SHORT_IPC_PROVEN' or proof['target_bootstrap_sha256']!=ipc.sha(__file__):raise RuntimeError('Target IPC bootstrap is not capability-validated')
 if not a.command or a.command[0]!='checkm2':raise RuntimeError('Expected unchanged checkm2 arguments')
 effective_path=ipc.project(os.environ['TREE2_EFFECTIVE_RUNTIME_MANIFEST'])
 if ipc.sha(effective_path)!=proof['effective_runtime_manifest_sha256']:raise RuntimeError('Effective runtime differs from IPC proof')
 effective=ipc.read(effective_path);original=ipc.project(effective['launch_protocol']['bootstrap_path'])
 if ipc.sha(original)!=effective['launch_protocol']['bootstrap_sha256'] or ipc.sha(original)!=proof['unchanged_effective_bootstrap_sha256']:raise RuntimeError('Accepted original effective bootstrap changed')
 before=prewarm();ipc.save(receipt,{**before,'phase':'BEFORE_UNCHANGED_EFFECTIVE_BOOTSTRAP','proof_sha256':a.proof_sha256})
 old_argv=sys.argv
 try:
  sys.argv=[str(original),*a.command]
  runpy.run_path(str(original),run_name='__main__')
 finally:
  sys.argv=old_argv
  after=multiprocessing.util.get_temp_dir()
  ipc.save(receipt,{**before,'phase':'UNCHANGED_EFFECTIVE_BOOTSTRAP_RETURNED_OR_RAISED','cached_ipc_directory_after':after,'ipc_cache_unchanged':after==before['cached_ipc_directory'],'scientific_tempfile_directory_after':tempfile.gettempdir(),'proof_sha256':a.proof_sha256,'author_cli_and_accepted_bootstrap_unchanged':True})
  if after!=before['cached_ipc_directory']:raise RuntimeError('Multiprocessing IPC cache changed during author CLI')
if __name__=='__main__':main()
