"""Finite-data messages and continuous real-augmented Gaussian integration.

Every function identifies its probability object. Negative Gaussian site
precision is a valid unnormalised EP factor and is never silently clipped.
"""
from pathlib import Path
import sys
import itertools

import numpy as np
from scipy.special import logsumexp, expit, xlogy
from numpy.polynomial.hermite import hermgauss

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.afdm_inference_causal_20261002.exact_oracle import enumerate_qpsk, exact_posterior
from experiments.afdm_structured_inference_20261003.collapsed import CollapsedModel, dense_operators, PHYSICAL, SOURCES
from experiments.afdm_structured_inference_20261003.common import run, dump


def bit_extrinsic(log_likelihood, bits, incoming_llr, base_log_prior=None):
    """APP and factor-to-bit LLR; delete exactly the recipient's own factor.

    base_log_prior may encode a correlated/code prior independent of incoming
    messages. Correlations cannot be reconstructed from marginal bit LLRs.
    """
    ll = np.asarray(log_likelihood,float)
    bits = np.asarray(bits)
    incoming = np.asarray(incoming_llr,float)
    if (bits.ndim != 2 or ll.shape != (len(bits),) or incoming.shape != (bits.shape[1],)
            or not np.isin(bits,[0,1]).all() or not np.isfinite(ll).all()
            or not np.isfinite(incoming).all()):
        raise ValueError('finite likelihood/LLR and binary candidate labels required')
    base = np.zeros(len(bits)) if base_log_prior is None else np.asarray(base_log_prior,float)
    if base.shape != ll.shape or np.isnan(base).any() or np.isposinf(base).any():
        raise ValueError('invalid base log prior')
    joint = ll + base + .5*(1-2*bits)@incoming
    if not np.isfinite(logsumexp(joint)):
        raise ValueError('empty prior support')
    app = np.array([logsumexp(joint[bits[:,j]==0])-logsumexp(joint[bits[:,j]==1])
                    for j in range(bits.shape[1])])
    return app, app-incoming


def gaussian_tilted_real(log_likelihood, mean, covariance, order, *, max_points=65536):
    """Gauss-Hermite quadrature of E_N(mean,cov)[exp(log_likelihood(z))].

    z is real augmented, with arbitrary covariance (proper or improper complex
    data). Numerical accuracy must be estimated by order refinement externally.
    Zero-variance directions stay deterministic; no epsilon information is added.
    """
    mean, covariance = np.asarray(mean,float), np.asarray(covariance,float)
    if mean.ndim != 1 or covariance.shape != (len(mean),len(mean)):
        raise ValueError('incompatible Gaussian dimensions')
    if not np.isfinite(mean).all() or not np.isfinite(covariance).all():
        raise ValueError('finite Gaussian parameters required')
    if not isinstance(order,int) or order < 2:
        raise ValueError('quadrature order must be an integer >= 2')
    scale = np.linalg.norm(covariance,ord=2)
    tolerance = 64*np.finfo(float).eps*len(mean)*scale
    if np.linalg.norm(covariance-covariance.T)>tolerance:
        raise ValueError('Gaussian covariance must be symmetric')
    values,vectors = np.linalg.eigh((covariance+covariance.T)/2)
    if values.min() < -tolerance:
        raise ValueError('Gaussian covariance must be PSD')
    positive = values>0
    factor = vectors[:,positive]*np.sqrt(values[positive])
    rank = factor.shape[1]
    if order**rank > max_points:
        raise ValueError('quadrature exceeds explicit point cap')
    nodes,weights = hermgauss(order)
    indices = np.array(list(itertools.product(range(order),repeat=rank)),dtype=int).reshape((-1,rank)) if rank else np.empty((1,0),int)
    points = mean + (np.sqrt(2)*nodes[indices])@factor.T
    log_weights = np.log(weights[indices]).sum(axis=1)-rank/2*np.log(np.pi)
    likelihoods = np.array([log_likelihood(point) for point in points])
    if not np.isfinite(likelihoods).all():
        raise FloatingPointError('nonfinite quadrature likelihood')
    log_z = float(logsumexp(log_weights+likelihoods))
    probability = np.exp(log_weights+likelihoods-log_z)
    tilted_mean = probability@points
    centered = points-tilted_mean
    tilted_covariance = np.einsum('k,ki,kj->ij',probability,centered,centered)
    return dict(log_evidence=log_z,mean=tilted_mean,covariance=tilted_covariance,
                points=points,log_quadrature_weights=log_weights,
                log_likelihood=likelihoods,probabilities=probability,
                support_rank=rank,point_count=len(points))


