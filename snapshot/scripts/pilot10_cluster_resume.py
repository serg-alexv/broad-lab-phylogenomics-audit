#!/usr/bin/env python3
"""One bounded cluster-only correction; preserve accepted Prodigal annotations."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import time
import uuid
import pilot10 as pilot

ROOT=pilot.ROOT
FAILED_RUN='20261026T161347Z-c4e91c88'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',action='store_true')
    args=p.parse_args()
    assert socket.gethostname().casefold()=='wd','WD-only'
    original=ROOT/'analysis/pilot10/runs'/FAILED_RUN
    failure=json.loads((original/'pilot_exit_receipt.json').read_text())
    assert failure['status']=='FAILED' and len(failure['annotations'])==10
    assert 'Cannot fit databases into 1023M' in (original/'mmseqs_easy_cluster.stderr').read_text()
    parameters={'change':'Explicit MMseqs k-mer length5, replacing automatic0; all remaining thresholds and budgets unchanged',
                'reason':'MMseqs automatic prefilter rejected its estimated index at1G before large observed RSS allocation.',
                'prior_sampled_peak_group_rss_bytes':json.loads((original/'mmseqs_easy_cluster.exit.json').read_text())['sampled_peak_group_rss_bytes'],
                'source_documentation':'https://mmseqs.com/latest/userguide.pdf',
                'method_limitation':'A smaller k-mer index changes the prefilter speed/sensitivity tradeoff. Results remain exploratory pilot candidates only.',
                'rss_budget_bytes':pilot.MAX_RSS,'per_process_address_space_budget_bytes':pilot.MAX_RSS,
                'split_memory_limit':'1G','threads':2,'timeout_seconds':600,'prodigal_rerun':False}
    if not args.run:
        print(json.dumps(parameters,indent=2));return 0
    assert pilot.available()>=pilot.MAX_RSS+pilot.HEADROOM,'Need>=3GiB Linux available memory'
    pilot.stop_gate()
    marker=ROOT/'state/pilot10_bounded_correction.json'
    assert not marker.exists(),'The one bounded correction has already been attempted; inspect its receipt'
    run_id=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-cluster-resume-'+uuid.uuid4().hex[:8]
    run=ROOT/'analysis/pilot10/runs'/run_id;run.mkdir(parents=True)
    lock=(ROOT/'state/pilot10.lock').open('a+')
    fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    pilot.write_json(marker,{'run_id':run_id,'started_utc':pilot.utc(),'attempt':1,'parameters':parameters})
    pilot.write_json(ROOT/'state/pilot10_owner.json',{'run_id':run_id,'started_utc':pilot.utc(),**pilot.process_stat(os.getpid())})
    for sig in (signal.SIGINT,signal.SIGTERM):
        signal.signal(sig,lambda *_:setattr(pilot,'STOPPING',True))
    env=dict(os.environ)
    for name in ('TMPDIR','TMP','TEMP'):env[name]=str(ROOT/'work/pilot10_tmp'/run_id)
    env['XDG_CACHE_HOME']=str(ROOT/'work/pilot10_cache')
    for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):env[name]='2'
    env['PATH']=str(ROOT/'tools/bioenv/bin')+':'+env.get('PATH','')
    Path(env['TMPDIR']).mkdir(parents=True);Path(env['XDG_CACHE_HOME']).mkdir(parents=True,exist_ok=True)
    started=time.monotonic();deadline=started+600
    status='FAILED';error=None;annotations=[];summary=None
    try:
        pilot.write_json(run/'correction_parameters.json',parameters)
        combined=run/'all_proteins.faa'
        panel=json.loads((ROOT/'metadata/pilot_panel.json').read_text())[:10]
        assert pilot.sha(ROOT/'metadata/pilot_panel.json')==failure['panel_sha256']
        assert [r['accession'] for r in panel]==[r['accession'] for r in failure['annotations']]
        with combined.open('wb') as out:
            for record,prior in zip(panel,failure['annotations']):
                pilot.stop_gate()
                accession=record['accession']
                folder=ROOT/'analysis/pilot10/annotations'/accession
                receipt_path=folder/'annotation_commit.json'
                receipt=json.loads(receipt_path.read_text())
                assert receipt['status']=='PASS_PILOT_GENE_CALLING' and receipt['accession']==accession
                assert receipt['protein_count']==prior['proteins']
                assert receipt['fingerprint']['script_sha256']==failure['script_sha256']
                assert receipt['fingerprint']['source_receipt_sha256']==pilot.sha(ROOT/'raw'/accession/'acquisition_receipt.json')
                assert receipt['fingerprint']['gene_calling_mode']=='single' and receipt['fingerprint']['translation_table']==11
                pilot.verify_files(folder,receipt)
                with (folder/'proteins.faa').open('rb') as src:shutil.copyfileobj(src,out)
                annotations.append({'accession':accession,'proteins':receipt['protein_count'],
                                    'action':'VERIFIED_REUSE_NO_GENE_CALLING','annotation_receipt_sha256':pilot.sha(receipt_path)})
        assert pilot.sha(combined)==pilot.sha(original/'all_proteins.faa'),'Combined input differs from failed run'
        command=[str(ROOT/'tools/bioenv/bin/mmseqs'),'easy-cluster',str(combined),str(run/'cluster'),str(run/'mmseqs_tmp'),
                 '--min-seq-id','0.3','-c','0.8','--cov-mode','0','--cluster-mode','2','--threads','2','--split-memory-limit','1G','-k','5']
        command_receipt=pilot.execute(command,run/'mmseqs_easy_cluster',deadline,env)
        summary=pilot.summarize_clusters(run/'cluster_cluster.tsv',run,panel)
        assert summary['proteins']==sum(r['proteins'] for r in annotations)
        for row in annotations:
            assert pilot.sha(ROOT/'analysis/pilot10/annotations'/row['accession']/'annotation_commit.json')==row['annotation_receipt_sha256']
        status='PASS_EXPLORATORY_PILOT_ONLY'
    except BaseException as exc:error=repr(exc)
    finally:
        fcntl.flock(lock.fileno(),fcntl.LOCK_UN);lock.close()
        receipt={'run_id':run_id,'resumed_from':FAILED_RUN,'status':status,'error':error,
                 'ended_utc':pilot.utc(),'elapsed_seconds':time.monotonic()-started,'annotations':annotations,
                 'summary':summary,'parameters':parameters,'script_sha256':pilot.sha(__file__),
                 'outputs_preserved':str(run),'lock_released':True,'biological_quality_status':'NOT_RUN',
                 'accepted_broad_lab_marker_set_status':'NOT_RUN','defence_status':'NOT_RUN'}
        pilot.write_json(run/'pilot_exit_receipt.json',receipt)
        pilot.write_json(ROOT/'state/pilot10_last_exit.json',receipt)
        pilot.write_json(marker,receipt)
        print(json.dumps(receipt,indent=2),flush=True)
    return 0 if status=='PASS_EXPLORATORY_PILOT_ONLY' else 2


if __name__=='__main__':raise SystemExit(main())
