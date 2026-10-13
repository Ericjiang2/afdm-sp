"""Collision information and bounded estimation in a declared covariance model.

q is the SQUARE OF THE HALF GAP. Known data is oracle; pilot/cavity models
match second moments only. All calculations use the unitary time coordinates.
"""
from dataclasses import dataclass
from pathlib import Path
import argparse
import time

import numpy as np
from scipy.linalg import cho_factor, cho_solve, solve_triangular
from scipy.optimize import minimize

from experiments.sp_afdm_frozen_20260920.src.physical import daft, regressors


@dataclass
class CollisionModel:
    n: int
    c1: float
    c2: float
    delay: int
    mean: np.ndarray
    variance: np.ndarray

    def __post_init__(self):
        self.mean = np.asarray(self.mean, complex)
        self.variance = np.asarray(self.variance, float)
        if (self.n < 2 or not isinstance(self.delay, (int, np.integer))
                or not 0 <= self.delay < self.n or self.mean.shape != (self.n,)
                or self.variance.shape != (self.n,) or np.any(self.variance < 0)
                or not np.isfinite(self.mean).all() or not np.isfinite(self.variance).all()
                or not np.isfinite([self.c1, self.c2]).all()):
            raise ValueError('finite matching moments, nonnegative variance and integer delay required')
        k = np.arange(self.n)
        cp = np.where(k < self.delay,
                      np.exp(2j*np.pi*self.c1*(self.n**2+2*self.n*(k-self.delay))), 1.)
        index = (k-self.delay) % self.n
        m = cp*daft(self.mean, self.c1, self.c2, True)[index]
        # Scalar variance commutes exactly with every unitary path operator.
        if np.all(self.variance == self.variance[0]):
            cov = self.variance[0]*np.eye(self.n)
        else:
            transform = daft(np.eye(self.n), self.c1, self.c2, True)
            transform = cp[:, None]*transform[index]
            cov = (transform*self.variance) @ transform.conj().T
        self.base = np.outer(m, m.conj())+cov
        self.omega = 2*np.pi*(k[:, None]-k[None, :])/self.n

    def covariance(self, center, q, power, noise, derivatives=False):
        if not np.isfinite([center, q, power, noise]).all() or q < 0 or power <= 0 or noise <= 0:
            raise ValueError('finite center, q >= 0, positive total power and noise required')
        centered = np.exp(1j*self.omega*center)*self.base
        gap = np.sqrt(q)
        signal = np.cos(self.omega*gap)*centered
        K = power*signal+noise*np.eye(self.n)
        if not derivatives:
            return K
        # sinc removes the removable 0/0 singularity at q=0, without jitter.
        dq = -.5*self.omega**2*np.sinc(self.omega*gap/np.pi)*centered*power
        dcenter = 1j*self.omega*signal*power
        return K, [dq, dcenter, signal, np.eye(self.n)]


def effective_information(K, derivatives):
    """Proper complex Fisher metric; derivative order q, center, power, noise."""
    L = np.linalg.cholesky(K)
    whitened = []
    for D in derivatives:
        left = solve_triangular(L, D, lower=True)
        whitened.append(solve_triangular(L, left.conj().T, lower=True).conj().T)
    vectors = np.array([np.concatenate((D.real.ravel(), D.imag.ravel())) for D in whitened])
    fisher = vectors@vectors.T
    nuisance = vectors[1:].T
    coefficients, _, rank, _ = np.linalg.lstsq(nuisance, vectors[0], rcond=None)
    residual = vectors[0]-nuisance@coefficients
    projected = float(residual@residual)
    schur = float(fisher[0, 0]-fisher[0, 1:]@np.linalg.pinv(fisher[1:, 1:], hermitian=True)@fisher[1:, 0])
    return dict(fisher=fisher, effective_projection=projected, effective_schur=schur,
                nuisance_rank=int(rank), nuisance_coefficients=coefficients)


def objective_and_gradient(model, y_time, parameters):
    center, q, logpower, lognoise = parameters
    power, noise = np.exp(logpower), np.exp(lognoise)
    K, derivatives = model.covariance(center, q, power, noise, True)
    factor = cho_factor(K, lower=True)
    alpha = cho_solve(factor, y_time)
    value = float(2*np.log(factor[0].diagonal().real).sum()+np.vdot(y_time, alpha).real)
    inverse = cho_solve(factor, np.eye(model.n))
    gradient = [float(np.trace(inverse@D).real-np.vdot(alpha, D@alpha).real) for D in derivatives]
    return value, np.array([gradient[1], gradient[0], gradient[2]*power, gradient[3]*noise])


