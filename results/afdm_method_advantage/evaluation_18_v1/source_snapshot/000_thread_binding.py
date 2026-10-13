"""Effective CPU BLAS binding, based on wideband.receiver_experiment.blas_binding.

Apple Accelerate mode is per calling execution thread (thread_api.h). Environment
variables and an empty threadpoolctl inventory alone are not evidence of one
thread. Unknown/unobservable backends fail instead of being silently accepted.
"""
import ctypes
import numpy as np
import threadpoolctl


def blas_binding():
    pools=threadpoolctl.threadpool_info()
    result=dict(threadpoolctl=threadpoolctl.__version__,pools=pools)
    name=getattr(np.__config__,'CONFIG',{}).get('Build Dependencies',{}).get('blas',{}).get('name')
    result['numpy_blas_name']=name
    if name=='accelerate':
        lib=ctypes.CDLL('/System/Library/Frameworks/Accelerate.framework/Accelerate')
        lib.BLASSetThreading.argtypes=[ctypes.c_uint];lib.BLASSetThreading.restype=ctypes.c_int
        lib.BLASGetThreading.argtypes=[];lib.BLASGetThreading.restype=ctypes.c_uint
        if lib.BLASSetThreading(1)!=0:raise RuntimeError('Accelerate single-thread mode unsupported')
        mode=int(lib.BLASGetThreading())
        if mode!=1:raise RuntimeError('Accelerate effective thread mode differs')
        result['accelerate_current_thread_mode']=mode
    elif not any(p.get('user_api')=='blas' for p in pools):
        raise RuntimeError('effective BLAS backend cannot be verified')
    if any(p['num_threads']!=1 for p in pools):raise ValueError('effective BLAS/OpenMP pools must be single threaded')
    return result


def verify_effective(rt):
    current=blas_binding()
    if current!=rt.environment['effective_blas_post_bootstrap']:raise ValueError('effective BLAS binding changed')
    return current
