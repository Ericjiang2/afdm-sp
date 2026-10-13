"""
W8 Path C — NN replaces MP-BP convergence loop.

Three architecture choices, all targeting "1-step feedforward" or near-it
to match the iter=10 canonical TCOM headline BER. Trained end-to-end with
BCE_bits + MSE_symbols loss; supervised by ground-truth QPSK data.

C1: SimplestC — bootstrap receiver runs ONE outer iter (OMP-once +
    initial MP-BP), then a 1D U-Net refiner produces the final x_hat
    delta. ~100K params. Lowest reviewer risk (keeps AFDM frame +
    OMP geometric prior).

C2: AggressiveC — Transformer-only receiver. Input: y_daft + DAFT
    params + sigma2. Output: x_hat. Completely replaces OMP+MP+head
    pipeline. ~500K params. Highest reviewer risk ("you broke AFDM").

C3: HybridC — Keep OMP outer loop (cluster-expand + DA-LS gain refit)
    but replace the inner MP-BP loop with an NN that maps
    (y_daft, H_eff, support, x_init) → x_refined. 1 outer iter total.
    ~50K params. Middle reviewer risk.

All three plug into the same train_path_c.py loop.
"""
from __future__ import annotations

import math
from typing import Dict, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


# ======================================================================
# C1 — SimplestC: bootstrap + UNet1D refiner
# ======================================================================

class UNet1D(nn.Module):
    """Small 1D U-Net with depth=3. Input/output shape (B, C_in, N) →
    (B, C_out, N).
    """
    def __init__(self, in_ch: int = 3, out_ch: int = 2, base_ch: int = 32):
        super().__init__()
        # Encoder
        self.enc1 = self._block(in_ch, base_ch)              # N
        self.pool1 = nn.MaxPool1d(2)
        self.enc2 = self._block(base_ch, base_ch * 2)        # N/2
        self.pool2 = nn.MaxPool1d(2)
        self.enc3 = self._block(base_ch * 2, base_ch * 4)    # N/4
        # Bottleneck
        self.bot = self._block(base_ch * 4, base_ch * 4)
        # Decoder
        self.up3 = nn.ConvTranspose1d(base_ch * 4, base_ch * 2, 2, stride=2)
        self.dec3 = self._block(base_ch * 4, base_ch * 2)
        self.up2 = nn.ConvTranspose1d(base_ch * 2, base_ch, 2, stride=2)
        self.dec2 = self._block(base_ch * 2, base_ch)
        self.head = nn.Conv1d(base_ch, out_ch, kernel_size=1)
        # Zero-init final head so init is identity (no perturbation
        # from bootstrap output).
        nn.init.zeros_(self.head.weight)
        nn.init.zeros_(self.head.bias)

    @staticmethod
    def _block(in_c: int, out_c: int) -> nn.Sequential:
        return nn.Sequential(
            nn.Conv1d(in_c, out_c, kernel_size=5, padding=2),
            nn.GELU(),
            nn.Conv1d(out_c, out_c, kernel_size=5, padding=2),
            nn.GELU(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, C, N)
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool1(e1))
        e3 = self.enc3(self.pool2(e2))
        b = self.bot(e3)
        d3 = self.dec3(torch.cat([self.up3(b), e2], dim=1))
        d2 = self.dec2(torch.cat([self.up2(d3), e1], dim=1))
        return self.head(d2)


class SimplestC(nn.Module):
    """C1: bootstrap (frozen 1-iter receiver) + UNet1D refiner.

    The bootstrap is the existing ClassicalJointUnrolled run at
    n_outer_iter=1 with no learnable heads — it gives an initial
    x_soft + H_est estimate. The refiner ingests (Re x_soft, Im x_soft,
    log H column energy) and outputs (Re delta, Im delta).

    Final x_hat = x_init + delta.
    """
    def __init__(self, bootstrap: nn.Module, base_ch: int = 32):
        super().__init__()
        self.bootstrap = bootstrap
        for p in self.bootstrap.parameters():
            p.requires_grad_(False)
        self.refiner = UNet1D(in_ch=3, out_ch=2, base_ch=base_ch)

    def forward(self, y_daft: torch.Tensor, x_pilot: torch.Tensor,
                sigma2: torch.Tensor, const: torch.Tensor) -> Dict:
        with torch.no_grad():
            init = self.bootstrap(y_daft, x_pilot, sigma2, const)
        x0 = init['x_soft']                             # (N,) complex
        H = init['H_est']                               # (N,N) complex
        # Per-column energy (normalized log)
        H_energy = (H.abs().pow(2)).sum(dim=0)          # (N,)
        H_energy = torch.log(H_energy.clamp(min=1e-30))
        feats = torch.stack([x0.real, x0.imag, H_energy.to(x0.real.dtype)],
                            dim=0).unsqueeze(0)         # (1, 3, N)
        delta = self.refiner(feats).squeeze(0)          # (2, N)
        x_hat = x0 + torch.complex(delta[0], delta[1]).to(x0.dtype)
        return dict(x_soft=x_hat, H_est=H,
                    x_soft_history=[x_hat], resnorm_history=[
                        (y_daft - H @ (x_pilot + x_hat)).abs().pow(2).sum().to(
                            sigma2.dtype)
                    ])


# ======================================================================
# C2 — AggressiveC: Transformer receiver
# ======================================================================