SEARCH = dict(center_bounds=[-1.5, 1.5], half_gap_max=.6, power_bounds=[.05, 5.],
              noise_bounds=[.01, 2.], center_points=13, gap_points=7,
              starts=4, maxiter=100, ftol=1e-9)


def estimate(model, y, coordinates='center_q', search=None):
    """Observation-only multistart estimate. Domain, starts and nuisance bounds fixed.

    Both coordinate systems use the same physical domain and coarse starts.
    No true center, gap, power, noise or symbols enter this API.
    """
    if coordinates not in ('center_q', 'two_path'):
        raise ValueError('unknown coordinate system')
    search = SEARCH if search is None else search
    y = np.asarray(y, complex)
    if y.shape != (model.n,) or not np.isfinite(y).all():
        raise ValueError('finite observation of declared dimension required')
    y_time = daft(y, model.c1, model.c2, True)
    low, high = search['center_bounds']
    gapmax = search['half_gap_max']
    lp = np.log(search['power_bounds']); ln = np.log(search['noise_bounds'])
    coarse = []
    for center in np.linspace(low, high, search['center_points']):
        for gap in np.linspace(0, gapmax, search['gap_points']):
            point = np.array([center, gap**2, 0., np.log(.2)])
            value, _ = objective_and_gradient(model, y_time, point)
            coarse.append((value, point))
    coarse.sort(key=lambda item: item[0])  # stable fixed ordinal tie break
    off_diagonal = model.base-np.diag(np.diag(model.base))
    if not np.any(off_diagonal):
        return dict(coordinates=coordinates, identifiable=False,
                    reason='second-moment covariance independent of center and q',
                    center=None, q=None, half_gap=None, paths=None, objective=coarse[0][0],
                    boundary=None, successful_starts=0, evaluations=len(coarse), fits=[]), np.array([
                        [v, *p] for v, p in coarse])
    fits = []
    start_time = time.perf_counter()
    for coarse_value, point in coarse[:search['starts']]:
        if coordinates == 'center_q':
            initial = point
            bounds = [(low, high), (0., gapmax**2), tuple(lp), tuple(ln)]
            constraints = ()

            def fun(t):
                return objective_and_gradient(model, y_time, t)
        else:
            mu, q, p, s = point
            initial = np.array([mu-np.sqrt(q), mu+np.sqrt(q), p, s])
            bounds = [(low-gapmax, high+gapmax)]*2+[tuple(lp), tuple(ln)]
            constraints = ({'type': 'ineq', 'fun': lambda t: np.array([
                (t[0]+t[1])/2-low, high-(t[0]+t[1])/2, t[1]-t[0],
                2*gapmax-(t[1]-t[0])])},)

            def fun(t):
                gap = (t[1]-t[0])/2
                value, grad = objective_and_gradient(model, y_time,
                                                     [(t[0]+t[1])/2, gap**2, t[2], t[3]])
                return value, np.array([.5*grad[0]-gap*grad[1], .5*grad[0]+gap*grad[1], *grad[2:]])
        fit = minimize(fun, initial, jac=True, method='SLSQP', bounds=bounds, constraints=constraints,
                       options=dict(maxiter=search['maxiter'], ftol=search['ftol']))
        if coordinates == 'center_q':
            mu, q, p, s = fit.x
        else:
            a, b, p, s = fit.x
            mu, q = (a+b)/2, ((b-a)/2)**2
        feasible = low-1e-7 <= mu <= high+1e-7 and 0 <= q <= gapmax**2+1e-7
        fits.append(dict(center=float(mu), q=float(q), power=float(np.exp(p)), noise=float(np.exp(s)),
                         objective=float(fit.fun), success=bool(fit.success), feasible=bool(feasible),
                         message=str(fit.message), evaluations=int(fit.nfev), iterations=int(fit.nit),
                         initial=initial.tolist(), initial_objective=float(coarse_value)))
    # Failed optimizer attempts remain in the ledger. A feasible coarse point
    # remains an explicit candidate, rather than silently pretending convergence.
    best = min([f for f in fits if f['feasible']], key=lambda f: f['objective'], default=None)
    if best is None or best['objective'] > coarse[0][0]:
        value, point = coarse[0]
        mu, q, p, s = point
        best = dict(center=float(mu), q=float(q), power=float(np.exp(p)), noise=float(np.exp(s)),
                    objective=float(value), success=False, message='coarse grid candidate retained')
    gap = np.sqrt(best['q'])
    result = dict(best)
    result.update(coordinates=coordinates, identifiable=True, half_gap=float(gap),
                paths=[best['center']-float(gap), best['center']+float(gap)],
                boundary=bool(best['q'] < 1e-8), search_edge=bool(
                    abs(best['center']-low)<1e-6 or abs(best['center']-high)<1e-6 or abs(gap-gapmax)<1e-6),
                successful_starts=sum(f['success'] for f in fits), evaluations=len(coarse)+sum(f['evaluations'] for f in fits),
                fits=fits, seconds=time.perf_counter()-start_time)
    return result, np.array([[v, *p] for v, p in coarse])


