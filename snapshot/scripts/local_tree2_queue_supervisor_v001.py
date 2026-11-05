"""Source-held external owner for V3 dispatcher processes; never launches science."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid

import local_tree2_dispatcher as b
from checkm2_optional_progress_S1R2 import safe_call

R = Path(__file__).resolve().parents[1]

def cause_hash(cause):
    return hashlib.sha256(json.dumps(cause, sort_keys=True).encode()).hexdigest()

def exact_owner(left, right):
    return (isinstance(left, dict) and isinstance(right, dict)
        and type(left.get('pid')) is int and type(right.get('pid')) is int
        and type(left.get('windows_creation_filetime_100ns')) is int
        and type(right.get('windows_creation_filetime_100ns')) is int
        and left['pid'] > 0 and left['windows_creation_filetime_100ns'] > 0
        and left['pid'] == right['pid']
        and left['windows_creation_filetime_100ns'] == right['windows_creation_filetime_100ns']
        and isinstance(left.get('creation_time_utc'), str)
        and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{7}Z',left['creation_time_utc']) is not None
        and left['creation_time_utc'] == right.get('creation_time_utc'))

def terminal_gate(terminal, child_owner, core_source, config):
    if terminal.get('schema') != 'TREE2_DISPATCHER_TERMINAL_ERROR_V3':
        raise RuntimeError('Missing typed dispatcher terminal error')
    if not exact_owner(terminal.get('dispatcher_owner'), child_owner):
        raise RuntimeError('Terminal error belongs to an unproved/stale dispatcher owner')
    if terminal.get('core_source') != core_source or terminal.get('config') != config:
        raise RuntimeError('Terminal error source/config binding differs')
    cause = terminal.get('rootcause')
    required = {'code','type','last_operation','operation_path','message_template'}
    if not isinstance(cause, dict) or set(cause) != required:
        raise RuntimeError('Required structured root cause is absent')
    if (cause['code'] != 'DISPATCHER_EXCEPTION'
        or not all(isinstance(cause[k], str) and cause[k] for k in ('type','last_operation'))
        or not (cause['operation_path'] is None or isinstance(cause['operation_path'], str))
        or not isinstance(cause['message_template'], str)):
        raise RuntimeError('Malformed structured root cause')
    key = cause_hash(cause)
    if terminal.get('rootcause_sha256') != key or terminal.get('root_cause_sha256') != key:
        raise RuntimeError('Structured root cause hash differs')
    if terminal.get('no_science_retry') is not True:
        raise RuntimeError('Process-only repair scope is not explicit')
    return cause, key

def may_repair(allowed, repairs, actual_exit_code, already_claimed):
    return (allowed is True and type(repairs) is int and repairs == 0
        and type(actual_exit_code) is int and actual_exit_code != 0
        and already_claimed is False)

def require_sources(core_source, config, private_config):
    for item in (core_source, config, private_config):
        b.bind(R, item)

def close_popen_handle(child):
    handle = getattr(child, '_handle', None)
    if handle is not None:
        handle.Close()
        child._handle = None

class Supervisor:
    def __init__(self, args):
        self.args = args
        self.config_path = b.inside(R, args.config)
        self.private_path = b.inside(R, args.cli_config)
        config = b.read(self.config_path)
        if Path(config['project_root']).resolve() != R:
            raise RuntimeError('Supervisor project root differs')
        self.directory = b.inside(R, config['state_directory'])
        if self.directory != R/'state/local_continuation_queue_v1':
            raise RuntimeError('V3 isolated state directory required')
        self.core_path = b.inside(R, args.core_source)
        if self.core_path != R/'scripts/local_tree2_queue_dispatcher_v001.py':
            raise RuntimeError('Only the reviewed V3 dispatcher may be supervised')
        self.core = b.row(R, self.core_path)
        if self.core['sha256'] != args.core_sha256:
            raise RuntimeError('Reviewed V3 source SHA differs')
        self.config = b.row(R, self.config_path)
        self.private = b.row(R, self.private_path)
        self.kernel = b.Windows()
        self.owner = self.kernel.identity(-1, os.getpid())
        self.token = uuid.uuid4().hex
        self.log_directory = R/'work/local_continuation/supervisor_logs'/self.token
        self.log_directory.mkdir(parents=True, exist_ok=False)
        self.unresolved = self.directory/'supervisor_unresolved_owner.json'
        if self.unresolved.exists():
            raise RuntimeError('Existing unresolved supervisor owner blocks relaunch')

    def display(self, status, **values):
        safe_call(b.atomic, self.directory/'supervisor_status.json', {
            'status':status,'updated_utc':b.utc(),'supervisor_owner':self.owner,
            'token':self.token,'model_tokens_used_by_wait':0,**values})

    def run_child(self, failure_event=None):
        require_sources(self.core, self.config, self.private)
        invocation = [sys.executable,'-B',str(self.core_path),'--config',str(self.config_path),
                      '--cli-config',str(self.private_path)]
        if failure_event:
            invocation += ['--dispatcher-failure-event',str(b.bind(R,failure_event)),
                           '--dispatcher-failure-event-sha256',failure_event['sha256']]
        elif self.args.initial_recovery_event and not (self.directory/'checkpoint.json').exists():
            seed={'path':self.args.initial_recovery_event,'sha256':self.args.initial_recovery_sha256}
            invocation += ['--recovery-event',str(b.bind(R,seed)),
                           '--recovery-event-sha256',seed['sha256']]
        attempt = uuid.uuid4().hex
        child = None
        child_owner = None
        reaped = False
        actual_exit = None
        try:
            with (self.log_directory/(attempt+'.stdout.txt')).open('xb') as stdout, \
                 (self.log_directory/(attempt+'.stderr.txt')).open('xb') as stderr:
                child = subprocess.Popen(invocation,stdin=subprocess.DEVNULL,stdout=stdout,
                    stderr=stderr,cwd=R,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                child_owner = self.kernel.identity(int(child._handle),child.pid)
                if not exact_owner(child_owner,child_owner):
                    raise RuntimeError('Initial dispatcher creation identity unproved')
                b.exclusive(self.directory/'supervisor_attempts'/(attempt+'_started.json'), {
                    'supervisor_owner':self.owner,'dispatcher_owner':child_owner,
                    'core_source':self.core,'config':self.config,'private_config':self.private,
                    'invocation':invocation,'failure_event':failure_event,'started_utc':b.utc()})
                while not self.kernel.wait(int(child._handle),30000):
                    self.display('WAITING_DISPATCHER',dispatcher_owner=child_owner)
                handle_code = self.kernel.exit_code(int(child._handle))
                actual_exit = child.wait()
                reaped = True
                if type(actual_exit) is not int or actual_exit != handle_code:
                    raise RuntimeError('Retained dispatcher handle and Popen exit observations differ')
            close_popen_handle(child)
            result = {'schema':'TREE2_RETAINED_DISPATCHER_ACTUAL_EXIT_V003',
                'supervisor_owner':self.owner,'dispatcher_owner':child_owner,
                'actual_exit_code':actual_exit,'retained_handle_reaped':True,
                'child_handles_closed':True,'core_source':self.core,'config':self.config,
                'private_config':self.private,'observed_utc':b.utc(),'science_killed_or_replayed':False}
            target = self.directory/'supervisor_attempts'/(attempt+'_actual_exit.json')
            b.exclusive(target,result)
            return result,b.row(R,target)
        except BaseException as error:
            # Never infer guest/CLI/science closure or signal their processes here.
            value = {'schema':'TREE2_SUPERVISOR_UNRESOLVED_OWNER_V003',
                'supervisor_owner':self.owner,'dispatcher_owner':child_owner,
                'known_child_pid':child.pid if child else None,'actual_exit_code':actual_exit,
                'retained_handle_reaped':reaped,'closure':'UNKNOWN_NO_RESTART',
                'error_type':type(error).__name__,'at_utc':b.utc(),'no_science_retry':True}
            b.exclusive(self.unresolved,value)
            raise
        finally:
            # Closing our handle is not a kill and never substitutes for the exit receipt.
            if child is not None:
                close_popen_handle(child)

    def run(self):
        repairs = 0
        failure_event = None
        with b.ByteLock(self.directory/'supervisor.lock'):
            while True:
                result,exit_row = self.run_child(failure_event)
                status_path = self.directory/'dispatcher_status.json'
                try:
                    status = b.read(status_path) if status_path.is_file() else {}
                except (OSError,ValueError,TypeError):
                    status = {}  # Optional display cannot establish completion or abort ownership handling.
                if result['actual_exit_code'] == 0 and status.get('status') == 'COMPLETE':
                    config = b.read(self.config_path)
                    handoff = b.validate_handoff(R,b.read(b.inside(R,config['handoff_path'])),
                        config['required_complete_outputs'])
                    if handoff['status'] == 'COMPLETE':
                        self.display('COMPLETE',dispatcher_actual_exit=exit_row)
                        return 0
                terminal_path = self.directory/'dispatcher_terminal_error.json'
                attention = {'schema':'TREE2_DISPATCHER_EXTERNAL_ATTENTION_V003',
                    'status':'DISPATCHER_STOPPED_REVIEW_REQUIRED','actual_dispatcher_exit':exit_row,
                    'supervisor_owner':self.owner,'at_utc':b.utc(),'no_science_retry':True}
                cause = None
                key = None
                immutable_terminal = None
                try:
                    require_sources(self.core,self.config,self.private)
                    terminal = b.read(terminal_path)
                    cause,key = terminal_gate(terminal,result['dispatcher_owner'],self.core,self.config)
                    immutable_terminal = terminal['immutable_terminal_error']
                    saved = b.read(b.bind(R,immutable_terminal))
                    saved_cause,saved_key = terminal_gate(saved,result['dispatcher_owner'],self.core,self.config)
                    if saved_cause != cause or saved_key != key:
                        raise RuntimeError('Immutable terminal error differs from the current pointer')
                except (OSError,ValueError,TypeError,KeyError,RuntimeError) as error:
                    attention['terminal_gate_error_type'] = type(error).__name__
                    cause = None
                    key = None
                event_path = self.directory/'failure_signals'/(uuid.uuid4().hex+'.json')
                if cause is not None:
                    attention.update(schema='TREE2_LOCAL_DISPATCHER_PROCESS_FAILURE_EVENT_V003',
                        event_kind='DISPATCHER_PROCESS_FAILURE',dispatcher_owner=result['dispatcher_owner'],
                        actual_exit_code=result['actual_exit_code'],retained_handle_reaped=True,
                        child_handles_closed=True,core_source=self.core,config=self.config,
                        private_config=self.private,terminal_error=immutable_terminal,
                        rootcause=cause,rootcause_sha256=key)
                b.exclusive(event_path,attention)
                failure_event = b.row(R,event_path)
                claim = self.directory/'supervisor_process_repair_claims'/((key or 'NO_CAUSE')+'.json')
                if cause is None or not may_repair(self.args.allow_one_process_repair,repairs,
                        result['actual_exit_code'],claim.exists()):
                    self.display('BLOCKED',reason='Exact dispatcher failure recorded; no further process/science retry',attention=failure_event)
                    return 2
                b.exclusive(claim,{'failure_event':failure_event,'at_utc':b.utc(),
                    'exact_source_and_config_only':True,'max_process_repairs':1,'no_science_retry':True})
                repairs += 1
                self.display('ONE_DISPATCHER_PROCESS_REPAIR',failure_event=failure_event)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config',required=True)
    parser.add_argument('--cli-config',required=True)
    parser.add_argument('--core-source',required=True)
    parser.add_argument('--core-sha256',required=True)
    parser.add_argument('--allow-one-process-repair',action='store_true')
    parser.add_argument('--initial-recovery-event')
    parser.add_argument('--initial-recovery-sha256')
    args=parser.parse_args()
    if bool(args.initial_recovery_event)!=bool(args.initial_recovery_sha256):
        parser.error('Recovery event and exact SHA must be supplied together')
    return Supervisor(args).run()

if __name__ == '__main__':
    raise SystemExit(main())
