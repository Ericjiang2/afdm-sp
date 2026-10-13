"""CPP-aware collision-coordinate operator diagnostics; no F1 optimizer calls."""
from pathlib import Path
import sys
import time
import math

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from experiments.afdm_structured_inference_20261003.common import run,dump
from experiments.afdm_inference_causal_20261002.oracle_comparison import load_frozen


def operator_derivatives(n,c1,c2,delay,center,order,physical=None):
    """Exact Doppler derivatives of the frozen CPP operator, including 1/k!."""
    if isinstance(order,bool) or not isinstance(order,int) or order < 0 or order > 4:
        raise ValueError('bounded jet order must be an integer in [0,4]')
    if physical is None:
        physical,_,_=load_frozen()
    channel=physical.Channel(n,c1,c2,[delay],[center],[1])
    base=np.column_stack([channel.apply(e) for e in np.eye(n)])
    time_base=physical.daft(base,c1,c2,True)
    multiplier=2j*np.pi*np.arange(n)/n
    return np.stack([physical.daft(multiplier[:,None]**k*time_base,c1,c2)/math.factorial(k)
                     for k in range(order+1)])


def moments_and_prior(gains,offsets,order,variance=.5):
    """Push forward h~CN(0, variance I) at fixed offsets; no independent-M prior."""
    offsets=np.asarray(offsets,float); gains=np.asarray(gains,complex)
    if offsets.ndim!=1 or gains.shape!=offsets.shape or not np.isfinite(offsets).all() or not np.isfinite(gains).all():
        raise ValueError('finite matching gain and offset vectors required')
    transform=offsets[None,:]**np.arange(order+1)[:,None]
    return transform@gains,variance*transform@transform.T,transform


def real_jacobian(complex_gain_basis,real_columns=()):
    basis=np.column_stack([a.ravel() for a in complex_gain_basis])
    columns=[basis,1j*basis]
    if len(real_columns):
        columns.append(np.column_stack([a.ravel() for a in real_columns]))
    matrix=np.column_stack(columns)
    return np.concatenate([matrix.real,matrix.imag],axis=0)


def spectrum(jacobian):
    values=np.linalg.svd(jacobian,compute_uv=False)
    tolerance=max(jacobian.shape)*np.finfo(float).eps*values[0]
    positive=values[values>tolerance]
    return dict(values=values.tolist(),rank=int(len(positive)),rank_tolerance=float(tolerance),
                nonzero_condition=float(positive[0]/positive[-1]))


def projection(basis,target):
    design=np.column_stack([a.ravel() for a in basis])
    coefficients,_,rank,singular=np.linalg.lstsq(design,target.ravel(),rcond=None)
    estimate=np.einsum('k,kij->ij',coefficients,basis)
    return estimate,coefficients,int(rank),singular


CONFIG=dict(seed=[20261003,104129,40],n=16,separations=[0.,.0001,.01,.05,.2,.6,1.2],
            gains={'same_phase':[[1.,0.],[.7,0.]],'cancellation':[[1.,0.],[-1.,0.]],
                   'general_complex':[[1.,0.],[.4,.8]]},orders=[1,2],
            strata=[dict(split='development',center=.25,midpoint_offset=0.,delay=0,stride=5.),
                    dict(split='heldout_center',center=-1.35,midpoint_offset=.11,delay=3,stride=5.),
                    dict(split='heldout_center_cpp',center=2.6,midpoint_offset=-.09,delay=15,stride=5.3)],
            center_modes=['exogenous_grid','oracle_midpoint'],cases=126,
            selection='orders fixed before all cases; no truth-based order selection',
            comparison='native fixed center, F1 exact two-column representation, order1/order2 jet; no optimizer')


