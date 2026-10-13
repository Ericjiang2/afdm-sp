#!/usr/bin/env python
"""E1 LDPC module — pure numpy, zero external dependencies (no torch, no pyldpc).

Self-contained rate-1/2 Gallager-regular LDPC code for the E1 coded-BER
experiment (.trellis/tasks/07-26-e1-ldpc-coded-ber). pyldpc failed to build
on the remote AFDM env (2026-07-26), hence this module.

Code: Gallager (d_v=3, d_c=6) regular construction, n=2048, built by block
column-permutation with a fixed seed; systematic encoder derived by GF(2)
Gaussian elimination (RREF). NOTE: n=2048 is not divisible by d_c=6, so the
base block has ceil(n/d_c)=342 rows — 341 rows of weight 6 plus one edge row
of weight n%6=2. Column weight is exactly d_v=3 everywhere. This is the
standard Gallager construction adapted to n not divisible by d_c; the code
is "regular up to 3 edge rows" (one per block). k = n - rank(H) (design.md
accepts k != 1024; the frame always carries exactly n coded bits).

The built code (H + generator + info-column bookkeeping) is cached to an
.npz next to this module so all runs / arms share one code.

Decoder: flooding sum-product BP in the log domain (tanh rule, implemented
via the self-inverse phi(x) = -log(tanh(x/2)) with sign/magnitude
decomposition), vectorised over the edge list with np.add.reduceat /
np.bincount; syndrome early stop.

LLR convention throughout: llr = log P(bit=0)/P(bit=1)  (llr < 0 -> bit 1).
"""
from __future__ import annotations

import os
import pathlib

import numpy as np

LLR_CLIP = 20.0
_PHI_MAG_MIN = 1e-12   # phi() stable range: phi(1e-12) ~ 28.0
_PHI_MAG_MAX = 30.0


# ----------------------------------------------------------------------
# Construction
# ----------------------------------------------------------------------

def _gallager_H(n: int, d_v: int, d_c: int, rng: np.random.Generator) -> np.ndarray:
    """Gallager block column-permutation parity-check matrix.

    Base block: ceil(n/d_c) rows; row i covers columns [i*d_c, (i+1)*d_c).
    The last row is short (weight n % d_c) when d_c does not divide n.
    Blocks 2..d_v are independent random column permutations of the base
    block. Every column has weight exactly d_v.
    """
    rows0 = (n + d_c - 1) // d_c
    base = np.zeros((rows0, n), dtype=np.uint8)
    for i in range(rows0):
        base[i, i * d_c: min((i + 1) * d_c, n)] = 1
    blocks = [base]
    for _ in range(d_v - 1):
        perm = rng.permutation(n)
        blocks.append(base[:, perm])
    return np.vstack(blocks)


def _gf2_rref(H_in: np.ndarray):
    """GF(2) reduced row-echelon form.

    Returns (H_rre[:rank], pivot_cols, free_cols, rank). Codewords c satisfy
    H_rre @ c = 0 (mod 2) with, per pivot row i, exactly one 1 in
    pivot_cols[i] plus 1s in free columns only — which gives the systematic
    encoder: c[free] = info, c[pivot_cols[i]] = sum_j H_rre[i, free_j]*info_j.
    """
    H = (np.asarray(H_in, dtype=np.uint8) & 1).copy()
    m, n = H.shape
    pivot_cols = []
    r = 0
    for c in range(n):
        if r >= m:
            break
        nz = np.nonzero(H[r:, c])[0]
        if nz.size == 0:
            continue
        p = r + int(nz[0])
        if p != r:
            H[[r, p]] = H[[p, r]]
        others = np.nonzero(H[:, c])[0]
        others = others[others != r]
        H[others] ^= H[r]
        pivot_cols.append(c)
        r += 1
    rank = r
    pivot_cols = np.asarray(pivot_cols, dtype=np.int64)
    free_cols = np.setdiff1d(np.arange(n, dtype=np.int64), pivot_cols)
    return H[:rank], pivot_cols, free_cols, rank


