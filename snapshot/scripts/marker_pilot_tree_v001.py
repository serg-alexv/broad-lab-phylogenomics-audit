"""A resource-bounded exploratory ten-taxon tree, never a full-panel result."""
import argparse,datetime,hashlib,json,os,pathlib,subprocess,sys,time
import marker_pilot_compute_v001 as g

R=pathlib.Path(__file__).resolve().parents[1]
def main(a):
    root=g.inside(a.input_directory);receipt=g.read(root/'data_receipt.json');out=g.inside(a.output);out.mkdir(parents=True,exist_ok=True)
    if receipt['status']!='EXPLORATORY_CONCATENATION_READY':raise ValueError('Concatenation has not passed its output checks')
    for key in ('concatenated','partitions_nexus','partitions_tsv','locus_metrics','taxa_source_flags'):g.bound(receipt[key])
    alignment=g.bound(receipt['concatenated'])
    if alignment!=root/'concatenated.faa':raise ValueError('Unexpected concatenation path')
    records=g.fasta(alignment,aligned=True)
    if len(records)!=10 or set(records)!=set(receipt['taxa'])or len({len(v)for v in records.values()})!=1:raise ValueError('Pilot requires the genuine ten-taxon concatenation')
    admission=g.read(g.inside(a.admission));tool=pathlib.Path(admission['tools']['iqtree']['path'])
    if admission['status']!='ROOT_ADMITTED_EXPLORATORY_TEN_TAXON_TREE' or g.sha(__file__)!=admission['script_sha256'] or g.sha(alignment)!=admission['alignment_sha256'] or g.sha(tool)!=admission['tools']['iqtree']['sha256']:raise ValueError('Tree input/tool/admission changed')
    if admission['cpu']not in (2,3)or not 0<admission['max_rss_bytes']<=402653184 or admission['linux_available_stop_bytes']<1342177280 or not 0<admission['unit_timeout_seconds']<=600:raise ValueError('Tree resource admission exceeds the bounded pilot')
    os.sched_setaffinity(0,{admission['cpu']});g.TOOLCHAIN_SHA=hashlib.sha256(json.dumps(admission,sort_keys=True).encode()).hexdigest()
    prefix=out/'pilot10_LG_G4';started=g.utc();last=0
    def publish(unit,peak=None,mem=None,terminal=None):
        nonlocal last
        if terminal is None and time.monotonic()-last<30:return
        data={'id':'08','name':'Phylogenetic inference','status':terminal or'RUNNING','operation':'EXPLORATORY_TEN_TAXON_MARKER_TREE','detail':'Ten-taxon exploratory LG+G4 tree; no final full-panel inference or support claim','done':int(terminal=='COMPUTED_PENDING_EXTERNAL_CLOSURE'),'total':1,'unit':'exploratory pilot tree','pid':a.native_pid,'creation_time_utc':a.native_creation_utc,'started_utc':started,'updated_utc':g.utc(),'sampled_peak_rss_bytes':peak,'linux_available_bytes':mem,'full_panel_tree_status':'NOT_RUN','production_acceptance':False,'log_path':str(out/'progress.json')};g.save(out/'progress.json',data);g.save(R/'state/stages/08.json',data);last=time.monotonic()
    command=[sys.executable,'-B',str(pathlib.Path(__file__).resolve()),'--_iqtree',str(tool),'--_alignment',str(alignment),'--_prefix',str(prefix),'--_report','{OUTPUT}']
    try:result=g.run_unit(out,'tree_unit',command,[g.ref(alignment),g.ref(root/'data_receipt.json'),g.ref(pathlib.Path(__file__).resolve())],'tree_execution.json',admission,publish)
    except BaseException:
        publish('scientific unit stopped; outputs remain provisional',terminal='STOPPED');raise
    executed=g.read(g.bound(result['output']))
    if executed['actual_iqtree_exit']!=0:raise ValueError('No genuine successful IQ-TREE exit')
    tree=g.bound(executed['tree'])
    g.save(out/'result.json',{'status':'EXPLORATORY_TEN_TAXON_TREE_COMPUTED','tree':g.ref(tree),'alignment':g.ref(alignment),'execution':result,'model':'LG+G4','search':'FAST_PILOT_ONLY','taxa':10,'alignment_sites':len(next(iter(records.values()))),'support':'NOT_ESTIMATED','source_held_taxa':'RETAINED_EXPLORATORY_ONLY','orthology':'PROVISIONAL','full_panel_tree':'NOT_RUN','representative_tree':'NOT_RUN','production_acceptance':False});publish('tree computed',terminal='COMPUTED_PENDING_EXTERNAL_CLOSURE')

if __name__=='__main__':
    if '--_iqtree'in sys.argv:
        z=sys.argv;tool=z[z.index('--_iqtree')+1];alignment=z[z.index('--_alignment')+1];prefix=z[z.index('--_prefix')+1];report=z[z.index('--_report')+1]
        cmd=[tool,'-s',alignment,'--fast','-m','LG+G4','-T','1','--seed','20261027','--prefix',prefix,'--mem','128M']
        p=subprocess.run(cmd);tree=pathlib.Path(prefix+'.treefile')
        if p.returncode!=0:sys.exit(p.returncode)
        if not tree.is_file()or not tree.stat().st_size:raise RuntimeError('IQ-TREE returned0 without a tree')
        g.save(g.inside(report),{'actual_iqtree_exit':p.returncode,'command':cmd,'tree':g.ref(tree),'scope':'EXPLORATORY10_ONLY','full_panel_tree_acceptance':False})
    else:
        p=argparse.ArgumentParser();p.add_argument('--input-directory',required=True);p.add_argument('--output',required=True);p.add_argument('--admission',required=True);p.add_argument('--native-pid',type=int);p.add_argument('--native-creation-utc');main(p.parse_args())