def gaussian_site(cavity_mean, cavity_cov, tilted_mean, tilted_cov):
    """Natural parameters of tilted/cavity, in real Gaussian convention.

    Requires proper normalisable cavity and tilted distributions. The site
    itself may be indefinite; combining with a cavity must be checked separately.
    """
    means = [np.asarray(v,float) for v in (cavity_mean,tilted_mean)]
    covs = [np.asarray(v,float) for v in (cavity_cov,tilted_cov)]
    if any(m.shape!=means[0].shape or m.ndim!=1 for m in means):
        raise ValueError('incompatible means')
    for cov in covs:
        if cov.shape != (len(means[0]),len(means[0])) or not np.isfinite(cov).all() or not np.allclose(cov,cov.T,atol=1e-14,rtol=1e-14):
            raise ValueError('finite symmetric covariance required')
        np.linalg.cholesky(cov)
    if not all(np.isfinite(m).all() for m in means):
        raise ValueError('finite means required')
    precision = [np.linalg.solve(cov,np.eye(len(means[0]))) for cov in covs]
    site_precision = precision[1]-precision[0]
    information = precision[1]@means[1]-precision[0]@means[0]
    return dict(precision=site_precision,information=information,
                minimum_eigenvalue=float(np.linalg.eigvalsh(site_precision).min()),
                normalizable_alone=bool(np.linalg.eigvalsh(site_precision).min()>0),
                policy='retain signed natural factor; require positive combined cavity precision, otherwise reject update')


CONFIG = dict(seed=[20261003,104129,60], independent_draws=4, n=2,
              geometries=['separated','near_repeat'], noise_variances=[.2,1.],
              prior='CN(nonzero,correlated); bit incoming observation-independent; correlated base prior',
              methods=['profile_marginal','meanH_marginal','collapsed_single_symbol_conditional','exact_discrete_marginal'],
              gaussian_cases=4, gaussian_orders=[9,17,25],
              gaussian_error_threshold=.003, gaussian_derivative_step=1e-4,
              all_integration_in_real_augmented_coordinates=True, receiver_calls=0)


def _probability_error(reference_llr, llr):
    p,q = expit(reference_llr),expit(llr)
    kl = xlogy(p,p)+xlogy(1-p,1-p)+p*np.logaddexp(0,-llr)+(1-p)*np.logaddexp(0,llr)
    return dict(llr_rmse=float(np.sqrt(np.mean((reference_llr-llr)**2))),
                probability_mse=float(np.mean((p-q)**2)),bernoulli_kl=float(np.mean(kl)))