def _edge_structs(H: np.ndarray):
    """Edge list sorted by check row (np.nonzero on 2D is C-ordered)."""
    chk, var = np.nonzero(H)
    row_counts = np.bincount(chk, minlength=H.shape[0])
    if (row_counts < 2).any():
        raise ValueError('parity-check matrix has a row of weight < 2')
    row_ptr = np.concatenate([[0], np.cumsum(row_counts)]).astype(np.int64)
    return chk.astype(np.int64), var.astype(np.int64), row_ptr


def build_code(n: int = 2048, d_v: int = 3, d_c: int = 6,
               seed: int = 20260726, cache_dir=None) -> dict:
    """Build (or load from cache) the E1 LDPC code.

    Returns a dict with:
      H          (m, n) uint8 parity-check matrix
      G          (n, k) uint8 systematic generator: c = (G @ info) % 2
      n, k       code dimensions (k = n - rank(H))
      free_cols  (k,) int — info-bit positions inside the codeword
                 (info = coded[free_cols] inverts the encoder)
      pivot_cols (rank,) int — parity positions
      chk, var, row_ptr — BP edge structures (check-sorted edge list)
      d_v, d_c, seed — construction parameters
    """
    cache_dir = pathlib.Path(cache_dir) if cache_dir is not None \
        else pathlib.Path(__file__).resolve().parent
    cache = cache_dir / f'e1_ldpc_code_n{n}_dv{d_v}_dc{d_c}_seed{seed}.npz'

    if cache.exists():
        z = np.load(cache)
        H = z['H'].astype(np.uint8)
        G = z['G'].astype(np.uint8)
        pivot_cols = z['pivot_cols'].astype(np.int64)
        free_cols = z['free_cols'].astype(np.int64)
    else:
        rng = np.random.default_rng(seed)
        H = _gallager_H(n, d_v, d_c, rng)
        H_rre, pivot_cols, free_cols, rank = _gf2_rref(H)
        k = n - rank
        # Systematic generator G (n x k): c = G @ info (mod 2).
        G = np.zeros((n, k), dtype=np.uint8)
        G[free_cols, np.arange(k)] = 1
        G[pivot_cols, :] = H_rre[:, free_cols]
        # Sanity: random info word must be a codeword of H.
        info_t = np.random.default_rng(seed + 1).integers(0, 2, size=k)
        c_t = (G.astype(np.int32) @ info_t.astype(np.int32)) % 2
        assert not ((H.astype(np.int32) @ c_t) % 2).any(), \
            'encoder/parity-check inconsistency'
        # Atomic write (tmp + rename): the geom / achievable runs may be
        # launched concurrently; both build identical content (deterministic
        # from seed) but a torn concurrent write must never leave a corrupt
        # cache for a later loader. Tmp name keeps the .npz suffix so numpy
        # does not append another one.
        tmp = cache.with_name(f'{cache.stem}.tmp{os.getpid()}.npz')
        np.savez_compressed(tmp, H=H, G=G,
                            pivot_cols=pivot_cols, free_cols=free_cols)
        os.replace(tmp, cache)

    chk, var, row_ptr = _edge_structs(H)
    return dict(H=H, G=G, n=int(H.shape[1]), k=int(G.shape[1]),
                pivot_cols=pivot_cols, free_cols=free_cols,
                chk=chk, var=var, row_ptr=row_ptr,
                d_v=int(d_v), d_c=int(d_c), seed=int(seed),
                cache_path=str(cache))


# ----------------------------------------------------------------------
# Encode / map / demap
# ----------------------------------------------------------------------

def encode(code: dict, info_bits: np.ndarray) -> np.ndarray:
    """Systematic encode: (n,) uint8 codeword; info sits at code['free_cols']."""
    info = np.asarray(info_bits).astype(np.int32) & 1
    if info.shape != (code['k'],):
        raise ValueError(f"info_bits must have shape ({code['k']},), "
                         f"got {info.shape}")
    return ((code['G'].astype(np.int32) @ info) % 2).astype(np.uint8)


def extract_info(code: dict, coded_bits: np.ndarray) -> np.ndarray:
    """Invert the systematic encoder: info = coded[free_cols]."""
    return np.asarray(coded_bits, dtype=np.uint8)[code['free_cols']]


