#!/usr/bin/env python
"""analytical_macs.py — closed-form MAC counts for §IV-F crosscheck.

Receiver pipeline (per Section 2.4-2.7 of the paper):

  1. OMP-once on dict Φ ∈ C^{N x Q}, picking P_oracle atoms, cost ~ P * N * Q per pick
  2. T_outer outer iterations (T_outer = 5):
       (a) DA-LS refit on locked support |S| (normal eqs O(|S|^2 * N))
       (b) sparse MP-BP detection on Dirichlet-virtual factor graph,
           T_mp inner iterations, edge degree d, cost ~ T_mp * N * d
  3. Learned head (invoked twice at t=0):
       pair-MLP applied per (cand, active) pair: ~ N * Q candidate-pool projection
       scorer-MLP: ~ N * (cand_topm) scoring evaluations

Conventions:
  - Q (dictionary size) is given by Q = (2*k_max + 1) * l_max + 1
  - |S_oracle| is the Dirichlet-expanded effective support size
    (~28 in the canonical UWA setup; closed-form = P * (2*k_leak + 1))
  - One MAC = 1 complex multiply + 1 complex add ≈ 4 real flops

This script does NOT measure anything; pair with measure_runtime.py for
the empirical crosscheck.

Usage:
    python analytical_macs.py --N-list 512 1024 2048 --out outputs_complexity
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import pathlib


def Q_dict(N: int, l_max: int, k_max: int) -> int:
    """Physical (l, k)-bin dictionary size."""
    return (2 * k_max + 1) * l_max + 1


def macs_omp_once(N: int, Q: int, P: int) -> int:
    """OMP-once: P passes, each pass projects residual onto Q columns of Φ.
    Cost per pick = N * Q (matched filter) + O(N * t) for orthogonalization
    on the t-th pick. Total ~ P * N * Q + sum_{t=1..P} N*t ≈ P*N*Q + P^2*N/2.
    """
    return P * N * Q + (P * (P + 1) // 2) * N


def macs_dals(N: int, S: int) -> int:
    """DA-LS refit on locked support |S|: normal equations Φ_S^H Φ_S + λI
    cost O(S^2 * N) form, plus O(S^3) solve. We report the dominant term.
    """
    return S * S * N + S * S * S


def macs_mp_bp(N: int, deg: int, T_mp: int) -> int:
    """Sparse MP-BP detection: T_mp iterations, each iteration sweeps N variable
    nodes with edge degree `deg`. Cost ~ T_mp * N * deg per iter (variable-node
    update) plus same for factor-node update. Conservative 2 * T_mp * N * deg.
    """
    return 2 * T_mp * N * deg


def macs_outer(N: int, S: int, deg: int, T_mp: int, T_outer: int) -> int:
    """T_outer * (DA-LS + MP-BP)."""
    return T_outer * (macs_dals(N, S) + macs_mp_bp(N, deg, T_mp))


def macs_learned_head(N: int, Q: int, M: int, P: int,
                      pair_in: int = 6, pair_hidden: int = 16,
                      scorer_in: int = 39, scorer_hidden: int = 16) -> int:
    """Learned head: pair-MLP applied over (cand, active) pairs (M candidates x P actives),
    pooling, then scorer-MLP applied per candidate. Sizes from §2.7 architecture (paper
    states 384 + 657 = 1041 trainable params).

    Pair-MLP per pair: pair_in -> pair_hidden -> pair_hidden ~ pair_in*pair_hidden + pair_hidden^2 MACs
    Scorer-MLP per candidate: scorer_in -> scorer_hidden -> 1 ~ scorer_in*scorer_hidden + scorer_hidden MACs

    Head invoked twice at t=0 -> factor 2.
    """
    pair_macs = (pair_in * pair_hidden + pair_hidden * pair_hidden) * (M * P)
    pool_macs = pair_hidden * (M * P)  # max+mean pool
    scorer_macs = (scorer_in * scorer_hidden + scorer_hidden) * M
    return 2 * (pair_macs + pool_macs + scorer_macs)


def total_macs(N: int, P: int, l_max: int, k_max: int, k_leak: int,
               T_outer: int, T_mp: int,
               with_head: bool, M: int) -> dict:
    Q = Q_dict(N, l_max, k_max)
    S_eff = P * (2 * k_leak + 1)
    deg = 2 * k_leak + 1  # MP-BP edge degree (Dirichlet-virtual neighborhood)

    omp = macs_omp_once(N, Q, P)
    outer = macs_outer(N, S_eff, deg, T_mp, T_outer)
    head = macs_learned_head(N, Q, M, P) if with_head else 0
    total = omp + outer + head

    return {
        'N': N, 'Q': Q, 'P': P, 'S_eff': S_eff, 'deg': deg,
        'T_outer': T_outer, 'T_mp': T_mp,
        'with_head': with_head, 'M': M,
        'omp_macs': omp,
        'outer_macs': outer,
        'head_macs': head,
        'total_macs': total,
        'gflops_4flops_per_mac': total * 4 / 1e9,
    }


def _scale_for_N(N: int, fs_factor: float) -> tuple[int, int]:
    """Best-effort l_max/k_max consistent with the simulator setup.

    For UWA-style 8-path, tau_spread = 10 ms, fs = fs_factor * B (B = 4 kHz):
      l_max ≈ ceil(tau_spread * fs)
      k_max derived from v_max via 3-sigma envelope; canonical: 4 at 2B, 2 at 4B.

    These match the Section 2.4 paper conventions; if the operating point
    changes, reconfigure here.
    """
    B = 4e3
    fs = fs_factor * B
    Ts = 1.0 / fs
    l_max = max(int(math.ceil(0.010 / Ts)), 1)  # tau_spread = 10 ms
    if abs(fs_factor - 4.0) < 1e-9:
        k_max = 2
    elif abs(fs_factor - 2.0) < 1e-9:
        k_max = 4
    else:
        # Approximate from v_max + 3*sigma_v at fc = 12 kHz, c = 1500 m/s
        v_max = 2.0 + 3.0 * 0.5
        d_norm = v_max * 12e3 / (1500.0 * fs)
        k_max = max(int(math.ceil(N * d_norm)), 1)
    return l_max, k_max


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N-list', nargs='+', type=int, default=[512, 1024, 2048])
    ap.add_argument('--p-paths', type=int, default=8)
    ap.add_argument('--k-leak', type=int, default=2)
    ap.add_argument('--t-outer', type=int, default=5)
    ap.add_argument('--t-mp', type=int, default=20)
    ap.add_argument('--cand-topm', type=int, default=96, help='M for the learned head')
    ap.add_argument('--fs-factor', type=float, default=2.0)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    out = pathlib.Path(args.out); out.mkdir(parents=True, exist_ok=True)

    rows = []
    for N in args.N_list:
        l_max, k_max = _scale_for_N(N, args.fs_factor)
        for label, with_head in [('classical', False), ('learned', True)]:
            r = total_macs(N=N, P=args.p_paths,
                           l_max=l_max, k_max=k_max, k_leak=args.k_leak,
                           T_outer=args.t_outer, T_mp=args.t_mp,
                           with_head=with_head, M=args.cand_topm)
            r['receiver'] = label
            r['l_max'] = l_max
            r['k_max'] = k_max
            rows.append(r)
            print(f'[{label:>10s} N={N:>4d}] Q={r["Q"]:>5d} S_eff={r["S_eff"]} '
                  f'OMP={r["omp_macs"]:.2e} OUTER={r["outer_macs"]:.2e} '
                  f'HEAD={r["head_macs"]:.2e} TOTAL={r["total_macs"]:.2e} '
                  f'(~{r["gflops_4flops_per_mac"]:.2f} GFLOPs)')

    csv_path = out / 'analytical_macs.csv'
    fields = ['receiver', 'N', 'Q', 'P', 'S_eff', 'deg', 'T_outer', 'T_mp',
              'with_head', 'M', 'l_max', 'k_max',
              'omp_macs', 'outer_macs', 'head_macs', 'total_macs',
              'gflops_4flops_per_mac']
    with open(csv_path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow(r)
    json_path = out / 'analytical_macs.json'
    with open(json_path, 'w') as f:
        json.dump({'config': vars(args), 'rows': rows}, f, indent=2)
    print(f'[done] wrote {csv_path} and {json_path}')


if __name__ == '__main__':
    main()