INFO_CONFIG = dict(seed=20261004061, n=16, half_gaps=[0., .001, .02, .15, .4],
                   centers=[-.41, .73], noises=[.05, .5], delay=15, stride=5.3,
                   modes=['known_data_oracle', 'pilot_uniform', 'fixed_soft_cavity', 'no_pilot_uniform'],
                   power=1., pd=.5, finite_difference_steps=[1e-3, 3e-4, 1e-4],
                   purpose='complex Gaussian covariance Fisher, not full QPSK likelihood Fisher')
ESTIMATE_CONFIG = dict(seed=20261004062, n=16, centers=[-.65, .43],
                       half_gaps=[0., .015, .12, .35], noises=[.05, .5], repeats=3,
                       modes=['pilot_uniform', 'fixed_soft_cavity', 'no_pilot_uniform'],
                       delay=15, stride=5.3, power=1., pd=.5, search=SEARCH,
                       purpose='bounded observation-only covariance quasi-MLE; known fixed delay')


def moments(n, mode, rng):
    pilot = .65*np.exp(.31j*np.arange(n))
    data = np.sqrt(.25)*(rng.choice([-1, 1], n)+1j*rng.choice([-1, 1], n))
    if mode == 'known_data_oracle':
        return pilot+data, np.zeros(n)
    if mode == 'pilot_uniform':
        return pilot, np.full(n, .5)
    if mode == 'fixed_soft_cavity':
        # Legal independent I/Q probabilities fixed before observing y.
        soft = .5*(.45*np.cos(.7*np.arange(n))+1j*.35*np.sin(.4*np.arange(n)))
        return pilot+soft, .5-abs(soft)**2
    if mode == 'no_pilot_uniform':
        return np.zeros(n), np.full(n, .5)
    raise ValueError('unknown moment object')


def calculate_information(output):
    from .common import dump
    config = INFO_CONFIG; rng = np.random.default_rng(config['seed']); records = []
    n = config['n']; c1 = config['stride']/(2*n); c2 = (np.sqrt(2)-1)/(2*n*n)
    for mode in config['modes']:
        mean, variance = moments(n, mode, rng)
        model = CollisionModel(n, c1, c2, config['delay'], mean, variance)
        for center in config['centers']:
            for noise in config['noises']:
                K0, D0 = model.covariance(center, 0., config['power'], noise, True)
                remainders = []
                for q in config['finite_difference_steps']:
                    remainder = np.linalg.norm(model.covariance(center, q, config['power'], noise)-K0-q*D0[0])
                    remainders.append(dict(q=q, absolute=float(remainder), scaled_q2=float(remainder/q**2)))
                for gap in config['half_gaps']:
                    K, D = model.covariance(center, gap**2, config['power'], noise, True)
                    info = effective_information(K, D)
                    record = dict(mode=mode, center=center, half_gap=gap, q=gap**2, noise=noise,
                                  fisher=info['fisher'].tolist(), effective_projection=info['effective_projection'],
                                  effective_schur=info['effective_schur'], nuisance_rank=info['nuisance_rank'],
                                  schur_projection_error=abs(info['effective_schur']-info['effective_projection']),
                                  delta_effective_information=4*gap**2*info['effective_projection'],
                                  expansion=remainders, boundary=gap==0.)
                    records.append(record)
                    np.savez(output/f'information_{len(records)-1:03d}.npz', mean=mean, variance=variance,
                             covariance=K, derivatives=np.array(D), fisher=info['fisher'])
    dump(output/'records.json', records)
    return dict(records=len(records), max_projection_error=max(r['schur_projection_error'] for r in records),
                by_mode={mode:dict(min_effective=min(r['effective_projection'] for r in records if r['mode']==mode),
                                   max_effective=max(r['effective_projection'] for r in records if r['mode']==mode))
                         for mode in config['modes']},
                scope=config['purpose'], boundary='q >= 0; no regular CRLB claim at zero')