def qpsk_map(bits: np.ndarray, scale: float = 1.0) -> np.ndarray:
    """Map 2*N bits (ordered [all I bits, then all Q bits]) to N Gray-QPSK
    symbols of the codebase alphabet {(+-1 +- 1j)/sqrt(2)} * scale.

    Matches the codebase bit convention (run_classical_baselines_python.py
    :101-106 `_bits_of_symbol`): bit=1  <->  component < 0. Hence
    component = (1 - 2*bit)/sqrt(2).
    """
    b = np.asarray(bits).astype(np.int64) & 1
    if b.size % 2:
        raise ValueError('bits length must be even')
    nsym = b.size // 2
    sym = ((1 - 2 * b[:nsym]) + 1j * (1 - 2 * b[nsym:])) / np.sqrt(2.0)
    return scale * sym.astype(complex)


def demap_llr(mu_post: np.ndarray, var_post, amp: float,
              clip: float = LLR_CLIP) -> np.ndarray:
    """Per-bit LLRs (llr = log P(b=0)/P(b=1)) from BP soft posteriors.

    Constellation / scaling conventions (verified against the codebase):
      * QPSK alphabet (run_classical_baselines_python.py:98):
            QPSK = [1+1j, 1-1j, -1+1j, -1-1j] / sqrt(2)   (unit symbol energy)
      * Frame assembly (paired_learned_eval.py:513-517 and 613-617):
            const_data = sqrt(P_d) * QPSK,   P_d = 1 - rho
            x_sp = sqrt(rho)*zc_seq + sqrt(P_d) * data_qam
        so each data symbol has per-component (I/Q) amplitude
            amp = sqrt(P_d) / sqrt(2) = sqrt(P_d / 2)
        in the detector's constellation space.
      * Bit convention (_bits_of_symbol, run_classical_baselines_python.py
        :101-106): bit_I[m] = 1 iff Re(s_m) < 0; bit_Q[m] = 1 iff
        Im(s_m) < 0; bits ordered [all I bits, then all Q bits].
      * BP posteriors (afdm_baselines.py:324-438 mp_detect_bp with
        return_soft=True): mu_post is the complex posterior mean IN
        CONSTELLATION SPACE (const_data scale), var_post the scalar complex
        posterior variance E|x - mu|^2 (covers both real dims).

    Derivation (Gaussian approximation): model symbol s ~ CN(mu, v) with
    v = var_post, i.e. per real dimension variance v/2. The I component
    takes values +-amp with equal prior, so
        LLR_I = log P(b_I=0|mu)/P(b_I=1|mu)
              = [ (Re mu + amp)^2 - (Re mu - amp)^2 ] / (2 * v/2)
              = 4 * amp * Re(mu) / v
    and analogously LLR_Q = 4 * amp * Im(mu) / v. LLR > 0 favours bit 0
    (positive component), consistent with bit=1 <-> component < 0.
    Clipped to +-clip (default +-20).
    """
    mu = np.asarray(mu_post, dtype=complex)
    v = np.maximum(np.broadcast_to(
        np.asarray(var_post, dtype=float), mu.shape).astype(float), 1e-30)
    llr_i = 4.0 * amp * mu.real / v
    llr_q = 4.0 * amp * mu.imag / v
    return np.clip(np.concatenate([llr_i, llr_q]), -clip, clip)


# ----------------------------------------------------------------------
# Decoder — flooding sum-product BP (log domain, tanh rule)
# ----------------------------------------------------------------------

def _phi(x: np.ndarray) -> np.ndarray:
    """phi(x) = -log(tanh(x/2)), self-inverse on (0, inf)."""
    return -np.log(np.tanh(np.clip(x, _PHI_MAG_MIN, _PHI_MAG_MAX) / 2.0))


def decode_llr(code, llr: np.ndarray, maxiter: int = 50):
    """Historical hard-return API; unchanged arithmetic and syndrome early stop."""
    return _decode_llr_core(code,llr,maxiter)


