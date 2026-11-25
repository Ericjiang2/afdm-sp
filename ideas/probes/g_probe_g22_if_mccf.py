#!/usr/bin/env python3
"""Read-only L1 sanity probe for I-20261122-g22 (IF-MCCF, <= 25 s on local CPU)."""
import os
import time

for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[k] = '1'

import numpy as np

t0 = time.time()
rng = np.random.default_rng(2026)


def make_clean_ldpc(N, rate, dv=3, seed=13):
    r = np.random.default_rng(seed)
    M_c = int(round(N * (1.0 - rate)))
    H = np.zeros((M_c, N), dtype=np.uint8)
    for col in range(N):
        for _ in range(dv):
            row_degs = H.sum(axis=1)
            avail = np.where(H[:, col] == 0)[0]
            cur_rows = np.where(H[:, col] == 1)[0]
            if len(cur_rows) > 0:
                nbr_cols = np.where(H[cur_rows, :].sum(axis=0) > 0)[0]
                cyc4 = H[avail][:, nbr_cols].sum(axis=1)
            else:
                cyc4 = np.zeros(len(avail), dtype=int)
            score = cyc4 * 100 + row_degs[avail] + r.uniform(0, 0.1, len(avail))
            H[avail[np.argmin(score)], col] = 1
    return H


def make_generator(H_c):
    M_c, N = H_c.shape
    A = H_c.copy().astype(np.uint8)
    pivs = []
    r = 0
    for c in range(N):
        if r >= M_c:
            break
        idx = np.where(A[r:, c] == 1)[0]
        if len(idx) == 0:
            continue
        p = r + idx[0]
        if p != r:
            A[[r, p]] = A[[p, r]]
        other = np.where(A[:, c] == 1)[0]
        other = other[other != r]
        if len(other) > 0:
            A[other] ^= A[r]
        pivs.append(c)
        r += 1
    piv_set = set(pivs)
    free = [c for c in range(N) if c not in piv_set]
    K = len(free)
    G = np.zeros((K, N), dtype=np.uint8)
    for i, fc in enumerate(free):
        G[i, fc] = 1
        G[i, pivs] = A[:r, fc]
    return G, K


def prep_ldpc(H_c):
    M_c, N = H_c.shape
    rows, cols = np.nonzero(H_c)
    return M_c, N, rows, cols


def ldpc_bp_batch(ldpc_info, llr_in, n_iter=18):
    M_c, N, rows, cols = ldpc_info
    S = llr_in.shape[0]
    E = len(rows)
    row_off = (np.arange(S)[:, None] * M_c + rows[None, :]).ravel()
    col_off = (np.arange(S)[:, None] * N + cols[None, :]).ravel()
    m_c2v = np.zeros((S, E))
    m_v2c = llr_in[:, cols].copy()
    for _ in range(n_iter):
        t = np.tanh(np.clip(m_v2c * 0.5, -15.0, 15.0))
        sgn = np.where(t >= 0, 1.0, -1.0)
        lt = np.log(np.clip(np.abs(t), 1e-12, 1.0))
        sum_lt = np.bincount(row_off, weights=lt.ravel(), minlength=S * M_c).reshape(S, M_c)
        neg_cnt = np.bincount(row_off, weights=(t < 0).ravel(), minlength=S * M_c).reshape(S, M_c).astype(int)
        tot_sgn = np.where(neg_cnt % 2 == 0, 1.0, -1.0)
        prod_excl = (tot_sgn[:, rows] * sgn) * np.exp(sum_lt[:, rows] - lt)
        m_c2v = 2.0 * np.arctanh(np.clip(prod_excl, -1 + 1e-12, 1 - 1e-12))
        llr_ldpc = np.bincount(col_off, weights=m_c2v.ravel(), minlength=S * N).reshape(S, N)
        tot = llr_in + llr_ldpc
        m_v2c = tot[:, cols] - m_c2v
    return tot, llr_ldpc


def check_syndrome(H_c, bits):
    return np.all(((H_c @ bits) & 1) == 0)


def lse(a, axis=-1):
    m = np.max(a, axis=axis, keepdims=True)
    return m.squeeze(axis) + np.log(np.sum(np.exp(a - m), axis=axis))


