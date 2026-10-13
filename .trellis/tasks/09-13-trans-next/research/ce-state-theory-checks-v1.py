"""Finite algebra checks; not receiver experiments or statistical confirmation."""
import hashlib
import itertools
import json
from pathlib import Path
import sys
import time

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'afdm_sp_joint_unrolled'))
sys.path.insert(0, str(ROOT))
from afdm_sp_joint_unrolled.classical_joint_unrolled import soft_gain_update


def operator(n, delay, doppler, spacing=5, c2=.023):
    cols = np.arange(n)
    rows = (cols + spacing * delay + doppler) % n
    c1 = spacing / (2 * n)
    phase = np.exp(2j * np.pi * (-c1 * delay**2 + c2 * (rows**2 - cols**2)
                                 - delay * cols / n))
    result = np.zeros((n, n), dtype=np.complex128)
    result[rows, cols] = phase
    return result


def run():
    started = time.perf_counter()
    rng = np.random.default_rng(2026091401)
    draw = lambda shape: (rng.normal(size=shape) + 1j * rng.normal(size=shape)) / np.sqrt(2)
    n, k = 8, 3
    basis = [operator(n, *item) for item in [(0, 0), (1, 0), (1, 1)]]
    F = np.array([[np.vdot(a, b) for b in basis] for a in basis])
    np.testing.assert_allclose(F, n * np.eye(k), atol=1e-12)
    gains, previous = draw(k), draw(k)
    tail = .24 * operator(n, 2, 0)
    assert max(abs(np.vdot(u, tail)) for u in basis) < 1e-12
    H = sum(g * u for g, u in zip(gains, basis)) + tail
    p, data, mu, noise = [draw(n) for _ in range(4)]
    y = H @ (p + data) + noise
    lam, sigma2 = .4, .3
    results = {'scope': 'Synthetic algebra and two shared CE unit calls; 0 G1 receiver/FER calls',
               'seed': 2026091401, 'affine_risk': []}
    for name in ('prior', 'GLS'):
        A = np.column_stack([u @ (p + mu) for u in basis])
        raw = draw((n, n))
        C = raw @ raw.conj().T + np.eye(n)
        W = np.eye(n) if name == 'prior' else sigma2 * np.linalg.inv(C)
        Q = .2 * np.eye(k) if name == 'prior' else np.zeros((k, k))
        M = A.conj().T @ W @ A + lam * np.eye(k) + Q
        B = np.linalg.solve(M, A.conj().T @ W)
        c = np.linalg.solve(M, lam * previous)
        estimate = B @ y + c
        kwargs = {'Q': torch.as_tensor(Q)} if name == 'prior' else {
            'C': torch.as_tensor(C), 'sigma2': torch.tensor(sigma2, dtype=torch.float64)}
        actual = soft_gain_update(torch.as_tensor(A), torch.as_tensor(y),
                                  torch.as_tensor(previous), torch.tensor(lam, dtype=torch.float64),
                                  **kwargs).numpy()
        np.testing.assert_allclose(actual, estimate, rtol=1e-12, atol=1e-12)
        terms = [(B @ A - np.eye(k)) @ gains + c,
                 B @ tail @ (p + mu), B @ H @ (data - mu), B @ noise]
        error = estimate - gains
        residual = float(np.linalg.norm(sum(terms) - error))
        cross = [float(2 * np.vdot(terms[i], terms[j]).real)
                 for i in range(4) for j in range(i + 1, 4)]
        reconstructed_energy = sum(float(np.vdot(t, t).real) for t in terms) + sum(cross)
        np.testing.assert_allclose(reconstructed_energy, np.vdot(error, error).real,
                                   rtol=1e-12, atol=1e-12)
        assert residual < 1e-11
        L = B @ A - np.eye(k)
        G = draw((k, 16)) + .2
        Eta = draw((n, k)) @ G + draw((n, 16)) + .4j
        mg, me = G.mean(axis=1), Eta.mean(axis=1)
        Gc, Ec = G - mg[:, None], Eta - me[:, None]
        Rg, Ce, Cge = Gc @ Gc.conj().T / 16, Ec @ Ec.conj().T / 16, Gc @ Ec.conj().T / 16
        bias = L @ mg + c + B @ me
        formula = (np.vdot(bias, bias).real + np.trace(L @ Rg @ L.conj().T).real
                   + np.trace(B @ Ce @ B.conj().T).real
                   + 2 * np.trace(L @ Cge @ B.conj().T).real)
        empirical = np.mean(np.sum(abs(L @ G + c[:, None] + B @ Eta)**2, axis=0))
        np.testing.assert_allclose(formula, empirical, rtol=1e-12, atol=1e-12)
        results['affine_risk'].append(dict(mode=name, reconstruction_residual=residual,
            shared_CE_relative_error=float(np.linalg.norm(actual - estimate) / np.linalg.norm(estimate)),
            cross_terms=cross, conditional_risk_identity_error=float(abs(formula - empirical))))

    design, obs, center = draw((9, 4)), draw(9), draw(4)
    J = design.conj().T @ design + .3 * np.eye(4)
    b = design.conj().T @ obs + .3 * center
    J0, q, h = J[:-1, :-1], J[:-1, -1], J[-1, -1]
    z = np.linalg.solve(J0, q)
    schur = float((h - np.vdot(q, z)).real)
    assert schur > 0
    drop = float(abs(b[-1] - np.vdot(q, np.linalg.solve(J0, b[:-1])))**2 / schur)
    actual_drop = float((np.vdot(b, np.linalg.solve(J, b))
                         - np.vdot(b[:-1], np.linalg.solve(J0, b[:-1]))).real)
    np.testing.assert_allclose(drop, actual_drop, rtol=1e-12)
    G = design.conj().T @ design
    G0, r = G[:-1, :-1], G[:-1, -1]
    z = np.linalg.solve(G0, r)
    s = float((G[-1, -1] - np.vdot(r, z)).real)
    trace_increment = float(np.trace(np.linalg.inv(G)).real - np.trace(np.linalg.inv(G0)).real)
    np.testing.assert_allclose(trace_increment, (1 + np.vdot(z, z).real) / s, rtol=1e-12)
    results['schur'] = dict(value=schur, frozen_objective_drop=drop,
                           objective_identity_error=abs(drop - actual_drop),
                           white_LS_variance_increment=trace_increment)

    size = 1024
    index = np.arange(size)
    variance = .25 * (1 + np.cos(2 * np.pi * index / size))
    c1 = 5 / (2 * size)
    phase0 = np.exp(2j * np.pi * (-c1 * 3**2 - 3 * index / size))
    phase1 = np.exp(2j * np.pi * (-c1 * 4**2 - 4 * index / size))
    cross = np.vdot(phase0, variance * phase1)
    q01_uniform = np.vdot(phase0, .25 * phase1)
    np.testing.assert_allclose([variance.sum(), abs(cross)], [256, 128], atol=1e-11)
    assert abs(q01_uniform) < 1e-11
    real_mean = np.sqrt(np.maximum(0, (.5 - variance) / 2))
    assert np.all((0 <= real_mean) & (real_mean <= .5))
    np.testing.assert_allclose(.5 - 2 * real_mean**2, variance, atol=1e-15)
    results['Q_collision'] = dict(atoms=[[3, 3], [4, -2]], physical_displacement=18,
        diagonal=float(variance.sum()), cross_abs=float(abs(cross)),
        uniform_cross_abs=float(abs(q01_uniform)), variance_is_legal_QPSK=True,
        pilot_does_not_enter_Q=True)

    symbols = np.array([.5+.5j, .5-.5j, -.5+.5j, -.5-.5j])
    independent = np.array(list(itertools.product(symbols, repeat=2)))
    correlated = np.column_stack([symbols, symbols])
    V0 = independent.T @ independent.conj() / len(independent)
    V1 = correlated.T @ correlated.conj() / len(correlated)
    np.testing.assert_allclose(np.diag(V0), np.diag(V1))
    assert abs(V0[0, 1]) == 0 and abs(V1[0, 1]) == .5
    results['LLR_nonidentifiability'] = dict(all_bit_LLRs=0,
        independent_cross_abs=float(abs(V0[0, 1])), correlated_cross_abs=float(abs(V1[0, 1])))

    n0 = 4
    ops = [operator(n0, 0, 0), operator(n0, 1, 0)]
    p0 = draw(n0)
    Ap = np.column_stack([u @ p0 for u in ops])
    average = np.zeros((2, 2), dtype=complex)
    count = 0
    for data0 in itertools.product(symbols, repeat=n0):
        A = np.column_stack([u @ (p0 + data0) for u in ops])
        average += A.conj().T @ A
        count += 1
    target = Ap.conj().T @ Ap + n0 * .5 * np.eye(2)
    np.testing.assert_allclose(average / count, target, rtol=1e-12, atol=1e-12)
    results['mean_Gram'] = dict(exhaustive_QPSK_states=count,
                               residual=float(np.linalg.norm(average / count - target)))
    r = -(1 - .001) / 23
    gram = (1 - r) * np.eye(24) + r * np.ones((24, 24))
    results['low_coherence_counterexample'] = dict(coherence=abs(r),
        lambda_min=float(np.linalg.eigvalsh(gram)[0]), gamma=float(np.trace(np.linalg.inv(gram)) / 24))
    assert results['low_coherence_counterexample']['gamma'] > 40
    observations = np.arange(3, dtype=float)
    nonlinear_estimates = observations**2 / (observations**2 + 1)
    np.testing.assert_allclose(nonlinear_estimates, [0, .5, .8])
    assert abs(np.diff(nonlinear_estimates, n=2)[0]) > .1
    results['fixed_support_not_affine'] = dict(
        y=observations.tolist(), estimates=nonlinear_estimates.tolist())
    results['status'] = 'PASS'
    results['source_sha256'] = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [ROOT/'afdm_sp_joint_unrolled/classical_joint_unrolled.py',
                  ROOT/'afdm_sp_joint_unrolled/supplement_feedback.py', Path(__file__)]}
    results['accounting'] = dict(shared_CE_unit_calls=2, fixed_stage_receiver_calls=0,
                                 synthetic_channel_samples=1, exhaustive_QPSK_states=256)
    results['wall_seconds'] = time.perf_counter() - started
    target = Path(__file__).with_name('ce-state-theory-checks-v1.json')
    target.write_text(json.dumps(results, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'status': results['status'], 'output': str(target),
                      'wall_seconds': results['wall_seconds']}))


if __name__ == '__main__':
    run()
