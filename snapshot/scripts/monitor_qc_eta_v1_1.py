"""Model-free, read-only QC counters and ETA; writes monitor sidecars only."""
from __future__ import annotations
import argparse, ctypes, datetime as dt, hashlib, json, math, os, re, time, uuid
from pathlib import Path

UTC=dt.timezone.utc
MSK=dt.timezone(dt.timedelta(hours=3), "MSK")
SCHEMA="TREE2_MONITOR_QC_ETA_V1"
GOOD_ROW={"SHARED_SEARCH_OWN_ROW_FEATURES_VALIDATED_PENDING_CONTROL_AND_OWNER_CLOSURE", "SHARED_SEARCH_BATCH_STOCK_OWN_ROW_VALIDATED_PENDING_CONTEXT_CLOSURE"}

def now(): return dt.datetime.now(UTC)
def stamp(value=None): return (value or now()).isoformat()
def date(value):
    try: return dt.datetime.fromisoformat(str(value).replace("Z","+00:00")).astimezone(UTC)
    except (ValueError,TypeError): return None
def finite(value): return type(value) in (int,float) and math.isfinite(value) and value>=0
def closed(value): return value.get("status")=="UNIT_EXIT0_GROUP_CLOSED" and type(value.get("exit_code")) is int and value["exit_code"]==0 and value.get("owned_group_empty") is True and value.get("remaining_owned_processes")==[]
def atomic(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    part=path.with_name(path.name+"."+uuid.uuid4().hex+".partial")
    with part.open("w",encoding="utf-8",newline="\n") as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.write("\n");stream.flush();os.fsync(stream.fileno())
    for attempt in range(30):
        try: os.replace(part,path);return
        except PermissionError:
            if attempt==29: raise
            time.sleep(.05)

def win_birth(pid):
    if os.name!="nt": return None
    from ctypes import wintypes as w
    api=ctypes.WinDLL("kernel32",use_last_error=True)
    api.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];api.OpenProcess.restype=w.HANDLE
    api.GetProcessTimes.argtypes=[w.HANDLE,ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME)]
    api.CloseHandle.argtypes=[w.HANDLE]
    handle=api.OpenProcess(0x1000,False,int(pid or 0))
    if not handle: return None
    try:
        birth,exit_,kernel,user=(w.FILETIME() for _ in range(4))
        if not api.GetProcessTimes(handle,ctypes.byref(birth),ctypes.byref(exit_),ctypes.byref(kernel),ctypes.byref(user)): return None
        if exit_.dwLowDateTime or exit_.dwHighDateTime: return None
        return (birth.dwHighDateTime<<32)|birth.dwLowDateTime
    finally: api.CloseHandle(handle)

class Reader:
    def __init__(self,root): self.root=Path(root).resolve();self.cache={};self.errors=[]
    def path(self,value):
        value=str(value)
        linux="/mnt/"+self.root.drive[:1].lower()+"/"+self.root.as_posix()[3:] if self.root.drive else ""
        if linux and value.lower().startswith(linux.lower()+"/"): value=value[len(linux)+1:]
        path=Path(value)
        if not path.is_absolute(): path=self.root/path
        path=path.resolve();path.relative_to(self.root)
        return path
    def read(self,path,required=False):
        try:
            path=self.path(path);stat=path.stat()
            if not path.is_file() or stat.st_size>8*1024*1024: raise ValueError("Not bounded JSON metadata")
            key=(stat.st_mtime_ns,stat.st_size)
            old=self.cache.get(str(path))
            if old and old[0]==key: return old[1]
            raw=path.read_bytes();value=json.loads(raw.decode("utf-8-sig"))
            self.cache[str(path)]=(key,value,hashlib.sha256(raw).hexdigest())
            return value
        except (OSError,ValueError,TypeError) as error:
            if required: self.errors.append(str(path)+": "+str(error))
            return {}
    def bound(self,row):
        if not isinstance(row,dict) or not row.get("path"): raise ValueError("Missing metadata binding")
        value=self.read(row["path"],True);path=self.path(row["path"]);cached=self.cache.get(str(path))
        if not cached or cached[2]!=row.get("sha256") or path.stat().st_size!=row.get("bytes"): raise ValueError("Metadata hash/size mismatch: "+row["path"])
        return value
    def ref(self,path):
        path=self.path(path);self.read(path);entry=self.cache.get(str(path))
        return {"path":path.relative_to(self.root).as_posix(),"sha256":entry[2],"bytes":path.stat().st_size} if entry else None

