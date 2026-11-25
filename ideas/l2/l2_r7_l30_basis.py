#!/usr/bin/env python3
"""Idea-funnel round 7 (runner l, claude-fable-5.2), L2 decisive check for parked card I-20261122-l30 (2026-11-23).
Question: for a bit-interleaved short binary code over 4x4 spatial multiplexing (8 bits per channel use), does re-basing each
8-bit symbol in GF(2) from its Walsh-Hadamard spectrum before ordered-statistics decoding beat (i) plain BICM at the better of
rank 4 QPSK and rank 2 16-QAM, (ii) one fixed basis per block, (iii) symbol-level reprocessing?  New code, numpy only
(the card's original probe script was never stored).  Pre-registered criteria: ideas/l2/PREDICTIONS_r7_l30.md.
  python l2_r7_l30_basis.py gate                       # implementation gates
  python l2_r7_l30_basis.py run --tag dev --first 1000 --frames 300 --workers 4
  python l2_r7_l30_basis.py read --tag dev
All arms: eBCH(128,64) with one random bit interleaver, block fading over the 16 data uses, orthogonal pilots and a
least-squares channel estimate used as if exact, the same total energy per block (pilots included), noise variance known,
order-2 reprocessing (2081 candidates; 1857 for the symbol-level arm), every candidate rescored with the joint Euclidean
metric under the estimated channel.
"""
import argparse, json, os, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np

SEED, K, N, T = 20261123, 64, 128, 16
HERE = Path(__file__).resolve().parent
BITS = ((np.arange(256)[:, None] >> np.arange(8)[None, :]) & 1).astype(np.uint8)          # BITS[b, i]
PAR = np.array([bin(i).count('1') & 1 for i in range(256)], np.uint8)
HAD = 1.0 - 2.0 * PAR[np.arange(256)[:, None] & np.arange(256)[None, :]]                   # HAD[w, b] = (-1)^{w.b}
PW = (1 << np.arange(8)).astype(np.int64)
I2, J2 = np.triu_indices(K, 1)
CONDS = dict(corr=0.85, iid=0.0)
SNRS = dict(corr=[float(s) for s in range(9, 20)], iid=[float(s) for s in range(6, 15)])   # 1 dB grid, frozen in PREDICTIONS_r7_l30.md (dev runs used a 2 dB grid)
ARMS = ['bicm4', 'wht', 'fixed', 'symosd', 'r2sub', 'r2eig', 'mllb4', 'union4', 'bicmid', 'r2sub_wht', 'r2eig_wht']
REBASED = ('wht', 'r2sub_wht', 'r2eig_wht')                 # arms that use per-symbol re-basing
STANDARD = ('bicm4', 'bicmid', 'r2sub', 'r2eig')            # rivals without re-basing, all at 8 bits per channel use


def make_code():
    """Systematic generator of the extended BCH(128,64) code (designed distance 21, extended 22)."""
    exp, log, x = [0] * 254, [0] * 128, 1
    for i in range(127):
        exp[i] = x; log[x] = i; x <<= 1
        if x & 128:
            x ^= 0x89                                                                      # x^7 + x^3 + 1
    for i in range(127, 254):
        exp[i] = exp[i - 127]
    roots = set()
    for r in range(1, 21):
        c = r
        while c not in roots:
            roots.add(c); c = (2 * c) % 127
    g = [1]
    for r in sorted(roots):
        a = exp[r]; ng = [0] * (len(g) + 1)
        for i, gi in enumerate(g):
            ng[i] ^= 0 if gi == 0 else exp[log[gi] + log[a]]
            ng[i + 1] ^= gi
        g = ng
    assert len(g) == 64 and all(c in (0, 1) for c in g), 'generator polynomial must be binary of degree 63'
    g = np.array(g, np.uint8); G = np.zeros((K, N), np.uint8)
    for i in range(K):
        r = np.zeros(64 + i, np.uint8); r[63 + i] = 1
        for d in range(63 + i, 62, -1):
            if r[d]:
                r[d - 63:d + 1] ^= g
        G[i, :63] = r[:63]; G[i, 63 + i] = 1
    G[:, 127] = G[:, :127].sum(1) % 2
    return G


