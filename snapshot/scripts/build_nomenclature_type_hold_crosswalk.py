"""Freeze accepted source-only holds for downstream QC; never alter the panel."""
from pathlib import Path
import csv
import datetime
import hashlib
import io
import json
import os

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'analysis/sequence_qc/d64e016face251f1/nomenclature_source_review'
REVIEWS = [
    (BASE/'priority1_first3_20261026','79d3d67b690a123d1fb13382fff613dfcc44ae61345d15f8caf2faae4672bfd8'),
    (BASE/'priority1_next3_20261027_v1','78dd6bc41854b9e6959e83863f3e02ab3302002dee223ebadd0dd043ce2d2e14')]
OUT = ROOT / 'metadata/nomenclature_type_holds/v001'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def save(path, obj):
    temp = path.with_suffix(path.suffix+'.tmp')
    with temp.open('w', encoding='utf-8', newline='') as handle:
        json.dump(obj, handle, indent=2)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def verify(directory, expected):
    if sha(directory/'manifest.json') != expected:
        raise RuntimeError('Accepted source manifest changed')
    rows = read(directory/'manifest.json')['files']
    for row in rows:
        path = (directory/row['path']).resolve()
        if not path.is_relative_to(directory.resolve()) or path.stat().st_size != row['bytes'] or sha(path) != row['sha256']:
            raise RuntimeError('Source-only artifact differs: '+str(path))
    return len(rows)


def tsv(path, rows):
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), delimiter='\t', lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    temporary = path.with_suffix('.tmp')
    with temporary.open('w',encoding='utf-8',newline='') as handle:
        handle.write(buffer.getvalue())
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary,path)


