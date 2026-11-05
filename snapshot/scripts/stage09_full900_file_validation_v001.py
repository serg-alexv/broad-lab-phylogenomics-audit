"""Independent saved-output arithmetic; no inference, model, caller or subprocess."""
from pathlib import Path
import collections,csv,gc,hashlib,json,math,re
import local_tree2_dispatcher as b
from fullpanel_gene_metrics_v001 import parse_newick


def tree_splits(root,index):
    """Canonical unrooted bit splits, counted once even at a degree-two root."""
    full=(1<<len(index))-1; splits={};tips={}
    def visit(node,is_root=False):
        if 'leaf' in node:
            mask=1<<index[node['leaf']];tips[node['leaf']]=node.get('branch_length')
        else:
            mask=0
            for child in node['children']:mask|=visit(child)
        if not is_root:
            key=min(mask,full^mask)
            if key:
                value={'side_taxa':min(mask.bit_count(),len(index)-mask.bit_count()),'label':node.get('internal_label'),'length':node.get('branch_length')}
                if key not in splits:splits[key]=value
                elif value['label'] is not None and splits[key]['label'] is None:splits[key]=value
        return mask
    assert visit(root,True)==full
    return splits,tips


def close_percent(actual,reported):
    value=float(reported);assert math.isfinite(value) and 0<=value<=100
    decimals=len(reported.split('.')[1]) if '.' in reported else 0
    return abs(actual-value)<=0.5*10**(-decimals)+1e-7


def fixtures():
    expected={'a','b','c','d'};index={v:i for i,v in enumerate(sorted(expected))}
    first,_=tree_splits(parse_newick('((a:1,b:1)80/100:1,c:1,d:1);',expected),index)
    second,_=tree_splits(parse_newick('(a:1,b:1,(c:1,d:1):1);',expected),index)
    assert set(first)==set(second) and len(first)==5
    rooted,_=tree_splits(parse_newick('((a:1,b:1):1,(c:1,d:1):1);',expected),index)
    assert set(rooted)==set(first)
    assert close_percent(94.7,'95') and not close_percent(94.4,'95')
    try:parse_newick('(a:1,b:1,c:1,c:1);',expected)
    except ValueError:pass
    else:raise AssertionError('Duplicate/missing-tip negative control did not reject')
    return {'unrooted_complement_and_root_placement':'PASS','duplicate_tip_rejected':'PASS','published_precision_arithmetic':'PASS'}


