"""Exact sparse CPP conditional covariance for uniform outside DAFT variance."""
from pathlib import Path
import argparse
import time

import numpy as np
from scipy import sparse
from scipy.linalg import cho_factor, cho_solve
from scipy.sparse.linalg import splu
from scipy.special import logsumexp

from experiments.sp_afdm_frozen_20260920.src.physical import Channel, daft
from experiments.afdm_inference_causal_20261002.exact_oracle import enumerate_qpsk


def cpp_time_matrix(channel):
    """N P entries including the chirp-periodic prefix, with aliases summed."""
    k = np.arange(channel.n)
    rows, cols, values = [], [], []
    for delay, doppler, gain in zip(channel.delays, channel.dopplers, channel.gains):
        cp = np.where(k < delay,
                      np.exp(2j*np.pi*channel.c1*(channel.n**2+2*channel.n*(k-delay))), 1.)
        rows.append(k); cols.append((k-delay) % channel.n)
        values.append(gain*cp*np.exp(2j*np.pi*k*doppler/channel.n))
    matrix = sparse.coo_matrix((np.concatenate(values), (np.concatenate(rows), np.concatenate(cols))),
                               shape=(channel.n, channel.n)).tocsc()
    matrix.sum_duplicates(); matrix.eliminate_zeros()
    return matrix


class ConditionalSolver:
    """S = noise I + v H H^H - v H E_B E_B^H H^H, at ONE gain node.

    E_B is in DAFT coordinates. Sparse LU is an exact generic sparse factor,
    not an assertion that any finite P guarantees small fill or runtime.
    Nonuniform outside variance is rejected, never averaged.
    """
    def __init__(self, channel, variance, target, noise):
        raw_target = np.asarray(target)
        if (raw_target.ndim != 1 or not np.issubdtype(raw_target.dtype, np.integer)
                or len(np.unique(raw_target)) != len(raw_target)
                or np.any(raw_target < 0) or np.any(raw_target >= channel.n)):
            raise ValueError('unique in-range integer target indices required')
        variance = np.asarray(variance, float)
        if variance.ndim == 0:
            variance = np.full(channel.n, float(variance))
        if variance.shape != (channel.n,) or np.any(variance < 0) or not np.isfinite(variance).all():
            raise ValueError('finite nonnegative DAFT variance required')
        outside = np.ones(channel.n, bool); outside[raw_target] = False
        outside_variances = variance[outside]
        if len(outside_variances) and not np.all(outside_variances == outside_variances[0]):
            raise NotImplementedError('nonuniform outside DAFT variance destroys this sparse-base contract')
        self.variance = float(outside_variances[0]) if len(outside_variances) else 0.
        if not np.isfinite(noise) or noise <= 0:
            raise ValueError('positive finite noise required')
        self.channel = channel; self.target = raw_target.astype(int); self.noise = float(noise)
        n, b = channel.n, len(target)
        started = time.perf_counter()
        self.H = cpp_time_matrix(channel)
        base = (self.variance*(self.H@self.H.conj().T)+noise*sparse.eye(n, format='csc')).tocsc()
        self.lu = splu(base)
        self.base_logdet = float(np.log(abs(self.lu.U.diagonal())).sum())
        E = np.zeros((n, b), complex); E[self.target, np.arange(b)] = 1.
        self.V = np.sqrt(self.variance)*(self.H@daft(E, channel.c1, channel.c2, True))
        self.W = self.lu.solve(self.V) if b else np.empty((n, 0), complex)
        small = np.eye(b)-self.V.conj().T@self.W
        self.small_factor = cho_factor(small, lower=True) if b else None
        self.logdet = self.base_logdet+(float(2*np.log(self.small_factor[0].diagonal().real).sum()) if b else 0.)
        self.stats = dict(n=n, paths=channel.p, block=b, time_channel_nnz=int(self.H.nnz),
                          covariance_base_nnz=int(base.nnz), lu_factor_nnz=int(self.lu.L.nnz+self.lu.U.nnz),
                          sparse_factorizations=1, sparse_solve_calls=int(b>0), sparse_solve_rhs=b,
                          small_factorizations=int(b>0), small_solve_calls=0, small_solve_rhs=0,
                          logdet_evaluations=1+int(b>0), low_rank_downdate_constructions=int(b>0),
                          inverse_daft_vectors=b, forward_daft_vectors=0,
                          sparse_channel_matvecs=b, conditional_likelihoods=0,
                          setup_seconds=time.perf_counter()-started, likelihood_seconds=0.)

    def _solve_time(self, rhs):
        value = self.lu.solve(rhs)
        columns = 1 if rhs.ndim == 1 else rhs.shape[1]
        self.stats['sparse_solve_calls'] += 1; self.stats['sparse_solve_rhs'] += columns
        if len(self.target):
            small = cho_solve(self.small_factor, self.V.conj().T@value)
            value = value+self.W@small
            self.stats['small_solve_calls'] += 1; self.stats['small_solve_rhs'] += columns
        return value

    def solve(self, rhs):
        rhs = np.asarray(rhs, complex)
        if rhs.ndim not in (1, 2) or rhs.shape[0] != self.channel.n or not np.isfinite(rhs).all():
            raise ValueError('finite compatible right-hand side required')
        columns = 1 if rhs.ndim == 1 else rhs.shape[1]
        self.stats['inverse_daft_vectors'] += columns; self.stats['forward_daft_vectors'] += columns
        time_rhs = daft(rhs, self.channel.c1, self.channel.c2, True)
        return daft(self._solve_time(time_rhs), self.channel.c1, self.channel.c2)

    def log_likelihood(self, y, x):
        """x = pilot + fixed target data + outside cavity mean, in DAFT."""
        y, x = np.asarray(y, complex), np.asarray(x, complex)
        if y.shape != (self.channel.n,) or x.shape != y.shape or not np.isfinite(y).all() or not np.isfinite(x).all():
            raise ValueError('finite matching observation and mean vectors required')
        started = time.perf_counter()
        residual = daft(y, self.channel.c1, self.channel.c2, True)-self.H@daft(x, self.channel.c1, self.channel.c2, True)
        self.stats['inverse_daft_vectors'] += 2; self.stats['sparse_channel_matvecs'] += 1
        quadratic = float(np.vdot(residual, self._solve_time(residual)).real)
        value = -self.channel.n*np.log(np.pi)-self.logdet-quadratic
        self.stats['conditional_likelihoods'] += 1
        self.stats['likelihood_seconds'] += time.perf_counter()-started
        return float(value)


