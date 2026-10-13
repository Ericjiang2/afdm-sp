#!/usr/bin/env python
"""W8 Path A Phase 1 — train logistic early-exit gate.

Reads trajectory.json from early_exit_probe.py, builds (X, y) samples
per (frame, outer iter t >= min_iter), fits a tiny logistic regression
that predicts "should we continue more iters?" (i.e., err_per_iter[t] >
err_per_iter[-1]).

Features per outer iter t (all inference-time computable):
  - log(resnorm[t])                  ── log residual energy
  - (resnorm[t-1]-resnorm[t]) / resnorm[t-1]   ── relative decay this iter
  - t / max_iter                     ── iter index normalized
  - resnorm[t] / resnorm[0]          ── shrinkage vs first iter

Label: should-continue ∈ {0, 1}, 1 = err[t] > err[-1] (we're not yet at
final BER).

Trains a 4-weight + bias logistic regression via simple SGD (numpy only,
no sklearn dependency). Saves gate.json with weights, mu, sigma, plus
per-threshold predicted-stop-iter histograms over the training set.
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np


def sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def build_dataset(per_frame, max_iter, min_iter, slack=0):
    """Construct (X, y, snr, frame_idx, t) flat arrays from trajectory.

    v2 features (6-dim):
      - log_resnorm
      - rel_decay = (resnorm[t-1] - resnorm[t]) / resnorm[t-1]
      - iter_norm = t / max_iter
      - ratio_init = resnorm[t] / resnorm[0]
      - log_flip_rate = log(flip_rate[t] + eps)   ← v2 BER-direct proxy
      - log_x_delta = log(x_soft_delta[t] + eps)   ← v2 continuous-state proxy

    v2 label: should-continue = 1 if err[t] > err[-1] + slack
      slack=0 → strict (any improvement triggers continue)
      slack=5 → tolerant (≤5 extra bit errors OK)
    """
    use_v2 = 'flip_rate_per_iter' in (per_frame[0] if per_frame else {})
    feats = []; labels = []; meta = []
    for rec in per_frame:
        err = rec['err_per_iter']
        res = rec['resnorm_per_iter']
        flip = rec.get('flip_rate_per_iter', [0.0] * max_iter)
        xdelta = rec.get('x_soft_delta_per_iter', [0.0] * max_iter)
        snr = rec['snr']
        fi = rec['frame_idx']
        err_final = err[-1]
        for t in range(min_iter, max_iter):
            log_r = float(np.log(res[t] + 1e-30))
            denom = max(res[t-1], 1e-30)
            decay = float((res[t-1] - res[t]) / denom)
            iter_norm = t / max_iter
            ratio_init = float(res[t] / max(res[0], 1e-30))
            if use_v2:
                log_flip = float(np.log(flip[t] + 1e-6))
                log_xd = float(np.log(xdelta[t] + 1e-12))
                feats.append([log_r, decay, iter_norm, ratio_init,
                              log_flip, log_xd])
            else:
                feats.append([log_r, decay, iter_norm, ratio_init])
            labels.append(1 if err[t] > err_final + slack else 0)
            meta.append((snr, fi, t))
    return (np.asarray(feats, dtype=np.float64),
            np.asarray(labels, dtype=np.float64), meta)


def fit_logreg(X: np.ndarray, y: np.ndarray, lr=0.1, epochs=400,
               l2=1e-4, verbose=False):
    """Fit logistic regression by full-batch gradient descent."""
    n, d = X.shape
    w = np.zeros(d, dtype=np.float64)
    b = 0.0
    for ep in range(epochs):
        z = X @ w + b
        p = sigmoid(z)
        grad_w = X.T @ (p - y) / n + l2 * w
        grad_b = (p - y).mean()
        w -= lr * grad_w
        b -= lr * grad_b
        if verbose and ep % 50 == 0:
            loss = -(y * np.log(p + 1e-12) + (1 - y)
                     * np.log(1 - p + 1e-12)).mean()
            print(f'  epoch={ep:3d} loss={loss:.5f}')
    return w, b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--trajectory', required=True,
                    help='trajectory.json from early_exit_probe.py')
    ap.add_argument('--out', required=True)
    ap.add_argument('--min-iter', type=int, default=2,
                    help='Gate evaluated only when t >= min_iter (1-indexed).')
    ap.add_argument('--lr', type=float, default=0.1)
    ap.add_argument('--epochs', type=int, default=400)
    ap.add_argument('--l2', type=float, default=1e-4)
    ap.add_argument('--slack', type=int, default=0,
                    help='Slack on the "should-continue" label. label_t = 1 '
                         'iff err[t] > err[-1] + slack. slack=0 is strict; '
                         'slack=5 lets gate stop when within 5 bit-errors of '
                         'the iter=10 final BER.')
    args = ap.parse_args()

    data = json.loads(pathlib.Path(args.trajectory).read_text())
    max_iter = int(data['meta']['max_iter'])
    per_frame = data['per_frame']

    X, y, meta = build_dataset(per_frame, max_iter, args.min_iter,
                                 slack=int(args.slack))
    print(f'Dataset: n_samples={len(y)}  pos_rate={y.mean():.3f}  '
          f'n_frames={len(per_frame)}  feature_dim={X.shape[1]}')

    mu = X.mean(axis=0)
    sigma = X.std(axis=0) + 1e-12
    Xn = (X - mu) / sigma

    w, b = fit_logreg(Xn, y, lr=args.lr, epochs=args.epochs, l2=args.l2,
                       verbose=True)
    p = sigmoid(Xn @ w + b)
    acc = float(((p > 0.5).astype(int) == y).mean())
    # AUC via Mann-Whitney
    pos = p[y == 1]; neg = p[y == 0]
    if len(pos) > 0 and len(neg) > 0:
        # Sample 5000 pairs for AUC estimate (full O(N^2) too slow at large N)
        rng = np.random.default_rng(42)
        n_pair = min(5000, len(pos) * len(neg))
        ip = rng.integers(0, len(pos), n_pair)
        ineg = rng.integers(0, len(neg), n_pair)
        auc_est = float((pos[ip] > neg[ineg]).mean()
                        + 0.5 * (pos[ip] == neg[ineg]).mean())
    else:
        auc_est = float('nan')

    # Per-threshold predicted-stop histogram (per-frame, per-SNR)
    thresholds = [0.1, 0.2, 0.3, 0.5, 0.7, 0.9]
    by_snr_stop = {}
    snr_frame_max = {}
    for (snr, fi, t), pi in zip(meta, p):
        snr_frame_max.setdefault((snr, fi), -1)
    # For each frame, find first t where p < threshold → stop iter
    # Otherwise stop iter = max_iter
    per_threshold_stats = {}
    for tau in thresholds:
        stop_iter_per_frame = {}
        for (snr, fi, t), pi in zip(meta, p):
            key = (snr, fi)
            if key in stop_iter_per_frame:
                continue
            if pi < tau:
                stop_iter_per_frame[key] = t + 1   # 1-indexed
        # Frames where gate never fired: stop at max_iter
        # All seen frames
        all_keys = set(snr_frame_max.keys())
        for key in all_keys:
            if key not in stop_iter_per_frame:
                stop_iter_per_frame[key] = max_iter
        by_snr_stops = {}
        for (snr, fi), si in stop_iter_per_frame.items():
            by_snr_stops.setdefault(snr, []).append(si)
        per_threshold_stats[str(tau)] = {
            str(snr): dict(
                avg_stop_iter=float(np.mean(arr)),
                median_stop_iter=float(np.median(arr)),
                p90_stop_iter=float(np.percentile(arr, 90)),
                speedup=float(max_iter) / float(np.mean(arr)),
            ) for snr, arr in by_snr_stops.items()
        }

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    feat_names = (['log_resnorm', 'rel_decay', 'iter_norm', 'ratio_init',
                    'log_flip_rate', 'log_x_soft_delta']
                  if Xn.shape[1] == 6
                  else ['log_resnorm', 'rel_decay', 'iter_norm', 'ratio_init'])
    out = dict(
        feature_names=feat_names,
        weights=w.tolist(), bias=float(b),
        mu=mu.tolist(), sigma=sigma.tolist(),
        min_iter=int(args.min_iter), max_iter=int(max_iter),
        slack=int(args.slack),
        train_acc=acc, auc_estimate=auc_est,
        pos_rate_label=float(y.mean()),
        n_samples=int(len(y)),
        thresholds=thresholds,
        per_threshold_stats=per_threshold_stats,
        meta=data['meta'],
    )
    (out_dir / 'gate.json').write_text(json.dumps(out, indent=2))
    print(f'\ngate.json written -> {out_dir/"gate.json"}')
    print(f'train_acc={acc:.3f}  auc≈{auc_est:.3f}  pos_rate={y.mean():.3f}')
    print('\nPredicted stop-iter under various thresholds (per SNR):')
    for tau in thresholds:
        line = f'  tau={tau}: '
        for snr in sorted(per_threshold_stats[str(tau)].keys(),
                          key=int):
            d = per_threshold_stats[str(tau)][snr]
            line += f'SNR={snr} avg={d["avg_stop_iter"]:.2f} '
        print(line)


if __name__ == '__main__':
    main()
