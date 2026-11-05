"""New balanced32 alignment diagnostics and196 all-copy fast gene trees; no final trees."""
from pathlib import Path
import os,sys,json,time,signal,fcntl,collections,hashlib
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import marker_pilot_compute_v001 as g
from fullpanel_phylo_units_v001 import Runtime
from fullpanel_gene_metrics_v001 import residues,pair_agreement,parse_newick,unrooted_monophyly

def main():
 def interrupted(number,frame):raise InterruptedError('Gene assessment signal '+str(number))
 signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
 plan_path=Path(sys.argv[1]);expected=sys.argv[2];assert g.sha(plan_path)==expected;P=g.read(plan_path)
 for q in P['sources']:g.bound(q)
 for q in P['tool_files']:
  p=Path(q['path']);assert p.stat().st_size==q['bytes']and g.sha(p)==q['sha256']
 scope=g.read(g.bound(P['scope_GO']));assert scope['status']=='ROOT_GO_FULL919_DIAGNOSTIC_GENE_TREES_AND_BALANCED32_SENSITIVITY'and scope['scope_sha256']==P['scope_sha256']
 OUT=R/P['output'];OUT.mkdir(exist_ok=True);E=R/P['work']
 with(OUT/'once_claim.json').open('x')as f:json.dump({'plan_sha256':expected,'started_utc':g.utc(),'no_automatic_retry':True},f)
 runtime=Runtime(P);common=(R/'state/checkm2_pilot.lock').open('r+b');fcntl.flock(common,fcntl.LOCK_EX|fcntl.LOCK_NB);lease=(OUT/'queue.lock').open('a+b');fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB);sens=[];trees=[]
 try:
  validation=g.read(g.bound(P['validated_alignments']));families={q['profile']:q for q in validation['rows']};assert set(families)==set(P['ordered_families'])and len(families)==196
  manifest=g.read(g.bound(P['source_genome_manifest']));labels={q['accession']:q['source_metadata']for q in manifest['rows']};assert len(labels)==919
  runtime.publish('Twenty length-stratified strict-core families;32 species-first family-balanced genomes',True)
  for selected in P['sensitivity_selection']:
   runtime.guard();name=runtime.current=selected['profile'];source_commit=g.read(g.bound(families[name]['commit']));art={Path(q['path']).name:q for q in source_commit['artifacts']};original=g.fasta(g.bound(art['all_qualifying_copies.faa']));aligned=g.fasta(g.bound(art['alignment.faa']),aligned=True);residues(original,aligned)
   by_acc={n.split('|',1)[0]:n for n in original};assert len(by_acc)==len(original)==919
   taxa=P['sensitivity_taxa'];subset={by_acc[a]:original[by_acc[a]]for a in taxa};projection={n:aligned[n]for n in subset};folder=OUT/'sensitivity'/name;folder.mkdir(parents=True,exist_ok=False);input_path=folder/'original32.faa';projected=folder/'projected_full919_alignment32.faa';g.write_fasta(input_path,subset);g.write_fasta(projected,projection)
   command=[P['mafft'],'--amino','--localpair','--maxiterate','1000','--thread','1','--inputorder','--quiet',str(input_path)];proof=runtime.run(folder/'careful_unit',command,'MAFFT_LINS_I_BALANCED32',[g.ref(input_path),families[name]['commit']]);careful_path=folder/'careful_unit/stdout.txt';careful=g.fasta(careful_path,aligned=True);comparison=pair_agreement(projection,careful,subset);flag=comparison['paired_residue_jaccard']is None or comparison['paired_residue_jaccard']<.9
   row={'profile':name,'stratum':selected['stratum'],'genomes':32,'selection':selected,'comparison':comparison,'review_alignment_sensitivity':flag,'review_jaccard_threshold':.9,'scope':'Balanced32 sensitivity of new full919 alignment projection, NOT a full919 alternative alignment or marker acceptance','execution':proof,'original_input':g.ref(input_path),'full_projection':g.ref(projected),'careful_alignment':g.ref(careful_path),'source_family_commit':families[name]['commit'],'source_taxonomy_QC_and_type_holds_preserved':True,'automatic_marker_acceptance_or_exclusion':False};g.save(folder/'COMMITTED.json',row);sens.append(g.ref(folder/'COMMITTED.json'));runtime.done+=1;runtime.publish('Careful32 alignment comparison committed',True)
  runtime.phase='FULL919_ALL_COPY_DIAGNOSTIC_GENE_TREES';runtime.done=0;runtime.total=196
  for name in P['ordered_families']:
   runtime.guard();runtime.current=name;family=g.read(g.bound(families[name]['commit']));art={Path(q['path']).name:q for q in family['artifacts']};alignment=g.bound(art['trimmed_all_copies.faa']);records=g.fasta(alignment,aligned=True);metadata=g.read(g.bound(art['leaf_provenance.json']));assert set(records)==set(metadata)
   folder=OUT/'gene_trees'/name;folder.mkdir(parents=True,exist_ok=False);unit=folder/'iqtree_unit';prefix=unit/'gene';command=[P['iqtree'],'-s',str(alignment),'--fast','-m','LG+G4','-T','1','--seed','20261029','--prefix',str(prefix),'--mem','1400M','--safe'];proof=runtime.run(unit,command,'IQTREE3_FAST_DIAGNOSTIC_GENE_TREE',[art['trimmed_all_copies.faa'],families[name]['commit']]);tree_path=Path(str(prefix)+'.treefile');report=Path(str(prefix)+'.iqtree');log=Path(str(prefix)+'.log')
   if not tree_path.exists()or not report.exists()or not log.exists():raise RuntimeError('IQ-TREE0 without required tree/report/log; preserve successful unit, no replay')
   root=parse_newick(tree_path.read_text(),set(records));family_groups={n:labels[metadata[n]['accession']]['family']for n in records};genome_groups={n:metadata[n]['accession']for n in records};family_diag=unrooted_monophyly(root,family_groups);copy_diag=unrooted_monophyly(root,genome_groups);duplicates={acc:count for acc,count in copy_diag['expected_group_leaf_counts'].items()if count>1};clustered=set(copy_diag['groups_matching_one_unrooted_split']);artifacts=[g.ref(p)for p in unit.iterdir()if p.is_file()]
   row={'profile':name,'status':'GENE_TREE0_EXACT_ALL_COPY_LEAF_SET_VALIDATED_PENDING_EXTERNAL_CLOSURE','execution':proof,'tree':g.ref(tree_path),'report':g.ref(report),'log':g.ref(log),'artifacts':artifacts,'input_alignment':art['trimmed_all_copies.faa'],'source_family_commit':families[name]['commit'],'original_leaf_provenance':art['leaf_provenance.json'],'leaves':len(records),'genomes':len(set(genome_groups.values())),'alignment_columns':len(next(iter(records.values()))),'model':'LG+G4','search':'IQTREE3_FAST_DIAGNOSTIC_ONLY','support':'NOT_ESTIMATED','family_source_label_split_diagnostic':family_diag,'genomes_with_multiple_qualifying_copies':duplicates,'multicopy_genomes_all_copies_cluster_on_one_unrooted_split':sorted(set(duplicates)&clustered),'multicopy_genomes_split_across_tree_review':sorted(set(duplicates)-clustered),'original_QC_taxonomy_type_source_and_cross_profile_ambiguity_masks_preserved':True,'orthology_or_paralogy_acceptance':'NOT_GRANTED_FROM_FAST_TOPOLOGY','source_taxonomy_truth_claimed':False,'final_marker_full_or_representative_tree_acceptance':False};g.save(folder/'COMMITTED.json',row);trees.append(g.ref(folder/'COMMITTED.json'));runtime.done+=1;runtime.publish('All-copy diagnostic gene-tree checkpoint committed',True)
  g.save(OUT/'result.json',{'status':'BALANCED32_SENSITIVITY20_AND_FULL919_ALL_COPY_DIAGNOSTIC_GENE_TREES196_COMPUTED_PENDING_EXTERNAL_CLOSURE','sensitivity_commits':sens,'gene_tree_commits':trees,'sensitivity_comparisons':20,'gene_trees':196,'genomes_in_source_scope':919,'input_plan':g.ref(plan_path),'actual_scientific_seconds':runtime.science,'cold_seconds':time.monotonic()-runtime.started,'peak_Linux_RSS_plus_private_RAM_bytes':runtime.peak,'all_previous_annotations_searches_QC_and_full_alignments_reused_without_replay':True,'broader_marker_discovery_reconciliation_and_final_selection_still_required':True,'source_taxonomy_species_balance_full_panel_defence_and_both_final_tree_validations_still_required':True,'final_marker_or_final_tree_acceptance':False});runtime.publish('Twenty careful32 comparisons and196 full919 diagnostic gene trees complete; external audit/reconciliation next',True,status='COMPUTED_PENDING_EXTERNAL_CLOSURE')
 except BaseException as error:
  g.save(E/'failure.json',{'error':repr(error),'phase':runtime.phase,'current':runtime.current,'completed_sensitivity':len(sens),'completed_gene_trees':len(trees),'actual_scientific_debit_seconds':runtime.science,'actual_cold_debit_seconds':time.monotonic()-runtime.started,'successful_units_and_partial_IQTREE_checkpoints_preserved':True,'no_automatic_retry':True,'unknown_or_unrun_is_not_negative':True,'at_utc':g.utc()});raise
 finally:fcntl.flock(lease,fcntl.LOCK_UN);lease.close();fcntl.flock(common,fcntl.LOCK_UN);common.close()

if __name__=='__main__':main()