def calculate_estimation(output):
    from .common import dump
    config = ESTIMATE_CONFIG; records = []; n = config['n']
    c1 = config['stride']/(2*n); c2 = (np.sqrt(2)-1)/(2*n*n)
    for mode in config['modes']:
        mean, variance = moments(n, mode, np.random.default_rng(config['seed']))
        model = CollisionModel(n, c1, c2, config['delay'], mean, variance)
        for rep in range(config['repeats']):
            # The same exogenous channel/data/noise is paired across geometry/noise.
            rng = np.random.default_rng([config['seed'], rep])
            gains = (rng.normal(size=2)+1j*rng.normal(size=2))/2
            noise_base = (rng.normal(size=n)+1j*rng.normal(size=n))/np.sqrt(2)
            if mode == 'fixed_soft_cavity':
                pilot = .65*np.exp(.31j*np.arange(n)); soft = mean-pilot
                data = .5*(np.where(rng.random(n)<.5+soft.real, 1, -1)
                           +1j*np.where(rng.random(n)<.5+soft.imag, 1, -1))
            else:
                pilot = mean
                data = .5*(rng.choice([-1, 1], n)+1j*rng.choice([-1, 1], n))
            x = pilot+data
            for center in config['centers']:
                for gap in config['half_gaps']:
                    paths = center+np.array([-gap, gap])
                    signal = regressors(x, [config['delay']]*2, paths, c1, c2)@gains
                    for noise in config['noises']:
                        y = signal+np.sqrt(noise)*noise_base
                        arms = {}; arrays = dict(y=y, mean=mean, variance=variance, truth_paths=paths,
                                                truth_gains=gains, truth_data=data, exogenous_noise=noise_base)
                        for coordinates in ['center_q', 'two_path']:
                            fit, grid = estimate(model, y, coordinates, config['search'])
                            if fit['identifiable']:
                                fit['center_error'] = fit['center']-center
                                fit['q_error'] = fit['q']-gap**2
                                fit['half_gap_error'] = fit['half_gap']-gap
                                fit['path_rmse'] = float(np.sqrt(np.mean((np.array(fit['paths'])-paths)**2)))
                            arms[coordinates] = fit; arrays[coordinates+'_grid'] = grid
                        index = len(records)
                        np.savez(output/f'estimate_{index:03d}.npz', **arrays)
                        record = dict(index=index, mode=mode, rep=rep, true_center=center, true_half_gap=gap,
                                      true_noise=noise, arms=arms, truth_is_scoring_only=True)
                        records.append(record)
                        dump(output/f'estimate_{index:03d}.json', record)
    summary = {}
    for mode in config['modes']:
        group = [r for r in records if r['mode']==mode]
        summary[mode] = {}
        for coord in ['center_q', 'two_path']:
            fits = [r['arms'][coord] for r in group]
            identifiable = [f for f in fits if f['identifiable']]
            summary[mode][coord] = dict(cases=len(fits), nonidentifiable=len(fits)-len(identifiable),
                boundary=sum(f['boundary'] for f in identifiable),
                unsuccessful_selected=sum(not f['success'] for f in identifiable),
                center_rmse=float(np.sqrt(np.mean([f['center_error']**2 for f in identifiable]))) if identifiable else None,
                q_rmse=float(np.sqrt(np.mean([f['q_error']**2 for f in identifiable]))) if identifiable else None,
                path_rmse=float(np.sqrt(np.mean([f['path_rmse']**2 for f in identifiable]))) if identifiable else None,
                evaluations=sum(f['evaluations'] for f in fits))
        summary[mode]['objective_difference_mean'] = float(np.mean([
            r['arms']['center_q']['objective']-r['arms']['two_path']['objective'] for r in group]))
    return dict(records=len(records), summary=summary, scope=config['purpose'],
                interpretation='coordinates change numerical optimization; they do not create information',
                independent_exogenous_clusters=config['repeats'])


if __name__ == '__main__':
    from .common import ROOT, run
    parser = argparse.ArgumentParser(); parser.add_argument('study', choices=['information', 'estimation'])
    parser.add_argument('--stage', required=True); args = parser.parse_args()
    sources = [__file__, Path(__file__).with_name('test_collision.py'),
               ROOT/'experiments/sp_afdm_frozen_20260920/src/physical.py']
    run(args.stage, INFO_CONFIG if args.study=='information' else ESTIMATE_CONFIG, sources,
        calculate_information if args.study=='information' else calculate_estimation)
