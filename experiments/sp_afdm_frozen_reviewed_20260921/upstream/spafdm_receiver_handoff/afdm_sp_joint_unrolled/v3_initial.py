"""Observable-only initial estimators on one common OMP path."""
import math
import time

import torch

from afdm_sp_joint_unrolled.classical_joint_unrolled import omp_sparse_torch


class InitialEstimator:
    def __init__(self, family, parameter=None):
        grids = dict(size=(.5,1.,2.),ridge=(1e-3,1e-2,1e-1),sbl=(1e-4,1e-3,1e-2),b0=(None,))
        if family not in grids or parameter not in grids[family]:
            raise ValueError('unregistered initial estimator')
        self.family, self.parameter = family, parameter
        self.record = None
        self.coefficients = None

    def __call__(self, y, Phi, capacity, sigma2):
        if capacity != 40:
            raise ValueError('v3 initial estimators require the common capacity 40')
        if not torch.isfinite(y).all() or not torch.isfinite(Phi).all():
            raise ValueError('nonfinite initial observation or dictionary')
        started = time.perf_counter()
        path = []
        def observe(support, gains, residual):
            path.append((support, gains.detach().clone(), float(residual.abs().square().sum())))
        h, support = omp_sparse_torch(y, Phi, capacity,
                                      path_observer=observe if self.family == 'size' else None)
        original_support = list(support)
        meta = dict(family=self.family,parameter=self.parameter,nomination_steps=len(support),
                    original_support=original_support)
        if self.family == 'size':
            n=len(y)
            floor=torch.finfo(y.real.dtype).tiny
            values=[n*math.log(max(rss/n,floor))+self.parameter*len(s)*math.log(n) for s,g,rss in path]
            selected=min(range(len(values)),key=lambda i:(values[i],i))
            support,gains,_=path[selected]
            h=torch.zeros_like(h);h[support]=gains
            meta.update(objectives=values,selected_k=len(support),
                        numeric_floor_uses=sum(rss/n<=floor for s,g,rss in path))
        elif support and self.family in ('ridge','sbl'):
            A=Phi[:,support]; gram=A.conj().T@A; rhs=A.conj().T@y
            if self.family == 'ridge':
                lam=self.parameter*gram.diagonal().real.mean()
                if not torch.isfinite(lam) or lam<=0:
                    raise ValueError('invalid ridge dictionary scale')
                gains=torch.linalg.solve(gram+lam*torch.eye(len(support),device=y.device,dtype=y.dtype),rhs)
                meta['lambda']=float(lam)
            else:
                variance=float(sigma2)
                if not math.isfinite(variance) or variance<=0:
                    raise ValueError('SBL requires positive fixed observable noise')
                # A positive observable floor initializes EM; it is not an
                # iteration-wise clip or an additional tuning parameter.
                floor=torch.finfo(y.real.dtype).eps*(y.abs().square().mean()/gram.diagonal().real.mean())
                gamma=torch.maximum(h[support].abs().square(),floor)
                converged=False
                for iteration in range(20):
                    precision=gram/variance+torch.diag(1/gamma).to(y.dtype)
                    factor=torch.linalg.cholesky(precision)
                    covariance=torch.cholesky_inverse(factor)
                    gains=torch.cholesky_solve((rhs/variance)[:,None],factor).squeeze(1)
                    updated=gains.abs().square()+covariance.diagonal().real
                    if not torch.isfinite(updated).all() or (updated<=0).any():
                        raise FloatingPointError('invalid SBL posterior second moment')
                    relative=float(torch.linalg.vector_norm(updated-gamma)/torch.linalg.vector_norm(gamma))
                    gamma=updated
                    if relative<=1e-4:
                        converged=True;break
                selected=gamma>=self.parameter*gamma.max()
                support=[s for s,keep in zip(support,selected.tolist()) if keep]
                gains=gains[selected]
                meta.update(iterations=iteration+1,converged=converged,relative_update=relative,
                            initialization_floor=float(floor),pruning='final gamma threshold; posterior mean; no LS debias')
            h=torch.zeros_like(h);h[support]=gains
        if not torch.isfinite(h).all():
            raise FloatingPointError('nonfinite initial estimate')
        meta.update(support=list(support),seconds=time.perf_counter()-started)
        self.record=meta
        self.coefficients=h.detach().cpu().numpy().copy()
        return h,support
