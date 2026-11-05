"""Metadata-only immutable queue/control packet. No genome/protein/tool reads."""
from pathlib import Path
import argparse,hashlib,json,os
from checkm2_qc_campaign_data_v001 import campaign_data
R=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def row(p):return {'path':p.relative_to(R).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
def bind(ref):
 p=(R/ref['path']).resolve()
 if not p.is_relative_to(R)or p.suffix!='.json'or row(p)!=ref:raise RuntimeError('Metadata-only exact bound JSON required')
 return p
def create(p,value):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb')as f:f.write((json.dumps(value,indent=2)+'\n').encode());f.flush();os.fsync(f.fileno())
 return row(p)
def prepare(output):
 queue=row(R/'metadata/tree2_qc_campaign_queue_v001.json');registry=row(R/'metadata/checkm2_accepted_method_result_registry_v006.json');repair=row(R/'metadata/checkm2_feature_request_repair_20261028/compound_cohort_repair_packet_v002.json')
 if queue['sha256']!='44d456e79af0f84a2c35a2dd3e1b6f8cd748df31d17ee8273becca7a765b75f1'or registry['sha256']!='8eb2c4cd6b679dc3f9f845fb56d3a8cd90e629bdb15623288f22bf9a0a81bbe7':raise RuntimeError('Frozen source queue/accepted registry changed')
 q=read(bind(queue));r=read(bind(registry));p=read(bind(repair));data=campaign_data(q,r,p)
 accepted=next(x for x in r['rows']if x['accession']=='GCF_002993975.1');own=read(bind(accepted['commit']));ann=read(bind(own['annotation_commit']));search=read(bind(own['diamond_commit']));raw=read(bind(search['diamond_receipt']))
 if raw.get('index_chunks')!=8 or raw.get('block_size')!=.5 or raw.get('threads')!=1:raise RuntimeError('Already accepted same8 serial control required')
 control={'role':'SEARCH_ONLY_CONTROL','accession':accepted['accession'],'selected_faa':ann['selected_faa'],'annotation_receipt':ann['annotation_receipt'],'annotation_unit_execution':ann['unit_execution'],'annotation_commit':own['annotation_commit'],'serial_search_commit':own['diamond_commit'],'reference_raw_diamond':search['raw_diamond'],'accepted_method_authority':accepted['authority']}
 uniform=row(R/'work/uniform_annotation_native_v003/local_controller_closed_annotation_acceptance_b37b.json');a=read(bind(uniform));rows=read(bind(a['verified_rows']))
 if a.get('status')!='CLOSED_VALIDATED_PROVISIONAL_PAIRED_ANNOTATION919'or a.get('actual_native_exit_code')!=0 or a.get('actual_wsl_exit_code')!=0 or len(rows['rows'])!=919:raise RuntimeError('Actual closed919 annotation cache context required')
 by={x['accession']:x for x in rows['rows']}
 data.update(canonical_queue=queue,accepted_registry=registry,compound_repair_packet=repair,controls=[control],uniform_annotation_authority=uniform,verified_uniform_annotations=a['verified_rows'],uniform_annotation_cache_candidates={acc:by[acc]for acc in data['ordered_new_accessions']},annotation_cache_ABI='ACTUAL_UNIFORM_RECEIPTS_NOT_RELABELLED_LEGACY_TEN_RETURN_CHECKM2_CALLER',scientific_execution_authorized=False,root_parent_admission=None)
 return create(output,data)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--output',required=True);args=a.parse_args();p=(R/args.output).resolve()
 if not p.is_relative_to(R):raise RuntimeError('Output outside project')
 print(json.dumps(prepare(p),indent=2))
