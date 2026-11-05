"""One saved-search stock prediction and full-feature check; no native/namespace launcher.

Only an explicitly admitted outer owner may call this inside the existing
accepted read-only CheckM2/overlay/private-IPC namespace. No annotation or
DIAMOND executable is dispatched. Importing this file performs no work.
"""
from pathlib import Path
import argparse,datetime,fcntl,hashlib,json,math,os,shutil,sys,time,traceback,uuid
from checkm2_saved_admission_read_v001 import admission_sha

R=Path(__file__).resolve().parents[1]
ACC='GCF_900636715.1'
AUTHORITY_SHA='8f95dce8536471676c08a9b045c31a1833dd37931e7d55fb438238e7718c0f19'
STOCK_SECONDS=548.0189570170041
LIMITS={'cpu':0,'stock_threads':1,'linux_total_rss_bytes':1543503872,'native_reserved_bytes':67108864,'total_owned_rss_bytes':1610612736,'linux_available_minimum_bytes':1879048192,'fresh_launch_available_minimum_bytes':3100000000,'disk_reserve_bytes':42949672960,'stock_seconds':STOCK_SECONDS,'feature_seconds':120}

def path(value):
    p=Path(value);s=str(p).replace('\\','/')
    linux='/mnt/c/Users/wheel/Documents/Codex/2026-10-26/referenced-chatgpt-conversation-this-is-an/outputs/TREE2_WD_20261026/'
    if os.name=='nt' and s.startswith(linux):p=R/s[len(linux):]
    p=(p if p.is_absolute() else R/p).resolve()
    if not p.is_relative_to(R):raise RuntimeError('Saved-stock path leaves project')
    return p
def sha(value):
    digest=hashlib.sha256()
    with path(value).open('rb') as f:
        for chunk in iter(lambda:f.read(65536),b''):digest.update(chunk)
    return digest.hexdigest()
def read(value):return json.loads(path(value).read_text(encoding='utf-8-sig'))
def save(value,data):
    p=path(value);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.'+uuid.uuid4().hex+'.partial')
    with tmp.open('x',encoding='utf-8',newline='\n')as f:json.dump(data,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,p)
def row(value):
    p=path(value);return {'path':p.relative_to(R).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size}
def bind(value):
    p=path(value['path'])
    if sha(p)!=value['sha256'] or p.stat().st_size!=value['bytes']:raise RuntimeError('Saved artifact/source differs:'+str(p))
    return p
def unit_closed(value):
    return value.get('status')=='UNIT_EXIT0_GROUP_CLOSED' and type(value.get('exit_code'))is int and value['exit_code']==0 and value.get('owned_group_empty')is True and value.get('remaining_owned_processes')==[]
def charged_unit(value,allowed):
    elapsed=value.get('elapsed_seconds')
    if not unit_closed(value)or type(elapsed)not in(int,float)or not math.isfinite(elapsed)or not 0<=elapsed<=allowed:raise RuntimeError('Actual closed phase debit missing or exceeds its remaining cap; preserve and hold')
    return elapsed
def verify_manifest(folder,value):
    folder=path(folder)
    for item in value['files']:
        p=path(folder/item['path'])
        if not p.is_relative_to(folder)or sha(p)!=item['sha256']or p.stat().st_size!=item['bytes']:raise RuntimeError('Saved phase manifest differs')
def manifest(folder):
    folder=path(folder);files=[{'path':p.relative_to(folder).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size}for p in sorted(folder.rglob('*'))if p.is_file()and p.name not in('manifest.json','commit.json')]
    save(folder/'manifest.json',{'files':files,'external_namespace_native_closure_pending':True});return row(folder/'manifest.json')

