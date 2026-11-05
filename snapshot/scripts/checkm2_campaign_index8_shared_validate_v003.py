"""HELD one-search raw/query binding and lossless split. No control comparison or ML."""
from pathlib import Path
import argparse,hashlib,json,math,sys
import checkm2_campaign_index8_common_v003 as c
import checkm2_protein_helpers_v001 as h
import checkm2_batched_search_splitter_v002 as splitter
from checkm2_campaign_index8_shared_producer_v003 import build_argv,no_models


def require_binary_execution(execution,prepared):
    elapsed=execution.get('elapsed_seconds')
    if (execution.get('status')!='UNIT_EXIT0_GROUP_CLOSED'
        or type(execution.get('exit_code'))is not int or execution['exit_code']!=0
        or execution.get('owned_group_empty')is not True or execution.get('remaining_owned_processes')!=[]
        or type(elapsed)not in(int,float)or not math.isfinite(elapsed)or elapsed<0
        or execution.get('declared_unit')!='unit_shared_diamond'):
        raise RuntimeError('One actual shared binary0, known debit and closed group required')
    actual=execution.get('child_identity');original=prepared.get('producer_creation_identity')
    if not isinstance(actual,dict)or not isinstance(original,dict):raise RuntimeError('Actual producer/binary creation identities required')
    for value in(actual,original):
        if(type(value.get('pid'))is not int or value['pid']<=0 or type(value.get('creation_ticks'))is not int
           or value['creation_ticks']<=0 or not isinstance(value.get('boot_id'),str)or not value['boot_id']):
            raise RuntimeError('Malformed producer/binary creation identity')
    if any(actual[k]!=original[k]for k in('pid','creation_ticks','boot_id')):
        raise RuntimeError('The observed binary is not the same exec-replaced producer')
    if type(prepared.get('producer_pid_before_exec'))is not int or prepared['producer_pid_before_exec']!=actual['pid']:
        raise RuntimeError('Prepared producer PID differs from the real shared binary unit')
    return elapsed


def expected_query_inventory(query_inputs,proteins_by_accession):
    names=[x['accession']for x in query_inputs]
    if not 2<=len(names)<=22 or len(set(names))!=len(names):raise RuntimeError('Distinct fresh/control query members required')
    roles=[x.get('role')for x in query_inputs]
    if not 1<=roles.count('FRESH')<=20 or not 1<=roles.count('SEARCH_ONLY_CONTROL')<=2 or any(x not in('FRESH','SEARCH_ONLY_CONTROL')for x in roles):
        raise RuntimeError('One to20 fresh and one/two control query roles required')
    inventory={}
    for item in query_inputs:
        acc=item['accession'];proteins=proteins_by_accession[acc]
        if not proteins:raise RuntimeError('Empty own FAA query member')
        for protein in proteins:
            primary=protein['id'];sequence=protein['sequence']
            if not primary or '\u03a9'in primary or any(x.isspace()for x in primary):raise RuntimeError('Ambiguous original primary key')
            key=acc+'\u03a9'+primary
            if key in inventory:raise RuntimeError('Duplicate author key would overwrite a query')
            inventory[key]={'accession':acc,'length':len(sequence),'sequence_sha256':hashlib.sha256(sequence.encode('ascii')).hexdigest()}
    return names,inventory


def require_query_inventory(expected,actual):
    if list(expected)!=list(actual)or expected!=actual:
        raise RuntimeError('Merged query IDs/order/sequences do not equal admitted original FAAs')


def scan_merged_raw(path,inventory):
    rows=0
    with Path(path).open(encoding='utf-8',newline='')as handle:
        for line in handle:
            _,fields=splitter.validate_row(line,inventory)
            reference,separator,annotation=fields[1].partition('~')
            if not separator or not reference or not annotation:
                raise RuntimeError('Original full reference~annotation target required')
            rows+=1
    return rows


