"""Benign self-expiring persistence fixture. No AI, scientific tools, auth or signals."""
from pathlib import Path
import argparse
import ctypes
from ctypes import wintypes
import json
import os
import sys
import time

import local_tree2_dispatcher as b
import local_tree2_detached_launch_v002 as job

R=Path(__file__).resolve().parents[1]

def job_membership(kernel,handle):
    inside=wintypes.BOOL()
    kernel.k.IsProcessInJob.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.POINTER(wintypes.BOOL)]
    if not kernel.k.IsProcessInJob(handle,None,ctypes.byref(inside)):
        raise ctypes.WinError(ctypes.get_last_error())
    return bool(inside.value)

def observe_parent(kernel,expected):
    if expected is None:return {'original_parent_identity_observed':False,'original_exit_code':'UNKNOWN'}
    handle=kernel.k.OpenProcess(0x1000,False,expected['pid'])
    if not handle:return {'original_parent_not_live':ctypes.get_last_error()==87,'OpenProcess_error':ctypes.get_last_error(),'original_exit_code':'UNKNOWN'}
    try:
        actual=kernel.identity(handle,expected['pid'])
        code=ctypes.c_uint32()
        if not kernel.k.GetExitCodeProcess(handle,ctypes.byref(code)):raise ctypes.WinError(ctypes.get_last_error())
        return {'current_birth':actual,'original_parent_not_live':b.worker_key(actual)!=b.worker_key(expected) or code.value!=259,
          'original_exit_code':int(code.value) if b.worker_key(actual)==b.worker_key(expected) and code.value!=259 else 'UNKNOWN'}
    finally:kernel.close(handle)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output-directory',required=True)
    parser.add_argument('--seconds',required=True,type=int)
    parser.add_argument('--label',required=True,choices=['DIRECT','DETACHED'])
    args=parser.parse_args()
    if not 30<=args.seconds<=180:raise RuntimeError('Fixture deadline must be30..180 seconds')
    directory=b.inside(R,args.output_directory);directory.mkdir(parents=True,exist_ok=False)
    kernel=b.Windows();current=ctypes.c_void_p(-1);owner=kernel.identity(current,os.getpid())
    parent_handle=kernel.k.OpenProcess(0x1000,False,os.getppid())
    try:parent=kernel.identity(parent_handle,os.getppid()) if parent_handle else None
    finally:
        if parent_handle:kernel.close(parent_handle)
    record={'schema':'TREE2_BENIGN_PERSISTENCE_FIXTURE_STARTED_V002','owner':owner,'parent_at_start':parent,
      'label':args.label,'in_any_job_at_start':job_membership(kernel,current),
      'immediate_current_job_at_start':job.current_job_snapshot(kernel),'seconds':args.seconds,
      'started_utc':b.utc(),'AI_scientific_runtime_auth_or_signal_actions':False}
    b.exclusive(directory/'started.json',record)
    started=time.monotonic();count=0
    with (directory/'heartbeat.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
        while time.monotonic()-started<args.seconds:
            value={'at_utc':b.utc(),'owner':owner,'count':count,'elapsed_seconds':time.monotonic()-started,
              'in_any_job':job_membership(kernel,current),'immediate_current_job':job.current_job_snapshot(kernel),
              'parent_observation':observe_parent(kernel,parent)}
            stream.write(json.dumps(value)+'\n');stream.flush();os.fsync(stream.fileno());count+=1
            time.sleep(min(2,max(0,args.seconds-(time.monotonic()-started))))
    b.exclusive(directory/'self_deadline_reached.json',{'status':'SELF_DEADLINE_REACHED_OWN_EXIT_NOT_OBSERVABLE',
      'owner':owner,'ended_utc':b.utc(),'elapsed_seconds':time.monotonic()-started,'heartbeats':count,
      'actual_own_exit':'UNKNOWN_UNTIL_SEPARATE_RETAINED_OS_OBSERVER','no_process_termination_used':True})
    return 0

if __name__=='__main__':raise SystemExit(main())
