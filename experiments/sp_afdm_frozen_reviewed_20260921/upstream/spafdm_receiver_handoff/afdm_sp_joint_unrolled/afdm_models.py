"""
afdm_models.py — PyTorch network architecture mixin for AFDM deep-unfolding.

Contains:
  - CEBackbone              (nn.Module: dual-stream CNN)
  - E2EModel                (nn.Module: CE + LMMSE + Demapper)
  - UnfoldingModel          (nn.Module: 2-stage deep-unfolding SIC)
  - AFDMModelsMixin         (mixin: builds / wraps the modules above)
    ├── build_dnn_model_full
    ├── build_e2e_model
    ├── build_e2e_unfolding_model
    ├── verify_differentiable_layers
    ├── diagnose_sic_physics   (pure NumPy — unchanged)
    └── diagnose_reconstruction (pure NumPy — unchanged)
"""

import copy
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from .afdm_layers import (Grid2DTo1DLayer, DiffRechirpLayer,
                           DiffReconstructLayer, DiffLMMSELayer,
                           DiffDemapperLayer, DiffRZFToGridLayer,
                           DiffSoftSICLayer, DifferentiableSoftThreshold,
                           SliceLayer, SymbolToGridLayer, QPSKPosterior,
                           OAMPNetDetector, EPNetDetector)


# ── helper ──────────────────────────────────────────────────────────────────

def _t(arr, dtype=torch.float32):
    """numpy → float32 tensor (no grad)."""
    return torch.from_numpy(np.asarray(arr, dtype=np.float32)).to(dtype)


def _detector_label(detector_type: str) -> str:
    detector_type = detector_type.lower()
    if detector_type == 'ep':
        return 'EP'
    if detector_type == 'oamp':
        return 'OAMP'
    raise ValueError(f"Unsupported detector_type={detector_type!r}")


def _build_soft_detector(detector_type, N, data_positions, num_layers):
    detector_type = detector_type.lower()
    if detector_type == 'oamp':
        return OAMPNetDetector(N, data_positions, num_layers=num_layers)
    if detector_type == 'ep':
        return EPNetDetector(N, data_positions, num_layers=num_layers)
    raise ValueError(f"Unsupported detector_type={detector_type!r}")


# ════════════════════════════════════════════════════════════════════════════
#  CEBackbone — physics-informed dual-stream 2D-CNN
# ════════════════════════════════════════════════════════════════════════════

