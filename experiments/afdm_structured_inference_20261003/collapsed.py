"""Exact Gaussian gain elimination at fixed data and fixed physical geometry.

This is a likelihood/score kernel, not a data marginal or receiver. Gain priors
are observation-independent working priors, including singular support.
"""
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.afdm_inference_causal_20261002.exact_oracle import _array, _prior_factor
from experiments.afdm_inference_causal_20261002.oracle_comparison import load_frozen
from experiments.afdm_structured_inference_20261003.common import run, dump

PHYSICAL, _, TWOFFT = load_frozen()
SOURCES = [__file__, ROOT/'experiments/afdm_inference_causal_20261002/exact_oracle.py',
           ROOT/'experiments/afdm_inference_causal_20261002/oracle_comparison.py',
           Path(PHYSICAL.__file__), Path(TWOFFT.__file__),
           ROOT/'experiments/sp_afdm_frozen_20260920/src/messages.py']


class CollapsedModel:
    def __init__(self, channel, gain_mean, gain_cov, noise_variance):
        self.channel = channel
        self.mean = _array(gain_mean, 'gain_mean', 1)
        cov = _array(gain_cov, 'gain_cov', 2)
        if self.mean.shape != (channel.p,) or cov.shape != (channel.p, channel.p):
            raise ValueError('gain prior dimensions disagree')
        if (not np.isscalar(noise_variance) or np.iscomplexobj(noise_variance)
                or not np.isfinite(noise_variance) or noise_variance <= 0):
            raise ValueError('noise variance must be finite and positive')
        self.noise = float(noise_variance)
        self.factor, self.prior_correction = _prior_factor(cov)
        self.ops = TWOFFT.TimePathOps(channel)

    def evaluate(self, y, x):
        """Return normalized log p(y|x), gain moments and Wirtinger score d/dx*."""
        y, x = _array(y, 'y', 1), _array(x, 'x', 1)
        c, sigma2, factor = self.channel, self.noise, self.factor
        if y.shape != (c.n,) or x.shape != (c.n,):
            raise ValueError('observation and data must match channel length')
        xt = PHYSICAL.daft(x, c.c1, c.c2, True)
        yt = PHYSICAL.daft(y, c.c1, c.c2, True)
        b = self.ops.responses_time(xt)
        t = b @ factor
        residual = yt - b @ self.mean
        precision = np.eye(factor.shape[1]) + t.conj().T @ t / sigma2
        chol = np.linalg.cholesky(precision)
        eta = t.conj().T @ residual / sigma2
        latent = np.linalg.solve(chol.conj().T, np.linalg.solve(chol, eta))
        mean = self.mean + factor @ latent
        post_factor = np.linalg.solve(chol, factor.conj().T).conj().T
        covariance = post_factor @ post_factor.conj().T
        # Evaluate the optimized residual plus latent prior penalty, avoiding
        # cancellation between two large Woodbury terms at high SNR.
        conditional_residual = yt - b @ mean
        profile = -float(np.vdot(conditional_residual, conditional_residual).real / sigma2
                         + np.vdot(latent, latent).real)
        logdet = float(2*np.log(chol.diagonal().real).sum())
        likelihood = profile - logdet - c.n*np.log(np.pi*sigma2)
        adj = self.ops.adjoint_time(mean, conditional_residual)
        # Column p is sum_q C[q,p] T_q x, hence T_p^H gives the required index.
        mixed = b @ covariance
        uncertainty = sum(np.roll(self.ops.phase[:, p].conj()*mixed[:, p], -int(delay))
                          for p, delay in enumerate(c.delays))
        score = PHYSICAL.daft((adj-uncertainty)/sigma2, c.c1, c.c2)
        if not all(np.isfinite(a).all() for a in (likelihood, mean, covariance, score)):
            raise FloatingPointError('nonfinite collapsed result')
        return dict(log_likelihood=float(likelihood), h_mean=mean, h_cov=covariance,
                    score=score, profile_log_density=profile,
                    logdet_update=logdet, prior_support_rank=factor.shape[1],
                    prior_roundoff_correction=self.prior_correction)


