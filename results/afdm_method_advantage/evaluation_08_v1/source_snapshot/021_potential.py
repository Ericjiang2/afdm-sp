"""Finite, real-augmented bilinear log-partition diagnostic, not a receiver."""
from pathlib import Path
import sys
import time

import numpy as np
from scipy.special import logsumexp

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.afdm_structured_inference_20261003.common import run, dump
from experiments.afdm_inference_causal_20261002.exact_oracle import enumerate_qpsk
from experiments.afdm_inference_causal_20261002.oracle_comparison import load_frozen


def real_pack(values):
    values = np.asarray(values)
    return np.concatenate([values.real, values.imag], axis=-1)


def finite_potential(z, f, log_prior, eta, xi, sigma2):
    """A y-independent finite base measure. Real coordinates, no Wirtinger factors.

    States are supplied by the caller; this function cannot certify that arbitrary
    states are QPSK or that a caller's base measure is observation independent.
    """
    raw = [np.asarray(a) for a in (z, f, log_prior, eta, xi)]
    if any(np.iscomplexobj(a) for a in raw):
        raise ValueError('potential inputs must use explicit real augmentation')
    z, f, log_prior, eta, xi = [a.astype(float) for a in raw]
    if z.ndim != 2 or f.ndim != 2 or min(z.shape) < 1 or min(f.shape) < 1:
        raise ValueError('z and f require nonempty [states, coordinates] matrices')
    k = len(z)
    if (len(f) != k or log_prior.shape != (k,) or eta.shape != (f.shape[1],)
            or xi.shape != (z.shape[1],)):
        raise ValueError('incompatible state/source dimensions')
    if (not all(np.isfinite(a).all() for a in [z, f, eta, xi])
            or np.isnan(log_prior).any() or np.isposinf(log_prior).any()
            or not np.isfinite(log_prior).any()):
        raise ValueError('invalid finite support or base log probabilities')
    if (not np.isscalar(sigma2) or np.iscomplexobj(sigma2)
            or not np.isfinite(sigma2) or sigma2 <= 0):
        raise ValueError('sigma2 must be finite and positive')
    if abs(float(logsumexp(log_prior))) > 1e-12:
        raise ValueError('base probabilities must sum to one')
    score = log_prior + f @ eta + z @ xi - np.sum(f*f, axis=1)/sigma2
    psi = float(logsumexp(score))
    if not np.isfinite(psi):
        raise FloatingPointError('nonfinite finite partition')
    probability = np.exp(score-psi)
    mz, mf = probability @ z, probability @ f
    dz, df = z-mz, f-mf
    return dict(psi=psi, probabilities=probability, mean_z=mz, mean_f=mf,
                cov_z=dz.T @ (probability[:, None]*dz),
                cov_f=df.T @ (probability[:, None]*df),
                cov_z_f=dz.T @ (probability[:, None]*df))


def source_jvp(z, f, probability, direction_xi, direction_eta):
    """Cov(z,z) v_xi + Cov(z,f) v_eta, without forming either covariance."""
    z, f, probability = np.asarray(z), np.asarray(f), np.asarray(probability)
    score_direction = z @ direction_xi + f @ direction_eta
    return (z-probability @ z).T @ (probability*score_direction)


def make_bilinear_case(kind='general', center=.31, stride=5., delay=1):
    """256 legal finite states, or known-variable reductions; fixed geometry."""
    if kind not in ('general', 'noncircular', 'known_gain', 'constant'):
        raise ValueError('unknown registered case kind')
    physical, _, _ = load_frozen()
    n = 2
    words, _ = enumerate_qpsk(n)
    gains, _ = enumerate_qpsk(2)
    if kind in ('known_gain', 'constant'):
        gains = np.array([[.6+.2j, -.3+.4j]])
    if kind == 'constant':
        words = words[:1]
    h = np.repeat(gains, len(words), axis=0)
    d = np.tile(words, (len(gains), 1))
    c1, c2 = stride/(2*n), (np.sqrt(2)-1)/(2*n*n)
    operators = np.stack([np.column_stack([
                              physical.Channel(n,c1,c2,[l],[nu],[1]).apply(e)
                              for e in np.eye(n)])
                          for l,nu in [(0,center),(delay,center+.47)]])
    pilot = np.array([.35+.1j, -.2+.3j])
    response = np.einsum('kp,pij,kj->ki', h, operators, pilot+d)
    z, f = real_pack(np.concatenate([h,d], axis=1)), real_pack(response)
    logits = np.zeros(len(z))
    if kind == 'noncircular':
        # Discrete y-independent prior deliberately couples I/Q moments.
        logits = 1.7*h[:,0].real + 2.1*h[:,0].real*h[:,0].imag + .8*d[:,0].real
    log_prior = logits-logsumexp(logits)
    return dict(z=z, f=f, log_prior=log_prior, operators=operators, h=h,d=d,pilot=pilot)


