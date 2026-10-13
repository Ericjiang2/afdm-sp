"""Deterministic complex-algebra and boundary examples; zero receiver calls."""
import hashlib
import json
from pathlib import Path
import platform

import numpy as np


def metrics(y, h, candidates):
    return np.sum(abs(y[:, None]-h@candidates.T)**2, axis=0)


def expansion(y, h, error, candidates):
    residual = y[:, None]-h@candidates.T
    perturbation = error@candidates.T
    return -2*np.real(np.sum(residual.conj()*perturbation, axis=0))+np.sum(abs(perturbation)**2, axis=0)


def main():
    rng = np.random.default_rng([20260914, 125851, 92])
    max_relative_error, stable, conservative = 0., 0, 0
    for n in (1, 2, 4, 16):
        for _ in range(64):
            h = rng.normal(size=(n, n))+1j*rng.normal(size=(n, n))
            e = .002*(rng.normal(size=(n, n))+1j*rng.normal(size=(n, n)))
            y = rng.normal(size=n)+1j*rng.normal(size=n)
            candidates = rng.normal(size=(8, n))+1j*rng.normal(size=(8, n))
            before, after = metrics(y, h, candidates), metrics(y, h+e, candidates)
            direct, expanded = after-before, expansion(y, h, e, candidates)
            error = float(np.max(abs(direct-expanded))/max(1., np.max(before), np.max(after)))
            max_relative_error = max(max_relative_error, error)
            assert error < 2e-14
            order = np.argsort(before, kind='stable')
            margin = before[order[1]]-before[order[0]]
            if np.max(abs(expanded)) < margin/2:
                assert np.argmin(before) == np.argmin(after)
                stable += 1
            elif np.argmin(before) == np.argmin(after):
                conservative += 1
    bpsk = np.array([[-1.], [1.]])
    zero = np.zeros((1, 1)); one = np.ones((1, 1))
    tie_before = metrics(np.array([1.]), zero, bpsk)
    tie_after = metrics(np.array([1.]), zero+1e-9, bpsk)
    assert tie_before[0] == tie_before[1] and np.argmin(tie_before) != np.argmin(tie_after)
    threshold_before = metrics(np.array([.25]), one, bpsk)
    threshold_after = metrics(np.array([.25]), 1j*one, bpsk)
    assert np.max(abs(threshold_after-threshold_before)) == (threshold_before[0]-threshold_before[1])/2
    assert threshold_after[0] == threshold_after[1] and np.argmin(threshold_before) != np.argmin(threshold_after)
    omitted = np.array([[0.], [1.]])
    missing_metrics = metrics(np.array([2.]), one, omitted)
    assert missing_metrics[0]-missing_metrics[1] == 3 and 2. not in omitted
    qpsk = np.array([[.5+.5j], [.5-.5j], [-.5+.5j], [-.5-.5j]])
    y = np.array([.05+.8j])
    original = int(np.argmin(metrics(y, one, qpsk)))
    same_norm = [int(np.argmin(metrics(y, one+e, qpsk))) for e in (.2, -.2j)]
    assert same_norm[0] == original and same_norm[1] != original
    subset = np.array([[-1.], [1.]])
    enlarged = np.array([[-1.], [1.], [1.j]])
    assert np.argmin(metrics(np.array([.1+.9j]), one, subset)) == 1
    assert np.argmin(metrics(np.array([.1+.9j]), one, enlarged)) == 2
    # Different supports still compare as complete operators in identical coordinates.
    sparse = np.diag([1.+.1j, 2.-.2j])
    changed = np.array([[1.+.1j, .04j], [.03, 2.-.2j]])
    cand = np.array([[1., -1.], [-1., 1.]])
    obs = np.array([.8+.2j, -1.5+.1j])
    np.testing.assert_allclose(metrics(obs, changed, cand)-metrics(obs, sparse, cand),
                               expansion(obs, sparse, changed-sparse, cand), atol=2e-15)
    pilot = np.array([.2+.3j, 1.-.4j])
    signals = cand+pilot
    np.testing.assert_allclose(metrics(obs, changed, signals)-metrics(obs, sparse, signals),
                               expansion(obs, sparse, changed-sparse, signals), atol=3e-15)
    channel_llr = float(metrics(np.array([.1]), one, bpsk)[0]-metrics(np.array([.1]), one, bpsk)[1])
    assert channel_llr > 0 and channel_llr-20 < 0
    assert np.clip(21., -20., 20.)-20. == 0. and np.clip(21.-20., -20., 20.) == 1.
    report = dict(status='PASS', random_complex_cases=256, certified_unchanged_cases=stable,
        unchanged_without_sufficient_certificate=conservative, max_scaled_identity_error=max_relative_error,
        boundaries=dict(tie=True, strict_threshold_tie=True, pilot_included=True,
                        candidate_omission=True, changed_candidate_set=True,
                        equal_nmse_different_decision=True, different_support=True, prior_and_saturation=True),
        receiver_calls=0, scope='exact algebra and scalar boundaries, not BP/LDPC performance',
        provenance=dict(script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                        python=platform.python_version(), numpy=np.__version__))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
