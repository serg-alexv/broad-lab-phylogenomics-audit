"""Stable Windows RSS sampler; ctypes types and prototypes are initialized once.

Returns summed RSS for the native owner and its retained live WSL client.
No resource ceiling, process creation, model or scientific policy lives here.
"""
import ctypes
from ctypes import wintypes

class MemoryCounters(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('faults', wintypes.DWORD)] + [
        (name, ctypes.c_size_t) for name in
        ('peak', 'rss', 'peakPaged', 'paged', 'peakNonpaged', 'nonpaged',
         'pagefile', 'peakPagefile', 'private')]

_API = None

def summed_native_rss(child=None):
    global _API
    if _API is None:
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        kernel.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
        psapi = ctypes.WinDLL('psapi', use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(MemoryCounters), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        _API = kernel, psapi
    kernel, psapi = _API
    current = kernel.GetCurrentProcess()
    if not kernel.SetProcessAffinityMask(current, 1):
        raise ctypes.WinError(ctypes.get_last_error())
    handles = [current]
    if child is not None and child.poll() is None:
        handles.append(int(child._handle))
    rss = 0
    for handle in handles:
        counters = MemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        rss += counters.rss
    return rss