def main(a):
    request_path=c.path(a.request)
    if c.sha(request_path)!=a.request_sha256:raise RuntimeError('Trusted shared validation request changed')
    request=c.read(request_path)
    if request.get('request_schema')!='TREE2_CAMPAIGN_SHARED_DIAMOND_REQUEST_V003':raise RuntimeError('Wrong shared raw request schema')
    plan,recipe,_=c.request_gate(request);h.runtime_required();no_models()
    prefix=c.path(request['runtime_prefix'])
    if Path(sys.executable).resolve()!=(prefix/'bin/python').resolve():raise RuntimeError('Accepted runtime Python required')
    output=c.path(a.output);inventory_path=output.with_name('query_inventory.json');destination=output.parent/'shards'
    if output.exists()or inventory_path.exists()or destination.exists():raise FileExistsError('Shared validator outputs exist; no implicit retry/overwrite')
    prepared_path=output.with_name('search_exec_prepared.json');prepared_ref=splitter._file_ref(c.R,prepared_path);prepared=c.read(prepared_path)
    expected_selected={x['accession']:x['selected_faa']for x in request['query_inputs']}
    if (prepared.get('status')!='MERGED_AUTHOR_QUERY_PREPARED_NO_SEARCH_EXIT_YET'
        or prepared.get('request_sha256')!=a.request_sha256 or prepared.get('query_inputs')!=request['query_inputs']
        or prepared.get('selected_faas')!=expected_selected or prepared.get('database')!=request['database']
        or prepared.get('diamond_binary')!=request['diamond_binary']or prepared.get('no_model_modules')!=[]):
        raise RuntimeError('Prepared merged query/request/FAA/tool provenance differs')
    binary_path=c.path(a.binary_execution)
    if c.sha(binary_path)!=a.binary_execution_sha256:raise RuntimeError('Trusted global binary execution changed')
    binary_ref=c.row(binary_path);execution=c.read(binary_path)
    require_binary_execution(execution,prepared)
    if not c.unit_closed(execution):raise RuntimeError('Shared binary unit closure is unavailable')
    proteins={}
    for item in request['query_inputs']:
        acc=item['accession'];faa=splitter._bind(c.R,item['selected_faa'])
        annotation=c.read(c.bind(item['annotation_receipt']))
        parsed=h.parse_fasta(faa.read_text(encoding='utf-8'),h.AA)
        if (faa.name!=acc+'.faa' or annotation.get('accession')!=acc
            or annotation.get('faa_sha256')!=item['selected_faa']['sha256']
            or annotation.get('protein_sequences')!=h.sequence_receipt(parsed)):
            raise RuntimeError('Exact original FAA/header/sequence annotation association required')
        proteins[acc]=parsed
    names,expected=expected_query_inventory(request['query_inputs'],proteins)
    query=prepared['query'];splitter._bind(c.R,query)
    actual_names,actual,_=splitter.query_inventory(c.R,query,names)
    if actual_names!=names:raise RuntimeError('Declared query member order differs')
    require_query_inventory(expected,actual)
    raw_path=c.path(request['search_output'])/'diamond_output/DIAMOND_RESULTS.tsv'
    if {p.name for p in raw_path.parent.iterdir()}!={'DIAMOND_RESULTS.tsv'}:raise RuntimeError('Exactly one new merged raw result required')
    merged_raw=splitter._file_ref(c.R,raw_path)
    defaults={'DIAMOND_QUERY_COVER':80,'DIAMOND_SUBJECT_COVER':80,'DIAMOND_PERCENT_ID':30,'DIAMOND_EVALUE':1e-5}
    expected_argv=build_argv(c.bind(request['diamond_binary']),c.path(query['path']),raw_path,
        c.path(request['database']['path']),c.path(request['durable_scratch'])/'diamond_work',defaults)
    if prepared['argv']!=expected_argv:raise RuntimeError('Original fixed-index8 scientific argv differs')
    for source in recipe['author_sources']:
        if c.sha(prefix/'lib/python3.12/site-packages/checkm2'/Path(source['path']).name)!=source['sha256']:
            raise RuntimeError('Original author source changed')
    origins=prepared.get('actual_author_origins')
    if not isinstance(origins,dict)or not origins or any(not Path(v).is_relative_to(prefix)for v in origins.values()):
        raise RuntimeError('Author module origin outside the accepted prefix')
    rows=scan_merged_raw(raw_path,actual)
    inventory_value={'query_fasta':query,'declared_accessions':names,'queries':actual,'query_count':len(actual),
        'exact_original_FAA_query_order_and_sequences':True}
    c.save(inventory_path,inventory_value)
    split_commit=splitter.split_search(project_root=c.R,query_fasta=query,merged_tsv=merged_raw,
        search_execution=binary_ref,declared_accessions=names,destination=destination)
    split=c.read(c.bind(split_commit))
    if (split['inputs']['search_execution']!=binary_ref or split['search_debit']['actual_unit_count']!=1
        or sum(x['rows']for x in split['shards'])!=rows or split['field_values_and_multiplicity_untouched']is not True):
        raise RuntimeError('Global split lost its unique actual-search or row-multiplicity binding')
    for item in request['query_inputs']:
        splitter._bind(c.R,item['selected_faa']);c.bind(item['annotation_receipt']);c.bind(item['annotation_unit_execution']);c.bind(item['annotation_commit'])
    splitter._bind(c.R,query);splitter._bind(c.R,merged_raw);c.bind(binary_ref);splitter._bind(c.R,prepared_ref)
    if c.sha(request_path)!=a.request_sha256:raise RuntimeError('Request changed during shared validation')
    no_models()
    c.save(output,{'status':'GLOBAL_SHARED_SEARCH_SPLIT_VALIDATED_PENDING_UNIT_CLOSURE',
        'request_sha256':a.request_sha256,'split_commit':split_commit,'merged_query':query,'merged_raw':merged_raw,
        'query_inventory':c.row(inventory_path),'selected_faas':expected_selected,'query_inputs':request['query_inputs'],
        'binary_execution':binary_ref,'search_exec_prepared':prepared_ref,'producer_creation_identity':prepared['producer_creation_identity'],
        'raw_rows':rows,'fresh_input_count':c.COUNT,'search_only_control_count':len(plan['controls']),
        'global_binary_execution_receipts':1,'per_row_binary_exit_or_debit_invented':False,
        'control_comparison':'NOT_PERFORMED_REQUIRES_FIRST_OWN_ML_FEATURE_CHECKPOINT',
        'numerical_model_or_genome_QC_validation_performed':False,'no_model_modules':no_models()})


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in('request','request-sha256','output','binary-execution','binary-execution-sha256'):
        parser.add_argument('--'+name,required=True)
    main(parser.parse_args())
