"""Tree2 V007 fixed native custody helpers. Copyright 2026 the project authors.

NativeProcess, exact identity, Job structure and kernel helpers are copied
verbatim from the accepted sibling harness; no service/network/daemon code is
imported. Original notices retained. This module launches nothing on import.
"""
from __future__ import annotations
import ctypes
from ctypes import wintypes
from ctypes import wintypes as w
import json,os,hashlib,uuid
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[2]
class Hold(RuntimeError):
    """Retained native custody/evidence is unavailable; no replacement."""


def now():
    return datetime.now(timezone.utc).isoformat()

def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    with tmp.open('w', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)

def load_json(path, maximum=2_000_000):
    if path.stat().st_size > maximum:
        raise ValueError('JSON exceeds read bound')
    return json.loads(path.read_text(encoding='utf-8-sig'))

def win_identity(pid, expected=None):
    """Read-only exact handle observation; never signals or adopts the process."""
    if os.name != 'nt':
        return {'state': 'UNAVAILABLE_PLATFORM', 'pid': pid}
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.GetProcessTimes.restype = wintypes.BOOL
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000 | 0x100000, False, int(pid))
    if not handle:
        return {'state': 'UNOBSERVED_UNKNOWN', 'pid': pid, 'winerror': ctypes.get_last_error()}
    try:
        created, exited, system, user = (wintypes.FILETIME() for _ in range(4))
        if not kernel.GetProcessTimes(handle, *[ctypes.byref(v) for v in (created, exited, system, user)]):
            return {'state': 'UNOBSERVED_UNKNOWN', 'pid': pid}
        ft = (created.dwHighDateTime << 32) | created.dwLowDateTime
        state = 'LIVE_EXACT_IDENTITY' if expected is None or ft == int(expected) else 'IDENTITY_MISMATCH'
        if state == 'LIVE_EXACT_IDENTITY':
            wait_result = kernel.WaitForSingleObject(handle, 0)
            if wait_result == 0:
                state = 'EXITED_OBSERVED_HANDLE'
            elif wait_result != 258:
                state = 'WAIT_OBSERVATION_UNKNOWN'
        return {'state': state, 'pid': pid, 'creation_filetime': str(ft), 'expected_creation_filetime': str(expected) if expected else None}
    finally:
        kernel.CloseHandle(handle)

class BasicLimits(ctypes.Structure):
    _fields_ = [('ProcessTime',ctypes.c_longlong),('JobTime',ctypes.c_longlong),('Flags',w.DWORD),
        ('MinWS',ctypes.c_size_t),('MaxWS',ctypes.c_size_t),('ActiveLimit',w.DWORD),
        ('Affinity',ctypes.c_size_t),('Priority',w.DWORD),('Scheduling',w.DWORD)]

class IOCounters(ctypes.Structure):
    _fields_ = [(n,ctypes.c_ulonglong) for n in ('ReadOps','WriteOps','OtherOps','ReadBytes','WriteBytes','OtherBytes')]

class ExtendedLimits(ctypes.Structure):
    _fields_ = [('Basic',BasicLimits),('IO',IOCounters),('ProcessMemory',ctypes.c_size_t),
        ('JobMemory',ctypes.c_size_t),('PeakProcess',ctypes.c_size_t),('PeakJob',ctypes.c_size_t)]

class MemoryStatus(ctypes.Structure):
    _fields_ = [('Length',w.DWORD),('Load',w.DWORD)] + [(n,ctypes.c_ulonglong) for n in
        ('TotalPhys','AvailPhys','TotalPage','AvailPage','TotalVirtual','AvailVirtual','Extended')]

def kernel():
    if os.name != 'nt':
        raise RuntimeError('Native audit custody currently supports this Windows host only')
    k = ctypes.WinDLL('kernel32',use_last_error=True)
    k.CreateJobObjectW.argtypes=[ctypes.c_void_p,w.LPCWSTR]; k.CreateJobObjectW.restype=w.HANDLE
    k.OpenJobObjectW.argtypes=[w.DWORD,w.BOOL,w.LPCWSTR]; k.OpenJobObjectW.restype=w.HANDLE
    k.SetInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD]
    k.QueryInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD,ctypes.c_void_p]
    k.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE]
    k.IsProcessInJob.argtypes=[w.HANDLE,w.HANDLE,ctypes.POINTER(w.BOOL)]
    k.TerminateJobObject.argtypes=[w.HANDLE,w.UINT]
    k.TerminateProcess.argtypes=[w.HANDLE,w.UINT]
    k.CloseHandle.argtypes=[w.HANDLE]
    k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD]; k.OpenProcess.restype=w.HANDLE
    k.GetProcessTimes.argtypes=[w.HANDLE]+[ctypes.POINTER(w.FILETIME)]*4
    k.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD]; k.WaitForSingleObject.restype=w.DWORD
    k.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)]
    k.GlobalMemoryStatusEx.argtypes=[ctypes.POINTER(MemoryStatus)]
    return k

