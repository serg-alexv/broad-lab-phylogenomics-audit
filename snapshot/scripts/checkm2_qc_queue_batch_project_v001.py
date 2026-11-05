"""Hash-first owned stock-batch row projection; no model, annotation or search."""
from pathlib import Path
import argparse,csv,hashlib,io,os,sys
import checkm2_qc_queue_common_v001 as c
import checkm2_posthoc_v002_validator as v

def main(a):
    request=c.read(c.path(a.request))
    if c.sha(c.path(a.request))!=a.request_sha256:raise RuntimeError('Trusted batch projection request changed')
    if request.get('request_schema')!='TREE2_QC_STOCK_BATCH_PROJECTION_REQUEST_V001':raise RuntimeError('Batch projection schema differs')
    plan,recipe,authority=c.request_gate(request);names=request['accessions']
    if not 1<=len(names)<=20 or len(names)!=len(set(names))or not set(names)<=set(plan['accessions']):raise RuntimeError('Exact declared fresh batch names required')
    commit=c.read(c.bind(request['batch_prediction_commit']))
    if commit['accessions']!=names or not c.unit_closed(c.read(c.bind(commit['stock_batch_execution']))):raise RuntimeError('Genuine owned global stock-batch0 required')
    raw=c.bind(commit['raw_pickle']);report=c.bind(commit['quality_report']);prefix=c.path(request['runtime_prefix']);v.no_models()
    if Path(sys.executable).resolve()!=(prefix/'bin/python').resolve()or os.environ.get('TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED')!='1':raise RuntimeError('Actual accepted RO Python required')
    import numpy as np
    import pandas as pd
    if sys.version_info[:3]!=(3,12,16)or np.__version__!='2.5.4'or pd.__version__!='3.1.0'or not Path(np.__file__).resolve().is_relative_to(prefix)or not Path(pd.__file__).resolve().is_relative_to(prefix):raise RuntimeError('Pinned projection runtime versions/origins required')
    v.no_models();frame=pd.read_pickle(raw);schema=c.read(c.bind(plan['feature_schema']))
    if list(frame.columns)!=['Name',*schema['ordered_model_features']]or frame.shape!=(len(names),21242):raise RuntimeError('Exact batch ordered21242 columns/shape required')
    observed=list(frame['Name'])
    if len(set(observed))!=len(names)or set(observed)!=set(names):raise RuntimeError('Batch frame names differ or duplicate')
    with report.open(newline='')as f:
        reader=csv.reader(f,delimiter='\t');header=next(reader);rows=list(reader)
    if len(header)!=5 or len(set(header))!=5 or header[0]!='Name'or len(rows)!=len(names)or any(len(x)!=5 for x in rows):raise RuntimeError('Strict complete five-column stock report required')
    reports={x[0]:x for x in rows}
    if len(reports)!=len(names)or set(reports)!=set(names):raise RuntimeError('Report/frame exact name join required')
    output=c.path(a.output)
    if output.exists():raise RuntimeError('Projection output exists; no overwrite/replay')
    output.mkdir(parents=True);projected=[]
    for accession in names:
        own=frame.iloc[[observed.index(accession)]].copy();values=v.validate_domains(schema,own,np);folder=output/accession;folder.mkdir()
        target=folder/'feature_vectors_1.pkl';own.to_pickle(target)
        report_path=folder/'quality_report.tsv'
        with report_path.open('x',newline='')as f:
            writer=csv.writer(f,delimiter='\t',lineterminator='\n');writer.writerow(header);writer.writerow(reports[accession])
        projected.append({'accession':accession,'raw_pickle':c.row(target),'quality_report':c.row(report_path),'canonical_float64_le_row_sha256':hashlib.sha256(np.asarray(values,dtype='<f8',order='C').tobytes()).hexdigest(),'original_batch_row_index':observed.index(accession)})
    if c.sha(raw)!=commit['raw_pickle']['sha256']or c.sha(report)!=commit['quality_report']['sha256']or c.sha(a.request)!=a.request_sha256:raise RuntimeError('Original owned batch inputs changed during projection')
    v.no_models();c.save(output/'projection_commit.json',{'status':'BATCH_STOCK_FEATURE_ROWS_PROJECTED_PENDING_UNIT_AND_CONTEXT_CLOSURE','request':c.row(a.request),'batch_prediction_commit':request['batch_prediction_commit'],'stock_batch_execution':commit['stock_batch_execution'],'raw_batch_pickle':commit['raw_pickle'],'raw_batch_report':commit['quality_report'],'accessions':names,'rows':projected,'annotation_DIAMOND_or_ML_runs':0,'global_ML_debit_not_copied_to_rows':True})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--request',required=True);p.add_argument('--request-sha256',required=True);p.add_argument('--output',required=True);main(p.parse_args())
