"""Unit tests for stageA5.py: fast covariance exactness, NLL exactness, metric, and verdict boundaries."""
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stageA5 as a5  # noqa: E402


def test_fast_covariance_and_nll_exactness():
    rng = np.random.default_rng(123)
    n, p, c1 = 64, 5, 0.004395
    delays = np.array([0, 3, 11, 25, 41], dtype=int)
    nu = np.array([-1.3, -0.2, 0.45, 1.1, 2.05], dtype=float)
    g = (rng.standard_normal(p) + 1j * rng.standard_normal(p)) * 0.4
    p_t = rng.standard_normal(n) + 1j * rng.standard_normal(n)
    r = rng.standard_normal(n) + 1j * rng.standard_normal(n)
    vd, sigma2 = 0.85, 0.4

    geom = a5.precompute_delay_geometry(delays, n, c1)
    c_mat = a5.doppler_vectors(geom, nu)

    # Dense reference T
    k = np.arange(n)
    T = np.zeros((n, n), dtype=np.complex128)
    for i in range(p):
        T[k, (k - delays[i]) % n] += g[i] * c_mat[i]
    C_ref = vd * (T @ T.conj().T) + sigma2 * np.eye(n, dtype=np.complex128)
    C_fast = a5.build_covariance_fast(geom, c_mat, g, vd, sigma2)
    assert np.linalg.norm(C_fast - C_ref) / np.linalg.norm(C_ref) < 1e-14

    # Check sb_nll_and_grad against direct slogdet + solve and central finite differences across all 3P coordinates
    theta = np.concatenate([nu, g.real, g.imag])
    shifted_pt = p_t[geom['cols']]
    nll_fast, grad_ana = a5.sb_nll_and_grad(theta, geom, shifted_pt, r, vd, sigma2)
    e_ref = r - T @ p_t
    _, ld = np.linalg.slogdet(C_ref)
    nll_ref = float(ld + np.vdot(e_ref, np.linalg.solve(C_ref, e_ref)).real)
    assert abs(nll_fast - nll_ref) / abs(nll_ref) < 1e-13, (nll_fast, nll_ref)

    eps = 1e-6
    grad_fd = np.empty_like(grad_ana)
    for idx in range(len(theta)):
        tp = theta.copy()
        tm = theta.copy()
        tp[idx] += eps
        tm[idx] -= eps
        fp, _ = a5.sb_nll_and_grad(tp, geom, shifted_pt, r, vd, sigma2)
        fm, _ = a5.sb_nll_and_grad(tm, geom, shifted_pt, r, vd, sigma2)
        grad_fd[idx] = (fp - fm) / (2.0 * eps)
    rel_err = float(np.linalg.norm(grad_ana - grad_fd) / np.linalg.norm(grad_fd))
    assert rel_err < 1e-6, (rel_err, grad_ana, grad_fd)


def test_verdict_and_metric():
    assert a5.verdict_a5(0.04, 0.08) == 'PASS'
    assert a5.verdict_a5(0.04, 0.079) == 'PASS'
    assert a5.verdict_a5(0.0801, 0.12) == 'FAIL'
    assert a5.verdict_a5(0.08, 0.12) == 'BORDERLINE'
    assert a5.verdict_a5(0.06, 0.09) == 'BORDERLINE'

    # Cap at 0.375 and outlier > 0.25
    m, o, _ = a5.doppler_metric(np.array([0.0, 1.0]), np.array([0.05, 0.0]), np.array([1.0, 1.0]))
    assert abs(m - 0.5 * (0.05 + 0.375)) < 1e-12
    assert abs(o - 0.5) < 1e-12


def test_frame_cluster_bootstrap():
    # Verify analyze_stageA5 resamples physical frames jointly (binding U and G)
    rows = []
    a4_rows = []
    for f in range(41000, 41020):
        # Construct anti-correlated U/G within each frame: frame mean is identically 0.060 -> CI must collapse to [0.06, 0.06]
        for s, val in (('U', 0.02), ('G', 0.10)):
            for rho in (100, 150, 200):
                rows.append(dict(
                    frame=f, scenario=s, rho=rho, snr=400,
                    metric=dict(PW=0.09, SB=val, KD=0.02),
                    outlier_frac=dict(PW=0.1, SB=0.0, KD=0.0),
                ))
                a4_rows.append(dict(
                    frame=f, scenario=s, rho=rho, snr=400,
                    metric=dict(pilot_white=0.08, pilot=0.07, semiblind=0.04, known=0.015),
                ))
    res = a5.analyze_stageA5(
        rows, a4_rows, (400,), {'100': 0.157, '150': 0.108, '200': 0.082},
        boot_draws=200, boot_seed=20261125,
    )
    assert res['boot_unit'] == 'physical_frame_cluster'
    assert res['frames'] == 20 and res['draws'] == 40
    assert abs(res['primary']['E_point'] - 0.06) < 1e-12
    assert abs(res['primary']['E_ci95'][0] - 0.06) < 1e-12
    assert abs(res['primary']['E_ci95'][1] - 0.06) < 1e-12
    assert res['primary']['verdict'] == 'PASS'


if __name__ == '__main__':
    test_fast_covariance_and_nll_exactness()
    test_verdict_and_metric()
    test_frame_cluster_bootstrap()
    print('ALL_STAGEA5_UNIT_TESTS_PASS')