def points_qpsk():                               # 4 streams, stream a carries bits 2a, 2a+1; unit power per stream
    return ((1 - 2.0 * BITS[:, 0::2]) + 1j * (1 - 2.0 * BITS[:, 1::2])) / np.sqrt(2)


def points_qam16():                              # 2 streams, stream a carries bits 4a..4a+3, Gray per axis; unit power
    lev = lambda b0, b1: (1 - 2.0 * b0) * (3 - 2.0 * b1)
    return np.stack([(lev(BITS[:, 4 * a], BITS[:, 4 * a + 1]) + 1j * lev(BITS[:, 4 * a + 2], BITS[:, 4 * a + 3])) / np.sqrt(10)
                     for a in range(2)], 1)


def mrb(G, order):
    """Gaussian elimination in reliability order: returns the generator in systematic form on the most reliable basis."""
    G = G.copy(); cols = []; row = 0
    for col in order:
        piv = np.flatnonzero(G[row:, col])
        if piv.size == 0:
            continue
        p = row + piv[0]
        if p != row:
            G[[row, p]] = G[[p, row]]
        m = G[:, col].astype(bool); m[row] = False
        G[m] ^= G[row]
        cols.append(col); row += 1
        if row == K:
            break
    return G, np.array(cols)


def idx_of(C):                                   # codeword bits (..., 128) -> symbol index per use (..., 16)
    return C.reshape(C.shape[:-1] + (T, 8)).astype(np.int64) @ PW


def score(C, D):                                 # Euclidean metric of candidates under per-use tables D (16, 256)
    return D[np.arange(T)[None, :], idx_of(C)].sum(1)


def greedy_basis(sc):
    """Eight GF(2)-independent parity masks in decreasing score (vector-matroid greedy)."""
    red, out = [], []
    for w in np.argsort(-sc[1:], kind='stable') + 1:
        v = int(w)
        for r in red:
            v = min(v, v ^ r)
        if v:
            red.append(v); out.append(int(w))
            if len(out) == 8:
                break
    return out


def osd2_basis(Gint, D, P, masks):
    """Order-2 OSD after re-basing use t with parity masks masks[t] (list of 8 ints); identity masks = plain BICM.
    Returns the best candidate in ORIGINAL bit coordinates and its metric."""
    Gt = np.empty_like(Gint); Dt = np.empty_like(D); llr = np.empty(N); back = np.empty((T, 256), np.int64)
    phat = np.clip(P @ HAD.T, -1 + 1e-12, 1 - 1e-12)
    for t in range(T):
        mk = np.array(masks[t])
        Gt[:, 8 * t:8 * t + 8] = (Gint[:, 8 * t:8 * t + 8].astype(np.int64) @ BITS[mk].T.astype(np.int64)) & 1
        tb = (PAR[np.arange(256)[:, None] & mk[None, :]].astype(np.int64) @ PW)             # original index -> re-based index
        back[t, tb] = np.arange(256); Dt[t, tb] = D[t]
        llr[8 * t:8 * t + 8] = 2 * np.arctanh(phat[t, mk])
    Gs, cols = mrb(Gt, np.argsort(-np.abs(llr), kind='stable'))
    c0 = ((llr[cols] < 0).astype(np.int64) @ Gs.astype(np.int64)) & 1
    C = np.concatenate([c0[None], c0[None] ^ Gs, c0[None] ^ Gs[I2] ^ Gs[J2]]).astype(np.uint8)
    m = score(C, Dt); b = int(np.argmin(m))
    orig = BITS[back[np.arange(T), idx_of(C[b])]].reshape(N)
    return orig, float(m[b])


