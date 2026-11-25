#!/usr/bin/env python3
"""L1 <=30s probe for I-20261123-g07 (parent: I-20261122-g15).
Isolates single-component intra-cluster per-tap prior unfolding (68 params total = 34/round,
ZERO learned noise or LLR-temperature scalars per LESSONS Rule 22) trained end-to-end through
fixed-iteration bilinear P-BiG-AMP (`twofft.py:51,64`) with pre-decoder signed-bit BCE loss,
against 5 strict controls on unseen dev frames (43500..43511) across Sinc (beta=0.0) and
unseen RRC/RC roll-off (beta=0.35) at SNR = 6.0 dB:
  1. ora_true48_fix       : Oracle 48-tap continuous channel upper bound
  2. free6_iso_cal        : Isotropic tau=1/48 + calibrated 1.35x noise (best classical from g15)
  3. deshrunk_pcsbl_cal   : Analytical VarPro-deattenuated Pattern-Coupled SBL (Fang TSP 2015)
                            with dev-tuned Round-0/Round-1 excess-variance thresholds
  4. bce_cal_only         : Learned frame noise/temperature ONLY (8 params, isotropic tau=1/48)
  5. mse_sblnet_2r        : Same 68-param per-tap prior network trained with channel MSE loss
                            (SBLNet-style, Gao et al. TWC 2023)
  6. bce_tap_unfold_2r    : Proposed 68-param per-tap prior network trained with pre-decoder
                            signed-bit BCE through 16-iter P-BiG-AMP (fixed 1.35x noise, temp=1.0)
Logs signed GMI (R0, R1), decoded FER, and mean cavity channel-uncertainty sum(vh).
"""
import os, sys, time, math
for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[k] = "1"

import types
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

M_REPO = "/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation"
sys.path.insert(0, os.path.join(M_REPO, "ideas", "l2"))
import l2_batch2 as b2


def make_g3_shim(C):
    daft_fn = C["ctx"].native.time_refine.__globals__["daft"]
    c1 = float(C["ctx"].system.c1)
    g3 = types.ModuleType("g_l2_batch3")
    g3.get_ctx = lambda: C
    g3.to_time_afdm = lambda x, c1_, c2_: daft_fn(x, c1_, c2_, True)
    g3.to_daft_afdm = lambda xt, c1_, c2_: daft_fn(xt, c1_, c2_, False)

    def pulse_kernel(t, beta):
        t = np.asarray(t, float)
        s = np.sinc(t)
        if beta <= 1e-12:
            return s
        den = 1.0 - (2.0 * beta * t) ** 2
        return s * np.where(np.abs(den) < 1e-7, math.pi / 4.0, np.cos(math.pi * beta * t) / np.where(np.abs(den) < 1e-7, 1.0, den))

    def frac_path_time(tsig, tau, nu, beta):
        n = len(tsig)
        k = np.arange(n, dtype=float)
        l0 = int(math.floor(tau))
        m_off = np.arange(-32, 33)
        w = pulse_kernel(tau - (l0 + m_off), beta)
        out = np.zeros(n, complex)
        for mo, wm in zip(m_off, w):
            lm = l0 + int(mo)
            wrap = k - lm
            cpp = np.where(wrap < 0, np.exp(2j * math.pi * c1 * (n * n + 2.0 * n * wrap)), 1.0)
            out += wm * tsig[np.mod(wrap.astype(int), n)] * cpp
        return out * np.exp(2j * math.pi * k * nu / n)

    g3.pulse_kernel = pulse_kernel
    g3.frac_path_time = frac_path_time
    sys.modules["g_l2_batch3"] = g3
    return g3


