import os, time
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"

import numpy as np
from probe_m01_child_e2e import (daft_matrix, build_cpp_ext, build_H_ext, zero_unwrap_complex,
                                 build_pca_bases, exact_proj_dual_gn_pca, exact_proj_lumped_gn_pca,
                                 gn_dual_banded, gn_lumped, analytical_lumped_ser_bound)

def oamp_exact(y, H_td, Ah_mat, sigma2, pts, data_mask, x_pilot_vec, n_iter=8):
    y_d = y - H_td @ (Ah_mat @ x_pilot_vec)
    Hd = (H_td @ Ah_mat)[:, data_mask]
    Nd = Hd.shape[1]
    U, sv, Vh = np.linalg.svd(Hd, full_matrices=False)
    sv2 = sv**2; Uhy = U.conj().T @ y_d
    v_fl = min(5e-4, max(sigma2*0.5, 1e-6))
    r = np.zeros(Nd, dtype=complex); v = 1.0
    for _ in range(n_iter):
        lam = sigma2 / max(v, v_fl)
        gain = sv2 / (sv2 + lam)
        xhat_lin = r + Vh.conj().T @ ((sv / (sv2 + lam)) * (Uhy - sv * (Vh @ r)))
        c_bar = min(float(np.sum(gain) / Nd), 0.9999)
        v_post = max(v * (1.0 - c_bar), v_fl)
        r_ext = (xhat_lin - (1.0 - c_bar) * r) / max(c_bar, 1e-6)
        v_ext = max(v_post / max(c_bar, 1e-6), v_fl)
        d2 = np.abs(r_ext[:, None] - pts[None, :])**2 / v_ext
        d2 -= d2.min(axis=1, keepdims=True)
        w = np.exp(-d2); w /= w.sum(axis=1, keepdims=True)
        xhat = w @ pts
        vx = max(float(np.mean(np.sum(w * np.abs(pts[None, :] - xhat[:, None])**2, axis=1))), v_fl)
        eta = min(vx / v_ext, 0.995)
        r = 0.65 * ((xhat - eta * r_ext) / (1.0 - eta)) + 0.35 * r
        v = 0.65 * max(vx / (1.0 - eta), v_fl) + 0.35 * v
    x_soft = x_pilot_vec.copy(); x_soft[data_mask] = xhat
    x_hard = x_pilot_vec.copy(); x_hard[data_mask] = pts[np.argmin(np.abs(r_ext[:, None] - pts[None, :]), axis=1)]
    return x_soft, x_hard, vx

