"""Loop-12 frame-level paired bootstrap CI.

Reads a paired_learned_eval `results.json` that contains
`paired_diff_per_frame` (added by Loop-12 patch — list of per-frame
`classical_err_bits - learned_err_bits`; positive = learned better).

Emits a table: per-SNR mean(diff), 95 % percentile bootstrap CI,
sign-test p (H_A: learned better), n frames.

Usage:
    python -m afdm_sp_joint_unrolled._loop12_frame_bootstrap \
        --results <path>/results.json --n-boot 10000 --seed 42
"""
import argparse
import json
import pathlib

import numpy as np


def bootstrap_ci(diffs: np.ndarray, n_boot: int, rng: np.random.Generator,
                 alpha: float = 0.05):
    n = len(diffs)
    if n == 0:
        return float('nan'), float('nan'), float('nan')
    idx = rng.integers(0, n, size=(n_boot, n))
    boot_means = diffs[idx].mean(axis=1)
    lo = float(np.quantile(boot_means, alpha / 2))
    hi = float(np.quantile(boot_means, 1 - alpha / 2))
    mean = float(diffs.mean())
    return mean, lo, hi


def sign_test_p(diffs: np.ndarray) -> float:
    """One-sided sign test, H_A: P(diff > 0) > 0.5 (learned better per-frame)."""
    pos = int((diffs > 0).sum())
    neg = int((diffs < 0).sum())
    n = pos + neg
    if n == 0:
        return 1.0
    if n < 200:
        from scipy.stats import binomtest
        r = binomtest(pos, n, p=0.5, alternative='greater')
        return float(r.pvalue)
    from math import erf, sqrt
    z = (pos - 0.5 - n * 0.5) / sqrt(n * 0.25)
    return 0.5 * (1 - erf(z / sqrt(2)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', required=True, type=pathlib.Path)
    ap.add_argument('--n-boot', type=int, default=10000)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--out', type=pathlib.Path, default=None)
    args = ap.parse_args()

    data = json.loads(args.results.read_text())
    rng = np.random.default_rng(args.seed)
    rows = [
        '# Loop-12 frame-level paired bootstrap CI',
        '',
        f'Source: `{args.results}`  n_boot = {args.n_boot}  seed = {args.seed}',
        '',
        '| SNR | n_frames | mean Δ (bits) | 95 % CI low | 95 % CI hi | sign-test p | verdict |',
        '|---:|---:|---:|---:|---:|---:|:---|',
    ]
    for snr_str, payload in sorted(
        ((k, v) for k, v in data.items() if k != '_config'),
        key=lambda kv: int(kv[0]),
    ):
        vec = payload.get('paired_diff_per_frame')
        if vec is None:
            rows.append(f'| {snr_str} | — | — | — | — | — | no per-frame data |')
            continue
        diffs = np.asarray(vec, dtype=float)
        mean, lo, hi = bootstrap_ci(diffs, args.n_boot, rng)
        p = sign_test_p(diffs)
        verdict = 'learned better (CI > 0)' if lo > 0 else (
            'learned worse (CI < 0)' if hi < 0 else 'CI straddles 0'
        )
        rows.append(
            f'| {snr_str} | {len(diffs)} | {mean:.3f} | {lo:.3f} | {hi:.3f} | '
            f'{p:.2e} | {verdict} |'
        )
    text = '\n'.join(rows) + '\n'
    print(text)
    if args.out:
        args.out.write_text(text)
        print(f'wrote {args.out}')


if __name__ == '__main__':
    main()