def finite_block_message(channel, nodes, weights, y, pilot, target, variance, noise, backend='sparse'):
    """Complete uniform-QPSK block message for a fixed positive finite h prior.

    This exactly sums the stated finite node measure, not a converged integral
    over a continuous Gaussian gain prior. No incoming target factor is used.
    """
    if backend not in ('sparse', 'dense'):
        raise ValueError('backend must be sparse or dense')
    nodes = np.asarray(nodes, complex); weights = np.asarray(weights, float)
    if (nodes.ndim != 2 or nodes.shape[1] != channel.p or len(nodes) < 1
            or weights.shape != (len(nodes),) or not np.isfinite(nodes).all()
            or not np.isfinite(weights).all() or np.any(weights <= 0)
            or not np.isclose(weights.sum(), 1., rtol=0., atol=1e-13)):
        raise ValueError('finite compatible gain nodes and positive normalized weights required')
    target = np.asarray(target)
    if (target.ndim != 1 or not np.issubdtype(target.dtype, np.integer)
            or len(target) < 1 or len(np.unique(target)) != len(target)
            or np.any(target < 0) or np.any(target >= channel.n)):
        raise ValueError('nonempty unique in-range integer block required')
    y, pilot = np.asarray(y, complex), np.asarray(pilot, complex)
    if y.shape != (channel.n,) or pilot.shape != y.shape or not np.isfinite(y).all() or not np.isfinite(pilot).all():
        raise ValueError('finite matching observation and fixed outside mean required')
    if not np.isscalar(variance) or not np.isfinite(variance) or variance < 0 or not np.isfinite(noise) or noise <= 0:
        raise ValueError('scalar nonnegative uniform variance and positive noise required')
    started = time.perf_counter()
    # The legal target alphabet is fixed at power .5, independently of the
    # supplied outside variance (which may describe perfectly known outside).
    words, bits = enumerate_qpsk(len(target), amplitude=.5)
    candidates = np.tile(pilot, (len(words), 1)); candidates[:, target] += words
    conditionals = []; operations = []; logdets = []
    for gains in nodes:
        node_channel = Channel(channel.n, channel.c1, channel.c2, channel.delays, channel.dopplers, gains)
        if backend == 'sparse':
            solver = ConditionalSolver(node_channel, variance, target, noise)
            conditional = [solver.log_likelihood(y, x) for x in candidates]
            operations.append(dict(solver.stats)); logdets.append(solver.logdet)
        else:
            setup_start = time.perf_counter()
            H = np.column_stack([node_channel.apply(e) for e in np.eye(channel.n)])
            outside = np.ones(channel.n, bool); outside[target] = False
            S = noise*np.eye(channel.n)+variance*H[:, outside]@H[:, outside].conj().T
            factor = cho_factor(S, lower=True)
            logdet = float(2*np.log(factor[0].diagonal().real).sum())
            setup_seconds = time.perf_counter()-setup_start
            score_start = time.perf_counter(); conditional = []
            for x in candidates:
                residual = y-H@x
                conditional.append(float(-channel.n*np.log(np.pi)-logdet-np.vdot(residual, cho_solve(factor, residual)).real))
            operations.append(dict(dense_factorizations=1, dense_solve_rhs=len(words),
                                   physical_column_actions=channel.n, covariance_assemblies=1,
                                   logdet_evaluations=1, conditional_likelihoods=len(words),
                                   setup_seconds=setup_seconds, likelihood_seconds=time.perf_counter()-score_start))
            logdets.append(logdet)
        conditionals.append(conditional)
    conditionals = np.asarray(conditionals)
    aggregation_start = time.perf_counter()
    scores = logsumexp(conditionals+np.log(weights[:, None]), axis=0)
    normalizer = logsumexp(scores)
    logp = scores-normalizer; probability = np.exp(logp)
    llr = np.array([logsumexp(logp[bits[:, j]==0])-logsumexp(logp[bits[:, j]==1]) for j in range(bits.shape[1])])
    return dict(scores=scores, logp=logp, probability=probability, llr=llr,
                log_evidence=float(normalizer-np.log(len(words))), conditionals=conditionals,
                words=words, bits=bits, candidates=candidates, logdets=np.array(logdets), operations=operations,
                node_count=len(nodes), candidate_count=len(words),
                conditional_likelihood_count=len(nodes)*len(words),
                aggregation_logsumexp_reductions=len(words)+1+2*bits.shape[1],
                aggregation_seconds=time.perf_counter()-aggregation_start,
                full_message_seconds=time.perf_counter()-started,
                finite_measure='declared positive normalized finite prior; no continuous-prior accuracy claim')


