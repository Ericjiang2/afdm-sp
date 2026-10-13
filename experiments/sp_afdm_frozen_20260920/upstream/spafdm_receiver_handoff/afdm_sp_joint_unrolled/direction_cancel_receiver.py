"""Legal observed-state callback; no frame, truth, decoder or model access."""
import numpy as np
from afdm_sp_joint_unrolled.afdm_baselines import construct_sensing_matrix
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
from afdm_sp_joint_unrolled.direction_cancel import working_factor, transform


class CancellationTransform:
    def __init__(self, system, mode):
        if mode not in ('scalar','diagonal','lowrank'):
            raise ValueError('unknown cancellation mode')
        self.N = int(system.N_total)
        self.c1, self.c2 = system.c1, system.c2
        self.lmax, self.kmax = system.l_max_cap, system.k_max_cap
        if int(round(2*self.N*self.c1)) != 2*self.kmax+1:
            raise ValueError('dictionary/generator shift convention mismatch')
        self.mode = mode

    def __call__(self, *, y, pilot, H, x_soft, support, sigma_base):
        ids = np.asarray(support)
        if (ids.ndim!=1 or (ids.size and ids.dtype.kind not in 'iu') or len(ids)>40
                or len(set(ids.tolist()))!=len(ids) or np.any(ids<0)
                or np.any(ids>=(self.lmax+1)*(2*self.kmax+1))):
            raise ValueError('illegal support')
        ids = ids.astype(np.int64)
        y,pilot,H,x_soft = [np.asarray(a,dtype=np.complex128) for a in (y,pilot,H,x_soft)]
        if (y.shape!=(self.N,) or pilot.shape!=y.shape or x_soft.shape!=y.shape
                or H.shape!=(self.N,self.N) or any(not np.isfinite(a).all() for a in (y,pilot,H,x_soft))):
            raise ValueError('invalid observed cancellation state')
        def sensing(x):
            return construct_sensing_matrix(self.N,x,self.c1,self.c2,self.lmax,self.kmax)[:,ids]
        A,P = sensing(pilot+x_soft),sensing(pilot)
        factor = working_factor(A,P,sigma_base)
        result = transform(y-H@pilot,H,factor['B'],sigma_base,self.mode)
        result['B'] = factor['B']
        result['diagnostics'].update(working_factor=factor['diagnostics'],
            A_sha256=array_hash(A),P_sha256=array_hash(P),support=ids.tolist(),
            sensing_input='pilot+x_soft; already power-scaled',truth_access='none')
        return result
