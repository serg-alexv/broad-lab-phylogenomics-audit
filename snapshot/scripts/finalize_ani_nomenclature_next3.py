"""Commit a bounded source-only assessment, preserving accepted inputs verbatim."""
from pathlib import Path
import datetime
import hashlib
import json
import os

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/sequence_qc/d64e016face251f1/nomenclature_source_review/priority1_next3_20261027_v1'
INPUT = ROOT / 'analysis/sequence_qc/d64e016face251f1/curation_source_review/3fa9c62b41bb4a54'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def save(path, obj):
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open('w', encoding='utf-8') as handle:
        json.dump(obj, handle, indent=2)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def main():
    if (OUT / 'commit.json').exists():
        raise RuntimeError('Committed output is immutable; use the review controller for verification')
    inputs = read(OUT / 'accepted_inputs.json')
    assert inputs['component_ids'] == ['ANI_REVIEW_054','ANI_REVIEW_059','ANI_REVIEW_064']
    source_receipts = {p.stem: read(p) for p in (OUT / 'sources').glob('*.json')}
    assert len(source_receipts) == 19 and all(r['source_readable'] for r in source_receipts.values())
    articles = source_receipts['primary_revisions_pubmed_xml']['articles']
    assert {a['pmid'] for a in articles} == {'32250238','33112225','37433981','37755156','38651909'}
    assert all(len(a['doi']) == 1 for a in articles)
    summary = read(OUT / 'source_retrieval_summary.json')
    summary['sources'] = [source_receipts[row['source_id']] for row in summary['sources']]
    summary['parser_metadata_normalized_before_commit'] = True
    save(OUT / 'source_retrieval_summary.json', summary)
    member_ids = {r['accession'] for r in inputs['genome_source_records']}
    pairs = [r for r in read(INPUT / 'pair_reviews.json') if r['reference'] in member_ids and r['query'] in member_ids]
    assert len(pairs) == 6
    save(OUT / 'existing_pair_evidence.json', dict(source_only=True, no_recomputation=True,
         input_pair_reviews_sha256=sha(INPUT / 'pair_reviews.json'), pairs=pairs))

    typed = 'SOURCE_DECLARED_IDENTIFIER_MATCHES_INDEPENDENT_TYPE_CULTURE'
    noanchor = 'NO_INDEPENDENT_TYPE_ANCHOR_ESTABLISHED'
    proposed = 'PROPOSED_TYPE_REFERENCE_IDENTIFIER_AGREES_NAME_NOT_VALIDLY_PUBLISHED'
    genomes = [
        ('GCF_002220175.1','dm',noanchor,[],['plantarum_lpsn']),
        ('GCF_003641165.1','DSM 16365',typed,['DSM 16365','CIP 108320','CCUG 50787','JCM 16169','DKO 22'],['argentoratensis_lpsn','argentoratensis_dsm','argentoratensis_jcm16169','argentoratensis_ncbi']),
        ('GCF_014131735.1','DSM 20174',typed,['DSM 20174','ATCC 14917','CIP 103151','JCM 1149'],['plantarum_lpsn','plantarum_dsm','plantarum_ncbi']),
        ('GCF_002813755.1','DSM 4838',typed,['DSM 4838','ATCC 43186','MUTK 559','NCDO 2375'],['mundtii_lpsn','mundtii_dsm','mundtii_ncbi']),
        ('GCF_013394305.1','15-1A',noanchor,[],['mundtii_lpsn']),
        ('GCF_030441955.1','IIL-Cl25',proposed,['IIL-Cl25'],['spodopteracolus_lpsn','spodopteracolus_ncbi']),
        ('GCF_003286595.3','UMB3440',typed,['UMB3440','DSM 115699','ATCC TSD-301','CCUG 76532','NR-58629'],['mictus_lpsn','mictus_dsm','mictus_ncbi']),
        ('GCF_003286735.3','UMB1016',noanchor,[],['mictus_lpsn']),
        ('GCF_008726475.3','UMB7049',noanchor,[],['tenax_lpsn','tenax_dsm'])]
    assessments = []
    cached = {row['accession']:row for row in inputs['genome_source_records']}
    for accession, strain, category, aliases, source_ids in genomes:
        row = cached[accession]
        assessment = dict(accession=accession, cached_strain=strain,
            cached_species_label=row['species'], biosample=row['biosample'],
            cached_type_label=row['type_label'], cached_type_evidence_class=row['type_evidence_class'],
            source_review_category=category,
            independently_defined_reference_identifiers=aliases,
            independently_authenticated_genome_or_physical_material=False,
            whole_genome_rehashed_by_this_review=False,
            source_receipts=[dict(source_id=key, path='sources/'+key+'.json', sha256=sha(OUT/'sources'/(key+'.json'))) for key in source_ids],
            accepted_report_sha256=row['report_sha256'], accepted_acquisition_receipt_sha256=row['acquisition_receipt_sha256'])
        if accession == 'GCF_003641165.1':
            assessment['scope_resolution'] = 'Older Lactobacillus plantarum subsp. argentoratensis BioSample wording is a homotypic synonym of current argentoratensis species; it is not the plantarum nominate type.'
        if accession == 'GCF_014131735.1':
            assessment['scope_resolution'] = 'Older Lactobacillus plantarum wording is a homotypic genus combination; DSM20174 agrees with current plantarum type.'
        if accession == 'GCF_030441955.1':
            assessment.update(name_validly_published_under_ICNP=False,
                lpsn_still_lists_nomenclatural_type_identifier=True,
                verified_repository_deposit_alias=None,
                absence_of_verified_deposit_does_not_prove_no_deposit=True)
        if accession == 'GCF_003286595.3':
            assessment['accession_string_bridge'] = dict(external_source='mictus_lpsn', external_accession='CP132985',
                cached_first_header=row['cached_first_fasta_header_read_only'], matched=True,
                external_sequence_field_label='16S rRNA gene', sequence_feature_not_validated=True,
                dsm_catalogue_accession_match=False, independent_physical_authentication=False)
        if accession == 'GCF_008726475.3':
            assessment['scope_resolution'] = 'UMB7049 is not the separately specified tenax type identifier UMB3669; no equivalence was established.'
        assessments.append(assessment)

    decisions = [
        dict(component_id='ANI_REVIEW_054', accepted_names=['Lactiplantibacillus argentoratensis','Lactiplantibacillus plantarum'],
             source_relation='Separate current correct names; older argentoratensis subspecies and genus combinations are homotypic synonyms of argentoratensis, not a merger of current species.',
             existing_cross_label_ANI=[95.59,95.83], relation_resolution='OLD_TYPE_WORDING_EXPLAINED_CROSS_LABEL_BIOLOGY_UNRESOLVED',
             primary_revisions_pmids=['32250238','33112225']),
        dict(component_id='ANI_REVIEW_059', accepted_names=['Enterococcus mundtii'], unvalidated_preferred_name='Enterococcus spodopteracolus',
             source_relation='IIL-Cl25 proposed/source reference identifier agrees in LPSN and NCBI, but the name is not validly published; no valid-species authenticated type-genome inference.',
             existing_cross_label_ANI=[95.34,96.46], relation_resolution='PUBLICATION_STATUS_QUALIFIED_BIOLOGY_AND_ELIGIBILITY_UNRESOLVED',
             primary_revisions_pmids=['37433981']),
        dict(component_id='ANI_REVIEW_064', accepted_names=['Aerococcus mictus','Aerococcus tenax'],
             source_relation='Separate validly published species from the urinae-complex revision; different type cultures. Reviewed mictus UMB3440 matches type identifier; reviewed tenax UMB7049 is not a proved type alias.',
             existing_cross_label_ANI=[95.15,95.05], relation_resolution='TYPE_SCOPE_CLARIFIED_CROSS_LABEL_BIOLOGY_UNRESOLVED',
             primary_revisions_pmids=['37755156','38651909'])]
    save(OUT / 'decisions.json', dict(source_only=True, genome_source_assessments=assessments,
        component_assessments=decisions, global_decision='NO_RENAMING_SELECTION_PRUNING_OR_BIOLOGICAL_ACCEPTANCE',
        unresolved_components=[r['component_id'] for r in decisions],
        unknown_is_negative=False, numerical_protologue_thresholds_not_independently_verified=True))
    save(OUT / 'summary.json', dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status='SOURCE_ONLY_REVIEW_COMPLETE_WITH_UNRESOLVED_RELATIONS', components=3, genomes=9,
        independently_defined_type_identifier_matches=4,
        proposed_reference_identifier_match_unvalidated_name=1, no_type_anchor_established=4,
        independently_authenticated_genomes=0, biological_relations_unresolved=3,
        primary_sources=19, primary_sources_readable=19, reused_accepted_genome_source_records=9,
        external_receipts_reused=0, no_exact_prior_external_URL_overlap=True,
        no_new_genomes=True, no_biological_computation=True,
        no_genome_label_selection_pruning_or_QC_changes=True))
    tracked = ['scripts/review_ani_nomenclature_next3.py','scripts/finalize_ani_nomenclature_next3.py',
               'docs/ANI_NOMENCLATURE_NEXT3_REVIEW.md']
    save(OUT / 'review_provenance.json', dict(source_only=True,
        controller_and_assessment_sources=[dict(path=path,sha256=sha(ROOT/path)) for path in tracked],
        accepted_input_manifest_sha256=inputs['input_manifest_sha256'],
        preserved_first3_manifest_sha256=inputs['first3_manifest_sha256'],
        primary_doi_metadata_correction='Corrected before commit; cited-reference DOIs are retained separately and are not attributed to the primary article.',
        frozen_output_rule='Manifest plus atomic commit; committed resume verifies bytes and SHA without fetching.'))
    files = [dict(path=p.relative_to(OUT).as_posix(), bytes=p.stat().st_size, sha256=sha(p))
             for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in ('manifest.json','commit.json')]
    save(OUT / 'manifest.json', dict(schema=1, source_only=True, files=files))
    committed = dict(status='COMMITTED_SOURCE_ONLY_REVIEW_WITH_UNRESOLVED_RELATIONS',
         created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
         manifest_sha256=sha(OUT/'manifest.json'), artifacts=len(files),
         biological_acceptance=False, no_label_selection_pruning_change=True,
         preserved_first3_manifest_sha256=inputs['first3_manifest_sha256'])
    save(OUT / 'commit.json', committed)
    print(json.dumps(committed))


if __name__ == '__main__':
    main()