class NativeProcess:
    """An owned query/synchronize handle, with creation identity checked once.

    Exiting and process-ID reuse cannot change the process referenced by handle.
    No PROCESS_TERMINATE right is requested or exposed.
    """
    def __init__(self, handle, pid, expected=None, require_executable=True):
        if os.name != 'nt':
            raise Hold('Native retained custody requires Windows')
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        k = self.kernel
        k.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        k.GetProcessTimes.restype = wintypes.BOOL
        k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k.WaitForSingleObject.restype = wintypes.DWORD
        k.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        k.GetExitCodeProcess.restype = wintypes.BOOL
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        k.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        k.QueryFullProcessImageNameW.restype = wintypes.BOOL
        self.handle, self.pid = handle, int(pid)
        try:
            times = [wintypes.FILETIME() for _ in range(4)]
            if not k.GetProcessTimes(handle, *[ctypes.byref(t) for t in times]):
                raise Hold('Creation time unavailable on retained handle')
            self.birth = str((times[0].dwHighDateTime << 32) | times[0].dwLowDateTime)
            if expected is not None and self.birth != str(expected):
                raise Hold('Retained process creation identity mismatched')
            size, buffer = wintypes.DWORD(32768), ctypes.create_unicode_buffer(32768)
            if not k.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                self.image_query_error = ctypes.get_last_error()
                if require_executable or self.exit_code() is None:
                    raise Hold('Retained process executable unavailable')
                self.executable = None  # Windows may remove image data after exit.
            else:
                self.executable = Path(buffer.value)
        except BaseException:
            self.close()
            raise

    @classmethod
    def open(cls, pid, expected, require_executable=True):
        if os.name != 'nt' or not expected:
            raise Hold('Exact Windows creation identity required')
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        handle = kernel.OpenProcess(0x1000 | 0x100000, False, int(pid))
        if not handle:
            raise Hold('Exact process handle unavailable; native exit UNKNOWN')
        return cls(handle, pid, expected, require_executable=require_executable)

    @classmethod
    def child(cls, process):
        # Duplicate the Popen-owned creation handle before Popen can release it.
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        kernel.DuplicateHandle.argtypes = [wintypes.HANDLE, wintypes.HANDLE, wintypes.HANDLE,
            ctypes.POINTER(wintypes.HANDLE), wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.DuplicateHandle.restype = wintypes.BOOL
        owner, duplicate = kernel.GetCurrentProcess(), wintypes.HANDLE()
        if not kernel.DuplicateHandle(owner, int(process._handle), owner, ctypes.byref(duplicate), 0x1000 | 0x100000, False, 0):
            raise Hold('Child handle duplication failed; do not relaunch')
        return cls(duplicate, process.pid)

    def exit_code(self):
        result = self.kernel.WaitForSingleObject(self.handle, 0)
        if result == 258:
            return None
        if result != 0:
            raise Hold('Retained handle wait failed; exit UNKNOWN')
        code = wintypes.DWORD()
        if not self.kernel.GetExitCodeProcess(self.handle, ctypes.byref(code)):
            raise Hold('Native exit code unavailable')
        return code.value  # 259 can be an actual terminal code after signalled wait.

    def wait(self, seconds):
        result = self.kernel.WaitForSingleObject(self.handle, int(seconds * 1000))
        if result not in (0, 258):
            raise Hold('Retained handle wait failed')
        return self.exit_code()

    def identity(self):
        return {'pid': self.pid, 'creation_filetime': self.birth}

    def close(self):
        if getattr(self, 'handle', None):
            self.kernel.CloseHandle(self.handle)
            self.handle = None

LIFECYCLE_NAMES=('tree2_activation_common_v007.py','tree2_dispatcher_v007.py',
 'tree2_status_io_v007.py','tree2_supervisor_v007.py','tree2_controller_launcher_v007.py',
 'tree2_controller_task_entry_v007.py','tree2_controller_task_v007.ps1','tree2_v007_event_prompt.txt')
def source_status(root=ROOT):
    root=Path(root).resolve()
    if root!=ROOT.resolve():raise RuntimeError('Fixed Tree2 root differs')
    authority=root/'metadata/finalization_recovery_20261103/controller_v007/Root_authority.json'
    raw=authority.read_bytes();value=json.loads(raw)
    pins=value.get('lifecycle_sources')
    if not isinstance(pins,dict) or set(pins)!=set(LIFECYCLE_NAMES):
        raise RuntimeError('Exact complete V007 lifecycle source profile required')
    for name,binding in pins.items():
        p=root/'scripts/finalization_controller_v007'/name;b=p.read_bytes()
        actual={'path':str(p.resolve()),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
        if binding!=actual:raise RuntimeError('Lifecycle source changed: '+name)
    return {'admission_sha256':hashlib.sha256(raw).hexdigest(),'verified_source_count':len(pins)}
