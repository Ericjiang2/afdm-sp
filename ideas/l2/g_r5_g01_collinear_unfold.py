#!/usr/bin/env python3
"""Runner g — Round 5 Batch 1 L2 verification for I-20261123-g01 (parent: I-20261122-g15).
Pre-registered protocol & boolean gates: ideas/l2/PREDICTIONS_g_r5b1.md.

Strictly enforces:
  1. Fresh disjoint frame partitions (ZERO overlap with g15's 45800..45829 or 46000..46199):
       - Smoke / noiseless / PyTorch-NumPy parity gate: frames 42990..42991
       - Train set (learned arms ONLY): frames 43000..43399 (400 frames, mixed beta in {0.0, 0.25}, SNR=6.0 dB)
       - Dev / scalar calibration & early-stop set: frames 43500..43579 (80 frames, beta in {0.0, 0.25}, SNR=6.0 dB)
       - Unseen test set: frames 47000..47239 (240 frames) across sinc (0.0), unseen rc015 (0.15), unseen rc035 (0.35)
         at SNR=6.0 dB, plus 160 unseen frames (47000..47159) at SNR=5.5 dB and 7.0 dB on sinc & rc035.
  2. Matched detector interface (Rule 21): all 6 non-oracle cluster arms run through identical 2-round
     2D cluster extraction -> Doppler refinement -> scalar_joint_hetero -> decoder_messages(maxiter=50).
  3. True signed-bit GMI (messages.py ALL-I THEN ALL-Q convention) and decoded FER (stage3.e1.gd.score).
  4. Seven paired arms isolating scalar noise calibration, full Fang-2015 PC-SBL, zero-train collinear projection,
     phase-blind magnitude unfolding (mlp_mag_unfold, 76 params), and collinear unfolding (collinear_unfold, 76 params).
"""
import argparse, json, math, os, sys, time
from multiprocessing import get_context
from pathlib import Path

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import numpy as np
from scipy import optimize
import torch
import torch.nn as nn
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import g_l2_batch3 as g3


def bootstrap_diff(a, b, rng, B=4000):
    d = np.asarray(a, float) - np.asarray(b, float)
    n = len(d)
    idx = rng.integers(0, n, size=(B, n))
    means = d[idx].mean(axis=1)
    return dict(point=float(d.mean()), ci95=[float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))])


def true_bits_pm_from_raw(raw, obs):
    """Exact ALL-I THEN ALL-Q bit sign vector (+1 for bit 0, -1 for bit 1) per messages.py:1,8."""
    from l2_batch3 import scale_of
    d = np.asarray(raw["data"], complex) / scale_of(raw, obs)
    b01 = np.concatenate([(d.real < 0).astype(np.float64), (d.imag < 0).astype(np.float64)])
    return 1.0 - 2.0 * b01


def signed_gmi_qpsk(llrs, b_pm):
    l = np.asarray(llrs, dtype=np.float64)
    return float(2.0 * np.mean(1.0 - np.log2(1.0 + np.exp(np.clip(-b_pm * l, -40.0, 40.0)))))


def build_frame_pulses(C, frame, snr_centi, betas, rho=250):
    from l2_batch3 import scale_of
    stage3, ctx = C["stage3"], C["ctx"]
    s = ctx.system
    c1, c2 = float(s.c1), float(s.c2)
    base = stage3.inputs(ctx, frame, "U", rho)
    raw, obs, truth = stage3.observed(ctx, base, rho, snr_centi)
    w = np.sqrt(float(obs["sigma2"])) * np.asarray(raw["noise"])
    x = np.asarray(obs["pilot"], complex) + np.asarray(raw["data"], complex) / scale_of(raw, obs)
    tsig = g3.to_time_afdm(x, c1, c2)
    l = np.asarray(truth["l_i"], int)
    k = np.asarray(truth["k_real"], float)
    g = np.asarray(truth["g_i"], complex)
    off = np.random.default_rng([20261123, frame, 71]).uniform(-0.5, 0.5, len(l))
    ci = sum(gi * g3.frac_path_time(tsig, float(li), ki, 0.0) for li, ki, gi in zip(l, k, g))
    y_int = g3.to_daft_afdm(ci, c1, c2) + w
    gate_err = float(np.linalg.norm(y_int - obs["y"]) / np.linalg.norm(obs["y"]))
    y_map = {}
    for b in betas:
        ce_b = sum(gi * g3.frac_path_time(tsig, float(li) + oi, ki, float(b)) for li, ki, gi, oi in zip(l, k, g, off))
        y_map[float(b)] = g3.to_daft_afdm(ce_b, c1, c2) + w
    b_pm = true_bits_pm_from_raw(raw, obs)
    return dict(frame=frame, snr_centi=snr_centi, obs=obs, truth=truth, l=l, k=k, g=g, off=off,
                y_map=y_map, b_pm=b_pm, gate_err=gate_err)


def extract_2d_clusters_and_refit_r0(C, obs_cur):
    ctx = C["ctx"]
    native = ctx.native
    daft_fn = native.time_refine.__globals__["daft"]
    dkernel = native.time_refine.__globals__["dkernel"]
    c1, c2, l_max = float(ctx.system.c1), float(ctx.system.c2), int(ctx.system.l_max_cap)
    y_cur = np.asarray(obs_cur["y"], complex)
    n = len(y_cur)
    sigma2 = float(obs_cur["sigma2"])
    s0 = native.pilot_front(obs_cur, ctx.system, ctx.code)
    order = np.argsort(-np.abs(s0["gains"]) ** 2)
    centers = []
    for idx in order:
        d0, nu0 = int(s0["delays"][idx]), float(s0["dopplers"][idx])
        if all((abs(d0 - c[0]) > 2) or (abs(nu0 - c[1]) > 1.0) for c in centers):
            centers.append((d0, nu0))
        if len(centers) >= 8:
            break
    while len(centers) < 8:
        centers.append((int(len(centers) * 10), 0.0))
    clusters = [(d0, nu0, list(range(max(0, min(l_max - 5, d0 - 2)), max(0, min(l_max - 5, d0 - 2)) + 6))) for d0, nu0 in centers]
    nu_cl, h_raw = refit_clusters(native, y_cur, obs_cur["pilot"], s0["mu"], s0["v"], clusters, sigma2 * 1.35, c1, c2)
    clusters = [(clusters[j][0], float(nu_cl[j]), clusters[j][2]) for j in range(len(clusters))]
    l_arr = np.concatenate([np.array(c[2], int) for c in clusters])
    cl_map = np.concatenate([np.full(len(c[2]), j, int) for j, c in enumerate(clusters)])
    return dict(clusters=clusters, l_arr=l_arr, cl_map=cl_map, nu_cl=nu_cl, h_raw=h_raw,
                mu0=s0["mu"].copy(), v0=s0["v"].copy(), prior0=s0["prior"].copy())


def refit_clusters(native, y_cur, pilot, mu, v, clusters, sig_reg, c1, c2):
    daft_fn = native.time_refine.__globals__["daft"]
    dkernel = native.time_refine.__globals__["dkernel"]
    n = len(y_cur)
    k_idx = np.arange(n)
    Y_time = daft_fn(y_cur, c1, c2, True)
    xt = daft_fn(pilot + mu, c1, c2, True)
    fft_v = np.fft.fft(v)
    nu_cl = np.array([c[1] for c in clusters], float)
    l_arr = np.concatenate([np.array(c[2], int) for c in clusters])
    cl_map = np.concatenate([np.full(len(c[2]), j, int) for j, c in enumerate(clusters)])
    wrap = k_idx[:, None] - l_arr[None, :]
    base = xt[wrap % n] * np.where(wrap < 0, np.exp(2j * np.pi * c1 * (n * n + 2 * n * wrap)), 1.0)
    dl = l_arr[None, :] - l_arr[:, None]
    gv = np.exp(2j * np.pi * c1 * (l_arr[:, None] ** 2 - l_arr[None, :] ** 2)) * fft_v[dl % n]

    def ev_ls(nu_v):
        nt = nu_v[cl_map]
        B = base * np.exp(2j * np.pi * k_idx[:, None] * nt[None, :] / n)
        G_m = gv * dkernel(nt[None, :] - nt[:, None] + 2 * n * c1 * dl, n)
        G_m = 0.5 * (G_m + G_m.conj().T)
        Q = B.conj().T @ B + G_m + sig_reg * np.eye(len(l_arr))
        bv = B.conj().T @ Y_time
        h = np.linalg.solve(Q, bv)
        return float((np.vdot(Y_time, Y_time) - np.vdot(bv, h)).real), h

    val, h_raw = ev_ls(nu_cl)
    for j in range(len(nu_cl)):
        z0 = nu_cl[j]
        opt = optimize.minimize_scalar(
            lambda z, jj=j: ev_ls(np.where(np.arange(len(nu_cl)) == jj, z, nu_cl))[0],
            bounds=(max(-3.0, z0 - 0.75), min(3.0, z0 + 0.75)),
            method="bounded",
            options={"xatol": 0.003, "maxiter": 12},
        )
        if opt.fun < val:
            nu_cl[j] = float(opt.x)
            val, h_raw = ev_ls(nu_cl)
    return nu_cl, h_raw


