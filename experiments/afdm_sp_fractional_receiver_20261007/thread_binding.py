"""Reuse the observable single-thread contract; include Torch in the inventory."""
from experiments.afdm_coherent_structure_20261006.thread_binding import blas_binding


def binding(torch):
    result = blas_binding()
    result.update(torch_intraop=torch.get_num_threads(),
                  torch_interop=torch.get_num_interop_threads())
    if result['torch_intraop'] != 1 or result['torch_interop'] != 1:
        raise RuntimeError('Torch thread binding differs from one CPU')
    return result
