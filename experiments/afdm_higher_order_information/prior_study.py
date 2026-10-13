"""Registered zero-observation actual-prior branch and moment audit."""
import argparse
from pathlib import Path
import numpy as np
from scipy.optimize import brentq

from experiments.afdm_higher_order_information import prior
from experiments.afdm_higher_order_information.protocol import ROOT, dump, run
from experiments.afdm_shared_channel_20261004.production_diagnostic import source_paths

CONFIG = dict(seed=[20261004,213705,31], n=16,
    geometries=[[0,0],[0,.01],[0,.05],[0,.1],[0,.2],[.27,0],[.27,.001],
                [.27,.01],[.27,.05],[.27,.12],[2,.05],[2,.2]],
    physical_doppler_clip='apply frozen cap to mu +/- delta before virtual weights and G1',
    pdps=[[1.,1.],[1.,.3]], models=['actual','fixed_energy','gaussian_equal_pdp'],
    positive_product_orders=[32,64,128], sobol_exponents=[14,16], sobol_scrambles=[4401,4402],
    lags=[3,7], noise=.2, derivative_geometry=[.27,.12],
    derivative_steps=[1e-3,3e-4,1e-4,3e-5], rank_tolerance=1e-12,
    refinement_atol=2e-4, refinement_rtol=.01,
    prune_root_bracket=[1e-7,.2], threshold_offsets=[-1e-7,0,1e-7],
    new_observations=0, receiver_calls=0, decoder_calls=0,
    independent_observation_clusters=0,
    node_scope='positive numerical integration of gain-only power moments; no sampled observations',
    pdp_scope='conditional oracle PDP curves, not unconditional production distribution',
    failure_policy='retain every finite-node value; divergent true moments are labelled infinite, not approximated')


def flatten(m):
    return np.r_[m['second'],m['cross'],m['T']]


def features_from_y(y, weights, noise, n):
    p=abs(y)**2; second=weights@p
    cross=(1-1/n)*(weights@(p[:,:1]*p[:,1:]))+noise*(second[0]+second[1:])+noise**2
    return np.r_[second+noise,cross]


def feature_jvp(y, dy, weights, noise, n):
    p=abs(y)**2; dp=2*(y.conj()*dy).real
    second=weights@dp
    cross=(1-1/n)*(weights@(dp[:,:1]*p[:,1:]+p[:,:1]*dp[:,1:]))+noise*(second[0]+second[1:])
    return np.r_[second,cross]


