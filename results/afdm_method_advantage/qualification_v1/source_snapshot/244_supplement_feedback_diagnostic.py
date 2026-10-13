"""Explicit offline one-shot true-symbol CE diagnostic; never a legal feedback prior."""
import numpy as np
import torch
from .supplement_feedback import CodeFeedback
from .supplement_messages import oracle_symbols
from .budgeted_support_diagnostics import array_hash


class DiagnosticCodeSymbols:
    def __init__(self,code,symbols,*,tag,checkpoint):
        if type(checkpoint) is not int or checkpoint<0:raise ValueError('explicit nonnegative checkpoint required')
        value=oracle_symbols(symbols,tag=tag)
        if (len(value['mu'])*2!=code['n'] or
                not np.isin(value['mu'].real,(-.5,.5)).all() or
                not np.isin(value['mu'].imag,(-.5,.5)).all()):
            raise ValueError('oracle requires matching already-scaled QPSK data symbols')
        self.code=code;self.tag=tag;self.checkpoint=checkpoint
        self.symbols=value['mu'];self.symbols.flags.writeable=False
        self.supplied_sha256=value['sha256'];self.records=[];self.begun=False;self.consumed=0
        self.feedback=CodeFeedback(code,checkpoint=checkpoint,control='zero') if tag=='I2realloc' else None

    def begin(self,n,outer_iterations,device):
        if self.begun:raise ValueError('diagnostic controller is single-use')
        if (self.tag not in ('I2','I2realloc') or type(self.checkpoint) is not int or self.checkpoint<0 or
                array_hash(self.symbols)!=self.supplied_sha256 or
                (self.tag=='I2' and self.feedback is not None) or
                (self.tag=='I2realloc' and (type(self.feedback) is not CodeFeedback or
                    self.feedback.code is not self.code or self.feedback.control!='zero' or
                    self.feedback.enabled is not True or self.feedback.checkpoint!=self.checkpoint))):
            raise ValueError('diagnostic identity or composed zero-feedback contract changed')
        if n*2!=self.code['n'] or self.checkpoint>=outer_iterations-1:
            raise ValueError('diagnostic requires matching symbols and following CE step')
        self.begun=True;self.device=device

    def replace(self,iteration,mean,support_count):
        if not self.begun:raise ValueError('diagnostic not initialized')
        if iteration!=self.checkpoint+1:return mean
        if self.records or self.consumed:raise ValueError('duplicate oracle application')
        if not support_count:raise ValueError('oracle target CE has empty support; no consumption')
        delivered=torch.tensor(self.symbols.copy(),dtype=mean.dtype,device=mean.device)
        self.records.append(dict(tag=self.tag,truth_access='true_symbols_oracle',legal_receiver_input=False,
            checkpoint=self.checkpoint,outer_iter=iteration,supplied_sha256=self.supplied_sha256,
            original_mean_sha256=array_hash(mean.detach().cpu().numpy()),
            consumed_mean_sha256=array_hash(delivered.detach().cpu().numpy()),
            variance=0.,variance_used_by_CE=False,status='prepared'))
        return delivered

    def consume(self,iteration,A):
        if iteration!=self.checkpoint+1:return
        if len(self.records)!=1 or self.consumed:raise ValueError('oracle consumption without unique preparation')
        self.records[0].update(status='consumed',A_sha256=array_hash(A.detach().cpu().numpy()))
        self.consumed=1

    def finish(self):
        if self.consumed!=1:raise ValueError('requested oracle CE was not consumed exactly once')
