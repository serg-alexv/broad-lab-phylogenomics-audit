"""Bounded ownership cleanup; individual Linux signals require creation identity."""
from pathlib import Path
import os,json,time,datetime,hashlib
from checkm2_optional_telemetry_v001 import structured_exception
from checkm1_pidfd_compat_v001 import pidfd_open, pidfd_send_signal

R=Path(__file__).resolve().parents[1]

def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def identity(pid):
    fields=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
    return {'pid':int(pid),'parent_pid':int(fields[1]),'process_group':int(fields[2]),
            'creation_ticks':int(fields[19]),'state':fields[0],
            'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}

def same_identity(expected,current):
    return (isinstance(expected,dict) and isinstance(current,dict)
            and all(expected.get(key) is not None and expected.get(key)==current.get(key)
                    for key in ('pid','boot_id','creation_ticks')))

def current_matching(expected):
    try:
        current=identity(expected['pid'])
        return current if same_identity(expected,current) else None
    except (FileNotFoundError,ProcessLookupError):return None

def track_descendants(root,known):
    """Retain creation identities across reparenting and distinct process groups."""
    table={}
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():continue
        try:table[int(path.name)]=identity(int(path.name))
        except (FileNotFoundError,ProcessLookupError):pass
    roots={pid:row for pid,row in known.items()
           if same_identity(row,table.get(pid))}
    if root is not None and same_identity(root,table.get(root['pid'])):
        roots[root['pid']]={**table[root['pid']],'depth':0}
    changed=True
    while changed:
        changed=False
        for pid,row in table.items():
            if pid not in roots and row['parent_pid'] in roots:
                roots[pid]={**row,'depth':roots[row['parent_pid']].get('depth',0)+1}
                changed=True
    for pid,row in roots.items():
        prior=known.get(pid)
        if prior is not None and not same_identity(prior,row):
            raise RuntimeError('Tracked PID was reused; never substitute its creation identity')
        known[pid]={**row,'depth':max(row.get('depth',0),(prior or {}).get('depth',0))}
    return [known[pid] for pid in roots]

def scoped_stop(path,token,reason):
    path=Path(path).resolve()
    if not path.is_relative_to(R):raise RuntimeError('STOP escapes the project')
    value={'owner_token':token,'reason':reason,'at_utc':utc(),
           'scope':'TREE2_FULL919_GENE_ASSESSMENT_V001_ONLY'}
    try:
        with path.open('x',encoding='utf-8') as handle:
            json.dump(value,handle,indent=2);handle.write('\n');handle.flush();os.fsync(handle.fileno())
        created=True
    except FileExistsError:created=False
    return {'path':str(path),'created_by_this_owner':created,
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

def immutable_handoff(evidence,blocker,token,kind,value):
    folder=Path(evidence)/'unresolved_ownership';folder.mkdir(parents=True,exist_ok=True)
    path=folder/(token+'_'+kind+'.json')
    row={'status':'FAILED_OWNED_WORK_UNKNOWN_CLOSURE','at_utc':utc(),
         'token':token,'kind':kind,'no_relaunch':True,**value}
    with path.open('x',encoding='utf-8') as handle:
        json.dump(row,handle,indent=2);handle.write('\n');handle.flush();os.fsync(handle.fileno())
    binding={'status':'HARD_NO_RELAUNCH_UNRESOLVED_OWNERSHIP','token':token,
             'immutable_handoff_path':str(path),
             'immutable_handoff_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    try:
        with Path(blocker).open('x',encoding='utf-8') as handle:
            json.dump(binding,handle,indent=2);handle.write('\n');handle.flush();os.fsync(handle.fileno())
    except FileExistsError:
        binding['existing_blocker_preserved']=True
        binding['existing_blocker_sha256']=hashlib.sha256(Path(blocker).read_bytes()).hexdigest()
    return {**binding,'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

def cleanup_linux_helper(child,root,known,stop_path,token):
    """30s STOP grace, matching individual TERM5s/KILL5s; never claims unmount."""
    import signal
    started=time.monotonic();started_utc=utc();events=[];errors=[];stop=None;forced=False
    if root is None:errors.append({'operation':'root creation identity unavailable','closure':'UNKNOWN'})
    def remaining():
        rows=[]
        for row in known.values():
            try:
                if current_matching(row) is not None:rows.append(row)
            except OSError as error:
                errors.append({'operation':'verify captured identity','identity':row,'exception':structured_exception(error,f"/proc/{row['pid']}/stat")})
                rows.append({**row,'current_identity_verification':'UNKNOWN'})
        return rows
    def refresh():
        try:return track_descendants(root,known)
        except Exception as error:
            errors.append({'operation':'descendant census','exception':structured_exception(error,'/proc'),'at_utc':utc()})
            return remaining()
    def wait_until(until):
        while time.monotonic()<until:
            refresh()
            if child.poll() is not None and not remaining():return
            time.sleep(min(.2,max(0,until-time.monotonic())))
    def signal_matching(number):
        nonlocal forced
        refresh()
        for row in sorted(known.values(),key=lambda x:(x.get('depth',0),x['pid']),reverse=True):
            try:current=current_matching(row)
            except OSError as error:
                errors.append({'operation':'pre-signal current identity','identity':row,'exception':structured_exception(error,f"/proc/{row['pid']}/stat")});continue
            if current is None:continue
            if row['pid']<=1 or row['pid']==os.getpid():
                errors.append({'operation':'refused unsafe identity','identity':row});continue
            descriptor=None
            try:
                # A pidfd pins the task while its creation identity is rechecked.
                descriptor=pidfd_open(row['pid'],0)
                if not same_identity(row,identity(row['pid'])):continue
                pidfd_send_signal(descriptor,number,None,0);forced=True
                events.append({'signal':int(number),'expected_identity':row,
                               'observed_identity':current,'method':'pidfd_send_signal','at_utc':utc()})
            except (ProcessLookupError,FileNotFoundError):pass
            except (OSError,RuntimeError) as error:errors.append({'operation':'individual signal','identity':row,'exception':structured_exception(error,f"pidfd:{row['pid']}")})
            finally:
                if descriptor is not None:os.close(descriptor)
    refresh()
    try:stop=scoped_stop(stop_path,token,'FATAL_FULL919_GENE_ASSESSMENT_OWNED_CLEANUP')
    except Exception as error:errors.append({'operation':'scoped STOP','exception':structured_exception(error,stop_path)})
    wait_until(started+30)
    if child.poll() is None or remaining():signal_matching(signal.SIGTERM);wait_until(started+35)
    if child.poll() is None or remaining():signal_matching(signal.SIGKILL);wait_until(started+40)
    refresh();left=remaining();code=child.poll();reaped=False
    if code is not None:code=child.wait();reaped=True
    return {'started_utc':started_utc,'elapsed_seconds':time.monotonic()-started,
            'policy_seconds':{'STOP_grace':30,'TERM':5,'KILL':5},'stop':stop,
            'tracked_creation_identities':list(known.values()),'signals':events,'errors':errors,
            'actual_helper_exit_code':code,'actual_helper_handle_reaped':reaped,
            'helper_poll':child.poll(),'remaining_matching_identities':left,
            'all_captured_identities_absent':not left,
            'forced_action':forced,'closure_proven':reaped and not left and not errors,
            'ordinary_runtime_closure':'UNKNOWN_FORCED_OR_FATAL_SUPERVISOR_PATH'}