class TapPriorOnlyRoundModule(nn.Module):
    """Pure single-component 34-param/round (68 total across 2 rounds) 1D cluster magnitude
    prior network: 5 -> 4 -> 2 MLP. Zero learned noise or LLR-temperature scalars."""
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(5, 4)
        self.fc2 = nn.Linear(4, 2)
        nn.init.zeros_(self.fc1.bias)
        nn.init.normal_(self.fc1.weight, std=0.15)
        nn.init.normal_(self.fc2.weight, std=0.10)
        self.fc2.bias.data = torch.tensor([1.0, 0.5])

    def forward(self, h_raw, sigma2, v_mean, ex_norm):
        B_sz = h_raw.shape[0]
        # De-attenuated noise scale & raw cluster magnitudes:
        s_tap = ((sigma2 + v_mean) / torch.clamp(ex_norm, min=1.0)).view(B_sz, 1, 1)
        mag2 = h_raw.real ** 2 + h_raw.imag ** 2
        pad1 = F.pad(mag2, (1, 1), mode="constant", value=0.0)
        nb1 = pad1[:, :, :-2] + pad1[:, :, 2:]
        pad2 = F.pad(mag2, (2, 2), mode="constant", value=0.0)
        nb2 = pad2[:, :, :-4] + pad2[:, :, 4:]
        cl_sum = torch.sum(mag2, dim=-1, keepdim=True) + 6.0 * s_tap
        f1 = torch.log1p(mag2 / (s_tap + 1e-12))
        f2 = torch.log1p(nb1 / (s_tap + 1e-12))
        f3 = mag2 / (cl_sum + 1e-12)
        f4 = torch.log1p(nb2 / (s_tap + 1e-12))
        f5 = v_mean.view(B_sz, 1, 1).expand_as(mag2)
        out = self.fc2(torch.tanh(self.fc1(torch.stack([f1, f2, f3, f4, f5], dim=-1))))
        gate_init = torch.sigmoid(out[..., 0])
        h_init = gate_init.to(h_raw.dtype) * h_raw
        tau_raw = s_tap.squeeze(-1).unsqueeze(-1) * F.softplus(out[..., 1]) + (mag2 * f3 * 0.25)
        return h_init.reshape(B_sz, -1), torch.clamp(tau_raw.reshape(B_sz, -1), min=1e-6)


def true_h_on_grid(it, b_val, l_arr, nu_taps, pulse_kernel):
    h_proj = np.zeros(len(l_arr), complex)
    for li, ki, gi, oi in zip(it["l_true"], it["k_true"], it["g_true"], it["off_true"]):
        tau_t = float(li) + float(oi)
        for m in range(len(l_arr)):
            dl = (l_arr[m] - tau_t + 512.0) % 1024.0 - 512.0
            if abs(dl) <= 3.5 and abs(nu_taps[m] - ki) <= 0.75:
                h_proj[m] += gi * pulse_kernel(tau_t - l_arr[m], b_val) * np.exp(1j * math.pi * (ki - nu_taps[m])) * np.sinc(ki - nu_taps[m])
    return h_proj


