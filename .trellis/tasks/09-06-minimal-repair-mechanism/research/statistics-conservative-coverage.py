"""Exploratory numerical fixture; not S5 preregistration or n selection.

Run with a NumPy/SciPy Python. CPU only; alarm limits runtime to 60 seconds.
Cell order: a=neither fails, b=new-only fails, c=reference-only fails,
d=both fail. Each binomial marginal CI is two-sided 97.5% (tails 1.25%).
Union bound gives >=95% simultaneous coverage regardless of paired dependence.
"""
from pathlib import Path
import json
import signal
import time
import numpy as np
import scipy
from scipy.stats import beta


def cp_interval(k, n, alpha):
    """Exact binomial inversion, two-sided confidence 1-alpha."""
    k = np.asarray(k)
    lo = np.zeros(k.shape, dtype=float)
    hi = np.ones(k.shape, dtype=float)
    pos, below = k > 0, k < n
    lo[pos] = beta.ppf(alpha / 2, k[pos], n - k[pos] + 1)
    hi[below] = beta.ppf(1 - alpha / 2, k[below] + 1, n - k[below])
    return lo, hi


def ratio_interval(new_errors, ref_errors, n):
    # Memoize identical counts via unique; no approximate quantiles.
    merged = np.concatenate([np.atleast_1d(new_errors), np.atleast_1d(ref_errors)])
    values, inverse = np.unique(merged, return_inverse=True)
    low, high = cp_interval(values, n, alpha=.025)
    ln, lr = np.split(low[inverse], 2)
    un, ur = np.split(high[inverse], 2)
    lower = ln / ur  # n finite and alpha>0 => ur always strictly positive.
    upper = np.full_like(lower, np.inf)
    np.divide(un, lr, out=upper, where=lr > 0)
    return lower, upper, ln, un, lr, ur


def main():
    signal.alarm(60)
    start = time.monotonic()
    trials = 20000
    cases = [
        ('rare_disjoint_R0.9_n32', 32, .0009, .001, 0.),
        ('rare_disjoint_R0.9_n192', 192, .009, .010, 0.),
        ('rare_disjoint_R1_n192', 192, .010, .010, 0.),
        ('rare_overlap_R0.9_n192', 192, .001, .002, .008),
        ('rare_overlap_R0.9_n1000', 1000, .001, .002, .008),
        ('rare_overlap_R0.9_n5000', 5000, .001, .002, .008),
        ('identical_rare_R1_n1000', 1000, 0., 0., .003),
        ('new_zero_R0_n192', 192, 0., .010, 0.),
        ('reference_zero_Rinf_n192', 192, .010, 0., 0.),
        ('both_zero_undefined_n192', 192, 0., 0., 0.),
        ('moderate_disjoint_R0.9_n1000', 1000, .090, .100, 0.),
        ('moderate_overlap_R1_n5000', 5000, .005, .005, .045),
    ]
    output = []
    for i, (name, n, b, c, d) in enumerate(cases):
        pn, pr = b+d, c+d
        probs = np.array([1-b-c-d, b, c, d])
        assert np.all(probs >= 0) and abs(probs.sum()-1) < 1e-14
        rng = np.random.default_rng(np.random.SeedSequence([20260906, 9, i]))
        counts = rng.multinomial(n, probs, size=trials)
        en, er = counts[:, 1]+counts[:, 3], counts[:, 2]+counts[:, 3]
        lo, hi, ln, un, lr, ur = ratio_interval(en, er, n)
        simultaneous = (ln <= pn) & (pn <= un) & (lr <= pr) & (pr <= ur)
        if pr > 0:
            ratio = pn / pr
            covered = (lo <= ratio) & (ratio <= hi)
            ratio_label = float(ratio)
        elif pn > 0:
            ratio_label = 'infinity'
            covered = np.isinf(hi)  # Extended ratio, explicit convention.
        else:
            ratio_label = 'undefined_0_over_0'
            covered = None
        if covered is not None:
            assert np.all(~simultaneous | covered)
            k = int(covered.sum())
            interval = cp_interval(np.array([k]), trials, .05)
            coverage = dict(count=k, proportion=k/trials,
                            mc_95pct_cp=[float(interval[0][0]), float(interval[1][0])])
        else:
            coverage = None
        false_gate = None
        if pr > 0 and pn/pr >= .9 - 1e-14:
            k = int((hi < .9).sum())
            ci = cp_interval(np.array([k]), trials, .05)
            false_gate = dict(count=k, proportion=k/trials,
                              mc_95pct_cp=[float(ci[0][0]), float(ci[1][0])])
        output.append(dict(name=name, n=n, trials=trials, probabilities_abcd=probs.tolist(),
                           p_new=pn, p_reference=pr, true_ratio=ratio_label,
                           ratio_coverage=coverage,
                           simultaneous_marginal_coverage=float(simultaneous.mean()),
                           upper_infinite_fraction=float(np.isinf(hi).mean()),
                           false_G1_style_upper_below_point9=false_gate))
    # Deterministic boundary contracts independent of MC frequency.
    l, u, *_ = ratio_interval(np.array([0, 0, 192, 192]), np.array([0, 192, 0, 192]), 192)
    assert l[0] == 0 and np.isinf(u[0])
    assert l[1] == 0 and 0 < u[1] < 1
    assert l[2] > 1 and np.isinf(u[2])
    assert l[3] < 1 < u[3]
    rare_three_errors = []
    for n in [32, 192, 1000]:
        lo, hi, *_ = ratio_interval(np.array([0]), np.array([3]), n)
        rare_three_errors.append(dict(n=n, counts_bcd=[0, 3, 0],
                                      ratio_interval=[float(lo[0]), float(hi[0])]))
    report = dict(scope='numerical fixture only; no S5 preregistration, power or n selection',
                  seed_sequence=[20260906, 9, 'case_index'], numpy=np.__version__, scipy=scipy.__version__,
                  per_marginal_confidence=.975, tail_probability=.0125,
                  guaranteed_simultaneous_confidence_at_least=.95,
                  rows=output, rare_three_errors=rare_three_errors,
                  elapsed_seconds=time.monotonic()-start)
    path = Path(__file__).with_suffix('.json')
    path.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(output=str(path), elapsed_seconds=report['elapsed_seconds'],
                         minimum_defined_mc_coverage=min(x['ratio_coverage']['proportion'] for x in output if x['ratio_coverage']))))


if __name__ == '__main__':
    main()