def scalar_joint_hetero_np(native, y, pilot, l_arr, nu_taps, h_init, noise, tau_vec, temp_llr=1.0, pd=0.5, prior=None, iterations=20, damping=0.3):
    Channel = native.pilot_front.__globals__["Channel"]
    TimePathOps = native.scalar_joint.__globals__["TimePathOps"]
    alphabet = native.scalar_joint.__globals__["alphabet"]
    marginal = native.scalar_joint.__globals__["marginal"]
    moments = native.scalar_joint.__globals__["moments"]
    daft_fn = native.time_refine.__globals__["daft"]
    c1, c2 = float(native.pilot_front.__globals__.get("_unused", 0.0)), 0.0  # overridden via Channel
    n = len(y)
    # Recover c1, c2 from caller via tuple if needed; pass Channel directly:
    raise NotImplementedError


def run_hetero_np(native, c1, c2, y, pilot, l_arr, nu_taps, h_init, noise, tau_vec, temp_llr=1.0, pd=0.5, prior=None, iterations=20, damping=0.3):
    Channel = native.pilot_front.__globals__["Channel"]
    TimePathOps = native.scalar_joint.__globals__["TimePathOps"]
    alphabet = native.scalar_joint.__globals__["alphabet"]
    marginal = native.scalar_joint.__globals__["marginal"]
    moments = native.scalar_joint.__globals__["moments"]
    daft_fn = native.time_refine.__globals__["daft"]

    y = np.asarray(y, complex)
    pilot = np.asarray(pilot, complex)
    n = len(y)
    c = Channel(n, c1, c2, np.asarray(l_arr, int), np.asarray(nu_taps, float), np.asarray(h_init, complex))
    if prior is None:
        prior = np.zeros(2 * n)
    a, _ = alphabet(pd)
    mu, v, _ = moments(prior, pd)
    x = pilot + mu
    o = TimePathOps(c)
    Y = daft_fn(y, c.c1, c.c2, True)
    tau = np.maximum(np.asarray(tau_vec, float), 1e-6)
    h = c.gains.copy()
    vh = tau.copy()
    xb = x.copy()
    hb = h.copy()
    Bb = None
    s_vec = np.zeros(n, complex)
    sv = 0.0
    bar0 = None
    vp0 = None
    for _ in range(iterations):
        xt = daft_fn(x, c.c1, c.c2, True)
        B = o.responses_time(xt)
        vx = float(v.mean())
        ex = float(np.vdot(x, x).real)
        channel_norm = o.power(h)
        sum_vh = float(np.sum(vh))
        bar = vx * channel_norm + sum_vh * ex / n
        vp = bar + sum_vh * vx
        if bar0 is not None:
            bar = damping * bar + (1.0 - damping) * bar0
            vp = damping * vp + (1.0 - damping) * vp0
        bar0, vp0 = bar, vp
        z = B @ h
        ph = z - s_vec * bar
        s_vec = damping * (Y - ph) / (noise + vp) + (1.0 - damping) * s_vec
        sv = damping / (noise + vp) + (1.0 - damping) * sv
        xb = damping * x + (1.0 - damping) * xb
        hb = damping * h + (1.0 - damping) * hb
        Bb = B.copy() if Bb is None else damping * B + (1.0 - damping) * Bb
        vr = 1.0 / max(sv * o.power(hb), 1e-12)
        vq = 1.0 / max(sv * np.vdot(xb, xb).real, 1e-12)
        adj = daft_fn(o.adjoint_time(hb, s_vec), c.c1, c.c2)
        rx = x + vr * (adj - xb * (sv * sum_vh))
        rh = h + vq * (Bb.conj().T @ s_vec - hb * sv * n * vx)
        ext, app, mu, v = marginal(-abs((rx - pilot)[:, None] - a) ** 2 / vr, prior, pd)
        x = pilot + mu
        vh = tau * vq / (tau + vq)
        h = tau * rh / (tau + vq)
    return dict(extrinsic=ext * float(temp_llr), app=app, mu=mu, v=v, gains=h, vh=vh)


# ==============================================================================
# PyTorch Batched Differentiable Detector + 76-Param Unfolded Prior Module
# ==============================================================================

