"""Observed-only physical refit; fixed model constants, no truth-bearing system."""
from types import SimpleNamespace
import numpy as np
from afdm_sp_joint_unrolled.afdm_env import AFDMEnvMixin
from afdm_sp_joint_unrolled.afdm_baselines import construct_sensing_matrix
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash


class PhysicalChannelRefit:
    def __init__(self, system, arm, *, soft_lambda_normalized=None):
        if arm not in ('m-group','m-param-budget','m-param-reference','m-soft'):
            raise ValueError('unknown registered physical arm')
        from afdm_sp_joint_unrolled.direction_physical import resolve_soft_lambda
        self.soft_lambda_normalized=resolve_soft_lambda(arm,soft_lambda_normalized)
        names=('N_total','c1','c2','l_max_cap','k_max_cap','k_guard','k_leak',
               'frac_prune_rel_thres','gen_h_daft_convention')
        self.geometry=SimpleNamespace(**{k:getattr(system,k) for k in names})
        self.geometry.dirichlet_alpha=AFDMEnvMixin.dirichlet_alpha
        g=self.geometry
        if (g.N_total!=1024 or g.l_max_cap!=102 or g.k_max_cap!=2 or g.k_leak!=2
                or g.frac_prune_rel_thres!=.01 or g.gen_h_daft_convention!='python'
                or int(round(2*g.N_total*g.c1))!=5):
            raise ValueError('physical refit differs from frozen geometry')
        self.arm=arm

    def __call__(self, *, y, pilot, H, x_soft, support, gains, sigma_base):
        from afdm_sp_joint_unrolled.direction_physical import fit_physical_observed
        g=self.geometry; ids=np.asarray(support)
        if (ids.ndim!=1 or (ids.size and ids.dtype.kind not in 'iu') or ids.size>40
                or len(set(ids.tolist()))!=ids.size or np.any(ids<0) or np.any(ids>=515)):
            raise ValueError('illegal physical refit support')
        ids=ids.astype(np.int64)
        y,pilot,H,x_soft,gains=[np.asarray(a,dtype=np.complex128) for a in (y,pilot,H,x_soft,gains)]
        if (y.shape!=(g.N_total,) or pilot.shape!=y.shape or x_soft.shape!=y.shape
                or H.shape!=(g.N_total,g.N_total) or gains.shape!=(len(ids),)
                or any(not np.isfinite(a).all() for a in (y,pilot,H,x_soft,gains))):
            raise ValueError('invalid observed physical refit state')
        A=construct_sensing_matrix(g.N_total,pilot+x_soft,g.c1,g.c2,g.l_max_cap,g.k_max_cap)[:,ids]
        fit=fit_physical_observed(g,y,A,ids,gains,sigma_base,self.arm,
            soft_lambda_normalized=self.soft_lambda_normalized)
        coefficients=np.asarray(fit['coefficients'],dtype=np.complex128)
        if coefficients.shape!=gains.shape or not np.isfinite(coefficients).all():
            raise ValueError('invalid fitted coefficients')
        fitted_H=AFDMEnvMixin.gen_h_daft(g,coefficients,ids//5,ids%5-2)
        diagnostics=dict(fit['diagnostics'],A_sha256=array_hash(A),
            support=ids.tolist(),gains_before_sha256=array_hash(gains),
            gains_after_sha256=array_hash(coefficients),H_before_sha256=array_hash(H),
            H_after_sha256=array_hash(fitted_H),truth_access='none',
            sensing_input='pilot+x_soft; already power-scaled',
            terminal_sigma_policy='unchanged B_star terminal sigma; no oracle recalibration')
        return {'H':fitted_H,'gains':coefficients,'diagnostics':diagnostics}