def decode_soft_messages(code, llr: np.ndarray, maxiter: int = 50):
    """Capture raw APP/check-sum at the same early-stop point as decode_llr."""
    H=np.asarray(code['H'] if isinstance(code,dict) else code)
    value=np.asarray(llr)
    if (H.ndim!=2 or not H.size or not np.isin(H,(0,1)).all() or
            np.any(H.sum(axis=1)<2) or np.iscomplexobj(value) or
            not np.isfinite(value).all() or type(maxiter) is not int or not 1<=maxiter<=200):
        raise ValueError('finite real LLR, binary check degree>=2 and iterations1..200 required')
    if isinstance(code,dict):
        expected=_edge_structs(H)
        if any(not np.array_equal(code[k],v) for k,v in zip(('chk','var','row_ptr'),expected)):
            raise ValueError('decoder edge structure differs from H')
    result=_decode_llr_core(code,value,maxiter,capture=True)
    if any(not np.isfinite(result[k]).all() for k in ('raw_app','raw_check_extrinsic')):
        raise FloatingPointError('nonfinite decoder messages')
    return result


def _decode_llr_core(code, llr: np.ndarray, maxiter: int = 50, *, capture=False):
    """Sum-product BP decode. Returns (coded_hat (n,) uint8, ok bool).

    `code` is the dict from build_code() (preferred; reuses precomputed edge
    structures) or a raw (m, n) parity-check ndarray. `ok` is True iff the
    syndrome is zero (valid codeword) at exit. Info bits are recovered from
    coded_hat via extract_info().
    """
    if isinstance(code, dict):
        chk, var, row_ptr = code['chk'], code['var'], code['row_ptr']
        m, n = code['H'].shape
    else:
        H = np.asarray(code)
        chk, var, row_ptr = _edge_structs(H)
        m, n = H.shape
    llr = np.asarray(llr, dtype=float)
    if llr.shape != (n,):
        raise ValueError(f'llr must have shape ({n},), got {llr.shape}')
    row_deg = np.diff(row_ptr)

    trace=[]
    def finish(hard,ok):
        if not capture:return hard,ok
        check_sum=np.bincount(var,weights=msg_c2v,minlength=n)
        return dict(decoded=hard,decode_ok=ok,incoming_llr=llr.copy(),
            raw_app=llr+check_sum,raw_check_extrinsic=check_sum,
            iterations=len(trace),syndrome_trace=trace)

    msg_c2v = np.zeros(chk.size, dtype=float)
    hard = (llr < 0).astype(np.uint8)
    for _ in range(maxiter):
        # variable -> check (extrinsic)
        tot = llr + np.bincount(var, weights=msg_c2v, minlength=n)
        msg_v2c = tot[var] - msg_c2v
        # check -> variable: tanh rule via phi with sign/magnitude split
        neg = (msg_v2c < 0).astype(np.int64)
        mag = np.abs(msg_v2c)
        ph = _phi(mag)
        ph_sum = np.add.reduceat(ph, row_ptr[:-1])
        neg_sum = np.add.reduceat(neg, row_ptr[:-1])
        ph_ext = np.repeat(ph_sum, row_deg) - ph
        neg_ext = np.repeat(neg_sum, row_deg) - neg
        sgn_ext = 1.0 - 2.0 * (neg_ext & 1)
        msg_c2v = sgn_ext * _phi(ph_ext)
        # posterior + syndrome early stop
        tot = llr + np.bincount(var, weights=msg_c2v, minlength=n)
        hard = (tot < 0).astype(np.uint8)
        syn = np.bincount(chk, weights=hard[var].astype(float),
                          minlength=m).astype(np.int64) & 1
        if capture:trace.append(dict(iteration=len(trace)+1,unsatisfied_checks=int(syn.sum()),checks=m,check_success_rate=float(1-syn.mean())))
        if not syn.any():
            return finish(hard, True)
    return finish(hard, False)


__all__ = ['build_code', 'encode', 'extract_info', 'qpsk_map',
           'demap_llr', 'decode_llr', 'decode_soft_messages', 'LLR_CLIP']
