"""Offline one-shot true-data CE controller; no decoder or detector prior input."""
import numpy as np
import torch

from .budgeted_support_diagnostics import array_hash
from .supplement_feedback import CodeFeedback


class OneShotTrueDataCE:
    def __init__(self, symbols):
        value = np.asarray(symbols)
        if (value.ndim != 1 or not value.size or not np.iscomplexobj(value)
                or not np.isfinite(value).all()
                or not np.isin(value.real, (-.5, .5)).all()
                or not np.isin(value.imag, (-.5, .5)).all()):
            raise ValueError('true data CE needs finite already-scaled QPSK symbols')
        self.symbols = value.astype(np.complex128, copy=True)
        self.symbols.flags.writeable = False
        self.supplied_sha256 = array_hash(self.symbols)
        self.records = []
        self.begun = False
        self.consumed = 0

    def begin(self, n, outer_iterations, configured_iterations, ce_iterations, feedback, mode, device):
        if self.begun:
            raise ValueError('true data CE controller is single-use')
        if (self.symbols.shape != (n,) or array_hash(self.symbols) != self.supplied_sha256
                or outer_iterations < 3 or outer_iterations != configured_iterations
                or tuple(ce_iterations) != tuple(range(1, outer_iterations)) or mode != 'mean'
                or type(feedback) is not CodeFeedback or not feedback.enabled
                or feedback.checkpoint != 1 or feedback.control != 'legal'
                or feedback.consumer != 'both' or feedback.stop_on_valid_codeword
                or feedback.diagnostic_perturbation is not None):
            raise ValueError('true data CE requires the legal t=1 mean-CE feedback route')
        self.begun = True
        self.device = device

    def replace(self, iteration, proposal_mean, proposal_variance, support_count):
        if not self.begun or iteration != 1 or self.records or not support_count:
            raise ValueError('true data CE must replace exactly one supported t=1 proposal')
        delivered = torch.as_tensor(self.symbols.copy(), dtype=proposal_mean.dtype,
                                    device=proposal_mean.device)
        self.records.append(dict(outer_iter=1, location='after_code_feedback_ce_before_x_total',
            truth_access='true_data_ce_only', legal_receiver_input=False,
            supplied_sha256=self.supplied_sha256,
            proposal_mean_sha256=array_hash(proposal_mean.detach().cpu().numpy()),
            proposal_variance_sha256=array_hash(proposal_variance.detach().cpu().numpy()),
            consumed_mean_sha256=array_hash(delivered.detach().cpu().numpy()),
            true_variance=0., variance_used_by_CE=False, status='prepared'))
        return delivered

    def consume(self, iteration, A):
        if iteration != 1 or len(self.records) != 1 or self.consumed:
            raise ValueError('true data CE consumption needs unique preparation')
        self.records[0].update(A_sha256=array_hash(A.detach().cpu().numpy()), status='consumed')
        self.consumed = 1

    def finish(self):
        if self.consumed != 1:
            raise ValueError('true data CE was not consumed exactly once')