def calculate(output):
    from experiments.afdm_structured_inference_20261003.test_jet_potential import run_registered_tests
    run_registered_tests('JetTests',output)
    physical,_,_=load_frozen(); rng=np.random.default_rng(CONFIG['seed']); records=[]
    n=CONFIG['n']; c2=(np.sqrt(2)-1)/(2*n*n)
    for stratum in CONFIG['strata']:
        c1=stratum['stride']/(2*n); midpoint=stratum['center']+stratum['midpoint_offset']
        x=(rng.normal(size=n)+1j*rng.normal(size=n))/np.sqrt(2)
        for separation in CONFIG['separations']:
            nus=midpoint+np.array([-.5,.5])*separation
            exact=[operator_derivatives(n,c1,c2,stratum['delay'],float(nu),1,physical) for nu in nus]
            f1_basis=np.stack([a[0] for a in exact])
            for gain_name,pairs in CONFIG['gains'].items():
                gains=np.array([a+1j*b for a,b in pairs]); target=np.einsum('p,pij->ij',gains,f1_basis)
                denominator=np.sqrt(n)*np.sum(abs(gains))
                for center_mode in CONFIG['center_modes']:
                    center=stratum['center'] if center_mode=='exogenous_grid' else midpoint
                    started=time.perf_counter()
                    basis=operator_derivatives(n,c1,c2,stratum['delay'],center,2,physical)
                    m,prior,transform=moments_and_prior(gains,nus-center,2)
                    estimates={'native_pushforward':m[0]*basis[0],
                               'jet1_pushforward':np.einsum('k,kij->ij',m[:2],basis[:2]),
                               'jet2_pushforward':np.einsum('k,kij->ij',m,basis)}
                    coefficients={}; ranks={}
                    for label,b in [('native_oracle_projection',basis[:1]),('jet1_oracle_projection',basis[:2]),
                                    ('jet2_oracle_projection',basis),('f1_oracle_columns_projection',f1_basis)]:
                        estimates[label],coefficients[label],ranks[label],_=projection(b,target)
                    errors={label:dict(operator_scaled=float(np.linalg.norm(value-target)/denominator),
                            response_scaled=float(np.linalg.norm((value-target)@x)/(np.linalg.norm(x)*np.sum(abs(gains)))))
                            for label,value in estimates.items()}
                    spectra=dict(f1_unknown_geometry=spectrum(real_jacobian(f1_basis,[gains[j]*exact[j][1] for j in range(2)])),
                                 f1_fixed_geometry=spectrum(real_jacobian(f1_basis)),
                                 native_unknown_center=spectrum(real_jacobian(basis[:1],[m[0]*basis[1]])),
                                 jet1_fixed_center=spectrum(real_jacobian(basis[:2])),
                                 jet2_fixed_center=spectrum(real_jacobian(basis)))
                    # h slots can be unrecoverable while aggregate moments remain stable.
                    h_fit=coefficients['f1_oracle_columns_projection']; m_fit=transform@h_fit
                    combination_error=float(np.linalg.norm(m_fit-m))
                    separated_error=float(np.linalg.norm(h_fit-gains))
                    remainder_bound=[]
                    for order in CONFIG['orders']:
                        phase_max=2*np.pi*(n-1)/n*abs(nus-center)
                        remainder_bound.append(float(np.sum(abs(gains)*phase_max**(order+1)/math.factorial(order+1))/np.sum(abs(gains))))
                    index=len(records)
                    np.savez(output/f'case_{index:03d}.npz',x=x,nus=nus,gains=gains,target=target,basis=basis,
                             f1_basis=f1_basis,moments=m,pushforward_cov=prior,pushforward_transform=transform,
                             **estimates,**{k+'_coefficients':v for k,v in coefficients.items()})
                    record=dict(index=index,**stratum,separation=separation,gains=gain_name,center_mode=center_mode,
                                expansion_center=center,errors=errors,spectra=spectra,complex_projection_ranks=ranks,
                                real_parameter_counts=dict(native_fixed=2,native_unknown_center=3,f1_fixed_geometry=4,
                                                           f1_unknown_geometry=6,jet1_fixed=4,jet2_fixed=6),
                                moment_prior_rank=int(np.linalg.matrix_rank(prior)),
                                relative_separated_coordinate_error=separated_error/float(np.linalg.norm(gains)),
                                aggregate_coordinate_error=combination_error,
                                remainder_bounds_scaled=remainder_bound,
                                seconds=time.perf_counter()-started)
                    records.append(record)
    dump(output/'curves.json',records)
    if len(records)!=CONFIG['cases']:
        raise AssertionError('registered case population mismatch')
    if max(r['errors']['f1_oracle_columns_projection']['operator_scaled'] for r in records)>1e-12:
        raise AssertionError('exact two-column representation failed')
    for r in records:
        for order in CONFIG['orders']:
            if r['errors'][f'jet{order}_pushforward']['operator_scaled'] > r['remainder_bounds_scaled'][order-1]+1e-12:
                raise AssertionError('Taylor remainder bound violated')
    summary={}
    for split in [s['split'] for s in CONFIG['strata']]:
        group=[r for r in records if r['split']==split and r['center_mode']=='exogenous_grid']
        summary[split]={str(gap):{name:max(r['errors'][name]['operator_scaled'] for r in group if r['separation']==gap)
                                   for name in ['native_pushforward','jet1_pushforward','jet2_pushforward']}
                        for gap in CONFIG['separations']}
    return dict(status='completed local operator diagnostic',records=len(records),summary=summary,
                operator_calls_only=True,f1_optimizer_calls=0,production_receiver_calls=0,
                interpretation='jet is local and prior-constrained; exact F1 representation is an oracle-column reference',
                cost='jet r uses r+1 response columns versus two F1 columns, O((r+1)N log N) actions; dense N16 only for diagnostics')


if __name__=='__main__':
    sources=[__file__,Path(__file__).with_name('test_jet_potential.py'),
             ROOT/'experiments/afdm_inference_causal_20261002/oracle_comparison.py',
             ROOT/'experiments/afdm_inference_causal_20261002/exact_oracle.py',
             ROOT/'experiments/sp_afdm_frozen_20260920/src/physical.py',
             ROOT/'experiments/sp_afdm_frozen_20260920/src/messages.py',
             ROOT/'experiments/sp_afdm_native_joint_20260921/src/twofft.py']
    run('jet_v1',CONFIG,sources,calculate)
