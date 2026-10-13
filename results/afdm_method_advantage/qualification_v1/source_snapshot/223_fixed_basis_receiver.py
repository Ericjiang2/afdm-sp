"""Explicit fixed-basis representation for the common uncoded CPU receiver."""
import time
import numpy as np
import torch

from .bandlimited_basis import BasisGeometry,basis_from_public_band,group_omp
from .bandlimited_estimation import fit_coefficients


class FixedBasisRepresentation:
    """Own one public basis/support; reuse the receiver's CE/BP/noise loop."""
    def __init__(self,*,family,q,n,c1,c2,delay_cap,prefix_length,sample_rate,max_doppler,coefficient_cap=60):
        start=time.perf_counter()
        if (type(coefficient_cap) is not int or not q<=coefficient_cap
                or coefficient_cap//q>delay_cap+1):
            raise ValueError('valid public coefficient/group budget required')
        basis=basis_from_public_band(family,n,q,sample_rate,max_doppler)
        self.geometry=BasisGeometry(basis,c1=c1,c2=c2,delay_cap=delay_cap,prefix_length=prefix_length)
        self.public=dict(family=family,q=q,n=n,c1=c1,c2=c2,delay_cap=delay_cap,prefix_length=prefix_length,
            sample_rate=sample_rate,max_doppler=max_doppler,coefficient_cap=coefficient_cap)
        self.selection=None
        self.counts=dict(basis_builds=1,initial_dictionary_builds=0,group_selections=0,
            group_qr=0,group_lstsq=0,initial_gels=0,dals_designs=0,channel_reconstructions=0)
        self.times=dict(public_basis=time.perf_counter()-start,initial=0.,dals_design=0.,channel=0.)

    def validate(self,cfg,y):
        g=self.geometry
        if (y.device.type!='cpu' or y.dtype!=torch.complex64 or cfg.dtype!=torch.complex64
                or cfg.N!=g.n or cfg.l_max!=g.delay_cap or cfg.c1!=g.c1 or cfg.c2!=g.c2
                or self.selection is not None):
            raise ValueError('fresh fixed basis matched to the complex64 CPU receiver required')

    def _array(self,value):
        if (not isinstance(value,torch.Tensor) or value.device.type!='cpu'
                or value.dtype!=torch.complex64 or value.shape!=(self.geometry.n,)
                or value.requires_grad or not torch.isfinite(value).all()):
            raise ValueError('fixed-basis inference requires a finite CPU complex64 vector')
        return value.detach().numpy()

    def initialize(self,y,pilot):
        if self.selection is not None:raise ValueError('fixed basis cannot reuse a previous observation')
        start=time.perf_counter()
        observed,p=self._array(y),self._array(pilot)
        design=np.ascontiguousarray(self.geometry.sensing(p))
        self.counts['initial_dictionary_builds']+=1
        selection=group_omp(design,observed,group_size=self.geometry.q,
                            max_groups=self.public['coefficient_cap']//self.geometry.q)
        self.counts['group_selections']+=1
        self.counts['group_qr']+=selection['group_qr_calls']
        self.counts['group_lstsq']+=selection['refits']
        fit=fit_coefficients(design[:,selection['columns']],observed)
        self.counts['initial_gels']+=fit['completed_solves']
        self.selection=selection;self.initial_fit=fit
        self.initial_pilot=p.copy();self.initial_observation=observed.copy()
        self.initial_design=design[:,selection['columns']].astype(np.complex64)
        self.times['initial']+=time.perf_counter()-start
        delays=torch.tensor(np.repeat(selection['delays'],self.geometry.q),dtype=torch.long)
        indices=torch.tensor(np.tile(np.arange(self.geometry.q),len(selection['delays'])),dtype=torch.long)
        return delays,indices,torch.from_numpy(fit['coefficients'].copy())

    def design(self,symbols):
        if self.selection is None:raise ValueError('basis support not initialized')
        start=time.perf_counter()
        self.last_symbols=self._array(symbols).copy()
        self.last_design=self.geometry.sensing(self.last_symbols,self.selection['delays']).astype(np.complex64)
        self.counts['dals_designs']+=1
        self.times['dals_design']+=time.perf_counter()-start
        return torch.from_numpy(self.last_design)

    def channel(self,coefficients):
        if (self.selection is None or coefficients.device.type!='cpu' or coefficients.dtype!=torch.complex64
                or coefficients.shape!=(len(self.selection['columns']),) or coefficients.requires_grad
                or not torch.isfinite(coefficients).all()):
            raise ValueError('finite coefficients on initialized fixed basis required')
        start=time.perf_counter()
        self.last_coefficients=coefficients.detach().numpy().copy()
        self.last_channel=self.geometry.channel(self.selection['delays'],self.last_coefficients).astype(np.complex64)
        self.counts['channel_reconstructions']+=1
        self.times['channel']+=time.perf_counter()-start
        return torch.from_numpy(self.last_channel)

    def result(self):
        if self.selection is None:raise ValueError('basis representation was not consumed')
        output=dict(public=self.public,basis=self.geometry.basis.copy(),selection=self.selection,
            counts=self.counts.copy(),times=self.times.copy(),initial_fit=self.initial_fit,
            initial_pilot=self.initial_pilot,initial_observation=self.initial_observation,
            initial_design=self.initial_design,last_channel=self.last_channel,last_coefficients=self.last_coefficients)
        if self.counts['dals_designs']:
            output.update(last_design=self.last_design,last_symbols=self.last_symbols)
        return output
