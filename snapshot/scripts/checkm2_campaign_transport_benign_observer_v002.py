"""Benign actual-transport observer: metadata and OS identity only, no targets."""
from pathlib import Path
import argparse,hashlib,json,os,sys
p=argparse.ArgumentParser();p.add_argument('--input-plan',required=True);p.add_argument('--input-plan-sha256',required=True);a=p.parse_args()
r=Path(__file__).resolve().parents[1];plan=Path(a.input_plan).resolve();assert plan.is_relative_to(r)
assert str(plan)==os.environ['TREE2_QC_BATCH_PLAN'] and a.input_plan_sha256==os.environ['TREE2_QC_BATCH_PLAN_SHA256']
assert hashlib.sha256(plan.read_bytes()).hexdigest()==a.input_plan_sha256
assert os.environ['TREE2_PRIVATE_NAMESPACE_VERIFIED']=='1'
assert os.environ['TREE2_CHECKM2_PILOT_LAUNCH_TOKEN']==os.environ['TREE2_TRANSPORT_PREFLIGHT_NONCE']
f=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()
owner={'pid':os.getpid(),'parent_pid':int(f[1]),'process_group':int(f[2]),'creation_ticks':int(f[19]),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
value={'status':'ACTUAL_PRIVATE_WRAPPER_TO_NEW_ENV_TRANSPORT_PASS','native_linux_identity':owner,'mount_namespace':os.readlink('/proc/self/ns/mnt'),'network_namespace':os.readlink('/proc/self/ns/net'),'received_exact_four_args':sys.argv[1:],'explicit_token_plan_SHA_verified':True,'source_compilation_runtime_model_import_or_genome_read':False}
print(json.dumps(value),flush=True)