class PriorUnfoldRoundModule(nn.Module):
    """38 parameters per round (76 total across 2 rounds):
    5 -> 4 -> 2 per-tap MLP (34 params) + 4 frame noise/temperature scalars = 38 params/round."""
    def __init__(self, mode="collinear"):
        super().__init__()
        self.mode = mode
        self.fc1 = nn.Linear(5, 4)
        self.fc2 = nn.Linear(4, 2)
        # Initialize near reasonable identity/prior baseline so training starts cleanly:
        nn.init.zeros_(self.fc1.bias)
        nn.init.normal_(self.fc1.weight, std=0.15)
        nn.init.normal_(self.fc2.weight, std=0.10)
        self.fc2.bias.data = torch.tensor([1.0, 0.5])
        # Frame noise multiplier softplus(w0 + w1 * split + w2 * orth_ratio) + LLR temp softplus(w3)
        self.w_noise = nn.Parameter(torch.tensor([0.85, 0.25, 0.15]))
        self.w_temp = nn.Parameter(torch.tensor([0.55]))  # softplus(0.55) ~ 1.0

    def forward(self, h_raw, sigma2, v_mean, ex_norm):
        """
        h_raw: (B, P_c, 6) complex64/complex128
        sigma2, v_mean, ex_norm: (B,) float
        Returns: h_init (B, 48), tau_vec (B, 48), noise_eff (B,), temp_llr (B,)
        """
        B_sz, P_c, K = h_raw.shape
        s_tap = ((sigma2 + v_mean) / torch.clamp(ex_norm, min=1.0)).view(B_sz, 1, 1)  # (B,1,1)

        if self.mode == "collinear":
            # Smooth principal 1D real-collinear axis u_j = sum_k h_{j,k}^2 -> theta_j = 0.5 * angle(u_j)
            s2 = torch.sum(h_raw * h_raw, dim=-1, keepdim=True)  # (B, P_c, 1)
            theta = 0.5 * torch.atan2(s2.imag, s2.real + 1e-12)
            rot = torch.polar(torch.ones_like(theta), -theta)
            h_rot = h_raw * rot
            re_p = h_rot.real
            im_p = h_rot.imag
            re2 = re_p * re_p
            im2 = im_p * im_p

            # Neighbor signed products along collinear real axis
            prod = re_p[:, :, :-1] * re_p[:, :, 1:]
            nb_sum = torch.zeros_like(re_p)
            nb_sum[:, :, :-1] = nb_sum[:, :, :-1] + prod
            nb_sum[:, :, 1:] = nb_sum[:, :, 1:] + prod
            nb_pos = F.relu(nb_sum)
            nb_neg = F.relu(-nb_sum)

            f1 = torch.log1p(re2 / (s_tap + 1e-12))
            f2 = torch.log1p(im2 / (s_tap + 1e-12))
            f3 = re2 / (re2 + im2 + s_tap + 1e-12)
            f4 = torch.log1p(nb_pos / (s_tap + 1e-12))
            f5 = torch.log1p(nb_neg / (s_tap + 1e-12))
            feats = torch.stack([f1, f2, f3, f4, f5], dim=-1)  # (B, P_c, 6, 5)

            out = self.fc2(torch.tanh(self.fc1(feats)))  # (B, P_c, 6, 2)
            gate_init = torch.sigmoid(out[..., 0])
            # Interpolate smoothly between collinear real projection and raw complex tap
            h_col = torch.polar(torch.ones_like(theta), theta) * re_p.to(h_raw.dtype)
            h_init = gate_init * h_col + (1.0 - gate_init) * h_raw
            tau_raw = s_tap.squeeze(-1).unsqueeze(-1) * F.softplus(out[..., 1]) + (re2 * f3 * 0.25)

            # Frame-level split ratio & quadrature interference ratio
            e_cl = re2 + 1e-12
            top1 = torch.amax(e_cl, dim=-1)
            split_rat = 1.0 - top1 / torch.clamp(torch.sum(e_cl, dim=-1), min=1e-12)  # (B, P_c)
            w_cl = torch.sum(e_cl, dim=-1)
            mean_split = torch.sum(w_cl * split_rat, dim=-1) / torch.clamp(torch.sum(w_cl, dim=-1), min=1e-12)
            orth_rat = torch.mean(im2 / (re2 + im2 + s_tap + 1e-12), dim=(1, 2))
        else:
            # Phase-blind magnitude-only ablation (exact same parameter count = 38/round = 76 total!)
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
            feats = torch.stack([f1, f2, f3, f4, f5], dim=-1)

            out = self.fc2(torch.tanh(self.fc1(feats)))
            gate_init = torch.sigmoid(out[..., 0])
            h_init = gate_init.to(h_raw.dtype) * h_raw
            tau_raw = s_tap.squeeze(-1).unsqueeze(-1) * F.softplus(out[..., 1]) + (mag2 * f3 * 0.25)

            top1 = torch.amax(mag2 + 1e-12, dim=-1)
            split_rat = 1.0 - top1 / torch.clamp(torch.sum(mag2 + 1e-12, dim=-1), min=1e-12)
            w_cl = torch.sum(mag2 + 1e-12, dim=-1)
            mean_split = torch.sum(w_cl * split_rat, dim=-1) / torch.clamp(torch.sum(w_cl, dim=-1), min=1e-12)
            orth_rat = torch.zeros_like(mean_split)

        noise_mult = 0.5 + F.softplus(self.w_noise[0] + self.w_noise[1] * mean_split + self.w_noise[2] * orth_rat)
        noise_eff = sigma2 * noise_mult
        temp_llr = 0.25 + F.softplus(self.w_temp[0]).expand(B_sz)
        return h_init.reshape(B_sz, -1), torch.clamp(tau_raw.reshape(B_sz, -1), min=1e-6), noise_eff, temp_llr


def daft_torch(x, c1, c2, inverse=False):
    """Exact match to native daft(x, c1, c2, inverse)."""
    n = x.shape[-1]
    idx = torch.arange(n, device=x.device, dtype=torch.float64)
    if inverse:
        # to_time: exp(-2j*pi*c1*idx^2) * ifft(exp(-2j*pi*c2*idx^2)*x) * sqrt(n)
        c_pre = torch.polar(torch.ones_like(idx), -2.0 * math.pi * c2 * (idx ** 2))
        c_post = torch.polar(torch.ones_like(idx), -2.0 * math.pi * c1 * (idx ** 2))
        return c_post * torch.fft.ifft(c_pre * x, dim=-1) * math.sqrt(n)
    else:
        c_pre = torch.polar(torch.ones_like(idx), 2.0 * math.pi * c1 * (idx ** 2))
        c_post = torch.polar(torch.ones_like(idx), 2.0 * math.pi * c2 * (idx ** 2))
        return c_post * torch.fft.fft(c_pre * x, dim=-1) / math.sqrt(n)


