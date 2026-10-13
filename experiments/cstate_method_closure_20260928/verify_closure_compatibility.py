"""Source-bound finite operator tests. No receiver, decoder, truth or simulation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PHYSICAL = ROOT / 'experiments/sp_afdm_frozen_20260920/src/physical.py'
EXPECTED_SHA = 'c0398247b59d10366a0602a3bf115271e57d339e5a783691dd703e4da02348c6'
ATOL, RTOL = 5e-11, 1e-10


def run() -> dict:
    actual = hashlib.sha256(PHYSICAL.read_bytes()).hexdigest()
    if actual != EXPECTED_SHA:
        raise ValueError('frozen physical operator source changed')
    sys.path.insert(0, str(PHYSICAL.parent))
    from physical import Channel, dkernel, projected_variance

    checks: list[dict] = []
    witnesses: list[dict] = []

    def equal(name: str, got, expected, case: str) -> None:
        a, b = np.asarray(got), np.asarray(expected)
        np.testing.assert_allclose(a, b, atol=ATOL, rtol=RTOL,
                                   err_msg=f'{name}: {case}')
        checks.append({'name': name, 'case': case,
                       'max_absolute_error': float(np.max(np.abs(a-b)))})

    def matrices(n: int, delays: list[int], nus: list[float]):
        c1, c2 = 5/(2*n), (np.sqrt(2)-1)/(2*n*n)
        eye = np.eye(n, dtype=complex)
        source = []
        k = np.arange(n)
        fourier = np.exp(-2j*np.pi*np.outer(k, k)/n)/np.sqrt(n)
        af = np.exp(2j*np.pi*c2*k*k)[:, None]*fourier*np.exp(2j*np.pi*c1*k*k)[None, :]
        for l, nu in zip(delays, nus, strict=True):
            channel = Channel(n, c1, c2, np.array([l]), np.array([nu]), np.ones(1))
            op = np.column_stack([channel.apply(eye[:, j]) for j in range(n)])
            shifted = k-l
            cp = np.where(shifted < 0, np.exp(2j*np.pi*c1*(n*n+2*n*shifted)), 1)
            td = np.zeros((n, n), complex)
            td[k, shifted % n] = cp*np.exp(2j*np.pi*k*nu/n)
            equal('frozen_CPP_operator', op, af@td@af.conj().T, f'N={n},l={l},nu={nu}')
            equal('operator_unitarity', op.conj().T@op, eye, f'N={n},l={l},nu={nu}')
            source.append(op)
        return source, af, c1

    def gamma(ops, covariance):
        return np.array([[np.trace(a.conj().T@b@covariance) for b in ops] for a in ops])

    for n in (8, 15, 31):
        for case, delays, nus in (
            ('same_fractional', [n-1, n-1], [.2, .57]),
            ('same_integer', [1, 1], [.2, 1.2]),
            ('same_duplicate', [1, 1], [.2, .2]),
            ('same_near_duplicate', [1, 1], [.2, .20000001]),
            ('distinct', [0, 1], [2.5, -2.5]),
        ):
            ops, af, c1 = matrices(n, delays, nus)
            m = ops[0].conj().T@ops[1]
            delta = nus[1]-nus[0]
            expected_r = dkernel(delta, n) if delays[0] == delays[1] else 0
            equal('positive_sign_R12', np.trace(m)/n, expected_r, f'{case},N={n}')
            equal('isotropic_Gamma', gamma(ops, .17*np.eye(n)),
                  .17*n*np.array([[1, expected_r], [np.conj(expected_r), 1]]), case)
            for k in range(n):
                covariance = np.zeros((n, n)); covariance[k, k] = 1
                equal('rank_one_AF_diagonal', gamma(ops, covariance)[0, 1], m[k, k], case)
            v = .1 + np.arange(n)/(3*n)
            equal('source_AF_diagonal_Gamma', gamma(ops, np.diag(v)),
                  projected_variance(v, delays, nus, c1), case)
            equal('zero_covariance_family', gamma(ops, np.zeros((n, n))), np.zeros((2, 2)), case)
            if delays[0] == delays[1]:
                equal('same_delay_AF_constant_diagonal', np.diag(m), np.full(n, expected_r), case)
                r = float(abs(expected_r))
                gram = np.array([[1, expected_r], [np.conj(expected_r), 1]])
                equal('doublet_eigenvalues', np.linalg.eigvalsh(gram), [1-r, 1+r], case)
                equal('doublet_scalar_minimum_attained', np.linalg.norm(gram-np.eye(2), 2), r, case)
                for scalar in (0, .5, 1, 1.5, 2, 1+.1j, -1j):
                    if np.linalg.norm(gram-scalar*np.eye(2), 2) < r-ATOL:
                        raise AssertionError('scalar minimax lower bound failed')
                if case == 'same_integer':
                    equal('AF_diagonal_exact_integer_doublet', gamma(ops, np.diag(v)),
                          np.sum(v)*np.eye(2), case)
                    transformed = af.conj().T@m@af
                    equal('other_basis_nonzero_diagonal_magnitude', abs(np.diag(transformed)), np.ones(n), case)
                    witnesses.append({'case': 'basis_dependence', 'N': n,
                                      'AF_diagonal_max': float(max(abs(np.diag(m)))),
                                      'time_diagonal_min_abs': float(min(abs(np.diag(transformed))))})
            else:
                equal('distinct_delay_isotropic_exact', np.trace(m), 0, case)
                witness = np.zeros((n, n)); witness[0, 0] = 1
                g = gamma(ops, witness)
                equal('distinct_delay_AF_nonuniform_counterexample', abs(g[0, 1]), 1, case)
                witnesses.append({'case': 'unique_delay_not_AF_diagonal_exact', 'N': n,
                                  'offdiagonal_abs': float(abs(g[0, 1]))})
            eigenvalues, eigenvectors = np.linalg.eig(m)
            x = eigenvectors[:, 0]/np.linalg.norm(eigenvectors[:, 0])
            witness = np.outer(x, x.conj())
            equal('complex_PSD_witness_unitary_cross_term', abs(np.trace(m@witness)), 1, case)
            equal('PSD_witness_eigenvalue', np.trace(m@witness), eigenvalues[0], case)

    # Complex PSD tests are essential when M is not Hermitian.
    skew = np.array([[0, 1], [-1, 0]], complex)
    for x in (np.array([1., 0]), np.array([0., 1]), np.array([1., 2])):
        equal('real_vector_false_negative', x@skew@x, 0, 'generic_unitary_skew')
    x = np.array([1, 1j])/np.sqrt(2)
    equal('complex_vector_detects_skew', np.vdot(x, skew@x), 1j, 'generic_unitary_skew')
    witnesses.append({'case': 'complex_rank_one_required', 'offdiagonal_abs': 1.0})

    asymptotic = []
    for delta in (.37, -.63, 1.4, -2.3):
        limit = np.exp(1j*np.pi*delta)*np.sinc(delta)
        records = []
        for n in (32, 64, 128, 256):
            finite = np.exp(2j*np.pi*np.arange(n)*delta/n).mean()
            equal('Dirichlet_finite_sum_source', dkernel(delta, n), finite, f'{delta}/{n}')
            equal('Dirichlet_negative_conjugate', dkernel(-delta, n), np.conj(finite), f'{delta}/{n}')
            bracket = 1-1j*np.pi*delta/n-(np.pi*delta)**2/(3*n*n)
            scaled_remainder = (finite/limit-bracket)*n**4
            coefficient = -(np.pi*delta)**4/45
            if abs(scaled_remainder-coefficient) > .05*(1+abs(coefficient)):
                raise AssertionError(f'asymptotic fourth-order remainder failed {delta}/{n}')
            records.append({'N': n, 'limit_absolute_error': float(abs(finite-limit)),
                            'scaled_fourth_remainder_real': float(scaled_remainder.real),
                            'scaled_fourth_remainder_imag': float(scaled_remainder.imag)})
        if abs(np.conj(limit)-limit) > .1 and abs(finite-limit) >= abs(finite-np.conj(limit)):
            raise AssertionError('positive phase sign not distinguished')
        asymptotic.append({'delta_fixed': delta, 'limit_real': float(limit.real),
                           'limit_imag': float(limit.imag), 'records': records})
    for n in (8, 15, 31):
        for delta in (0, n, -n, 2*n, 1, -1, n+.25):
            finite = np.exp(2j*np.pi*np.arange(n)*delta/n).mean()
            equal('Dirichlet_removable_periodic_boundary', dkernel(delta, n), finite, f'{delta}/{n}')
    return {'schema': 'closure-compatibility-finite-tests/1', 'status': 'pass',
            'source_sha256': {str(PHYSICAL.relative_to(ROOT)): actual},
            'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'numpy_version': np.__version__, 'dimensions': [8, 15, 31],
            'tolerances': {'atol': ATOL, 'rtol': RTOL}, 'checks': checks,
            'comparison_count': len(checks), 'counterexamples': witnesses,
            'asymptotic_finite_sequences': asymptotic,
            'new_receiver_calls': 0, 'new_decoder_calls': 0, 'new_observations': 0,
            'limitation': 'Finite cases corroborate the analytic proof; no universal quantifier or asymptotic theorem is proved by numerics.'}


if __name__ == '__main__':
    print(json.dumps(run(), indent=2, sort_keys=True, allow_nan=False))