def calculate(output):
    rng = np.random.default_rng(CONFIG['seed'])
    words,bits = enumerate_qpsk(2)
    records = []
    for seed in range(CONFIG['independent_draws']):
        gain = (rng.normal(size=2)+1j*rng.normal(size=2))/2
        actual_data = words[rng.integers(len(words))]
        noise_draw = (rng.normal(size=2)+1j*rng.normal(size=2))/np.sqrt(2)
        incoming = rng.normal(size=4)*.7
        base = .35*(1-2*bits[:,0])*(1-2*bits[:,1])
        log_prior = base+.5*(1-2*bits)@incoming
        prior = np.exp(log_prior-logsumexp(log_prior))
        prior_mean = prior@words
        frozen_data = words[np.argmax(prior)]
        for geometry in CONFIG['geometries']:
            channel = PHYSICAL.Channel(2,.37/2,.13/4,[0,1] if geometry=='separated' else [0,0],
                                       [.23,-.38] if geometry=='separated' else [.23,.24],[1,1])
            ops = dense_operators(channel)
            pilot = .4*np.exp(.3j*np.arange(2))
            mean = np.array([.25+.1j,-.1+.2j])
            cov = np.array([[.5,.1+.07j],[.1-.07j,.4]])
            for noise in CONFIG['noise_variances']:
                y = np.einsum('p,pij,j->i',gain,ops,pilot+actual_data)+np.sqrt(noise)*noise_draw
                model = CollapsedModel(channel,mean,cov,noise)
                exact = exact_posterior(y,ops,pilot,words,mean,cov,noise,bits=bits,prior_probabilities=prior)
                evaluated = [model.evaluate(y,pilot+word) for word in words]
                collapsed_ll = np.array([r['log_likelihood'] for r in evaluated])
                collapsed_app,ext = bit_extrinsic(collapsed_ll,bits,incoming,base)
                profile_ll = np.array([r['profile_log_density'] for r in evaluated])
                profile_app,_ = bit_extrinsic(profile_ll,bits,incoming,base)
                plugin_h = model.evaluate(y,pilot+prior_mean)['h_mean']
                h = np.einsum('p,pij->ij',plugin_h,ops)
                mean_ll = -np.sum(abs(y[None,:]-(pilot[None,:]+words)@h.T)**2,axis=1)/noise
                mean_app,_ = bit_extrinsic(mean_ll,bits,incoming,base)
                condition_llrs = np.zeros(4)
                # Exact channel integration but nuisance symbol frozen to its
                # prior mode (not truth). Restrict the SAME correlated prior.
                for symbol in range(2):
                    selected = np.all(words[:,np.arange(2)!=symbol]==frozen_data[np.arange(2)!=symbol],axis=1)
                    sub_app,_ = bit_extrinsic(collapsed_ll[selected],bits[selected],incoming,base[selected])
                    condition_llrs[[symbol,symbol+2]] = sub_app[[symbol,symbol+2]]
                methods = dict(profile_marginal=profile_app,meanH_marginal=mean_app,
                               collapsed_single_symbol_conditional=condition_llrs,exact_discrete_marginal=collapsed_app)
                own_edge_errors = []
                for bit in range(4):
                    modified = incoming.copy();modified[bit]+=1.7
                    _,changed_ext = bit_extrinsic(collapsed_ll,bits,modified,base)
                    own_edge_errors.append(abs(ext[bit]-changed_ext[bit]))
                index = len(records)
                np.savez(output/f'discrete_{index:03d}.npz',y=y,operators=ops,pilot=pilot,words=words,bits=bits,
                         gain_mean=mean,gain_cov=cov,noise=noise,base_log_prior=base,incoming=incoming,
                         collapsed_log_likelihood=collapsed_ll,profile_log_density=profile_ll,meanH_log_likelihood=mean_ll,
                         prior_probabilities=prior,exact_llr=exact.llr,frozen_data=frozen_data,plugin_gain=plugin_h,
                         **methods)
                records.append(dict(case=index,seed=seed,geometry=geometry,noise=noise,
                                    metrics={name:_probability_error(exact.llr,llr) for name,llr in methods.items()},
                                    own_edge_error=float(max(own_edge_errors)),
                                    likelihood_error=float(np.max(abs(collapsed_ll-exact.log_likelihood)))))
    quadratures = []
    # A single complex coordinate is an actual continuous Gaussian cavity.
    # The other data coordinate is deterministic and not drawn from QPSK here.
    for index in range(CONFIG['gaussian_cases']):
        channel = PHYSICAL.Channel(2,.37/2,.13/4,[0,1],[.23,-.38],[1,1])
        y = .3*(rng.normal(size=2)+1j*rng.normal(size=2))
        model = CollapsedModel(channel,[.2+.1j,-.1],[[.3,.05j],[-.05j,.4]],1.)
        r = np.array([.1,-.15])
        v = np.array([[.12,.035],[.035,.08]])*(1+index*.15)
        fixed = .15+.08j
        def likelihood(z):
            return model.evaluate(y,np.array([z[0]+1j*z[1],fixed]))['log_likelihood']
        results = []
        for order in CONFIG['gaussian_orders']:
            q = gaussian_tilted_real(likelihood,r,v,order)
            np.savez(output/f'gaussian_{index:02d}_order_{order:02d}.npz',y=y,cavity_mean=r,cavity_covariance=v,
                     fixed_other_coordinate=fixed,**q)
            results.append(q)
        coarse,fine = results[-2:]
        errors = dict(log_evidence=abs(fine['log_evidence']-coarse['log_evidence']),
                      mean=float(np.linalg.norm(fine['mean']-coarse['mean'])),
                      covariance=float(np.linalg.norm(fine['covariance']-coarse['covariance'])))
        score = np.linalg.solve(v,fine['mean']-r)
        step = CONFIG['gaussian_derivative_step']
        fd = np.zeros(2)
        for j in range(2):
            direction=np.eye(2)[j]*step
            plus=gaussian_tilted_real(likelihood,r+direction,v,CONFIG['gaussian_orders'][-1])
            minus=gaussian_tilted_real(likelihood,r-direction,v,CONFIG['gaussian_orders'][-1])
            fd[j]=(plus['log_evidence']-minus['log_evidence'])/(2*step)
        site=gaussian_site(r,v,fine['mean'],fine['covariance'])
        recovered_precision=np.linalg.inv(v)+site['precision']
        recovered_mean=np.linalg.solve(recovered_precision,np.linalg.solve(v,r)+site['information'])
        quadratures.append(dict(case=index,orders=CONFIG['gaussian_orders'],refinement_error=errors,
                                score_identity_error=float(np.linalg.norm(score-fd)),
                                site_roundtrip_error=float(np.linalg.norm(recovered_mean-fine['mean'])),
                                minimum_site_eigenvalue=site['minimum_eigenvalue'],
                                real_improper_covariance=True,object='one complex coordinate, other coordinate deterministic'))
    # Multi-coordinate correlated cavity under known H has an analytic Gaussian
    # answer, checking quadrature across symbols and the zero-gain-uncertainty limit.
    r=np.array([.1,-.1,.05,.02])
    v=np.diag([.04,.03,.04,.03]);v[0,1]=v[1,0]=.01;v[0,2]=v[2,0]=.008
    matrix=np.array([[.5,.1,.2,-.1],[.1,.4,-.1,.2]])
    obs=np.array([.3,-.2]); noise_cov=np.eye(2)*.7
    def known_likelihood(z): return -.5*float((obs-matrix@z)@np.linalg.solve(noise_cov,obs-matrix@z))
    known=gaussian_tilted_real(known_likelihood,r,v,9)
    analytic_cov=np.linalg.inv(np.linalg.inv(v)+matrix.T@np.linalg.solve(noise_cov,matrix))
    analytic_mean=analytic_cov@(np.linalg.solve(v,r)+matrix.T@np.linalg.solve(noise_cov,obs))
    known_error=float(max(np.linalg.norm(known['mean']-analytic_mean),np.linalg.norm(known['covariance']-analytic_cov)))
    np.savez(output/'correlated_known_channel.npz',mean=r,covariance=v,matrix=matrix,observation=obs,
             noise_covariance=noise_cov,analytic_mean=analytic_mean,analytic_covariance=analytic_cov,**{'quadrature_'+k:v for k,v in known.items()})
    # Explicit signed-site counterexample: a symmetric two-mode factor widens
    # variance beyond cavity; the factor alone need not be normalisable.
    negative=gaussian_site([0.],[[1.]],[0.],[[4.]])
    deterministic=gaussian_tilted_real(lambda z:-float(z@z),np.array([.3,-.2]),np.zeros((2,2)),3)
    dump(output/'raw.json',dict(discrete=records,gaussian=quadratures,known_channel_error=known_error,
                               negative_site={k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in negative.items()},
                               deterministic_point_count=deterministic['point_count']))
    if max(r['likelihood_error'] for r in records)>1e-10 or max(r['own_edge_error'] for r in records)>1e-10 or known_error>1e-10:
        raise AssertionError('message exact algebra contract failed; raw retained')
    return dict(discrete_cases=len(records),independent_exogenous_draws=CONFIG['independent_draws'],
                mean_metrics={method:{key:float(np.mean([r['metrics'][method][key] for r in records])) for key in records[0]['metrics'][method]} for method in methods},
                max_likelihood_error=max(r['likelihood_error'] for r in records),
                max_own_edge_error=max(r['own_edge_error'] for r in records),gaussian_cases=quadratures,
                gaussian_numerically_resolved=all(max(r['refinement_error'].values())<CONFIG['gaussian_error_threshold'] for r in quadratures),
                gaussian_max_score_identity_error=max(r['score_identity_error'] for r in quadratures),
                correlated_known_channel_error=known_error,negative_site_precision=-.75,
                production_utility='not_tested',geometry_integration='not_tested; geometry fixed in every comparison')


if __name__ == '__main__':
    run('message_v1',CONFIG,[*SOURCES,__file__],calculate)