def run_hetero_torch_batch(c1, c2, y_b, pilot_b, l_b, nu_b, h_init_b, noise_b, tau_b, temp_b, prior_b, pd=0.5, iterations=20, damping=0.3):
    """Exact differentiable batched equivalent of run_hetero_np on (B, N), M=48."""
    device = y_b.device
    B_sz, n = y_b.shape
    M = l_b.shape[1]
    k_idx = torch.arange(n, device=device, dtype=torch.float64)  # (N,)

    # Precompute shift indices & CPP/Doppler phase tensor E_mat of shape (B, N, M):
    wrap = k_idx.view(1, n, 1) - l_b.to(torch.float64).view(B_sz, 1, M)  # (B, N, M)
    shift_idx = torch.remainder(wrap.to(torch.long), n)  # (B, N, M)
    cpp_phase = torch.where(wrap < 0, 2.0 * math.pi * c1 * (n * n + 2.0 * n * wrap), torch.zeros_like(wrap))
    dop_phase = 2.0 * math.pi * k_idx.view(1, n, 1) * nu_b.view(B_sz, 1, M) / n
    E_mat = torch.polar(torch.ones_like(dop_phase), cpp_phase + dop_phase)  # (B, N, M) complex128

    # Exact TimePathOps(c).power(h) = h^H P_gram h where entry (m1, m2) = delta_{l1,l2} * dkernel(nu2 - nu1, n):
    same_l = (l_b.unsqueeze(2) == l_b.unsqueeze(1)).to(torch.complex128)  # (B, M, M)
    d_nu = nu_b.unsqueeze(1) - nu_b.unsqueeze(2)  # (B, M, M): entry (m1, m2) = nu[m2] - nu[m1] matching TimePathOps.R!
    d_nu_wrap = torch.remainder(d_nu + 0.5 * n, float(n)) - 0.5 * n
    # Exact closed-form dkernel(t, n) = exp(j*pi*(n-1)*t/n) * sinc(t) / sinc(t/n) (1024x smaller than (B,M,M,N) sum!):
    denom_s = torch.sinc(d_nu_wrap / float(n))
    ratio_s = torch.where(torch.abs(d_nu_wrap) < 1e-12, torch.ones_like(d_nu_wrap), torch.sinc(d_nu_wrap) / denom_s)
    ker = torch.polar(ratio_s, math.pi * (n - 1) * d_nu_wrap / float(n))
    P_gram = same_l * ker

    a_const = math.sqrt(pd / 2.0) * torch.tensor([1 + 1j, 1 - 1j, -1 + 1j, -1 - 1j], device=device, dtype=torch.complex128)
    bits_tbl = torch.tensor([[0.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 1.0]], device=device, dtype=torch.float64)
    sign_tbl = 1.0 - 2.0 * bits_tbl  # (4, 2)

    def logprior_fn(L):
        li = torch.stack([L[:, :n], L[:, n:]], dim=-1)  # (B, N, 2)
        aa = 0.5 * torch.matmul(li, sign_tbl.T)  # (B, N, 4)
        return aa - torch.logsumexp(aa, dim=-1, keepdim=True)

    def moments_fn(L):
        p = torch.exp(logprior_fn(L))
        mu_v = torch.matmul(p.to(torch.complex128), a_const)
        v_v = torch.clamp(pd - (mu_v.real ** 2 + mu_v.imag ** 2), min=0.0)
        return mu_v, v_v

    def marginal_fn(lik, pr):
        post = lik + logprior_fn(pr)
        l0_i = torch.logsumexp(post[:, :, [0, 1]], dim=-1) - torch.logsumexp(post[:, :, [2, 3]], dim=-1)
        l0_q = torch.logsumexp(post[:, :, [0, 2]], dim=-1) - torch.logsumexp(post[:, :, [1, 3]], dim=-1)
        app_v = torch.cat([l0_i, l0_q], dim=-1)
        p = torch.exp(post - torch.logsumexp(post, dim=-1, keepdim=True))
        mu_v = torch.matmul(p.to(torch.complex128), a_const)
        v_v = torch.clamp(pd - (mu_v.real ** 2 + mu_v.imag ** 2), min=0.0)
        return app_v - pr, app_v, mu_v, v_v

    def ch_power(h_vec):
        # Match TimePathOps.power(h) = Re(h^H P_gram h) (verified in smoke gate!)
        ph_g = torch.matmul(P_gram, h_vec.unsqueeze(-1)).squeeze(-1)
        return torch.clamp(torch.sum((h_vec.conj() * ph_g).real, dim=-1), min=0.0)

    mu, v = moments_fn(prior_b)
    x = pilot_b + mu
    Y = daft_torch(y_b, c1, c2, inverse=True)
    tau = torch.clamp(tau_b.to(torch.float64), min=1e-6)
    h = h_init_b.to(torch.complex128)
    vh = tau.clone()
    xb = x.clone()
    hb = h.clone()
    Bb = None
    s_vec = torch.zeros((B_sz, n), device=device, dtype=torch.complex128)
    sv = torch.zeros(B_sz, device=device, dtype=torch.float64)
    bar0 = None
    vp0 = None

    b_arange = torch.arange(B_sz, device=device).view(B_sz, 1, 1)
    for _ in range(iterations):
        xt = daft_torch(x, c1, c2, inverse=True)  # (B, N)
        xt_shifted = xt[b_arange, shift_idx]  # (B, N, M)
        B_mat = xt_shifted * E_mat  # (B, N, M)

        vx = v.mean(dim=-1)
        ex = torch.sum(x.real ** 2 + x.imag ** 2, dim=-1)
        cnorm = ch_power(h)
        sum_vh = torch.sum(vh, dim=-1)
        bar = vx * cnorm + sum_vh * ex / n
        vp = bar + sum_vh * vx
        if bar0 is not None:
            bar = damping * bar + (1.0 - damping) * bar0
            vp = damping * vp + (1.0 - damping) * vp0
        bar0, vp0 = bar, vp

        z = torch.matmul(B_mat, h.unsqueeze(-1)).squeeze(-1)
        ph = z - s_vec * bar.unsqueeze(-1)
        denom = (noise_b + vp).unsqueeze(-1)
        s_vec = damping * (Y - ph) / denom + (1.0 - damping) * s_vec
        sv = damping / (noise_b + vp) + (1.0 - damping) * sv
        xb = damping * x + (1.0 - damping) * xb
        hb = damping * h + (1.0 - damping) * hb
        Bb = B_mat if Bb is None else damping * B_mat + (1.0 - damping) * Bb

        vr = 1.0 / torch.clamp(sv * ch_power(hb), min=1e-12)
        ex_b = torch.sum(xb.real ** 2 + xb.imag ** 2, dim=-1)
        vq = 1.0 / torch.clamp(sv * ex_b, min=1e-12)

        # adjoint_time(hb, s_vec): sum_m hb_m^* * s_vec[(k + l_m)%n] * E_mat[(k + l_m)%n, m]^*
        fwd_idx = torch.remainder(k_idx.view(1, n, 1).to(torch.long) + l_b.view(B_sz, 1, M), n)
        s_fwd = s_vec[b_arange, fwd_idx]  # (B, N, M)
        E_fwd = E_mat[b_arange, fwd_idx, torch.arange(M, device=device).view(1, 1, M)]
        adj_t = torch.sum(s_fwd * E_fwd.conj() * hb.conj().unsqueeze(1), dim=-1)  # (B, N)
        adj = daft_torch(adj_t, c1, c2, inverse=False)

        rx = x + vr.unsqueeze(-1) * (adj - xb * (sv * sum_vh).unsqueeze(-1))
        rh = h + vq.unsqueeze(-1) * (torch.matmul(Bb.conj().transpose(1, 2), s_vec.unsqueeze(-1)).squeeze(-1) - hb * (sv * n * vx).unsqueeze(-1))

        diff = (rx - pilot_b).unsqueeze(-1) - a_const.view(1, 1, 4)
        lik = -(diff.real ** 2 + diff.imag ** 2) / vr.view(B_sz, 1, 1)
        ext, app, mu, v = marginal_fn(lik, prior_b)
        x = pilot_b + mu
        vh = tau * vq.unsqueeze(-1) / (tau + vq.unsqueeze(-1))
        h = tau.to(torch.complex128) * rh / (tau + vq.unsqueeze(-1)).to(torch.complex128)

    return ext * temp_b.unsqueeze(-1), mu, v, h


# ==============================================================================
# Multiprocessing Pre-extraction Worker
# ==============================================================================

def _prep_worker(job):
    frame, snr_centi, betas = job
    C = g3.get_ctx()
    rec = build_frame_pulses(C, frame, snr_centi, betas, rho=250)
    out_pulses = {}
    for b in betas:
        obs_b = dict(rec["obs"], y=rec["y_map"][float(b)])
        c_r0 = extract_2d_clusters_and_refit_r0(C, obs_b)
        out_pulses[float(b)] = c_r0
    return dict(
        frame=frame,
        snr_centi=snr_centi,
        gate_err=rec["gate_err"],
        sigma2=float(rec["obs"]["sigma2"]),
        pilot=rec["obs"]["pilot"],
        y_map=rec["y_map"],
        b_pm=rec["b_pm"],
        truth=rec["truth"],
        l_true=rec["l"],
        k_true=rec["k"],
        g_true=rec["g"],
        off_true=rec["off"],
        r0_map=out_pulses,
    )


def apply_closed_form_collinear(h_raw, cl_map, sigma2, v_mean, ex_norm, c_coh=2.5, c_nb=0.5, c_fl=0.12):
    h_clean = np.zeros_like(h_raw, complex)
    tau_col = np.zeros_like(h_raw, float)
    s_tap = (sigma2 + v_mean) / max(ex_norm, 1.0)
    n_cl = int(np.max(cl_map)) + 1
    splits = []
    weights = []
    for j in range(n_cl):
        m_idx = np.flatnonzero(cl_map == j)
        hj = h_raw[m_idx]
        s2 = np.sum(hj ** 2)
        th = 0.5 * np.angle(s2) if abs(s2) > 1e-12 else 0.0
        rot = np.exp(-1j * th)
        re_p = np.real(hj * rot)
        im_p = np.imag(hj * rot)
        coh = (re_p ** 2) / (re_p ** 2 + c_coh * (im_p ** 2) + s_tap)
        h_clean[m_idx] = re_p * np.exp(1j * th)
        in_nb = np.zeros(len(hj), float)
        in_nb[:-1] += np.maximum(re_p[:-1] * re_p[1:], 0.0)
        in_nb[1:] += np.maximum(re_p[:-1] * re_p[1:], 0.0)
        tau_col[m_idx] = coh * (re_p ** 2 + c_nb * in_nb) + c_fl * s_tap
        e_cl = re_p ** 2 + 1e-12
        splits.append(1.0 - float(np.max(e_cl) / np.sum(e_cl)))
        weights.append(float(np.sum(e_cl)))
    mean_split = float(np.sum(np.array(weights) * np.array(splits)) / max(np.sum(weights), 1e-12))
    return h_clean, np.maximum(tau_col, 1e-6), mean_split