def dense_operators(channel):
    """Independent finite DFT and explicit CPP time matrices; small N only."""
    n = channel.n
    k = np.arange(n)
    fourier = np.exp(-2j*np.pi*k[:, None]*k[None, :]/n)/np.sqrt(n)
    a = (np.exp(2j*np.pi*channel.c2*k*k)[:, None] * fourier
         * np.exp(2j*np.pi*channel.c1*k*k)[None, :])
    operators = []
    for delay, doppler in zip(channel.delays, channel.dopplers):
        t = np.zeros((n, n), complex)
        for j in range(n):
            source = j-int(delay)
            cpp = np.exp(2j*np.pi*channel.c1*(n*n+2*n*source)) if source < 0 else 1.
            t[j, source % n] = cpp*np.exp(2j*np.pi*j*doppler/n)
        operators.append(a @ t @ a.conj().T)
    return np.array(operators)


def dense_reference(y, x, operators, mean, covariance, noise):
    b = np.einsum('pij,j->ip', operators, x)
    s = noise*np.eye(len(y)) + b @ covariance @ b.conj().T
    r = y-b@mean
    chol = np.linalg.cholesky(s)
    inverse_r = np.linalg.solve(chol.conj().T, np.linalg.solve(chol, r))
    m = mean + covariance@b.conj().T@inverse_r
    c = covariance-covariance@b.conj().T@np.linalg.solve(s, b@covariance)
    h = np.einsum('p,pij->ij', m, operators)
    dc = np.einsum('qp,pji,qjk->ik', c, operators.conj(), operators)
    score = (h.conj().T@(y-h@x)-dc@x)/noise
    likelihood = -len(y)*np.log(np.pi)-2*np.log(chol.diagonal().real).sum()-np.vdot(r,inverse_r).real
    return dict(log_likelihood=float(likelihood), h_mean=m, h_cov=c, score=score)


CONFIG = dict(seed=[20261003,104129,30], independent_draws=4, n=7,
              geometries=['distinct', 'repeat', 'near_repeat', 'cpp_boundary'],
              priors=['zero_mean', 'nonzero_correlated', 'singular', 'known_channel'],
              noises=[.02, 2.], finite_difference_steps=[1e-3,1e-4,1e-5],
              comparison_tolerance=2e-8, derivative_tolerance=2e-6,
              microbenchmark=[[8,2,20],[1024,8,20]], receiver_calls=0)