def main():
    checked = [dict(path=folder.relative_to(ROOT).as_posix(),manifest_sha256=digest,artifacts_verified=verify(folder,digest)) for folder,digest in REVIEWS]
    if (OUT/'commit.json').exists():
        commit=read(OUT/'commit.json')
        count=verify(OUT,commit['manifest_sha256'])
        print(json.dumps(dict(status='VERIFIED_IMMUTABLE_SOURCE_HOLD_CROSSWALK_NO_FETCH',manifest_sha256=commit['manifest_sha256'],artifacts=count)))
        return
    OUT.mkdir(parents=True,exist_ok=False)
    first,next_=[folder for folder,digest in REVIEWS]
    a=read(first/'review_decisions.json');b=read(next_/'decisions.json')
    inputs=[read(folder/'accepted_inputs.json') for folder,digest in REVIEWS]
    cached={row['accession']:row for item in inputs for row in item['genome_source_records']}
    assert len(cached)==18
    for row in cached.values():
        if sha(ROOT/row['report_path'])!=row['report_sha256'] or sha(ROOT/'raw'/row['accession']/'acquisition_receipt.json')!=row['acquisition_receipt_sha256']:
            raise RuntimeError('Cached genome source record changed')
    panelpath=ROOT/'metadata/provisional_panel.json';panelsha=sha(panelpath)
    panel={row['accession']:row for row in read(panelpath)}
    members={accession:component['component_id'] for item in inputs for component in item['components'] for accession in component['members']}
    assert len(members)==18
    firstmaps={row['accession']:row for row in a['genome_identifier_mappings']}
    nextmaps={row['accession']:row for row in b['genome_source_assessments']}
    genomes=[]
    for accession in sorted(cached):
        source=cached[accession];mapping=firstmaps.get(accession) or nextmaps[accession]
        if accession in firstmaps:
            category='SOURCE_DECLARED_IDENTIFIER_MATCHES_INDEPENDENT_TYPE_CULTURE'
            matches=[mapping['matched_external_type_identifier']]
            alias_unverified=mapping.get('personal_strain_alias_independently_verified') is False
            bridge=mapping.get('genome_accession_bridge_independently_checked',False)
        else:
            category=mapping['source_review_category']
            matches=mapping['independently_defined_reference_identifiers']
            alias_unverified=False
            bridge=bool(mapping.get('accession_string_bridge',{}).get('matched'))
        name_unvalidated=source['species']=='Enterococcus spodopteracolus'
        hold=['CROSS_LABEL_COMPONENT_RELATION_UNRESOLVED','GENOME_IDENTITY_NOT_AUTHENTICATED_BY_SOURCE_REVIEW']
        if alias_unverified:hold.append('PERSONAL_ALIAS_ONLY_LINKED_BY_SUBMISSION_COLLECTION_ASSERTION')
        if name_unvalidated:hold.extend(['NAME_NOT_VALIDLY_PUBLISHED_ICNP','FINAL_PANEL_NOMENCLATURAL_ELIGIBILITY_UNRESOLVED'])
        if category=='NO_INDEPENDENT_TYPE_ANCHOR_ESTABLISHED':hold.append('TYPE_ANCHOR_NOT_ESTABLISHED_NOT_A_NEGATIVE_TYPE_CALL')
        if members[accession]=='ANI_REVIEW_046':hold.append('TEUBERI_LMG_IDENTIFIER_CONFLICT_NOT_NORMALIZED')
        if members[accession] in ('ANI_REVIEW_003','ANI_REVIEW_046'):hold.append('REPEATED_DECLARED_CULTURE_RETENTION_REQUIRES_REVIEW')
        if accession in panel and panel[accession]['species']!=source['species']:hold.append('CURRENT_PANEL_LABEL_DIFFERS_ACCEPTED_SOURCE_REVIEW')
        genomes.append(dict(accession=accession,component_id=members[accession],source_species_label=source['species'],
            biosample=source['biosample'],source_strains=source['raw_strain_values'],source_culture_collections=source['raw_culture_collection_values'],
            original_type_material_flag=source['type_label'],original_type_scope_class=source['type_evidence_class'],
            source_review_category=category,matched_reference_identifiers=matches,
            personal_alias_link_not_independently_verified=alias_unverified,
            external_accession_string_bridge_checked=bridge,
            physical_genome_identity='NOT_AUTHENTICATED_BY_THIS_REVIEW',
            whole_genome_file_not_rehashed_by_this_crosswalk=True,
            current_provisional_panel_member=accession in panel,
            current_provisional_panel_label=panel.get(accession,{}).get('species'),
            biological_QC='READ_ACTUAL_QC_RECEIPTS_NOT_THIS_SOURCE_CROSSWALK',
            unresolved_holds=hold,genome_quality_measurement_permitted=True,
            final_panel_acceptance_granted=False,
            original_source_record_binding=dict(report_sha256=source['report_sha256'],acquisition_receipt_sha256=source['acquisition_receipt_sha256']),
            accepted_source_assessment=mapping))
    component_holds={
        'ANI_REVIEW_003':['Cross-label infantarius/ruminicola relation unresolved; FDAARGOS personal alias unauthenticated; repeated infantarius type-culture retention undecided.','ATCC BAA-102 = DSM22960; ruminicola CNU_G2 is a separate type.'],
        'ANI_REVIEW_027':['Do not collapse valid algida/carnosa names from skani alone; genome identity/QC unresolved.','Lactobacillus algidus is homotypic with Dellaglioa algida; carnosa protologue has ANIb95.1/dDDH63.2 context.'],
        'ANI_REVIEW_046':['LMG21695 versus LMG24695 conflict; SS1998/SS1997 aliases, cross-label relations and repeated-culture retention unresolved.','DSM21459/CG-21 and D7T301/JCM31178 define distinct types; CP017267 accession bridge is identifier-only.'],
        'ANI_REVIEW_054':['Cross-label argentoratensis/plantarum relations unresolved; dm lacks an established type anchor.','Older argentoratensis subspecies/genus wording is homotypic; DSM16365 and plantarum DSM20174 are different types.'],
        'ANI_REVIEW_059':['Spodopteracolus name not validly published; proposed IIL-Cl25 reference is not an authenticated valid-species type genome; eligibility and15-1A relation unresolved.','Mundtii DSM4838 type identifier agrees; LPSN and NCBI agree on proposed personal reference IIL-Cl25.'],
        'ANI_REVIEW_064':['Cross-label mictus/tenax relations unresolved; UMB1016/UMB7049 have no type anchor established; do not equate UMB7049 with UMB3669.','Mictus UMB3440=DSM115699; tenax UMB3669=DSM115700; CP132985 accession bridge is identifier-only.']}
    components=[]
    for component in sorted(set(members.values())):
        rows=[g for g in genomes if g['component_id']==component]
        components.append(dict(component_id=component,accessions=[g['accession'] for g in rows],
            current_source_species_labels=sorted({g['source_species_label'] for g in rows}),
            source_relation_clarified=component_holds[component][1],
            unresolved_final_panel_hold=component_holds[component][0],
            biological_relation='UNRESOLVED',genome_QC_may_proceed=True,
            automatic_relabel_merge_or_prune_admitted=False))
    counts=dict(components=len(components),genomes=len(genomes),
        defined_type_identifier_matches=sum(g['source_review_category']=='SOURCE_DECLARED_IDENTIFIER_MATCHES_INDEPENDENT_TYPE_CULTURE' for g in genomes),
        unvalidated_proposed_reference_identifier_matches=sum('NAME_NOT_VALIDLY_PUBLISHED_ICNP' in g['unresolved_holds'] for g in genomes),
        no_type_anchor_established=sum(g['source_review_category']=='NO_INDEPENDENT_TYPE_ANCHOR_ESTABLISHED' for g in genomes),
        unverified_personal_alias_links=sum(g['personal_alias_link_not_independently_verified'] for g in genomes),
        external_accession_string_bridges=sum(g['external_accession_string_bridge_checked'] for g in genomes),
        physical_genome_authentications=0)
    assert counts==dict(components=6,genomes=18,defined_type_identifier_matches=13,unvalidated_proposed_reference_identifier_matches=1,no_type_anchor_established=4,unverified_personal_alias_links=3,external_accession_string_bridges=2,physical_genome_authentications=0)
    result=dict(schema=1,status='FROZEN_SOURCE_ONLY_HOLDS_NO_FINAL_PANEL_ACCEPTANCE',
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),accepted_source_reviews=checked,
        provisional_panel_binding=dict(path=panelpath.relative_to(ROOT).as_posix(),sha256=panelsha),
        counts=counts,components=components,genomes=genomes,
        downstream_rules=dict(carry_this_manifest_SHA_into_cohort_QC_and_curation=True,
            QC_measurement_allowed_while_source_holds_open=True,
            panel_freeze_requires_explicit_resolution_or_documented_treatment=True,
            source_type_flags_do_not_authenticate_genomes=True,
            missing_type_anchor_is_unknown_not_negative=True,
            no_renaming_selection_pruning_or_biological_acceptance=True),
        source_controller_sha256=sha(Path(__file__)),
        human_summary_path='docs/NOMENCLATURE_TYPE_HOLD_CROSSWALK.md',
        human_summary_sha256=sha(ROOT/'docs/NOMENCLATURE_TYPE_HOLD_CROSSWALK.md'))
    save(OUT/'crosswalk.json',result)
    tsv(OUT/'genomes.tsv',[dict(accession=g['accession'],component_id=g['component_id'],species=g['source_species_label'],
        original_type_flag=g['original_type_material_flag'],source_review_category=g['source_review_category'],
        matched_reference_identifiers='; '.join(g['matched_reference_identifiers']),
        personal_alias_unverified=g['personal_alias_link_not_independently_verified'],
        accession_string_bridge_checked=g['external_accession_string_bridge_checked'],
        unresolved_holds='; '.join(g['unresolved_holds']),panel_accepted=False) for g in genomes])
    tsv(OUT/'components.tsv',[dict(component_id=c['component_id'],accessions='; '.join(c['accessions']),
        source_species='; '.join(c['current_source_species_labels']),source_relation_clarified=c['source_relation_clarified'],
        unresolved_final_panel_hold=c['unresolved_final_panel_hold'],genome_QC_may_proceed=True,panel_accepted=False) for c in components])
    if sha(panelpath)!=panelsha:
        raise RuntimeError('Provisional panel changed during source-only crosswalk creation')
    files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(OUT.iterdir()) if p.is_file()]
    save(OUT/'manifest.json',dict(schema=1,source_only=True,files=files))
    commit=dict(status='FROZEN_SOURCE_HOLD_CROSSWALK_NO_BIOLOGICAL_ACCEPTANCE',
        manifest_sha256=sha(OUT/'manifest.json'),artifacts=len(files),counts=counts,
        accepted_source_manifests=[digest for folder,digest in REVIEWS],panel_unchanged=True)
    save(OUT/'commit.json',commit)
    print(json.dumps(commit))


if __name__=='__main__':
    main()
