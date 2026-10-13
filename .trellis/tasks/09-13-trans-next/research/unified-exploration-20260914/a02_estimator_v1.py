"""Observed-only initial-estimation comparison; no BP or code consumers."""
import time
import numpy as np
import torch

from afdm_sp_joint_unrolled.bandlimited_basis import BasisGeometry, basis_from_public_band, group_omp, normalized_geometry
from afdm_sp_joint_unrolled.bandlimited_estimation import fit_coefficients, external_error_accounting
from afdm_sp_joint_unrolled.classical_joint_unrolled import construct_sensing_matrix_torch, omp_sparse_torch, expand_cluster_support
import physical_transfer_receiver_v1 as registered_receiver


CONFIGS = [(family,q) for family in ("fourier","gce","dpss") for q in (3,5,7)]+[("small",5)]


def make_geometry(family,q):
    n=256
    if family=="small":
        # Canonical integer atom phases match the existing OMP receiver.
        basis=np.exp(2j*np.pi*np.arange(n)[:,None]*np.arange(-2,3)[None,:]/n)/np.sqrt(n)
    else:
        basis=basis_from_public_band(family,n,q,4000.,16.)
    return BasisGeometry(basis,c1=5/512,c2=(np.sqrt(2)-1)/(2*n*n),delay_cap=24,prefix_length=32)


def estimate(observation,family,q):
    registered_receiver.base.validate_observed(observation,256)
    if (family,q) not in CONFIGS:
        raise ValueError("unregistered initial-estimation configuration")
    times={}
    start=time.perf_counter();geom=make_geometry(family,q)
    design=np.ascontiguousarray(geom.sensing(observation["pilot"]))
    times['basis_and_dictionary']=time.perf_counter()-start
    start=time.perf_counter()
    if family=="small":
        phi=construct_sensing_matrix_torch(256,torch.tensor(observation['pilot'],dtype=torch.complex64),
            geom.c1,geom.c2,24,2,cdtype=torch.complex64)
        np.testing.assert_allclose(phi.numpy(),design,atol=3e-6,rtol=3e-6)
        h,columns=omp_sparse_torch(torch.tensor(observation['y'],dtype=torch.complex64),phi,12,lstsq_driver='gels')
        delays,dopplers,_=expand_cluster_support(columns,2,2,h,125)
        selection=dict(columns=columns,nomination=12,expanded_count=len(delays),
            expanded_delays=delays.numpy(),expanded_dopplers=dopplers.numpy(),
            selection_refits=len(columns)+1,rejected_groups=[],
            geometry=normalized_geometry(design[:,columns]))
        # Work with the exact rounded design consumed by the classical OMP fit.
        fit_design=phi[:,columns].numpy()
    else:
        selection=group_omp(design,observation['y'],group_size=q,max_groups=60//q)
        columns=selection['columns']
        selection['selection_refits']=selection['refits']
        fit_design=design[:,columns]
    times['support_selection']=time.perf_counter()-start
    start=time.perf_counter()
    fits={name:fit_coefficients(fit_design,observation['y'],strength)
          for name,strength in [('ls',0.),('ridge',.1)]}
    times['paired_fits']=time.perf_counter()-start
    return dict(family=family,q=q,basis=geom.basis.copy(),selection=selection,fits=fits,times=times,
        frozen_soft_mean=np.zeros(256,complex),frozen_data_variance=np.full(256,.5),
        coding_calls=0,bp_calls=0,completed_final_fits=2,
        online_inputs=['y','pilot','sigma2','constellation'])


def geometry_from_value(value):
    # Coefficients are coordinates in this exact saved basis, never in an
    # independently regenerated eigenvector/QR phase convention.
    return BasisGeometry(value['basis'],c1=5/512,c2=(np.sqrt(2)-1)/(2*256**2),
                         delay_cap=24,prefix_length=32)


def score(value,observation,truth):
    geom=geometry_from_value(value)
    columns=value['selection']['columns']
    return {name:external_error_accounting(geom,columns,fit,observation,truth)
            for name,fit in value['fits'].items()}