def eval_single_item_all_arms(item, b_val, C, cal_cfg, mod_col_cpu, mod_mag_cpu):
    stage3, ctx = C["stage3"], C["ctx"]
    native = ctx.native
    Channel = native.pilot_front.__globals__["Channel"]
    daft_fn = native.time_refine.__globals__["daft"]
    c1, c2 = float(ctx.system.c1), float(ctx.system.c2)
    y_cur = item["y_map"][float(b_val)]
    pilot = item["pilot"]
    sigma2 = item["sigma2"]
    b_pm = item["b_pm"]
    truth = item["truth"]
    n = len(y_cur)
    sc_fn = lambda dec_val: int(stage3.e1.gd.score(ctx, dec_val, truth)) > 0

    out = {}

    # 1) ora_true48_fix: true continuous 6-tap/path pulse weights
    l_list, nu_list, h_list = [], [], []
    for li, ki, gi, oi in zip(item["l_true"], item["k_true"], item["g_true"], item["off_true"]):
        tau_t = float(li) + float(oi)
        l0 = int(math.floor(tau_t))
        offs = np.arange(-2, 4)
        wj = g3.pulse_kernel(tau_t - (l0 + offs), float(b_val))
        for m_off, wm in zip(offs, wj):
            l_list.append((l0 + int(m_off)) % n)
            nu_list.append(float(ki))
            h_list.append(complex(gi * wm))
    ch_ora = Channel(n, c1, c2, np.array(l_list, int), np.array(nu_list, float), np.array(h_list, complex))
    prior = np.zeros(2 * n, float)
    gmi_r0_ora = 0.0
    for r_it in range(2):
        o_ora = native.scalar_joint(y_cur, pilot, ch_ora, sigma2 * 1.15, pd=0.5, prior=prior, iterations=20, gain_mode="fixed")
        if r_it == 0:
            gmi_r0_ora = signed_gmi_qpsk(o_ora["extrinsic"], b_pm)
        dec_ora = native.decoder_messages(ctx.code, np.clip(o_ora["extrinsic"], -20, 20), maxiter=50)
        prior = np.clip(dec_ora["raw_check_extrinsic"], -20, 20)
    out["ora_true48_fix"] = dict(fer=int(sc_fn(dec_ora["decoded"])), gmi_r0=gmi_r0_ora, gmi_r1=signed_gmi_qpsk(o_ora["extrinsic"], b_pm))

    r0 = item["r0_map"][float(b_val)]
    l_arr = r0["l_arr"]
    cl_map = r0["cl_map"]

    for arm in ["free6_iso_cal", "full_pcsbl_cal", "split_noise_only", "zero_train_collinear_cal", "mlp_mag_unfold", "collinear_unfold"]:
        clusters = [ (c[0], c[1], c[2]) for c in r0["clusters"] ]
        mu = r0["mu0"].copy()
        v = r0["v0"].copy()
        prior = r0["prior0"].copy()
        vh_prev = np.full(len(l_arr), 1.0 / len(l_arr), float)
        gmi_r0 = 0.0

        for r_it in range(2):
            if r_it == 0:
                nu_cl = r0["nu_cl"].copy()
                h_raw = r0["h_raw"].copy()
            else:
                nu_cl, h_raw = refit_clusters(native, y_cur, pilot, mu, v, clusters, sigma2 * 1.35, c1, c2)
                clusters = [(clusters[j][0], float(nu_cl[j]), clusters[j][2]) for j in range(len(clusters))]
            nu_taps = nu_cl[cl_map]
            xt = daft_fn(pilot + mu, c1, c2, True)
            ex_norm = float(np.vdot(xt, xt).real)
            v_mean = float(np.mean(v))

            if arm == "free6_iso_cal":
                tau_v = np.full(len(l_arr), 1.0 / len(l_arr), float)
                o = run_hetero_np(native, c1, c2, y_cur, pilot, l_arr, nu_taps, h_raw,
                                  sigma2 * cal_cfg["k_iso"], tau_v, temp_llr=1.0, prior=prior)
            elif arm == "full_pcsbl_cal":
                # Full Fang TSP 2015 PC-SBL: posterior 2nd moment e_m = |h_m|^2 + vh_m + coupled neighbor precision!
                # Run 2 inner EM updates of tau_pc with posterior variance:
                s_tap = (sigma2 + v_mean) / max(ex_norm, 1.0)
                vh_est = np.full(len(l_arr), s_tap, float) if r_it == 0 else vh_prev
                e_sec = np.abs(h_raw) ** 2 + vh_est
                tau_pc = np.zeros_like(e_sec)
                b_pc = cal_cfg["beta_pcsbl"]
                for j in range(8):
                    m_idx = np.flatnonzero(cl_map == j)
                    ej = e_sec[m_idx]
                    epad = np.pad(ej, (1, 1), mode="constant")
                    # Fang Eq. (20): alpha_i = d / (e_i + beta*(e_{i-1}+e_{i+1})), prior variance = 1 / alpha_i
                    tau_pc[m_idx] = (ej + b_pc * (epad[:-2] + epad[2:])) / (1.0 + 2.0 * b_pc) + 0.05 * s_tap
                o = run_hetero_np(native, c1, c2, y_cur, pilot, l_arr, nu_taps, h_raw,
                                  sigma2 * cal_cfg["k_pcsbl"], tau_pc, temp_llr=1.0, prior=prior)
                vh_prev = o["vh"].copy()
            elif arm == "split_noise_only":
                # Isotropic prior + per-frame split-ratio adaptive noise ONLY (no collinear projection/prior!)
                _, _, mean_sp = apply_closed_form_collinear(h_raw, cl_map, sigma2, v_mean, ex_norm)
                sig_sp = sigma2 * (cal_cfg["k_sp_base"] + cal_cfg["k_sp_slope"] * mean_sp)
                tau_v = np.full(len(l_arr), 1.0 / len(l_arr), float)
                o = run_hetero_np(native, c1, c2, y_cur, pilot, l_arr, nu_taps, h_raw,
                                  sig_sp, tau_v, temp_llr=1.0, prior=prior)
            elif arm == "zero_train_collinear_cal":
                h_cl, tau_cl, _ = apply_closed_form_collinear(h_raw, cl_map, sigma2, v_mean, ex_norm)
                o = run_hetero_np(native, c1, c2, y_cur, pilot, l_arr, nu_taps, h_cl,
                                  sigma2 * cal_cfg["k_zt_col"], tau_cl, temp_llr=cal_cfg["t_zt_col"], prior=prior)
            elif arm in ("mlp_mag_unfold", "collinear_unfold"):
                mod = mod_col_cpu[r_it] if arm == "collinear_unfold" else mod_mag_cpu[r_it]
                with torch.no_grad():
                    hr_t = torch.tensor(h_raw.reshape(1, 8, 6), dtype=torch.complex128)
                    s2_t = torch.tensor([sigma2], dtype=torch.float64)
                    vm_t = torch.tensor([v_mean], dtype=torch.float64)
                    ex_t = torch.tensor([ex_norm], dtype=torch.float64)
                    hi_t, tv_t, ne_t, tl_t = mod(hr_t, s2_t, vm_t, ex_t)
                o = run_hetero_np(native, c1, c2, y_cur, pilot, l_arr, nu_taps,
                                  hi_t[0].numpy(), float(ne_t[0].item()), tv_t[0].numpy(),
                                  temp_llr=float(tl_t[0].item()), prior=prior)

            if r_it == 0:
                gmi_r0 = signed_gmi_qpsk(o["extrinsic"], b_pm)
            dec = native.decoder_messages(ctx.code, np.clip(o["extrinsic"], -20, 20), maxiter=50)
            prior = np.clip(dec["raw_check_extrinsic"], -20, 20)
            mu, v, _ = native.moments(np.clip(dec["raw_app"], -20, 20), 0.5)

        out[arm] = dict(fer=int(sc_fn(dec["decoded"])), gmi_r0=gmi_r0, gmi_r1=signed_gmi_qpsk(o["extrinsic"], b_pm))
    return out


def _eval_worker_tuple(args):
    item, b_val, cal_cfg, col_sd, mag_sd = args
    C = g3.get_ctx()
    mod_col = [PriorUnfoldRoundModule("collinear").double(), PriorUnfoldRoundModule("collinear").double()]
    mod_mag = [PriorUnfoldRoundModule("mag").double(), PriorUnfoldRoundModule("mag").double()]
    for r in range(2):
        mod_col[r].load_state_dict(col_sd[r]); mod_col[r].eval()
        mod_mag[r].load_state_dict(mag_sd[r]); mod_mag[r].eval()
    res = eval_single_item_all_arms(item, b_val, C, cal_cfg, mod_col, mod_mag)
    return item["frame"], item["snr_centi"], float(b_val), res


