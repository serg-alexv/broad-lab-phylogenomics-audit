"""Honest supplied-protein reuse of closed uniform annotation; no tools on import."""
from pathlib import Path
import os,re,shutil,uuid

R=Path(__file__).resolve().parents[1]
STATUS='UNIFORM_ANNOTATION_REUSED_NO_NEW_UNIT'
MASKS=('source_holds_preserved','source_pending_reasons','source_masks')

def annotation_execution_closed(unit):
    if unit.get('owned_group_empty')is not True:return False
    if unit.get('status')=='UNIT0_CLOSED':
        return type(unit.get('actual_exit_code'))is int and unit['actual_exit_code']==0
    return (unit.get('status')=='UNIT_EXIT0_GROUP_CLOSED' and type(unit.get('exit_code'))is int
            and unit['exit_code']==0 and unit.get('remaining_owned_processes')==[])

def _context(plan,item,*,read,bind):
    acc=item['accession']
    if not re.fullmatch(r'GC[AF]_\d{9}\.\d+',acc):raise RuntimeError('Versioned own accession required')
    data=read(bind(plan['campaign_data']));candidate=data['uniform_annotation_cache_candidates'][acc]
    authority_ref=plan['uniform_annotation_authority']
    if data['uniform_annotation_authority']!=authority_ref:raise RuntimeError('Uniform annotation authority differs')
    authority=read(bind(authority_ref))
    if (authority.get('status')!='CLOSED_VALIDATED_PROVISIONAL_PAIRED_ANNOTATION919'
        or type(authority.get('actual_native_exit_code'))is not int or authority['actual_native_exit_code']!=0
        or type(authority.get('actual_wsl_exit_code'))is not int or authority['actual_wsl_exit_code']!=0
        or authority.get('genomes')!=919 or any(authority.get(k)is not True for k in
        ('source_masks_and_holds_preserved','annotation_OS_flock_released','all_1827_captured_identity_entries_and_914_owned_groups_closed'))):
        raise RuntimeError('Actual closed uniform919 authority required; no annotation or QC promotion')
    verified=read(bind(authority['verified_rows']));matches=[x for x in verified['rows']if x['accession']==acc]
    if len(matches)!=1 or matches[0]!=candidate:raise RuntimeError('Own cached row differs from closed verified919 row')
    original=read(bind(candidate['commit']));source=data['source_rows'][acc]
    if (candidate['accession']!=acc or original.get('schema')!='TREE2_PROVISIONAL_UNIFORM_ANNOTATION_ROW_V001'
        or original.get('status')!='COMMITTED_PROVISIONAL_PAIRED_COORDINATE_ANNOTATION' or original.get('accession')!=acc
        or original['source_metadata']!=candidate['source_metadata'] or original['fingerprint']['source_FNA']!=source['FNA_from_receipt']
        or original['fingerprint'].get('gene_calling_mode')!='single' or original['fingerprint'].get('translation_table')!=11
        or candidate['proteins']!=original['artifacts']['proteins.faa']
        or candidate['coordinates']!=original['artifacts']['protein_coordinate_map.json']
        or candidate['protein_count']!=original['protein_count']):raise RuntimeError('Own uniform protein/FNA/method/source association differs')
    for key in MASKS:
        if key not in item or item[key]!=source[key] or item[key]!=original['source_metadata'][key]:raise RuntimeError('Own source holds/pending/masks changed: '+key)
    if 'FNA_from_receipt'in item and item['FNA_from_receipt']!=source['FNA_from_receipt']:raise RuntimeError('Own FNA receipt differs')
    if 'fasta_sha256'in item and item['fasta_sha256']!=source['FNA_from_receipt']['sha256']:raise RuntimeError('Own FNA SHA differs')
    if not annotation_execution_closed(read(bind(original['scientific_execution']))):raise RuntimeError('Original uniform scientific execution not actual0/closed')
    for ref in (candidate['proteins'],candidate['coordinates'],original['artifacts']['prodigal.gff'],original['coordinate_integrity']['validation']):bind(ref)
    return candidate,original,authority_ref