def validate(R,p,output,guard,publish):
    fixture=fixtures();snapshot=b.read(b.bind(R,p['computed_snapshot']));closure=b.read(b.bind(R,p['production_closure']))
    assert closure['all_owned_groups_namespaces_FDs_and_four_leases_closed'] is True
    execution=b.read(b.bind(R,closure['actual_IQTREE_execution']))
    assert execution['actual_exit_code']==0 and execution['actual_child_waited_and_reaped'] and execution['group_closed']
    assert execution['error'] is None and not execution['remaining_owned_identities'] and not execution['remaining_group_members']
    production=b.read(b.bind(R,p['production_plan']));computed=b.read(b.bind(R,p['production_COMPUTED']))
    assert computed['plan']==p['production_plan'] and computed['execution']==closure['actual_IQTREE_execution']
    for row in snapshot['files']:
        guard();b.bind(R,row['original']);b.bind(R,row['copy'])
        assert row['original']['sha256']==row['copy']['sha256'] and row['original']['bytes']==row['copy']['bytes']
    assert {x['original']['path'] for x in snapshot['files']}=={x['path'] for x in computed['artifacts']}
    paths={Path(row['copy']['path']).suffix:b.bind(R,row['copy']) for row in snapshot['files']}
    labels=set(b.bind(R,p['accessions']).read_text().splitlines());assert len(labels)==900
    index={x:i for i,x in enumerate(sorted(labels))};full=(1<<900)-1
    ml=parse_newick(paths['.treefile'].read_text(),labels);consensus=parse_newick(paths['.contree'].read_text(),labels)
    ml_splits,tips=tree_splits(ml,index);con_splits,_=tree_splits(consensus,index)
    ml_internal={k:v for k,v in ml_splits.items() if v['side_taxa']>1};con_internal={k:v for k,v in con_splits.items() if v['side_taxa']>1}
    assert len(ml_internal)==897,'Expected fully bifurcating unrooted900-tip ML tree'
    assert all(v['length'] is not None and math.isfinite(v['length']) and v['length']>=0 for v in ml_splits.values())
    report=paths['.iqtree'].read_text();log=paths['.log'].read_text();stock=b.bind(R,p['production_stdout']).read_text()
    assert 'Input data: 900 sequences with 13071 amino-acid sites' in report
    assert 'Model of substitution: LG+F+G4' in report and 'Random seed number: 20261029' in report
    assert 'SH-aLRT support (%) / ultrafast bootstrap support (%)' in report and 'Tree is UNROOTED' in report
    likelihood=float(re.search(r'Log-likelihood of the tree:\s*([-+0-9.eE]+)',report)[1]);assert math.isfinite(likelihood)
    assert 'Testing tree branches by SH-like aLRT with 1000 replicates...' in stock
    assert stock.index('Testing tree branches by SH-like aLRT with 1000 replicates...')<stock.index('Creating bootstrap support values...')<stock.index('Analysis results written to:')
    command=b.read(b.bind(R,p['production_command']))['argv']
    expected=[production['iqtree'],'-s','/mnt/c/'+str(R/production['alignment']['path']).replace('\\','/')[3:],'--seqtype','AA','-m','LG+F+G4','-T','1','--mem','500M','--safe','--seed','20261029','--cptime','30','-B','1000','--alrt','1000','--bnni','--boot-trees','--prefix','/mnt/c/'+str(R/production['prefix']).replace('\\','/')[3:]]
    assert command==expected,'Actual scientific argv differs from admitted exact settings'
    counts=collections.Counter();replicates=0;range_splits=[]
    with paths['.ufboot'].open() as stream:
        for line in stream:
            if not line.strip():continue
            guard();assert len(line.encode('utf-8'))<=1048576
            tree=parse_newick(line,labels);splits,_=tree_splits(tree,index);counts.update(splits.keys());replicates+=1;range_splits.append(len(splits))
            assert len(counts)<=100000,'Refuse unbounded validation allocation; no split discarded'
            if replicates%10==0:gc.collect()
            if replicates%25==0:publish('Reconstructing exact1000 bootstrap split frequencies',replicates,1000)
    assert replicates==1000
    nexus=paths['.nex'].read_text();taxa_text=nexus.split('TAXLABELS',1)[1].split(';',1)[0]
    taxa={int(i):name for i,name in re.findall(r"\[(\d+)\]\s*'([^']+)'",taxa_text)}
    assert set(taxa)==set(range(1,901)) and set(taxa.values())==labels
    declared=int(re.search(r'nsplits=(\d+)',nexus)[1]);matrix=nexus.split('MATRIX',1)[1].split(';',1)[0];weights={}
    for line in matrix.splitlines():
        if not line.strip():continue
        match=re.fullmatch(r'\s*([-+0-9.eE]+)\s+((?:\d+\s*)+),\s*',line);assert match,'Unsupported/malformed NEXUS split record'
        numbers=list(map(int,match[2].split()));assert len(numbers)==len(set(numbers)) and all(n in taxa for n in numbers)
        mask=0
        for number in numbers:mask|=1<<index[taxa[number]]
        key=min(mask,full^mask);assert key and key not in weights
        weight=float(match[1]);assert math.isfinite(weight) and 0<=weight<=100
        weights[key]=weight
    assert len(weights)==declared and set(counts)<=set(weights)
    for key,value in weights.items():assert abs(value-counts[key]/10)<=1e-6,'NEXUS weight differs from independently counted final bootstrap trees'
    branch_rows=[];sh=[];uf=[]
    for key,value in ml_internal.items():
        label=value['label'];assert isinstance(label,str) and re.fullmatch(r'[-+0-9.]+/[-+0-9.]+',label)
        first,second=label.split('/');a=float(first);z=float(second);assert math.isfinite(a) and 0<=a<=100
        assert close_percent(counts[key]/10,second),'ML UFBoot label differs from raw replicate frequency at published precision'
        sh.append(a);uf.append(z)
        branch_rows.append({'split_sha256':hashlib.sha256(key.to_bytes(113,'big')).hexdigest(),'side_taxa':value['side_taxa'],'branch_length':value['length'],'SH_aLRT':a,'reported_UFBoot':z,'reconstructed_UFBoot_count':counts[key],'reconstructed_UFBoot_percent':counts[key]/10})
    for key,value in con_internal.items():
        assert value['label'] is not None and close_percent(counts[key]/10,value['label']),'Consensus support differs from raw replicate frequency'
    # Reconstruct matrix dimensions and expose missingness without biological exclusions.
    alignment=b.bind(R,p['alignment']);seqs={};current=None
    with alignment.open() as stream:
        for line in stream:
            if line.startswith('>'):current=line[1:].strip().split()[0];assert current not in seqs;seqs[current]=[]
            elif line.strip():assert current is not None;seqs[current].append(line.strip())
    assert set(seqs)==labels
    missing=[]
    for name,parts in seqs.items():
        seq=''.join(parts);assert len(seq)==13071
        missing.append({'accession':name,'gap_or_unknown_columns':sum(seq.count(x) for x in '-.?X'),'columns':13071})
    del seqs;gc.collect();guard()
    with (output/'branch_support_reconstruction.tsv').open('x',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(branch_rows[0]),delimiter='\t');writer.writeheader();writer.writerows(sorted(branch_rows,key=lambda x:x['split_sha256']))
    b.atomic(output/'matrix_missingness_diagnostics.json',{'rows':missing,'no_automatic_exclusion_or_taxonomy_inference':True})
    for row in snapshot['files']:guard();b.bind(R,row['original']);b.bind(R,row['copy'])
    result={'status':'INDEPENDENT_COMPUTED_OUTPUT_INTEGRITY_AND_SUPPORT_RECONSTRUCTION_PASS_SCIENTIFIC_HOLDS_REMAIN','production_snapshot':p['computed_snapshot'],'production_closure':p['production_closure'],'fixtures':fixture,'ML_leaf_count':900,'consensus_leaf_count':900,'exact_UFBoot_replicates_independently_parsed':1000,'all_replicates_exact_expected900_unique_labels':True,'all_parsed_branch_lengths_finite_nonnegative':True,'NEXUS_declared_and_parsed_splits':declared,'NEXUS_every_weight_reconstructed_from_raw1000_bootstrap_trees':True,'zero_weight_historical_NEXUS_splits':sum(v==0 for v in weights.values()),'ML_nontrivial_splits':len(ml_internal),'consensus_nontrivial_splits':len(con_internal),'ML_and_consensus_shared_nontrivial_splits':len(set(ml_internal)&set(con_internal)),'unrooted_RF_split_symmetric_difference_diagnostic':len(set(ml_internal)^set(con_internal)),'ML_UFBoot_supports_match_reconstructed_counts_at_printed_precision':True,'consensus_supports_match_reconstructed_counts_at_printed_precision':True,'SH_aLRT_requested_and_stock_output_replicates':1000,'SH_aLRT_output_column_count':len(sh),'SH_aLRT_column_order_range_and_complete_stock_phase_validated':True,'SH_aLRT_algorithm_not_reexecuted':True,'branch_counts_SHaLRT_ge80':sum(x>=80 for x in sh),'branch_counts_UFBoot_ge95':sum(x>=95 for x in uf),'finite_ML_log_likelihood':likelihood,'rooting':'UNROOTED_DRAWN_TAXON_IS_NOT_VALIDATED_OUTGROUP','longest_terminal_branches_diagnostic':sorted(tips.items(),key=lambda x:x[1],reverse=True)[:10],'branch_support_reconstruction':b.row(Path(p['project_root']),output/'branch_support_reconstruction.tsv'),'matrix_missingness':b.row(Path(p['project_root']),output/'matrix_missingness_diagnostics.json'),'broader_Stage09_second_seed_gene_trees_concordance_model_adequacy_rooting_and_expanded_seed_checks':'OWED_SEPARATE_ADMISSION_NO_INFERENCE_REPLAY_HERE','retained_holds':p['retained_holds'],'full_panel_final_scientific_acceptance':False,'representative_tree_validated':False,'no_scientific_binary_model_or_subprocess_invoked':True}
    return result
