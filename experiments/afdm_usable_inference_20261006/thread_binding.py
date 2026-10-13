"""Reuse full effective BLAS/OpenMP inventory verification without weakening it."""
from experiments.afdm_coherent_structure_20261006.thread_binding import blas_binding, verify_effective

__all__ = ['blas_binding', 'verify_effective']
