"""Fixed-subspace prediction-risk check; not an adaptive receiver/FER theorem."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np


def fixed_subspace_audit(repetitions=20000):
    if type(repetitions) is not int or repetitions < 20000:
        raise ValueError('at least 20000 independent numerical replicates required')
    rng = np.random.default_rng(20260909090115)
    n, k, rank = 32, 8, 3
    raw = rng.standard_normal((n, k)) + 1j*rng.standard_normal((n, k))
    basis, _ = np.linalg.qr(raw)
    physical = basis[:, :rank]
    beta = np.array([1+.5j, -.8+.3j, .25-.2j])
    mean = physical @ beta
    cases = []
    for distribution in ('complex_normal', 'independent_qpsk'):
        if distribution == 'complex_normal':
            noise = (rng.standard_normal((repetitions, n)) +
                     1j*rng.standard_normal((repetitions, n)))/np.sqrt(2)
        else:
            noise = ((2*rng.integers(0, 2, (repetitions, n))-1) +
                     1j*(2*rng.integers(0, 2, (repetitions, n))-1))/np.sqrt(2)
        observations = mean + noise
        estimates = {'atom': (observations @ basis.conj()) @ basis.T,
                     'physical': (observations @ physical.conj()) @ physical.T}
        for model, estimate in estimates.items():
            expected = k if model == 'atom' else rank
            risk = np.sum(abs(estimate-mean)**2, axis=1)
            observed = float(risk.mean())
            sem = float(risk.std(ddof=1)/np.sqrt(repetitions))
            if abs(observed-expected) > .05*expected:
                raise AssertionError('fixed-correct-subspace risk differs from rank by >5%')
            cases.append({'noise': distribution, 'model': model, 'rank': expected,
                          'mean_prediction_error': observed, 'standard_error': sem,
                          'absolute_tolerance': .05*expected})
    # Identical physical columns are not two identifiable gain coordinates.
    overlapping = np.column_stack((physical[:, 0], physical[:, 0]))
    s = np.linalg.svd(overlapping, compute_uv=False)
    overlap_rank = int(np.count_nonzero(s > np.finfo(float).eps*n*s[0]))
    if overlap_rank != 1:
        raise AssertionError('identical path columns must have rank one')
    return {'status': 'passed', 'evidence_kind': 'controlled_fixed_subspace_simulation',
            'seed': 20260909090115, 'repetitions_per_noise': repetitions,
            'N': n, 'K': k, 'r': rank, 'cases': cases,
            'identical_columns': {'count': 2, 'rank': overlap_rank, 'singular_values': s.tolist()},
            'derivation': 'For fixed orthogonal projector P, correct mean in range(P), E||P(y)-mean||^2=tr(P Cov(w) P^H)=tr(P)=rank(P) when E[w]=0 and Cov(w)=I. No Gaussian assumption needed.',
            'limitations': ['Fixed nested subspaces and correct mean only; OMP/data-selected subspaces excluded.',
                           'Estimated geometry adds bias and selection dependence; no FER or full-receiver implication.',
                           'Five-percent numerical tolerance is frozen before execution, not a significance test.']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    result = fixed_subspace_audit()
    result.update(wall_seconds=time.monotonic()-started,
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  numpy=np.__version__)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write('\n')
    print(json.dumps({'status': result['status'], 'out': str(args.out)}))


if __name__ == '__main__':
    main()