def _pack_r1_worker(args):
    it, r0_sd, mode = args
    C = g3.get_ctx()
    ctx = C["ctx"]
    native = ctx.native
    daft_fn = native.time_refine.__globals__["daft"]
    c1, c2 = float(ctx.system.c1), float(ctx.system.c2)
    r0_mod = PriorUnfoldRoundModule(mode=mode).double()
    r0_mod.load_state_dict(r0_sd)
    r0_mod.eval()

    b_use = 0.0 if (it["frame"] % 2 == 0) else 0.25
    y_cur = it["y_map"][b_use]
    pilot = it["pilot"]
    sigma2 = it["sigma2"]
    r0 = it["r0_map"][b_use]
    l_arr = r0["l_arr"]
    cl_map = r0["cl_map"]
    with torch.no_grad():
        xt0 = daft_fn(pilot + r0["mu0"], c1, c2, True)
        hi0, tv0, ne0, tl0 = r0_mod(
            torch.tensor(r0["h_raw"].reshape(1, 8, 6), dtype=torch.complex128),
            torch.tensor([sigma2], dtype=torch.float64),
            torch.tensor([float(np.mean(r0["v0"]))], dtype=torch.float64),
            torch.tensor([float(np.vdot(xt0, xt0).real)], dtype=torch.float64),
        )
    o0 = run_hetero_np(native, c1, c2, y_cur, pilot, l_arr, r0["nu_cl"][cl_map],
                       hi0[0].numpy(), float(ne0[0].item()), tv0[0].numpy(),
                       temp_llr=float(tl0[0].item()), prior=r0["prior0"])
    dec0 = native.decoder_messages(ctx.code, np.clip(o0["extrinsic"], -20, 20), maxiter=50)
    prior = np.clip(dec0["raw_check_extrinsic"], -20, 20)
    mu, v, _ = native.moments(np.clip(dec0["raw_app"], -20, 20), 0.5)
    nu_cl, h_raw = refit_clusters(native, y_cur, pilot, mu, v, r0["clusters"], sigma2 * 1.35, c1, c2)
    xt = daft_fn(pilot + mu, c1, c2, True)
    return dict(
        y=y_cur, pilot=pilot, l_arr=l_arr, nu_taps=nu_cl[cl_map],
        h_raw=h_raw.reshape(8, 6), sigma2=sigma2, v_mean=float(np.mean(v)),
        ex_norm=float(np.vdot(xt, xt).real), prior=prior, b_pm=it["b_pm"],
    )


def train_unfolded_two_rounds(C, train_items, dev_items, mode="collinear", device="cpu", epochs_r0=16, epochs_r1=14, batch_size=100, workers=24, seed=20261123):
    torch.set_num_threads(24)
    torch.manual_seed(seed + (0 if mode == "collinear" else 100))
    ctx = C["ctx"]
    native = ctx.native
    daft_fn = native.time_refine.__globals__["daft"]
    c1, c2 = float(ctx.system.c1), float(ctx.system.c2)

    def pack_r0_samples(items):
        samples = []
        for it in items:
            b_use = 0.0 if (it["frame"] % 2 == 0) else 0.25
            y_cur = it["y_map"][b_use]
            pilot = it["pilot"]
            sigma2 = it["sigma2"]
            r0 = it["r0_map"][b_use]
            xt = daft_fn(pilot + r0["mu0"], c1, c2, True)
            samples.append(dict(
                y=y_cur, pilot=pilot, l_arr=r0["l_arr"], nu_taps=r0["nu_cl"][r0["cl_map"]],
                h_raw=r0["h_raw"].reshape(8, 6), sigma2=sigma2, v_mean=float(np.mean(r0["v0"])),
                ex_norm=float(np.vdot(xt, xt).real), prior=r0["prior0"], b_pm=it["b_pm"],
            ))
        return samples

    def to_tensors(s_list, dev_t):
        return dict(
            y=torch.tensor(np.stack([s["y"] for s in s_list]), dtype=torch.complex128, device=dev_t),
            pilot=torch.tensor(np.stack([s["pilot"] for s in s_list]), dtype=torch.complex128, device=dev_t),
            l_arr=torch.tensor(np.stack([s["l_arr"] for s in s_list]), dtype=torch.long, device=dev_t),
            nu_taps=torch.tensor(np.stack([s["nu_taps"] for s in s_list]), dtype=torch.float64, device=dev_t),
            h_raw=torch.tensor(np.stack([s["h_raw"] for s in s_list]), dtype=torch.complex128, device=dev_t),
            sigma2=torch.tensor([s["sigma2"] for s in s_list], dtype=torch.float64, device=dev_t),
            v_mean=torch.tensor([s["v_mean"] for s in s_list], dtype=torch.float64, device=dev_t),
            ex_norm=torch.tensor([s["ex_norm"] for s in s_list], dtype=torch.float64, device=dev_t),
            prior=torch.tensor(np.stack([s["prior"] for s in s_list]), dtype=torch.float64, device=dev_t),
            b_pm=torch.tensor(np.stack([s["b_pm"] for s in s_list]), dtype=torch.float64, device=dev_t),
        )

    def fit_one_round(tr_s, dv_s, n_ep):
        mod = PriorUnfoldRoundModule(mode=mode).double().to(device)
        opt = torch.optim.Adam(mod.parameters(), lr=0.04)
        T_tr = to_tensors(tr_s, device)
        T_dv = to_tensors(dv_s, device)
        N_tr = len(tr_s)
        best_dv_loss = 1e30
        best_sd = {k: v.detach().cpu().clone() for k, v in mod.state_dict().items()}
        rng_p = np.random.default_rng(seed)

        for ep in range(n_ep):
            mod.train()
            perm = torch.tensor(rng_p.permutation(N_tr), dtype=torch.long, device=device)
            for st in range(0, N_tr, batch_size):
                idx = perm[st:st + batch_size]
                opt.zero_grad()
                hi, tv, ne, tl = mod(T_tr["h_raw"][idx], T_tr["sigma2"][idx], T_tr["v_mean"][idx], T_tr["ex_norm"][idx])
                ext, _, _, _ = run_hetero_torch_batch(
                    c1, c2, T_tr["y"][idx], T_tr["pilot"][idx], T_tr["l_arr"][idx], T_tr["nu_taps"][idx],
                    hi, ne, tv, tl, T_tr["prior"][idx], iterations=20
                )
                # Exact signed-bit BCE loss (= ln(2) * (1 - GMI/2)):
                loss = F.softplus(-T_tr["b_pm"][idx] * torch.clamp(ext, -25.0, 25.0)).mean()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(mod.parameters(), 2.0)
                opt.step()

            mod.eval()
            with torch.no_grad():
                hi_v, tv_v, ne_v, tl_v = mod(T_dv["h_raw"], T_dv["sigma2"], T_dv["v_mean"], T_dv["ex_norm"])
                ext_v, _, _, _ = run_hetero_torch_batch(
                    c1, c2, T_dv["y"], T_dv["pilot"], T_dv["l_arr"], T_dv["nu_taps"],
                    hi_v, ne_v, tv_v, tl_v, T_dv["prior"], iterations=20
                )
                dv_loss = float(F.softplus(-T_dv["b_pm"] * torch.clamp(ext_v, -25.0, 25.0)).mean().item())
                if dv_loss < best_dv_loss:
                    best_dv_loss = dv_loss
                    best_sd = {k: v.detach().cpu().clone() for k, v in mod.state_dict().items()}

        mod_cpu = PriorUnfoldRoundModule(mode=mode).double()
        mod_cpu.load_state_dict(best_sd)
        mod_cpu.eval()
        return mod_cpu, best_sd, best_dv_loss

    tr0 = pack_r0_samples(train_items)
    dv0 = pack_r0_samples(dev_items)
    m0_cpu, sd0, loss0 = fit_one_round(tr0, dv0, epochs_r0)

    with get_context("spawn").Pool(workers) as pool:
        tr1 = list(pool.map(_pack_r1_worker, [(it, sd0, mode) for it in train_items]))
        dv1 = list(pool.map(_pack_r1_worker, [(it, sd0, mode) for it in dev_items]))
    m1_cpu, sd1, loss1 = fit_one_round(tr1, dv1, epochs_r1)
    n_params = sum(p.numel() for p in m0_cpu.parameters()) + sum(p.numel() for p in m1_cpu.parameters())
    print(f"[{mode}] Trained {n_params} params | best dev BCE R0={loss0:.5f}, R1={loss1:.5f}", flush=True)
    return [sd0, sd1], n_params, [loss0, loss1]