def derivative_diagnostic(case, eta, xi, sigma2, step=2e-5):
    z,f,lp = case['z'],case['f'],case['log_prior']
    center = finite_potential(z,f,lp,eta,xi,sigma2)
    gradient = np.empty(len(xi)); hessian = np.empty_like(center['cov_z'])
    cross = np.empty_like(center['cov_z_f'])
    for j in range(len(xi)):
        delta = np.eye(len(xi))[j]*step
        plus = finite_potential(z,f,lp,eta,xi+delta,sigma2)
        minus = finite_potential(z,f,lp,eta,xi-delta,sigma2)
        gradient[j] = (plus['psi']-minus['psi'])/(2*step)
        hessian[:,j] = (plus['mean_z']-minus['mean_z'])/(2*step)
    for j in range(len(eta)):
        delta = np.eye(len(eta))[j]*step
        plus = finite_potential(z,f,lp,eta+delta,xi,sigma2)
        minus = finite_potential(z,f,lp,eta-delta,xi,sigma2)
        cross[:,j] = (plus['mean_z']-minus['mean_z'])/(2*step)
    vx = np.linspace(-.4,.7,len(xi)); ve = np.linspace(.6,-.3,len(eta))
    plus = finite_potential(z,f,lp,eta+step*ve,xi+step*vx,sigma2)
    minus = finite_potential(z,f,lp,eta-step*ve,xi-step*vx,sigma2)
    jvp = source_jvp(z,f,center['probabilities'],vx,ve)
    errors = dict(gradient_max_error=float(np.max(abs(gradient-center['mean_z']))),
            hessian_max_error=float(np.max(abs(hessian-center['cov_z']))),
            cross_max_error=float(np.max(abs(cross-center['cov_z_f']))),
            jvp_max_error=float(np.max(abs((plus['mean_z']-minus['mean_z'])/(2*step)-jvp))),
            response_y_max_error=float(np.max(abs(2*(cross-center['cov_z_f'])/sigma2))),
            min_cov_eigenvalue=float(np.linalg.eigvalsh(center['cov_z']).min()))
    return center, errors, dict(gradient_fd=gradient,hessian_fd=hessian,cross_fd=cross,jvp=jvp)


CONFIG = dict(seed=[20261003,104129,50], kinds=['general','noncircular','known_gain','constant'],
              geometries=[dict(split='development',center=.31,stride=5.,delay=1),
                          dict(split='heldout_center_cpp',center=-1.17,stride=5.3,delay=1)],
              sigma2=.7, difference_step=2e-5, finite_state_limit=256,
              tolerance=2e-8, cases=8, production_hessian=False,
              selection='none; all registered cases retained')