def calibrate(samples,remaining_proteins,remaining_genomes):
    if not samples or remaining_proteins is None: return None
    proteins=sum(s["query_proteins"] for s in samples);genomes=sum(s["genomes"] for s in samples)
    search=sum(s["search_seconds"] for s in samples);other=sum(max(0,s["wall_seconds"]-s["search_seconds"]) for s in samples)
    if proteins<=0 or genomes<=0: return None
    return {"search_seconds_per_query_protein":search/proteins,"residual_wall_seconds_per_new_genome":other/genomes,
            "remaining_seconds":remaining_proteins*search/proteins+remaining_genomes*other/genomes,
            "completed_cohorts_used":len(samples),"completed_genomes_used":genomes,"completed_query_proteins_used":proteins}

def successor(r):
    """Read the public handoff only; bind its launch, contract, argv and plan."""
    runtime=r.read("state/local_continuation_current_runtime.json")
    directory=runtime.get("state_directory","state/local_continuation_queue_v1")
    handoff=r.read(str(directory)+"/handoff.json")
    worker=handoff.get("worker") or {}
    if not worker or (worker.get("role") and "QC" not in str(worker["role"])): return None
    found={"status":"UNRESOLVED","worker":worker,"session":None,"proofs":[]}
    try:
        if type(worker.get("pid")) is not int or worker["pid"]<=0 or type(worker.get("windows_creation_filetime_100ns")) is not int or worker["windows_creation_filetime_100ns"]<=0: raise ValueError("Missing exact creation identity")
        launch=r.bound(worker["launch_receipt"])
        identity=launch.get("native_owner") or launch.get("worker_identity") or launch.get("worker") or launch
        for key in ("pid","windows_creation_filetime_100ns"):
            if identity.get(key)!=worker.get(key): raise ValueError("Handoff/launch owner mismatch")
        contract=r.bound(launch["contract"]);args=contract.get("arguments",[])
        if not isinstance(args,list) or len(args)>256: raise ValueError("Invalid bounded argument vector")
        def argument(flag):
            if args.count(flag)!=1 or args.index(flag)+1>=len(args): raise ValueError("Missing unique "+flag)
            return args[args.index(flag)+1]
        plan_path=r.path(argument("--input-plan"));expected=argument("--input-plan-sha256")
        plan_ref=r.ref(plan_path)
        if not re.fullmatch("[0-9a-f]{64}",str(expected)) or not plan_ref or plan_ref["sha256"]!=expected: raise ValueError("Input-plan expected SHA mismatch")
        plan=r.bound(plan_ref)
        if plan.get("accepted_registry"): r.bound(plan["accepted_registry"])
        registration=r.path(contract["registration_directory"])
        if registration!=r.path(worker["launch_receipt"]["path"]).parent: raise ValueError("Registration path mismatch")
        work=registration.parent.relative_to(r.root).as_posix()
        owner=r.read(work+"/native_owner.json")
        if owner and any(owner.get("native_owner",{}).get(k)!=identity.get(k) for k in ("pid","windows_creation_filetime_100ns")): raise ValueError("Native owner/launch mismatch")
        found.update(status="CANONICAL_PLAN_BOUND_SESSION_PENDING",work=work,owner=owner or {"native_owner":identity,"started_utc":launch.get("registered_utc")},plan=plan,plan_ref=plan_ref,proofs=[worker["launch_receipt"],launch["contract"],plan_ref])
        # Actual request binds both its parent plan and its declared output_root.
        # Its location need not share the native folder's name/version.
        candidates=[]
        step=r.read(work+"/step.json")
        for value in (plan.get("output_root"),plan.get("session_root"),step.get("run_directory")):
            if value:
                path=r.path(value)
                for parent in [path,*list(path.parents)[:5]]:
                    try: parent.relative_to(r.root)
                    except ValueError: continue
                    candidates.append(parent/"bulk_parent_runtime_request.json")
        candidates.extend(sorted((r.root/"analysis").glob("checkm2_qc_persistent_session_*/session/bulk_parent_runtime_request.json"))[:64])
        for candidate in dict.fromkeys(candidates):
            request=r.read(candidate)
            if (request.get("parent_plan") or {}).get("sha256")!=expected: continue
            r.bound(request["parent_plan"])
            output=r.path(request["output_root"])
            if output!=r.path(candidate).parent: raise ValueError("Request output_root mismatch")
            if request.get("native_launch"):
                actual=r.bound(request["native_launch"])
                if actual.get("native_owner")!=identity: raise ValueError("Request native owner mismatch")
            found.update(status="CANONICAL_PLAN_AND_REQUEST_BOUND",session=output.relative_to(r.root).as_posix())
            found["proofs"].append(r.ref(candidate));break
    except (KeyError,ValueError,OSError,TypeError,IndexError) as error:
        found["status"]="UNRESOLVED";found["error"]=str(error)
    return found