def calibrate_classical_on_dev(C, dev_items):
    """Calibrate scalar multipliers strictly on dev frames 43500..43579."""
    ctx = C["ctx"]
    native = ctx.native
    daft_fn = native.time_refine.__globals__["daft"]
    c1, c2 = float(ctx.system.c1), float(ctx.system.c2)

    # 1) k_iso for free6_iso_cal
    best_iso = (1.35, -1e9)
    for k_m in [1.15, 1.35, 1.60, 1.90]:
        gmis = []
        for it in dev_items[:40]:
            b_u = 0.0 if (it["frame"] % 2 == 0) else 0.25
            r0 = it["r0_map"][b_u]
            o = run_hetero_np(native, c1, c2, it["y_map"][b_u], it["pilot"], r0["l_arr"],
                              r0["nu_cl"][r0["cl_map"]], r0["h_raw"], it["sigma2"] * k_m,
                              np.full(48, 1.0 / 48.0), temp_llr=1.0, prior=r0["prior0"])
            gmis.append(signed_gmi_qpsk(o["extrinsic"], it["b_pm"]))
        sc = float(np.mean(gmis))
        if sc > best_iso[1]:
            best_iso = (k_m, sc)

    # 2) (beta_pcsbl, k_pcsbl) for full_pcsbl_cal
    best_pc = ((0.5, 1.35), -1e9)
    for b_pc in [0.25, 0.5, 1.0]:
        for k_m in [1.2, 1.5, 1.9]:
            gmis = []
            for it in dev_items[:40]:
                b_u = 0.0 if (it["frame"] % 2 == 0) else 0.25
                r0 = it["r0_map"][b_u]
                xt = daft_fn(it["pilot"] + r0["mu0"], c1, c2, True)
                s_tap = (it["sigma2"] + float(np.mean(r0["v0"]))) / max(float(np.vdot(xt, xt).real), 1.0)
                e_sec = np.abs(r0["h_raw"]) ** 2 + s_tap
                tau_pc = np.zeros_like(e_sec)
                for j in range(8):
                    mi = np.flatnonzero(r0["cl_map"] == j)
                    epad = np.pad(e_sec[mi], (1, 1), mode="constant")
                    tau_pc[mi] = (e_sec[mi] + b_pc * (epad[:-2] + epad[2:])) / (1.0 + 2.0 * b_pc) + 0.05 * s_tap
                o = run_hetero_np(native, c1, c2, it["y_map"][b_u], it["pilot"], r0["l_arr"],
                                  r0["nu_cl"][r0["cl_map"]], r0["h_raw"], it["sigma2"] * k_m,
                                  tau_pc, temp_llr=1.0, prior=r0["prior0"])
                gmis.append(signed_gmi_qpsk(o["extrinsic"], it["b_pm"]))
            sc = float(np.mean(gmis))
            if sc > best_pc[1]:
                best_pc = ((b_pc, k_m), sc)

    # 3) (k_zt_col, t_zt_col) for zero_train_collinear_cal
    best_zt = ((1.35, 1.0), -1e9)
    for k_m in [1.15, 1.35, 1.65]:
        for t_m in [0.85, 1.0, 1.15]:
            gmis = []
            for it in dev_items[:40]:
                b_u = 0.0 if (it["frame"] % 2 == 0) else 0.25
                r0 = it["r0_map"][b_u]
                xt = daft_fn(it["pilot"] + r0["mu0"], c1, c2, True)
                hcl, tcl, _ = apply_closed_form_collinear(r0["h_raw"], r0["cl_map"], it["sigma2"],
                                                          float(np.mean(r0["v0"])), float(np.vdot(xt, xt).real))
                o = run_hetero_np(native, c1, c2, it["y_map"][b_u], it["pilot"], r0["l_arr"],
                                  r0["nu_cl"][r0["cl_map"]], hcl, it["sigma2"] * k_m,
                                  tcl, temp_llr=t_m, prior=r0["prior0"])
                gmis.append(signed_gmi_qpsk(o["extrinsic"], it["b_pm"]))
            sc = float(np.mean(gmis))
            if sc > best_zt[1]:
                best_zt = ((k_m, t_m), sc)

    return dict(
        k_iso=best_iso[0],
        beta_pcsbl=best_pc[0][0],
        k_pcsbl=best_pc[0][1],
        k_sp_base=1.10,
        k_sp_slope=0.90,
        k_zt_col=best_zt[0][0],
        t_zt_col=best_zt[0][1],
    )


def run_smoke():
    C = g3.get_ctx()
    ctx = C["ctx"]
    native = ctx.native
    c1, c2 = float(ctx.system.c1), float(ctx.system.c2)
    it = _prep_worker((42990, 600, [0.0, 0.35]))
    assert it["gate_err"] < 1e-11, f"Gate err: {it['gate_err']}"

    # Verify exact parity between run_hetero_np and run_hetero_torch_batch!
    r0 = it["r0_map"][0.0]
    tau_test = np.linspace(0.01, 0.05, 48)
    o_np = run_hetero_np(native, c1, c2, it["y_map"][0.0], it["pilot"], r0["l_arr"],
                         r0["nu_cl"][r0["cl_map"]], r0["h_raw"], it["sigma2"] * 1.35,
                         tau_test, temp_llr=1.0, prior=r0["prior0"], iterations=20)
    ext_th, _, _, _ = run_hetero_torch_batch(
        c1, c2,
        torch.tensor(it["y_map"][0.0][None, :], dtype=torch.complex128),
        torch.tensor(it["pilot"][None, :], dtype=torch.complex128),
        torch.tensor(r0["l_arr"][None, :], dtype=torch.long),
        torch.tensor(r0["nu_cl"][r0["cl_map"]][None, :], dtype=torch.float64),
        torch.tensor(r0["h_raw"][None, :], dtype=torch.complex128),
        torch.tensor([it["sigma2"] * 1.35], dtype=torch.float64),
        torch.tensor(tau_test[None, :], dtype=torch.float64),
        torch.tensor([1.0], dtype=torch.float64),
        torch.tensor(r0["prior0"][None, :], dtype=torch.float64),
        iterations=20,
    )
    max_diff = float(np.max(np.abs(o_np["extrinsic"] - ext_th[0].numpy())))
    print(f"SMOKE PASS: gate_err={it['gate_err']:.2e}, PyTorch-NumPy max LLR diff={max_diff:.2e}")
    assert max_diff < 1e-7, f"PyTorch-NumPy parity failed: {max_diff}"