def main():
    t0 = time.time()
    C = b2.setup()
    g3 = make_g3_shim(C)
    import g_r5_g01_collinear_unfold as g01

    ctx, stage3 = C["ctx"], C["stage3"]
    native = ctx.native
    daft_fn = native.time_refine.__globals__["daft"]
    c1, c2 = float(ctx.system.c1), float(ctx.system.c2)

    # 12 train frames (43000..43011, beta in {0.0, 0.25}) + 10 eval frames (43500..43509, beta in {0.0, 0.35}) -> <28s total
    tr_items = [g01._prep_worker((f, 600, [0.0, 0.25])) for f in range(43000, 43012)]
    ev_items = [g01._prep_worker((f, 600, [0.0, 0.35])) for f in range(43500, 43510)]
    max_gate = max(it["gate_err"] for it in tr_items + ev_items)
    assert max_gate < 1e-11, f"Noiseless/integer gate failed: {max_gate}"
    print(f"Gate err max: {max_gate:.2e} | Prepped 12 train + 10 eval frames in {time.time()-t0:.2f}s")

    def pack_round(items, b_fn, r0_mod=None):
        rows = []
        for it in items:
            b_u = b_fn(it["frame"])
            y_cur, pilot, s2 = it["y_map"][b_u], it["pilot"], it["sigma2"]
            r0 = it["r0_map"][b_u]
            l_arr, cl_map = r0["l_arr"], r0["cl_map"]
            if r0_mod is None:
                nu_taps = r0["nu_cl"][cl_map]
                h_raw = r0["h_raw"]
                mu, v, prior = r0["mu0"], r0["v0"], r0["prior0"]
            else:
                xt0 = daft_fn(pilot + r0["mu0"], c1, c2, True)
                with torch.no_grad():
                    hi0, tv0 = r0_mod(
                        torch.tensor(r0["h_raw"].reshape(1, 8, 6), dtype=torch.complex128),
                        torch.tensor([s2], dtype=torch.float64),
                        torch.tensor([float(np.mean(r0["v0"]))], dtype=torch.float64),
                        torch.tensor([float(np.vdot(xt0, xt0).real)], dtype=torch.float64),
                    )
                o0 = g01.run_hetero_np(native, c1, c2, y_cur, pilot, l_arr, r0["nu_cl"][cl_map],
                                       hi0[0].numpy(), s2 * 1.35, tv0[0].numpy(), temp_llr=1.0, prior=r0["prior0"], iterations=16)
                dec0 = native.decoder_messages(ctx.code, np.clip(o0["extrinsic"], -20, 20), maxiter=50)
                prior = np.clip(dec0["raw_check_extrinsic"], -20, 20)
                mu, v, _ = native.moments(np.clip(dec0["raw_app"], -20, 20), 0.5)
                nu_cl, h_raw = g01.refit_clusters(native, y_cur, pilot, mu, v, r0["clusters"], s2 * 1.35, c1, c2)
                nu_taps = nu_cl[cl_map]
            xt = daft_fn(pilot + mu, c1, c2, True)
            ht48 = true_h_on_grid(it, b_u, l_arr, nu_taps, g3.pulse_kernel)
            rows.append(dict(y=y_cur, pilot=pilot, l_arr=l_arr, nu_taps=nu_taps, h_raw=h_raw.reshape(8, 6),
                             sigma2=s2, v_mean=float(np.mean(v)), ex_norm=float(np.vdot(xt, xt).real),
                             prior=prior, b_pm=it["b_pm"], h_true=ht48))
        return dict(
            y=torch.tensor(np.stack([r["y"] for r in rows]), dtype=torch.complex128),
            pilot=torch.tensor(np.stack([r["pilot"] for r in rows]), dtype=torch.complex128),
            l_arr=torch.tensor(np.stack([r["l_arr"] for r in rows]), dtype=torch.long),
            nu_taps=torch.tensor(np.stack([r["nu_taps"] for r in rows]), dtype=torch.float64),
            h_raw=torch.tensor(np.stack([r["h_raw"] for r in rows]), dtype=torch.complex128),
            sigma2=torch.tensor([r["sigma2"] for r in rows], dtype=torch.float64),
            v_mean=torch.tensor([r["v_mean"] for r in rows], dtype=torch.float64),
            ex_norm=torch.tensor([r["ex_norm"] for r in rows], dtype=torch.float64),
            prior=torch.tensor(np.stack([r["prior"] for r in rows]), dtype=torch.float64),
            b_pm=torch.tensor(np.stack([r["b_pm"] for r in rows]), dtype=torch.float64),
            h_true=torch.tensor(np.stack([r["h_true"] for r in rows]), dtype=torch.complex128),
        )

    def fit_two_rounds(loss_kind):
        torch.manual_seed(20261123)
        mods = []
        for r_it in range(2):
            T = pack_round(tr_items, lambda f: 0.0 if f % 2 == 0 else 0.25, r0_mod=mods[0] if r_it == 1 else None)
            mod = TapPriorOnlyRoundModule().double()
            opt = torch.optim.Adam(mod.parameters(), lr=0.05)
            ne = T["sigma2"] * 1.35
            tl = torch.ones_like(T["sigma2"])
            for _ in range(14):
                opt.zero_grad()
                hi, tv = mod(T["h_raw"], T["sigma2"], T["v_mean"], T["ex_norm"])
                ext, _, _, h_out = g01.run_hetero_torch_batch(c1, c2, T["y"], T["pilot"], T["l_arr"], T["nu_taps"], hi, ne, tv, tl, T["prior"], iterations=16)
                if loss_kind == "mse":
                    loss = torch.mean(torch.abs(h_out - T["h_true"]) ** 2)
                else:
                    loss = F.softplus(-T["b_pm"] * torch.clamp(ext, -25.0, 25.0)).mean()
                loss.backward()
                opt.step()
            mod.eval()
            mods.append(mod)
        return mods

    mods_mse = fit_two_rounds("mse")
    mods_bce = fit_two_rounds("bce")
    n_params = sum(p.numel() for m in mods_bce for p in m.parameters())
    print(f"Trained 2-round TapPriorOnly modules ({n_params} params total) at {time.time()-t0:.2f}s")

    # Evaluate all 5 arms on ev_items across Sinc (0.0) and unseen RC (0.35):
    Channel = native.pilot_front.__globals__["Channel"]
    for b_lbl, b_v in [("sinc(0.00)", 0.0), ("rc(0.35)", 0.35)]:
        stats = {k: dict(g0=[], g1=[], fer=[], vh0=[], vh1=[]) for k in ["ora_true48", "free6_iso_cal", "deshrunk_pcsbl", "mse_sblnet_2r", "bce_tap_unfold_2r"]}
        for it in ev_items:
            y_cur, pilot, s2 = it["y_map"][b_v], it["pilot"], it["sigma2"]
            b_pm, truth = it["b_pm"], it["truth"]

            # Oracle 48-tap:
            l_l, nu_l, h_l = [], [], []
            for li, ki, gi, oi in zip(it["l_true"], it["k_true"], it["g_true"], it["off_true"]):
                tau_t = float(li) + float(oi); l0 = int(math.floor(tau_t)); offs = np.arange(-2, 4)
                for mo, wm in zip(offs, g3.pulse_kernel(tau_t - (l0 + offs), b_v)):
                    l_l.append((l0 + int(mo)) % 1024); nu_l.append(float(ki)); h_l.append(complex(gi * wm))
            ch_o = Channel(1024, c1, c2, np.array(l_l, int), np.array(nu_l, float), np.array(h_l, complex))
            pr_o = np.zeros(2048)
            for r_it in range(2):
                oo = native.scalar_joint(y_cur, pilot, ch_o, s2 * 1.15, pd=0.5, prior=pr_o, iterations=16, gain_mode="fixed")
                if r_it == 0: stats["ora_true48"]["g0"].append(g01.signed_gmi_qpsk(oo["extrinsic"], b_pm))
                do = native.decoder_messages(ctx.code, np.clip(oo["extrinsic"], -20, 20), maxiter=50)
                pr_o = np.clip(do["raw_check_extrinsic"], -20, 20)
            stats["ora_true48"]["g1"].append(g01.signed_gmi_qpsk(oo["extrinsic"], b_pm))
            stats["ora_true48"]["fer"].append(int(stage3.e1.gd.score(ctx, do["decoded"], truth) > 0))
            stats["ora_true48"]["vh0"].append(0.0); stats["ora_true48"]["vh1"].append(0.0)

            r0 = it["r0_map"][b_v]
            l_arr, cl_map = r0["l_arr"], r0["cl_map"]
            for arm in ["free6_iso_cal", "deshrunk_pcsbl", "mse_sblnet_2r", "bce_tap_unfold_2r"]:
                clusters = [(c[0], c[1], c[2]) for c in r0["clusters"]]
                mu, v, prior = r0["mu0"].copy(), r0["v0"].copy(), r0["prior0"].copy()
                for r_it in range(2):
                    if r_it == 0:
                        nu_cl, h_raw = r0["nu_cl"].copy(), r0["h_raw"].copy()
                    else:
                        nu_cl, h_raw = g01.refit_clusters(native, y_cur, pilot, mu, v, clusters, s2 * 1.35, c1, c2)
                        clusters = [(clusters[j][0], float(nu_cl[j]), clusters[j][2]) for j in range(len(clusters))]
                    xt = daft_fn(pilot + mu, c1, c2, True); ex = float(np.vdot(xt, xt).real); vm = float(np.mean(v))
                    if arm == "free6_iso_cal":
                        hi, tv = h_raw, np.full(48, 1.0 / 48.0)
                    elif arm == "deshrunk_pcsbl":
                        alpha = ex / (ex + 1024.0 * vm + 1.35 * s2); h_u = h_raw / alpha
                        s_u = (1.35 * s2 + vm) / max(ex, 1.0); thr = 1.0 if r_it == 0 else 2.5
                        ex_p = np.maximum(np.abs(h_u) ** 2 - thr * s_u, 0.0)
                        tv = np.zeros(48)
                        for j in range(8):
                            idx = np.flatnonzero(cl_map == j); mj = ex_p[idx]; mp = np.pad(mj, (1, 1))
                            tv[idx] = np.maximum(0.75 * mj + 0.125 * (mp[:-2] + mp[2:]), 1e-5)
                        hi = (tv / (tv + thr * s_u)) * h_u
                    else:
                        mod_use = (mods_mse if arm == "mse_sblnet_2r" else mods_bce)[r_it]
                        with torch.no_grad():
                            hi_t, tv_t = mod_use(
                                torch.tensor(h_raw.reshape(1, 8, 6), dtype=torch.complex128),
                                torch.tensor([s2], dtype=torch.float64),
                                torch.tensor([vm], dtype=torch.float64),
                                torch.tensor([ex], dtype=torch.float64),
                            )
                        hi, tv = hi_t[0].numpy(), tv_t[0].numpy()
                    o = g01.run_hetero_np(native, c1, c2, y_cur, pilot, l_arr, nu_cl[cl_map], hi, s2 * 1.35, tv, temp_llr=1.0, prior=prior, iterations=16)
                    if r_it == 0:
                        stats[arm]["g0"].append(g01.signed_gmi_qpsk(o["extrinsic"], b_pm))
                        stats[arm]["vh0"].append(float(np.sum(o["vh"])))
                    else:
                        stats[arm]["vh1"].append(float(np.sum(o["vh"])))
                    dec = native.decoder_messages(ctx.code, np.clip(o["extrinsic"], -20, 20), maxiter=50)
                    prior = np.clip(dec["raw_check_extrinsic"], -20, 20)
                    mu, v, _ = native.moments(np.clip(dec["raw_app"], -20, 20), 0.5)
                stats[arm]["g1"].append(g01.signed_gmi_qpsk(o["extrinsic"], b_pm))
                stats[arm]["fer"].append(int(stage3.e1.gd.score(ctx, dec["decoded"], truth) > 0))
        print(f"=== {b_lbl} (n={len(ev_items)}, SNR=6.0 dB) ===")
        for arm, st in stats.items():
            print(f"  {arm:18s} | G0={np.mean(st['g0']):.3f} G1={np.mean(st['g1']):.3f} FER={np.mean(st['fer']):.2f} | sum_vh(R0,R1)=({np.mean(st['vh0']):.4f}, {np.mean(st['vh1']):.4f})")
    print(f"Total runtime: {time.time()-t0:.2f}s")


if __name__ == "__main__":
    main()