def saved_phases(ref):
    if ref['sha256']!=AUTHORITY_SHA:raise RuntimeError('Exact actual closed saved-phase authority required')
    authority=read(bind(ref))
    if authority.get('status')!='ROOT_CLOSED_FAILED_QC_CONTEXT_SAVED_ANNOTATION_SEARCH_VALIDATION_REUSABLE_PENDING_BOUNDED_RECOVERY' or authority.get('owned_group_namespace_image_lease_closure_verified')is not True or authority.get('actual_native_exit_code')!=2 or authority.get('actual_WSL_exit_code')!=1:raise RuntimeError('Original failed context/closure must be preserved')
    for item in authority['all_prior_21_unit_receipts']:bind(item)
    ann=read(bind(authority['reusable_annotation_commit']));search=read(bind(authority['reusable_diamond_commit']))
    if ann['accession']!=ACC or search['accession']!=ACC or ann['selected_faa']!=search['selected_faa']:raise RuntimeError('Saved own FAA/phase association differs')
    for phase in(ann,search):
        p=bind(phase['manifest']);verify_manifest(p.parent,read(p))
    for item in(ann['unit_execution'],search['unit_execution'],search['validation_unit_execution']):
        if not unit_closed(read(bind(item))):raise RuntimeError('Saved annotation/search/raw-validation actual0 required')
    search_receipt=read(bind(search['diamond_receipt']))
    old_request_path=path(authority['reusable_diamond_commit']['path']).parent/'requests/diamond.json'
    if sha(old_request_path)!=search_receipt['request_sha256']:raise RuntimeError('Saved original search request differs')
    old_request=read(old_request_path)
    plan=read(bind(old_request['input_plan']));recipe=read(bind(plan['scientific_recipe']));item=next(x for x in recipe['inputs']if x['accession']==ACC)
    if search['input_plan_sha256']!=old_request['input_plan']['sha256']or ann['input_plan_sha256']!=old_request['input_plan']['sha256']or ann['source_manifest_sha256']!=old_request['source_manifest']['sha256']or search['source_manifest_sha256']!=old_request['source_manifest']['sha256']:raise RuntimeError('Original source/plan lineage differs')
    if authority['failed_first_resume600_cap_consumed_seconds']!=51.98104298299586 or authority['first_resume_cap_remaining_seconds']!=STOCK_SECONDS:raise RuntimeError('Original failed stock debit/cap changed')
    return authority,ann,search,old_request,plan,recipe,item

def request_gate(request):
    if request.get('request_schema')not in('TREE2_PARALLEL_SAVED_STOCK_REQUEST_V001','TREE2_PARALLEL_SAVED_STOCK_FEATURE_REQUEST_V001'):raise RuntimeError('Saved-stock request schema differs')
    protocol=read(bind(request['protocol_admission']))
    if protocol.get('status')!='ROOT_ADMITTED_ONE_PARALLEL_SAVED_STOCK_RECOVERY_V001'or protocol.get('saved_stock_execution_authorized')is not True or protocol.get('no_annotation_or_search_replay')is not True or protocol.get('limits')!=LIMITS:raise RuntimeError('Explicit saved-only parallel Root admission required')
    if protocol.get('source_manifest')!=request['source_manifest']or protocol.get('saved_phase_authority')!=request['saved_phase_authority']or protocol.get('companion_marker')!=request['companion_marker']:raise RuntimeError('Source/saved-phase/exact companion Root bindings differ')
    if path(protocol['output_root'])!=path(request['output_root'])or path(protocol['scoped_stop'])!=path(request['scoped_stop'])or protocol.get('helper_max_seconds')!=900:raise RuntimeError('Root once-output/own STOP/finite helper binding differs')
    for name in('launch','admission'):bind(request['companion_marker'][name])
    sources=read(bind(request['source_manifest']))
    for source in sources['sources']:bind(source)
    a,ann,search,original,plan,recipe,item=saved_phases(request['saved_phase_authority'])
    if request.get('accession')!=ACC:raise RuntimeError('One exact saved accession only')
    return plan,{'input':item,'original':original,'annotation':ann,'search':search,'authority':a},protocol

