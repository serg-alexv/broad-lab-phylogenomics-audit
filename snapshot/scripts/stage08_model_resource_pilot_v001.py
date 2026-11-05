"""Stock IQ-TREE limited model/resource pilot; unchanged accepted900x13071 AA matrix."""
from pathlib import Path
import os,sys,json,time,signal,fcntl,re,math
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import marker_pilot_compute_v001 as g
from stage08_model_resource_units_v001 import Runtime
from fullpanel_gene_metrics_v001 import parse_newick

def main():
 def interrupted(number,frame):raise InterruptedError('Stage08 pilot signal '+str(number))
 signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
 plan_path=Path(sys.argv[1]);expected=sys.argv[2];assert g.sha(plan_path)==expected;P=g.read(plan_path)
 for q in P['sources']+P['bound_inputs']:g.bound(q)
 for q in P['tool_files']:
  p=Path(q['path']);assert p.stat().st_size==q['bytes']and g.sha(p)==q['sha256']
 scope=g.read(g.bound(P['scope_GO']));assert scope['status']=='ROOT_GO_BOUNDED_STAGE08_MODEL_RESOURCE_PILOT_ONLY'and scope['scope_sha256']==P['scope_sha256']
 accepted=g.read(g.bound(P['matrix_acceptance']));assert accepted['status']=='ROOT_ACCEPTED_CLOSED_COMPUTATIONAL_INPUT_QC_ONLY'
 OUT=R/P['output'];OUT.mkdir(exist_ok=True);E=R/P['work'];commits=[]
 with(OUT/'once_claim.json').open('x')as f:json.dump({'plan_sha256':expected,'started_utc':g.utc(),'no_automatic_retry':True},f)
 runtime=Runtime(P);common=(R/'state/checkm2_pilot.lock').open('r+b');fcntl.flock(common,fcntl.LOCK_EX|fcntl.LOCK_NB);lease=(OUT/'queue.lock').open('a+b');fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
 try:
  # Verify accepted input bytes/labels only. No reconstruction, realignment or repeated Stage07 QC.
  alignment=g.bound(P['alignment']);records=g.fasta(alignment,aligned=True);assert len(records)==900 and {len(s)for s in records.values()}=={13071};labels=set(g.bound(P['accession_labels']).read_text().splitlines());assert set(records)==labels
  runtime.phase='LIMITED_STOCK_MODELFINDER_RESOURCE_MEASUREMENT';runtime.current='LG_WAG_JTT_EMPIRICAL_FREQUENCIES_GAMMA4';runtime.publish('Unchanged900taxa/13071AA; restricted3model stock TESTONLY. This is a bounded global resource/fit diagnostic, not final model adequacy',True)
  unit=OUT/'model_test';prefix=unit/'pilot';argv=[P['iqtree'],'-s',str(alignment),*P['model_test_arguments'],'--prefix',str(prefix)];proof=runtime.run(unit,argv,'IQTREE3_TESTONLY_LG_WAG_JTT_F_G4',[P['alignment'],P['matrix_acceptance']])
  report=Path(str(prefix)+'.iqtree');log=Path(str(prefix)+'.log');text=report.read_text()+'\n'+log.read_text()+'\n'+(unit/'stdout.txt').read_text();matches=re.findall(r'Best-fit model(?: according to BIC)?:\s*([A-Za-z0-9+._-]+)',text);assert matches,'Stock0 saved outputs lack readable best-fit model; preserve0,no replay';model=matches[-1];assert model in P['permitted_best_models'],model
  c={'status':'STOCK_TESTONLY0_LIMITED_MODEL_COMPARISON_PENDING_EXTERNAL_CLOSURE','execution':proof,'alignment':P['alignment'],'matrix_acceptance':P['matrix_acceptance'],'best_model_BIC_in_limited_candidate_set':model,'candidate_set':P['permitted_best_models'],'artifacts':[g.ref(p)for p in unit.iterdir()if p.is_file()],'model_adequacy_or_partition_scheme_acceptance':False,'source_and_taxonomy_holds_preserved':True};g.save(unit/'COMMITTED.json',c);commits.append(g.ref(unit/'COMMITTED.json'));runtime.done=1;runtime.publish('Restricted stock ModelFinder phase committed; next bounded fast pilot search, no support or production acceptance',True)
  runtime.phase='FAST_FULL900_MODEL_RESOURCE_SEARCH_PILOT';runtime.current=model;unit=OUT/'fast_tree';prefix=unit/'pilot';argv=[P['iqtree'],'-s',str(alignment),'-m',model,*P['tree_pilot_arguments'],'--prefix',str(prefix)];proof=runtime.run(unit,argv,'IQTREE3_FAST_FULL900_RESOURCE_PILOT',[P['alignment'],commits[0]])
  tree=Path(str(prefix)+'.treefile');report=Path(str(prefix)+'.iqtree');log=Path(str(prefix)+'.log');parse_newick(tree.read_text(),labels);text=report.read_text();size=re.search(r'Input data: (\d+) sequences with (\d+) amino-acid sites',text);assert size and tuple(map(int,size.groups()))==(900,13071);likelihood=re.search(r'Log-likelihood of the tree:\s*([^\s]+)',text);assert likelihood and math.isfinite(float(likelihood[1]));assert 'Model of substitution: '+model in text
  c={'status':'FAST900_PILOT_TREE0_EXACT_ACCESSION_LEAFSET_PENDING_EXTERNAL_CLOSURE','execution':proof,'alignment':P['alignment'],'source_model_test':commits[0],'model':model,'finite_log_likelihood':float(likelihood[1]),'tree':g.ref(tree),'report':g.ref(report),'log':g.ref(log),'artifacts':[g.ref(p)for p in unit.iterdir()if p.is_file()],'taxa':900,'columns':13071,'support':'NOT_ESTIMATED','scope':'Bounded fast-search resource pilot only; not production full-panel tree or final model adequacy','all_source_taxonomy_type_quality_masks_preserved':True,'production_full_or_representative_tree_acceptance':False};g.save(unit/'COMMITTED.json',c);commits.append(g.ref(unit/'COMMITTED.json'));runtime.done=2
  g.save(OUT/'PILOT_COMPLETE.json',{'status':'TWO_STOCK_STAGE08_PILOT_PHASES_COMPLETE_EXTERNAL_CLOSURE_AND_REVIEW_REQUIRED','source_plan':g.ref(plan_path),'commits':commits,'matrix_acceptance':P['matrix_acceptance'],'alignment':P['alignment'],'best_model_in_limited_set':model,'actual_scientific_seconds':runtime.science,'actual_cold_seconds':time.monotonic()-runtime.started,'peak_Linux_RSS_plus_private_RAM_bytes':runtime.peak,'no_accepted_annotation_search_alignment_matrix_validation_replayed':True,'known19_genome_holds_3_sensitive_marker_holds_9_composition_flags_preserved':True,'expanded_seed_robustness_taxonomy_eligible_species_rescue_orthology_and_model_adequacy_still_required':True,'full_panel_production_tree_acceptance':False,'representative_panel_tree_acceptance':False});runtime.publish('Stage08 bounded pilot finished. Actual external closure, fit/resource review, then separately admit full inference and independent QC',True,status='COMPUTED_PENDING_EXTERNAL_CLOSURE')
 except BaseException as error:
  g.save(E/'failure.json',{'error':repr(error),'phase':runtime.phase,'current':runtime.current,'phase_commits':commits,'actual_scientific_debit_seconds':runtime.science,'actual_cold_debit_seconds':time.monotonic()-runtime.started,'successful_units_and_partial_IQTREE_checkpoints_preserved':True,'no_automatic_retry':True,'unresolved_unknown_is_not_failure_of_biology_or_negative':True,'at_utc':g.utc()});raise
 finally:fcntl.flock(lease,fcntl.LOCK_UN);lease.close();fcntl.flock(common,fcntl.LOCK_UN);common.close()

if __name__=='__main__':main()
