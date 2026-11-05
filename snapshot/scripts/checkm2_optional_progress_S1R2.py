"""S1R2 optional callback I/O only; critical observers never call this wrapper."""
from checkm2_optional_telemetry_v001 import structured_exception

def safe_call(callback,*args,error_sink=None,**kwargs):
    try:
        callback(*args,**kwargs)
        return None
    except OSError as error:
        detail=structured_exception(error,'optional_progress_callback')
        detail['classification']='OPTIONAL_PROGRESS_IO_UNAVAILABLE'
        if error_sink is not None:
            try:error_sink(detail)
            except OSError:pass
        return detail