def feature_context(request):
    plan,context,protocol=request_gate(request)
    expected={'raw_pickle','selected_faa','annotation_receipt','annotation_unit_execution','annotation_commit','diamond_receipt','diamond_unit_execution','diamond_commit','quality_report','quality_unit_execution','diamond_validation_unit_execution'}
    artifacts=request['artifacts']
    if set(artifacts)!=expected:raise RuntimeError('Complete own saved-stock feature artifact set required')
    for item in artifacts.values():bind(item)
    ann=context['annotation'];search=context['search']
    joins={'selected_faa':ann['selected_faa'],'annotation_receipt':ann['annotation_receipt'],'annotation_unit_execution':ann['unit_execution'],'annotation_commit':context['authority']['reusable_annotation_commit'],'diamond_receipt':search['diamond_receipt'],'diamond_unit_execution':search['unit_execution'],'diamond_commit':context['authority']['reusable_diamond_commit'],'diamond_validation_unit_execution':search['validation_unit_execution']}
    if any(artifacts[k]!=v for k,v in joins.items()):raise RuntimeError('Original saved phase/FAA provenance was relabelled')
    stock=read(bind(artifacts['quality_unit_execution']));charged_unit(stock,STOCK_SECONDS)
    if stock.get('declared_unit')!='unit_resume'or path(artifacts['quality_unit_execution']['path'])!=path(request['output_root'])/'unit_resume/execution.json':raise RuntimeError('New stock0 must belong to this exact saved-only owner output')
    if request['input_plan']!=context['original']['input_plan']or request['scientific_recipe']!=plan['scientific_recipe']or request['schema']!=plan['feature_schema']:raise RuntimeError('Original recipe/input/schema lineage changed')
    return plan,context,protocol

