"""Use the immutable qualified SCREEN128 estimator; change only the code arms."""
from experiments.afdm_acquisition_screen128_20261007.core import estimate, simulate

ARMS = ('quadratic', 'random', 'optimized')
METHODS = ('SCREEN128', 'FULL')
__all__ = ['ARMS', 'METHODS', 'estimate', 'simulate']
