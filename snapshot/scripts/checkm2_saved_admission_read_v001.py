"""Strict small immutable-admission reads. No scientific or process imports."""
from pathlib import Path
import errno, hashlib, os, stat, time

def identity(value):
    return value.st_dev,value.st_ino,value.st_size,value.st_mtime_ns

def admission_sha(value,expected,*,error_sink=None,read=os.read,sleep=time.sleep):
    """Reopen and restart at most three ENOMEM-only reads; never accept a failed read.

    A 4KiB syscall avoids hashlib.file_digest's 256KiB readinto buffer.
    This is an operational API change, not proof of the historical ENOMEM cause.
    Each successful check hashes ALL exact current bytes, on a regular unchanged
    file. A source change, other error, or exhausted ENOMEM remains fatal.
    """
    path=Path(value)
    for attempt in range(3):
        descriptor=None
        try:
            before=path.lstat()
            if not stat.S_ISREG(before.st_mode) or before.st_size>1048576:
                raise RuntimeError('Admission must be a regular file no larger than1MiB')
            descriptor=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
            opened=os.fstat(descriptor)
            if identity(before)!=identity(opened):raise RuntimeError('Admission changed while opening')
            digest=hashlib.sha256();count=0
            while True:
                chunk=read(descriptor,4096)
                if not chunk:break
                count+=len(chunk)
                if count>1048576:raise RuntimeError('Admission grew beyond bounded read')
                digest.update(chunk)
            after=os.fstat(descriptor);current=path.lstat()
            if count!=opened.st_size or identity(opened)!=identity(after) or identity(after)!=identity(current):
                raise RuntimeError('Admission changed during current full-byte hash')
            actual=digest.hexdigest()
            if actual!=expected:raise InterruptedError('Pinned current admission bytes changed')
            return actual
        except OSError as error:
            if error.errno!=errno.ENOMEM or attempt==2:raise
            if error_sink is not None:
                error_sink({'operation':'strict_current_admission_os_read','errno':error.errno,'attempt':attempt+1,'path':str(path),'full_read_and_SHA_still_required':True})
            sleep((.05,.20)[attempt])
        finally:
            if descriptor is not None:os.close(descriptor)
    raise AssertionError('Unreachable admission read boundary')
