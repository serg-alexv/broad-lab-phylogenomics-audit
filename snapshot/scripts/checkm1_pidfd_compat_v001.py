"""Exact-task libc pidfds for the scientific Python; never a PID signal fallback."""
import ctypes
import os
import signal

_LIBC = None

def _libc():
    global _LIBC
    if _LIBC is None:
        value = ctypes.CDLL(None, use_errno=True)
        value.pidfd_open.argtypes = [ctypes.c_int, ctypes.c_uint]
        value.pidfd_open.restype = ctypes.c_int
        value.pidfd_send_signal.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint]
        value.pidfd_send_signal.restype = ctypes.c_int
        _LIBC = value
    return _LIBC

def pidfd_open(pid, flags=0):
    if hasattr(os, 'pidfd_open'):
        return os.pidfd_open(pid, flags)
    descriptor = _libc().pidfd_open(pid, flags)
    if descriptor < 0:
        number = ctypes.get_errno()
        raise OSError(number, os.strerror(number))
    return descriptor

def pidfd_send_signal(descriptor, number, info=None, flags=0):
    if info is not None:
        raise ValueError('Only null siginfo is admitted')
    if hasattr(signal, 'pidfd_send_signal'):
        return signal.pidfd_send_signal(descriptor, number, None, flags)
    if _libc().pidfd_send_signal(descriptor, number, None, flags) < 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