def ep_mimo(Y, Hs, sigma2, llr_prior, n_ep=5, damp=0.35):
    N, Nr, K = Hs.shape
    p1 = 1.0 / (1.0 + np.exp(-np.clip(llr_prior, -30, 30)))
    mu_p = 2 * p1 - 1
    var_p = np.clip(1 - mu_p**2, 1e-4, 1.0)
    lam = 1.0 / var_p
    gam = mu_p / var_p
    HtH = np.einsum('nmi,nmj->nij', Hs, Hs) / sigma2
    Hty = np.einsum('nmi,nm->ni', Hs, Y) / sigma2
    eye = np.eye(K)[None, :, :]
    for _ in range(n_ep):
        Prec = HtH + lam[:, :, None] * eye
        Sigma = np.linalg.inv(Prec)
        mu = np.einsum('nij,nj->ni', Sigma, Hty + gam)
        v_post = np.clip(np.diagonal(Sigma, axis1=1, axis2=2), 1e-6, 1e6)
        inv_v_cav = np.maximum(1.0 / v_post - lam, 1e-6)
        h_cav = mu / v_post - gam
        L_post = 2.0 * h_cav + llr_prior
        pp = 1.0 / (1.0 + np.exp(-np.clip(L_post, -30, 30)))
        m_new = 2 * pp - 1
        v_new = np.clip(1 - m_new**2, 1e-4, 1.0)
        lam_new = np.maximum(1.0 / v_new - inv_v_cav, 1e-4)
        gam_new = m_new / v_new - h_cav
        lam = damp * lam + (1 - damp) * lam_new
        gam = damp * gam + (1 - damp) * gam_new
    Prec = HtH + lam[:, :, None] * eye
    Sigma = np.linalg.inv(Prec)
    mu = np.einsum('nij,nj->ni', Sigma, Hty + gam)
    v_post = np.clip(np.diagonal(Sigma, axis1=1, axis2=2), 1e-6, 1e6)
    h_cav = mu / v_post - gam
    return 2.0 * h_cav, Sigma, mu, lam, gam


def lll_reduce(B, delta=0.75):
    B = B.copy().astype(float)
    K = B.shape[1]
    U = np.eye(K, dtype=int)

    def gs(M):
        Q = np.zeros_like(M)
        R = np.eye(K)
        for j in range(K):
            v = M[:, j].copy()
            for i in range(j):
                R[i, j] = np.dot(Q[:, i], M[:, j]) / (np.dot(Q[:, i], Q[:, i]) + 1e-15)
                v -= R[i, j] * Q[:, i]
            Q[:, j] = v
        return Q, R

    Q, R = gs(B)
    k = 1
    while k < K:
        for j in range(k - 1, -1, -1):
            if abs(R[j, k]) > 0.5:
                q = int(np.round(R[j, k]))
                B[:, k] -= q * B[:, j]
                U[:, k] -= q * U[:, j]
                Q, R = gs(B)
        if np.dot(Q[:, k], Q[:, k]) >= (delta - R[k - 1, k] ** 2) * np.dot(Q[:, k - 1], Q[:, k - 1]):
            k += 1
        else:
            B[:, [k, k - 1]] = B[:, [k - 1, k]]
            U[:, [k, k - 1]] = U[:, [k - 1, k]]
            Q, R = gs(B)
            k = max(k - 1, 1)
    return B, U


def gf2_inv(A_mod2):
    K = A_mod2.shape[0]
    M = np.hstack([A_mod2.copy() & 1, np.eye(K, dtype=np.uint8)])
    for c in range(K):
        p = np.where(M[c:, c] == 1)[0]
        if len(p) == 0:
            return None
        p = c + p[0]
        if p != c:
            M[[c, p]] = M[[p, c]]
        other = np.where(M[:, c] == 1)[0]
        other = other[other != c]
        if len(other) > 0:
            M[other] ^= M[c]
    return M[:, K:]


