"""Pure owner imports and closed-FIRSTFV reuse predicates; no runtime or data."""
from pathlib import Path
import copy,importlib,sys,types,unittest,io,errno,hashlib,tempfile,time
from unittest.mock import patch

R=Path(__file__).resolve().parents[1]

class OwnerRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.c=importlib.import_module('checkm2_qc_persistent_common_v002')

    def fixture(self):
        refs={name:{'path':name,'sha256':name,'bytes':1} for name in
              ('checkpoint','authority','plan','source','launch','feature','unit','stock','failed','request','native_exit','execution','namespace','closure')}
        zero={'status':'UNIT_EXIT0_GROUP_CLOSED','exit_code':0,'owned_group_empty':True,'remaining_owned_processes':[],'elapsed_seconds':9.402791953000019}
        first={'status':'SAVED_FEATURE_REPAIR_VALIDATED_PENDING_CONTEXT_CLOSURE','accession':'GCF_900636715.1','repaired_request':{**refs['request'],'sha256':'e585a66ecf45d508294ae161024fdef1ee2c57bb55fd5e0f5f4fe3bcdd32621e'},'feature_validation':refs['feature'],'new_validation_execution':refs['unit'],'saved_stock_execution':refs['stock'],'failed_validation_execution':refs['failed'],'annotation_DIAMOND_or_ML_runs':0,'new_actual_feature_seconds':zero['elapsed_seconds'],'previous_feature_seconds':6.108859692001715,'cumulative_feature_seconds':15.511651645001734,'original_feature_allowance_seconds':120}
        prior={'input_plan':refs['plan'],'source_manifest':refs['source'],'native_launch':refs['launch'],'native_owner':{'pid':18940,'windows_creation_filetime_100ns':134376589361620324}}
        plan={'recovery_mode':'REUSE_CLOSED_FIRSTFV0_AND_RUN_FRESH_BULK_ONLY_V002','reused_first_feature_authority':refs['authority'],'reused_first_feature_checkpoint':refs['checkpoint'],'prior_failed_runtime':prior}
        authority={'status':'ROOT_ADMITTED_REUSE_CLOSED_FIRST_FEATURE_CHECKPOINT_V002','first_feature_checkpoint':refs['checkpoint'],'original_runtime_plan':refs['plan'],'original_source_manifest':refs['source'],'original_native_owner':prior['native_owner'],'actual_native_exit_code':2,'actual_WSL_exit_code':4,'actual_helper_exit_code':1,'parent_group_namespace_image_IPC_and_three_lease_closure_verified':True,'original_post_unmount_hash_status':'UNKNOWN_TIMEOUT_PRESERVED','original_post_unmount_hash_claimed_complete':False,'independent_windows_full_image_hash_actual_exit_code':0,'independent_windows_full_image_hash_sha256':'c40e6918688eaf2e1a9e4161e77a4b473c3f611de575b39a89bdc03fba224ad4','independent_windows_full_image_hash_bytes':17179869184,'independent_hash_exact_owner_retained_and_reaped':True,'independent_hash_deny_write_handle_and_same_file_identity_verified':True,'fresh_no_old_owners_FDs_image_loops_and_three_leases_closed':True,'no_bulk_phase_started':True,'no_feature_annotation_DIAMOND_or_ML_replay_authorized':True,'parent_actual_native_exit':refs['native_exit'],'parent_execution':refs['execution'],'parent_namespace_receipt':refs['namespace'],'parent_external_closure':refs['closure'],'independent_windows_full_image_hash':refs['closure'],'independent_windows_full_image_hash_actual_exit':refs['native_exit'],'fresh_external_owner_FD_loop_and_three_lease_closure':refs['closure']}
        objects={'authority':authority,'checkpoint':first,'feature':{'status':'P20_FEATURES_PASS_PENDING_NATIVE_CLOSURE','accession':'GCF_900636715.1','finite_domain_features':21241,'exact_FAA_metadata_features':22,'independently_recomputed_membership_features':1220,'membership_mismatches':0},'unit':zero,'stock':{**zero,'elapsed_seconds':81.0847595},'failed':{**zero,'status':'UNIT_FAILED_OR_CLOSURE_UNPROVEN','exit_code':1,'elapsed_seconds':6.108859692001715}}
        return plan,objects

    def check(self,plan,objects):
        with patch.object(self.c,'bind',lambda ref:ref['path']),patch.object(self.c,'read',lambda p:objects.get(p,{})):
            return self.c.reuse_first_feature_gate(plan)

    def test_real_owner_imports_have_distinct_complete_path_ABI(self):
        base=types.ModuleType('checkm2_private_install_controller');base.utc=lambda:'PURE';base.OWNER={'pid':1};base.L='/PURE'
        pilot=types.ModuleType('checkm2_protein_pilot_v001');pilot.legacy=types.SimpleNamespace()
        with patch.dict(sys.modules,{'checkm2_private_install_controller':base,'checkm2_protein_pilot_v001':pilot}),patch('subprocess.Popen',side_effect=AssertionError('No process')),patch('subprocess.run',side_effect=AssertionError('No process')):
            for suffix in ('native','entry','bridge'):
                module=importlib.import_module('checkm2_qc_persistent_'+suffix+'_v002')
                self.assertTrue(callable(module.main))
        self.assertEqual(self.c.E,R/'work/checkm2_qc_persistent_native_v002')
        self.assertEqual(self.c.OUT,R/'analysis/checkm2_qc_persistent_session_v002')
        self.assertEqual(self.c.STEP,self.c.E/'step.json')
        self.assertTrue(str(self.c.STOP).endswith('STOP_CHECKM2_QC_PERSISTENT_V002'))
        self.assertFalse(any(n.split('.')[0]in('numpy','pandas','tensorflow','keras','lightgbm','sklearn')for n in sys.modules))

    def test_exact_original_two_feature_debits_and_zero_reuse(self):
        plan,objects=self.fixture();ref,first=self.check(plan,objects)
        self.assertEqual(ref,plan['reused_first_feature_checkpoint']);self.assertEqual(first['cumulative_feature_seconds'],15.511651645001734)

    def test_unknown_or_false_parent_exit_is_rejected(self):
        for field,value in [('actual_native_exit_code',None),('actual_native_exit_code',0),('actual_WSL_exit_code',1),('actual_WSL_exit_code',False),('actual_helper_exit_code',0),('parent_group_namespace_image_IPC_and_three_lease_closure_verified',False),('independent_windows_full_image_hash_actual_exit_code',False),('original_post_unmount_hash_claimed_complete',True),('independent_hash_deny_write_handle_and_same_file_identity_verified',False)]:
            plan,objects=self.fixture();objects['authority'][field]=value
            with self.assertRaises(RuntimeError):self.check(plan,objects)

    def test_original_unit_feature_or_debit_tampering_is_rejected(self):
        for obj,key,value in [('unit','exit_code',-15),('feature','membership_mismatches',1),('failed','elapsed_seconds',0),('checkpoint','annotation_DIAMOND_or_ML_runs',1)]:
            plan,objects=self.fixture();objects[obj][key]=value
            with self.assertRaises(RuntimeError):self.check(plan,objects)

    def test_bridge_has_no_first_feature_dispatch_and_shell_is_LF(self):
        text=(R/'scripts/checkm2_qc_persistent_bridge_v002.py').read_text()
        self.assertNotIn('run_saved_features',text);self.assertNotIn('invoke_first',text)
        self.assertLess(text.index('reuse_first_feature_gate(plan)'),text.index('queue.run_campaign('))
        self.assertIn('ORIGINAL_CLOSED_FIRSTFV0_REUSED_NO_CURRENT_EXECUTION',text)
        shell=(R/'scripts/checkm2_qc_persistent_v002.sh').read_bytes();self.assertNotIn(b'\r',shell)
        self.assertEqual(shell,(R/'scripts/checkm2_qc_persistent_v001.sh').read_bytes().replace(b'checkm2_qc_persistent_entry_v001.py',b'checkm2_qc_persistent_entry_v002.py'))

    def test_real_efficient_hash_preserves_digest_and_file_identity(self):
        entry=importlib.import_module('checkm2_qc_persistent_entry_v002')
        data=bytes(range(256))*257
        with tempfile.TemporaryDirectory(dir=R/'work',prefix='closed_hash_pure_')as temp:
            file=Path(temp)/'toy.bin';file.write_bytes(data)
            with patch.object(entry,'linux_available_bytes',lambda:2**40),patch.object(entry.common,'active_resource_limits',lambda:{'linux_available_minimum_bytes':1}),patch.object(entry,'publish',lambda *a,**k:None),patch.dict(entry.CONTEXT,{'cold_monotonic_deadline':time.monotonic()+1000}):
                digest,count=entry.hash_closed_image(file,{'operation':'PURE_TOY'})
            self.assertEqual(digest,hashlib.sha256(data).hexdigest());self.assertEqual(count,len(data))

    def test_ENOMEM_fallback_seeks_back_and_preserves_all_bytes(self):
        blocks=importlib.import_module('checkm2_qc_persistent_entry_v002').closed_image_blocks
        data=b'0123456789'*3000
        class Reads(io.BytesIO):
            def __init__(self,payload,error):super().__init__(payload);self.error=error;self.calls=[]
            def read(self,size=-1):
                self.calls.append(size)
                if len(self.calls)==1:
                    super().read(7)
                    raise self.error
                return super().read(size)
        for error in(MemoryError('toy'),OSError(errno.ENOMEM,'toy')):
            stream=Reads(data,error);self.assertEqual(b''.join(blocks(stream)),data)
            self.assertEqual(stream.calls[0],8*1024**2);self.assertEqual(set(stream.calls[1:]),{4096})

    def test_fallback_second_ENOMEM_and_other_IO_errors_remain_fatal(self):
        blocks=importlib.import_module('checkm2_qc_persistent_entry_v002').closed_image_blocks
        class Bad(io.BytesIO):
            def __init__(self,error):super().__init__(b'toy');self.error=error;self.calls=0
            def read(self,size=-1):self.calls+=1;raise self.error
        for error,expected in((OSError(errno.ENOMEM,'toy'),2),(MemoryError('toy'),2),(OSError(errno.EACCES,'toy'),1)):
            stream=Bad(error)
            with self.assertRaises(type(error)):list(blocks(stream))
            self.assertEqual(stream.calls,expected)

    def test_hash_policy_proofs_initial_periodic_and_final_not_each_block(self):
        entry=importlib.import_module('checkm2_qc_persistent_entry_v002');clock=[0.];calls=[]
        def policy():calls.append(clock[0]);return{'linux_available_minimum_bytes':1}
        def blocks(handle):
            for when,data in zip((.1,.4,1.1,1.5,2.2),(b'a',b'b',b'c',b'd',b'e')):
                clock[0]=when;yield data
        with tempfile.TemporaryDirectory(dir=R/'work',prefix='policy_clock_pure_')as temp:
            file=Path(temp)/'toy.bin';file.write_bytes(b'abcde')
            with patch.object(entry.time,'monotonic',lambda:clock[0]),patch.object(entry,'closed_image_blocks',blocks),patch.object(entry,'linux_available_bytes',lambda:2**40),patch.object(entry.common,'active_resource_limits',policy),patch.object(entry,'publish',lambda *a,**k:None),patch.dict(entry.CONTEXT,{'cold_monotonic_deadline':1000}):
                digest,count=entry.hash_closed_image(file,{'operation':'PURE_TOY'})
        self.assertEqual(calls,[0.,1.1,2.2,2.2]);self.assertEqual(count,5);self.assertEqual(digest,hashlib.sha256(b'abcde').hexdigest())

    def test_final_policy_revalidation_cannot_hide_deadline_overrun(self):
        entry=importlib.import_module('checkm2_qc_persistent_entry_v002');clock=[0.];calls=[]
        def policy():
            calls.append(clock[0])
            if len(calls)==2:clock[0]=601.
            return{'linux_available_minimum_bytes':1}
        with tempfile.TemporaryDirectory(dir=R/'work',prefix='policy_deadline_pure_')as temp:
            file=Path(temp)/'toy.bin';file.write_bytes(b'toy')
            with patch.object(entry.time,'monotonic',lambda:clock[0]),patch.object(entry,'linux_available_bytes',lambda:2**40),patch.object(entry.common,'active_resource_limits',policy),patch.object(entry,'publish',lambda *a,**k:None),patch.dict(entry.CONTEXT,{'cold_monotonic_deadline':1000}):
                with self.assertRaises(TimeoutError):entry.hash_closed_image(file,{'operation':'PURE_TOY'})

if __name__=='__main__':unittest.main()