def main(args,progress=None):
    if os.name!='posix':raise RuntimeError('Admitted Linux read-only/private-IPC owner required')
    import checkm2_parallel_saved_observer_v001 as observer
    import checkm2_protein_pilot_v001 as pilot
    import checkm2_phase_separated_artifacts_N1 as inventory
    request=read(args.request)
    if sha(args.request)!=args.request_sha256:raise RuntimeError('Own request changed')
    plan,context,protocol=request_gate(request)
    if os.environ.get('TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED')!='1'or os.environ.get('TREE2_PRIVATE_NAMESPACE_VERIFIED')!='1':raise RuntimeError('Existing accepted private read-only runtime required')
    runtime_receipt=read(bind(request['runtime_binding_receipt']));runtime=runtime_receipt['runtime']
    if runtime_receipt['mount_namespace']!=os.readlink('/proc/self/ns/mnt'):raise RuntimeError('Actual runtime namespace differs')
    pilot.legacy.readonly_runtime_gate(runtime['ready']);route,_=pilot.legacy.ipc_runtime_gate(runtime)
    original_recipe=read(bind(plan['scientific_recipe']));abi=original_recipe['runtime_binding'];prefix=path(runtime['prefix'])
    if prefix!=path(abi['canonical_prefix'])or runtime['database_sha256']!=abi['database']['sha256']or runtime['ready']['runtime_image']['sha256']!=abi['image_sha256']or runtime['effective_runtime']['manifest_sha256']!=abi['effective_manifest']['sha256']:raise RuntimeError('Accepted unchanged runtime/DB/model/effective ABI differs')
    if 0 not in os.sched_getaffinity(0):raise RuntimeError('SpareCPU0 unavailable; do not borrow markerCPU2')
    os.sched_setaffinity(0,{0})
    output=path(args.output)
    if output!=path(request['output_root'])or output.exists():raise RuntimeError('New once-only output required; old paths preserved')
    deadline=request['helper_deadline_unix']
    if type(deadline)not in(int,float)or not math.isfinite(deadline)or not 0<deadline-time.time()<=900:raise RuntimeError('Root-bounded saved helper window within900s required')
    deadline=time.monotonic()+deadline-time.time();errors=[]
    companion=request['companion_marker']['linux_owner']
    def controllers():
        rows=[];pid=os.getpid()
        for _ in range(64):
            item=pilot.legacy.stat(pid);rows.append(item)
            if item['parent_pid']<=1:break
            pid=item['parent_pid']
        return rows
    def stop():
        if any(path(p).exists()for p in('state/STOP','state/STOP_CHECKM2_PILOT',request['scoped_stop'])):raise InterruptedError('Project or own saved-stock STOP')
        admission_sha(bind_path,request['protocol_admission']['sha256'],error_sink=errors.append)
        observed=pilot.legacy.stat(companion['pid'])
        if any(observed.get(k)!=companion.get(k)for k in('pid','creation_ticks','boot_id')):raise InterruptedError('Exact companion changed; close own QC only')
        if os.sched_getaffinity(companion['pid'])!={2}:raise InterruptedError('Companion CPU2 binding changed; close own QC only')
        if time.monotonic()>=deadline:raise TimeoutError('Saved-only helper finite deadline')
        if pilot.legacy.mem_available()<LIMITS['linux_available_minimum_bytes']or shutil.disk_usage(R).free<LIMITS['disk_reserve_bytes']:raise RuntimeError('RESOURCE_GATE protective1.75GiB headroom/40GiB reserve')
        if sum(x['rss_bytes']for x in controllers())>LIMITS['linux_total_rss_bytes']:raise RuntimeError('RESOURCE_GATE own Linux controller RSS')
    bind_path=path(request['protocol_admission']['path']);stop()
    if pilot.legacy.mem_available()<LIMITS['fresh_launch_available_minimum_bytes']:raise RuntimeError('Fresh parallel stock launch requires3GiB available; marker remains undisturbed')
    lock=(R/'state/checkm2_pilot.lock').open('r+b')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BaseException:lock.close();raise
    try:
        output.mkdir(parents=True,exist_ok=False);save(output/'once_claim.json',{'request':row(args.request),'saved_phase_authority':request['saved_phase_authority'],'prior_stock_minus15_preserved':True,'only_stock_and_features':True})
        ann=context['annotation'];search=context['search'];faa=bind(ann['selected_faa']);raw=bind(search['raw_diamond'])
        inputs=output/'protein_input';inputs.mkdir();shutil.copyfile(faa,inputs/faa.name)
        resume=output/'resume_output';(resume/'protein_files').mkdir(parents=True);(resume/'diamond_output').mkdir();shutil.copyfile(faa,resume/'protein_files'/faa.name);shutil.copyfile(raw,resume/'diamond_output/DIAMOND_RESULTS.tsv')
        before={'proteins':inventory.exact_faa_inventory(resume/'protein_files',ACC,ann['selected_faa']['sha256']),'search':inventory.exact_diamond_inventory(resume/'diamond_output',{**search['raw_diamond'],'path':(resume/'diamond_output/DIAMOND_RESULTS.tsv').relative_to(R).as_posix()})};save(output/'inventory_before.json',before)
        env=pilot.environment(prefix);env.update({name:'1'for name in('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','TF_NUM_INTRAOP_THREADS','TF_NUM_INTEROP_THREADS')});env['TREE2_EFFECTIVE_ORIGIN_RECEIPT']=str(output/'effective_import_origins.json');tmp=output/'tmp';tmp.mkdir()
        command=[str(prefix/'bin/python'),'-B',route['bootstrap_path'],'--proof',route['proof_path'],'--proof-sha256',route['proof_sha256'],'--receipt',str(output/'target_ipc.json'),'checkm2','predict','--genes','--extension','faa','--threads','1','--lowmem','--resume','--input',str(inputs),'--output-directory',str(resume),'--tmpdir',str(tmp),'--database_path',str(path(runtime['database_path'])),'--dbg_vectors','--debug']
        hooks={'save':save,'stop_gate':stop,'stat':pilot.legacy.stat,'group':lambda pgid:observer.strict_group(pgid,pilot.legacy.stat),'mem_available':pilot.legacy.mem_available,'controller_rows':controllers,'progress':progress or(lambda *a,**k:None),'optional_error_sink':errors.append}
        seconds=min(STOCK_SECONDS,deadline-time.monotonic());save(output/'unit_resume_budget.json',{'allowed_seconds':seconds,'original_phase_cap_seconds':600,'prior_consumed_seconds':51.98104298299586,'remaining_original_phase_seconds':STOCK_SECONDS,'all_original_debits':context['authority']['all_prior_21_unit_receipts']})
        observer.run_unit('unit_resume',command,env,output,seconds,hooks=hooks)
        stock_spent=charged_unit(read(output/'unit_resume/execution.json'),seconds)
        after={'proteins':inventory.exact_faa_inventory(resume/'protein_files',ACC,ann['selected_faa']['sha256']),'search':inventory.exact_diamond_inventory(resume/'diamond_output',{**search['raw_diamond'],'path':(resume/'diamond_output/DIAMOND_RESULTS.tsv').relative_to(R).as_posix()})}
        if before!=after:raise RuntimeError('Stock resume changed saved search/FAA')
        if {x.name for x in resume.glob('feature_vectors_*.pkl')}!={'feature_vectors_1.pkl'}:raise RuntimeError('Exactly one own feature vector required')
        artifacts={'raw_pickle':row(resume/'feature_vectors_1.pkl'),'quality_report':row(resume/'quality_report.tsv'),'quality_unit_execution':row(output/'unit_resume/execution.json'),'selected_faa':ann['selected_faa'],'annotation_receipt':ann['annotation_receipt'],'annotation_unit_execution':ann['unit_execution'],'annotation_commit':context['authority']['reusable_annotation_commit'],'diamond_receipt':search['diamond_receipt'],'diamond_unit_execution':search['unit_execution'],'diamond_validation_unit_execution':search['validation_unit_execution'],'diamond_commit':context['authority']['reusable_diamond_commit']}
        features=output/'feature_validation.json';feature_request=output/'feature_request.json'
        save(feature_request,{**request,'request_schema':'TREE2_PARALLEL_SAVED_STOCK_FEATURE_REQUEST_V001','input_plan':context['original']['input_plan'],'scientific_recipe':plan['scientific_recipe'],'schema':plan['feature_schema'],'artifacts':artifacts,'resume_output':str(resume)})
        remaining=min(LIMITS['feature_seconds'],deadline-time.monotonic());save(output/'unit_feature_validation_budget.json',{'allowed_seconds':remaining,'old_feature_cap_seconds':plan['limits']['per_input_validation_seconds'],'stricter_new_cap_seconds':LIMITS['feature_seconds']})
        command=[str(prefix/'bin/python'),'-B',str(R/'scripts/checkm2_saved_stock_features_v001.py'),'--request',str(feature_request),'--request-sha256',sha(feature_request),'--output',str(features)]
        observer.run_unit('unit_feature_validation',command,env,output,remaining,hooks=hooks)
        feature_spent=charged_unit(read(output/'unit_feature_validation/execution.json'),remaining)
        result=read(features)
        if result.get('finite_domain_features')!=21241 or result.get('exact_FAA_metadata_features')!=22 or result.get('independently_recomputed_membership_features')!=1220 or result.get('membership_mismatches')!=0:raise RuntimeError('Complete own feature validation required')
        member={'accession':ACC,'feature_validation':row(features),'original_annotation_commit':context['authority']['reusable_annotation_commit'],'original_diamond_commit':context['authority']['reusable_diamond_commit'],'quality_unit_execution':artifacts['quality_unit_execution'],'feature_validation_unit_execution':row(output/'unit_feature_validation/execution.json'),'all_original_debits_preserved':True}
        save(output/'commit.json',{'status':'SAVED_STOCK_ROW_PENDING_NATIVE_CLOSURE',**member,'request':row(args.request),'source_manifest':request['source_manifest'],'protocol_admission':request['protocol_admission'],'manifest':manifest(output),'no_annotation_or_search_runs':True,'quality_thresholds_unchanged':True,'production_panel_acceptance':False})
        result={'status':'SAVED_STOCK_ROW_PENDING_NATIVE_CLOSURE','completed_qc_rows':1,'rows':[member],'no_annotation_or_search_runs':True,'admission_read_errors':errors,'old_actual_scientific_seconds_preserved':context['authority']['prior_plus_current_actual_scientific_seconds'],'new_stock_actual_seconds':stock_spent,'new_feature_actual_seconds':feature_spent,'new_scientific_seconds_charged':stock_spent+feature_spent,'prior_plus_new_scientific_seconds':context['authority']['prior_plus_current_actual_scientific_seconds']+stock_spent+feature_spent,'whole_native_namespace_image_lease_closure':'PENDING','quality_thresholds_unchanged':True,'production_panel_acceptance':False};save(output/'result.json',result)
        return result
    except BaseException as error:
        if output.exists():
            try:save(output/'failure.json',{'status':'SAVED_STOCK_FAILED_NO_AUTOMATIC_RETRY','error_type':type(error).__name__,'error':repr(error),'traceback':traceback.format_exc(),'original_saved_phase_authority':request['saved_phase_authority'],'actual_phase_receipts':[row(p)for p in sorted(output.glob('unit_*/execution.json'))],'no_annotation_or_DIAMOND_dispatch':True,'no_unknown_debit_reset':True,'outer_native_namespace_image_lease_closure':'PENDING'})
            except BaseException as persistence_error:raise error from persistence_error
        raise
    finally:fcntl.flock(lock,fcntl.LOCK_UN);lock.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--request',required=True);p.add_argument('--request-sha256',required=True);p.add_argument('--output',required=True);main(p.parse_args())
