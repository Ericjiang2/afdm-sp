"""path_e_models.py — End-to-end ladder for paper §IV-H E2E evidence.

Four stages of increasing inductive bias to test "is E2E truly infeasible
or were Path C failures implementation artifacts":

E0 — FixedTransformerReceiver: pure Transformer, NO DAFT structure.
     Fixes Path C2 bugs (broken pilot subtract; zero-init out_proj; raw scalar
     chirp params as broadcast features). Otherwise unchanged from C2.

E1 — DaftAwareTransformerReceiver: E0 + explicit DAFT basis features.
     Inputs include Re/Im of the chirp basis exp(j·2π·(-c1·n² + c2·n²)),
     giving the transformer a head-start at decoding without learning the
     entire DAFT operator from scratch.

E2 — OtfsModularReceiver: U-Net CENet for channel estimation +
     differentiable LMMSE detector. Replaces OMP+MP entirely while keeping
     DAFT structure fixed. Mirrors arXiv 2601.22523 (Superimposed-Pilot OTFS
     Modular E2E Learning), adapted from 2D DD grid to AFDM's 1D DAFT.

E3 — AutoencoderJointTxRx: jointly learnable constellation mapping + pilot
     insertion + IZak-like RX + detector. SOTA upper bound, follows
     NAE-OTFS / VAE-OTFS pattern.

This file: model definitions only. Training in `train_path_e.py`.
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


# =====================================================================
# Helper: feature stacking with proper pilot handling
# =====================================================================
def _stack_realimag(t: torch.Tensor) -> torch.Tensor:
    """Stack real, imag, magnitude of a complex (N,) tensor → (3, N) float."""
    return torch.stack([t.real, t.imag, t.abs()], dim=0)


# =====================================================================
# E0 — Fixed pure Transformer (no DAFT structure)
# =====================================================================
class FixedTransformerReceiver(nn.Module):
    """E0: Path C2 with bug fixes.

    Fixes vs C2:
      - Pilot is NOT naively subtracted. Both y_daft and x_pilot are passed
        as separate Re/Im/Mag feature channels (6 channels per position).
        NN must learn pilot cancellation internally.
      - Output projection is Xavier-initialised (not zero-init), so initial
        x_hat is small Gaussian rather than identically zero. Gives BCE
        gradient signal a finite reasonable starting point.
      - SNR (log_sigma2) is broadcast per position, not as a raw value.

    Input feature dim: 6 (= Re(y), Im(y), |y|, Re(pilot), Im(pilot), log_σ²).
    No chirp params in input (E1 will add them).
    """

    def __init__(self, N: int = 1024, d_model: int = 128, nhead: int = 4,
                 num_layers: int = 4, dim_ff: int = 512):
        super().__init__()
        self.N = N
        self.in_proj = nn.Linear(6, d_model)
        self.pos = nn.Parameter(0.02 * torch.randn(1, N, d_model))
        enc_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=dim_ff,
            batch_first=True, activation='gelu')
        self.encoder = nn.TransformerEncoder(enc_layer, num_layers=num_layers)
        self.out_proj = nn.Linear(d_model, 2)
        # Xavier init — initial output is small random, not zero.
        nn.init.xavier_uniform_(self.out_proj.weight, gain=0.1)
        nn.init.zeros_(self.out_proj.bias)

    def _build_features(self, y_daft: torch.Tensor, x_pilot: torch.Tensor,
                         sigma2: torch.Tensor) -> torch.Tensor:
        N = y_daft.shape[-1]
        log_sig = sigma2.clamp_min(1e-30).log().expand(N).to(y_daft.real.dtype)
        feats = torch.stack([
            y_daft.real, y_daft.imag, y_daft.abs(),
            x_pilot.real, x_pilot.imag, log_sig,
        ], dim=-1).unsqueeze(0)                              # (1, N, 6)
        return feats

    def forward(self, y_daft: torch.Tensor, x_pilot: torch.Tensor,
                sigma2: torch.Tensor, const: torch.Tensor,
                c1: float = 0.0, c2: float = 0.0) -> Dict:
        N = y_daft.shape[-1]
        assert N == self.N, f'Transformer fixed N={self.N}, got {N}'
        feats = self._build_features(y_daft, x_pilot, sigma2)  # (1, N, 6)
        h = self.in_proj(feats) + self.pos
        h = self.encoder(h)
        out = self.out_proj(h).squeeze(0)                      # (N, 2)
        x_hat = torch.complex(out[:, 0], out[:, 1]).to(y_daft.dtype)
        H_id = torch.eye(N, dtype=y_daft.dtype, device=y_daft.device)
        return dict(x_soft=x_hat, H_est=H_id,
                    x_soft_history=[x_hat],
                    resnorm_history=[torch.tensor(0.0, device=y_daft.device,
                                                    dtype=sigma2.dtype)])


# =====================================================================
# E1 — DAFT-aware Transformer (chirp basis as input features)
# =====================================================================
class DaftAwareTransformerReceiver(FixedTransformerReceiver):
    """E1: E0 + chirp basis as input features.

    Additional 4 channels: Re/Im of two chirp bases
      - basis_c1[n] = exp(j·2π·(-c1·n²))
      - basis_c2[n] = exp(j·2π·(c2·n²))
    These are the building blocks of the DAFT operator A_n = Λ_c2·F·Λ_c1;
    feeding them to the NN should let it match-filter against the chirp
    structure without learning the full operator from scratch.

    Input feature dim: 10 = 6 (E0) + 4 (chirp basis Re/Im for c1 and c2).
    """

    def __init__(self, N: int = 1024, d_model: int = 128, nhead: int = 4,
                 num_layers: int = 4, dim_ff: int = 512):
        super().__init__(N=N, d_model=d_model, nhead=nhead,
                         num_layers=num_layers, dim_ff=dim_ff)
        # Override in_proj for 10-dim input
        self.in_proj = nn.Linear(10, d_model)

    def _build_features(self, y_daft: torch.Tensor, x_pilot: torch.Tensor,
                         sigma2: torch.Tensor, c1: float = 0.0,
                         c2: float = 0.0) -> torch.Tensor:
        N = y_daft.shape[-1]
        device = y_daft.device
        rdtype = y_daft.real.dtype
        log_sig = sigma2.clamp_min(1e-30).log().expand(N).to(rdtype)
        # Chirp basis: exp(j·2π·(-c1·n²)) and exp(j·2π·(c2·n²))
        n = torch.arange(N, device=device, dtype=torch.float64)
        ang1 = (2.0 * math.pi) * (-float(c1)) * n.pow(2)
        ang2 = (2.0 * math.pi) * (float(c2)) * n.pow(2)
        basis_c1_re = torch.cos(ang1).to(rdtype)
        basis_c1_im = torch.sin(ang1).to(rdtype)
        basis_c2_re = torch.cos(ang2).to(rdtype)
        basis_c2_im = torch.sin(ang2).to(rdtype)
        feats = torch.stack([
            y_daft.real, y_daft.imag, y_daft.abs(),
            x_pilot.real, x_pilot.imag, log_sig,
            basis_c1_re, basis_c1_im,
            basis_c2_re, basis_c2_im,
        ], dim=-1).unsqueeze(0)                              # (1, N, 10)
        return feats

    def forward(self, y_daft: torch.Tensor, x_pilot: torch.Tensor,
                sigma2: torch.Tensor, const: torch.Tensor,
                c1: float = 0.0, c2: float = 0.0) -> Dict:
        N = y_daft.shape[-1]
        assert N == self.N, f'Transformer fixed N={self.N}, got {N}'
        feats = self._build_features(y_daft, x_pilot, sigma2, c1=c1, c2=c2)
        h = self.in_proj(feats) + self.pos
        h = self.encoder(h)
        out = self.out_proj(h).squeeze(0)
        x_hat = torch.complex(out[:, 0], out[:, 1]).to(y_daft.dtype)
        H_id = torch.eye(N, dtype=y_daft.dtype, device=y_daft.device)
        return dict(x_soft=x_hat, H_est=H_id,
                    x_soft_history=[x_hat],
                    resnorm_history=[torch.tensor(0.0, device=y_daft.device,
                                                    dtype=sigma2.dtype)])


# =====================================================================
# E2 — OTFS modular E2E ported to AFDM (CENet + diff. LMMSE)
# =====================================================================
class UNet1DCENet(nn.Module):
    """1D U-Net channel estimator. Input: (Re y, Im y, Re pilot, Im pilot,
    log_sigma2) → output: (Re H_diag, Im H_diag) approximating a per-position
    effective channel diagonal H_eff[n,n]. Simplified vs full (N,N) — we
    estimate diagonal entries which are the dominant terms in the chirp-domain
    effective channel.
    """

    def __init__(self, base_ch: int = 32):
        super().__init__()
        self.enc1 = self._block(5, base_ch)
        self.enc2 = self._block(base_ch, base_ch * 2)
        self.enc3 = self._block(base_ch * 2, base_ch * 4)
        self.dec3 = self._block(base_ch * 4, base_ch * 2)
        self.dec2 = self._block(base_ch * 2 * 2, base_ch)
        self.out = nn.Conv1d(base_ch * 2, 2, kernel_size=1)
        nn.init.zeros_(self.out.weight)
        nn.init.zeros_(self.out.bias)
        self.pool = nn.AvgPool1d(2)
        self.up = nn.Upsample(scale_factor=2, mode='linear', align_corners=False)

    @staticmethod
    def _block(in_c: int, out_c: int) -> nn.Sequential:
        return nn.Sequential(
            nn.Conv1d(in_c, out_c, kernel_size=5, padding=2),
            nn.GELU(),
            nn.Conv1d(out_c, out_c, kernel_size=5, padding=2),
            nn.GELU(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))
        d3 = self.dec3(e3)
        d2 = self.dec2(torch.cat([self.up(d3), e2], dim=1))
        d1 = torch.cat([self.up(d2), e1], dim=1)
        return self.out(d1)                                  # (1, 2, N)


class _HReconstructor(nn.Module):
    """Vectorised AFDM H_eff reconstruction from DD-grid coefficients.

    Precomputes per-(l, k, n) phase factors and destination row indices at
    init time (c1, c2 are fixed). Forward is a single scatter_add over
    L·K·N entries — 100×+ faster than the equivalent Python-loop version.

    Forward signature:
        g_dd: (L, K) complex → H_eff: (N, N) complex
    """

    def __init__(self, N: int, l_max: int, k_max: int,
                 c1: float, c2: float,
                 cdtype: torch.dtype = torch.complex64):
        super().__init__()
        self.N = N
        self.l_max = l_max
        self.k_max = k_max
        self.L = l_max + 1
        self.K = 2 * k_max + 1
        self.cdtype = cdtype

        L, K = self.L, self.K
        n_arr = torch.arange(N, dtype=torch.float64)            # (N,)
        # Build per-(l, k, n) phase pattern and destination row indices.
        # angle[l, k, n] = 2π · ( -c1·l² + c2·(m² - n²) - l·n/N ), m = (n + δ) mod N
        l_idx = torch.arange(L, dtype=torch.float64).view(L, 1, 1)        # (L,1,1)
        k_idx = (torch.arange(K, dtype=torch.float64) - k_max).view(1, K, 1)  # (1,K,1)
        n_v = n_arr.view(1, 1, N)                                          # (1,1,N)
        delta = (l_idx * K + k_idx).long()                                 # (L,K,1)
        m_arr = (n_v.long() + delta) % N                                   # (L,K,N) long
        m_f = m_arr.to(torch.float64)
        angle = 2.0 * math.pi * (
            -float(c1) * l_idx.pow(2)
            + float(c2) * (m_f.pow(2) - n_v.pow(2))
            - l_idx * n_v / float(N)
        )                                                                  # (L,K,N) float64
        phase_re = torch.cos(angle).to(torch.float32 if cdtype == torch.complex64 else torch.float64)
        phase_im = torch.sin(angle).to(torch.float32 if cdtype == torch.complex64 else torch.float64)
        phase = torch.complex(phase_re, phase_im).to(cdtype)               # (L,K,N) cdtype

        # Flat scatter indices for H_flat[row*N + col] += contrib
        cols_LKN = torch.arange(N).view(1, 1, N).expand(L, K, N).long()    # (L,K,N)
        flat_idx = (m_arr * N + cols_LKN).reshape(-1)                      # (L*K*N,) long

        self.register_buffer('phase_LKN', phase.reshape(-1))               # (L*K*N,) cdtype
        self.register_buffer('flat_idx', flat_idx)                         # (L*K*N,) long

    def forward(self, g_dd: torch.Tensor) -> torch.Tensor:
        """g_dd: (L, K) complex → H_eff: (N, N) complex.

        Implementation: contribution per (l, k, n) is g_dd[l,k] · phase[l,k,n];
        scatter-add into H_flat at index (m_arr * N + n).
        """
        N = self.N
        device = g_dd.device
        # Broadcast g_dd over N: (L*K*1) × (1*N) → flat (L*K*N,)
        g_flat = g_dd.reshape(-1).unsqueeze(-1).expand(-1, N).reshape(-1)  # (L*K*N,)
        contrib = g_flat * self.phase_LKN                                  # (L*K*N,)
        H_flat = torch.zeros(N * N, dtype=self.cdtype, device=device)
        H_flat = H_flat.scatter_add(0, self.flat_idx.to(device), contrib)
        return H_flat.view(N, N)


def _reconstruct_H_from_dd(N: int, l_max: int, k_max: int,
                            g_dd: torch.Tensor, c1: float, c2: float,
                            cdtype: torch.dtype = torch.complex64) -> torch.Tensor:
    """Legacy slow Python-loop version, retained for tests. Use
    `_HReconstructor` for production training (vectorised, gradient-safe)."""
    device = g_dd.device
    K = 2 * k_max + 1
    L = l_max + 1
    H = torch.zeros((N, N), dtype=cdtype, device=device)
    n_arr = torch.arange(N, device=device, dtype=torch.float64)
    cols = torch.arange(N, device=device, dtype=torch.long)
    for l in range(L):
        for k_idx in range(K):
            k = k_idx - k_max
            delta = l * K + k
            m_arr = ((cols + delta) % N).to(torch.long)
            m_f = m_arr.to(torch.float64)
            angle = 2.0 * math.pi * (
                -float(c1) * (l ** 2)
                + float(c2) * (m_f.pow(2) - n_arr.pow(2))
                - float(l) * n_arr / float(N)
            )
            phase = torch.complex(torch.cos(angle), torch.sin(angle)).to(cdtype)
            g = g_dd[l, k_idx].to(cdtype)
            H[m_arr, cols] = H[m_arr, cols] + g * phase
    return H


class CENet_DDGrid(nn.Module):
    """CENet that outputs sparse DD-grid coefficients (L_max+1, K=2k_max+1)
    in complex from the SP observation (y, x_pilot, log σ²).

    Architecture (v2 — fixed from broken global-pool→MLP version):
    Per-position 1D U-Net keeps spatial info; final adaptive pool maps the
    spatial N-dim to the (L*K) DD-grid output. Each output bin is a learned
    weighted sum of nearby spatial features, instead of being decoded from
    a globally pooled vector.

    Input: (1, 5, N) — (Re y, Im y, Re pilot, Im pilot, log_σ²) — but the
    caller pre-multiplies the y channels with the SP-aware mask.
    Output: (L, K) complex — DD-grid coefficients.
    """

    def __init__(self, N: int, l_max: int, k_max: int, base_ch: int = 32):
        super().__init__()
        self.N = N
        self.l_max = l_max
        self.k_max = k_max
        self.L = l_max + 1
        self.K = 2 * k_max + 1
        out_dim = 2 * self.K   # per delay-bin output: K Doppler taps × 2 (Re/Im)
        # Per-position encoder: 1D conv chain keeping (B, C, N)
        self.enc = nn.Sequential(
            nn.Conv1d(5, base_ch, kernel_size=7, padding=3), nn.GELU(),
            nn.Conv1d(base_ch, base_ch * 2, kernel_size=7, padding=3), nn.GELU(),
            nn.Conv1d(base_ch * 2, base_ch * 4, kernel_size=7, padding=3), nn.GELU(),
            nn.Conv1d(base_ch * 4, out_dim, kernel_size=1),
        )
        # After enc: (1, 2K, N). Then adaptive-pool spatial N → L delay bins.
        # Each delay bin l aggregates evidence from a learned region of the
        # N-dim spatial signal — implicitly chirp-aware via spatial conv.
        self.pool = nn.AdaptiveAvgPool1d(self.L)
        # Small Xavier init on the 1×1 conv output, so g_dd starts near zero
        # but with gradient direction information from spatial features.
        nn.init.xavier_uniform_(self.enc[-1].weight, gain=0.05)
        nn.init.zeros_(self.enc[-1].bias)

    def forward(self, feats: torch.Tensor) -> torch.Tensor:
        """feats: (1, 5, N) → DD coefficients (L, K) complex."""
        h = self.enc(feats)                                    # (1, 2K, N)
        h = self.pool(h)                                       # (1, 2K, L)
        h = h.squeeze(0).transpose(0, 1)                       # (L, 2K)
        h = h.view(self.L, self.K, 2)                          # (L, K, 2)
        return torch.complex(h[..., 0], h[..., 1])             # (L, K) complex


class ThresholdNet(nn.Module):
    """Small NN that outputs a magnitude soft-mask separating pilot-dominant
    vs data-dominant positions in the SP observation. Mirrors OTFS-SP modular
    paper's ThresholdNet idea.

    Output: per-position mask m[n] ∈ (0, 1), where m[n] ≈ 1 ⇒ pilot-dominant
    (use for CE) and m[n] ≈ 0 ⇒ data-dominant (use for detection).
    """

    def __init__(self, hidden: int = 32):
        super().__init__()
        # Input: (|y|, |pilot|, log_sigma2) per position
        self.net = nn.Sequential(
            nn.Conv1d(3, hidden, kernel_size=5, padding=2), nn.GELU(),
            nn.Conv1d(hidden, hidden, kernel_size=5, padding=2), nn.GELU(),
            nn.Conv1d(hidden, 1, kernel_size=1),
        )
        # Small Xavier init last layer → mask varies slightly around 0.5 at
        # init based on input, giving gradient signal for ThresholdNet to
        # learn pilot/data magnitude separation.
        nn.init.xavier_uniform_(self.net[-1].weight, gain=0.1)
        nn.init.zeros_(self.net[-1].bias)

    def forward(self, y_abs: torch.Tensor, pilot_abs: torch.Tensor,
                log_sigma2: torch.Tensor) -> torch.Tensor:
        # All inputs (N,) → stack → (1, 3, N) → conv → (1, 1, N) → squeeze (N,)
        feats = torch.stack([y_abs, pilot_abs, log_sigma2], dim=0).unsqueeze(0)
        out = self.net(feats).squeeze(0).squeeze(0)
        return torch.sigmoid(out)


class OtfsModularReceiver(nn.Module):
    """E2: U-Net CENet outputs DD-grid coefficients → analytical chirp-formula
    H_eff reconstruction → differentiable LMMSE detector with full N×N channel.
    Optional ThresholdNet for SP pilot/data magnitude-based separation.

    Pipeline (per-frame, no batch dim):
      1. ThresholdNet (optional): magnitude-based soft mask m[n] ∈ (0, 1)
         indicating pilot-vs-data dominance per position.
      2. CENet_DDGrid: outputs sparse DD coefficients g_dd ∈ ℂ^(L+1, 2k_max+1).
      3. H_eff = _reconstruct_H_from_dd(g_dd; c1, c2): analytical chirp.
      4. y_data = y − H_eff · x_pilot  (SP cancellation)
      5. LMMSE: x̂ = (H_eff^H H_eff + σ² I)^{-1} H_eff^H y_data

    Gradients backprop through: detector → H_eff → g_dd → CENet weights
    AND optionally through threshold mask → ThresholdNet weights.
    """

    def __init__(self, N: int, l_max: int, k_max: int, base_ch: int = 32,
                 use_threshold: bool = True,
                 c1: float = 0.0, c2: float = 0.0,
                 cdtype: torch.dtype = torch.complex64):
        super().__init__()
        self.N = N
        self.l_max = l_max
        self.k_max = k_max
        self.use_threshold = use_threshold
        self.cenet = CENet_DDGrid(N=N, l_max=l_max, k_max=k_max, base_ch=base_ch)
        self.threshold = ThresholdNet(hidden=32) if use_threshold else None
        # Precompute H reconstructor (uses fixed c1, c2 buffers)
        self.h_recon = _HReconstructor(N=N, l_max=l_max, k_max=k_max,
                                        c1=c1, c2=c2, cdtype=cdtype)

    def forward(self, y_daft: torch.Tensor, x_pilot: torch.Tensor,
                sigma2: torch.Tensor, const: torch.Tensor,
                c1: float = 0.0, c2: float = 0.0) -> Dict:
        N = y_daft.shape[-1]
        device = y_daft.device
        cdtype = y_daft.dtype
        rdtype = y_daft.real.dtype
        log_sig = sigma2.clamp_min(1e-30).log().expand(N).to(rdtype)
        # ThresholdNet mask m[n] ∈ (0, 1)
        if self.threshold is not None:
            mask = self.threshold(y_daft.abs(), x_pilot.abs(), log_sig)
        else:
            mask = torch.ones(N, dtype=rdtype, device=device)
        # CENet input: mask-weighted (y, pilot, log_sigma2)
        feats = torch.stack([
            (y_daft.real * mask),
            (y_daft.imag * mask),
            x_pilot.real,
            x_pilot.imag,
            log_sig,
        ], dim=0).unsqueeze(0)                                 # (1, 5, N)
        g_dd = self.cenet(feats)                               # (L+1, K) complex
        H_eff = self.h_recon(g_dd)                             # (N, N) complex
        # Differentiable LMMSE detector
        y_data = y_daft - H_eff @ x_pilot
        H_H = H_eff.conj().T
        sigma2_c = sigma2.to(cdtype)
        # (H^H H + σ² I)  — N × N, complex
        gram = H_H @ H_eff + sigma2_c * torch.eye(N, dtype=cdtype, device=device)
        rhs = H_H @ y_data
        x_hat = torch.linalg.solve(gram, rhs)
        resnorm = (y_daft - H_eff @ (x_pilot + x_hat)).abs().pow(2).sum().to(rdtype)
        return dict(x_soft=x_hat, H_est=H_eff, g_dd=g_dd,
                    mask=mask,
                    x_soft_history=[x_hat],
                    resnorm_history=[resnorm])


# =====================================================================
# E3 — Full autoencoder (joint TX + RX learning)
# =====================================================================
class AutoencoderJointTxRx(nn.Module):
    """E3: E2 RX architecture + learnable TX side.

    TX-learnable parts (gradients flow back through frame generation):
      - Constellation: 4 learnable complex symbols (init QPSK, unit-power
        constraint applied each forward).
      - Pilot symbol scaling: 1 learnable complex value (init √ρ, |pilot|=√ρ
        constraint applied each forward).

    RX: identical to E2 (DD-grid CENet + ThresholdNet + analytical chirp
    H_eff + LMMSE).
    Joint train: BCE on bits propagates through RX → CENet weights AND
    through TX constellation/pilot via the frame generation step (handled
    in train_path_e.py for E3).
    """

    def __init__(self, N: int, l_max: int, k_max: int, base_ch: int = 32,
                 rho: float = 0.5, use_threshold: bool = True,
                 c1: float = 0.0, c2: float = 0.0,
                 cdtype: torch.dtype = torch.complex64):
        super().__init__()
        self.N = N
        self.l_max = l_max
        self.k_max = k_max
        self.rho = rho
        qpsk_init = torch.tensor(
            [(1 + 1j), (1 - 1j), (-1 + 1j), (-1 - 1j)],
            dtype=torch.complex64) / math.sqrt(2.0)
        self.constellation_re = nn.Parameter(qpsk_init.real)
        self.constellation_im = nn.Parameter(qpsk_init.imag)
        self.pilot_re = nn.Parameter(torch.tensor(math.sqrt(rho)))
        self.pilot_im = nn.Parameter(torch.tensor(0.0))
        self.rx = OtfsModularReceiver(N=N, l_max=l_max, k_max=k_max,
                                       base_ch=base_ch,
                                       use_threshold=use_threshold,
                                       c1=c1, c2=c2, cdtype=cdtype)

    def constellation(self) -> torch.Tensor:
        c = torch.complex(self.constellation_re, self.constellation_im)
        return c / c.abs().mean().clamp_min(1e-6)

    def pilot_symbol(self) -> torch.Tensor:
        p = torch.complex(self.pilot_re, self.pilot_im)
        return p * (math.sqrt(self.rho) / p.abs().clamp_min(1e-6))

    def forward(self, y_daft: torch.Tensor, x_pilot: torch.Tensor,
                sigma2: torch.Tensor, const: torch.Tensor,
                c1: float = 0.0, c2: float = 0.0) -> Dict:
        return self.rx(y_daft, x_pilot, sigma2, const, c1=c1, c2=c2)


def _build_phi_buffer(N: int, l_max: int, k_max: int,
                       x_pilot, c1: float, c2: float,
                       cdtype: torch.dtype = torch.complex64):
    """Module-level Phi builder, shared by Path A (HybridOMPRefiner) and
    Path B (TwoHeadCENet). Returns (Phi (N, L*K), col_norm_sq (L*K,))."""
    L = l_max + 1
    K = 2 * k_max + 1
    if not isinstance(x_pilot, torch.Tensor):
        x_pilot_t = torch.tensor(x_pilot, dtype=cdtype)
    else:
        x_pilot_t = x_pilot.to(cdtype)
    Phi = torch.zeros((N, L * K), dtype=cdtype)
    q_arr = torch.arange(N, dtype=torch.float64)
    col = 0
    for l in range(L):
        l_sq = float(l) ** 2
        l_f = float(l)
        for k_idx in range(K):
            k = k_idx - k_max
            delta = l * K + k
            p_arr = ((q_arr - delta) % N).to(torch.long)
            p_f = p_arr.to(torch.float64)
            angle = 2.0 * math.pi * (
                -float(c1) * l_sq
                + float(c2) * (q_arr.pow(2) - p_f.pow(2))
                - l_f * p_f / float(N)
            )
            phase = torch.complex(torch.cos(angle), torch.sin(angle)).to(cdtype)
            Phi[:, col] = phase * x_pilot_t[p_arr]
            col += 1
    col_norm_sq = (Phi.conj() * Phi).real.sum(dim=0)
    return Phi, col_norm_sq


# =====================================================================
# Path B (Phase 2) — Two-head support+gain decomposition
# =====================================================================
class TwoHeadCENet(nn.Module):
    """Path B: decouple sparse recovery into support classification + gain
    regression. Backbone reuses the Phi^H y matched-filter prior from Path A.

    Two parallel heads on per-bin features:
      - support_head: (L*K, 1) sigmoid logits → BCE against (|h_omp| > thr)
      - gain_head:    (L*K, 2) Re/Im → MSE against h_omp on active bins only

    Output: g_dd = sigmoid(support_logits) · gain_complex  (soft-gated)
    """

    def __init__(self, N: int, l_max: int, k_max: int,
                 x_pilot, c1: float, c2: float,
                 hidden: int = 64, cdtype: torch.dtype = torch.complex64):
        super().__init__()
        self.N = N
        self.l_max = l_max
        self.k_max = k_max
        self.L = l_max + 1
        self.K = 2 * k_max + 1
        self.cdtype = cdtype
        Phi, col_norm_sq = _build_phi_buffer(
            N, l_max, k_max, x_pilot, c1, c2, cdtype)
        rdtype = torch.float32 if cdtype == torch.complex64 else torch.float64
        self.register_buffer('Phi', Phi)
        self.register_buffer('col_norm_sq', col_norm_sq.to(rdtype))

        # Shared trunk over per-bin features
        self.trunk = nn.Sequential(
            nn.Linear(4, hidden), nn.GELU(),
            nn.Linear(hidden, hidden), nn.GELU(),
        )
        self.support_head = nn.Linear(hidden, 1)
        # init support_head so sigmoid(out) starts near 0.5 (neutral)
        nn.init.xavier_uniform_(self.support_head.weight, gain=0.1)
        nn.init.zeros_(self.support_head.bias)
        self.gain_head = nn.Linear(hidden, 2)
        nn.init.zeros_(self.gain_head.weight)
        nn.init.zeros_(self.gain_head.bias)

        self.h_recon = _HReconstructor(N=N, l_max=l_max, k_max=k_max,
                                        c1=c1, c2=c2, cdtype=cdtype)

    def forward(self, y_daft: torch.Tensor, x_pilot: torch.Tensor,
                sigma2: torch.Tensor, const: torch.Tensor,
                c1: float = 0.0, c2: float = 0.0) -> Dict:
        N = y_daft.shape[-1]
        device = y_daft.device
        cdtype = y_daft.dtype
        rdtype = y_daft.real.dtype

        Phi_H = self.Phi.conj().T
        mf = Phi_H @ y_daft
        mf_normalised = mf / self.col_norm_sq.to(cdtype)
        mf_LK = mf_normalised.view(self.L, self.K)
        log_sig = sigma2.clamp_min(1e-30).log().expand_as(mf_LK.real).to(rdtype)
        feats = torch.stack([
            mf_LK.real, mf_LK.imag, mf_LK.abs(), log_sig,
        ], dim=-1).view(-1, 4)                          # (L*K, 4)
        h = self.trunk(feats)                           # (L*K, hidden)
        supp_logit = self.support_head(h).view(self.L, self.K)  # (L, K) real
        # Soft-gate at init: sigmoid(supp_logit) ≈ 0.5 so gain_head's
        # zero-init output * 0.5 = 0; output starts at MF correlation only
        # via the residual baseline.
        supp_prob = torch.sigmoid(supp_logit).to(cdtype)
        gain_out = self.gain_head(h).view(self.L, self.K, 2)
        gain_c = torch.complex(gain_out[..., 0], gain_out[..., 1]).to(cdtype)

        # Composition: g_dd = mf_init + support_gate * gain_refinement
        # At init, gain=0 → g_dd = mf_init (MF correlation)
        # After training, support gates which bins to use and gain refines them
        g_dd = mf_LK + supp_prob * gain_c

        H_eff = self.h_recon(g_dd)
        y_data = y_daft - H_eff @ x_pilot
        H_H = H_eff.conj().T
        sigma2_c = sigma2.to(cdtype)
        gram = H_H @ H_eff + sigma2_c * torch.eye(N, dtype=cdtype, device=device)
        rhs = H_H @ y_data
        x_hat = torch.linalg.solve(gram, rhs)
        resnorm = (y_daft - H_eff @ (x_pilot + x_hat)).abs().pow(2).sum().to(rdtype)
        return dict(x_soft=x_hat, H_est=H_eff, g_dd=g_dd,
                    supp_logit=supp_logit, gain_c=gain_c,
                    x_soft_history=[x_hat], resnorm_history=[resnorm])


# =====================================================================
# Path A (Phase 2) — Hybrid OMP + NN refinement
# =====================================================================
class HybridOMPRefiner(nn.Module):
    """Path A: matched-filter correlation as inductive bias; small MLP refines.

    Pre-compute Phi sensing matrix at init (depends on c1, c2, x_pilot — all
    fixed across frames in our setup). At forward, compute Phi^H @ y_daft
    (classical OMP step 1) and treat as DD-grid prior. MLP outputs a small
    residual on top.

    Final output: g_dd = (Phi^H y) / ||Phi[:, col]||² + MLP_residual

    At init MLP_residual = 0, so the model behaves as a *dense matched-filter*
    pseudo-inverse — already a non-trivial AFDM channel estimate. Training
    learns to refine for SP data interference suppression.
    """

    def __init__(self, N: int, l_max: int, k_max: int,
                 x_pilot, c1: float, c2: float,
                 hidden: int = 64, cdtype: torch.dtype = torch.complex64):
        super().__init__()
        self.N = N
        self.l_max = l_max
        self.k_max = k_max
        self.L = l_max + 1
        self.K = 2 * k_max + 1
        self.cdtype = cdtype

        # Build Phi (sensing matrix) — same construction as classical OMP's
        # construct_sensing_matrix but as torch tensor and as a buffer.
        Phi, col_norm_sq = _build_phi_buffer(N, l_max, k_max, x_pilot,
                                              c1, c2, cdtype)
        self.register_buffer('Phi', Phi)              # (N, L*K)
        self.register_buffer('col_norm_sq',
                             col_norm_sq.to(self._rdtype()))  # (L*K,) real

        # Refiner MLP — per-bin (Re/Im of MF estimate, magnitude, log_σ²)
        # → small (Re, Im) residual gain. Zero-init final layer so MLP
        # outputs 0 at init and g_dd = pure matched-filter estimate.
        self.refine = nn.Sequential(
            nn.Linear(4, hidden), nn.GELU(),
            nn.Linear(hidden, hidden), nn.GELU(),
            nn.Linear(hidden, 2),
        )
        nn.init.zeros_(self.refine[-1].weight)
        nn.init.zeros_(self.refine[-1].bias)

        # H reconstructor (vectorised scatter)
        self.h_recon = _HReconstructor(N=N, l_max=l_max, k_max=k_max,
                                        c1=c1, c2=c2, cdtype=cdtype)

    def _rdtype(self) -> torch.dtype:
        return torch.float32 if self.cdtype == torch.complex64 else torch.float64

    @staticmethod
    def _build_phi(N: int, l_max: int, k_max: int,
                    x_pilot, c1: float, c2: float,
                    cdtype: torch.dtype):
        """Vectorised build of sensing matrix Phi (N, L*K) + col norm squares."""
        L = l_max + 1
        K = 2 * k_max + 1
        if not isinstance(x_pilot, torch.Tensor):
            x_pilot_t = torch.tensor(x_pilot, dtype=cdtype)
        else:
            x_pilot_t = x_pilot.to(cdtype)
        Phi = torch.zeros((N, L * K), dtype=cdtype)
        q_arr = torch.arange(N, dtype=torch.float64)
        col = 0
        for l in range(L):
            l_sq = float(l) ** 2
            l_f = float(l)
            for k_idx in range(K):
                k = k_idx - k_max
                delta = l * K + k
                p_arr = ((q_arr - delta) % N).to(torch.long)
                p_f = p_arr.to(torch.float64)
                angle = 2.0 * math.pi * (
                    -float(c1) * l_sq
                    + float(c2) * (q_arr.pow(2) - p_f.pow(2))
                    - l_f * p_f / float(N)
                )
                phase = torch.complex(torch.cos(angle), torch.sin(angle)).to(cdtype)
                Phi[:, col] = phase * x_pilot_t[p_arr]
                col += 1
        # column squared norms
        col_norm_sq = (Phi.conj() * Phi).real.sum(dim=0)         # (L*K,)
        return Phi, col_norm_sq

    def forward(self, y_daft: torch.Tensor, x_pilot: torch.Tensor,
                sigma2: torch.Tensor, const: torch.Tensor,
                c1: float = 0.0, c2: float = 0.0) -> Dict:
        N = y_daft.shape[-1]
        device = y_daft.device
        cdtype = y_daft.dtype
        rdtype = y_daft.real.dtype

        # Matched-filter correlation: Phi^H @ y → normalized by column-norm²
        # so initial estimate has approximately path-gain magnitude scale.
        Phi_H = self.Phi.conj().T                       # (L*K, N)
        mf = Phi_H @ y_daft                             # (L*K,) complex
        mf_normalised = mf / self.col_norm_sq.to(cdtype)  # (L*K,) ~ path-gain scale
        mf_LK = mf_normalised.view(self.L, self.K)      # (L, K) complex

        # Per-bin features for refiner MLP
        log_sig = sigma2.clamp_min(1e-30).log().expand_as(mf_LK.real).to(rdtype)
        feats = torch.stack([
            mf_LK.real, mf_LK.imag, mf_LK.abs(), log_sig,
        ], dim=-1)                                      # (L, K, 4)
        feats_flat = feats.view(-1, 4)                  # (L*K, 4)
        residual = self.refine(feats_flat).view(self.L, self.K, 2)
        residual_c = torch.complex(residual[..., 0], residual[..., 1]).to(cdtype)
        g_dd = mf_LK + residual_c                        # (L, K) complex

        # Build H_eff and run LMMSE
        H_eff = self.h_recon(g_dd)
        y_data = y_daft - H_eff @ x_pilot
        H_H = H_eff.conj().T
        sigma2_c = sigma2.to(cdtype)
        gram = H_H @ H_eff + sigma2_c * torch.eye(N, dtype=cdtype, device=device)
        rhs = H_H @ y_data
        x_hat = torch.linalg.solve(gram, rhs)
        resnorm = (y_daft - H_eff @ (x_pilot + x_hat)).abs().pow(2).sum().to(rdtype)
        return dict(x_soft=x_hat, H_est=H_eff, g_dd=g_dd,
                    x_soft_history=[x_hat], resnorm_history=[resnorm])


# =====================================================================
# Path F (Phase 2 extension) — Unrolled OMP-Net (K iterations)
# =====================================================================
class UnrolledOMPNet(nn.Module):
    """Path F: K-layer unrolled differentiable iterative OMP-like recovery.

    Architecture: K iterations of (residual correlation + learned refinement +
    update). At each iteration k=1..K:
      1. corr_k = Phi^H @ residual_k / ||col||²       (matched filter on residual)
      2. delta_k = MLP_k([corr_k, |corr_k|, log_σ²])  (learned per-iter update)
      3. g_{k+1} = g_k + delta_k                       (accumulate gains)
      4. residual_{k+1} = y - Phi @ g_{k+1}            (re-compute residual)

    Final: g_dd = g_K, H_eff via analytical chirp, LMMSE detector.

    The K=10 unrolled layers replicate classical OMP's K iterations of greedy
    refinement (correlate → pick → update) but as differentiable end-to-end
    operations, allowing the network to learn iterative sparse recovery beyond
    the single-pass ceiling.

    Optional weight sharing across iterations (untied=False ⇒ same MLP across K)
    or per-iter MLP (untied=True).
    """

    def __init__(self, N: int, l_max: int, k_max: int,
                 x_pilot, c1: float, c2: float,
                 K: int = 10, hidden: int = 64, untied: bool = False,
                 use_attention: bool = False, attn_heads: int = 4,
                 use_softsort_topk: bool = False, softsort_k: int = 10,
                 cdtype: torch.dtype = torch.complex64):
        super().__init__()
        self.N = N
        self.l_max = l_max
        self.k_max = k_max
        self.L = l_max + 1
        self.K_grid = 2 * k_max + 1
        self.K_iter = K
        self.cdtype = cdtype
        self.untied = untied
        self.use_attention = use_attention
        self.use_softsort_topk = use_softsort_topk
        self.softsort_k = softsort_k

        # Phi buffer
        Phi, col_norm_sq = _build_phi_buffer(N, l_max, k_max, x_pilot,
                                              c1, c2, cdtype)
        rdtype = torch.float32 if cdtype == torch.complex64 else torch.float64
        self.register_buffer('Phi', Phi)
        self.register_buffer('col_norm_sq', col_norm_sq.to(rdtype))

        # Iterative refiner — per-bin small MLP that takes
        # (Re/Im/mag of current correlation + log_σ²) → (Re, Im) gain delta.
        # Path J: optional self-attention block between encoder MLP and
        # decoder linear, letting each DD bin's update depend on all others.
        in_dim = 4  # Re(corr), Im(corr), |corr|, log σ²

        def _make_enc():
            # 2-layer MLP encoder: in_dim → hidden → hidden
            return nn.Sequential(
                nn.Linear(in_dim, hidden), nn.GELU(),
                nn.Linear(hidden, hidden), nn.GELU(),
            )

        def _make_dec():
            # 1-layer linear decoder: hidden → 2 (Re/Im delta)
            return nn.Linear(hidden, 2)

        def _make_attn():
            # Self-attention over (M=L*K_grid) bins
            return nn.MultiheadAttention(
                embed_dim=hidden, num_heads=attn_heads, batch_first=True)

        if untied:
            self.encoders = nn.ModuleList([_make_enc() for _ in range(K)])
            self.decoders = nn.ModuleList([_make_dec() for _ in range(K)])
            if use_attention:
                self.attns = nn.ModuleList([_make_attn() for _ in range(K)])
            for dec in self.decoders:
                nn.init.xavier_uniform_(dec.weight, gain=0.1)
                nn.init.zeros_(dec.bias)
        else:
            self.shared_enc = _make_enc()
            self.shared_dec = _make_dec()
            if use_attention:
                self.shared_attn = _make_attn()
            nn.init.xavier_uniform_(self.shared_dec.weight, gain=0.1)
            nn.init.zeros_(self.shared_dec.bias)

        # H reconstructor (vectorised scatter)
        self.h_recon = _HReconstructor(N=N, l_max=l_max, k_max=k_max,
                                        c1=c1, c2=c2, cdtype=cdtype)

    def _enc_at(self, k_iter: int) -> nn.Module:
        return self.encoders[k_iter] if self.untied else self.shared_enc

    def _dec_at(self, k_iter: int) -> nn.Module:
        return self.decoders[k_iter] if self.untied else self.shared_dec

    def _attn_at(self, k_iter: int):
        if not self.use_attention:
            return None
        return self.attns[k_iter] if self.untied else self.shared_attn


    def forward(self, y_daft: torch.Tensor, x_pilot: torch.Tensor,
                sigma2: torch.Tensor, const: torch.Tensor,
                c1: float = 0.0, c2: float = 0.0,
                softsort_tau: float = 1.0) -> Dict:
        N = y_daft.shape[-1]
        device = y_daft.device
        cdtype = y_daft.dtype
        rdtype = y_daft.real.dtype

        Phi = self.Phi
        Phi_H = Phi.conj().T                          # (L*K_grid, N)
        col_norm = self.col_norm_sq.to(cdtype)        # (L*K_grid,) complex

        # Initial: g = 0, residual = y
        g = torch.zeros(self.L * self.K_grid, dtype=cdtype, device=device)
        residual = y_daft.clone()

        log_sig = sigma2.clamp_min(1e-30).log().to(rdtype)

        # Track per-iter g_dd for deep supervision (Path G).
        g_dd_history: List[torch.Tensor] = []

        for k_iter in range(self.K_iter):
            # Correlate residual with Phi columns (matched filter on residual)
            corr = (Phi_H @ residual) / col_norm       # (L*K_grid,) complex
            # Build per-bin features (M, 4)
            log_sig_b = log_sig.expand_as(corr.real).to(rdtype)
            feats = torch.stack([
                corr.real, corr.imag, corr.abs(), log_sig_b,
            ], dim=-1)                                  # (L*K_grid, 4)
            # Encoder: per-bin MLP → hidden representation (M, hidden)
            h = self._enc_at(k_iter)(feats)
            # Path J: optional self-attention over DD bins. Each bin's
            # update conditioned on all other bins' hidden states.
            attn = self._attn_at(k_iter)
            if attn is not None:
                # MultiheadAttention expects (B, M, d) with batch_first.
                h_seq = h.unsqueeze(0)                  # (1, M, hidden)
                attn_out, _ = attn(h_seq, h_seq, h_seq, need_weights=False)
                h = h + attn_out.squeeze(0)             # residual add
            # Decoder: linear → (M, 2) Re/Im delta
            delta_2 = self._dec_at(k_iter)(h)
            # Path H: top-K support proposal via classical OMP score |corr|.
            # Following LGM / Softsort-OMP recipe (Cohen 2021, arXiv 2505.15661):
            # "hard classical select + soft learned gain" — selection uses the
            # classical OMP criterion (residual correlation magnitude), only
            # the gain refinement is learned. No separate learned score head
            # (cold-start unstable, as we observed in v1 of Path H).
            # STE: forward = hard top-K, backward = soft sigmoid surrogate.
            # Gradient flows back from soft_mask to corr → residual → previous
            # iter's g_dd → previous decoders, teaching them to set up
            # residuals whose energy concentrates at bins that should be active.
            if self.use_softsort_topk:
                scores_k = corr.abs().to(rdtype)            # (M,) magnitude
                # Hard top-K (forward path)
                topk_vals, indices = scores_k.topk(self.softsort_k)
                hard_mask = torch.zeros_like(scores_k)
                hard_mask[indices] = 1.0
                if self.training:
                    thresh = topk_vals.min().detach()
                    tau_clamped = max(float(softsort_tau), 1e-3)
                    soft_mask = torch.sigmoid((scores_k - thresh) / tau_clamped)
                    # STE: forward = hard, backward = soft (passes grad to corr)
                    mask = soft_mask + (hard_mask - soft_mask).detach()
                else:
                    mask = hard_mask
                delta_2 = delta_2 * mask.unsqueeze(-1)
            delta_c = torch.complex(delta_2[..., 0], delta_2[..., 1]).to(cdtype)
            # Accumulate
            g = g + delta_c
            # Update residual: y - Phi @ g
            residual = y_daft - Phi @ g
            # Snapshot per-iter g_dd for deep supervision
            g_dd_history.append(g.view(self.L, self.K_grid))

        # Final g_dd reshaped to (L, K_grid)
        g_dd = g.view(self.L, self.K_grid)

        # H_eff + LMMSE
        H_eff = self.h_recon(g_dd)
        y_data = y_daft - H_eff @ x_pilot
        H_H = H_eff.conj().T
        sigma2_c = sigma2.to(cdtype)
        gram = H_H @ H_eff + sigma2_c * torch.eye(N, dtype=cdtype, device=device)
        rhs = H_H @ y_data
        x_hat = torch.linalg.solve(gram, rhs)
        resnorm = (y_daft - H_eff @ (x_pilot + x_hat)).abs().pow(2).sum().to(rdtype)
        return dict(x_soft=x_hat, H_est=H_eff, g_dd=g_dd,
                    g_dd_history=g_dd_history,
                    x_soft_history=[x_hat], resnorm_history=[resnorm])


def count_params(m: nn.Module) -> int:
    return sum(p.numel() for p in m.parameters() if p.requires_grad)


__all__ = [
    'FixedTransformerReceiver',
    'DaftAwareTransformerReceiver',
    'OtfsModularReceiver',
    'AutoencoderJointTxRx',
    'HybridOMPRefiner',
    'TwoHeadCENet',
    'UnrolledOMPNet',
    'UNet1DCENet',
    'count_params',
]