def blind_ce_varpro(y_tr, A, Ah, s_p_ext, N, L_cpp, two_Nc1, k_p):
    """100% BLIND channel + noise variance estimation from pilot training frame (ZERO truth)."""
    Y0 = A @ y_tr; n_arr = np.arange(N)
    # Initial robust noise floor from far-from-pilot bins [0:120] (completely outside [208:256]!)
    sig2_init = max(float(np.median(np.abs(Y0[:120])**2) / np.log(2.0)), 1e-7)
    en = np.array([float(np.sum(np.abs(Y0[k_p - two_Nc1*l - 1 : k_p - two_Nc1*l + 2])**2)) for l in range(L_cpp+1)])
    thr = max(15.0 * 3 * sig2_init, 0.04 * float(en.max()))
    cl = [l for l in range(L_cpp+1) if en[l] > thr and (l == 0 or en[l] >= en[l-1]) and (l == L_cpp or en[l] >= en[l+1])]
    if not cl: cl = [int(np.argmax(en))]
    cl = np.array(sorted(cl), dtype=int)
    nu_c = np.zeros(len(cl))
    for i, l in enumerate(cl):
        kc = k_p - two_Nc1*l
        m = np.zeros(N, dtype=bool); m[kc-2:kc+3] = True
        Ys = np.zeros(N, dtype=complex); Ys[m] = Y0[m]
        zp = (Ah @ Ys) * np.conj(s_p_ext[L_cpp + n_arr - l])
        ph = zero_unwrap_complex(zp[L_cpp:N-L_cpp]); ti = n_arr[L_cpp:N-L_cpp]
        sl = np.sum((ti-ti.mean())*(ph-ph.mean()))/np.sum((ti-ti.mean())**2)
        nu_c[i] = float(np.clip(-sl*N/(2*np.pi), -0.49, 0.49))
    for _ in range(3):
        X = np.column_stack([s_p_ext[L_cpp+n_arr-int(l)]*np.exp(-1j*2*np.pi*nu_c[i]*n_arr/N) for i,l in enumerate(cl)])
        h_c, _, _, _ = np.linalg.lstsq(X, y_tr, rcond=None)
        for i in range(len(cl)):
            res_i = y_tr - X @ h_c + X[:, i]*h_c[i]
            phi_i = X[:, i]*h_c[i]
            dphi = (-1j*2*np.pi*n_arr/N)*phi_i
            dnu = np.clip(float(np.real(np.vdot(dphi, res_i - phi_i)))/(float(np.real(np.vdot(dphi, dphi)))+1e-12), -0.1, 0.1)
            nu_c[i] = float(np.clip(nu_c[i] + dnu, -0.5, 0.5))
            X[:, i] = s_p_ext[L_cpp+n_arr-int(cl[i])]*np.exp(-1j*2*np.pi*nu_c[i]*n_arr/N)
    h_c, _, _, _ = np.linalg.lstsq(X, y_tr, rcond=None)
    # Exact unbiased blind noise variance from full-frame pilot residual!
    res_tr = y_tr - X @ h_c
    sig2_hat = max(float(np.sum(np.abs(res_tr)**2) / max(N - 2*len(cl), 1)), 1e-7)
    return sig2_hat, cl, h_c, nu_c

