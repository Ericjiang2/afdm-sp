"""
afdm_layers.py — PyTorch nn.Module equivalents of the AFDM deep-unfolding layers.

All modules are differentiable and work inside torch.autograd.
No numpy channel physics here — import afdm_env for that.

Migration note (TF → PyTorch):
  - keras.layers.Layer.add_weight  → nn.Parameter
  - tf.constant in __init__        → self.register_buffer(...)
  - tf.gather(x, idx, axis=1)      → x[:, idx]  (advanced indexing)
  - tf.linalg.solve(A, b)          → torch.linalg.solve(A, b)
  - tf.linalg.matvec(M, v)         → torch.bmm(M, v.unsqueeze(-1)).squeeze(-1)
  - tf.math.softplus               → torch.nn.functional.softplus
  - tf.concat([a,b], axis=-1)      → torch.cat([a,b], dim=-1)
"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


# ─────────────────────────────────────────────────────────────────────────────
#  Utility
# ─────────────────────────────────────────────────────────────────────────────

class SliceLayer(nn.Module):
    """Serialization-safe slicing module."""
    def __init__(self, start: int, end: int):
        super().__init__()
        self.start = start
        self.end   = end

    def forward(self, x):
        return x[:, self.start:self.end]


# ─────────────────────────────────────────────────────────────────────────────
#  Differentiable physics layers
# ─────────────────────────────────────────────────────────────────────────────

class Grid2DTo1DLayer(nn.Module):
    """
    Differentiable inverse of map_1d_to_2d_grid.

    Maps 2D delay-Doppler grid (L_max x W) -> 1D tap vector (N,).
    Overlapping cells averaged via precomputed scatter matrix S (stored as S^T).

    Inputs:  (batch, 2*L*W)  — [Re_flat, Im_flat]
    Outputs: (batch, 2*N)    — [Re, Im]
    """
    def __init__(self, N, K_factor, k_max, L_max, W, pad_size):
        super().__init__()
        self.N = N; self.L_max = L_max; self.W = W
        offsets   = np.arange(-(k_max + pad_size), k_max + pad_size + 1)
        centers   = np.arange(L_max) * K_factor
        delta_idx = (centers[:, None] + offsets[None, :]) % N
        count = np.zeros(N, dtype=np.float32)
        np.add.at(count, delta_idx.ravel(), 1.0)
        count = np.maximum(count, 1.0)
        S = np.zeros((N, L_max * W), dtype=np.float32)
        for cell_i, d in enumerate(delta_idx.ravel()):
            S[d, cell_i] = 1.0 / count[d]
        self.register_buffer('S_T', torch.from_numpy(S.T))   # (L*W, N)

    def forward(self, h_2d_flat):
        LW = self.L_max * self.W
        h_re = h_2d_flat[:, :LW];  h_im = h_2d_flat[:, LW:]
        return torch.cat([h_re @ self.S_T, h_im @ self.S_T], dim=-1)


class DiffRechirpLayer(nn.Module):
    """
    Differentiable re-chirp: h[d] *= exp(-j2pi*c2*(m_obs^2-m0^2)),
    m_obs = (m0+d) % N.

    Inputs/Outputs: (batch, 2*N) [Re, Im]
    """
    def __init__(self, N, c2, m0):
        super().__init__()
        self.N = N
        delta_arr = np.arange(N, dtype=np.float64)
        m_obs_arr = (m0 + delta_arr) % N
        factor    = np.exp(-1j * 2 * np.pi * c2 * (m_obs_arr**2 - float(m0)**2))
        self.register_buffer('fr', torch.from_numpy(np.real(factor).astype(np.float32)))
        self.register_buffer('fi', torch.from_numpy(np.imag(factor).astype(np.float32)))

    def forward(self, h_flat):
        N = self.N
        hr = h_flat[:, :N];  hi = h_flat[:, N:]
        return torch.cat([hr * self.fr - hi * self.fi,
                          hr * self.fi + hi * self.fr], dim=-1)


class DiffReconstructLayer(nn.Module):
    """
    Differentiable H_eff reconstruction from re-chirped h_tap.
    H_est[r,c] = phase[r,c] * h_tap[(r-c) % N]  (bijection per entry).

    Inputs:  (batch, 2*N)   — [Re, Im] h_tap
    Outputs: (batch, 2*N^2) — [Re(H_flat), Im(H_flat)]
    """
    def __init__(self, N, c1, c2, m0, l_max_cap, k_max_cap):
        super().__init__()
        self.N = N
        K_factor = max(int(round(2 * N * c1)), 1)
        L_max    = min(N // K_factor, l_max_cap + 1)
        centers  = np.arange(L_max) * K_factor
        diffs    = np.abs(np.arange(N)[:, None] - centers[None, :])
        home_row = np.argmin(np.minimum(diffs, N - diffs), axis=1)
        row_g, col_g = np.meshgrid(np.arange(N, dtype=np.float64),
                                   np.arange(N, dtype=np.float64), indexing='ij')
        delta_g = (row_g - col_g).astype(int) % N
        l_g     = home_row[delta_g]
        m_obs_g = (m0 + delta_g) % N
        pa = (c2 * (row_g**2 - col_g**2
                    - m_obs_g.astype(np.float64)**2 + float(m0)**2)
              + l_g.astype(np.float64) * (float(m0) - col_g) / N)
        pm = np.exp(1j * 2 * np.pi * pa).astype(np.complex64)
        self.register_buffer('delta_flat',
            torch.from_numpy(delta_g.ravel().astype(np.int64)))
        self.register_buffer('pr', torch.from_numpy(np.real(pm).ravel().astype(np.float32)))
        self.register_buffer('pi_', torch.from_numpy(np.imag(pm).ravel().astype(np.float32)))

    def forward(self, h_flat):
        N = self.N
        hr = h_flat[:, :N];  hi = h_flat[:, N:]
        hgr = hr[:, self.delta_flat];  hgi = hi[:, self.delta_flat]
        return torch.cat([hgr * self.pr - hgi * self.pi_,
                          hgr * self.pi_ + hgi * self.pr], dim=-1)


class DiffLMMSELayer(nn.Module):
    """
    Differentiable LMMSE detection via block-real torch.linalg.solve.

    Signal model: y = H (x_p + x_d) + w
    1. Pilot cancellation: y_d = y - H x_p
    2. H_d = H[:, data_pos]
    3. Block-real LMMSE: [G_re -G_im; G_im G_re] x = [rhs_re; rhs_im]

    Learnable noise_floor prevents ill-conditioned solve at high SNR.

    Inputs:  [H_flat (B,2N^2), y (B,2N), xp (B,2N), sw2 (B,1)]
    Outputs: (x_hat (B,2*n_data),  v_x (B,2*n_data))
      x_hat : LMMSE mean  (block-real: [Re|Im])
      v_x   : per-symbol posterior variance  diag( sigma2*(H_d^H H_d + sigma2 I)^{-1} )
              computed via Cholesky diagonal extraction — same cost as existing solve.
    """
    def __init__(self, N, data_positions):
        super().__init__()
        self.N = N; self.n_data = len(data_positions)
        self.register_buffer('data_pos',
            torch.from_numpy(np.asarray(data_positions, dtype=np.int64)))
        self.noise_floor = nn.Parameter(torch.tensor(-3.0))

    @torch.amp.autocast('cuda', enabled=False)   # linalg.solve requires float32
    def forward(self, inputs):
        H_flat, y_flat, xp_flat, sigma_w2 = inputs
        # Cast to float32: autocast may have downcast upstream activations to fp16
        H_flat, y_flat, xp_flat, sigma_w2 = (
            H_flat.float(), y_flat.float(), xp_flat.float(), sigma_w2.float())
        N = self.N; n_d = self.n_data
        Hr = H_flat[:, :N*N].reshape(-1, N, N)
        Hi = H_flat[:, N*N:].reshape(-1, N, N)
        yr = y_flat[:, :N];   yi = y_flat[:, N:]
        xpr = xp_flat[:, :N]; xpi = xp_flat[:, N:]
        # Pilot cancellation
        Hxpr = (torch.bmm(Hr,  xpr.unsqueeze(-1)).squeeze(-1)
              - torch.bmm(Hi,  xpi.unsqueeze(-1)).squeeze(-1))
        Hxpi = (torch.bmm(Hr,  xpi.unsqueeze(-1)).squeeze(-1)
              + torch.bmm(Hi,  xpr.unsqueeze(-1)).squeeze(-1))
        ydr = yr - Hxpr;  ydi = yi - Hxpi
        # Data columns
        Hdr = Hr[:, :, self.data_pos];  Hdi = Hi[:, :, self.data_pos]
        HHr =  Hdr.transpose(-2, -1);   HHi = -Hdi.transpose(-2, -1)
        Gr = torch.bmm(HHr, Hdr) - torch.bmm(HHi, Hdi)
        Gi = torch.bmm(HHr, Hdi) + torch.bmm(HHi, Hdr)
        # Regularise
        s2  = sigma_w2.float() + F.softplus(self.noise_floor) * 0.1
        eye = torch.eye(n_d, dtype=torch.float32, device=H_flat.device)
        Gr  = Gr + s2.unsqueeze(-1) * eye.unsqueeze(0)
        # rhs
        ydr_ = ydr.unsqueeze(-1);  ydi_ = ydi.unsqueeze(-1)
        rr = (torch.bmm(HHr, ydr_) - torch.bmm(HHi, ydi_)).squeeze(-1)
        ri = (torch.bmm(HHr, ydi_) + torch.bmm(HHi, ydr_)).squeeze(-1)
        # Block-real Gram matrix  G_blk = [Gr -Gi; Gi Gr]  (2n_d x 2n_d)
        G_blk = torch.cat([torch.cat([ Gr, -Gi], dim=2),
                           torch.cat([ Gi,  Gr], dim=2)], dim=1)
        rhs   = torch.cat([rr, ri], dim=1).unsqueeze(-1)
        # LMMSE mean: x_hat = G_blk^{-1} rhs
        x_hat = torch.linalg.solve(G_blk, rhs).squeeze(-1)
        # Per-symbol posterior variance: diag(s2 * G_blk^{-1})
        # via Cholesky:  G = L L^T  =>  G^{-1} = (L^{-1})^T L^{-1}
        # diag(G^{-1}) = sum of squares of rows of L^{-T}
        try:
            L      = torch.linalg.cholesky(G_blk)          # (B, 2n_d, 2n_d) lower
            I_2nd  = torch.eye(2 * n_d, dtype=torch.float32,
                               device=H_flat.device).unsqueeze(0).expand_as(G_blk)
            L_inv  = torch.linalg.solve_triangular(L, I_2nd, upper=False)
            # diag(G^{-1}) = column-wise squared-norm of L_inv
            v_x    = (L_inv ** 2).sum(dim=-2) * s2.squeeze(-1).unsqueeze(-1)
        except RuntimeError:
            # Fallback if Cholesky fails (non-PD after regularisation)
            v_x    = s2.expand(-1, 2 * n_d).clone()
        return x_hat, v_x


class DiffDemapperLayer(nn.Module):
    """
    Gray-coded QPSK soft demapper.

    If v_x is provided (per-symbol LMMSE posterior variance):
        tau_i = 2 / v_x_i   (proper max-log QPSK LLR, noise-adaptive per symbol)
    Else fallback:
        tau = softplus(tau_raw) + 0.1   (legacy global scale, BC with old checkpoints)

    Sign convention: L_k > 0  means  bit_k = 1  is more likely.
      L_0 = -tau * Re(x_hat)  (MSB / in-phase)
      L_1 = -tau * Im(x_hat)  (LSB / quadrature)

    Inputs : x_flat (B, 2*n_data)  [Re | Im]
             v_x    (B, 2*n_data) or None
    Outputs: (B, 2*n_data)  LLRs
    """
    def __init__(self, n_data):
        super().__init__()
        self.n_data  = n_data
        self.tau_raw = nn.Parameter(torch.tensor(2.0))   # softplus(2)~2.13

    def forward(self, x_flat, v_x=None):
        n = self.n_data
        if v_x is not None:
            # per-symbol adaptive scale: 2/v  (max-log QPSK LLR)
            tau = (2.0 / v_x.clamp_min(1e-6))   # (B, 2*n)
            return torch.cat([-tau[:, :n] * x_flat[:, :n],
                              -tau[:, n:] * x_flat[:, n:]], dim=-1)
        else:
            # legacy fallback: global learned scale
            tau = F.softplus(self.tau_raw) + 0.1
            return torch.cat([-tau * x_flat[:, :n],
                              -tau * x_flat[:, n:]], dim=-1)


# ══════════════════════════════════════════════════════════════════════════════
class OAMPLayer(nn.Module):
    """
    Single OAMP (Orthogonal AMP) iteration layer.

    Implements one unrolled OAMP step with learnable step size and
    regularization. Replaces the one-shot LMMSE matrix solve with an
    iterative refinement that explicitly handles colored interference.

    Per-layer learnable parameters:
      gamma_raw : transformed to gamma = softplus(gamma_raw) + 0.1  (step size)
      theta_raw : transformed to theta = softplus(theta_raw) + 0.01 (regularization)

    Mathematical operation per layer:
      1. Linear estimator (LE):
         C = H^H H + theta * sigma2_eff * I        [N×N complex, O(N³)]
         W = inv(C) @ H^H                           [N×N complex]
         r = mu_x_prev + gamma * W @ (y_d - H @ mu_x_prev)

      2. Onsager correction (variance tracking):
         tau = sigma² * (1 - tr(W @ H) / N)  [per-sample scalar]
         tau = clamp(tau, min=1e-4)

      3. Non-linear estimator (NLE):
         mu_x, v_x, llr = QPSKPosterior(r, tau)

    Inputs:
      y_d_c     : (B, N)     complex64 — pilot-cancelled received signal
      H_c       : (B, N, N)  complex64 — channel matrix
      HHH       : (B, N, N)  complex64 — precomputed H^H H (shared across layers)
      mu_x_prev : (B, N, 2)  float32   — previous posterior mean [Re, Im]
      v_x_prev  : (B, N, 1)  float32   — previous posterior variance
      sigma2    : (B, 1)     float32   — effective noise variance
      qpsk_post : QPSKPosterior       — shared NLE module

    Outputs: (mu_x, v_x, llr) with same shapes as QPSKPosterior outputs
    """
    def __init__(self):
        super().__init__()
        self.gamma_raw = nn.Parameter(torch.tensor(0.0))   # softplus(0)≈0.693
        self.theta_raw = nn.Parameter(torch.tensor(-2.0))  # softplus(-2)≈0.127

    @torch.amp.autocast('cuda', enabled=False)   # linalg.inv requires float32
    def forward(self, y_d_c, H_c, HHH, mu_x_prev, v_x_prev, sigma2, qpsk_post,
                llr_a=None):
        # Cast everything to float32/complex64 (may have been downcast by AMP)
        y_d_c  = y_d_c.to(torch.complex64)
        H_c    = H_c.to(torch.complex64)
        HHH    = HHH.to(torch.complex64)
        sigma2 = sigma2.float()

        B, N   = y_d_c.shape
        device = y_d_c.device

        gamma  = F.softplus(self.gamma_raw) + 0.1   # (scalar) step size > 0.1
        theta  = F.softplus(self.theta_raw) + 0.01  # (scalar) regularization > 0.01

        # ── 1. Effective noise variance (per sample) ───────────────────────
        # Use mean v_x of previous iteration for adaptive regularization
        mean_vx = v_x_prev.float().mean(dim=(1, 2), keepdim=False)  # (B,)
        sigma2_eff = (sigma2.squeeze(-1) / mean_vx.clamp_min(1e-6))  # (B,)

        # ── 2. LMMSE filter: C = H^H H + theta * sigma2_eff * I ───────────
        eye    = torch.eye(N, dtype=torch.complex64, device=device).unsqueeze(0)  # (1,N,N)
        reg    = (theta * sigma2_eff).to(torch.complex64).view(B, 1, 1) * eye     # (B,N,N)
        C      = HHH + reg                                             # (B, N, N)
        Hh     = H_c.transpose(-2, -1).conj()                          # (B, N, N)
        # Use a solve instead of explicit inverse: this is numerically better
        # and avoids MAGMA's batched inverse path on some CUDA builds.
        try:
            chol = torch.linalg.cholesky(C)
            W    = torch.cholesky_solve(Hh, chol)                      # (B, N, N)
        except torch.linalg.LinAlgError:
            W    = torch.linalg.solve(C, Hh)                           # (B, N, N)

        # ── 3. Residual linear estimate ────────────────────────────────────
        # Convert previous mean to complex: (B, N)
        mu_prev_c = torch.complex(mu_x_prev[..., 0].float(),
                                  mu_x_prev[..., 1].float())           # (B, N)
        residual  = y_d_c - torch.bmm(H_c, mu_prev_c.unsqueeze(-1)).squeeze(-1)  # (B, N)
        r_c       = mu_prev_c + gamma * torch.bmm(W, residual.unsqueeze(-1)).squeeze(-1)  # (B, N)

        # ── 4. Onsager correction: effective variance for NLE ──────────────
        # tau = sigma² * (1 - tr(W H) / N)  [theoretically correct Onsager term]
        WH       = torch.bmm(W, H_c)                                   # (B, N, N)
        tr_WH    = WH.diagonal(dim1=-2, dim2=-1).real.sum(dim=-1)      # (B,)
        onsager  = (1.0 - tr_WH / N).clamp(min=1e-3)                  # (B,) > 0
        tau      = (sigma2.squeeze(-1) * onsager).clamp_min(1e-4)      # (B,)

        # ── 5. NLE: QPSKPosterior(r, tau) ─────────────────────────────────
        r_real   = torch.stack([r_c.real, r_c.imag], dim=-1)           # (B, N, 2)
        tau_2d   = tau.view(B, 1, 1).expand(B, N, 1)                   # (B, N, 1)
        mu_x_next, v_x_next, llr = qpsk_post(
            r_real, tau_2d, llr_a=llr_a)                               # (B,N,2), (B,N,1), (B,N,2)
        return mu_x_next, v_x_next, llr


class OAMPNetDetector(nn.Module):
    """
    T-layer OAMP-Net detector (drop-in replacement for DiffLMMSELayer +
    DiffDemapperLayer combined).

    Unlike LMMSE which treats SP self-interference as white Gaussian noise,
    OAMP's Onsager correction orthogonalizes the estimate residuals so that
    each layer's input is effectively decorrelated ('matched'). This is the
    mechanism that breaks the 25 dB error floor.

    Learnable parameters: 2 scalars per OAMP layer (gamma, theta) + 1
    noise_floor = 2T + 1 parameters total (default T=4: 9 params).

    Forward interface: identical to DiffLMMSELayer for drop-in replacement.

    Inputs:  [H_flat (B,2N²), y (B,2N), xp (B,2N), sigma_w2 (B,1)]
    Outputs: (x_hat (B,2N), v_x (B,2N), llr_out (B,2N))

    The 3-tuple output is a superset of DiffLMMSELayer's 2-tuple. E2EOAMPModel
    uses x_hat, v_x, llr_out directly (llr replaces DiffDemapperLayer).
    """
    def __init__(self, N, data_positions, num_layers=4):
        super().__init__()
        self.N       = N
        self.n_data  = len(data_positions)
        self.register_buffer('data_pos',
            torch.from_numpy(np.asarray(data_positions, dtype=np.int64)))
        # Learnable noise floor (same role as DiffLMMSELayer.noise_floor)
        self.noise_floor = nn.Parameter(torch.tensor(-3.0))
        # T OAMP layers — each has gamma_raw, theta_raw (2 params each)
        self.layers      = nn.ModuleList([OAMPLayer() for _ in range(num_layers)])
        # Shared NLE — no parameters, but needs to live on same device
        self.qpsk_post   = QPSKPosterior()

    @torch.amp.autocast('cuda', enabled=False)   # linalg.inv chain requires float32
    def forward(self, inputs):
        if len(inputs) == 4:
            H_flat, y_flat, xp_flat, sigma_w2 = inputs
            mu_init_flat = None
            v_init_flat  = None
            llr_a_flat   = None
        elif len(inputs) == 7:
            (H_flat, y_flat, xp_flat, sigma_w2,
             mu_init_flat, v_init_flat, llr_a_flat) = inputs
        else:
            raise ValueError(
                "OAMPNetDetector expects 4 inputs ([H,y,xp,sigma]) or "
                "7 inputs ([H,y,xp,sigma,mu0,v0,llr_a]).")
        H_flat, y_flat, xp_flat, sigma_w2 = (
            H_flat.float(), y_flat.float(), xp_flat.float(), sigma_w2.float())
        N = self.N; n_d = self.n_data

        # ── 1. Unpack block-real → complex ────────────────────────────────
        Hr = H_flat[:, :N * N].reshape(-1, N, N)
        Hi = H_flat[:, N * N:].reshape(-1, N, N)
        H_c = torch.complex(Hr, Hi)                                    # (B, N, N)

        yr = y_flat[:, :N];   yi = y_flat[:, N:]
        y_c = torch.complex(yr, yi)                                    # (B, N)

        xpr = xp_flat[:, :N]; xpi = xp_flat[:, N:]
        xp_c = torch.complex(xpr, xpi)                                 # (B, N)

        # ── 2. Pilot cancellation (done once, outside OAMP loop) ──────────
        Hxp = torch.bmm(H_c, xp_c.unsqueeze(-1)).squeeze(-1)          # (B, N)
        y_d_c = y_c - Hxp                                              # (B, N)

        # ── 3. Precompute H^H H (shared across all layers) ────────────────
        Hh    = H_c.transpose(-2, -1).conj()                           # (B, N, N)
        HHH   = torch.bmm(Hh, H_c)                                    # (B, N, N)

        # ── 4. Effective sigma² with learnable floor ──────────────────────
        sigma2 = sigma_w2 + F.softplus(self.noise_floor) * 0.1        # (B, 1)

        # ── 5. OAMP iterations ────────────────────────────────────────────
        # Optional outer-loop soft prior turns the detector into a true
        # soft-input block instead of restarting from the same null prior.
        B = H_flat.shape[0]
        device = H_flat.device
        if mu_init_flat is None:
            mu_x = torch.zeros(B, n_d, 2, device=device)              # (B, N, 2)
        else:
            mu_init_flat = mu_init_flat.float()
            mu_x = torch.stack([mu_init_flat[:, :N], mu_init_flat[:, N:]], dim=-1)

        if v_init_flat is None:
            v_x = torch.full((B, n_d, 1), 0.5, device=device)         # (B, N, 1)
        else:
            v_init_flat = v_init_flat.float()
            if v_init_flat.dim() == 2 and v_init_flat.shape[1] == 2 * N:
                v_x = v_init_flat[:, :N].unsqueeze(-1)
            elif v_init_flat.dim() == 2 and v_init_flat.shape[1] == N:
                v_x = v_init_flat.unsqueeze(-1)
            else:
                raise ValueError("v_init_flat must have shape (B,N) or (B,2N)")

        llr_a = None
        if llr_a_flat is not None:
            llr_a_flat = llr_a_flat.float()
            llr_a = torch.stack([llr_a_flat[:, :N], llr_a_flat[:, N:]], dim=-1)

        for layer in self.layers:
            mu_x, v_x, llr = layer(
                y_d_c, H_c, HHH, mu_x, v_x, sigma2,
                self.qpsk_post, llr_a=llr_a)

        # ── 6. Convert outputs to block-real (B, 2N) for compatibility ────
        x_hat   = torch.cat([mu_x[..., 0], mu_x[..., 1]], dim=-1)     # (B, 2N) [Re|Im]
        v_x_s   = v_x.squeeze(-1)                                      # (B, N)
        v_x_out = torch.cat([v_x_s, v_x_s], dim=-1).contiguous()      # (B, 2N) symmetric [Re|Im]
        llr_out = torch.cat([llr[..., 0], llr[..., 1]], dim=-1)       # (B, 2N) [b0|b1]
        return x_hat, v_x_out, llr_out


class EPLayer(nn.Module):
    """
    One EP iteration with Gaussian site updates.

    The detector keeps a scalar Gaussian site per QPSK symbol:
      q_t(x_n) ~ CN(x_n ; gamma_n / lambda_n, 1 / lambda_n)

    Each layer performs:
      1. Gaussian posterior solve from H, y, sigma2, lambda, gamma
      2. Cavity extraction (mean_ab, var_ab)
      3. Exact QPSK projection via QPSKPosterior
      4. Damped site update (lambda, gamma)
    """
    def __init__(self, beta_init=0.4):
        super().__init__()
        beta_init = float(np.clip(beta_init, 1e-3, 1.0 - 1e-3))
        beta_logit = np.log(beta_init / (1.0 - beta_init))
        self.beta_raw = nn.Parameter(torch.tensor(beta_logit, dtype=torch.float32))
        self.jitter_raw = nn.Parameter(torch.tensor(-7.0, dtype=torch.float32))

    @torch.amp.autocast('cuda', enabled=False)
    def forward(self, y_d_c, H_d_c, HHH, Hhy, sigma2, lambda_prev, gamma_prev,
                qpsk_post):
        y_d_c      = y_d_c.to(torch.complex64)
        H_d_c      = H_d_c.to(torch.complex64)
        HHH        = HHH.to(torch.complex64)
        Hhy        = Hhy.to(torch.complex64)
        sigma2     = sigma2.float().squeeze(-1)
        lambda_prev = lambda_prev.float().clamp_min(1e-5)
        gamma_prev = gamma_prev.to(torch.complex64)

        B, N = Hhy.shape
        device = Hhy.device
        eye = torch.eye(N, dtype=torch.complex64, device=device).unsqueeze(0)
        beta = torch.sigmoid(self.beta_raw).clamp(0.05, 0.95)
        jitter = F.softplus(self.jitter_raw) * 1e-3 + 1e-7

        reg = sigma2.view(B, 1, 1).to(torch.complex64) * torch.diag_embed(
            lambda_prev).to(torch.complex64)
        C = HHH + reg + jitter * eye
        rhs = Hhy + sigma2.view(B, 1).to(torch.complex64) * gamma_prev

        try:
            chol = torch.linalg.cholesky(C)
            mu_mmse = torch.cholesky_solve(rhs.unsqueeze(-1), chol).squeeze(-1)
            invC = torch.cholesky_solve(
                eye.expand(B, -1, -1).contiguous(), chol)
        except torch.linalg.LinAlgError:
            mu_mmse = torch.linalg.solve(C, rhs.unsqueeze(-1)).squeeze(-1)
            invC = torch.linalg.solve(
                C, eye.expand(B, -1, -1).contiguous())

        var_mmse = (sigma2.view(B, 1) * invC.diagonal(dim1=-2, dim2=-1).real
                    ).clamp_min(1e-6)
        cav_precision = (1.0 / var_mmse - lambda_prev).clamp_min(1e-6)
        var_ab = (1.0 / cav_precision).clamp_min(1e-6)
        mean_ab = var_ab.to(torch.complex64) * (
            mu_mmse / var_mmse.to(torch.complex64) - gamma_prev)

        mu_post, v_post, llr = qpsk_post(
            torch.stack([mean_ab.real, mean_ab.imag], dim=-1),
            var_ab.unsqueeze(-1))
        mu_post_c = torch.complex(mu_post[..., 0].float(), mu_post[..., 1].float())
        v_post_s = v_post.squeeze(-1).float().clamp_min(1e-6)

        lambda_new = 1.0 / v_post_s - 1.0 / var_ab
        gamma_new = (mu_post_c / v_post_s.to(torch.complex64)
                     - mean_ab / var_ab.to(torch.complex64))

        invalid = (~torch.isfinite(lambda_new)) | (lambda_new <= 1e-6)
        invalid = invalid | (~torch.isfinite(gamma_new.real))
        invalid = invalid | (~torch.isfinite(gamma_new.imag))
        lambda_new = torch.where(invalid, lambda_prev, lambda_new)
        gamma_new = torch.where(invalid, gamma_prev, gamma_new)

        lambda_next = (beta * lambda_prev + (1.0 - beta) * lambda_new).clamp_min(1e-6)
        gamma_next = beta * gamma_prev + (1.0 - beta) * gamma_new
        return mu_post, v_post, llr, lambda_next, gamma_next


class EPNetDetector(nn.Module):
    """
    T-layer EP detector with the same block-real contract as OAMPNetDetector.

    Inputs:
      [H_flat, y, xp, sigma] or [H_flat, y, xp, sigma, mu0, v0, llr_a]
    Outputs:
      x_hat  : (B, 2*n_data)
      v_x    : (B, 2*n_data)
      llr    : (B, 2*n_data)
    """
    _INV_SQRT2 = float(1.0 / np.sqrt(2.0))

    def __init__(self, N, data_positions, num_layers=4, beta=0.4):
        super().__init__()
        self.N = N
        self.n_data = len(data_positions)
        self.register_buffer(
            'data_pos', torch.from_numpy(np.asarray(data_positions, dtype=np.int64)))
        self.noise_floor = nn.Parameter(torch.tensor(-3.0))
        self.layers = nn.ModuleList([
            EPLayer(beta_init=beta) for _ in range(num_layers)])
        self.qpsk_post = QPSKPosterior()

    def _prior_from_llr(self, llr_a_flat):
        llr_a_flat = llr_a_flat.float()
        n_d = self.n_data
        llr = torch.stack([llr_a_flat[:, :n_d], llr_a_flat[:, n_d:]], dim=-1)
        mu = -torch.tanh(llr * 0.5) * self._INV_SQRT2
        var = (0.5 - mu.square()).mean(dim=-1).clamp_min(1e-3)
        return mu, var

    def _prior_from_moments(self, mu_init_flat, v_init_flat):
        n_d = self.n_data
        mu_init_flat = mu_init_flat.float()
        mu = torch.stack([mu_init_flat[:, :n_d], mu_init_flat[:, n_d:]], dim=-1)
        if v_init_flat.dim() == 2 and v_init_flat.shape[1] == 2 * n_d:
            var = 0.5 * (v_init_flat[:, :n_d].float() + v_init_flat[:, n_d:].float())
        elif v_init_flat.dim() == 2 and v_init_flat.shape[1] == n_d:
            var = v_init_flat.float()
        else:
            raise ValueError("v_init_flat must have shape (B,n_d) or (B,2*n_d)")
        return mu, var.clamp_min(1e-3)

    @torch.amp.autocast('cuda', enabled=False)
    def forward(self, inputs):
        if len(inputs) == 4:
            H_flat, y_flat, xp_flat, sigma_w2 = inputs
            mu_init_flat = None
            v_init_flat = None
            llr_a_flat = None
        elif len(inputs) == 7:
            (H_flat, y_flat, xp_flat, sigma_w2,
             mu_init_flat, v_init_flat, llr_a_flat) = inputs
        else:
            raise ValueError(
                "EPNetDetector expects 4 inputs ([H,y,xp,sigma]) or "
                "7 inputs ([H,y,xp,sigma,mu0,v0,llr_a]).")

        H_flat = H_flat.float()
        y_flat = y_flat.float()
        xp_flat = xp_flat.float()
        sigma_w2 = sigma_w2.float()

        N = self.N
        n_d = self.n_data

        Hr = H_flat[:, :N * N].reshape(-1, N, N)
        Hi = H_flat[:, N * N:].reshape(-1, N, N)
        H_c = torch.complex(Hr, Hi)
        H_d_c = H_c[:, :, self.data_pos]

        yr = y_flat[:, :N]
        yi = y_flat[:, N:]
        y_c = torch.complex(yr, yi)

        xpr = xp_flat[:, :N]
        xpi = xp_flat[:, N:]
        xp_c = torch.complex(xpr, xpi)

        Hxp = torch.bmm(H_c, xp_c.unsqueeze(-1)).squeeze(-1)
        y_d_c = y_c - Hxp

        Hh = H_d_c.transpose(-2, -1).conj()
        HHH = torch.bmm(Hh, H_d_c)
        Hhy = torch.bmm(Hh, y_d_c.unsqueeze(-1)).squeeze(-1)
        sigma2 = sigma_w2 + F.softplus(self.noise_floor) * 0.1

        if llr_a_flat is not None:
            mu_prior, v_prior = self._prior_from_llr(llr_a_flat)
        elif mu_init_flat is not None and v_init_flat is not None:
            mu_prior, v_prior = self._prior_from_moments(mu_init_flat, v_init_flat)
        else:
            B = H_flat.shape[0]
            device = H_flat.device
            mu_prior = torch.zeros(B, n_d, 2, device=device)
            v_prior = torch.full((B, n_d), 0.5, device=device)

        lambda_site = (1.0 / v_prior).clamp_min(1e-3)
        gamma_site = torch.complex(
            mu_prior[..., 0].float(), mu_prior[..., 1].float()
        ) / v_prior.to(torch.complex64)

        mu_x = mu_prior
        v_x = v_prior.unsqueeze(-1)
        llr = torch.zeros_like(mu_prior)
        for layer in self.layers:
            mu_x, v_x, llr, lambda_site, gamma_site = layer(
                y_d_c, H_d_c, HHH, Hhy, sigma2,
                lambda_site, gamma_site, self.qpsk_post)

        x_hat = torch.cat([mu_x[..., 0], mu_x[..., 1]], dim=-1)
        v_x_s = v_x.squeeze(-1)
        v_x_out = torch.cat([v_x_s, v_x_s], dim=-1).contiguous()
        llr_out = torch.cat([llr[..., 0], llr[..., 1]], dim=-1)
        return x_hat, v_x_out, llr_out


class DiffRZFToGridLayer(nn.Module):
    """
    Differentiable RZF feature extractor for Stage-2.
    h = W_match @ y_clean -> dechirp -> scatter to 2D grid.
    Inputs:  (batch, 2*N)         Outputs: (batch, 2*L_max*W)
    """
    def __init__(self, N, L_max, W, W_match_np, delta_idx_flat, c2, m0):
        super().__init__()
        self.N = N; self.L_max = L_max; self.W = W
        self.register_buffer('WrT', torch.from_numpy(np.real(W_match_np).T.astype(np.float32)))
        self.register_buffer('WiT', torch.from_numpy(np.imag(W_match_np).T.astype(np.float32)))
        da = np.arange(N, dtype=np.float64)
        dc = np.exp(1j*2*np.pi*c2*(((m0+da)%N)**2 - float(m0)**2))
        self.register_buffer('dcr', torch.from_numpy(np.real(dc).astype(np.float32)))
        self.register_buffer('dci', torch.from_numpy(np.imag(dc).astype(np.float32)))
        self.register_buffer('didx', torch.from_numpy(delta_idx_flat.astype(np.int64)))

    def forward(self, y_2n):
        N = self.N
        yr = y_2n[:, :N];  yi = y_2n[:, N:]
        hr = yr @ self.WrT - yi @ self.WiT
        hi = yr @ self.WiT + yi @ self.WrT
        hdr = hr * self.dcr - hi * self.dci
        hdi = hr * self.dci + hi * self.dcr
        return torch.cat([hdr[:, self.didx], hdi[:, self.didx]], dim=-1)


class SymbolToGridLayer(nn.Module):
    """
    Map N-length DAFT-domain quantities to the (L_max, W) 2D grid
    using the same delta_idx gather as Grid2DTo1DLayer (inverse scatter).

    mode='complex':  input (B, 2N) [Re|Im]  →  output (B, 2, L_max, W)
    mode='real':     input (B,  N)           →  output (B, 1, L_max, W)

    Fully differentiable via integer-index gather (gradients flow
    through the gathered source values).  Overlapping grid cells
    receive the same tap value (no averaging needed — this is a
    lookup, not a scatter-accumulate).
    """
    def __init__(self, N, K_factor, k_max, L_max, W, pad_size):
        super().__init__()
        self.N = N; self.L_max = L_max; self.W = W
        offsets   = np.arange(-(k_max + pad_size), k_max + pad_size + 1)
        centers   = np.arange(L_max) * K_factor
        delta_idx = ((centers[:, None] + offsets[None, :]) % N).ravel()  # (L_max*W,)
        self.register_buffer('didx', torch.from_numpy(delta_idx.astype(np.int64)))

    def forward(self, x, mode='complex'):
        LW = self.L_max * self.W
        if mode == 'complex':
            # x: (B, 2N) → split Re/Im → gather → reshape to (B, 2, L, W)
            N = self.N
            xr = x[:, :N][:, self.didx]  # (B, L*W)
            xi = x[:, N:][:, self.didx]  # (B, L*W)
            return torch.stack([xr.view(-1, self.L_max, self.W),
                                 xi.view(-1, self.L_max, self.W)], dim=1)  # (B, 2, L, W)
        else:
            # x: (B, N) → gather → reshape to (B, 1, L, W)
            xg = x[:, self.didx]  # (B, L*W)
            return xg.view(-1, 1, self.L_max, self.W)  # (B, 1, L, W)


class DiffSoftSICLayer(nn.Module):
    """
    Differentiable soft-SIC:  y_clean = y_orig - H @ mu_x

    sic_mode options:
      'soft'      : subtract x_hat directly (legacy)
      'qpsk_proj' : soft QPSK projection via tanh (learnable beta)
      'mmse'      : subtract QPSK posterior mean mu_x computed from
                    (x_hat, v_x) via QPSKPosterior.
                    Needs v_x in inputs; falls back to 'soft' if absent.

    Inputs:  [H_flat (B,2N^2), x_hat (B,2N), y_orig (B,2N)]
          or [H_flat (B,2N^2), x_hat (B,2N), y_orig (B,2N), v_x (B,2N)]  (mmse mode)
    Outputs: y_clean (B,2N)
    """
    def __init__(self, N, rho=0.3, sic_mode='soft'):
        super().__init__()
        self.N = N; self.rho = rho; self.sic_mode = sic_mode
        if sic_mode == 'qpsk_proj':
            self.beta_raw = nn.Parameter(torch.tensor(2.0))
        if sic_mode == 'mmse':
            self._qpsk_post = QPSKPosterior()

    def forward(self, inputs):
        # Accept 3-tuple (legacy) or 4-tuple (with v_x)
        if len(inputs) == 4:
            H_flat, x_hat, y_orig, v_x = inputs
        else:
            H_flat, x_hat, y_orig = inputs
            v_x = None
        N  = self.N
        Hr = H_flat[:, :N*N].reshape(-1, N, N)
        Hi = H_flat[:, N*N:].reshape(-1, N, N)
        xr = x_hat[:, :N];  xi = x_hat[:, N:]
        if self.sic_mode == 'qpsk_proj':
            beta = F.softplus(self.beta_raw) + 0.5
            amp  = float(np.sqrt((1.0 - self.rho) / 2.0))
            xr   = torch.tanh(beta * (xr / amp)) * amp
            xi   = torch.tanh(beta * (xi / amp)) * amp
        elif self.sic_mode == 'mmse' and v_x is not None:
            # Compute QPSK posterior mean from (x_hat, v_x)
            # Reshape to (B, N, 2) for QPSKPosterior
            z   = torch.stack([xr, xi], dim=-1)          # (B, N, 2)
            vv  = v_x[:, :N].unsqueeze(-1)               # (B, N, 1) use Re-component var
            mu, _, _ = self._qpsk_post(z, vv)
            xr  = mu[:, :, 0];  xi = mu[:, :, 1]
        Hxr = (torch.bmm(Hr, xr.unsqueeze(-1)).squeeze(-1)
             - torch.bmm(Hi, xi.unsqueeze(-1)).squeeze(-1))
        Hxi = (torch.bmm(Hr, xi.unsqueeze(-1)).squeeze(-1)
             + torch.bmm(Hi, xr.unsqueeze(-1)).squeeze(-1))
        yr = y_orig[:, :N];  yi = y_orig[:, N:]
        return torch.cat([yr - Hxr, yi - Hxi], dim=-1)


class DifferentiableSoftThreshold(nn.Module):
    """
    Soft-thresholding: y = sign(x) * ReLU(|x| - tau),  tau = softplus(tau_raw) > 0.
    tau_raw is learnable, initialised => tau ~ 0.127 (conservative).
    """
    def __init__(self):
        super().__init__()
        self.tau_raw = nn.Parameter(torch.tensor(-2.0))

    def forward(self, x):
        tau = F.softplus(self.tau_raw)
        return torch.sign(x) * torch.relu(torch.abs(x) - tau)


# ══════════════════════════════════════════════════════════════════════════════
class QPSKPosterior(nn.Module):
    """
    Exact differentiable QPSK posterior from Gaussian message (z, v_x).

    For each data symbol n, given:
      z_n   = mu_LMMSE_n  (channel output after equalization)
      v_n   = posterior variance from LMMSE
      L_a   = a-priori LLR (optional, e.g. from outer decoder)

    Computes per-symbol:
      mu_x  :  E[x | z, v_x, L_a]        posterior mean  (block-real)
      v_post:  Var[x | z, v_x, L_a]      posterior variance
      llr_e :  extrinsic LLR             (for turbo exchange)

    Sign convention: LLR > 0 means bit = 1 more likely.
    Gray QPSK constellation (block-real representation):
      s0 = (+1/√2, +1/√2) → bits (0,0)
      s1 = (+1/√2, -1/√2) → bits (0,1)
      s2 = (-1/√2, +1/√2) → bits (1,0)
      s3 = (-1/√2, -1/√2) → bits (1,1)

    Inputs:
      z     : (B, N, 2) or (B, N)  block-real LMMSE output   [Re | Im per symbol]
      v_x   : (B, N, 1) or (B, N)  per-symbol variance
      llr_a : (B, N, 2) or None    a-priori LLR [b0, b1]

    Outputs:
      mu_x  : (B, N, 2)  posterior mean (block-real)
      v_post: (B, N, 1)  posterior variance (scalar per symbol)
      llr_e : (B, N, 2)  extrinsic LLR [b0, b1]
    """
    _INV_SQRT2 = float(1.0 / np.sqrt(2.0))

    def __init__(self):
        super().__init__()
        # 4 QPSK points in block-real form: (4, 2)
        s = self._INV_SQRT2
        const = torch.tensor([[ s,  s],
                              [ s, -s],
                              [-s,  s],
                              [-s, -s]], dtype=torch.float32)
        # Gray-code bit patterns: bit0 (MSB) maps to I, bit1 (LSB) maps to Q
        bits = torch.tensor([[0, 0],
                             [0, 1],
                             [1, 0],
                             [1, 1]], dtype=torch.float32)
        self.register_buffer('const', const)   # (4, 2)
        self.register_buffer('bits',  bits)    # (4, 2)

    def forward(self, z, v_x, llr_a=None):
        """
        z     : (B, N, 2)  block-real LMMSE mean per symbol
        v_x   : (B, N, 1)  per-symbol variance   (must be > 0)
        llr_a : (B, N, 2)  a-priori LLR or None
        """
        # --- reshape inputs to (B, N, ...) ---
        if z.dim() == 2:            # (B, 2N) flat -> (B, N, 2)
            B, two_N = z.shape
            N = two_N // 2
            z   = torch.stack([z[:, :N], z[:, N:]], dim=-1)    # (B,N,2)
        if v_x.dim() == 2:          # (B, 2N) -> (B, N, 1)
            B, two_N = v_x.shape
            N = two_N // 2
            v_x = v_x[:, :N].unsqueeze(-1)                     # use Re-component var

        # Gaussian log-likelihood for each constellation point
        # d2: (B, N, 4)  ||z - s||^2 / v
        diff = z.unsqueeze(-2) - self.const.view(1, 1, 4, 2)   # (B, N, 4, 2)
        d2   = (diff ** 2).sum(dim=-1)                         # (B, N, 4)
        logp = -d2 / v_x.clamp_min(1e-7)                       # (B, N, 4)

        # Incorporate a-priori LLR if provided
        if llr_a is not None:
            # bits: (4,2)  llr_a: (B,N,2)  sign convention: llr_a>0 => bit=1
            b   = self.bits.view(1, 1, 4, 2)                   # (1,1,4,2)
            # log p(b|L_a) = sum_k  b_k * ln sigma(L_ak) + (1-b_k) * ln sigma(-L_ak)
            # = sum_k  L_ak * (b_k - 0.5)    [up to constant]
            log_prior = (llr_a.unsqueeze(-2) * (b - 0.5)).sum(dim=-1)  # (B,N,4)
            logp = logp + log_prior

        # Numerically stable softmax
        logp = logp - logp.max(dim=-1, keepdim=True).values
        p    = torch.softmax(logp, dim=-1)                     # (B, N, 4)

        # Posterior mean  mu = E[x|z] = sum_s  s * p(s)
        mu = torch.einsum('bns,sc->bnc', p, self.const)        # (B, N, 2)

        # Posterior variance  v = E[|x - mu|^2]
        diff2  = (self.const.view(1, 1, 4, 2) - mu.unsqueeze(-2)) ** 2  # (B,N,4,2)
        v_post = (p.unsqueeze(-1) * diff2).sum(dim=-2).mean(dim=-1, keepdim=True)  # (B,N,1)

        # Extrinsic LLR  (b=0 vs b=1 per bit position, subtract a-priori)
        neg_inf = torch.full_like(logp, -1e9)
        llr_e_list = []
        for bit_idx in range(2):
            # bit=1 accumulator
            mask1 = (self.bits[:, bit_idx] > 0.5).view(1, 1, 4)
            mask0 = ~mask1
            lse1  = torch.logsumexp(torch.where(mask1, logp, neg_inf), dim=-1)  # (B,N)
            lse0  = torch.logsumexp(torch.where(mask0, logp, neg_inf), dim=-1)  # (B,N)
            llr_e_list.append(lse1 - lse0)                     # L_intrinsic
        llr_intr = torch.stack(llr_e_list, dim=-1)             # (B, N, 2)
        # Extrinsic = intrinsic - a-priori
        if llr_a is not None:
            llr_e = llr_intr - llr_a
        else:
            llr_e = llr_intr

        return mu, v_post, llr_e