def run_full(out_dir, workers=24):
    t0 = time.time()
    out_p = Path(out_dir)
    out_p.mkdir(parents=True, exist_ok=True)
    run_smoke()
    C = g3.get_ctx()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Running g01 L2 on device={device}, workers={workers}", flush=True)

    # 1) Pre-extract clusters in parallel across train (43000..43399), dev (43500..43579), and unseen test (47000..47239)
    tr_jobs = [(f, 600, [0.0 if f % 2 == 0 else 0.25]) for f in range(43000, 43400)]
    dv_jobs = [(f, 600, [0.0 if f % 2 == 0 else 0.25]) for f in range(43500, 43580)]
    te_600_jobs = [(f, 600, [0.0, 0.15, 0.35]) for f in range(47000, 47240)]
    te_550_jobs = [(f, 550, [0.0, 0.35]) for f in range(47000, 47160)]
    te_700_jobs = [(f, 700, [0.0, 0.35]) for f in range(47000, 47160)]

    with get_context("spawn").Pool(workers) as pool:
        train_items = list(pool.map(_prep_worker, tr_jobs))
        dev_items = list(pool.map(_prep_worker, dv_jobs))
        te_600 = list(pool.map(_prep_worker, te_600_jobs))
        te_550 = list(pool.map(_prep_worker, te_550_jobs))
        te_700 = list(pool.map(_prep_worker, te_700_jobs))
    print(f"Pre-extraction done in {time.time() - t0:.1f}s", flush=True)

    # 2) Calibrate classical scalar parameters on dev_items ONLY
    cal_cfg = calibrate_classical_on_dev(C, dev_items)
    print(f"Dev-calibrated classical scalars: {cal_cfg}", flush=True)

    # 3) Train collinear_unfold (76 params) and mlp_mag_unfold (76 params) on train_items ONLY
    t_tr = time.time()
    col_sd, n_p_col, col_dv_loss = train_unfolded_two_rounds(C, train_items, dev_items, mode="collinear", device=device)
    mag_sd, n_p_mag, mag_dv_loss = train_unfolded_two_rounds(C, train_items, dev_items, mode="mag", device=device)
    train_sec = time.time() - t_tr
    assert n_p_col == n_p_mag <= 80

    # 4) Evaluate all 7 arms on unseen test sets in parallel
    eval_tasks = []
    for it in te_600:
        for b_v in [0.0, 0.15, 0.35]:
            eval_tasks.append((it, b_v, cal_cfg, col_sd, mag_sd))
    for it in te_550:
        for b_v in [0.0, 0.35]:
            eval_tasks.append((it, b_v, cal_cfg, col_sd, mag_sd))
    for it in te_700:
        for b_v in [0.0, 0.35]:
            eval_tasks.append((it, b_v, cal_cfg, col_sd, mag_sd))

    with get_context("spawn").Pool(workers) as pool:
        raw_eval = list(pool.map(_eval_worker_tuple, eval_tasks))

    # Aggregate results & compute pre-registered boolean verdicts
    arms = ["ora_true48_fix", "free6_iso_cal", "full_pcsbl_cal", "split_noise_only",
            "zero_train_collinear_cal", "mlp_mag_unfold", "collinear_unfold"]
    cells = {}
    by_cell = {}
    for fr, snr_c, b_v, res in raw_eval:
        key = f"snr{snr_c}_beta{b_v:.2f}"
        by_cell.setdefault(key, []).append((fr, res))

    rng = np.random.default_rng(20261123)
    for key, rows in sorted(by_cell.items()):
        rows.sort(key=lambda x: x[0])
        cells[key] = dict(
            n_frames=len(rows),
            fer={a: float(np.mean([r[1][a]["fer"] for r in rows])) for a in arms},
            gmi_r0={a: float(np.mean([r[1][a]["gmi_r0"] for r in rows])) for a in arms},
            gmi_r1={a: float(np.mean([r[1][a]["gmi_r1"] for r in rows])) for a in arms},
        )

    # Pooled contrasts at SNR=6.0 dB
    r_sinc6 = [r[1] for r in sorted(by_cell["snr600_beta0.00"], key=lambda x: x[0])]
    r_rc15_6 = [r[1] for r in sorted(by_cell["snr600_beta0.15"], key=lambda x: x[0])]
    r_rc35_6 = [r[1] for r in sorted(by_cell["snr600_beta0.35"], key=lambda x: x[0])]
    pool_2p = r_sinc6 + r_rc35_6
    pool_3p = r_sinc6 + r_rc15_6 + r_rc35_6

    ci_col_vs_iso_2p = bootstrap_diff([x["collinear_unfold"]["fer"] for x in pool_2p],
                                      [x["free6_iso_cal"]["fer"] for x in pool_2p], rng)
    ci_col_vs_mag_2p = bootstrap_diff([x["collinear_unfold"]["fer"] for x in pool_2p],
                                      [x["mlp_mag_unfold"]["fer"] for x in pool_2p], rng)
    ci_col_vs_pc_2p = bootstrap_diff([x["collinear_unfold"]["fer"] for x in pool_2p],
                                     [x["full_pcsbl_cal"]["fer"] for x in pool_2p], rng)
    ci_col_vs_sp_2p = bootstrap_diff([x["collinear_unfold"]["fer"] for x in pool_2p],
                                     [x["split_noise_only"]["fer"] for x in pool_2p], rng)
    ci_col_vs_iso_3p = bootstrap_diff([x["collinear_unfold"]["fer"] for x in pool_3p],
                                      [x["free6_iso_cal"]["fer"] for x in pool_3p], rng)
    ci_col_vs_zt_fer = bootstrap_diff([x["collinear_unfold"]["fer"] for x in pool_3p],
                                      [x["zero_train_collinear_cal"]["fer"] for x in pool_3p], rng)
    ci_col_vs_zt_gmi = bootstrap_diff([0.5 * (x["collinear_unfold"]["gmi_r0"] + x["collinear_unfold"]["gmi_r1"]) for x in pool_3p],
                                      [0.5 * (x["zero_train_collinear_cal"]["gmi_r0"] + x["zero_train_collinear_cal"]["gmi_r1"]) for x in pool_3p], rng)

    gate_headroom = (cells["snr600_beta0.00"]["fer"]["free6_iso_cal"] - cells["snr600_beta0.00"]["fer"]["ora_true48_fix"]) >= 0.20
    dir_beats = (
        ci_col_vs_iso_2p["ci95"][1] < 0.0
        and ci_col_vs_mag_2p["ci95"][1] < 0.0
        and ci_col_vs_pc_2p["point"] < 0.0
        and ci_col_vs_sp_2p["point"] < 0.0
    )
    quant_gain = (-ci_col_vs_iso_3p["point"]) >= 0.10
    unfold_beats_zt = ((-ci_col_vs_zt_fer["point"]) >= 0.04) or (ci_col_vs_zt_gmi["point"] >= 0.03 and ci_col_vs_zt_gmi["ci95"][0] > 0.0)

    verdicts = dict(
        gate_headroom=bool(gate_headroom),
        dir_beats_baselines_and_mag_mlp=bool(dir_beats),
        quant_fer_or_gmi_gain=bool(quant_gain),
        unfold_beats_zerotrain_by_4pp=bool(unfold_beats_zt),
        PASS=bool(gate_headroom and dir_beats and quant_gain and unfold_beats_zt),
    )

    summary = dict(
        _argv=sys.argv,
        _config=dict(
            card="I-20261123-g01",
            train_frames=[43000, 43400],
            dev_frames=[43500, 43580],
            test_frames_6dB=[47000, 47240],
            test_frames_55_70=[47000, 47160],
            n_params_collinear=n_p_col,
            n_params_mag=n_p_mag,
            cal_cfg=cal_cfg,
            device=device,
            workers=workers,
            train_seconds=round(train_sec, 2),
            wall_seconds=round(time.time() - t0, 2),
        ),
        dev_bce_loss=dict(collinear=col_dv_loss, mag=mag_dv_loss),
        cells=cells,
        contrasts_6dB=dict(
            col_minus_iso_2pulse_fer=ci_col_vs_iso_2p,
            col_minus_mag_2pulse_fer=ci_col_vs_mag_2p,
            col_minus_pcsbl_2pulse_fer=ci_col_vs_pc_2p,
            col_minus_split_2pulse_fer=ci_col_vs_sp_2p,
            col_minus_iso_3pulse_fer=ci_col_vs_iso_3p,
            col_minus_zerotrain_3pulse_fer=ci_col_vs_zt_fer,
            col_minus_zerotrain_3pulse_gmi=ci_col_vs_zt_gmi,
        ),
        verdicts=verdicts,
    )
    (out_p / "summary_g01.json").write_text(json.dumps(summary, indent=2))
    print("DONE g01 verdicts:", json.dumps(verdicts), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["smoke", "run"])
    ap.add_argument("--out", default="ideas/l2/out_g_r5_b1")
    ap.add_argument("--workers", type=int, default=24)
    args = ap.parse_args()
    if args.mode == "smoke":
        run_smoke()
    else:
        run_full(args.out, workers=args.workers)
