"""Tiny mocked metadata only: no real sequences, stage calls, tools or runtime."""
from pathlib import Path
import copy,unittest
import checkm2_uniform_annotation_cache_QC_v001 as m

ACC='GCF_000000001.1'
def fixture():
 refs={name:{'path':name,'sha256':str(i%10)*64,'bytes':i+1}for i,name in enumerate(('campaign','authority','verified','commit','proteins','coords','gff','coordcheck','unit','fna','stage'),1)}
 refs['stage']={**refs['proteins'],'path':'toy/'+ACC+'.faa'}
 masks={'source_holds_preserved':['TYPE_UNRESOLVED'],'source_pending_reasons':['missing_context'],'source_masks':{'production_acceptance':False,'independent_taxonomy':'UNRESOLVED_NOT_ACCEPTED'}}
 source={'accession':ACC,'FNA_from_receipt':refs['fna'],**masks}
 original={'schema':'TREE2_PROVISIONAL_UNIFORM_ANNOTATION_ROW_V001','status':'COMMITTED_PROVISIONAL_PAIRED_COORDINATE_ANNOTATION','accession':ACC,'source_metadata':{'accession':ACC,**masks},'fingerprint':{'source_FNA':refs['fna'],'gene_calling_mode':'single','translation_table':11},'artifacts':{'proteins.faa':refs['proteins'],'protein_coordinate_map.json':refs['coords'],'prodigal.gff':refs['gff']},'coordinate_integrity':{'validation':refs['coordcheck']},'scientific_execution':refs['unit'],'protein_count':3}
 candidate={'accession':ACC,'commit':refs['commit'],'proteins':refs['proteins'],'coordinates':refs['coords'],'protein_count':3,'source_metadata':original['source_metadata']}
 authority={'status':'CLOSED_VALIDATED_PROVISIONAL_PAIRED_ANNOTATION919','actual_native_exit_code':0,'actual_wsl_exit_code':0,'genomes':919,'source_masks_and_holds_preserved':True,'annotation_OS_flock_released':True,'all_1827_captured_identity_entries_and_914_owned_groups_closed':True,'verified_rows':refs['verified']}
 data={'uniform_annotation_cache_candidates':{ACC:candidate},'uniform_annotation_authority':refs['authority'],'source_rows':{ACC:source}}
 objects={'campaign':data,'authority':authority,'verified':{'rows':[candidate]},'commit':original,'unit':{'status':'UNIT0_CLOSED','actual_exit_code':0,'owned_group_empty':True}}
 def bind(ref):return Path(ref['path'])
 def read(path):return objects[str(path)]
 plan={'campaign_data':refs['campaign'],'uniform_annotation_authority':refs['authority'],'_sha':'a'*64,'source_manifest':{'sha256':'b'*64}}
 descriptor={'status':m.STATUS,'accession':ACC,'source_uniform_commit':refs['commit'],'annotation_receipt':refs['commit'],'unit_execution':refs['unit'],'uniform_annotation_authority':refs['authority'],'input_plan_sha256':plan['_sha'],'source_manifest_sha256':'b'*64,'new_annotation_unit_created':False,'legacy_ten_return_values_available':False,'selected_faa':refs['stage'],**masks}
 return plan,source,descriptor,objects,read,bind

class Cache(unittest.TestCase):
 def test_two_actual_receipt_ABIs_and_typed_zeros(self):
  self.assertTrue(m.annotation_execution_closed({'status':'UNIT0_CLOSED','actual_exit_code':0,'owned_group_empty':True}))
  self.assertTrue(m.annotation_execution_closed({'status':'UNIT_EXIT0_GROUP_CLOSED','exit_code':0,'owned_group_empty':True,'remaining_owned_processes':[]}))
  for value in(False,0.0,None,-15):self.assertFalse(m.annotation_execution_closed({'status':'UNIT0_CLOSED','actual_exit_code':value,'owned_group_empty':True}))
 def test_own_exact_honest_descriptor_returns_original(self):
  p,i,d,o,read,bind=fixture();self.assertIs(m.uniform_annotation_gate(p,i,d,read=read,bind=bind),o['commit'])
  self.assertEqual(d['annotation_receipt'],d['source_uniform_commit']);self.assertFalse(d['new_annotation_unit_created'])
 def test_fake_current_unit_or_legacy_metrics_rejected(self):
  for change in({'new_annotation_unit_created':True},{'all10_original_return_values':[]},{'unit_execution':{'path':'fake_current_0'}},{'legacy_ten_return_values_available':True}):
   p,i,d,o,read,bind=fixture()
   with self.assertRaises(RuntimeError):m.uniform_annotation_gate(p,i,{**d,**change},read=read,bind=bind)
 def test_changed_source_masks_and_FNA_rejected(self):
  for key,value in(('source_holds_preserved',[]),('source_pending_reasons',[]),('source_masks',{}),('FNA_from_receipt',{'sha256':'wrong'})):
   p,i,d,o,read,bind=fixture();i=copy.deepcopy(i);i[key]=value
   with self.assertRaises(RuntimeError):m.uniform_annotation_gate(p,i,d,read=read,bind=bind)
 def test_changed_staged_bytes_or_versioned_name_rejected(self):
  for key,value in(('bytes',1),('sha256','wrong'),('path','toy/proteins.faa')):
   p,i,d,o,read,bind=fixture();d=copy.deepcopy(d);d['selected_faa'][key]=value
   with self.assertRaises(RuntimeError):m.uniform_annotation_gate(p,i,d,read=read,bind=bind)
 def test_unknown_original_or_parent_closure_rejected(self):
  for target,key,value in(('unit','actual_exit_code',None),('authority','actual_native_exit_code',False),('authority','annotation_OS_flock_released',False)):
   p,i,d,o,read,bind=fixture();o[target][key]=value
   with self.assertRaises(RuntimeError):m.uniform_annotation_gate(p,i,d,read=read,bind=bind)
if __name__=='__main__':unittest.main()
