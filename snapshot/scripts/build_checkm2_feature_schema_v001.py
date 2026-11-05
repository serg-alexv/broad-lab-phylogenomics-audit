"""Derive an immutable ordered schema using stdlib-only original-source/data reads."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import os

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'tools/checkm2_runtime_pkgs/checkm2-1.1.0-pyhdfd78af_2'
PKG=CACHE/'site-packages/checkm2'
OUT=ROOT/'metadata/checkm2_feature_schema_v001.json'
SOURCES=['main.py','predictQuality.py','metadata.py','diamond.py','keggData.py',
         'modelProcessing.py','modelPostprocessing.py','defaultValues.py','sequenceClasses.py',
         'data/feature_ordering.json','data/kegg_path_category_mapping.json','data/module_definitions.json']


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def json_hash(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,separators=(',',':')).encode('utf-8')).hexdigest()


def main():
    records=[];metadata=CACHE/'info/paths.json'
    paths={row['_path']:row for row in json.loads(metadata.read_text())['paths']}
    for relative in SOURCES:
        path=PKG/relative;official='site-packages/checkm2/'+relative;digest=sha(path)
        if digest!=paths[official]['sha256'] or path.stat().st_size!=paths[official]['size_in_bytes']:
            raise RuntimeError('Original producer/source data payload differs:'+relative)
        records.append(dict(cached_path=path.relative_to(ROOT).as_posix(),official_package_path=official,
            runtime_project_relative_path='tools/checkm2_env/lib/python3.12/site-packages/checkm2/'+relative,
            bytes=path.stat().st_size,sha256=digest,official_cached_payload_match=True))
    order=json.loads((PKG/'data/feature_ordering.json').read_text())
    modules=json.loads((PKG/'data/module_definitions.json').read_text())
    mapping=json.loads((PKG/'data/kegg_path_category_mapping.json').read_text())
    assert order['Metadata']==list('ACDEFGHIKLMNPQRSTVWY')+['AALength','CDS']
    assert list(modules)==order['KO_Modules']
    assert all(len(value)==len(set(value)) for value in order.values())
    groups=[];features=[];offset=0;kos=set(order['KO_Genes']);exceptions=[]
    for group in ('Metadata','KO_Genes','KO_Pathways','KO_Modules','KO_Categories'):
        names=list(modules) if group=='KO_Modules' else order[group]
        count=len(names);counts=group in ('Metadata','KO_Genes')
        groups.append(dict(name=group,count=count,model_start_zero_based=offset,model_stop_exclusive=offset+count,
            dataframe_start_zero_based=offset+1,dataframe_stop_exclusive=offset+count+1,
            ordered_names_sha256=json_hash(names),logical_type='NONNEGATIVE_INTEGER' if counts else 'MEMBERSHIP_FRACTION',
            allowed_numeric_domain='finite >=0 and integral' if counts else 'finite within inclusive[0,1]',
            nominal_raw_dtype='integer numeric' if counts else 'real numeric',
            validator_storage_rule='real numeric dtype; reject bool/complex/object/string/missing values; counts must be integral',
            actual_model_dtype='float64 after unchanged producer cast'))
        features.extend(names);offset+=count
    assert offset==21241 and len(set(features))==21241
    denominator_records={}
    for group in ('KO_Pathways','KO_Categories'):
        counts=Counter(mapping[group].values())
        assert all(counts[name]>0 for name in order[group])
        assert set(mapping[group])==set(mapping['Kegg_ID'])
        assert all(ko in kos for ko in mapping['Kegg_ID'].values())
        denominator_records[group]={name:counts[name] for name in order[group]}
    denominators={}
    for name,values in modules.items():
        missing=[value for value in values if value not in kos]
        duplicates=len(values)-len(set(values))
        denominators[name]=len(values)
        assert values
        if missing or duplicates:
            exceptions.append(dict(feature=name,original_denominator=len(values),
                retained_membership_occurrences=sum(value in kos for value in values),
                missing_KO_membership_occurrences=missing,duplicate_membership_occurrences=duplicates,
                original_algorithm_preserves_list_multiplicity_and_pre_filter_denominator=True))
    assert sum(len(row['missing_KO_membership_occurrences']) for row in exceptions)==14
    assert sum(row['duplicate_membership_occurrences'] for row in exceptions)==63
    columns=['Name',*features]
    schema=dict(schema='TREE2_CHECKM2_ORDERED_FEATURE_SCHEMA_V1',status='STATIC_SOURCE_ONLY_NO_MODEL_GENOME_OR_FEATURE_PICKLE_READ',
        checkm2_version='1.1.0',checkm2_package_build='pyhdfd78af_2',
        source_files_and_assets=records,cached_package_paths_metadata_sha256=sha(metadata),
        expected_single_genome_dataframe_shape=[1,21242],expected_model_matrix_shape=[1,21241],
        ordered_dataframe_columns=columns,ordered_model_features=features,
        ordered_dataframe_columns_sha256=json_hash(columns),ordered_model_features_sha256=json_hash(features),
        order_hash_serialization='UTF8 JSON list; ensure_ascii=False; compact comma/colon separators; no trailing newline',
        groups=groups,unique_names=True,module_definition_order_matches_feature_order_asset=True,
        name_column=dict(index=0,logical_type='text',value_rule='exact versioned accession from bound input plan',
            raw_pandas_dtype='NOT_ASSERTED_FROM_STATIC_SOURCE',excluded_from_model_input=True),
        metadata_semantics=dict(amino_acid_counts='counts of the twenty named uppercase letters in parsed protein strings',
            AALength='sum of full parsed protein-string lengths, including preserved stop/ambiguous characters',
            CDS='number of parsed unique protein identifiers; duplicate input IDs must be rejected separately',
            AA_counts_sum_may_be_less_than_AALength=True,do_not_normalize_case_or_remove_stops=True),
        KO_gene_semantics='retained DIAMOND annotation-row counts after default-KO filter, grouped by genome and KO',
        pathway_category_semantics='proportion of mapped membership occurrences present after clipping KO counts above1 to1',
        pathway_category_denominators=denominator_records,module_original_denominators=denominators,
        module_semantics='original membership occurrences present divided by original list length before missing-KO filtering; no deduplication',
        module_exceptions=exceptions,module_missing_KO_occurrences=14,module_duplicate_membership_occurrences=63,
        model_input_recipe='feature_vectors.iloc[:,1:].values.astype(float)',
        general_models_input='full unscaled21241 float64 matrix',
        scaler_input='full21241 float64 matrix',
        neural_input=dict(scaled=True,feature_slice_start=0,feature_slice_stop_exclusive=20021,shape=[1,20021,1]),
        cosine_input=dict(scaled=True,feature_slice_start=0,feature_slice_stop_exclusive=20021),
        selector=dict(model_feature_zero_based=20,name='AALength',ratio='AALength / mean(general,specific completeness)'),
        dbg_vectors=dict(cli_flag='--dbg_vectors',default=False,algorithm_options_changed=False,
            phase='after each feature chunk has undergone model/postprocessing calculations',
            output_pattern='output/feature_vectors_<chunk_counter>.pkl',first_chunk=1,
            serialization='pandas.DataFrame.to_pickle(protocol=4)',dump_representation='unscaled mixed-numeric DataFrame with Name first',
            additional_serialization_and_IO_still_subject_to_original_resource_gates=True),
        parser_requirements=['bound controlled artifact SHA before reading pickle','one exact expected Name row',
            'exact full ordered columns; no duplicate/missing/extra/reordered columns',
            'numeric finite values only; nonnegative integral counts; membership fractions0..1',
            'reject nulls and nonnumeric/bool/complex values; do not fill missing columns with zero',
            'canonical ordered float64 values are distinct from raw pickle bytes',
            'no model-accuracy or biological acceptance from schema or vectors alone'],
        protein_auto_report_columns=['Name','Completeness','Contamination','Completeness_Model_Used','Additional_Notes'],
        extensionless_copy_warning='Use input-plan accession; splitext(extensionless versioned accession) would strip its assembly version.',
        no_scientific_import_model_genome_FAA_or_pickle_read=True,no_author_code_or_data_modified=True,
        builder_sha256=sha(Path(__file__)),human_summary_sha256=sha(ROOT/'docs/CHECKM2_ORDERED_FEATURE_SCHEMA_V001.md'))
    raw=(json.dumps(schema,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    if OUT.exists():
        if OUT.read_bytes()!=raw:raise RuntimeError('Frozen schema differs; use a new explicit version')
        status='VERIFIED_IMMUTABLE_SOURCE_SCHEMA_REUSE_NO_RUNTIME_READ'
    else:
        temporary=OUT.with_suffix('.pending')
        with temporary.open('xb') as handle:
            handle.write(raw);handle.flush();os.fsync(handle.fileno())
        os.replace(temporary,OUT);status='CREATED_STATIC_ORDERED_FEATURE_SCHEMA'
    digest=hashlib.sha256(raw).hexdigest();checksum=OUT.with_suffix('.sha256')
    expected=(digest+'  '+OUT.name+'\n').encode('ascii')
    if checksum.exists() and checksum.read_bytes()!=expected:raise RuntimeError('Frozen schema checksum sidecar differs')
    if not checksum.exists():
        temp=checksum.with_suffix('.pending')
        with temp.open('xb') as handle:handle.write(expected);handle.flush();os.fsync(handle.fileno())
        os.replace(temp,checksum)
    print(json.dumps(dict(status=status,path=OUT.relative_to(ROOT).as_posix(),sha256=digest,bytes=len(raw),
        columns=len(columns),numeric_features=len(features),ordered_columns_sha256=json_hash(columns))))


if __name__=='__main__':main()