def uniform_annotation_gate(plan,item,descriptor,*,read,bind):
    candidate,original,authority_ref=_context(plan,item,read=read,bind=bind)
    if (descriptor.get('status')!=STATUS or descriptor.get('accession')!=item['accession']
        or descriptor.get('source_uniform_commit')!=candidate['commit'] or descriptor.get('annotation_receipt')!=candidate['commit']
        or descriptor.get('unit_execution')!=original['scientific_execution'] or descriptor.get('uniform_annotation_authority')!=authority_ref
        or descriptor.get('input_plan_sha256')!=plan['_sha'] or descriptor.get('source_manifest_sha256')!=plan['source_manifest']['sha256']
        or descriptor.get('new_annotation_unit_created')is not False or descriptor.get('legacy_ten_return_values_available')is not False):
        raise RuntimeError('Supplied-protein descriptor lineage differs or invents a new annotation unit')
    for key in MASKS:
        if descriptor.get(key)!=item[key]:raise RuntimeError('Staged annotation mask differs: '+key)
    if any(k in descriptor for k in ('all10_original_return_values','all10_return_values','new_unit_execution')):raise RuntimeError('No fabricated legacy caller metrics or current annotation execution')
    selected=descriptor['selected_faa'];staged=Path(bind(selected))
    if (staged.name!=item['accession']+'.faa' or selected['sha256']!=candidate['proteins']['sha256']
        or selected['bytes']!=candidate['proteins']['bytes']):raise RuntimeError('Staged own versioned FAA differs from exact cached proteins')
    return original

def stage_uniform_annotation(plan,item,folder,*,read,bind,row,save):
    folder=Path(folder).resolve();acc=item['accession'];run=Path(plan['run_directory']).resolve()
    if not folder.is_relative_to(R) or folder!=(run/'rows'/acc).resolve():raise RuntimeError('Own annotation staging escapes declared row')
    target=folder/'annotation'/f'{acc}.faa';commit_path=folder/'annotation_commit.json'
    if commit_path.exists():
        descriptor=read(commit_path);uniform_annotation_gate(plan,item,descriptor,read=read,bind=bind)
    else:
        candidate,original,authority_ref=_context(plan,item,read=read,bind=bind)
        source=Path(bind(candidate['proteins']))
        target.parent.mkdir(parents=True,exist_ok=False)
        partial=target.with_name(target.name+'.'+uuid.uuid4().hex+'.partial')
        with source.open('rb')as src,partial.open('xb')as dst:shutil.copyfileobj(src,dst,1024*1024);dst.flush();os.fsync(dst.fileno())
        actual=row(partial)
        if actual['sha256']!=candidate['proteins']['sha256']or actual['bytes']!=candidate['proteins']['bytes']:raise RuntimeError('Copied cached FAA SHA/bytes differ')
        os.link(partial,target);partial.unlink()
        descriptor={'status':STATUS,'accession':acc,'selected_faa':row(target),'annotation_receipt':candidate['commit'],
            'source_uniform_commit':candidate['commit'],'unit_execution':original['scientific_execution'],
            'uniform_annotation_authority':authority_ref,'input_plan_sha256':plan['_sha'],
            'source_manifest_sha256':plan['source_manifest']['sha256'],'new_annotation_unit_created':False,
            'legacy_ten_return_values_available':False,'production_panel_acceptance':False,'defence_status':'UNKNOWN_UNSEARCHED',
            **{key:item[key]for key in MASKS}}
        save(commit_path,descriptor);uniform_annotation_gate(plan,item,descriptor,read=read,bind=bind)
    return {'accession':acc,'role':'FRESH','selected_faa':descriptor['selected_faa'],'annotation_receipt':descriptor['annotation_receipt'],
            'annotation_unit_execution':descriptor['unit_execution'],'annotation_commit':row(commit_path)}