class TransformerReceiver(nn.Module):
    """C2: encode y_daft + (c1, c2, sigma2) → x_hat directly. No OMP.

    Input projection: (Re, Im, |y|, sigma2_broadcast, c1_broadcast,
    c2_broadcast) → d_model.
    Architecture: depth-N transformer encoder over the N-token sequence.
    Output projection: d_model → (Re_x_hat, Im_x_hat).
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
        nn.init.zeros_(self.out_proj.weight)
        nn.init.zeros_(self.out_proj.bias)

    def forward(self, y_daft: torch.Tensor, x_pilot: torch.Tensor,
                sigma2: torch.Tensor, const: torch.Tensor,
                c1: float = 0.0, c2: float = 0.0) -> Dict:
        N = y_daft.shape[-1]
        assert N == self.N, f'Transformer fixed N={self.N}, got {N}'
        y_no_pilot = y_daft - x_pilot   # rough pilot-cancel
        sigma2_b = sigma2.expand(N).to(y_daft.real.dtype)
        c1_b = torch.full((N,), float(c1), device=y_daft.device,
                          dtype=y_daft.real.dtype)
        c2_b = torch.full((N,), float(c2), device=y_daft.device,
                          dtype=y_daft.real.dtype)
        feats = torch.stack([
            y_no_pilot.real, y_no_pilot.imag,
            y_no_pilot.abs(), sigma2_b, c1_b, c2_b
        ], dim=-1).unsqueeze(0)                          # (1, N, 6)
        h = self.in_proj(feats) + self.pos
        h = self.encoder(h)
        out = self.out_proj(h).squeeze(0)                # (N, 2)
        x_hat = torch.complex(out[:, 0], out[:, 1]).to(y_daft.dtype)
        # H_est is unavailable in pure-NN path; emit identity placeholder.
        H_id = torch.eye(N, dtype=y_daft.dtype, device=y_daft.device)
        return dict(x_soft=x_hat, H_est=H_id,
                    x_soft_history=[x_hat],
                    resnorm_history=[torch.tensor(0.0, device=y_daft.device,
                                                    dtype=sigma2.dtype)])


# ======================================================================
# C3 — HybridC: keep OMP, NN replaces inner MP-BP
# ======================================================================

class NNMessagePassing(nn.Module):
    """C3 inner: replace MP-BP with NN that conditions on (H_eff, y, x_init).

    Per symbol n, gather H[:, n] (column from active support) and predict
    a delta to x_init[n]. Implemented as a 1D ConvNet over the full (N,)
    sequence after per-position feature extraction.
    """
    def __init__(self, in_features: int = 7, hidden: int = 64, depth: int = 4):
        super().__init__()
        layers = [nn.Conv1d(in_features, hidden, kernel_size=5, padding=2),
                  nn.GELU()]
        for _ in range(depth - 1):
            layers += [nn.Conv1d(hidden, hidden, kernel_size=5, padding=2),
                       nn.GELU()]
        layers += [nn.Conv1d(hidden, 2, kernel_size=1)]
        self.net = nn.Sequential(*layers)
        # Zero-init final 1x1 conv → identity at init
        nn.init.zeros_(self.net[-1].weight)
        nn.init.zeros_(self.net[-1].bias)

    def forward(self, y_daft: torch.Tensor, H: torch.Tensor,
                x_init: torch.Tensor, x_pilot: torch.Tensor,
                sigma2: torch.Tensor) -> torch.Tensor:
        # Build per-position features
        res = y_daft - H @ (x_pilot + x_init)
        H_diag = (H.abs().pow(2)).sum(dim=0)
        sigma2_b = sigma2.expand_as(H_diag).to(H_diag.dtype)
        feats = torch.stack([
            x_init.real, x_init.imag,
            res.real, res.imag,
            H_diag, y_daft.abs(),
            sigma2_b,
        ], dim=0).unsqueeze(0)
        delta = self.net(feats.to(torch.float32)).squeeze(0)
        return torch.complex(delta[0], delta[1]).to(x_init.dtype)


class HybridC(nn.Module):
    """C3: 1-outer-iter receiver. OMP-once + DA-LS gives initial (x, H);
    then NNMessagePassing replaces MP-BP. No explicit n_outer_iter loop.

    Constructor takes a frozen ClassicalJointUnrolled bootstrap that runs
    iter=1 (OMP-once + 1 MP-BP) to provide x_init + H_eff.
    """
    def __init__(self, bootstrap: nn.Module, hidden: int = 64, depth: int = 4):
        super().__init__()
        self.bootstrap = bootstrap
        for p in self.bootstrap.parameters():
            p.requires_grad_(False)
        self.nn_mp = NNMessagePassing(in_features=7, hidden=hidden,
                                       depth=depth)

    def forward(self, y_daft: torch.Tensor, x_pilot: torch.Tensor,
                sigma2: torch.Tensor, const: torch.Tensor) -> Dict:
        with torch.no_grad():
            init = self.bootstrap(y_daft, x_pilot, sigma2, const)
        x0 = init['x_soft']
        H = init['H_est']
        delta = self.nn_mp(y_daft, H, x0, x_pilot, sigma2)
        x_hat = x0 + delta
        resnorm = (y_daft - H @ (x_pilot + x_hat)).abs().pow(2).sum().to(
            sigma2.dtype)
        return dict(x_soft=x_hat, H_est=H,
                    x_soft_history=[x_hat], resnorm_history=[resnorm])


# ======================================================================
# Param-count helper
# ======================================================================
def count_params(m: nn.Module) -> int:
    return sum(p.numel() for p in m.parameters() if p.requires_grad)


__all__ = ['UNet1D', 'SimplestC', 'TransformerReceiver',
            'NNMessagePassing', 'HybridC', 'count_params']