def calculate(output):
    system=prior.small_system(CONFIG['n']); records=[]; identities=[]
    rules=[]
    for order in CONFIG['positive_product_orders']:
        z,w=prior.sphere_rule(order); rules.append((f'product_{order}',z,w))
    for exponent in CONFIG['sobol_exponents']:
        for seed in CONFIG['sobol_scrambles']:
            z,w=prior.sphere_sobol(exponent,seed); rules.append((f'sobol_{exponent}_{seed}',z,w))
    for name,z,w in rules:
        np.savez_compressed(output/(name+'.npz'),base_sphere=z,positive_weights=w)
    for i,(mu,delta) in enumerate(CONFIG['geometries']):
        g=prior.geometry(system,mu,delta)
        gram_error=float(np.max(abs(g['gram']-prior.dense_gram(system,g['weights']))))
        status={kind:prior.singular_moment_status(g['gram'],g[kind]) for kind in ['g0','g1']}
        np.savez_compressed(output/f'geometry_{i:02d}.npz',**g)
        identities.append(dict(case=i,mu=mu,delta=delta,gram_error=gram_error,
            eigenvalues=np.linalg.eigvalsh(g['gram']).tolist(),status=status,
            requested_dopplers=g['requested_dopplers'].tolist(),actual_dopplers=g['dopplers'].tolist(),
            physical_clip_mask=g['physical_clip_mask'].tolist(),
            active_rows=np.flatnonzero(np.any(g['weights']!=0,axis=1)).tolist()))
        for di,pdp in enumerate(CONFIG['pdps']):
            models=['actual','fixed_energy']+(['gaussian'] if di==0 else [])
            for model in models:
                for kind in ['g0','g1']:
                    values={}
                    for name,z,w in rules:
                        m=prior.mapped_moments(z,w,pdp,g['gram'],g[kind],model,
                            noise=CONFIG['noise'],a=CONFIG['lags'][0],b=CONFIG['lags'][1])
                        values[name]=flatten(m)
                    ref=values['product_128']
                    checks={name:bool(np.all(abs(v-ref)<=CONFIG['refinement_atol']+CONFIG['refinement_rtol']*abs(ref)))
                            for name,v in values.items() if name!='product_32'}
                    true_finite=model!='actual' or status[kind]['fourth']=='finite'
                    np.savez_compressed(output/f'moments_{i:02d}_{di}_{model}_{kind}.npz',**values)
                    records.append(dict(case=i,pdp=pdp,model=model,operator=kind,
                        reference=ref.tolist(),checks=checks,
                        true_moment_status='finite' if true_finite else 'infinite',
                        numerical_refined=bool(true_finite and all(checks.values())),
                        comparison='paired same base angular variables; Gaussian radial moments exact'))
    # Locate the first prune threshold by the original Dirichlet amplitudes.
    def root(d):
        alpha=np.array([system.dirichlet_alpha(m,d,system.N_total) for m in range(-2,3)])
        return abs(alpha[1])**2-system.frac_prune_rel_thres*np.max(abs(alpha)**2)
    threshold=brentq(root,*CONFIG['prune_root_bracket'],xtol=1e-14)
    jump=[]
    for offset in CONFIG['threshold_offsets']:
        g=prior.geometry(system,0,threshold+offset)
        jump.append(dict(delta=threshold+offset,active=np.flatnonzero(np.any(g['weights']!=0,axis=1)).tolist(),
                         gram_eigenvalues=np.linalg.eigvalsh(g['gram']).tolist()))
    gleft=prior.geometry(system,0,threshold-1e-7); gright=prior.geometry(system,0,threshold+1e-7)
    boundary=dict(threshold=threshold,rows=jump,weight_jump_norm=float(np.linalg.norm(gright['weights']-gleft['weights'])))
    # Full pushforward derivative and frozen-prior ablation at a regular branch.
    mu,delta=CONFIG['derivative_geometry']; pdp=np.array(CONFIG['pdps'][1]); n=system.N_total
    g=prior.geometry(system,mu,delta); z,w=rules[2][1:]; derivatives=[]
    h,_=prior.pushforward_nodes(z,w,pdp,g['gram'])
    for kind in ['g0','g1']:
        base_y=h@g[kind].T; f0=features_from_y(base_y,w,CONFIG['noise'],n)
        for step in CONFIG['derivative_steps']:
            gp=prior.geometry(system,mu,delta+step); gm=prior.geometry(system,mu,delta-step)
            stable=all(np.array_equal(gx['weights']!=0,g['weights']!=0) for gx in [gp,gm])
            if not stable:
                raise ValueError('registered derivative steps cross a frozen prune branch')
            dR=(gp['gram']-gm['gram'])/(2*step); dB=(gp[kind]-gm[kind])/(2*step)
            y,dy=prior.pushforward_jvp(z,pdp,g['gram'],g[kind],np.zeros(2),dR,dB)
            j=feature_jvp(y,dy,w,CONFIG['noise'],n)/(2*delta)
            frozen=feature_jvp(y,h@dB.T,w,CONFIG['noise'],n)/(2*delta)
            hp,_=prior.pushforward_nodes(z,w,pdp,gp['gram']); hm,_=prior.pushforward_nodes(z,w,pdp,gm['gram'])
            fd=(features_from_y(hp@gp[kind].T,w,CONFIG['noise'],n)-features_from_y(hm@gm[kind].T,w,CONFIG['noise'],n))/(4*step*delta)
            derivatives.append(dict(operator=kind,step=step,stable_support=stable,
                full_q_derivative=j.tolist(),finite_difference=fd.tolist(),frozen_prior_derivative=frozen.tolist(),
                max_jvp_fd_error=float(np.max(abs(j-fd))),prior_derivative_omission_norm=float(np.linalg.norm(j-frozen))))
        # Nuisance rank is a numerical moment diagnostic, not a certified Fisher value.
        eps=CONFIG['derivative_steps'][-1]; J=[]
        for nuisance in ['mu','log_pdp_ratio','log_scale','noise']:
            fs=[]
            for sign in [-1,1]:
                ge=prior.geometry(system,mu+sign*eps if nuisance=='mu' else mu,delta)
                de=pdp*np.exp([0,sign*eps]) if nuisance=='log_pdp_ratio' else pdp
                he,_=prior.pushforward_nodes(z,w,de,ge['gram'])
                ye=he@ge[kind].T
                if nuisance=='log_scale': ye*=np.exp(sign*eps/2)
                noise=CONFIG['noise']+sign*eps if nuisance=='noise' else CONFIG['noise']
                fs.append(features_from_y(ye,w,noise,n))
            J.append((fs[1]-fs[0])/(2*eps))
        J=np.column_stack(J); jq=np.array(derivatives[-1]['full_q_derivative'])
        projection=jq-J@np.linalg.lstsq(J,jq,rcond=1e-10)[0]
        np.savez_compressed(output/f'derivative_{kind}.npz',features=f0,nuisance_jacobian=J,q_jacobian=jq,residual=projection)
        derivatives[-1]['nuisance_residual_norm']=float(np.linalg.norm(projection))
        derivatives[-1]['nuisance_names']=['mu','log_pdp_ratio','log_scale','noise']
        derivatives[-1]['information_claim']='no certified positive efficient information; residual is finite-rule diagnostic only'
    dump(output/'moments.json',records); dump(output/'geometry.json',identities)
    dump(output/'derivatives.json',derivatives); dump(output/'boundaries.json',boundary)
    return dict(cases=len(identities),moment_cases=len(records),
        refined=sum(r['numerical_refined'] for r in records),
        divergent=sum(r['true_moment_status']=='infinite' for r in records),
        unresolved=[{k:r[k] for k in ['case','pdp','model','operator','true_moment_status']} for r in records if not r['numerical_refined']],
        max_dense_gram_error=max(r['gram_error'] for r in identities),
        prune_threshold=threshold, derivative_records=derivatives,
        theorem='G0 single-atom plateau has zero efficient information; G1 nonannihilating nullspace has infinite second moment',
        new_observations=0,receiver_calls=0,decoder_calls=0,
        interpretation='conditional model moments; numerical nonconvergence never removes cases or implies finite singular moments')


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--stage',required=True); args=parser.parse_args()
    base=Path(__file__).parent
    # Frozen config import loads Torch/OpenMP; inventory must be fixed before admission.
    prior.frozen_components()
    run(args.stage,CONFIG,[*source_paths(),__file__,base/'prior.py',base/'test_prior.py',
        ROOT/'experiments/afdm_shared_channel_20261004/production_prior.py'],calculate,wall_seconds=600)

if __name__=='__main__': main()