def calculate(output):
    rng = np.random.default_rng(CONFIG['seed'])
    records = []
    n = CONFIG['n']
    for seed in range(CONFIG['independent_draws']):
        x = rng.normal(size=n)+1j*rng.normal(size=n)
        y = rng.normal(size=n)+1j*rng.normal(size=n)
        direction = rng.normal(size=n)+1j*rng.normal(size=n)
        direction /= np.linalg.norm(direction)
        for geometry in CONFIG['geometries']:
            delays = [0, 1] if geometry == 'distinct' else [n-1, n-1] if geometry == 'cpp_boundary' else [0,0]
            nus = [.31,.31] if geometry == 'repeat' else [.31,.31001] if geometry == 'near_repeat' else [.31,-.27]
            channel = PHYSICAL.Channel(n, .37/n, .13/n**2, delays, nus, [1,1])
            operators = dense_operators(channel)
            action_error = np.linalg.norm(np.einsum('pij,j->ip',operators,x)-channel.regressors(x))
            adjoint_error = abs(np.vdot(channel.apply(x),y)-np.vdot(x,channel.adjoint(y)))
            for prior in CONFIG['priors']:
                mean = np.array([.3+.2j,-.1+.4j]) if prior != 'zero_mean' else np.zeros(2)
                cov = np.array([[.7,.2+.13j],[.2-.13j,.4]])
                if prior == 'zero_mean': cov = np.eye(2)/2
                if prior == 'singular': cov = np.array([[.5,.5j],[-.5j,.5]])
                if prior == 'known_channel': cov = np.zeros((2,2))
                for noise in CONFIG['noises']:
                    model = CollapsedModel(channel,mean,cov,noise)
                    result = model.evaluate(y,x)
                    reference = dense_reference(y,x,operators,mean,cov,noise)
                    errors = {key:float(np.linalg.norm(result[key]-reference[key]) / max(1.,np.linalg.norm(reference[key])))
                              for key in reference}
                    exact_direction = 2*np.vdot(result['score'],direction).real
                    finite_differences = []
                    for step in CONFIG['finite_difference_steps']:
                        derivative = (model.evaluate(y,x+step*direction)['log_likelihood']
                                      -model.evaluate(y,x-step*direction)['log_likelihood'])/(2*step)
                        finite_differences.append(dict(step=step,value=derivative,
                            relative_error=abs(derivative-exact_direction)/max(1.,abs(exact_direction))))
                    index = len(records)
                    np.savez(output/f'case_{index:03d}.npz', x=x,y=y,direction=direction,
                             operators=operators,mean=mean,cov=cov,noise=noise,
                             **{'actual_'+k:result[k] for k in reference},
                             **{'reference_'+k:reference[k] for k in reference})
                    records.append(dict(case=index,seed=seed,geometry=geometry,prior=prior,noise=noise,
                                        errors=errors,action_error=float(action_error),adjoint_error=float(adjoint_error),
                                        directional_derivative=float(exact_direction),finite_differences=finite_differences,
                                        support_rank=result['prior_support_rank'],prior_roundoff=result['prior_roundoff_correction']))
    single = PHYSICAL.Channel(n,.37/n,.13/n**2,[n-1],[.41],[1.])
    model = CollapsedModel(single,[0],[[1]],.3)
    # All equal-modulus x have identical ||U x||^2 for one unitary path.
    logdets = [model.evaluate(y,np.exp(1j*rng.uniform(-np.pi,np.pi,n)))['logdet_update'] for _ in range(8)]
    benchmark = []
    for bn,bp,repeats in CONFIG['microbenchmark']:
        by = rng.normal(size=bn)+1j*rng.normal(size=bn)
        bx = rng.normal(size=bn)+1j*rng.normal(size=bn)
        times = []
        for _ in range(repeats):
            start = time.perf_counter()
            c = PHYSICAL.Channel(bn,.37/bn,.13/bn**2,np.arange(bp)%bn,np.linspace(-.4,.7,bp),np.ones(bp))
            CollapsedModel(c,np.zeros(bp),np.eye(bp)/bp,.3).evaluate(by,bx)
            times.append(time.perf_counter()-start)
        benchmark.append(dict(n=bn,p=bp,seconds=times,mean_seconds=float(np.mean(times)),
                              p95_seconds=float(np.quantile(times,.95)), includes='channel/phase setup, prior factor, 3 DAFT transforms, responses, Gram, solve, covariance, full score',
                              excludes='input generation/import, receiver/data integration/LDPC/storage'))
    dump(output/'raw.json',dict(cases=records,constant_modulus_logdets=logdets,benchmark=benchmark))
    max_errors = {key:max(r['errors'][key] for r in records) for key in reference}
    passed = (max(max_errors.values())<CONFIG['comparison_tolerance']
              and max(r['action_error'] for r in records)<1e-10
              and max(r['adjoint_error'] for r in records)<1e-10
              and max(min(z['relative_error'] for z in r['finite_differences']) for r in records)<CONFIG['derivative_tolerance']
              and np.ptp(logdets)<1e-12)
    if not passed:
        raise AssertionError('collapsed numerical contract failed; raw retained')
    return dict(status='supported_within_Gaussian_fixed_geometry_model', cases=len(records),
                independent_exogenous_draws=CONFIG['independent_draws'],max_errors=max_errors,
                derivative_best_step_max_error=max(min(z['relative_error'] for z in r['finite_differences']) for r in records),
                constant_logdet_range=float(np.ptp(logdets)),benchmark=benchmark,
                production_utility='not_tested')


if __name__ == '__main__':
    run('collapse_v1',CONFIG,SOURCES,calculate)