class CEBackbone(nn.Module):
    """
    Dual-stream 2D-CNN with FiLM auxiliary conditioning and
    asymmetric dilated residual blocks.

    Input : (B, input_dim)   where input_dim = 2*L*W + aux_dim
    Output: (B, 2*L*W)       normalised  h_2d  [Re_flat | Im_flat]

    N=512 design:
      Grid (L_max=51, W=13, 2).  Asymmetric dilations d_H=[1,2,4,8,16]
      grow RF_H to 65 rows (> L_max) while keeping RF_W at 13 (= W).
    """
    def __init__(self, L_max, W, aux_dim=4, n_res=5):
        super().__init__()
        self.L_max, self.W, self.aux_dim = L_max, W, aux_dim

        # Stem (NCHW input channels = 2: Re + Im)
        self.stem_a    = nn.Conv2d(2, 64, (1, W), padding=(0, W // 2), bias=False)
        self.stem_b    = nn.Conv2d(2, 64, (3, 3), padding=(1, 1),      bias=False)
        self.stem_bn   = nn.BatchNorm2d(128, momentum=0.01)
        self.stem_fuse = nn.Conv2d(128, 128, (1, 1), bias=False)
        self.fuse_bn   = nn.BatchNorm2d(128, momentum=0.01)

        # FiLM
        self.aux_d1    = nn.Linear(aux_dim, 16)
        self.film_g    = nn.Linear(16, 128)
        self.film_b    = nn.Linear(16, 128)

        # Dilated ResBlocks
        _dh = [1, 2, 4, 8, 16]
        self.rc1 = nn.ModuleList([
            nn.Conv2d(128, 128, (3, 3),
                      padding=(_dh[i], 1), dilation=(_dh[i], 1), bias=False)
            for i in range(n_res)])
        self.rbn1 = nn.ModuleList([nn.BatchNorm2d(128, momentum=0.01)
                                   for _ in range(n_res)])
        self.rdrop = nn.ModuleList([nn.Dropout(0.15) for _ in range(n_res)])
        self.rc2  = nn.ModuleList([
            nn.Conv2d(128, 128, (3, 3),
                      padding=(_dh[i], 1), dilation=(_dh[i], 1), bias=False)
            for i in range(n_res)])
        self.rbn2 = nn.ModuleList([nn.BatchNorm2d(128, momentum=0.01)
                                   for _ in range(n_res)])

        # FFN + SE head
        self.ffn1    = nn.Conv2d(128, 128, (1, 1), bias=False)
        self.ffn_bn1 = nn.BatchNorm2d(128, momentum=0.01)
        self.ffn2    = nn.Conv2d(128, 64,  (1, 1), bias=False)
        self.ffn_bn2 = nn.BatchNorm2d(64,  momentum=0.01)
        self.se_fc1  = nn.Linear(64, 32)
        self.se_fc2  = nn.Linear(32, 64)
        self.conv_out   = nn.Conv2d(64, 2, (1, 1))
        self.soft_thr   = DifferentiableSoftThreshold()

    def forward(self, inp):
        L, W, gd = self.L_max, self.W, self.L_max * self.W
        tap  = inp[:, :gd * 2]
        aux  = inp[:, gd * 2 : gd * 2 + self.aux_dim]

        # (B, 2, L, W)
        x = torch.cat([tap[:, :gd].reshape(-1, 1, L, W),
                        tap[:, gd:].reshape(-1, 1, L, W)], dim=1)

        # Dual-stream stem
        x = torch.cat([self.stem_a(x), self.stem_b(x)], dim=1)
        x = F.relu(self.stem_bn(x))
        x = F.relu(self.fuse_bn(self.stem_fuse(x)))

        # FiLM
        ah  = F.relu(self.aux_d1(aux))
        fg  = F.softplus(self.film_g(ah)).unsqueeze(-1).unsqueeze(-1)
        fb  = self.film_b(ah).unsqueeze(-1).unsqueeze(-1)
        x   = x * fg + fb

        # 5× Asymmetric Dilated ResBlocks
        for i in range(5):
            sc = x
            x  = F.relu(self.rbn1[i](self.rc1[i](x)))
            x  = self.rdrop[i](x)
            x  = self.rbn2[i](self.rc2[i](x))
            x  = F.relu(x + sc)

        # FFN + SE
        x  = F.relu(self.ffn_bn1(self.ffn1(x)))
        x  = F.relu(self.ffn_bn2(self.ffn2(x)))
        se = torch.sigmoid(self.se_fc2(F.relu(self.se_fc1(x.mean(dim=[2, 3])))))
        x  = x * se.unsqueeze(-1).unsqueeze(-1)

        # Project → (B, 2, L, W) → soft-threshold → flatten
        x  = self.soft_thr(self.conv_out(x))
        return torch.cat([x[:, 0].reshape(-1, gd),
                          x[:, 1].reshape(-1, gd)], dim=-1)    # (B, 2*L*W)


# ════════════════════════════════════════════════════════════════════════════
#  E2EModel  — CE backbone + 4 differentiable physics layers
# ════════════════════════════════════════════════════════════════════════════

class E2EModel(nn.Module):
    """
    Inputs : inp_feat (B, input_dim), inp_y (B, 2N), inp_xp (B, 2N), inp_sigma (B,1)
    Outputs: dict  {'detection': x̂, 'bits': LLRs, 'channel_est': h_2d_scaled}
    """
    def __init__(self, ce_backbone, N, K_factor, k_max, L_max, W, pad_size,
                 data_positions, c1, c2, m0, l_max_cap, k_max_cap,
                 global_std_y=1.0):
        super().__init__()
        self.std_y      = float(global_std_y)
        self.backbone   = ce_backbone
        self.g2d        = Grid2DTo1DLayer(N, K_factor, k_max, L_max, W, pad_size)
        self.rechirp    = DiffRechirpLayer(N, c2, m0)
        self.reconstruct = DiffReconstructLayer(N, c1, c2, m0, l_max_cap, k_max_cap)
        self.lmmse      = DiffLMMSELayer(N, data_positions)
        self.demapper   = DiffDemapperLayer(len(data_positions))

    def forward(self, inp_feat, inp_y, inp_xp, inp_sigma):
        h_sc   = self.backbone(inp_feat)
        h_2d   = h_sc * self.std_y
        H_flat = self.reconstruct(self.rechirp(self.g2d(h_2d)))
        x_hat, v_x = self.lmmse([H_flat, inp_y, inp_xp, inp_sigma])
        return {'detection':   x_hat,
                'v_x':         v_x,
                'bits':        self.demapper(x_hat, v_x=v_x),
                'channel_est': h_sc}


# ════════════════════════════════════════════════════════════════════════════
#  E2EOAMPModel  — CE backbone + OAMPNetDetector (replaces LMMSE+Demapper)
# ════════════════════════════════════════════════════════════════════════════

class E2EOAMPModel(nn.Module):
    """
    Drop-in replacement for E2EModel that uses OAMPNetDetector instead
    of DiffLMMSELayer + DiffDemapperLayer.

    OAMPNetDetector internally handles:
      - Pilot cancellation (was inside DiffLMMSELayer)
      - Iterative OAMP detection (T=4 unrolled layers)
      - QPSK posterior (was DiffDemapperLayer)

    Learnable parameters: CE backbone (~1.5M) + OAMP (2*T + 1 = 9 for T=4)
    Forward output dict is identical to E2EModel for training compatibility.

    Inputs : inp_feat (B, input_dim), inp_y (B, 2N), inp_xp (B, 2N), inp_sigma (B,1)
    Outputs: dict  {'detection': x_hat, 'v_x': v_x, 'bits': LLRs, 'channel_est': h_sc}
    """
    def __init__(self, ce_backbone, N, K_factor, k_max, L_max, W, pad_size,
                 data_positions, c1, c2, m0, l_max_cap, k_max_cap,
                 global_std_y=1.0, num_oamp_layers=4):
        super().__init__()
        self.std_y        = float(global_std_y)
        self.backbone     = ce_backbone
        self.g2d          = Grid2DTo1DLayer(N, K_factor, k_max, L_max, W, pad_size)
        self.rechirp      = DiffRechirpLayer(N, c2, m0)
        self.reconstruct  = DiffReconstructLayer(N, c1, c2, m0, l_max_cap, k_max_cap)
        self.oamp         = OAMPNetDetector(N, data_positions, num_layers=num_oamp_layers)

    def forward(self, inp_feat, inp_y, inp_xp, inp_sigma):
        h_sc   = self.backbone(inp_feat)
        h_2d   = h_sc * self.std_y
        H_flat = self.reconstruct(self.rechirp(self.g2d(h_2d)))
        x_hat, v_x, llr = self.oamp([H_flat, inp_y, inp_xp, inp_sigma])
        return {'detection':   x_hat,
                'v_x':         v_x,
                'bits':        llr,
                'channel_est': h_sc}


class E2EEPModel(nn.Module):
    """
    CE backbone + EPNetDetector with the same output contract as E2EModel.
    """
    def __init__(self, ce_backbone, N, K_factor, k_max, L_max, W, pad_size,
                 data_positions, c1, c2, m0, l_max_cap, k_max_cap,
                 global_std_y=1.0, num_ep_layers=4):
        super().__init__()
        self.std_y = float(global_std_y)
        self.backbone = ce_backbone
        self.g2d = Grid2DTo1DLayer(N, K_factor, k_max, L_max, W, pad_size)
        self.rechirp = DiffRechirpLayer(N, c2, m0)
        self.reconstruct = DiffReconstructLayer(N, c1, c2, m0, l_max_cap, k_max_cap)
        self.ep = EPNetDetector(N, data_positions, num_layers=num_ep_layers)

    def forward(self, inp_feat, inp_y, inp_xp, inp_sigma):
        h_sc = self.backbone(inp_feat)
        h_2d = h_sc * self.std_y
        H_flat = self.reconstruct(self.rechirp(self.g2d(h_2d)))
        x_hat, v_x, llr = self.ep([H_flat, inp_y, inp_xp, inp_sigma])
        return {'detection':   x_hat,
                'v_x':         v_x,
                'bits':        llr,
                'channel_est': h_sc}


# ════════════════════════════════════════════════════════════════════════════
#  UnfoldingModel  — 2-stage deep-unfolding SIC
# ════════════════════════════════════════════════════════════════════════════

class UnfoldingModel(nn.Module):
    """
    Stage-1 + SIC + Stage-2 (SP full-domain ZC version).

    Returns 6-tuple:
      (bits_s1, det_s1, ce_s1, bits_s2, det_s2, ce_s2)
    """
    def __init__(self, ce_backbone_1, ce_backbone_2,
                 N, K_factor, k_max, L_max, W, pad_size,
                 data_positions, W_match_s2, delta_idx_flat,
                 c1, c2, m0, rho, l_max_cap, k_max_cap,
                 global_std_y=1.0, global_std_X=1.0,
                 sic_mode='soft'):
        super().__init__()
        self.std_y   = float(global_std_y)
        self.std_x   = float(global_std_X)
        self.grid_dim = L_max * W * 2

        self.ce_s1 = ce_backbone_1
        self.ce_s2 = ce_backbone_2

        sa = (N, K_factor, k_max, L_max, W, pad_size)
        ra = (N, c1, c2, m0, l_max_cap, k_max_cap)
        n  = len(data_positions)

        self.g2d_s1     = Grid2DTo1DLayer(*sa)
        self.rch_s1     = DiffRechirpLayer(N, c2, m0)
        self.rec_s1     = DiffReconstructLayer(*ra)
        self.lmm_s1     = DiffLMMSELayer(N, data_positions)
        self.demap_s1   = DiffDemapperLayer(n)

        self.sic        = DiffSoftSICLayer(N, rho=rho, sic_mode=sic_mode)
        self.rzf_s2     = DiffRZFToGridLayer(N, L_max, W, W_match_s2,
                                              delta_idx_flat, c2, m0)

        self.g2d_s2     = Grid2DTo1DLayer(*sa)
        self.rch_s2     = DiffRechirpLayer(N, c2, m0)
        self.rec_s2     = DiffReconstructLayer(*ra)
        self.lmm_s2     = DiffLMMSELayer(N, data_positions)
        self.demap_s2   = DiffDemapperLayer(n)

    def forward(self, inp_feat, inp_y, inp_xp, inp_sigma):
        # ═ Stage 1 ═══════════════════════════════════════════════════════════════════
        ce_out_s1 = self.ce_s1(inp_feat)
        H_s1      = self.rec_s1(self.rch_s1(self.g2d_s1(ce_out_s1 * self.std_y)))
        x_s1, v_s1 = self.lmm_s1([H_s1, inp_y, inp_xp, inp_sigma])

        # ═ SIC (pass v_s1 for mmse mode; ignored in soft/qpsk_proj) ═══════════════
        y_clean = self.sic([H_s1, x_s1, inp_y, v_s1])

        # ═ Stage-2 features ══════════════════════════════════════════════════════
        grid_s2  = self.rzf_s2(y_clean) / self.std_x
        feat_s2  = torch.cat([grid_s2, inp_feat[:, self.grid_dim:]], dim=-1)

        # ═ Stage 2 ═══════════════════════════════════════════════════════════════════
        ce_out_s2 = self.ce_s2(feat_s2)
        H_s2      = self.rec_s2(self.rch_s2(self.g2d_s2(ce_out_s2 * self.std_y)))
        x_s2, v_s2 = self.lmm_s2([H_s2, inp_y, inp_xp, inp_sigma])

        return (self.demap_s1(x_s1, v_x=v_s1), x_s1, ce_out_s1,
                self.demap_s2(x_s2, v_x=v_s2), x_s2, ce_out_s2)


# ════════════════════════════════════════════════════════════════════════════
#  ChannelRefiner — lightweight 3-block correction CNN
# ════════════════════════════════════════════════════════════════════════════

class ChannelRefiner(nn.Module):
    """
    Lightweight 3-block asymmetric dilated ResNet that predicts a
    channel correction ΔH on the 2D delay-Doppler grid.

    Input : (B, C_in, L_max, W)  — stacked soft-information channels
    Output: (B, 2,    L_max, W)  — correction ΔH [Re | Im]

    Default C_in=8 corresponds to:
      feat_residual(2) + feat_h1(2) + feat_mu_x(2) + feat_vx(1) + feat_llr(1)
    """
    def __init__(self, L_max, W, C_in=8, n_res=3):
        super().__init__()
        self.L_max, self.W = L_max, W

        # Stem
        self.stem    = nn.Conv2d(C_in, 64, (3, 3), padding=(1, 1), bias=False)
        self.stem_bn = nn.BatchNorm2d(64, momentum=0.01)

        # 3× Asymmetric Dilated ResBlocks, dilation_H=[1,2,4], dilation_W=1
        _dh = [1, 2, 4]
        self.rc1   = nn.ModuleList([
            nn.Conv2d(64, 64, (3, 3),
                      padding=(_dh[i], 1), dilation=(_dh[i], 1), bias=False)
            for i in range(n_res)])
        self.rbn1  = nn.ModuleList([nn.BatchNorm2d(64, momentum=0.01)
                                    for _ in range(n_res)])
        self.rdrop = nn.ModuleList([nn.Dropout(0.10) for _ in range(n_res)])
        self.rc2   = nn.ModuleList([
            nn.Conv2d(64, 64, (3, 3),
                      padding=(_dh[i], 1), dilation=(_dh[i], 1), bias=False)
            for i in range(n_res)])
        self.rbn2  = nn.ModuleList([nn.BatchNorm2d(64, momentum=0.01)
                                    for _ in range(n_res)])

        # Output head: project to 2 channels (raw delta_H).
        # Default Kaiming init (PyTorch Conv2d default) gives healthy
        # gradient magnitudes. Safety during Deep Unrolling is ensured
        # by the per-iteration refine_scale (alpha) in JointTurboReceiver,
        # which starts at 0 and lets the network smoothly ramp up delta_H.
        self.conv_out  = nn.Conv2d(64, 2, (1, 1))

    def forward(self, feat):
        # feat: (B, C_in, L, W)
        x = F.relu(self.stem_bn(self.stem(feat)))
        for i in range(len(self.rc1)):
            sc = x
            x  = F.relu(self.rbn1[i](self.rc1[i](x)))
            x  = self.rdrop[i](x)
            x  = self.rbn2[i](self.rc2[i](x))
            x  = F.relu(x + sc)
        return self.conv_out(x)    # (B, 2, L, W) raw delta_H


# ════════════════════════════════════════════════════════════════════════════
#  TurboRefinerModel — frozen Stage-1 E2E + soft-feature extractor +
#                      trainable ChannelRefiner
# ════════════════════════════════════════════════════════════════════════════

class TurboRefinerModel(nn.Module):
    """
    Turbo-AI receiver: frozen Stage-1 E2EModel feeds soft information
    (mu_x, v_x, |LLR|, residual y) into a trainable ChannelRefiner
    to produce a refined Stage-2 channel estimate H_hat_2.

    Training target: MSE( channel_est_s2 , y_ce_labels )
    (same normalised 2D-grid MSE as Phase-1 CE pre-training).

    Forward returns dict:
      'channel_est_s1' : (B, 2*L*W)  Stage-1 CE output (scaled, for loss logging)
      'channel_est_s2' : (B, 2*L*W)  Stage-2 CE output (scaled, for MSE loss)
      'h_2d_s2'        : (B, 2*L*W)  Stage-2 physical CE (unscaled)

    Stage-1 is fully frozen: its parameters receive no gradients.
    """
    def __init__(self, e2e_s1,
                 N, K_factor, k_max, L_max, W, pad_size,
                 data_positions, W_match_s2, delta_idx_flat,
                 c1, c2, m0, l_max_cap, k_max_cap,
                 global_std_y=1.0):
        super().__init__()
        self.std_y  = float(global_std_y)
        self.L_max  = L_max
        self.W      = W
        self.N      = N

        # ── Stage-1 (frozen) ──────────────────────────────────────────────
        self.e2e_s1 = e2e_s1
        for p in self.e2e_s1.parameters():
            p.requires_grad = False

        # ── Soft-feature helper layers (no learnable params) ──────────────
        self.qpsk_post  = QPSKPosterior()
        self.sym2grid   = SymbolToGridLayer(N, K_factor, k_max, L_max, W, pad_size)
        self.rzf2grid   = DiffRZFToGridLayer(N, L_max, W, W_match_s2,
                                              delta_idx_flat, c2, m0)

        # ── Trainable ChannelRefiner ──────────────────────────────────────
        self.refiner = ChannelRefiner(L_max, W, C_in=8)

    @staticmethod
    def _blk_matvec(H_flat, x_2n):
        """(B, 2N², B, 2N) → (B, 2N): block-real H @ x."""
        N = x_2n.shape[1] // 2
        Hr = H_flat[:, :N * N].view(-1, N, N)
        Hi = H_flat[:, N * N:].view(-1, N, N)
        xr = x_2n[:, :N].unsqueeze(-1)    # (B, N, 1)
        xi = x_2n[:, N:].unsqueeze(-1)
        yr = (torch.bmm(Hr, xr) - torch.bmm(Hi, xi)).squeeze(-1)  # (B, N)
        yi = (torch.bmm(Hr, xi) + torch.bmm(Hi, xr)).squeeze(-1)
        return torch.cat([yr, yi], dim=-1)  # (B, 2N)

    def forward(self, inp_feat, inp_y, inp_xp, inp_sigma):
        L, W, std_y = self.L_max, self.W, self.std_y

        # ── Stage-1 (frozen) ─────────────────────────────────────────────
        with torch.no_grad():
            h_sc_1 = self.e2e_s1.backbone(inp_feat)          # (B, 2*L*W)
            h_2d_1 = h_sc_1 * std_y
            H_flat = self.e2e_s1.reconstruct(
                         self.e2e_s1.rechirp(
                             self.e2e_s1.g2d(h_2d_1)))        # (B, 2N²)
            x_hat_1, v_x_1 = self.e2e_s1.lmmse(
                         [H_flat, inp_y, inp_xp, inp_sigma])  # (B, 2N) each
            llr_1 = self.e2e_s1.demapper(x_hat_1, v_x=v_x_1) # (B, 2N)

        # ── QPSK posterior mean mu_x ──────────────────────────────────────
        N = self.N
        z   = torch.stack([x_hat_1[:, :N], x_hat_1[:, N:]], dim=-1)  # (B, N, 2)
        vv  = v_x_1[:, :N].unsqueeze(-1)                              # (B, N, 1)
        mu_x_bn, _, _ = self.qpsk_post(z, vv)                         # (B, N, 2)
        mu_x_flat = torch.cat([mu_x_bn[:, :, 0], mu_x_bn[:, :, 1]], dim=-1)  # (B, 2N)

        # ── Residual: y − H_hat_1 @ (x_p + mu_x) ────────────────────────
        x_total = inp_xp + mu_x_flat                           # (B, 2N)
        y_res   = inp_y - self._blk_matvec(H_flat, x_total)   # (B, 2N)

        # ── 8-channel feature tensor (B, 8, L, W) ─────────────────────────
        # Channel 0-1: residual through RZF matched filter
        feat_res = self.rzf2grid(y_res)                        # (B, 2*L*W)
        feat_res = feat_res[:, :L * W].view(-1, 1, L, W), \
                   feat_res[:, L * W:].view(-1, 1, L, W)
        feat_res = torch.cat(feat_res, dim=1)                  # (B, 2, L, W)

        # Channel 2-3: Stage-1 h_2d (physical scale)
        feat_h1 = h_2d_1[:, :L * W].view(-1, 1, L, W), \
                  h_2d_1[:, L * W:].view(-1, 1, L, W)
        feat_h1 = torch.cat(feat_h1, dim=1)                    # (B, 2, L, W)

        # Channel 4-5: mu_x mapped to grid
        feat_mu = self.sym2grid(mu_x_flat, mode='complex')     # (B, 2, L, W)

        # Channel 6: v_x (Re-component) mapped to grid
        feat_vx = self.sym2grid(v_x_1[:, :N], mode='real')    # (B, 1, L, W)

        # Channel 7: |LLR| confidence (mean of |b0-LLR| and |b1-LLR| per symbol)
        llr_conf = (llr_1[:, :N].abs() + llr_1[:, N:].abs()) * 0.5  # (B, N)
        feat_llr = self.sym2grid(llr_conf, mode='real')        # (B, 1, L, W)

        feat_all = torch.cat([feat_res, feat_h1, feat_mu,
                              feat_vx, feat_llr], dim=1)       # (B, 8, L, W)

        # ── Refiner: predict ΔH and add residual correction ──────────────
        delta_h = self.refiner(feat_all)                       # (B, 2, L, W)
        h_2d_s2 = h_2d_1[:, :L * W].view(-1, 1, L, W), \
                  h_2d_1[:, L * W:].view(-1, 1, L, W)
        h_2d_s2 = torch.cat(h_2d_s2, dim=1) + delta_h         # (B, 2, L, W) residual skip
        h_2d_s2_flat = torch.cat([
            h_2d_s2[:, 0].reshape(-1, L * W),
            h_2d_s2[:, 1].reshape(-1, L * W)], dim=-1)        # (B, 2*L*W) physical
        h_sc_s2 = h_2d_s2_flat / std_y                        # normalised (for loss)

        return {'channel_est_s1': h_sc_1,
                'channel_est_s2': h_sc_s2,
                'h_2d_s2':        h_2d_s2_flat}


# ════════════════════════════════════════════════════════════════════════════
#  JointTurboReceiver — deep-unrolled OAMP ↔ ChannelRefiner outer loop
# ════════════════════════════════════════════════════════════════════════════

class JointTurboReceiver(nn.Module):
    """
    Stage-4: Outer Turbo Loop that alternates T times between:
      1. OAMPNetDetector  — iterative symbol detection (inner OAMP + Onsager)
      2. ChannelRefiner   — CNN residual channel correction

    Each outer iteration has INDEPENDENT parameters (separate OAMP scalars
    and Refiner CNN weights), giving the network maximum flexibility to learn
    iteration-specific processing strategies.

    Layer-wise supervision: forward returns history of all T outputs so the
    training loss can supervise every iteration separately.

    Learnable parameters:
      T × OAMPNetDetector (each: 2*num_oamp_layers + 1 ≈ 9 params for T=3)
      T × ChannelRefiner  (each: ~64k params)
      1 × CEBackbone      (~1.5M params)
      Total ≈ 1.5M + 3*(9+64k) ≈ 1.7M params

    Forward inputs:  inp_feat (B, input_dim), inp_y (B, 2N),
                     inp_xp   (B, 2N),         inp_sigma (B, 1)
    Forward output:  dict with history lists + final_ convenience keys
    """
    def __init__(self, ce_backbone,
                 N, K_factor, k_max, L_max, W, pad_size,
                 data_positions, W_match_s2, delta_idx_flat,
                 c1, c2, m0, l_max_cap, k_max_cap,
                 global_std_y=1.0,
                 num_outer_iters=3,
                 num_oamp_layers=4,
                 detector_type='oamp'):
        super().__init__()
        self.std_y     = float(global_std_y)
        self.L_max     = L_max
        self.W         = W
        self.N         = N
        self.T         = num_outer_iters
        self.detector_type = detector_type.lower()

        # ── Shared CE backbone (converts input features → h_2d) ───────────
        self.backbone   = ce_backbone

        # ── Shared geometry layers (no learnable params) ──────────────────
        sa = (N, K_factor, k_max, L_max, W, pad_size)
        ra = (N, c1, c2, m0, l_max_cap, k_max_cap)
        self.g2d        = Grid2DTo1DLayer(*sa)
        self.rechirp    = DiffRechirpLayer(N, c2, m0)
        self.reconstruct= DiffReconstructLayer(*ra)

        # ── Per-iteration independent OAMP detectors ──────────────────────
        self.detectors  = nn.ModuleList([
            _build_soft_detector(self.detector_type, N, data_positions,
                                 num_layers=num_oamp_layers)
            for _ in range(num_outer_iters)])

        # ── Per-iteration independent Channel Refiners ────────────────────
        self.refiners   = nn.ModuleList([
            ChannelRefiner(L_max, W, C_in=14)
            for _ in range(num_outer_iters)])

        # ── Learnable alpha-scales for residual connection ────────────────
        # Each scale starts at 0 → delta_H has zero effect on epoch 0.
        # Refiner backbone uses standard Kaiming init (full-rank gradients),
        # the scale is the only thing that ramps up.  A single scalar per
        # iteration can grow from 0 to 1 in just a few gradient steps.
        #   h_new = h_prev + alpha_t * refiner_t(feat)
        self.refine_scales = nn.ParameterList([
            nn.Parameter(torch.zeros(1)) for _ in range(num_outer_iters)])
        self.gate_conf_gains = nn.ParameterList([
            nn.Parameter(torch.tensor(1.0)) for _ in range(num_outer_iters)])
        self.gate_vx_gains = nn.ParameterList([
            nn.Parameter(torch.tensor(2.0)) for _ in range(num_outer_iters)])
        self.gate_biases = nn.ParameterList([
            nn.Parameter(torch.tensor(-1.0)) for _ in range(num_outer_iters)])

        # ── Shared soft-feature helper layers (no learnable params) ───────
        self.qpsk_post  = QPSKPosterior()
        self.sym2grid   = SymbolToGridLayer(N, K_factor, k_max, L_max, W, pad_size)
        self.rzf2grid   = DiffRZFToGridLayer(N, L_max, W, W_match_s2,
                                              delta_idx_flat, c2, m0)
        # NOTE: No soft_thr here. The CE backbone already enforces DD-domain
        # sparsity in normalised space where tau/signal ≈ 0.04 (appropriate).
        # In physical space tau ≈ 0.127 vs |h| ≈ 0.05–0.14 → 90% of taps land
        # in the dead zone → gradient blocked → Refiner learns identity.
        # Refiner corrects dense data interference, not sparse channel,
        # so pure residual addition is the correct physics.

    @staticmethod
    def _blk_matvec(H_flat, x_2n):
        """Block-real (B, 2N²) × (B, 2N) → (B, 2N): H @ x."""
        N  = x_2n.shape[1] // 2
        Hr = H_flat[:, :N * N].view(-1, N, N)
        Hi = H_flat[:, N * N:].view(-1, N, N)
        xr = x_2n[:, :N].unsqueeze(-1)
        xi = x_2n[:, N:].unsqueeze(-1)
        yr = (torch.bmm(Hr, xr) - torch.bmm(Hi, xi)).squeeze(-1)
        yi = (torch.bmm(Hr, xi) + torch.bmm(Hi, xr)).squeeze(-1)
        return torch.cat([yr, yi], dim=-1)

    def _h2d_to_H_flat(self, h_2d_flat):
        """(B, 2*L*W) physical scale → (B, 2*N²) H_flat matrix."""
        return self.reconstruct(self.rechirp(self.g2d(h_2d_flat)))

    def _grid_2ch(self, flat_2lw):
        L, W = self.L_max, self.W
        return torch.cat([
            flat_2lw[:, :L * W].view(-1, 1, L, W),
            flat_2lw[:, L * W:].view(-1, 1, L, W)], dim=1)

    def _compute_refine_gate(self, t, llr_conf, v_x_t):
        conf_mean = llr_conf.mean(dim=-1, keepdim=True)
        vx_mean   = v_x_t[:, :self.N].mean(dim=-1, keepdim=True)
        conf_gain = F.softplus(self.gate_conf_gains[t]) + 1e-3
        vx_gain   = F.softplus(self.gate_vx_gains[t]) + 1e-3
        gate_logit = conf_gain * conf_mean - vx_gain * vx_mean + self.gate_biases[t]
        return torch.sigmoid(gate_logit).view(-1, 1, 1, 1)

    def forward(self, inp_feat, inp_y, inp_xp, inp_sigma):
        L, W, std_y = self.L_max, self.W, self.std_y
        N = self.N

        # ── Initial CE: backbone → H_flat ─────────────────────────────────
        h_sc_0  = self.backbone(inp_feat)             # (B, 2*L*W) normalised
        h_2d_t  = h_sc_0 * std_y                      # (B, 2*L*W) physical
        H_flat_t = self._h2d_to_H_flat(h_2d_t)       # (B, 2*N²)

        # History buffers — one entry per outer iteration
        history_h_sc    = []   # normalised refined CE (B, 2*L*W)
        history_llr     = []   # detection LLR (B, 2N)
        history_det     = []   # x_hat / posterior mean (B, 2N)
        history_mu      = []   # soft symbol mean used by refiner/loss (B, 2N)
        history_vx      = []   # v_x   (B, 2N)
        history_H_pre   = []   # detector input H_t        (B, 2N²)
        history_H_post  = []   # refined channel H_{t+1}   (B, 2N²)
        history_gate    = []   # confidence / low-SNR gate (B, 1)

        mu_prev_flat = None
        v_prev_flat  = None
        llr_a_flat   = None

        for t in range(self.T):
            # ── 1. OAMP detection ─────────────────────────────────────────
            det_inputs = [H_flat_t, inp_y, inp_xp, inp_sigma]
            if mu_prev_flat is not None:
                det_inputs.extend([mu_prev_flat, v_prev_flat, llr_a_flat])
            x_hat_t, v_x_t, llr_t = self.detectors[t](det_inputs)
            # x_hat_t/v_x_t/llr_t each (B, 2N) block-real

            history_det.append(x_hat_t)
            history_vx.append(v_x_t)
            history_llr.append(llr_t)
            history_H_pre.append(H_flat_t)

            # ── 2. Detector already returns posterior mean x_hat_t ───────
            mu_x_flat = x_hat_t
            history_mu.append(mu_x_flat)

            # ── 3. Residual decomposition for task-oriented refiner ──────
            H_xp = self._blk_matvec(H_flat_t, inp_xp)
            H_mu = self._blk_matvec(H_flat_t, mu_x_flat)
            y_pilot_clean = inp_y - H_xp
            y_res = y_pilot_clean - H_mu
            delta_mu_flat = mu_x_flat if mu_prev_flat is None else (mu_x_flat - mu_prev_flat)

            # ── 4. Build 14-channel turbo feature tensor (B, 14, L, W) ───
            # Ch 0-1: final residual y - H(xp + mu)
            feat_res_flat = self.rzf2grid(y_res)                           # (B, 2*L*W)
            feat_res = self._grid_2ch(feat_res_flat)                       # (B,2,L,W)

            # Ch 2-3: current h_2d (physical scale)
            feat_h = self._grid_2ch(h_2d_t)                               # (B,2,L,W)

            # Ch 4-5: posterior mean mu_x on grid
            feat_mu  = self.sym2grid(mu_x_flat, mode='complex')            # (B,2,L,W)

            # Ch 6: v_x (Re-component) on grid
            feat_vx  = self.sym2grid(v_x_t[:, :N], mode='real')           # (B,1,L,W)

            # Ch 7: |LLR| confidence on grid
            llr_conf = (llr_t[:, :N].abs() + llr_t[:, N:].abs()) * 0.5   # (B,N)
            feat_llr = self.sym2grid(llr_conf, mode='real')                # (B,1,L,W)

            # Ch 8-9: pilot-only cleaned observation y - Hxp
            feat_y_pilot = self._grid_2ch(self.rzf2grid(y_pilot_clean))    # (B,2,L,W)

            # Ch 10-11: explicit self-interference estimate Hmu
            feat_hmu = self._grid_2ch(self.rzf2grid(H_mu))                 # (B,2,L,W)

            # Ch 12-13: inter-iteration delta mu
            feat_dmu = self.sym2grid(delta_mu_flat, mode='complex')        # (B,2,L,W)

            feat_all = torch.cat(
                [feat_res, feat_h, feat_mu, feat_vx, feat_llr,
                 feat_y_pilot, feat_hmu, feat_dmu], dim=1)                 # (B,14,L,W)

            # ── 5. Channel Refiner: alpha-scaled residual correction ─────
            # alpha_t starts at 0 → safe identity at init; Kaiming-init
            # Refiner gets full-rank gradients from the start.
            delta_h  = self.refiners[t](feat_all)                         # (B,2,L,W)
            alpha_t  = self.refine_scales[t]                               # scalar
            gate_t   = self._compute_refine_gate(t, llr_conf, v_x_t)      # (B,1,1,1)
            h_2d_4d  = self._grid_2ch(h_2d_t)                              # (B,2,L,W)
            h_2d_new_4d = h_2d_4d + gate_t * alpha_t * delta_h             # (B,2,L,W)

            # Flatten back to (B, 2*L*W) and rebuild H_flat for next iter
            h_2d_t   = torch.cat([
                h_2d_new_4d[:, 0].reshape(-1, L * W),
                h_2d_new_4d[:, 1].reshape(-1, L * W)], dim=-1)            # (B,2LW)
            H_flat_t = self._h2d_to_H_flat(h_2d_t)

            history_h_sc.append(h_2d_t / std_y)                           # normalised
            history_H_post.append(H_flat_t)
            history_gate.append(gate_t.view(-1, 1))

            mu_prev_flat = mu_x_flat
            v_prev_flat  = v_x_t
            llr_a_flat   = llr_t.clamp(min=-10.0, max=10.0)

        return {
            'history_h_sc'   : history_h_sc,    # list[T] of (B, 2*L*W)
            'history_llr'    : history_llr,     # list[T] of (B, 2N)
            'history_det'    : history_det,     # list[T] of (B, 2N)
            'history_mu'     : history_mu,      # list[T] of (B, 2N)
            'history_vx'     : history_vx,      # list[T] of (B, 2N)
            'history_H_pre'  : history_H_pre,   # list[T] of (B, 2N²)
            'history_H_post' : history_H_post,  # list[T] of (B, 2N²)
            'history_gate'   : history_gate,    # list[T] of (B, 1)
            # convenience — last iteration outputs
            'final_detection': history_det[-1],
            'final_bits'     : history_llr[-1],
            'final_vx'       : history_vx[-1],
            'final_gate'     : history_gate[-1],
            'channel_est'    : history_h_sc[-1],
        }


# ════════════════════════════════════════════════════════════════════════════
#  AFDMModelsMixin
# ════════════════════════════════════════════════════════════════════════════

class AFDMModelsMixin:

    # ------------------------------------------------------------------ #
    #  Builder helpers                                                     #
    # ------------------------------------------------------------------ #

    def build_dnn_model_full(self, input_dim,
                              model_name='AFDM_DualStream_DirectOut',
                              device=None):
        """
        Construct the CEBackbone nn.Module matching the original Keras model.

        Returns: CEBackbone (nn.Module)
        """
        K_factor, k_max, L_max, W, pad_size = self._get_2d_grid_params()
        aux_dim = 4
        print(f"AFDM SP Dual-Stream CNN (FFN+SE Head + FiLM):")
        print(f"  Input dim = {input_dim},  Output 2D dim = {L_max*W*2}")
        print(f"  Grid shape: ({L_max}, {W}, 2)  K={K_factor}")
        print(f"  Asymmetric Dilated ResBlocks ×5: d_H=[1,2,4,8,16], d_W=1")
        model = CEBackbone(L_max, W, aux_dim=aux_dim)
        if device is not None:
            model = model.to(device)
        return model

    def build_e2e_model(self, input_dim, data_positions,
                         ce_backbone=None, device=None):
        """
        Assemble E2EModel.

        Returns: (E2EModel, ce_backbone)
        """
        N     = self.N_total
        m0    = self._m0
        K_factor, k_max, L_max, W, pad_size = self._get_2d_grid_params()
        std_y = float(self.global_std_y) if self.global_std_y is not None else 1.0
        if ce_backbone is None:
            ce_backbone = self.build_dnn_model_full(input_dim, device=device)
        model = E2EModel(
            ce_backbone   = ce_backbone,
            N             = N,
            K_factor      = K_factor, k_max=k_max,
            L_max         = L_max,    W=W, pad_size=pad_size,
            data_positions= data_positions,
            c1=self.c1, c2=self.c2, m0=m0,
            l_max_cap=self.l_max_cap, k_max_cap=self.k_max_cap,
            global_std_y  = std_y,
        )
        if device is not None:
            model = model.to(device)
        return model, ce_backbone

    def build_e2e_oamp_model(self, input_dim, data_positions,
                              ce_backbone=None, num_oamp_layers=4, device=None):
        """
        Assemble E2EOAMPModel: CE backbone + OAMPNetDetector.

        Args:
            input_dim       : int — feature vector size (= 2*L*W + 4)
            data_positions  : np.ndarray — data subcarrier indices
            ce_backbone     : pre-trained CEBackbone or None (build fresh)
            num_oamp_layers : number of OAMP unrolling layers (default 4)
            device          : torch.device or None

        Returns: (E2EOAMPModel, ce_backbone)
        """
        N     = self.N_total
        m0    = self._m0
        K_factor, k_max, L_max, W, pad_size = self._get_2d_grid_params()
        std_y = float(self.global_std_y) if self.global_std_y is not None else 1.0
        if ce_backbone is None:
            ce_backbone = self.build_dnn_model_full(input_dim, device=device)
        model = E2EOAMPModel(
            ce_backbone    = ce_backbone,
            N              = N,
            K_factor       = K_factor, k_max=k_max,
            L_max          = L_max,    W=W, pad_size=pad_size,
            data_positions = data_positions,
            c1=self.c1, c2=self.c2, m0=m0,
            l_max_cap      = self.l_max_cap, k_max_cap=self.k_max_cap,
            global_std_y   = std_y,
            num_oamp_layers= num_oamp_layers,
        )
        n_total     = sum(p.numel() for p in model.parameters())
        n_oamp      = sum(p.numel() for p in model.oamp.parameters())
        n_ce        = sum(p.numel() for p in model.backbone.parameters())
        print(f"  E2EOAMPModel: total={n_total:,}  "
              f"CE={n_ce:,}  OAMP={n_oamp:,} (T={num_oamp_layers})")
        if device is not None:
            model = model.to(device)
        return model, ce_backbone

    def build_e2e_ep_model(self, input_dim, data_positions,
                            ce_backbone=None, num_ep_layers=4, device=None):
        """
        Assemble E2EEPModel: CE backbone + EPNetDetector.

        Returns: (E2EEPModel, ce_backbone)
        """
        N     = self.N_total
        m0    = self._m0
        K_factor, k_max, L_max, W, pad_size = self._get_2d_grid_params()
        std_y = float(self.global_std_y) if self.global_std_y is not None else 1.0
        if ce_backbone is None:
            ce_backbone = self.build_dnn_model_full(input_dim, device=device)
        model = E2EEPModel(
            ce_backbone    = ce_backbone,
            N              = N,
            K_factor       = K_factor, k_max=k_max,
            L_max          = L_max,    W=W, pad_size=pad_size,
            data_positions = data_positions,
            c1=self.c1, c2=self.c2, m0=m0,
            l_max_cap      = self.l_max_cap, k_max_cap=self.k_max_cap,
            global_std_y   = std_y,
            num_ep_layers  = num_ep_layers,
        )
        n_total = sum(p.numel() for p in model.parameters())
        n_ep    = sum(p.numel() for p in model.ep.parameters())
        n_ce    = sum(p.numel() for p in model.backbone.parameters())
        print(f"  E2EEPModel: total={n_total:,}  "
              f"CE={n_ce:,}  EP={n_ep:,} (T={num_ep_layers})")
        if device is not None:
            model = model.to(device)
        return model, ce_backbone

    def build_e2e_unfolding_model(self, input_dim, data_positions,
                                   ce_backbone_1=None, ce_backbone_2=None,
                                   sic_mode='soft', device=None):
        """
        Assemble 2-stage deep-unfolding UnfoldingModel.

        Returns: (UnfoldingModel, ce_backbone_1, ce_backbone_2)
        """
        N     = self.N_total
        m0    = self._m0
        K_factor, k_max, L_max, W, pad_size = self._get_2d_grid_params()
        std_y = float(self.global_std_y) if self.global_std_y is not None else 1.0
        std_x = float(self.global_std_X) if self.global_std_X is not None else 1.0

        # Delta indices for DiffRZFToGridLayer
        offsets        = np.arange(-(k_max + pad_size), k_max + pad_size + 1)
        centers        = np.arange(L_max) * K_factor
        delta_idx_flat = ((centers[:, None] + offsets[None, :]) % N).ravel()

        ce_s1 = self.build_dnn_model_full(input_dim,
                                           model_name='AFDM_DualStream_s1',
                                           device=device)
        if ce_backbone_1 is not None:
            ce_s1.load_state_dict(ce_backbone_1.state_dict())

        ce_s2 = self.build_dnn_model_full(input_dim,
                                           model_name='AFDM_DualStream_s2',
                                           device=device)
        if ce_backbone_2 is not None:
            ce_s2.load_state_dict(ce_backbone_2.state_dict())

        model = UnfoldingModel(
            ce_backbone_1 = ce_s1,
            ce_backbone_2 = ce_s2,
            N             = N,
            K_factor      = K_factor, k_max=k_max,
            L_max         = L_max,    W=W, pad_size=pad_size,
            data_positions= data_positions,
            W_match_s2    = self._W_match_s2,
            delta_idx_flat= delta_idx_flat,
            c1=self.c1, c2=self.c2, m0=m0, rho=self.rho,
            l_max_cap=self.l_max_cap, k_max_cap=self.k_max_cap,
            global_std_y  = std_y,
            global_std_X  = std_x,
            sic_mode      = sic_mode,
        )
        if device is not None:
            model = model.to(device)
        return model, ce_s1, ce_s2

    def build_turbo_refiner_model(self, pretrained_e2e_model, device=None):
        """
        Assemble TurboRefinerModel: frozen Stage-1 E2EModel + trainable
        ChannelRefiner.

        Args:
            pretrained_e2e_model: a loaded E2EModel with checkpoint weights.
            device: torch.device or None (auto-detect via _pt_device).

        Returns: (TurboRefinerModel, refiner_subnet)
          - TurboRefinerModel: full model (Stage-1 frozen, refiner trainable)
          - refiner_subnet: the ChannelRefiner sub-module (for param count)
        """
        N     = self.N_total
        m0    = self._m0
        K_factor, k_max, L_max, W, pad_size = self._get_2d_grid_params()
        std_y = float(self.global_std_y) if self.global_std_y is not None else 1.0

        offsets        = np.arange(-(k_max + pad_size), k_max + pad_size + 1)
        centers        = np.arange(L_max) * K_factor
        delta_idx_flat = ((centers[:, None] + offsets[None, :]) % N).ravel()

        model = TurboRefinerModel(
            e2e_s1         = pretrained_e2e_model,
            N              = N,
            K_factor       = K_factor, k_max=k_max,
            L_max          = L_max,    W=W, pad_size=pad_size,
            data_positions = np.arange(N),
            W_match_s2     = self._W_match_s2,
            delta_idx_flat = delta_idx_flat,
            c1=self.c1, c2=self.c2, m0=m0,
            l_max_cap=self.l_max_cap, k_max_cap=self.k_max_cap,
            global_std_y   = std_y,
        )
        if device is not None:
            model = model.to(device)

        n_total    = sum(p.numel() for p in model.parameters())
        n_trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"  TurboRefinerModel: total={n_total:,}  trainable={n_trainable:,}")
        print(f"    (Stage-1 frozen: {n_total - n_trainable:,} params locked)")
        return model, model.refiner

    def build_turbo_receiver(self, input_dim, data_positions,
                              ce_state_dict=None,
                              detector_state_dict=None,
                              oamp_state_dict=None,
                              num_outer_iters=3,
                              num_oamp_layers=4,
                              detector_type='oamp',
                              device=None):
        """
        Assemble JointTurboReceiver: single CE backbone +
        T independent (detector + ChannelRefiner) outer-loop pairs.

        Weight seeding strategy:
          CE backbone  : loaded from ce_state_dict (dnn_ce_model.pt)
          detectors[t] : replicated from detector_state_dict or the legacy
                         oamp_state_dict['oamp.*'] for all t
          refiners[t]  : random Xavier init (no prior checkpoint)

        Args:
            input_dim       : int — feature vector size
            data_positions  : np.ndarray — data subcarrier indices
            ce_state_dict   : state_dict of a CEBackbone (optional)
            detector_state_dict : state_dict of an E2E detector model
                                  (E2EOAMPModel/E2EEPModel) or detector-only
                                  module state_dict.
            oamp_state_dict : legacy alias for detector_state_dict.
            num_outer_iters : number of outer Turbo iterations (default 3)
            num_oamp_layers : inner detector unrolling depth (default 4)
            detector_type   : 'oamp' or 'ep'
            device          : torch.device or None

        Returns: (JointTurboReceiver, ce_backbone)
        """
        N     = self.N_total
        m0    = self._m0
        K_factor, k_max, L_max, W, pad_size = self._get_2d_grid_params()
        std_y = float(self.global_std_y) if self.global_std_y is not None else 1.0

        offsets        = np.arange(-(k_max + pad_size), k_max + pad_size + 1)
        centers        = np.arange(L_max) * K_factor
        delta_idx_flat = ((centers[:, None] + offsets[None, :]) % N).ravel()

        ce_backbone = self.build_dnn_model_full(input_dim, device=device)
        if ce_state_dict is not None:
            ce_backbone.load_state_dict(ce_state_dict)
            print(f"  CE backbone loaded from provided state_dict")

        model = JointTurboReceiver(
            ce_backbone    = ce_backbone,
            N              = N,
            K_factor       = K_factor, k_max=k_max,
            L_max          = L_max,    W=W, pad_size=pad_size,
            data_positions = data_positions,
            W_match_s2     = self._W_match_s2,
            delta_idx_flat = delta_idx_flat,
            c1=self.c1, c2=self.c2, m0=m0,
            l_max_cap      = self.l_max_cap, k_max_cap=self.k_max_cap,
            global_std_y   = std_y,
            num_outer_iters= num_outer_iters,
            num_oamp_layers= num_oamp_layers,
            detector_type  = detector_type,
        )

        detector_type = detector_type.lower()
        detector_label = _detector_label(detector_type)
        seed_state = detector_state_dict if detector_state_dict is not None else oamp_state_dict
        if seed_state is not None:
            prefix = f"{detector_type}."
            detector_sub = {k[len(prefix):]: v
                            for k, v in seed_state.items()
                            if k.startswith(prefix)}
            if not detector_sub and detector_type == 'oamp':
                detector_sub = {k[len('oamp.'):]: v
                                for k, v in seed_state.items()
                                if k.startswith('oamp.')}
            if not detector_sub:
                detector_sub = dict(seed_state)
            for t in range(num_outer_iters):
                model.detectors[t].load_state_dict(detector_sub, strict=False)
            print(f"  detectors[0..{num_outer_iters-1}] seeded from {detector_label} checkpoint")

        if device is not None:
            model = model.to(device)

        n_total  = sum(p.numel() for p in model.parameters())
        n_ce     = sum(p.numel() for p in model.backbone.parameters())
        n_det    = sum(p.numel() for t in range(num_outer_iters)
                       for p in model.detectors[t].parameters())
        n_ref    = sum(p.numel() for t in range(num_outer_iters)
                       for p in model.refiners[t].parameters())
        print(f"  JointTurboReceiver: T={num_outer_iters}  total={n_total:,}")
        print(f"    CE={n_ce:,}  {detector_label}×{num_outer_iters}={n_det:,}  "
              f"Refiner×{num_outer_iters}={n_ref:,}")
        return model, ce_backbone

    # ------------------------------------------------------------------ #
    #  Verification & diagnostics                                          #
    # ------------------------------------------------------------------ #

    def verify_differentiable_layers(self):
        """
        Gate check: compare each differentiable PyTorch layer against its
        NumPy counterpart on a random channel realisation.
        Prints max absolute error per stage and verifies gradient flow.
        """
        print("\n" + "=" * 60)
        print("  verify_differentiable_layers()  [PyTorch]")
        print("=" * 60)
        N = self.N_total
        m0 = self._m0
        K_factor, k_max, L_max, W, pad_size = self._get_2d_grid_params()

        H_eff, H_time, _ = self.generate_channel_matrix(30.0, 'EVA')
        _, pilot_pos, pilot_syms, guard_pos, data_pos = self.generate_pilot_frame()
        n_data = N

        qpsk      = np.array([1+1j, 1-1j, -1+1j, -1-1j]) / np.sqrt(2)
        x_frame   = (np.sqrt(1.0 - self.rho) *
                     qpsk[np.random.randint(0, 4, N)])
        x_p       = np.zeros(N, dtype=complex)
        x_p[pilot_pos] = pilot_syms
        x_frame  += x_p

        s      = self.afdm_modulation(x_frame)
        r, sw2 = self.add_awgn(H_time @ s, 20.0)
        y_daft = self.afdm_demodulation(r)

        # ─ NumPy reference ─────────────────────────────────────────
        h_tap_clean  = self._generate_clean_h_tap(H_eff, m0)
        h_2d_clean   = self.map_1d_to_2d_grid(
            self._dechirp(h_tap_clean, m0=m0), pad_size=pad_size)
        h_2d_flat    = np.concatenate([np.real(h_2d_clean).ravel(),
                                       np.imag(h_2d_clean).ravel()]).astype(np.float32)[None]
        np_h1d       = self.map_2d_grid_to_1d(h_2d_clean, pad_size=pad_size)
        np_h1d_ri    = np.concatenate([np.real(np_h1d),
                                       np.imag(np_h1d)]).astype(np.float32)[None]
        np_H         = self._reconstruct_H_eff_from_taps_2d(
            self._rechirp(np_h1d, m0=m0), m0, threshold_db=-300)
        np_H_flat    = np.concatenate([np.real(np_H).ravel(),
                                       np.imag(np_H).ravel()]).astype(np.float32)[None]
        np_xhat      = self._lmmse_detect_np(np_H, y_daft, x_p, data_pos, sw2)
        np_xhat_ri   = np.concatenate([np.real(np_xhat),
                                       np.imag(np_xhat)]).astype(np.float32)[None]

        # ─ Build PyTorch layers ────────────────────────────────────
        lay_g2d = Grid2DTo1DLayer(N, K_factor, k_max, L_max, W, pad_size)
        lay_rch = DiffRechirpLayer(N, self.c2, m0)
        lay_rec = DiffReconstructLayer(N, self.c1, self.c2, m0,
                                       self.l_max_cap, self.k_max_cap)
        lay_lmm = DiffLMMSELayer(N, data_pos)
        for m in [lay_g2d, lay_rch, lay_rec, lay_lmm]:
            m.eval()

        th  = torch.from_numpy(h_2d_flat)
        _tol = (5e-4, 5e-4, 5e-4, 1e-2)

        with torch.no_grad():
            # Stage A
            h1d = lay_g2d(th)
            np_ref_a = np.concatenate([np.real(np_h1d), np.imag(np_h1d)]).astype(np.float32)[None]
            err_a = float((h1d - torch.from_numpy(np_ref_a)).abs().max())
            print(f"  Stage A Grid2DTo1D   max|err| = {err_a:.3e}"
                  f"  {'OK' if err_a < _tol[0] else 'FAIL'}")

            # Stage B
            h1dr = lay_rch(h1d)
            err_b = float((h1dr - torch.from_numpy(np_h1d_ri)).abs().max())
            print(f"  Stage B DiffRechirp  max|err| = {err_b:.3e}"
                  f"  {'OK' if err_b < _tol[1] else 'FAIL'}")

            # Stage C
            Hf = lay_rec(h1dr)
            err_c = float((Hf - torch.from_numpy(np_H_flat)).abs().max())
            print(f"  Stage C DiffReconst  max|err| = {err_c:.3e}"
                  f"  {'OK' if err_c < _tol[2] else 'FAIL'}")

            # Stage D (pin noise_floor ≈ 0)
            with torch.no_grad():
                lay_lmm.noise_floor.data.fill_(-100.0)
            y_t  = torch.from_numpy(
                np.concatenate([np.real(y_daft), np.imag(y_daft)]).astype(np.float32)[None])
            xp_t = torch.from_numpy(
                np.concatenate([np.real(x_p), np.imag(x_p)]).astype(np.float32)[None])
            s_t  = torch.tensor([[sw2]], dtype=torch.float32)
            xhat, v_x = lay_lmm([Hf, y_t, xp_t, s_t])
            err_d = float((xhat - torch.from_numpy(np_xhat_ri)).abs().max())
            print(f"  Stage D DiffLMMSE    max|err| = {err_d:.3e}"
                  f"  {'OK' if err_d < _tol[3] else 'FAIL'}"
                  f"  (noise_floor pinned for reference)")
            # v_x sanity: should be > 0 and finite
            vx_ok = bool((v_x > 0).all() and torch.isfinite(v_x).all())
            print(f"  Stage D v_x          {'all>0 & finite OK' if vx_ok else 'FAIL: non-positive or NaN'}"
                  f"  mean={v_x.mean().item():.3e}  max={v_x.max().item():.3e}")

        # ─ Gradient check ──────────────────────────────────────────
        with torch.no_grad():
            lay_lmm.noise_floor.data.fill_(-3.0)
        h2d_var = torch.from_numpy(h_2d_flat).requires_grad_(True)
        Hf2     = lay_rec(lay_rch(lay_g2d(h2d_var)))
        xhat2, _ = lay_lmm([Hf2, y_t, xp_t, s_t])
        loss    = xhat2.pow(2).mean()
        loss.backward()
        grad_ok = (h2d_var.grad is not None and
                   bool(torch.isfinite(h2d_var.grad).all()))
        print(f"  Gradient flow        {'finite OK' if grad_ok else 'FAIL: None or NaN'}")

        all_ok = (err_a < _tol[0] and err_b < _tol[1] and
                  err_c < _tol[2] and err_d < _tol[3] and vx_ok and grad_ok)
        print(f"{'  ALL CHECKS PASSED' if all_ok else '  SOME CHECKS FAILED'}")
        print("=" * 60)
        return all_ok

    # ------------------------------------------------------------------ #
    #  diagnose_sic_physics — pure NumPy (unchanged from TF version)      #
    # ------------------------------------------------------------------ #

    def diagnose_sic_physics(self, n_trials=30, snr_db=20.0, channel_type='EVA'):
        """Pure-NumPy SIC Physics Diagnostic (no PyTorch / Keras)."""
        print("\n" + "=" * 64)
        print("  SIC PHYSICS DIAGNOSTIC  (pure NumPy)")
        print(f"  {n_trials} trials  |  SNR = {snr_db} dB  |  channel = {channel_type}")
        print("=" * 64)

        N   = self.N_total;  m0 = self._m0;  rho = self.rho
        _, pilot_pos, pilot_syms, guard_pos, data_pos = self.generate_pilot_frame()
        qpsk = np.array([1+1j, 1-1j, -1+1j, -1-1j]) / np.sqrt(2)
        amp  = np.sqrt((1.0 - rho) / 2.0)
        beta = 3.1

        dnn_available = (self.dnn_model_full is not None and
                         self.global_std_X   is not None)
        if not dnn_available:
            print("  NOTE: dnn_model_full not loaded; Stage-1 uses pure RZF.")
        nm1l, nm1d, nm2l, gl, b1l, b2l = [], [], [], [], [], []

        for _ in range(n_trials):
            H_eff, H_time, _ = self.generate_channel_matrix(300.0, channel_type)
            x_d   = np.sqrt(1.0 - rho) * qpsk[np.random.randint(0, 4, N)]
            x_p   = np.zeros(N, dtype=complex);  x_p[pilot_pos] = pilot_syms
            s     = self.afdm_modulation(x_d + x_p)
            r, sw2 = self.add_awgn(H_time @ s, snr_db)
            y     = self.afdm_demodulation(r)

            h_s1  = self._correlate_with_pilot(y)
            Hs1   = self._reconstruct_H_eff_from_taps_2d(h_s1, m0)
            nm1l.append(self.calculate_nmse(H_eff, Hs1))

            H_sic = Hs1
            if dnn_available:
                try:
                    Hdnn = self.dnn_estimation(y, pilot_pos, pilot_syms, guard_pos)
                    nm1d.append(self.calculate_nmse(H_eff, Hdnn))
                    H_sic = Hdnn
                except Exception:
                    dnn_available = False

            x_h1  = self._lmmse_detect_np(H_sic, y, x_p, data_pos, sw2)
            xs_re = np.tanh(beta*(np.real(x_h1)/amp))*amp
            xs_im = np.tanh(beta*(np.imag(x_h1)/amp))*amp
            x_s   = xs_re + 1j*xs_im
            ti    = H_eff @ x_d;  ei = H_sic @ x_s
            gl.append(np.mean(np.abs(ti-ei)**2) / (np.mean(np.abs(ti)**2)+1e-12))
            y_c   = y - ei
            Hs2   = self._reconstruct_H_eff_from_taps_2d(self._W_match_s2 @ y_c, m0)
            nm2l.append(self.calculate_nmse(H_eff, Hs2))
            def _ber(a, b):
                return np.mean(
                    (np.sign(np.real(a)) != np.sign(np.real(b))).astype(float) +
                    (np.sign(np.imag(a)) != np.sign(np.imag(b))).astype(float)) / 2
            b1l.append(_ber(x_h1, x_d))
            b2l.append(_ber(self._lmmse_detect_np(Hs2, y, x_p, data_pos, sw2), x_d))

        _s = lambda l: (float(np.mean(l)), float(np.std(l)))
        nm1m,_  = _s(nm1l);  nm2m,_ = _s(nm2l)
        gm,_    = _s(gl)
        imp = (nm1m - nm2m)/(nm1m+1e-12)*100
        print(f"  Stage-1 linear NMSE  : {nm1m:.4f}")
        if nm1d: print(f"  Stage-1 DNN NMSE     : {float(np.mean(nm1d)):.4f}")
        print(f"  Stage-2 linear NMSE  : {nm2m:.4f}  ({imp:+.1f}%)")
        print(f"  Residual gamma mean  : {gm:.4f}")
        print(f"  BER S1/S2            : {float(np.mean(b1l)):.4f} / {float(np.mean(b2l)):.4f}")
        verdict = ("VERDICT A — SIC effective" if nm2m < nm1m*0.90 else
                   "VERDICT B — SIC net-harmful")
        print(f"  {verdict}")
        print("=" * 64)
        return {'gamma_mean': gm, 'nmse_s1_lin': nm1m, 'nmse_s2_lin': nm2m,
                'improvement_pct': imp, 'verdict': verdict}

    def diagnose_reconstruction(self, verbose=True):
        """Check Algorithm 5.2.2 aliasing constraint."""
        N = self.N_total;  K = 2*self.k_max_cap+1
        delta_max = self.k_max_cap + K*self.l_max_cap
        feasible  = delta_max < N;  Q = (self.l_max_cap+1)*K - 1
        overhead  = 1 + 2*Q
        if verbose:
            print(f"=== Reconstruction Feasibility ===")
            print(f"  delta_max={delta_max} < N={N}: "
                  f"{'OK' if feasible else 'ALIASING FAIL'}")
            print(f"  overhead={overhead}/{N}={overhead/N*100:.1f}%  "
                  f"data={max(0,N-overhead)}/{N}={max(0,N-overhead)/N*100:.1f}%")
        return feasible