class Estimator:
    def __init__(self,root):
        self.root=Path(root).resolve();self.reader=Reader(root);self.output=self.root/"state/monitor_qc_eta_v1";self.sequence=0
    def build(self):
        r=self.reader;r.errors=[];at=now();stage=r.read("state/stages/04.json",True);cfg=r.read("state/monitor_qc_eta_v1/input.json")
        discovery=successor(r);canonical=(discovery or {}).get("plan",{});session_known=True
        if discovery:
            work=discovery.get("work","state/monitor_qc_eta_v1/unresolved_owner")
            owner=discovery.get("owner",{"native_owner":discovery["worker"]})
            session_known=discovery.get("session") is not None
            session=discovery.get("session") or "state/monitor_qc_eta_v1/unresolved_session"
        else:
            work=cfg.get("work_root","work/checkm2_qc_persistent_native_v002")
            log=stage.get("log_path","")
            if log:
                try:
                    candidate=r.path(log).parent
                    if re.fullmatch(r"checkm2_qc_persistent_native_v\d+",candidate.name): work=candidate.relative_to(self.root).as_posix()
                except ValueError: pass
            owner=r.read(work+"/native_owner.json",True)
            session=cfg.get("session_root","analysis/checkm2_qc_persistent_session_v002/session")
            suffix=re.search(r"_v(\d+)$",work)
            if suffix: session="analysis/checkm2_qc_persistent_session_v"+suffix[1]+"/session"
        identity=owner.get("native_owner",{})
        request=r.read(session+"/bulk_parent_runtime_request.json",session_known)
        authority=r.bound(request["campaign_authority"]) if request.get("campaign_authority") else {}
        data=r.bound(authority["campaign_data"]) if authority.get("campaign_data") else (r.bound(canonical["campaign_data"]) if canonical.get("campaign_data") else {})
        groups=data.get("cohorts",[]);bulk=set(authority.get("ordered_new_accessions",data.get("ordered_new_accessions",[])));history=authority.get("historical_review_only",data.get("historical_review_only",[]))
        token=owner.get("token") or stage.get("windows_launch_token")
        sub=(stage.get("current_substep") or {}) if stage.get("windows_launch_token")==token else {}
        step=r.read(work+"/step.json")
        if token and step.get("windows_launch_token")==token: sub=step
        current=int(sub.get("current_cohort",0) or 0);plan=r.read(session+f"/cohort_plans/{current:03d}/input_plan.json")
        reuse=r.read(session+"/reused_first_feature.json");saved_count=int(reuse.get("status")=="ORIGINAL_FIRSTFV0_REUSED_NO_CURRENT_UNIT_OR_DEBIT")
        saved={};saved_accession=None
        if saved_count and reuse.get("original_checkpoint"):
            saved=r.bound(reuse["original_checkpoint"]);saved_accession=saved.get("accession")
        if not saved_count and canonical.get("reused_first_feature_checkpoint") and canonical.get("reused_first_feature_authority"):
            # Previously validated saved features remain validated during a new
            # preflight; this does not assert current-session reuse has happened.
            r.bound(canonical["reused_first_feature_authority"])
            saved=r.bound(canonical["reused_first_feature_checkpoint"]);saved_accession=saved.get("accession")
            saved_count=int(bool(saved_accession))
        # Use the latest verified public method registry, never change that registry.
        registries=sorted((self.root/"metadata").glob("checkm2_accepted_method_result_registry_v*.json"),key=lambda p:int(re.search(r"v(\d+)\.json$",p.name)[1]),reverse=True)
        registry={};accepted=set();supported=set()
        intent=r.read("state/qc_campaign_queue_v1/intent.json")
        if intent.get("queue"):
            queue=r.bound(intent["queue"]);supported={x["accession"] for x in queue.get("rows",[]) if x.get("source_supported_scope") is True}
        for file in registries:
            value=r.read(file)
            try:
                authorities={}
                for row in value.get("rows",[]):
                    auth=row.get("authority") or value.get("cohort_authority")
                    if not auth: raise ValueError("Missing method acceptance authority")
                    authorities[auth["sha256"]]=auth
                if value.get("additional_baseline"): authorities[value["additional_baseline"]["authority"]["sha256"]]=value["additional_baseline"]["authority"]
                for auth in authorities.values():
                    status=str(r.bound(auth).get("status",""))
                    if "ACCEPT" not in status or "HELD" in status: raise ValueError("Unaccepted authority")
                names=value.get("accepted_unique_method_accessions",[])
                if not names or any(not isinstance(x,str) for x in names): raise ValueError("Missing exact accepted list")
                registry=value;accepted=set(names)&supported;break
            except (ValueError,OSError,KeyError): continue
        features=set();checkpointed=set();samples=[];calibration_proofs=[];closed_cohorts=0
        timings=r.bound(cfg["timing_input"]) if cfg.get("timing_input") else r.read("state/monitor_qc_eta_v1/timing_input.json")
        protein_map={int(x["index"]):x for x in timings.get("cohorts",[]) if type(x.get("query_proteins")) is int and x["query_proteins"]>0}
        for group in groups[:128]:
            index=int(group["cohort_index"]);names=group["accessions"];folder=session+f"/cohorts/{index:03d}"
            cohort_plan=r.ref(session+f"/cohort_plans/{index:03d}/input_plan.json")
            for accession in names:
                commit=r.read(folder+"/rows/"+accession+"/commit.json")
                if commit.get("status") not in GOOD_ROW or commit.get("accession")!=accession or not cohort_plan or commit.get("input_plan_sha256")!=cohort_plan["sha256"]: continue
                try:
                    unit=r.bound(commit["per_row_unit_executions"]["unit_feature_validation"]);value=r.bound(commit["feature_validation"])
                    if not closed(unit) or value.get("status")!="P20_FEATURES_PASS_PENDING_NATIVE_CLOSURE" or value.get("accession")!=accession: continue
                    if (value.get("finite_domain_features"),value.get("exact_FAA_metadata_features"),value.get("independently_recomputed_membership_features"),value.get("membership_mismatches"))!=(21241,22,1220,0): continue
                    if value.get("input_plan_sha256")!=commit.get("input_plan_sha256"): continue
                    features.add(accession)
                except (ValueError,OSError,KeyError): continue
            result=r.read(folder+"/result.json")
            if result.get("status")!="COHORT_COMPUTED_PENDING_CONTEXT_CLOSURE" or result.get("cohort_index")!=index or [x.get("accession") for x in result.get("rows",[])]!=names or not set(names)<=features: continue
            try: r.bound(result["input_plan"])
            except (ValueError,OSError,KeyError): continue
            checkpointed.update(names);closed_cohorts+=1;calibration_proofs.append(r.ref(folder+"/result.json"))
            executions=[]
            base=r.path(folder)
            if base.exists():
                for file in list(base.rglob("execution.json"))[:1024]:
                    value=r.read(file)
                    if closed(value) and date(value.get("started_utc")) and date(value.get("ended_utc")): executions.append(value)
            search=r.read(folder+"/shared/unit_shared_diamond/execution.json")
            if index in protein_map and executions and closed(search):
                wall=(max(date(x["ended_utc"]) for x in executions)-min(date(x["started_utc"]) for x in executions)).total_seconds()
                if finite(wall) and finite(search.get("elapsed_seconds")):
                    samples.append({"index":index,"genomes":len(names),"query_proteins":protein_map[index]["query_proteins"],"wall_seconds":wall,"search_seconds":search["elapsed_seconds"]})
        phase=sub.get("declared_unit") or "runtime/model/database preparation"
        unit_path=session+f"/cohorts/{current:03d}/shared/"+str(phase)+"/execution.json"
        terminal=r.read(unit_path);command=r.path(session+f"/cohorts/{current:03d}/shared/"+str(phase)+"/command.json")
        phase_elapsed=terminal.get("elapsed_seconds") if finite(terminal.get("elapsed_seconds")) else sub.get("elapsed_seconds")
        if not finite(phase_elapsed) and command.exists(): phase_elapsed=max(0,at.timestamp()-command.stat().st_mtime)
        own_live=type(identity.get("windows_creation_filetime_100ns")) is int and identity["windows_creation_filetime_100ns"]>0 and win_birth(identity.get("pid"))==identity["windows_creation_filetime_100ns"]
        failed=str(sub.get("status",stage.get("status",""))).upper()
        stopped=bool(terminal and not closed(terminal)) or bool(re.search("FAIL|STOP|ERROR",failed))
        queue_state="STOPPED_OR_REPAIRING" if stopped else ("OWNER_ACTIVE" if own_live else "OWNER_EXIT_OR_HANDOFF_PENDING")
        budget=r.read(session+"/bulk_actual_debit_ledger.json")
        cold_limit=float(canonical.get("cold_session_seconds",cfg.get("cold_context_seconds",172800)));started=date(owner.get("started_utc"));cold_remaining=max(0,cold_limit-(at-started).total_seconds()) if started else None
        science_remaining=budget.get("remaining_new_global_seconds",canonical.get("limits",{}).get("global_scientific_seconds"))
        total_proteins=timings.get("total_query_proteins")
        used_proteins=sum(protein_map[x["index"]]["query_proteins"] for x in samples)
        remaining_proteins=max(0,total_proteins-used_proteins) if type(total_proteins) is int and len(protein_map)==len(groups) else None
        estimate=calibrate(samples,remaining_proteins,len(bulk-checkpointed))
        eta={"status":"UNCALIBRATED_NO_COMPLETED_BATCH","basis":"No completed full cohort; interrupted phases are not throughput samples.","remaining_seconds":None,"finish_utc":None,"finish_msk":None,"display_text":"CALIBRATING - no completed batch; whole-QC ETA not yet measurable.","full_queue_remaining_seconds":None,"historical_review_eta_seconds":None,"completed_cohorts_used":len(samples),"completed_genomes_used":len(checkpointed),"provisional_reference":timings.get("provisional_reference")}
        if estimate:
            eta.update(estimate);eta["status"]="PROTEIN_WEIGHTED_SAMPLE_LIMITED";eta["basis"]="Successful whole-cohort wall time: search seconds/query protein plus residual seconds/new genome; five historical reviews and final acceptance extra."
            eta["display_text"]=f"BULK estimate {estimate['remaining_seconds']/3600:.1f}h; {len(samples)} completed cohort(s), protein-weighted and sample-limited. Five history reviews/final acceptance extra."
            if own_live and not stopped:
                finish=at+dt.timedelta(seconds=estimate["remaining_seconds"]);eta["finish_utc"]=stamp(finish);eta["finish_msk"]=finish.astimezone(MSK).strftime("%Y-%m-%d %H:%M MSK")
            else: eta["display_text"]+=" Finish clock suspended during stop/repair."
        elif checkpointed: eta["status"]="CALIBRATION_WAIT_QUERY_COUNTS";eta["display_text"]="CALIBRATING - completed batch exists; bound query-protein counts required for a defensible forecast."
        diagnostics=[]
        if estimate and finite(science_remaining) and estimate["remaining_seconds"]>science_remaining: diagnostics.append("Estimated remaining workload exceeds the finite remaining scientific allowance; diagnostic only, no pause or gate change.")
        if estimate and finite(cold_remaining) and estimate["remaining_seconds"]>cold_remaining: diagnostics.append("Estimated remaining wall time exceeds the current finite context allowance; diagnostic only, not a completion ETA or biological failure.")
        all_validated=accepted|features|({saved_accession} if saved_count and saved_accession else set())
        dispatcher=r.read("state/local_continuation_queue_v1/dispatcher_status.json")
        self.sequence+=1
        value={"schema":SCHEMA,"updated_utc":stamp(at),"sequence":self.sequence,"updater_pid":os.getpid(),"owner":{**identity,"verified_live":own_live},
                "campaign":{"source_supported":len(supported),"accepted_supported":len(accepted),"saved_validated_reused":saved_count,"saved_already_accepted":saved_accession in accepted,"bulk_total":len(bulk),"first_new_genomes_completed":len(features&bulk),"new_genomes_feature_validated":len(features&bulk),"new_bulk_cohort_checkpointed":len(checkpointed&bulk),"new_bulk_accepted":len(accepted&bulk),"all_method_validated_including_saved":len(all_validated&supported),"remaining_processing_and_history":len((bulk|set(history))-(features|accepted)),"historical_review_remaining":len(set(history)-accepted),"closed_cohorts":closed_cohorts,"panel_acceptance":"NOT_GRANTED"},
                "batch":{"number":min(current+1,len(groups)) if groups else None,"total":len(groups),"genomes":len(plan.get("accessions",groups[current]["accessions"] if current<len(groups) else [])),"controls":len(plan.get("controls",data.get("controls",[]))),"phase":phase,"phase_elapsed_seconds":phase_elapsed,"phase_status":terminal.get("status") or sub.get("status"),"failure_kind":terminal.get("failure_kind"),"features_validated_in_current_batch":len(features&set(plan.get("accessions",[])))},
                "queue":{"status":queue_state,"automatic_controller_preserved":True,"dispatcher_status":dispatcher.get("status"),"dispatcher_pid":dispatcher.get("dispatcher_pid"),"ordinary_AI_calls":dispatcher.get("AI_calls_during_wait"),"no_retry_or_launch_by_monitor":True},
                "eta":eta,"budgets":{"science_remaining_seconds":science_remaining,"cold_context_remaining_seconds":cold_remaining,"cold_context_limit_seconds":cold_limit,"limits_are_not_completion_ETA":True,"diagnostics":diagnostics},
                "calibration_samples":samples,"provenance":[x for x in [r.ref(work+"/native_owner.json"),r.ref(session+"/bulk_parent_runtime_request.json"),r.ref(unit_path),r.ref(session+"/reused_first_feature.json"),*calibration_proofs[:48]] if x],"read_warnings":r.errors[:10],"scientific_files_or_state_modified":False}
        value["path_resolution"]={k:v for k,v in (discovery or {"status":"LEGACY_STAGE_BOUND"}).items() if k not in {"plan","owner","worker"}}
        value["provenance"].extend((discovery or {}).get("proofs",[]))
        value["campaign"]["saved_reused_current_session"]=reuse.get("status")=="ORIGINAL_FIRSTFV0_REUSED_NO_CURRENT_UNIT_OR_DEBIT"
        if discovery and discovery["status"]=="UNRESOLVED":
            # The existing GUI's schema guard presents its explicit unavailable
            # block. This avoids PowerShell formatting null arithmetic as zero.
            value["schema"]="TREE2_MONITOR_QC_ETA_UNRESOLVED_V1"
            for key in value["campaign"]:
                if key not in {"source_supported","accepted_supported","panel_acceptance"}: value["campaign"][key]=None
            value["batch"]={"number":None,"total":None,"genomes":None,"controls":None,"phase":"NEW WORKER DETECTED - path unresolved","phase_elapsed_seconds":None,"phase_status":"UNKNOWN","features_validated_in_current_batch":None}
            value["eta"].update(status="NEW_WORKER_PATH_UNRESOLVED",display_text="NEW WORKER DETECTED - path unresolved. Current campaign counts and speed are UNKNOWN; no prior attempt is carried forward.",remaining_seconds=None,finish_utc=None,finish_msk=None)
            value["queue"]["status"]="NEW_WORKER_PATH_UNRESOLVED"
        return value

def main():
    p=argparse.ArgumentParser();p.add_argument("--project-root",type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument("--interval",type=int,default=30);p.add_argument("--once",action="store_true");a=p.parse_args()
    if a.interval<30: p.error("interval must be at least30seconds")
    service=Estimator(a.project_root);service.output.mkdir(parents=True,exist_ok=True)
    atomic(service.output/"owner.json",{"pid":os.getpid(),"started_utc":stamp(),"script":str(Path(__file__).resolve()),"role":"READ_ONLY_MONITOR_ESTIMATOR_NOT_SCIENCE_OR_DISPATCHER"})
    while True:
        try:
            value=service.build();atomic(service.output/"current.json",value)
            if a.once: print(json.dumps(value));return
        except Exception as error:
            with (service.output/"errors.jsonl").open("a",encoding="utf-8") as log: log.write(json.dumps({"at_utc":stamp(),"error":repr(error)})+"\n")
            if a.once: raise
        time.sleep(a.interval)

if __name__=="__main__": main()