def main():
    t0 = time.time()
    N=512; L_cpp=16; B=N+L_cpp; two_Nc1=3; c1=two_Nc1/(2*N); c2=1/(2*np.pi*N)
    A_a=daft_matrix(N,c1,c2); Ah_a=A_a.conj().T; P_a=build_cpp_ext(N,c1,L_cpp)
    A_o=daft_matrix(N,0.0,0.0); Ah_o=A_o.conj().T; P_o=build_cpp_ext(N,0.0,L_cpp)
    g8=np.array([-7,-5,-3,-1,1,3,5,7]); pts64=(g8[:,None]+1j*g8[None,:]).ravel()/np.sqrt(42.0)
    qpsk=np.array([-1-1j,-1+1j,1-1j,1+1j])/np.sqrt(2.0)

    k_p=N//2; guard=np.zeros(N,dtype=bool); guard[180:334]=True; data_mask=~guard; n_guard=int(guard.sum()); Nd=int(data_mask.sum())
    pilot_obs_a=np.zeros(N,dtype=bool); pilot_obs_a[196:268]=True
    obs_o1=np.zeros(N,dtype=bool); obs_o1[200:312]=True
    comb_mask=np.zeros(N,dtype=bool); comb_mask[np.round(np.linspace(0,N-1,n_guard,endpoint=False)).astype(int)]=True; data_comb=~comb_mask
    x_p=np.zeros(N,dtype=complex); x_p[k_p]=np.sqrt(float(n_guard))
    sp_a=P_a@(Ah_a@x_p); sp_o=P_o@(Ah_o@x_p)
    pca=build_pca_bases(N,L_cpp,K_pca=18)
    ls_t=np.array([0,7,16]); pdp=np.array([0.4225,0.3025,0.2750]); w_p=pdp/pdp.sum()

    for name, snr_db, sig_r, sig_t, n_fr in [
        ("ZeroPN_30dB",  30.0, 0.0,    0.0,    2),
        ("PN_3e3_30dB",  30.0, 1.5e-3, 1.5e-3, 5),
        ("PN_3e3_45dB",  45.0, 1.5e-3, 1.5e-3, 5),
    ]:
        sig2_true = 10.0**(-snr_db/10.0)
        sig_r_p, sig_t_p = 1.5e-3, 1.5e-3
        sig2_irred, ana_ser = analytical_lumped_ser_bound(w_p, ls_t, sig_t, sig2_true, M=64)
        res = {k: [] for k in ['Uncomp', 'LumpPrac_Sym6', 'Gavert_Comb_DIC6', 'Gavert_Guard_1Step', 'NoDemux_CPE_GN6', 'AFDM_EP_Dual_Sym6', 'OFDM_c1=0_Sym6', 'LumpOrac_Indep', 'DualOrac']}
        for f in range(n_fr):
            rng = np.random.default_rng(40000+f)
            nus_t = rng.uniform(-0.4, 0.4, 3); hs_t = np.sqrt(pdp)*np.exp(1j*rng.uniform(0,2*np.pi,3))
            H_lin_t = build_H_ext(N, L_cpp, hs_t, ls_t, nus_t)
            w_tr = np.sqrt(sig2_true/2)*(rng.standard_normal(N)+1j*rng.standard_normal(N))
            sig2_hat, l_h, h_h, nu_h = blind_ce_varpro(H_lin_t@sp_a + w_tr, A_a, Ah_a, sp_a, N, L_cpp, two_Nc1, k_p)
            H_lin_h = build_H_ext(N, L_cpp, h_h, l_h, nu_h); H_circ_h = H_lin_h @ P_a
            H_paths_h = [build_H_ext(N, L_cpp, [h_h[i]], [l_h[i]], [nu_h[i]]) for i in range(len(l_h))]

            phi_t = np.cumsum(np.sqrt(sig_t)*rng.standard_normal(B)) if sig_t > 0 else np.zeros(B); phi_t -= phi_t[L_cpp]
            phi_r = np.cumsum(np.sqrt(sig_r)*rng.standard_normal(N)) if sig_r > 0 else np.zeros(N)
            w = np.sqrt(sig2_true/2)*(rng.standard_normal(N)+1j*rng.standard_normal(N))
            xd_vals = pts64[rng.integers(0, 64, Nd)]

            x_a = x_p.copy(); x_a[data_mask] = xd_vals
            y_a = np.exp(1j*phi_r)*(H_lin_t@(np.exp(1j*phi_t)*(P_a@(Ah_a@x_a)))) + w
            Y_a = A_a @ y_a

            def run_outer(y_in, P_i, Ah_i, dm_i, xp_i, pr0, pt0):
                pr_c, pt_c = pr0.copy(), pt0.copy(); s2 = sig2_hat
                best_r = np.inf; best_xh = None
                for out in range(6):
                    Hc = np.exp(1j*pr_c)[:,None]*((H_lin_h*np.exp(1j*pt_c)[None,:])@P_i)
                    xs, xhc, vx = oamp_exact(y_in, Hc, Ah_i, max(s2, 1e-6) + 0.02*(0.6**out), pts64, dm_i, xp_i, 8)
                    pr_c, pt_c = gn_dual_banded(y_in, H_lin_h, P_i@(Ah_i@xs), pr_c, pt_c, max(s2, 1e-6) + 0.5*vx, sig_r_p, sig_t_p, L_cpp, 3)
                    rc = float(np.sum(np.abs(y_in - np.exp(1j*pr_c)*(H_lin_h@(np.exp(1j*pt_c)*(P_i@(Ah_i@xhc)))))**2))
                    s2 = float(np.clip(rc/N, max(sig2_hat*0.5, 1e-6), 0.05))
                    if rc < best_r: best_r = rc; best_xh = xhc
                return best_xh
            def ser(xh, xt, dm): return float(np.mean(np.abs(xh[dm]-xt[dm]) > 1e-3))

            _, xhu, _ = oamp_exact(y_a, H_circ_h, Ah_a, sig2_hat, pts64, data_mask, x_p, 8)
            res['Uncomp'].append(ser(xhu, x_a, data_mask))

            ref_all = H_circ_h @ (Ah_a @ x_p)
            phi_cpe = np.full(N, np.angle(np.vdot(ref_all, y_a)))
            k_cs = [k_p - two_Nc1*int(l) for l in l_h]
            z_mrc = np.zeros(N, dtype=complex)
            for i, l in enumerate(l_h):
                k_hi = min(k_cs[i]+8, (k_cs[i]+k_cs[i-1])//2) if i>0 else k_cs[i]+8
                k_lo = max(k_cs[i]-8, (k_cs[i]+k_cs[i+1])//2+1) if i<len(l_h)-1 else k_cs[i]-8
                m = np.zeros(N, dtype=bool); m[k_lo:k_hi+1] = True
                Ys = np.zeros(N, dtype=complex); Ys[m] = Y_a[m]
                z_mrc += (Ah_a @ Ys) * np.conj(H_paths_h[i] @ sp_a)
            pi = zero_unwrap_complex(z_mrc[L_cpp:N-L_cpp])
            phi_mrc = np.empty(N); phi_mrc[L_cpp:N-L_cpp]=pi; phi_mrc[:L_cpp]=pi[0]; phi_mrc[N-L_cpp:]=pi[-1]

            # LumpPrac_Sym6 (symmetric 6 init + 6 outer + blind mismatch var!)
            phi_l = exact_proj_lumped_gn_pca(Y_a[pilot_obs_a], A_a[pilot_obs_a,:], H_lin_h, sp_a, phi_mrc, max(sig2_hat, 1e-3), sig_r_p+sig_t_p, L_cpp, pca, 6)
            s2_l = sig2_hat; xs_l = None
            for out in range(6):
                xs_l, _, vx_l = oamp_exact(y_a*np.exp(-1j*phi_l), H_circ_h, Ah_a, max(s2_l, 1e-6)+0.02*(0.6**out), pts64, data_mask, x_p, 8)
                phi_l = gn_lumped(y_a, H_circ_h, Ah_a@xs_l, phi_l, max(s2_l, 1e-6)+0.5*vx_l, sig_r_p+sig_t_p, 3)
                s2_l = float(np.clip(np.mean(np.abs(y_a*np.exp(-1j*phi_l)-H_circ_h@(Ah_a@xs_l))**2), max(sig2_hat*0.5, 1e-6), 0.05))
            _, xhl, _ = oamp_exact(y_a*np.exp(-1j*phi_l), H_circ_h, Ah_a, max(s2_l, 1e-6), pts64, data_mask, x_p, 10)
            res['LumpPrac_Sym6'].append(ser(xhl, x_a, data_mask))

            # Gavert_Guard_1Step
            pr, pt = exact_proj_dual_gn_pca(Y_a[pilot_obs_a], A_a[pilot_obs_a,:], H_paths_h, l_h, sp_a, phi_cpe, np.zeros(B), max(sig2_hat, 1e-3), sig_r_p, sig_t_p, L_cpp, pca, 1)
            res['Gavert_Guard_1Step'].append(ser(run_outer(y_a, P_a, Ah_a, data_mask, x_p, pr, pt), x_a, data_mask))

            # NoDemux_CPE_GN6
            pr, pt = exact_proj_dual_gn_pca(Y_a[pilot_obs_a], A_a[pilot_obs_a,:], H_paths_h, l_h, sp_a, phi_cpe, np.zeros(B), max(sig2_hat, 1e-3), sig_r_p, sig_t_p, L_cpp, pca, 6)
            res['NoDemux_CPE_GN6'].append(ser(run_outer(y_a, P_a, Ah_a, data_mask, x_p, pr, pt), x_a, data_mask))

            # AFDM_EP_Dual_Sym6
            pr, pt = exact_proj_dual_gn_pca(Y_a[pilot_obs_a], A_a[pilot_obs_a,:], H_paths_h, l_h, sp_a, phi_mrc, np.zeros(B), max(sig2_hat, 1e-3), sig_r_p, sig_t_p, L_cpp, pca, 6)
            res['AFDM_EP_Dual_Sym6'].append(ser(run_outer(y_a, P_a, Ah_a, data_mask, x_p, pr, pt), x_a, data_mask))

            # Gavert_Comb_DIC6
            xc=np.zeros(N,dtype=complex); xc[data_comb]=xd_vals; xc[comb_mask]=qpsk[rng.integers(0,4,n_guard)]
            xpc=np.where(comb_mask,xc,0.0); spc=P_a@(Ah_a@xpc)
            yc=np.exp(1j*phi_r)*(H_lin_t@(np.exp(1j*phi_t)*(P_a@(Ah_a@xc)))) + w; Yc=A_a@yc
            pcc=np.full(N,np.angle(np.vdot(H_circ_h@(Ah_a@xpc), yc)))
            pr, pt = exact_proj_dual_gn_pca(Yc[comb_mask], A_a[comb_mask,:], H_paths_h, l_h, spc, pcc, np.zeros(B), sig2_hat+Nd/N, sig_r_p, sig_t_p, L_cpp, pca, 3)
            Hc_ic = np.exp(1j*pr)[:,None]*((H_lin_h*np.exp(1j*pt)[None,:])@P_a)
            xs_ic, _, vx_ic = oamp_exact(yc, Hc_ic, Ah_a, sig2_hat+0.05, pts64, data_comb, xpc, 6)
            yc_dic = yc - np.exp(1j*pr)*(H_lin_h@(np.exp(1j*pt)*(P_a@(Ah_a@np.where(data_comb,xs_ic,0.0)))))
            pr, pt = exact_proj_dual_gn_pca((A_a@yc_dic)[comb_mask], A_a[comb_mask,:], H_paths_h, l_h, spc, pr, pt, sig2_hat+0.5*vx_ic, sig_r_p, sig_t_p, L_cpp, pca, 3)
            res['Gavert_Comb_DIC6'].append(ser(run_outer(yc, P_a, Ah_a, data_comb, xpc, pr, pt), xc, data_comb))

            # OFDM_c1=0_Sym6
            xo=x_p.copy(); xo[data_mask]=xd_vals
            yo=np.exp(1j*phi_r)*(H_lin_t@(np.exp(1j*phi_t)*(P_o@(Ah_o@xo)))) + w; Yo=A_o@yo
            pco=np.full(N,np.angle(np.vdot((H_lin_h@P_o)@(Ah_o@x_p), yo)))
            pr, pt = exact_proj_dual_gn_pca(Yo[obs_o1], A_o[obs_o1,:], H_paths_h, l_h, sp_o, pco, np.zeros(B), max(sig2_hat, 1e-3), sig_r_p, sig_t_p, L_cpp, pca, 6)
            res['OFDM_c1=0_Sym6'].append(ser(run_outer(yo, P_o, Ah_o, data_mask, x_p, pr, pt), xo, data_mask))

            # LumpOrac_Indep (true channel + optimal data-independent lumped phase + exact mismatch var!)
            phi_ind = phi_r + np.angle(sum(w_p[p]*np.exp(1j*phi_t[L_cpp-ls_t[p]:L_cpp-ls_t[p]+N]) for p in range(3)))
            _, xhlo, _ = oamp_exact(y_a*np.exp(-1j*phi_ind), H_lin_t@P_a, Ah_a, sig2_true+sig2_irred, pts64, data_mask, x_p, 10)
            res['LumpOrac_Indep'].append(ser(xhlo, x_a, data_mask))

            # DualOrac
            Ho = np.exp(1j*phi_r)[:,None]*((H_lin_t*np.exp(1j*phi_t)[None,:])@P_a)
            _, xhdo, _ = oamp_exact(y_a, Ho, Ah_a, sig2_true, pts64, data_mask, x_p, 10)
            res['DualOrac'].append(ser(xhdo, x_a, data_mask))

        print(f"\n[{name}] ({n_fr} fr, N=512, L=16 | AnaLumpLinearSER={ana_ser:.4f}):")
        for k in ['Uncomp', 'Gavert_Comb_DIC6', 'OFDM_c1=0_Sym6', 'Gavert_Guard_1Step', 'LumpPrac_Sym6', 'LumpOrac_Indep', 'NoDemux_CPE_GN6', 'AFDM_EP_Dual_Sym6', 'DualOrac']:
            a=np.array(res[k])
            print(f"  {k:20s}: mean={a.mean():.4f} | lock_loss(>5%)={(a>0.05).mean()*100:5.1f}% | max={a.max():.3f}")
    print(f"\nElapsed: {time.time()-t0:.1f}s")

if __name__ == '__main__':
    main()