def osd2_symbol(Gint, D, P, llr, kalt=8):
    """Symbol-level order-2 reprocessing: information set filled use by use in decreasing symbol reliability, hard
    decisions from the jointly most likely symbol, substitutions by the next kalt most likely symbols in one or two uses."""
    uses = np.argsort(-P.max(1), kind='stable')
    order = np.concatenate([8 * t + np.argsort(-np.abs(llr[8 * t:8 * t + 8]), kind='stable') for t in uses])
    Gs, cols = mrb(Gint, order)
    rank = np.argsort(-P, axis=1, kind='stable')
    hard = BITS[rank[:, 0]].reshape(N)
    u0 = hard[cols].astype(np.int64); c0 = (u0 @ Gs.astype(np.int64)) & 1
    su = np.unique(cols // 8); deltas = []
    for s in su:
        sel = np.flatnonzero(cols // 8 == s)
        alt = BITS[rank[s, 1:kalt + 1]][:, cols[sel] % 8].astype(np.int64)                  # (kalt, bits of use s in the set)
        du = np.zeros((kalt, K), np.int64); du[:, sel] = alt ^ u0[sel][None, :]
        deltas.append((du @ Gs.astype(np.int64)) & 1)
    dl = np.stack(deltas)                                                                   # (uses, kalt, 128)
    one = dl.reshape(-1, N); a, b = np.triu_indices(len(su), 1)
    two = (dl[a][:, :, None, :] ^ dl[b][:, None, :, :]).reshape(-1, N)
    C = (c0[None] ^ np.concatenate([np.zeros((1, N), np.int64), one, two])).astype(np.uint8)
    m = score(C, D); b = int(np.argmin(m))
    return C[b], float(m[b])


def bicm_id(Gint, D, llr0, rounds=3, clip=12.0):
    """Coordinate-domain iterative demapping with list soft output (the card's iterative rival): OSD-2 on bit LLRs, max-log
    a-posteriori LLRs from the candidate list, extrinsic part fed back as bit priors to the exact 256-point demapper.
    Returns the best candidate over all rounds under the joint Euclidean metric (3 OSD passes = 3x the candidates)."""
    llr = llr0.copy(); best = None; B = BITS.astype(float)
    for _ in range(rounds):
        Gs, cols = mrb(Gint, np.argsort(-np.abs(llr), kind='stable'))
        c0 = ((llr[cols] < 0).astype(np.int64) @ Gs.astype(np.int64)) & 1
        C = np.concatenate([c0[None], c0[None] ^ Gs, c0[None] ^ Gs[I2] ^ Gs[J2]]).astype(np.uint8)
        m = score(C, D); b = int(np.argmin(m))
        if best is None or m[b] < best[1]:
            best = (C[b].copy(), float(m[b]))
        m1 = np.where(C == 1, m[:, None], np.inf).min(0); m0 = np.where(C == 0, m[:, None], np.inf).min(0)
        app = np.clip(np.where(np.isinf(m1), clip, np.where(np.isinf(m0), -clip, m1 - m0)), -clip, clip)
        La = (app - llr).reshape(T, 8)                                                      # extrinsic from the decoder list
        prior = B @ (-np.logaddexp(0, La)).T + (1 - B) @ (-np.logaddexp(0, -La)).T          # (256, T): log prior of each point
        post = -D + prior.T; post -= post.max(1, keepdims=True); e = np.exp(post)
        s1 = e @ B; s0 = e @ (1 - B)
        llr = (np.log(np.maximum(s0, 1e-300)) - np.log(np.maximum(s1, 1e-300)) - La).reshape(N)
    return best


def tables(Y, Hhat, X):
    """Per-use squared distances to the 256 points and the posterior (noise variance 1)."""
    D = (np.abs(Y[:, None, :] - (X @ Hhat.T)[None, :, :]) ** 2).sum(-1)
    L = -(D - D.min(1, keepdims=True)); P = np.exp(L); P /= P.sum(1, keepdims=True)
    return D, P


def bit_llr(P):
    phat = np.clip(P @ HAD[PW].T, -1 + 1e-12, 1 - 1e-12)
    return (2 * np.arctanh(phat)).reshape(N)


_S = {}


def setup():
    if not _S:
        G = make_code(); perm = np.random.default_rng([SEED, 1]).permutation(N)
        _S.update(G=G, Gint=np.ascontiguousarray(G[:, perm]), Xq=points_qpsk(), Xm=points_qam16(), ident=[[1 << i for i in range(8)]] * T)
    return _S


def frame(cond, f, snrs, perfect=False, noiseless=False):
    """One block at every SNR with common random numbers.  Returns {snr: {arm: error flag}}."""
    S = setup(); rho = CONDS[cond]; rng = np.random.default_rng([SEED, 7, list(CONDS).index(cond), f])
    Rt = rho ** np.abs(np.arange(4)[:, None] - np.arange(4)[None, :]); ev, V = np.linalg.eigh(Rt)
    H = ((rng.standard_normal((4, 4)) + 1j * rng.standard_normal((4, 4))) / np.sqrt(2)) @ (V * np.sqrt(ev)) @ V.T
    cw = (rng.integers(0, 2, K) @ S['Gint'].astype(np.int64) & 1).astype(np.uint8); it = idx_of(cw)
    Wd = (rng.standard_normal((T, 4)) + 1j * rng.standard_normal((T, 4))) / np.sqrt(2)
    Wp = (rng.standard_normal((4, 4)) + 1j * rng.standard_normal((4, 4))) / np.sqrt(2)
    if noiseless:
        Wd, Wp = Wd * 0, Wp * 0
    out = {}
    for snr in snrs:
        p4 = 10 ** (snr / 10); p2 = p4 * 20 / 18; r = {}      # same block energy: 16 data + 4 pilot uses vs 16 + 2
        # rank 4, QPSK
        Hd = H * np.sqrt(p4 / 4); Hh = Hd if perfect else Hd + Wp * np.sqrt(1 / 4)        # LS from one full-power use per stream
        D, P = tables(S['Xq'][it] @ Hd.T + Wd, Hh, S['Xq'])
        llr = bit_llr(P); phat = P @ HAD.T; true_m = float(D[np.arange(T), it].sum()); cands = {}
        cands['bicm4'] = osd2_basis(S['Gint'], D, P, S['ident'])
        cands['wht'] = osd2_basis(S['Gint'], D, P, [greedy_basis(np.abs(phat[t])) for t in range(T)])
        cands['fixed'] = osd2_basis(S['Gint'], D, P, [greedy_basis(np.abs(phat).mean(0))] * T)
        cands['symosd'] = osd2_symbol(S['Gint'], D, P, llr)
        r['bicmid'] = bool(np.any(bicm_id(S['Gint'], D, llr)[0] != cw))
        for a, (c, m) in cands.items():
            r[a] = bool(np.any(c != cw))
        best = min(cands.values(), key=lambda cm: cm[1])
        r['union4'] = bool(np.any(best[0] != cw)); r['mllb4'] = bool(best[1] < true_m - 1e-9)
        # rank 2, 16-QAM: antenna subset {0, 3} (rank indicator only) and the two dominant transmit eigenmodes (long-term precoder)
        for a, B in (('r2sub', np.eye(4)[:, [0, 3]]), ('r2eig', V[:, [3, 2]])):
            Hd = (H @ B) * np.sqrt(p2 / 2); Hh = Hd if perfect else Hd + Wp[:, :2] * np.sqrt(1 / 2)
            D, P = tables(S['Xm'][it] @ Hd.T + Wd, Hh, S['Xm'])
            c, m = osd2_basis(S['Gint'], D, P, S['ident']); r[a] = bool(np.any(c != cw))
            ph = P @ HAD.T
            c, m = osd2_basis(S['Gint'], D, P, [greedy_basis(np.abs(ph[t])) for t in range(T)]); r[a + '_wht'] = bool(np.any(c != cw))
        out[snr] = r
    return out


def gate():
    S = setup(); G = S['G']; rng = np.random.default_rng(5)
    w = ((rng.integers(0, 2, (4000, K)) @ G.astype(np.int64)) & 1).sum(1)
    g = dict(rank=int(np.linalg.matrix_rank(G[:, 63:127].astype(float))), min_weight_sampled=int(w[w > 0].min()),
             row_weights_min=int(G.sum(1).min()), even_weight=bool(np.all(w % 2 == 0)))
    g['noiseless_errors'] = int(sum(v for f in range(8) for c in CONDS for r in frame(c, f, [10.0], perfect=True, noiseless=True).values() for v in r.values()))
    # re-basing must not change the metric of a codeword, and identity masks must reproduce plain bit LLRs
    rng = np.random.default_rng(6); D = rng.random((T, 256)); P = rng.random((T, 256)); P /= P.sum(1, keepdims=True)
    masks = [greedy_basis(rng.random(256)) for _ in range(T)]
    c1, m1 = osd2_basis(S['Gint'], D, P, masks)
    g['rebased_metric_consistent'] = bool(abs(m1 - float(score(c1[None], D)[0])) < 1e-9)
    g['rebased_is_codeword'] = bool(np.linalg.matrix_rank(np.vstack([S['Gint'], c1]).astype(float)) >= 0 and _in_code(S['Gint'], c1))
    g['identity_llr_matches'] = bool(np.allclose(bit_llr(P), np.concatenate([2 * np.arctanh(np.clip((P @ HAD.T)[t, PW], -1 + 1e-12, 1 - 1e-12)) for t in range(T)])))
    g['qam_unit_power'] = float(np.mean(np.abs(S['Xm']) ** 2)); g['qpsk_unit_power'] = float(np.mean(np.abs(S['Xq']) ** 2))
    g['PASS'] = bool(g['rank'] == 64 and g['min_weight_sampled'] >= 22 and g['even_weight'] and g['noiseless_errors'] == 0
                     and g['rebased_metric_consistent'] and g['rebased_is_codeword'] and g['identity_llr_matches']
                     and abs(g['qam_unit_power'] - 1) < 1e-9 and abs(g['qpsk_unit_power'] - 1) < 1e-9)
    print(json.dumps(g, indent=1)); return g


def _in_code(Gint, c):
    Gs, cols = mrb(Gint, np.arange(N))
    return bool(np.array_equal((c[cols].astype(np.int64) @ Gs.astype(np.int64)) & 1, c))


def _job(a):
    cond, f = a
    r = frame(cond, f, SNRS[cond])
    return cond, f, [[int(r[s][arm]) for arm in ARMS] for s in SNRS[cond]]


def run(tag, first, frames, workers):
    out = HERE / f'out_r7_l30'; out.mkdir(exist_ok=True); t0 = time.time()
    g = gate()
    if not g['PASS']:
        raise SystemExit('implementation gate failed')
    jobs = [(c, f) for c in CONDS for f in range(first, first + frames)]
    E = {c: np.zeros((frames, len(SNRS[c]), len(ARMS)), np.uint8) for c in CONDS}
    with get_context('fork').Pool(workers) as pool:
        for c, f, r in pool.imap_unordered(_job, jobs, chunksize=4):
            E[c][f - first] = r
    np.savez_compressed(out / f'errors_{tag}.npz', **E)
    json.dump(dict(tag=tag, first=first, frames=frames, workers=workers, seconds=time.time() - t0, snrs=SNRS, arms=ARMS, gate=g,
                   _argv=os.sys.argv, _config=dict(seed=SEED, conds=CONDS, K=K, N=N, T=T)), open(out / f'meta_{tag}.json', 'w'), indent=1)
    print('done', tag, round(time.time() - t0, 1), 's')


def cross(snrs, bler, target=1e-2):
    """SNR where the curve first goes below target (log-linear interpolation); None if it never does, grid minimum if below at once."""
    b = np.maximum(bler, 1e-6)
    for i in range(len(snrs)):
        if b[i] <= target:
            if i == 0:
                return None
            return float(snrs[i - 1] + (np.log(b[i - 1]) - np.log(target)) / (np.log(b[i - 1]) - np.log(b[i])) * (snrs[i] - snrs[i - 1]))
    return None


def read(tag, boot=1000):
    out = HERE / 'out_r7_l30'; E = np.load(out / f'errors_{tag}.npz'); meta = json.load(open(out / f'meta_{tag}.json'))
    rng = np.random.default_rng([SEED, 99]); res = {}
    for c in CONDS:
        e = E[c].astype(float); snrs = np.array(SNRS[c]); F = e.shape[0]

        def stats(x):
            bl = x.mean(0); cr = {a: cross(snrs, bl[:, i]) for i, a in enumerate(ARMS)}
            base = [cr[a] for a in ('bicm4', 'r2sub') if cr[a] is not None]
            d = dict(cr); d['best_openloop'] = min(base) if base else None
            std = [cr[a] for a in STANDARD if cr[a] is not None]; reb = [cr[a] for a in REBASED if cr[a] is not None]
            d['best_standard'] = min(std) if std else None; d['best_rebased'] = min(reb) if reb else None
            g = lambda u, v: (d[u] - d[v]) if d.get(u) is not None and d.get(v) is not None else None
            d['gain_wht_vs_openloop'] = g('best_openloop', 'wht'); d['gain_wht_vs_bicm4'] = g('bicm4', 'wht')
            d['gain_fixed_vs_bicm4'] = g('bicm4', 'fixed'); d['gain_wht_vs_symosd'] = g('symosd', 'wht')
            d['gain_wht_vs_r2eig'] = g('r2eig', 'wht'); d['gain_mllb_vs_openloop'] = g('best_openloop', 'mllb4')
            d['gain_union_vs_openloop'] = g('best_openloop', 'union4')
            d['gain_wht_vs_bicmid'] = g('bicmid', 'wht')
            d['gain_rebased_vs_standard'] = g('best_standard', 'best_rebased'); d['gain_r2eigwht_vs_r2eig'] = g('r2eig', 'r2eig_wht')
            d['fixed_share'] = (d['gain_fixed_vs_bicm4'] / d['gain_wht_vs_bicm4']) if d['gain_wht_vs_bicm4'] not in (None, 0) and d['gain_fixed_vs_bicm4'] is not None else None
            return bl, d
        bl, point = stats(e); bs = [stats(e[rng.integers(0, F, F)])[1] for _ in range(boot)]
        ci = {}
        for k in ('gain_wht_vs_openloop', 'gain_wht_vs_bicm4', 'gain_fixed_vs_bicm4', 'gain_wht_vs_symosd', 'gain_wht_vs_r2eig',
                  'gain_mllb_vs_openloop', 'gain_union_vs_openloop', 'fixed_share', 'gain_wht_vs_bicmid',
                  'gain_rebased_vs_standard', 'gain_r2eigwht_vs_r2eig'):
            v = [b[k] for b in bs if b[k] is not None]
            ci[k] = dict(point=point[k], lo=float(np.quantile(v, .025)) if len(v) > boot / 2 else None,
                         hi=float(np.quantile(v, .975)) if len(v) > boot / 2 else None, valid=len(v))
        res[c] = dict(frames=F, snrs=list(map(float, snrs)), bler={a: [float(x) for x in bl[:, i]] for i, a in enumerate(ARMS)},
                      errors={a: [int(x) for x in e[:, :, i].sum(0)] for i, a in enumerate(ARMS)},
                      cross_db={a: point[a] for a in ARMS}, best_openloop_db=point['best_openloop'],
                      best_standard_db=point['best_standard'], best_rebased_db=point['best_rebased'], gaps=ci)
    k = res['corr']['gaps']; v = lambda n: k[n]['point']; cr = res['corr']['cross_db']
    # Card I-20261122-l30, criteria (i)(ii)(iii) written on 2026-11-22; reading frozen in PREDICTIONS_r7_l30.md.
    # Judged on the correlated 4x4 condition (the card's claim); a curve that never reaches 1e-2 on the grid counts as worse.
    riv = [cr[a] for a in ('bicm4', 'r2sub', 'r2eig') if cr[a] is not None]; rival = min(riv) if riv else None
    gi = None if (cr['wht'] is None or rival is None) else rival - cr['wht']
    kill_i = bool(cr['wht'] is None or (gi is not None and gi < 1.0))
    gw, gf = v('gain_wht_vs_bicm4'), v('gain_fixed_vs_bicm4')
    share = (gf / gw) if (gw is not None and gw > 0 and gf is not None) else None
    kill_ii = bool(share is not None and share >= 0.8)
    gs = None if (cr['wht'] is None or cr['symosd'] is None) else cr['symosd'] - cr['wht']
    kill_iii = bool(cr['wht'] is None or (gs is not None and gs < 0.3))
    ol = [cr[a] for a in ('bicm4', 'r2sub') if cr[a] is not None]
    summ = dict(tag=tag, meta=dict(first=meta['first'], frames=meta['frames'], seconds=meta['seconds'], gate_pass=meta['gate']['PASS']), results=res,
                card_criteria=dict(i_gain_wht_vs_best_of_rank4_rank2_db=gi, i_rival_db=rival, ii_fixed_share=share, iii_gain_wht_vs_symbol_osd_db=gs),
                verdicts=dict(KILL_i_gain_below_1dB=kill_i, KILL_ii_fixed_basis_recovers_80pct=kill_ii, KILL_iii_symbol_osd_ties=kill_iii,
                              PASS_PRIMARY=bool(not (kill_i or kill_ii or kill_iii))),
                scope_readouts=dict(corr_gain_wht_vs_rank2_without_precoder_reading_db=(None if (cr['wht'] is None or not ol) else min(ol) - cr['wht']),
                                    corr_gain_best_rebased_vs_best_standard=k['gain_rebased_vs_standard'], corr_gain_wht_vs_bicm4=k['gain_wht_vs_bicm4'],
                                    corr_gain_wht_vs_r2eig=k['gain_wht_vs_r2eig'], corr_gain_wht_vs_bicmid=k['gain_wht_vs_bicmid'],
                                    corr_gain_r2eigwht_vs_r2eig=k['gain_r2eigwht_vs_r2eig'], corr_gain_wht_vs_symosd=k['gain_wht_vs_symosd'],
                                    corr_fixed_share=k['fixed_share'], corr_gain_mllb_vs_openloop=k['gain_mllb_vs_openloop'],
                                    iid_gain_wht_vs_bicm4=res['iid']['gaps']['gain_wht_vs_bicm4'], iid_gain_rebased_vs_standard=res['iid']['gaps']['gain_rebased_vs_standard']))
    json.dump(summ, open(out / f'summary_{tag}.json', 'w'), indent=1)
    for c in CONDS:
        print(c, 'frames', res[c]['frames']); print('  snr   ', res[c]['snrs'])
        for a in ARMS:
            print(f'  {a:7s}', res[c]['errors'][a], 'cross@1e-2:', None if res[c]['cross_db'][a] is None else round(res[c]['cross_db'][a], 2))
        for n, g in res[c]['gaps'].items():
            print(f'  {n:26s}', {kk: (None if vv is None else round(vv, 3)) for kk, vv in g.items()})
    print(json.dumps(summ['card_criteria'])); print(json.dumps(summ['verdicts']))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd', choices=['gate', 'run', 'read'])
    ap.add_argument('--tag', default='dev'); ap.add_argument('--first', type=int, default=1000)
    ap.add_argument('--frames', type=int, default=200); ap.add_argument('--workers', type=int, default=4)
    a = ap.parse_args()
    gate() if a.cmd == 'gate' else run(a.tag, a.first, a.frames, a.workers) if a.cmd == 'run' else read(a.tag)
