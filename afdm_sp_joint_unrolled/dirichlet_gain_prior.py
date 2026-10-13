"""One-use fixed integer-bin covariance controller; no continuous fit."""
import time
import numbers
import numpy as np
import torch
from .dirichlet_prior import build_precision


class DirichletGainPrior:
    def __init__(self, kind='dirichlet', strength=.1):
        if (kind not in ('ridge', 'diagonal', 'dirichlet')
                or isinstance(strength, (bool, np.bool_)) or not isinstance(strength, numbers.Real)
                or not np.isfinite(strength) or strength < 0):
            raise ValueError('registered prior and finite nonnegative strength required')
        self.kind, self.strength = kind, float(strength)
        self.record = None
        self.started = False

    def begin(self):
        if self.started:
            raise ValueError('a gain prior is one-use')
        self.started = True

    def initialize(self, n, delays, dopplers, gains):
        if not self.started or self.record is not None or gains.device.type != 'cpu':
            raise ValueError('fresh CPU prior required')
        start = time.perf_counter()
        d, k, g = [x.detach().cpu().numpy().copy() for x in (delays, dopplers, gains)]
        result = build_precision(n, d, k, g, kind=self.kind)
        self.precision = torch.tensor(result['precision'], dtype=gains.dtype, device=gains.device)
        self.delays, self.dopplers = delays.clone(), dopplers.clone()
        self.record = dict(result, kind=self.kind, strength=self.strength, initial_gains=g,
                           delays=d, dopplers=k, construction_seconds=time.perf_counter()-start,
                           penalty_calls=0, truth_access='none', continuous_parameter_fits=0)

    def penalty(self, a, delays, dopplers):
        if self.record is None or not torch.equal(delays, self.delays) or not torch.equal(dopplers, self.dopplers):
            raise ValueError('fixed prior support changed')
        self.record['penalty_calls'] += 1
        return self.strength * a.abs().square().sum() / a.shape[1] * self.precision
