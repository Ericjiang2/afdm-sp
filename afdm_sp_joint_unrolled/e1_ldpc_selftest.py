#!/usr/bin/env python
"""Standalone selftest for e1_ldpc.py (numpy only, no torch).

Checks:
  1. Code structure: column weight d_v everywhere, row weight <= d_c,
     every encoded word satisfies H c = 0 (mod 2), k reported.
  2. Zero-noise roundtrip: encode -> QPSK map -> perfect LLR -> decode ->
     exact info recovery, 20 random codewords.
  3. AWGN QPSK at Eb/N0 = 2.5 and 3.5 dB, >= 200 codewords each:
     coded (post-decode info-bit) BER must be clearly below uncoded
     (pre-decode raw coded-bit) BER; hard assert coded < uncoded/3 at 3.5 dB.

Prints PASS/FAIL summary lines; exit code 0 iff all pass.

Run (remote): conda activate AFDM && python e1_ldpc_selftest.py
"""
from __future__ import annotations

import sys
import time

import numpy as np

try:
    from afdm_sp_joint_unrolled.e1_ldpc import (
        build_code, encode, extract_info, qpsk_map, demap_llr, decode_llr)
except ImportError:  # standalone (e.g. scp'd flat into /data/guoyikun/tmp/)
    from e1_ldpc import (
        build_code, encode, extract_info, qpsk_map, demap_llr, decode_llr)


def _awgn_run(code, ebn0_db, n_words, rng, maxiter=50):
    """One AWGN QPSK point. Returns (uncoded_ber, coded_ber, n_decode_fail).

    Unit-energy QPSK (Es=1), 2 coded bits/symbol, rate R = k/n:
        Es/N0 = 2 * R * Eb/N0   =>   N0 = 1 / (2 * R * ebn0_lin)
    y = x + w, w ~ CN(0, N0). Channel LLR via demap_llr(y, N0, 1/sqrt(2))
    (per-component amplitude a = 1/sqrt(2), per-component variance N0/2:
    llr = 2*a*y_comp/(N0/2) = 4*a*y_comp/N0 — same Gaussian formula).
    """
    n, k = code['n'], code['k']
    R = k / n
    ebn0_lin = 10.0 ** (ebn0_db / 10.0)
    N0 = 1.0 / (2.0 * R * ebn0_lin)
    raw_err = 0
    info_err = 0
    n_fail = 0
    for _ in range(n_words):
        info = rng.integers(0, 2, size=k).astype(np.uint8)
        c = encode(code, info)
        x = qpsk_map(c, scale=1.0)
        nsym = x.size
        w = (rng.standard_normal(nsym) + 1j * rng.standard_normal(nsym)) \
            * np.sqrt(N0 / 2.0)
        y = x + w
        llr = demap_llr(y, N0, 1.0 / np.sqrt(2.0))
        raw_err += int(((llr < 0).astype(np.uint8) != c).sum())
        c_hat, ok = decode_llr(code, llr, maxiter=maxiter)
        if not ok:
            n_fail += 1
        info_err += int((extract_info(code, c_hat) != info).sum())
    return raw_err / (n_words * n), info_err / (n_words * k), n_fail


def main():
    t0 = time.time()
    passed = True

    code = build_code(n=2048, d_v=3, d_c=6, seed=20260726)
    H = code['H']
    n, k = code['n'], code['k']
    print(f'[code] n={n} k={k} rate={k/n:.4f} m={H.shape[0]} '
          f'rank={n - k} cache={code["cache_path"]}')

    # ---- 1. structure -------------------------------------------------
    col_w = H.sum(axis=0)
    row_w = H.sum(axis=1)
    ok_struct = (col_w == code['d_v']).all() and (row_w <= code['d_c']).all() \
        and (row_w >= 2).all()
    print(f"[{'PASS' if ok_struct else 'FAIL'}] structure: col weight "
          f"unique={sorted(set(col_w.tolist()))} row weight "
          f"unique={sorted(set(row_w.tolist()))}")
    passed &= ok_struct

    rng = np.random.default_rng(1)
    ok_enc = True
    for _ in range(5):
        c = encode(code, rng.integers(0, 2, size=k))
        ok_enc &= not ((H.astype(np.int32) @ c.astype(np.int32)) % 2).any()
    print(f"[{'PASS' if ok_enc else 'FAIL'}] encoder: H@c=0 (mod 2) "
          f"for 5 random info words")
    passed &= ok_enc

    # ---- 2. zero-noise roundtrip -------------------------------------
    ok_rt = True
    for _ in range(20):
        info = rng.integers(0, 2, size=k).astype(np.uint8)
        c = encode(code, info)
        x = qpsk_map(c, scale=1.0)
        # perfect LLR: noiseless observation, vanishing variance
        llr = demap_llr(x, 1e-9, 1.0 / np.sqrt(2.0))
        c_hat, ok = decode_llr(code, llr, maxiter=50)
        ok_rt &= ok and (c_hat == c).all() \
            and (extract_info(code, c_hat) == info).all()
    print(f"[{'PASS' if ok_rt else 'FAIL'}] zero-noise roundtrip: "
          f"20/20 exact info recovery")
    passed &= ok_rt

    # ---- 3. AWGN coding gain -----------------------------------------
    n_words = 200
    results = {}
    for ebn0 in (2.5, 3.5):
        raw, coded, n_fail = _awgn_run(code, ebn0, n_words, rng)
        results[ebn0] = (raw, coded, n_fail)
        print(f'[awgn] Eb/N0={ebn0} dB  words={n_words}  '
              f'uncoded BER={raw:.4e}  coded BER={coded:.4e}  '
              f'decode failures={n_fail}/{n_words}')
    ok_gain = results[3.5][1] < results[3.5][0] / 3.0
    print(f"[{'PASS' if ok_gain else 'FAIL'}] coding gain at 3.5 dB: "
          f"coded {results[3.5][1]:.4e} < uncoded/3 "
          f"= {results[3.5][0] / 3.0:.4e}")
    passed &= ok_gain
    ok_gain25 = results[2.5][1] < results[2.5][0]
    print(f"[{'PASS' if ok_gain25 else 'FAIL'}] coding gain at 2.5 dB: "
          f"coded {results[2.5][1]:.4e} < uncoded {results[2.5][0]:.4e}")
    passed &= ok_gain25

    print(f"[{'PASS' if passed else 'FAIL'}] e1_ldpc selftest "
          f"({time.time() - t0:.1f}s)")
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