CONFIG = dict(seed=20261004071, sizes=[16, 64, 256, 1024], blocks=[1, 2],
              gain_nodes=3, node_weights=[1/6, 1/3, 1/2], candidates_per_node='all 4**block', pd=.5, noise=.12, paths=3,
              delays=[0, 2, 5], dopplers=[.31, -.47, .18], stride=5.3,
              gain_measure='fixed seeded positive finite 3-node prior, independent of y; not Gaussian quadrature convergence',
              purpose='complete finite-node uniform-outside-Gaussian block message; not a continuous-prior or receiver cost claim')


def calculate(output):
    from .common import dump
    rng = np.random.default_rng(CONFIG['seed']); records = []
    prior_started = time.perf_counter()
    nodes = (rng.normal(size=(CONFIG['gain_nodes'], CONFIG['paths']))
             +1j*rng.normal(size=(CONFIG['gain_nodes'], CONFIG['paths'])))/np.sqrt(2*CONFIG['paths'])
    weights = np.asarray(CONFIG['node_weights'])
    prior_setup_seconds = time.perf_counter()-prior_started
    for n in CONFIG['sizes']:
        c1 = CONFIG['stride']/(2*n); c2 = (np.sqrt(2)-1)/(2*n*n)
        y = (rng.normal(size=n)+1j*rng.normal(size=n))/np.sqrt(2)
        pilot = .4*np.exp(.3j*np.arange(n))
        for block in CONFIG['blocks']:
            target = np.arange(block)
            channel = Channel(n, c1, c2, CONFIG['delays'], CONFIG['dopplers'], nodes[0])
            fast = finite_block_message(channel, nodes, weights, y, pilot, target, CONFIG['pd'], CONFIG['noise'])
            dense = finite_block_message(channel, nodes, weights, y, pilot, target, CONFIG['pd'], CONFIG['noise'], 'dense')
            index = len(records)
            arrays = dict(y=y, nodes=nodes, weights=weights, target=target, words=fast['words'], bits=fast['bits'], candidates=fast['candidates'])
            for backend, result in [('sparse', fast), ('dense', dense)]:
                arrays.update({backend+'_'+name:result[name] for name in ['scores', 'logp', 'probability', 'llr', 'conditionals', 'logdets']})
            np.savez(output/f'message_{index:03d}.npz', **arrays)
            errors = {name:float(np.max(abs(fast[name]-dense[name]))) for name in ['scores', 'logp', 'probability', 'llr', 'conditionals', 'logdets']}
            scalar_keys = ['node_count', 'candidate_count', 'conditional_likelihood_count', 'aggregation_logsumexp_reductions',
                           'aggregation_seconds', 'full_message_seconds', 'log_evidence', 'operations']
            record = dict(index=index, n=n, block=block, errors=errors,
                          sparse={key:fast[key] for key in scalar_keys}, dense={key:dense[key] for key in scalar_keys},
                          probability_sum=float(fast['probability'].sum()), scope=CONFIG['purpose'])
            records.append(record); dump(output/f'message_{index:03d}.json', record)
    return dict(records=len(records), max_errors={key:max(r['errors'][key] for r in records) for key in records[0]['errors']},
                fixed_node_prior_setup_seconds=prior_setup_seconds,
                records_by_size={str(n):[r for r in records if r['n']==n] for n in CONFIG['sizes']},
                scope=CONFIG['purpose'],
                cost='one sparse base factor plus one block downdate per node, reused by candidates; fill depends on delay geometry',
                nonuniform_daft_variance='explicitly unsupported; no mean-variance substitution')


if __name__ == '__main__':
    from .common import ROOT, run
    parser = argparse.ArgumentParser(); parser.add_argument('--stage', required=True); args = parser.parse_args()
    run(args.stage, CONFIG, [__file__, Path(__file__).with_name('test_conditional_solver.py'),
                            ROOT/'experiments/sp_afdm_frozen_20260920/src/physical.py',
                            ROOT/'experiments/afdm_inference_causal_20261002/exact_oracle.py'], calculate)