def calculate(output):
    from experiments.afdm_structured_inference_20261003.test_jet_potential import run_registered_tests
    run_registered_tests('PotentialTests',output)
    rng = np.random.default_rng(CONFIG['seed']); records=[]
    for geometry in CONFIG['geometries']:
        for kind in CONFIG['kinds']:
            case = make_bilinear_case(kind, **{k:v for k,v in geometry.items() if k!='split'})
            eta = rng.normal(size=case['f'].shape[1]); xi = rng.normal(size=case['z'].shape[1])*.2
            started=time.perf_counter()
            result,errors,raw = derivative_diagnostic(case,eta,xi,CONFIG['sigma2'])
            # Path relabeling permutes gain coordinates and operators jointly.
            pidx=np.array([1,0,2,3,5,4,6,7])
            perm = finite_potential(case['z'][:,pidx],case['f'],case['log_prior'],eta,xi[pidx],CONFIG['sigma2'])
            errors['path_permutation_error']=float(np.max(abs(perm['mean_z']-result['mean_z'][pidx])))
            # h -> i h, (pilot,d) -> -i(pilot,d) preserves f, with prior pushed forward.
            phase_z=real_pack(np.concatenate([1j*case['h'],-1j*case['d']],axis=1))
            phase_f=real_pack(np.einsum('kp,pij,kj->ki',1j*case['h'],case['operators'],-1j*(case['pilot']+case['d'])))
            errors['phase_physical_error']=float(np.max(abs(phase_f-case['f'])))
            phase = finite_potential(phase_z,phase_f,case['log_prior'],eta,np.zeros_like(xi),CONFIG['sigma2'])
            no_source = finite_potential(case['z'],case['f'],case['log_prior'],eta,np.zeros_like(xi),CONFIG['sigma2'])
            errors['phase_probability_error']=float(np.max(abs(phase['probabilities']-no_source['probabilities'])))
            gain_deviation=case['h']-result['probabilities']@case['h']
            gain_pseudocov=gain_deviation.T@(result['probabilities'][:,None]*gain_deviation)
            index=len(records)
            np.savez(output/f'case_{index:02d}.npz',**case,eta=eta,xi=xi,gain_pseudocov=gain_pseudocov,**result,**raw)
            records.append(dict(index=index,kind=kind,**geometry,states=len(case['z']),errors=errors,
                                covariance_trace=float(np.trace(result['cov_z'])),
                                gain_pseudocov_norm=float(np.linalg.norm(gain_pseudocov)),
                                cross_norm=float(np.linalg.norm(result['cov_z_f'])),
                                seconds=time.perf_counter()-started))
    # C2 is a separate analytic limiting fixture, not the bilinear training task.
    a=np.array([.7,-.2]); source=.63
    z=np.array([[-1.],[1.]]); f=z*a
    eta=np.array([.3,-.4]); xi=np.array([source]); s=float(eta@a+source)
    c2=finite_potential(z,f,np.full(2,-np.log(2)),eta,xi,CONFIG['sigma2'])
    c2_errors=dict(psi=abs(c2['psi']-(np.logaddexp(s,-s)-np.log(2)-a@a/CONFIG['sigma2'])),
                   mean=abs(float(c2['mean_z'][0])-np.tanh(s)),
                   variance=abs(float(c2['cov_z'][0,0])-(1-np.tanh(s)**2)))
    dump(output/'c2_raw.json',dict(a=a.tolist(),eta=eta.tolist(),xi=xi.tolist(),errors=c2_errors))
    dump(output/'records.json',records)
    if max(v for r in records for k,v in r['errors'].items() if k!='min_cov_eigenvalue') > CONFIG['tolerance']:
        raise AssertionError('registered derivative/transform tolerance failed')
    if max(c2_errors.values()) > 1e-12:
        raise AssertionError('C2 analytic limit failed')
    return dict(records=records,c2_errors=c2_errors,status='supported within finite working model',
                support='legal finite QPSK and finite gain prior; not Gaussian-gain oracle',
                learning_contract='fixed support logsumexp preserves support; generic convex network does not',
                cost='O(K*(dim(z)+dim(f))) mean/JVP, K exponential in full-state enumeration')


if __name__ == '__main__':
    sources=[__file__,Path(__file__).with_name('test_jet_potential.py'),
             ROOT/'experiments/afdm_inference_causal_20261002/oracle_comparison.py',
             ROOT/'experiments/afdm_inference_causal_20261002/exact_oracle.py',
             ROOT/'experiments/sp_afdm_frozen_20260920/src/physical.py',
             ROOT/'experiments/sp_afdm_frozen_20260920/src/messages.py',
             ROOT/'experiments/sp_afdm_native_joint_20260921/src/twofft.py']
    run('potential_v1',CONFIG,sources,calculate)