def if_row_llr(Y, Hs, sigma2, am, Cov_pre, Hty_pre):
    aCov = np.einsum('i,nij->nj', am, Cov_pre)
    v_eff = np.clip(np.einsum('nj,j->n', aCov, am), 1e-9, None)
    z = np.einsum('ni,ni->n', aCov, Hty_pre)
    dist = {0: 1}
    for ak in am:
        ak = int(ak)
        if ak == 0:
            continue
        nd = {}
        for val, cnt in dist.items():
            nd[val + ak] = nd.get(val + ak, 0) + cnt
            nd[val - ak] = nd.get(val - ak, 0) + cnt
        dist = nd
    u_vals = np.array(sorted(dist.keys()), dtype=float)
    counts = np.array([dist[int(v)] for v in u_vals], dtype=float)
    par_u = ((int(np.sum(am)) - u_vals.astype(int)) // 2) & 1
    d2 = (z[:, None] - u_vals[None, :]) ** 2 / (2.0 * v_eff[:, None])
    ll = -d2 + np.log(counts[None, :])
    return lse(ll[:, par_u == 0], axis=1) - lse(ll[:, par_u == 1], axis=1)


def ep_xor_llr(Sigma, mu, lam, gam, i, j):
    sii = Sigma[:, i, i]
    sjj = Sigma[:, j, j]
    sij = Sigma[:, i, j]
    det = np.clip(sii * sjj - sij**2, 1e-12, None)
    p11 = sjj / det
    p22 = sii / det
    p12 = -sij / det
    h1 = p11 * mu[:, i] + p12 * mu[:, j] - gam[:, i]
    h2 = p12 * mu[:, i] + p22 * mu[:, j] - gam[:, j]
    beta = -p12

    def lcosh(z):
        az = np.abs(z)
        return az + np.log1p(np.exp(-2.0 * az))

    return 2.0 * beta + lcosh(h1 + h2) - lcosh(h1 - h2)


def integer_forcing_receiver(Y, H, sigma2, ldpc_info):
    N, Nr = Y.shape
    K = H.shape[1]
    Hs = np.broadcast_to(H[None, :, :], (N, Nr, K))
    Cov_s = np.linalg.inv(H.T @ H / sigma2 + np.eye(K))
    L = np.linalg.cholesky(Cov_s)
    _, U = lll_reduce(L.T)
    A = U.T
    Cov_b = np.broadcast_to(Cov_s[None, :, :], (N, K, K))
    Hty_b = (Y @ H) / sigma2
    llrs_u = np.array([if_row_llr(Y, Hs, sigma2, A[m], Cov_b, Hty_b) for m in range(K)])
    tot_u, _ = ldpc_bp_batch(ldpc_info, llrs_u, n_iter=22)
    U_hat = (tot_u < 0).astype(np.uint8)
    A_inv = gf2_inv(np.abs(A).astype(np.uint8) & 1)
    if A_inv is None:
        return turbo_ep(Y, Hs, sigma2, ldpc_info, n_turbo=5, damp=0.35)
    return (A_inv @ U_hat) & 1


def turbo_ep(Y, Hs, sigma2, ldpc_info, n_turbo=5, damp=0.35):
    N, Nr, K = Hs.shape
    llr_a = np.zeros((N, K))
    for _ in range(n_turbo):
        llr_e, _, _, _, _ = ep_mimo(Y, Hs, sigma2, llr_a, n_ep=5, damp=damp)
        tot, ext = ldpc_bp_batch(ldpc_info, llr_e.T, n_iter=18)
        llr_a = 0.7 * ext.T + 0.3 * llr_a
    return (tot < 0).astype(np.uint8)


def ep_sic_receiver(Y, H, sigma2, H_c, ldpc_info, n_turbo=5, damp=0.35):
    N, Nr = Y.shape
    K_orig = H.shape[1]
    Hs = np.broadcast_to(H[None, :, :], (N, Nr, K_orig)).copy()
    Y_cur = Y.copy()
    active_ids = list(range(K_orig))
    decoded = []
    for _ in range(K_orig):
        K = Hs.shape[2]
        if K == 0:
            break
        if K == 1:
            l0 = 2.0 * np.einsum('nm,nm->n', Y_cur, Hs[:, :, 0]) / sigma2
            tot, _ = ldpc_bp_batch(ldpc_info, l0[None, :], n_iter=22)
            decoded.append((active_ids[0], (tot[0] < 0).astype(np.uint8)))
            Hs = np.delete(Hs, 0, axis=2)
            del active_ids[0]
            break
        llr_e, _, _, _, _ = ep_mimo(Y_cur, Hs, sigma2, np.zeros((N, K)), n_ep=5, damp=damp)
        tot_b, _ = ldpc_bp_batch(ldpc_info, llr_e.T, n_iter=22)
        order = np.argsort([-float(np.mean(np.minimum(np.abs(llr_e[:, i]), 10.0))) for i in range(K)])
        chosen = None
        for i in order:
            b_hat = (tot_b[i] < 0).astype(np.uint8)
            if check_syndrome(H_c, b_hat):
                chosen = (i, b_hat)
                break
        if chosen is None:
            break
        i, b_hat = chosen
        Y_cur = Y_cur - (1.0 - 2.0 * b_hat)[:, None] * Hs[:, :, i]
        Hs = np.delete(Hs, i, axis=2)
        decoded.append((active_ids[i], b_hat))
        del active_ids[i]
    bits_out = np.zeros((K_orig, N), dtype=np.uint8)
    for oid, bv in decoded:
        bits_out[oid] = bv
    if Hs.shape[2] > 0:
        b_rem = turbo_ep(Y_cur, Hs, sigma2, ldpc_info, n_turbo=n_turbo, damp=damp)
        for idx_k, oid in enumerate(active_ids):
            bits_out[oid] = b_rem[idx_k]
    return bits_out


def if_mccf_receiver(Y, H, sigma2, H_c, ldpc_info, n_turbo=5, damp=0.35):
    N, Nr = Y.shape
    K_orig = H.shape[1]
    Hs = np.broadcast_to(H[None, :, :], (N, Nr, K_orig)).copy()
    Y_cur = Y.copy()
    active_ids = list(range(K_orig))
    folds = []
    n_folds = 0
    for _ in range(K_orig):
        K = Hs.shape[2]
        if K == 0:
            break
        if K == 1:
            l0 = 2.0 * np.einsum('nm,nm->n', Y_cur, Hs[:, :, 0]) / sigma2
            tot, _ = ldpc_bp_batch(ldpc_info, l0[None, :], n_iter=22)
            folds.append(('sic', active_ids[0], -1, (tot[0] < 0).astype(np.uint8)))
            Hs = np.delete(Hs, 0, axis=2)
            del active_ids[0]
            break
        HtH_all = np.einsum('nmi,nmj->nij', Hs, Hs) / sigma2
        Cov_all = np.linalg.inv(HtH_all + np.eye(K)[None, :, :])
        Hty_all = np.einsum('nmi,nm->ni', Hs, Y_cur) / sigma2
        Cov_avg = np.mean(Cov_all, axis=0)
        L = np.linalg.cholesky(Cov_avg)
        _, U = lll_reduce(L.T)
        A_lll = U.T
        cand_vecs = []
        seen = set()

        def add_cand(v):
            v = np.array(v, dtype=int)
            if int(np.sum(np.abs(v) & 1)) not in (1, 2):
                return
            nz = np.nonzero(v)[0]
            if len(nz) == 0:
                return
            if v[nz[0]] < 0:
                v = -v
            key = tuple(v.tolist())
            if key not in seen:
                seen.add(key)
                cand_vecs.append(v)

        for m in range(K):
            add_cand(A_lll[m])
            for m2 in range(m + 1, K):
                add_cand(A_lll[m] + A_lll[m2])
                add_cand(A_lll[m] - A_lll[m2])
        for i in range(K):
            e = np.zeros(K, dtype=int)
            e[i] = 1
            add_cand(e)
            for j in range(i + 1, K):
                e1 = np.zeros(K, dtype=int)
                e1[i] = 1
                e1[j] = 1
                add_cand(e1)
                e2 = np.zeros(K, dtype=int)
                e2[i] = 1
                e2[j] = -1
                add_cand(e2)
        scored = sorted([(float(a @ Cov_avg @ a), a) for a in cand_vecs], key=lambda x: x[0])
        top_a = [x[1] for x in scored[: min(6, len(scored))]]
        llrs_batch = [if_row_llr(Y_cur, Hs, sigma2, a, Cov_all, Hty_all) for a in top_a]
        tot_b, _ = ldpc_bp_batch(ldpc_info, np.array(llrs_batch), n_iter=22)
        chosen = None
        for idx_c, a in enumerate(top_a):
            b_hat = (tot_b[idx_c] < 0).astype(np.uint8)
            if check_syndrome(H_c, b_hat):
                chosen = (a, b_hat)
                break
        if chosen is None:
            llr_a_tmp = np.zeros((N, K))
            for _ in range(2):
                llr_e, Sig, mu, lam, gam = ep_mimo(Y_cur, Hs, sigma2, llr_a_tmp, n_ep=5, damp=damp)
                tot_t, ext_t = ldpc_bp_batch(ldpc_info, llr_e.T, n_iter=15)
                llr_a_tmp = 0.7 * ext_t.T + 0.3 * llr_a_tmp
            ep_cands = [('single', i, -1) for i in range(K)]
            ep_llrs = [llr_e[:, i] for i in range(K)]
            S_avg = np.mean(np.abs(Sig), axis=0)
            d_s = np.sqrt(np.clip(np.diag(S_avg), 1e-9, None))
            R_avg = S_avg / (d_s[:, None] * d_s[None, :])
            p_list = sorted([(R_avg[i, j], i, j) for i in range(K) for j in range(i + 1, K)], reverse=True)[:4]
            for _, i, j in p_list:
                ep_cands.append(('pair', i, j))
                ep_llrs.append(ep_xor_llr(Sig, mu, lam, gam, i, j))
            tot_e, _ = ldpc_bp_batch(ldpc_info, np.array(ep_llrs), n_iter=22)
            for idx_e, (kind, i, j) in enumerate(ep_cands):
                b_hat = (tot_e[idx_e] < 0).astype(np.uint8)
                if check_syndrome(H_c, b_hat):
                    a_fake = np.zeros(K, dtype=int)
                    a_fake[i] = 1
                    if kind == 'pair':
                        a_fake[j] = 1
                    chosen = (a_fake, b_hat)
                    break
        if chosen is None:
            break
        a, b_hat = chosen
        supp = np.where((np.abs(a) & 1) == 1)[0]
        if len(supp) == 1:
            i = int(supp[0])
            Y_cur = Y_cur - (1.0 - 2.0 * b_hat)[:, None] * Hs[:, :, i]
            Hs = np.delete(Hs, i, axis=2)
            folds.append(('sic', active_ids[i], -1, b_hat))
            del active_ids[i]
        else:
            i, j = int(supp[0]), int(supp[1])
            sgn_u = 1.0 - 2.0 * b_hat
            Hs[:, :, i] = Hs[:, :, i] + sgn_u[:, None] * Hs[:, :, j]
            Hs = np.delete(Hs, j, axis=2)
            folds.append(('fold', active_ids[i], active_ids[j], b_hat))
            del active_ids[j]
            n_folds += 1
    bits_out = np.zeros((K_orig, N), dtype=np.uint8)
    K_rem = Hs.shape[2]
    if K_rem > 0:
        b_rem = turbo_ep(Y_cur, Hs, sigma2, ldpc_info, n_turbo=n_turbo, damp=damp)
        for idx_k, oid in enumerate(active_ids):
            bits_out[oid] = b_rem[idx_k]
    for kind, id1, id2, b_vec in reversed(folds):
        if kind == 'sic':
            bits_out[id1] = b_vec
        else:
            bits_out[id2] = bits_out[id1] ^ b_vec
    return bits_out, n_folds


def make_complex_mimo_real(Nr_c, Nt_c, rho_t, rho_r):
    idx_t = np.arange(Nt_c)
    Lt = np.linalg.cholesky(rho_t ** np.abs(idx_t[:, None] - idx_t[None, :]))
    idx_r = np.arange(Nr_c)
    Lr = np.linalg.cholesky(rho_r ** np.abs(idx_r[:, None] - idx_r[None, :]))
    G = (rng.normal(0, 1, (Nr_c, Nt_c)) + 1j * rng.normal(0, 1, (Nr_c, Nt_c))) / np.sqrt(2.0 * Nr_c)
    Hc = Lr @ G @ Lt.T
    return np.block([[Hc.real, -Hc.imag], [Hc.imag, Hc.real]])


N = 240
rate = 0.5
H_c = make_clean_ldpc(N, rate, dv=3, seed=13)
G_c, K_info = make_generator(H_c)
ldpc_info = prep_ldpc(H_c)


def run_regime(name, Nr_c, Nt_c, rho_t, rho_r, snrs, n_trials=16):
    print(f'=== {name} (Complex {Nr_c}x{Nt_c} QPSK -> Real {2*Nr_c}x{2*Nt_c}, rho_t={rho_t}, rho_r={rho_r}, N={N}, R={K_info/N:.2f}) ===')
    for snr_db in snrs:
        sigma2 = 1.0 / (10 ** (snr_db / 10.0))
        b_ora = b_if = b_ep20 = b_ep35 = b_ep55 = b_epsic = b_mccf = 0.0
        tot_f = 0
        for _ in range(n_trials):
            H = make_complex_mimo_real(Nr_c, Nt_c, rho_t, rho_r)
            Nr, Nt = H.shape
            msg = rng.integers(0, 2, size=(Nt, K_info), dtype=np.uint8)
            C_true = (msg @ G_c) & 1
            X_true = (1.0 - 2.0 * C_true).T
            W = rng.normal(0, np.sqrt(sigma2), size=(N, Nr))
            Y = X_true @ H.T + W
            g = np.sum(H**2, axis=0)
            y_mf = X_true * g[None, :] + W @ H
            tot_ora, _ = ldpc_bp_batch(ldpc_info, (2.0 * y_mf / sigma2).T, n_iter=18)
            b_ora += np.mean((tot_ora < 0) != C_true)
            b_if += np.mean(integer_forcing_receiver(Y, H, sigma2, ldpc_info) != C_true)
            Hs_fix = np.broadcast_to(H[None, :, :], (N, Nr, Nt))
            b_ep20 += np.mean(turbo_ep(Y, Hs_fix, sigma2, ldpc_info, n_turbo=5, damp=0.20) != C_true)
            b_ep35 += np.mean(turbo_ep(Y, Hs_fix, sigma2, ldpc_info, n_turbo=5, damp=0.35) != C_true)
            b_ep55 += np.mean(turbo_ep(Y, Hs_fix, sigma2, ldpc_info, n_turbo=5, damp=0.55) != C_true)
            b_epsic += np.mean(ep_sic_receiver(Y, H, sigma2, H_c, ldpc_info, n_turbo=5, damp=0.35) != C_true)
            cm, nf = if_mccf_receiver(Y, H, sigma2, H_c, ldpc_info, n_turbo=5, damp=0.35)
            b_mccf += np.mean(cm != C_true)
            tot_f += nf
        b_ep1d = min(b_ep20, b_ep35, b_ep55)
        print(
            f'SNR={snr_db:4.1f}dB | Ora={b_ora/n_trials:.4f} | Lin-IF={b_if/n_trials:.4f} '
            f'| T-EP(1D)={b_ep1d/n_trials:.4f} | EP-SIC={b_epsic/n_trials:.4f} '
            f'| IF-MCCF={b_mccf/n_trials:.4f} (folds={tot_f/n_trials:.2f})'
        )


if __name__ == '__main__':
    run_regime('Regime 1: Correlated 4x4 QPSK MIMO', 4, 4, 0.92, 0.50, [10.0, 12.0, 14.0], n_trials=16)
    run_regime('Regime 2: Overloaded 3x4 Correlated QPSK MIMO', 3, 4, 0.88, 0.30, [10.0, 12.0, 14.0], n_trials=16)
    run_regime('Regime 3: Overloaded 2x3 Correlated QPSK MIMO', 2, 3, 0.85, 0.00, [10.0, 12.0, 14.0], n_trials=16)
    print(f'Elapsed: {time.time()-t0:.2f}s')
