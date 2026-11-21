"""
afdm_trainer.py — Data generation, training and evaluation mixin.

Contains:
  - generate_training_dataset, generate_e2e_training_dataset
  - train_e2e, evaluate_e2e
  - train_e2e_unfolding, evaluate_e2e_unfolding
  - dnn_estimation, run_comparison_test
  - visualize_pilot_placement, visualize_channel_estimation_results
  - comprehensive_comparison, plot_results

Depends on: afdm_env + afdm_models (via self.*).
"""
import copy
import pickle
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import TensorDataset, DataLoader
from pathlib import Path
def train_test_split(*arrays, test_size=0.2, random_state=None):
    """Minimal numpy drop-in for sklearn.model_selection.train_test_split.
    Replaces the sklearn dependency to avoid scipy.spatial slow-import on Windows."""
    rng = np.random.RandomState(random_state)
    n   = len(arrays[0])
    idx = rng.permutation(n)
    n_val = max(1, int(np.ceil(n * test_size)))
    val_idx, tr_idx = idx[:n_val], idx[n_val:]
    result = []
    for a in arrays:
        a = np.asarray(a)
        result.append(a[tr_idx])
        result.append(a[val_idx])
    return result
import sys
import time
import warnings
warnings.filterwarnings('ignore')


def _fmt_time(s):
    """Format seconds -> '2m05s' or '1h03m'."""
    s = max(0, int(s))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}h{m:02d}m" if h else f"{m}m{sec:02d}s"


def _ep_bar(label, ep, epochs, t_ep, t0_fit, loss, val, lr):
    """Overwrite-in-place epoch progress bar (no tqdm dependency)."""
    pct  = (ep + 1) / epochs
    done = int(pct * 24)
    bar  = '\u2588' * done + '\u2591' * (24 - done)
    elapsed = time.time() - t0_fit
    eta     = elapsed / (ep + 1) * (epochs - ep - 1)
    ep_s    = time.time() - t_ep
    eta_str = 'done   ' if (ep + 1) >= epochs else _fmt_time(eta)
    msg = (f"\r  {label} [{ep+1:3d}/{epochs}] {bar} {pct*100:4.0f}%"
           f"  loss={loss:.3e}  val={val:.3e}"
           f"  lr={lr:.1e}  {ep_s:.0f}s/ep  ETA {eta_str}")
    sys.stdout.write(msg)
    sys.stdout.flush()


def compute_turbo_loss(out, bits_true, x_data_true, y_ce_labels,
                       inp_y, inp_xp,
                       lambda_bce=1.0, lambda_sym=0.2,
                       lambda_ce=0.1,  lambda_obs=0.02,
                       lambda_kd=0.0,  llr_teacher=None):
    """
    Layer-wise multi-task loss for JointTurboReceiver.

    Supervises EVERY outer iteration's output so earlier iterations learn
    meaningful physics-based representations (not just the final layer).
    Iterations closer to the end are weighted more heavily (weight_t = (t+1)/T).

    Loss terms per iteration t:
      1. BCE on LLR (BER driver)
      2. Symbol MSE (physical anchor)
      3. CE MSE on normalised refined h_2d grid (CE accuracy)
      4. Measurement consistency on the refined channel:
         ||y - H_hat_post @ (x_p + mu_x)||^2
      5. KD: KL(student_LLR || teacher_LLR) [disabled by default lambda_kd=0]

    Args:
      out            : dict from JointTurboReceiver.forward()
      bits_true      : (B, 2N) float32 {0,1} ground-truth Gray bits
      x_data_true    : (B, 2N) float32 ground-truth scaled data symbols
      y_ce_labels    : (B, 2*L*W) float32 normalised CE ground truth
      inp_y          : (B, 2N) received signal (for measurement consistency)
      inp_xp         : (B, 2N) pilot frame
      lambda_*       : loss weights
      llr_teacher    : (B, 2N) optional teacher LLR for KD (default None)

    Returns: scalar total_loss
    """
    T = len(out['history_llr'])
    total_loss = bits_true.new_zeros(1).squeeze()

    ce_energy = y_ce_labels.pow(2)
    ce_weight = (0.25 + ce_energy / (ce_energy.mean(dim=-1, keepdim=True).detach() + 1e-6)).detach()

    for t in range(T):
        w_t = (float(t + 1) / T) ** 2   # task-oriented: final iterations matter more

        llr_t    = out['history_llr'][t]      # (B, 2N)
        det_t    = out['history_det'][t]      # (B, 2N)
        mu_t     = out.get('history_mu', out['history_det'])[t]       # (B, 2N)
        h_sc_t   = out['history_h_sc'][t]     # (B, 2*L*W)
        H_flat_t = out.get('history_H_post', out.get('history_H_pre'))[t]  # (B, 2*N^2)

        # 1. BCE loss (BER driver)
        loss_bce = F.binary_cross_entropy_with_logits(llr_t, bits_true)

        # 2. Symbol MSE (physical anchor)
        loss_sym = F.mse_loss(mu_t, x_data_true)

        # 3. Detection-oriented CE anchor:
        #    focus on stronger taps and decay the CE pressure after t=0 so
        #    later outer loops are not dominated by average-pixel CE MSE.
        ce_ref   = (ce_energy * ce_weight).mean().detach() + 1e-6
        loss_ce  = ((h_sc_t - y_ce_labels).pow(2) * ce_weight).mean() / ce_ref
        ce_iter_w = 1.0 if t == 0 else 0.25

        # 4. Measurement consistency on the refined H and soft posterior mean
        # Normalised by ||y||^2 so that scale depends only on relative residual,
        # not on the absolute power of the received signal / channel matrix.
        N     = inp_y.shape[1] // 2
        x_est = inp_xp + mu_t            # (B, 2N): pilot + soft posterior mean
        Hr    = H_flat_t[:, :N * N].view(-1, N, N)
        Hi    = H_flat_t[:, N * N:].view(-1, N, N)
        xr    = x_est[:, :N].unsqueeze(-1)
        xi    = x_est[:, N:].unsqueeze(-1)
        yr    = (torch.bmm(Hr, xr) - torch.bmm(Hi, xi)).squeeze(-1)
        yi    = (torch.bmm(Hr, xi) + torch.bmm(Hi, xr)).squeeze(-1)
        y_hat = torch.cat([yr, yi], dim=-1)     # (B, 2N)
        y_ref    = inp_y.pow(2).mean().detach() + 1e-6
        loss_obs = F.mse_loss(y_hat, inp_y) / y_ref
        obs_iter_w = 0.5 + 0.5 * float(t + 1) / T

        # 5. Knowledge Distillation (default disabled, lambda_kd=0)
        loss_kd = bits_true.new_zeros(1).squeeze()
        if llr_teacher is not None and lambda_kd > 0:
            log_p_s = F.logsigmoid(llr_t)           # (B, 2N)
            p_t     = torch.sigmoid(llr_teacher)     # (B, 2N)
            loss_kd = F.kl_div(log_p_s, p_t, reduction='batchmean')

        layer_loss = (lambda_bce * loss_bce +
                      lambda_sym * loss_sym +
                      lambda_ce  * ce_iter_w * loss_ce  +
                      lambda_obs * obs_iter_w * loss_obs +
                      lambda_kd  * loss_kd)
        total_loss = total_loss + w_t * layer_loss

    return total_loss


class AFDMTrainerMixin:
    def _e2e_cache_signature(self):
        K_factor, k_max, L_max, W, pad_size = self._get_2d_grid_params()
        return {
            'N_total': int(self.N_total),
            'rho': float(self.rho),
            'l_max_cap': int(self.l_max_cap),
            'k_max_cap': int(self.k_max_cap),
            'K_factor': int(K_factor),
            'L_max': int(L_max),
            'W': int(W),
            'pad_size': int(pad_size),
            'P_paths': int(self.P_paths),
            'use_frac_doppler': bool(self.use_frac_doppler),
            'global_std_X': None if self.global_std_X is None else float(self.global_std_X),
            'global_std_y': None if self.global_std_y is None else float(self.global_std_y),
        }

    def save_e2e_dataset_cache(self, dataset, cache_path):
        cache_path = Path(cache_path)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            'signature': self._e2e_cache_signature(),
            'dataset': dataset,
        }
        with cache_path.open('wb') as f:
            pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"  E2E dataset cache saved → {cache_path}")

    def load_e2e_dataset_cache(self, cache_path):
        cache_path = Path(cache_path)
        with cache_path.open('rb') as f:
            payload = pickle.load(f)

        dataset = payload['dataset'] if isinstance(payload, dict) and 'dataset' in payload else payload
        cached_sig = payload.get('signature') if isinstance(payload, dict) else None
        cur_sig = self._e2e_cache_signature()
        if cached_sig is not None and cached_sig != cur_sig:
            raise ValueError(
                f"E2E dataset cache signature mismatch for {cache_path}.\n"
                f"cached={cached_sig}\ncurrent={cur_sig}")

        print(f"  E2E dataset cache loaded ← {cache_path}")
        return dataset

    def generate_e2e_training_dataset(self, n_samples=10000,
                                      snr_range=(10, 25),
                                      speed_range=None,
                                      guard_factor=None):
        """
        SP version: every sub-carrier carries a QPSK data symbol.
        Produces:
          - y_received   : received DAFT signal   [Re, Im]  (2*N,)
          - x_pilot_frame: pilot-ONLY frame        [Re, Im]  (2*N,)  ← used for pilot cancellation
          - x_data_true  : true data symbols       [Re, Im]  (2*N,)  ← all N symbols
          - sigma_w2     : noise variance          scalar
          - bits_true    : Gray bits               (2*N,)    ← 2 bits/symbol × N symbols

        SP frame assembly:
            x_full = sqrt(1-rho)*QPSK_data  +  x_pilot_only
            x_pilot_only[m0] = sqrt(rho*N)*p,  zeros elsewhere
        """
        if speed_range is None:
            speed_range = (5, self.max_speed_kmh)

        N = self.N_total
        K_factor, k_max, L_max, W, pad_size = self._get_2d_grid_params()
        QPSK = np.array([1+1j, 1-1j, -1+1j, -1-1j], dtype=complex) / np.sqrt(2)

        # SP layout is fixed for all samples
        _, pilot_pos, pilot_syms, guard_pos, data_pos = self.generate_pilot_frame()
        n_data = N   # SP: all N sub-carriers carry data
        m0 = self._m0

        print(f"Generating SP E2E training dataset: {n_samples} samples")
        print(f"  rho={self.rho:.2f}, n_data={n_data} (all sub-carriers), "
              f"SNR range={snr_range}, pad_size={pad_size}")

        X_feats, y_ce_labels   = [], []
        y_recv, x_pilots       = [], []
        x_data_true, sigma_list = [], []
        bits_true_list          = []

        for i in range(n_samples):
            if (i + 1) % 2000 == 0:
                print(f"  {i+1}/{n_samples}...")

            snr_db       = np.random.uniform(snr_range[0], snr_range[1])
            max_speed    = np.random.uniform(speed_range[0], speed_range[1])
            channel_type = np.random.choice(['EPA', 'EVA'])

            H_eff, H_time, _ = self.generate_channel_matrix(max_speed, channel_type)

            # ── SP frame assembly ──────────────────────────────────
            data_sym   = QPSK[np.random.randint(0, 4, N)]       # N QPSK symbols
            x_data_sc  = np.sqrt(1.0 - self.rho) * data_sym     # scaled data
            x_p_only   = np.zeros(N, dtype=complex)             # pilot-only frame
            x_p_only[pilot_pos] = pilot_syms                    # sqrt(rho*N)*p at m0
            x_full     = x_data_sc + x_p_only                   # full SP frame

            # Gray bit labels
            bits_b0 = (np.real(data_sym) < 0).astype(np.float32)  # (N,)
            bits_b1 = (np.imag(data_sym) < 0).astype(np.float32)  # (N,)

            # ── Transmit ───────────────────────────────────────────
            s      = self.afdm_modulation(x_full)
            r, sw2 = self.add_awgn(H_time @ s, snr_db)
            y_daft = self.afdm_demodulation(r)

            # ── DNN features (SP version) ──────────────────────────
            feats = self.extract_dnn_features(
                y_daft, pilot_pos, pilot_syms, guard_pos)

            # ── CE label (clean 2D grid, unchanged from EP) ────────
            h_tap_clean = self._generate_clean_h_tap(H_eff, m0)
            h_2d_clean  = self.map_1d_to_2d_grid(
                self._dechirp(h_tap_clean, m0=m0), pad_size=pad_size)
            ce_lbl = np.concatenate([np.real(h_2d_clean).flatten(),
                                     np.imag(h_2d_clean).flatten()])

            X_feats.append(feats.astype(np.float32))
            y_ce_labels.append(ce_lbl.astype(np.float32))
            y_recv.append(np.concatenate([np.real(y_daft),
                                          np.imag(y_daft)]).astype(np.float32))
            # Pilot-only frame: gives LMMSE the exact pilot component to cancel
            x_pilots.append(np.concatenate([np.real(x_p_only),
                                            np.imag(x_p_only)]).astype(np.float32))
            # True data symbols (scaled, what the receiver should recover)
            x_data_true.append(np.concatenate([np.real(x_data_sc),
                                               np.imag(x_data_sc)]).astype(np.float32))
            bits_true_list.append(np.concatenate([bits_b0, bits_b1]))  # (2*N,)
            sigma_list.append(np.float32(sw2))

        X_raw = np.array(X_feats)
        y_raw = np.array(y_ce_labels)

        if self.global_std_X is None:
            self.global_std_X = max(float(np.std(X_raw)), 1e-8)
            self.global_std_y = max(float(np.std(y_raw)), 1e-8)

        return {
            'X_features'   : X_raw  / self.global_std_X,
            'y_ce_labels'  : y_raw  / self.global_std_y,
            'y_received'   : np.array(y_recv),
            'x_pilot_frames': np.array(x_pilots),
            'x_data_true'  : np.array(x_data_true),
            'bits_true'    : np.array(bits_true_list, dtype=np.float32),  # (n, 2*N)
            'sigma_w2'     : np.array(sigma_list).reshape(-1, 1),
            'data_positions': data_pos,
            'pilot_positions': pilot_pos,
        }

    def train_e2e(self, n_samples=20000, snr_range=(10, 25),
                  epochs_pretrain=50, epochs_e2e=30,
                  batch_size=128, guard_factor=None,
                  det_loss_weight=1.0, ce_loss_weight=0.1,
                  sym_loss_weight_A=0.5, sym_loss_weight_B=0.05,
                  phase_a_ratio=0.3):
        """
        Two-phase end-to-end training with curriculum BCE loss — SP mode.

        SP-specific note on Phase 1 (CE pre-training):
          CNN must learn to extract the channel from y / x_p when data symbols
          are superimposed.  This is significantly harder than EP (where guards
          provided clean observations).  We therefore default epochs_pretrain=50
          (up from 30 in EP) and recommend at least 20k training samples.

        Phase 2  Fine-tune full CE→LMMSE→Demapper graph with curriculum:
          Phase 2-A (stabilisation, ~30% of epochs):
            L = det_loss_weight * BCE(bits, b_true)
              + sym_loss_weight_A * MSE(x̂, sqrt(1-rho)*QPSK)   ← physical anchor
              + ce_loss_weight * MSE(ĥ, h)
            Pilot cancellation inside DiffLMMSELayer:
              y_d = y - Ĥ @ x_pilot_only

          Phase 2-B (BER sprint, ~70% of epochs):
            L = det_loss_weight * BCE + sym_loss_weight_B * MSE + ce_loss_weight * MSE
            Lower LR + loosened MSE anchor.

        Returns (e2e_model, history_pretrain, (hist_A, hist_B), e2e_data)
        """
        N = self.N_total

        # ── Phase 1: CE pre-training ──────────────────────────────
        print("\n" + "=" * 60)
        print("  Phase 1: SP-CE pre-training  (CNN learns to filter data interference)")
        print("=" * 60)
        ce_dataset = self.generate_training_dataset(
            n_samples=n_samples, snr_range=snr_range)
        input_dim = ce_dataset['X_data'].shape[1]

        self.dnn_model_full = self.build_dnn_model_full(input_dim)
        X_tr, X_va, y_tr, y_va = train_test_split(
            ce_dataset['X_data'], ce_dataset['y_data_full'],
            test_size=0.2, random_state=42)
        hist_pre = self._pt_fit_ce(
            self.dnn_model_full, X_tr, y_tr, X_va, y_va,
            epochs=epochs_pretrain, batch_size=batch_size,
            patience=12, lr=1e-3, min_lr=1e-6)

        # GPU cleanup: move CE model off GPU before building larger E2E model
        # (avoids 2x VRAM spike on 6 GB GPUs, allocations from best_sd are freed)
        self.dnn_model_full.cpu()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        # ── Phase 2: E2E curriculum fine-tuning ───────────────────
        print("\n" + "=" * 60)
        print("  Phase 2: SP E2E curriculum fine-tuning (pilot cancel + LMMSE + BCE)")
        print("=" * 60)
        e2e_data   = self.generate_e2e_training_dataset(
            n_samples=n_samples, snr_range=snr_range)
        data_pos   = e2e_data['data_positions']

        e2e_model, ce_sub = self.build_e2e_model(
            input_dim, data_pos, ce_backbone=self.dnn_model_full)
        # (no summary equivalent in PyTorch; skip)

        n = len(e2e_data['X_features'])
        perm  = np.random.permutation(n)
        split = int(0.8 * n)
        tr, va = perm[:split], perm[split:]

        def _inputs(idx):
            return [e2e_data['X_features'][idx],
                    e2e_data['y_received'][idx],
                    e2e_data['x_pilot_frames'][idx],
                    e2e_data['sigma_w2'][idx]]

        def _labels(idx):
            return {'detection':   e2e_data['x_data_true'][idx],
                    'bits':        e2e_data['bits_true'][idx],
                    'channel_est': e2e_data['y_ce_labels'][idx]}

        epochs_A = max(1, int(epochs_e2e * phase_a_ratio))
        print(f"\n  Phase 2-A: stabilisation ({epochs_A} epochs)")
        hist_A = self._pt_fit_e2e(
            e2e_model, e2e_data, tr, va, epochs_A, batch_size,
            lr=1e-4, patience=6, min_lr=5e-6,
            det_w=det_loss_weight, sym_w=sym_loss_weight_A,
            ce_w=ce_loss_weight)

        epochs_B = epochs_e2e - epochs_A
        print(f"\n  Phase 2-B: BER sprint ({epochs_B} epochs)")
        hist_B = self._pt_fit_e2e(
            e2e_model, e2e_data, tr, va, epochs_B, batch_size,
            lr=1e-5, patience=10, min_lr=1e-6,
            det_w=det_loss_weight, sym_w=sym_loss_weight_B,
            ce_w=ce_loss_weight)

        # Do NOT sync E2E backbone weights back to self.dnn_model_full.
        # E2E/BCE fine-tuning task-orients the backbone for LLR output,
        # warping it away from pure CE.  Overwriting would destroy the
        # standalone DNN-CE+LMMSE baseline used in evaluate_e2e().
        # self.dnn_model_full.set_weights(ce_sub.get_weights())  # <- intentionally disabled
        self.e2e_model        = e2e_model
        self._e2e_ce_backbone = ce_sub   # kept for inspection / fine-tune continuation
        self._e2e_data_pos    = data_pos
        self._e2e_n_data      = len(data_pos)
        return e2e_model, hist_pre, (hist_A, hist_B), e2e_data

    def evaluate_e2e(self, n_test=1000, guard_factor=None):
        """
        Evaluate E2E model: SER and NMSE vs SNR (SP mode).

        Compares:  LS+LMMSE, MMSE+LMMSE, DNN-CE+LMMSE(NumPy), E2E-DNN+LMMSE(TF)

        SP note:
          LS- and MMSE-based baselines use only the observation at m0
          (guard_pos is empty), so their CE quality degrades significantly
          compared to EP.  This is the expected SP trade-off (compensated
          by full spectral efficiency).  SER/BER are computed via sign-based
          quadrant decisions (valid for amplitude-scaled QPSK).
        """
        if not hasattr(self, 'e2e_model'):
            raise ValueError("e2e_model not trained — call train_e2e() first.")

        snr_list = [5, 10, 15, 20, 25, 30]
        QPSK = np.array([1+1j, 1-1j, -1+1j, -1-1j], dtype=complex) / np.sqrt(2)
        N    = self.N_total
        rho  = self.rho

        _, pilot_pos, pilot_syms, guard_pos, data_pos = self.generate_pilot_frame()
        n_data = N   # SP: all N sub-carriers carry data
        m0     = self._m0

        results = {snr: {'ser_ls': [], 'ser_ls2d': [], 'ser_mmse': [],
                         'ser_cednn': [], 'ser_e2e': [],
                         'ber_ls': [], 'ber_ls2d': [], 'ber_mmse': [],
                         'ber_cednn': [], 'ber_e2e': [],
                         'nmse_ls': [], 'nmse_ls2d': [],
                         'nmse_mmse': [], 'nmse_dnn': []}
                   for snr in snr_list}

        spp = max(1, n_test // len(snr_list))

        for snr_db in snr_list:
            print(f"  Evaluating SNR={snr_db} dB ({spp} samples)...")
            for _ in range(spp):
                H_eff, H_time, _ = self.generate_channel_matrix(
                    np.random.uniform(5, self.max_speed_kmh),
                    np.random.choice(['EPA', 'EVA']))

                # SP frame: x_full = sqrt(1-rho)*QPSK_data + pilot_only
                data_sym   = QPSK[np.random.randint(0, 4, N)]
                x_data_sc  = np.sqrt(1.0 - rho) * data_sym
                x_p_only   = np.zeros(N, dtype=complex)
                x_p_only[pilot_pos] = pilot_syms
                x_full     = x_data_sc + x_p_only

                r, sw2 = self.add_awgn(H_time @ self.afdm_modulation(x_full), snr_db)
                y_daft = self.afdm_demodulation(r)

                # Channel estimates
                H_ls   = self.improved_ls_estimation(y_daft, pilot_pos, pilot_syms,
                                                      guard_pos)
                H_ls2d = self.improved_ls_estimation_2d(y_daft, pilot_pos, pilot_syms,
                                                        guard_pos)
                H_mmse = self.traditional_mmse_estimation(y_daft, pilot_pos,
                                                          pilot_syms, guard_pos, sw2)
                H_dnn  = self.dnn_estimation(y_daft, pilot_pos, pilot_syms,
                                              guard_pos)

                # NumPy LMMSE detection (all N data symbols in SP)
                xh_ls   = self._lmmse_detect_np(H_ls,   y_daft, x_p_only, data_pos, sw2)
                xh_ls2d = self._lmmse_detect_np(H_ls2d, y_daft, x_p_only, data_pos, sw2)
                xh_mmse = self._lmmse_detect_np(H_mmse, y_daft, x_p_only, data_pos, sw2)
                xh_ce   = self._lmmse_detect_np(H_dnn,  y_daft, x_p_only, data_pos, sw2)

                # PyTorch E2E forward pass
                feats   = self.extract_dnn_features(y_daft, pilot_pos, pilot_syms, guard_pos)
                pred    = self._pt_infer_e2e(self.e2e_model, feats, y_daft, x_p_only, sw2)
                xh_e2e  = pred['detection'][:N] + 1j * pred['detection'][N:]
                bits_e2e = (pred['bits'] > 0.0).astype(np.float32)

                # ── SP helpers: sign-based SER / BER ──────────────
                # All estimates target x_data_sc = sqrt(1-rho)*QPSK.
                # Sign-based decisions (= quadrant) are amplitude-invariant,
                # so they work correctly for any non-zero scale factor.
                def _bits_from_signs(sym_arr):
                    """Gray bits from sign of Re/Im (amplitude-invariant)."""
                    b0 = (np.real(sym_arr) < 0).astype(np.float32)  # bit 0
                    b1 = (np.imag(sym_arr) < 0).astype(np.float32)  # bit 1
                    return np.concatenate([b0, b1])  # (2*N,)

                def _ber(true_sym, est_bits):
                    """BER: compare est_bits with true Gray bits."""
                    true_bits = _bits_from_signs(true_sym)
                    return float(np.mean(np.abs(true_bits - est_bits)))

                def _ser_from_signs(true_sym, soft_sym):
                    """SER via quadrant (sign-of-Re, sign-of-Im)."""
                    det_re = np.where(np.real(soft_sym) >= 0, 1.0, -1.0) / np.sqrt(2)
                    det_im = np.where(np.imag(soft_sym) >= 0, 1.0, -1.0) / np.sqrt(2)
                    det = det_re + 1j * det_im
                    t_re  = np.where(np.real(true_sym) >= 0, 1.0, -1.0) / np.sqrt(2)
                    t_im  = np.where(np.imag(true_sym) >= 0, 1.0, -1.0) / np.sqrt(2)
                    true_hard = t_re + 1j * t_im
                    return float(np.mean(np.abs(true_hard - det) > 1e-6))

                r = results[snr_db]
                # Use x_data_sc (scaled data) as ground truth for SER/BER
                r['ser_ls'].append(_ser_from_signs(x_data_sc, xh_ls))
                r['ser_ls2d'].append(_ser_from_signs(x_data_sc, xh_ls2d))
                r['ser_mmse'].append(_ser_from_signs(x_data_sc, xh_mmse))
                r['ser_cednn'].append(_ser_from_signs(x_data_sc, xh_ce))
                r['ser_e2e'].append(_ser_from_signs(x_data_sc, xh_e2e))
                r['ber_ls'].append(_ber(x_data_sc, _bits_from_signs(xh_ls)))
                r['ber_ls2d'].append(_ber(x_data_sc, _bits_from_signs(xh_ls2d)))
                r['ber_mmse'].append(_ber(x_data_sc, _bits_from_signs(xh_mmse)))
                r['ber_cednn'].append(_ber(x_data_sc, _bits_from_signs(xh_ce)))
                r['ber_e2e'].append(_ber(x_data_sc, bits_e2e))
                r['nmse_ls'].append(self.calculate_nmse(H_eff, H_ls))
                r['nmse_ls2d'].append(self.calculate_nmse(H_eff, H_ls2d))
                r['nmse_mmse'].append(self.calculate_nmse(H_eff, H_mmse))
                r['nmse_dnn'].append(self.calculate_nmse(H_eff, H_dnn))

        # Print summary — SER table
        hdr = (f"{'SNR':>4} | {'SER_LS':>9} | {'SER_LS2D':>9} | "
               f"{'SER_MMSE':>9} | {'SER_CEDNN':>9} | {'SER_E2E':>9}")
        print("\n" + hdr)
        print("-" * len(hdr))
        for snr in snr_list:
            r = results[snr]
            print(f"{snr:4d} | {np.mean(r['ser_ls']):9.4e} | "
                  f"{np.mean(r['ser_ls2d']):9.4e} | "
                  f"{np.mean(r['ser_mmse']):9.4e} | "
                  f"{np.mean(r['ser_cednn']):9.4e} | "
                  f"{np.mean(r['ser_e2e']):9.4e}")

        # BER table
        hdr2 = (f"{'SNR':>4} | {'BER_LS':>9} | {'BER_LS2D':>9} | "
                f"{'BER_MMSE':>9} | {'BER_CEDNN':>9} | {'BER_E2E':>9}")
        print("\n" + hdr2)
        print("-" * len(hdr2))
        for snr in snr_list:
            r = results[snr]
            print(f"{snr:4d} | {np.mean(r['ber_ls']):9.4e} | "
                  f"{np.mean(r['ber_ls2d']):9.4e} | "
                  f"{np.mean(r['ber_mmse']):9.4e} | "
                  f"{np.mean(r['ber_cednn']):9.4e} | "
                  f"{np.mean(r['ber_e2e']):9.4e}")

        # NMSE table (diagnostic: LS vs LS-2D vs DNN)
        hdr3 = (f"{'SNR':>4} | {'NMSE_LS':>10} | {'NMSE_LS2D':>10} | "
                f"{'NMSE_MMSE':>10} | {'NMSE_DNN':>10}")
        print("\n" + hdr3)
        print("-" * len(hdr3))
        for snr in snr_list:
            r = results[snr]
            print(f"{snr:4d} | {np.mean(r['nmse_ls']):10.4e} | "
                  f"{np.mean(r['nmse_ls2d']):10.4e} | "
                  f"{np.mean(r['nmse_mmse']):10.4e} | "
                  f"{np.mean(r['nmse_dnn']):10.4e}")
        return results

    # ================================================================
    # Deep Unfolding: 2-Stage CE + SIC
    # ================================================================

    def train_e2e_unfolding(self,
                             n_samples=20000,
                             snr_range=(10, 25),
                             epochs_pretrain=50,
                             epochs_e2e=30,
                             batch_size=64,
                             sic_mode='qpsk_proj',
                             det_loss_weight=1.0,
                             ce_loss_weight=0.1,
                             sym_loss_weight_A=0.5,
                             sym_loss_weight_B=0.05,
                             s1_bce_weight_A=0.3,
                             s1_bce_weight_B=0.1,
                             s1_sym_weight_A=0.2,
                             s1_sym_weight_B=0.02,
                             phase_a_ratio=0.3,
                             pretrained_backbone=None):
        """
        Train the 2-Stage Deep Unfolding model end-to-end.

        Phase 1 -- CE pre-training (same as train_e2e Phase 1).
          If pretrained_backbone is provided (a Keras model), Phase 1 is
          SKIPPED and its weights are reused directly.  Caller must set
          self.global_std_X / global_std_y before calling.

        Phase 1 -- original doc (kept for reference):
          Pre-trained weights are clone-initialised into BOTH Stage-1 and
          Stage-2 backbones.  Fine-tuning specialises Stage-1 for
          "dirty-signal CE" and Stage-2 for "SIC-cleaned CE".

        Phase 2 — E2E curriculum on 6 supervised outputs:
          Primary (Stage 2): bits, detection, channel_est
          Auxiliary (Stage 1): bits_stage1, detection_stage1, channel_est_stage1

          Phase 2-A (stabilisation, ~30% epochs): high sym anchor weights.
          Phase 2-B (BER sprint, ~70% epochs):  Stage-1 aux weight annealed;
            network transitions to altruistic Stage-1 Deep Unfolding optimum.

        Returns (unfolding_model, hist_pretrain, (hist_A, hist_B), e2e_data)
        """
        N = self.N_total

        # ── Phase 1: CE pre-training (or reuse pretrained_backbone) ──────────
        if pretrained_backbone is not None:
            print("\n" + "=" * 60)
            print("  Deep Unfolding Phase 1: SKIPPED -- using pretrained_backbone")
            print("=" * 60)
            if self.global_std_X is None or self.global_std_y is None:
                raise RuntimeError(
                    "pretrained_backbone provided but global_std_X/y not set. "
                    "Load scalers before calling train_e2e_unfolding().")
            self.dnn_model_full = pretrained_backbone
            # Compute input_dim from system grid params (PyTorch has no .input_shape)
            _K, _k, _L, _W, _pad = self._get_2d_grid_params()
            input_dim = _L * _W * 2 + 4
            n_params  = sum(p.numel() for p in pretrained_backbone.parameters())
            print(f"  Backbone params : {n_params:,}")
            print(f"  input_dim       : {input_dim}")
            print(f"  global_std_X    : {self.global_std_X:.6f}")
            print(f"  global_std_y    : {self.global_std_y:.6f}")
            _empty = []
            hist_pre = type('_FakeHist', (), {
                'history': {'loss': _empty, 'val_loss': _empty}})()
        else:
            print("\n" + "=" * 60)
            print("  Deep Unfolding Phase 1: SP-CE pre-training")
            print("=" * 60)
            ce_dataset = self.generate_training_dataset(
                n_samples=n_samples, snr_range=snr_range)
            input_dim = ce_dataset['X_data'].shape[1]

            self.dnn_model_full = self.build_dnn_model_full(input_dim)
            X_tr, X_va, y_tr, y_va = train_test_split(
                ce_dataset['X_data'], ce_dataset['y_data_full'],
                test_size=0.2, random_state=42)
            X_tr, X_va, y_tr, y_va = train_test_split(
                ce_dataset['X_data'], ce_dataset['y_data_full'],
                test_size=0.2, random_state=42)
            hist_pre = self._pt_fit_ce(
                self.dnn_model_full, X_tr, y_tr, X_va, y_va,
                epochs=epochs_pretrain, batch_size=batch_size,
                patience=12, lr=1e-3, min_lr=1e-6)

        # ── Phase 2: E2E unfolding ─────────────────────────────────
        print("\n" + "=" * 60)
        print("  Deep Unfolding Phase 2: E2E curriculum fine-tuning")
        print(f"  SIC mode: '{sic_mode}'")
        print("=" * 60)
        e2e_data = self.generate_e2e_training_dataset(
            n_samples=n_samples, snr_range=snr_range)
        data_pos = e2e_data['data_positions']

        # Deep-copy pre-trained backbone to both stages
        ce_sub1 = copy.deepcopy(self.dnn_model_full)
        ce_sub2 = copy.deepcopy(self.dnn_model_full)

        unfolding_model, ce_sub1, ce_sub2 = self.build_e2e_unfolding_model(
            input_dim, data_pos,
            ce_backbone_1=ce_sub1, ce_backbone_2=ce_sub2,
            sic_mode=sic_mode)
        # (no summary equivalent in PyTorch; skip)

        n = len(e2e_data['X_features'])
        perm  = np.random.permutation(n)
        split = int(0.8 * n)
        tr, va = perm[:split], perm[split:]

        def _inputs(idx):
            return [e2e_data['X_features'][idx],
                    e2e_data['y_received'][idx],
                    e2e_data['x_pilot_frames'][idx],
                    e2e_data['sigma_w2'][idx]]

        def _labels(idx):
            return {
                'bits':               e2e_data['bits_true'][idx],
                'detection':          e2e_data['x_data_true'][idx],
                'channel_est':        e2e_data['y_ce_labels'][idx],
                'bits_stage1':        e2e_data['bits_true'][idx],
                'detection_stage1':   e2e_data['x_data_true'][idx],
                'channel_est_stage1': e2e_data['y_ce_labels'][idx],
            }

        epochs_A = max(1, int(epochs_e2e * phase_a_ratio))
        print(f"\n  Phase 2-A: stabilisation ({epochs_A} epochs)")
        print(f"    S2: det={det_loss_weight}, sym={sym_loss_weight_A}, ce={ce_loss_weight}")
        print(f"    S1: det={s1_bce_weight_A}, sym={s1_sym_weight_A}")
        hist_A = self._pt_fit_unfolding(
            unfolding_model, e2e_data, tr, va, epochs_A, batch_size,
            lr=1e-4, patience=6, min_lr=5e-6,
            det_w=det_loss_weight, sym_w=sym_loss_weight_A, ce_w=ce_loss_weight,
            s1_det_w=s1_bce_weight_A, s1_sym_w=s1_sym_weight_A,
            s1_ce_w=ce_loss_weight * 0.5)

        epochs_B = epochs_e2e - epochs_A
        print(f"\n  Phase 2-B: BER sprint ({epochs_B} epochs)")
        hist_B = self._pt_fit_unfolding(
            unfolding_model, e2e_data, tr, va, epochs_B, batch_size,
            lr=1e-5, patience=10, min_lr=1e-6,
            det_w=det_loss_weight, sym_w=sym_loss_weight_B, ce_w=ce_loss_weight,
            s1_det_w=s1_bce_weight_B, s1_sym_w=s1_sym_weight_B,
            s1_ce_w=ce_loss_weight * 0.5)

        self.unfolding_model  = unfolding_model
        self._unf_ce_s1       = ce_sub1
        self._unf_ce_s2       = ce_sub2
        self._unf_data_pos    = data_pos
        self._unf_n_data      = len(data_pos)
        self._unf_sic_mode    = sic_mode
        return unfolding_model, hist_pre, (hist_A, hist_B), e2e_data

    def evaluate_e2e_unfolding(self, n_test=1000):
        """
        Evaluate the 2-Stage Deep Unfolding model vs baselines.

        Reports Stage-1 and Stage-2 BER/SER separately so the unfolding
        gain is directly measurable.  Requires train_e2e_unfolding() first.
        """
        if not hasattr(self, 'unfolding_model'):
            raise ValueError(
                "unfolding_model not trained — call train_e2e_unfolding() first.")

        snr_list = [5, 10, 15, 20, 25, 30]
        QPSK = np.array([1+1j, 1-1j, -1+1j, -1-1j], dtype=complex) / np.sqrt(2)
        N, rho = self.N_total, self.rho

        _, pilot_pos, pilot_syms, guard_pos, data_pos = self.generate_pilot_frame()
        m0 = self._m0

        results = {snr: {
            'ser_ls': [], 'ser_mmse': [], 'ser_cednn': [],
            'ser_e2e': [], 'ser_unf_s1': [], 'ser_unf_s2': [],
            'ser_omp': [], 'ser_joint': [],
            'ber_ls': [], 'ber_mmse': [], 'ber_cednn': [],
            'ber_e2e': [], 'ber_unf_s1': [], 'ber_unf_s2': [],
            'ber_omp': [], 'ber_joint': [],
        } for snr in snr_list}

        spp = max(1, n_test // len(snr_list))

        def _bits_s(sym_arr):
            return np.concatenate([
                (np.real(sym_arr) < 0).astype(np.float32),
                (np.imag(sym_arr) < 0).astype(np.float32)])

        def _ber(true_sym, est_bits):
            return float(np.mean(np.abs(_bits_s(true_sym) - est_bits)))

        def _ser(true_sym, soft_sym):
            det = (np.where(np.real(soft_sym) >= 0, 1., -1.)
                   + 1j * np.where(np.imag(soft_sym) >= 0, 1., -1.)) / np.sqrt(2)
            tru = (np.where(np.real(true_sym) >= 0, 1., -1.)
                   + 1j * np.where(np.imag(true_sym) >= 0, 1., -1.)) / np.sqrt(2)
            return float(np.mean(np.abs(det - tru) > 1e-6))

        for snr_db in snr_list:
            print(f"  [Unfolding] SNR={snr_db} dB ({spp} samples)...")
            for _ in range(spp):
                H_eff, H_time, _ = self.generate_channel_matrix(
                    np.random.uniform(5, self.max_speed_kmh),
                    np.random.choice(['EPA', 'EVA']))

                data_sym  = QPSK[np.random.randint(0, 4, N)]
                x_data_sc = np.sqrt(1.0 - rho) * data_sym
                x_p_only  = np.zeros(N, dtype=complex)
                x_p_only[pilot_pos] = pilot_syms
                x_full    = x_data_sc + x_p_only

                r_raw, sw2 = self.add_awgn(
                    H_time @ self.afdm_modulation(x_full), snr_db)
                y_daft = self.afdm_demodulation(r_raw)

                # NumPy baselines
                H_ls   = self.improved_ls_estimation(
                    y_daft, pilot_pos, pilot_syms, guard_pos)
                H_mmse = self.traditional_mmse_estimation(
                    y_daft, pilot_pos, pilot_syms, guard_pos, sw2)
                try:
                    H_dnn = self.dnn_estimation(
                        y_daft, pilot_pos, pilot_syms, guard_pos)
                except Exception:
                    H_dnn = H_ls

                xh_ls   = self._lmmse_detect_np(
                    H_ls,   y_daft, x_p_only, data_pos, sw2)
                xh_mmse = self._lmmse_detect_np(
                    H_mmse, y_daft, x_p_only, data_pos, sw2)
                xh_ce   = self._lmmse_detect_np(
                    H_dnn,  y_daft, x_p_only, data_pos, sw2)

                # Classical iterative baselines (OMP + LMMSE / Joint OMP+MP)
                try:
                    xh_omp, _ = self.omp_lmmse_detect(
                        y_daft, x_p_only, data_pos, sw2)
                except Exception:
                    xh_omp = xh_ls
                try:
                    xh_joint, _ = self.joint_iterative_detect(
                        y_daft, x_p_only, data_pos, sw2, n_outer=5)
                except Exception:
                    xh_joint = xh_omp

                # TF-style input prep removed; PyTorch infer helpers take raw arrays

                # Single-stage E2E baseline (PyTorch)
                if hasattr(self, 'e2e_model'):
                    feats_e2e = self.extract_dnn_features(y_daft, pilot_pos, pilot_syms, guard_pos)
                    pe = self._pt_infer_e2e(self.e2e_model, feats_e2e, y_daft, x_p_only, sw2)
                    xh_e2e   = pe['detection'][:N] + 1j * pe['detection'][N:]
                    bits_e2e = (pe['bits'] > 0).astype(np.float32)
                else:
                    xh_e2e   = xh_ls
                    bits_e2e = _bits_s(xh_e2e)

                # Deep Unfolding forward pass (PyTorch)
                feats_unf = self.extract_dnn_features(y_daft, pilot_pos, pilot_syms, guard_pos)
                pu = self._pt_infer_unfolding(self.unfolding_model, feats_unf,
                                              y_daft, x_p_only, sw2)
                xh_s1   = pu['det_s1'][:N] + 1j * pu['det_s1'][N:]
                bits_s1 = (pu['bits_s1'] > 0).astype(np.float32)
                xh_s2   = pu['det_s2'][:N] + 1j * pu['det_s2'][N:]
                bits_s2 = (pu['bits_s2'] > 0).astype(np.float32)

                r = results[snr_db]
                r['ser_ls'].append(_ser(x_data_sc, xh_ls))
                r['ser_mmse'].append(_ser(x_data_sc, xh_mmse))
                r['ser_cednn'].append(_ser(x_data_sc, xh_ce))
                r['ser_e2e'].append(_ser(x_data_sc, xh_e2e))
                r['ser_unf_s1'].append(_ser(x_data_sc, xh_s1))
                r['ser_unf_s2'].append(_ser(x_data_sc, xh_s2))
                r['ser_omp'].append(_ser(x_data_sc, xh_omp))
                r['ser_joint'].append(_ser(x_data_sc, xh_joint))
                r['ber_ls'].append(_ber(x_data_sc, _bits_s(xh_ls)))
                r['ber_mmse'].append(_ber(x_data_sc, _bits_s(xh_mmse)))
                r['ber_cednn'].append(_ber(x_data_sc, _bits_s(xh_ce)))
                r['ber_e2e'].append(_ber(x_data_sc, bits_e2e))
                r['ber_unf_s1'].append(_ber(x_data_sc, bits_s1))
                r['ber_unf_s2'].append(_ber(x_data_sc, bits_s2))
                r['ber_omp'].append(_ber(x_data_sc, _bits_s(xh_omp)))
                r['ber_joint'].append(_ber(x_data_sc, _bits_s(xh_joint)))

        hdr = (f"{'SNR':>4} | {'BER_LS':>9} | {'BER_MMSE':>9} | "
               f"{'BER_OMP':>9} | {'BER_JOINT':>10} | "
               f"{'BER_CEDNN':>9} | "
               f"{'BER_UNF_S1':>10} | {'BER_UNF_S2':>10}")
        print("\n" + "=" * len(hdr))
        print("  Deep Unfolding + Classical Baselines BER Comparison (SP full-domain ZC)")
        print("=" * len(hdr))
        print(hdr)
        print("-" * len(hdr))
        for snr in snr_list:
            r = results[snr]
            print(f"{snr:4d} | {np.mean(r['ber_ls']):9.4e} | "
                  f"{np.mean(r['ber_mmse']):9.4e} | "
                  f"{np.mean(r['ber_omp']):9.4e} | "
                  f"{np.mean(r['ber_joint']):10.4e} | "
                  f"{np.mean(r['ber_cednn']):9.4e} | "
                  f"{np.mean(r['ber_unf_s1']):10.4e} | "
                  f"{np.mean(r['ber_unf_s2']):10.4e}")
        return results

    def generate_training_dataset(self, n_samples=10000, snr_range=(10, 25),
                                   speed_range=None, guard_factor=None):
        """
        Generate training dataset for AFDM 2D-CNN channel estimation.

        Label strategy (fractional Doppler aware):
        - Simulate noise-free transmission through H_time
        - Extract h_tap_clean from clean received signal (same path as LS)
        - De-chirp → map to 2D grid → flatten (real + imag)
        - DNN learns: noisy 2D grid → clean 2D grid (Sinc leakage preserved)
        """
        if speed_range is None:
            speed_range = (5, self.max_speed_kmh)

        K_factor, k_max, L_max, W, pad_size = self._get_2d_grid_params()
        # L_max is now 5, output_2d_dim = 5*15*2 = 150
        output_2d_dim = L_max * W * 2
        QPSK = np.array([1+1j, 1-1j, -1+1j, -1-1j], dtype=complex) / np.sqrt(2)

        # SP DATA AUGMENTATION
        # For each physical channel realization, generate N_AUG different random
        # QPSK data overlays.  The CE label (H_eff) is the SAME for all overlays —
        # this directly teaches the CNN the invariance we need:
        #   "channel estimate must not depend on which data symbols were sent"
        # Effective dataset size = n_samples (n_channels * N_AUG samples total).
        N_AUG = 5   # 5 data overlays per channel; 50k/5=10k unique channels
        n_channels = n_samples // N_AUG   # unique channel realizations
        actual_samples = n_channels * N_AUG

        print(f"Generating AFDM SP training dataset: {n_channels} channels × {N_AUG} data-aug = {actual_samples} samples")
        print(f"  SP mode: rho={self.rho:.2f} (pilot), 1-rho={1-self.rho:.2f} (data)")
        print(f"  SNR range: {snr_range[0]} - {snr_range[1]} dB  (re-sampled per aug)")
        print(f"  Speed range: {speed_range[0]:.1f} - {speed_range[1]:.1f} km/h")
        print(f"  Grid: ({L_max}x{W}x2={output_2d_dim} dim), pad_size={pad_size}")

        X_data = []
        y_data_full = []
        metadata = {
            'snr_values': [], 'speed_values': [],
            'channel_types': [], 'pilot_densities': []
        }

        FIXED_PILOT_DENSITY = 0.25   # kept for API compat; not used in SP

        # Fixed pilot frame structure (same for every sample)
        _, pilot_pos, pilot_syms, guard_pos, data_pos = self.generate_pilot_frame()
        m0 = self._m0
        N  = self.N_total
        x_pilot_only_base        = np.zeros(N, dtype=complex)
        x_pilot_only_base[pilot_pos] = pilot_syms

        for i in range(n_channels):
            if (i + 1) % 500 == 0:
                print(f"  Generated {(i+1)*N_AUG}/{actual_samples} samples...")

            max_speed    = np.random.uniform(speed_range[0], speed_range[1])
            channel_type = np.random.choice(['EPA', 'EVA'])

            # Generate ONE channel realization for this group
            H_eff, H_time, ch_params = self.generate_channel_matrix(
                max_speed, channel_type)

            # Compute CE label ONCE — shared by all N_AUG augmentations
            h_tap_clean           = self._generate_clean_h_tap(H_eff, m0)
            h_tap_clean_dechirped = self._dechirp(h_tap_clean, m0=m0)
            h_2d_clean = self.map_1d_to_2d_grid(h_tap_clean_dechirped,
                                                 pad_size=pad_size)
            full_target = np.concatenate([
                np.real(h_2d_clean).flatten(),
                np.imag(h_2d_clean).flatten()
            ])

            # Pre-modulate the pilot-only frame (constant across augs)
            s_pilot_mod = self.afdm_modulation(x_pilot_only_base)

            for aug in range(N_AUG):
                # Fresh random SNR and QPSK data for each augmentation
                snr_db         = np.random.uniform(snr_range[0], snr_range[1])
                data_sym       = QPSK[np.random.randint(0, 4, N)]
                x_data_scaled  = np.sqrt(1.0 - self.rho) * data_sym
                x_full         = x_data_scaled + x_pilot_only_base

                # Transmit SP frame through H_time
                s = self.afdm_modulation(x_full)
                r_noisy, sigma_w_2 = self.add_awgn(H_time @ s, snr_db)
                y_daft_noisy = self.afdm_demodulation(r_noisy)

                features = self.extract_dnn_features(
                    y_daft_noisy, pilot_pos, pilot_syms, guard_pos)

                X_data.append(features)
                y_data_full.append(full_target)   # same label for all augs
                metadata['snr_values'].append(snr_db)
                metadata['speed_values'].append(max_speed)
                metadata['channel_types'].append(channel_type)
                metadata['pilot_densities'].append(FIXED_PILOT_DENSITY)

        X_raw = np.array(X_data)
        y_raw = np.array(y_data_full)

        # Global scalar scaling — single divisor per domain.
        # Unlike StandardScaler (per-feature), this preserves the relative
        # magnitudes between all pixels, keeping the PDP structure intact.
        # StandardScaler would amplify noise-only pixels to unit variance,
        # destroying the multipath energy profile the CNN needs to learn.
        self.global_std_X = max(float(np.std(X_raw)), 1e-8)
        self.global_std_y = max(float(np.std(y_raw)), 1e-8)
        X_scaled = X_raw / self.global_std_X
        y_scaled = y_raw / self.global_std_y
        print(f"  Global Scaler X std: {self.global_std_X:.6f}")
        print(f"  Global Scaler Y std: {self.global_std_y:.6f}")
        metadata['global_std_X'] = self.global_std_X
        metadata['global_std_y'] = self.global_std_y

        return {
            'X_data': X_scaled,
            'y_data_full': y_scaled,
            'X_raw': X_raw,
            'y_raw': y_raw,
            'metadata': metadata
        }

    # ------------------------------------------------------------------ #
    #  Turbo Refiner training                                              #
    # ------------------------------------------------------------------ #

    def train_turbo_refiner(self,
                            pretrained_e2e_model,
                            n_samples=20000,
                            snr_range=(0, 25),
                            epochs=30,
                            batch_size=64,
                            lr=5e-4,
                            patience=8,
                            min_lr=1e-6):
        """
        Train the Stage-2 ChannelRefiner (TurboRefinerModel) with a frozen
        Stage-1 E2EModel as the soft-information provider.

        Loss: pure MSE on the normalized 2D channel-grid output
              MSE( channel_est_s2 , y_ce_labels )

        This is identical in scale to Phase-1 CE pre-training, making
        val_loss / val_nmse directly comparable.

        Args:
            pretrained_e2e_model : loaded E2EModel (Stage-1).
            n_samples  : E2E training samples to generate (default 20k).
            snr_range  : SNR range for data generation.
            epochs     : max training epochs.
            batch_size : mini-batch size (recommend 64 due to H_flat memory).
            lr / min_lr: initial / floor learning rate.
            patience   : EarlyStopping patience.

        Returns: (turbo_model, hist)
          hist : dict {'loss', 'val_loss', 'val_nmse'}
        """
        print("\n" + "=" * 60)
        print("  Turbo Refiner Training  (Stage-1 frozen, refiner trainable)")
        print("=" * 60)

        # ─ Build turbo model ──────────────────────────────────────────
        turbo_model, _ = self.build_turbo_refiner_model(
            pretrained_e2e_model, device=self._pt_device())

        # ─ Data ───────────────────────────────────────────────────────
        e2e_data = self.generate_e2e_training_dataset(
            n_samples=n_samples, snr_range=snr_range)

        n     = len(e2e_data['X_features'])
        perm  = np.random.permutation(n)
        split = int(0.8 * n)
        tr, va = perm[:split], perm[split:]

        hist = self._pt_fit_refiner(
            turbo_model, e2e_data, tr, va, epochs, batch_size,
            lr=lr, patience=patience, min_lr=min_lr)

        self.turbo_model = turbo_model
        return turbo_model, hist

    # ------------------------------------------------------------------ #
    #  OAMP-Net training                                                    #
    # ------------------------------------------------------------------ #

    def train_oamp_e2e(self,
                       pretrained_ce_backbone=None,
                       n_samples=20000,
                       snr_range=(0, 25),
                       epochs_phase_a=20,
                       epochs_phase_b=15,
                       batch_size=64,
                       lr_a=1e-2,
                       lr_b=1e-5,
                       patience=8,
                       min_lr=1e-6,
                       num_oamp_layers=4):
        """
        Two-phase OAMP-Net E2E training strategy:

        Phase A (冻结 CE 骨干, 只训练 OAMP 9 个参数):
          - Freeze ce_backbone, train only OAMP scalars (2T+1 params)
          - High LR (lr_a=1e-2) converges OAMP quickly from random init
          - 20 epochs default (few params, converges fast)

        Phase B (解冻全网络联合微调):
          - Unfreeze CE backbone, joint training
          - Low LR (lr_b=1e-5) to avoid destroying pre-trained CE
          - 15 epochs default (fine-tune regime)

        Args:
            pretrained_ce_backbone : CEBackbone with pre-trained weights.
                                     If None, CE is trained from scratch in Phase A.
            n_samples              : number of E2E training samples.
            snr_range              : SNR range for data generation.
            epochs_phase_a/b       : epochs per phase.
            batch_size             : mini-batch (recommend 64 due to 4× N³ OAMP).
            lr_a / lr_b            : learning rates for Phase A / B.
            patience               : EarlyStopping patience (per phase).
            min_lr                 : LR scheduler floor.
            num_oamp_layers        : OAMP unrolling depth (default 4).

        Returns: (oamp_e2e_model, hist_a, hist_b)
        """
        print("\n" + "█" * 70)
        print("  OAMP-NET E2E TRAINING  (CE frozen Phase-A, joint Phase-B)")
        print("█" * 70)

        # ─ Generate E2E dataset (常规数据集, 和 E2E / Refiner 一致) ───────────
        e2e_data = self.generate_e2e_training_dataset(
            n_samples=n_samples, snr_range=snr_range)
        data_pos  = e2e_data['data_positions']
        input_dim = e2e_data['X_features'].shape[1]

        n     = len(e2e_data['X_features'])
        perm  = np.random.permutation(n)
        split = int(0.8 * n)
        tr, va = perm[:split], perm[split:]

        # ─ Build E2EOAMPModel ────────────────────────────────────────────────────
        oamp_model, ce_sub = self.build_e2e_oamp_model(
            input_dim, data_pos,
            ce_backbone=pretrained_ce_backbone,
            num_oamp_layers=num_oamp_layers,
            device=self._pt_device())

        n_oamp = sum(p.numel() for p in oamp_model.oamp.parameters())
        n_ce   = sum(p.numel() for p in oamp_model.backbone.parameters())
        print(f"  Phase-A: 冻结 CE ({n_ce:,} params), 训练 OAMP ({n_oamp:,} params)")

        # ─ Phase A: CE frozen, OAMP only ──────────────────────────────────
        print(f"\n  Phase A: {epochs_phase_a} epochs (冻结 CE, 高 LR={lr_a:.0e})")
        for p in oamp_model.backbone.parameters():
            p.requires_grad = False
        hist_a = self._pt_fit_oamp(
            oamp_model, e2e_data, tr, va,
            epochs=epochs_phase_a, batch_size=batch_size,
            lr=lr_a, patience=patience, min_lr=min_lr)

        # ─ Phase B: joint fine-tune all params ───────────────────────────
        print(f"\n  Phase B: {epochs_phase_b} epochs (解冻 CE, 全网络联合微调 LR={lr_b:.0e})")
        for p in oamp_model.backbone.parameters():
            p.requires_grad = True
        hist_b = self._pt_fit_oamp(
            oamp_model, e2e_data, tr, va,
            epochs=epochs_phase_b, batch_size=batch_size,
            lr=lr_b, patience=patience + 4, min_lr=1e-7)

        self.oamp_model = oamp_model
        return oamp_model, hist_a, hist_b

    def train_ep_e2e(self,
                     pretrained_ce_backbone=None,
                     n_samples=20000,
                     snr_range=(0, 25),
                     epochs_phase_a=20,
                     epochs_phase_b=15,
                     batch_size=64,
                     lr_a=5e-3,
                     lr_b=1e-5,
                     patience=8,
                     min_lr=1e-6,
                     num_ep_layers=4):
        """
        Two-phase EP detector training with the same CE scaffold as OAMP.

        Returns: (ep_e2e_model, hist_a, hist_b)
        """
        print("\n" + "█" * 70)
        print("  EP E2E TRAINING  (CE frozen Phase-A, joint Phase-B)")
        print("█" * 70)

        e2e_data = self.generate_e2e_training_dataset(
            n_samples=n_samples, snr_range=snr_range)
        data_pos = e2e_data['data_positions']
        input_dim = e2e_data['X_features'].shape[1]

        n = len(e2e_data['X_features'])
        perm = np.random.permutation(n)
        split = int(0.8 * n)
        tr, va = perm[:split], perm[split:]

        ep_model, _ = self.build_e2e_ep_model(
            input_dim, data_pos,
            ce_backbone=pretrained_ce_backbone,
            num_ep_layers=num_ep_layers,
            device=self._pt_device())

        n_ep = sum(p.numel() for p in ep_model.ep.parameters())
        n_ce = sum(p.numel() for p in ep_model.backbone.parameters())
        print(f"  Phase-A: 冻结 CE ({n_ce:,} params), 训练 EP ({n_ep:,} params)")

        print(f"\n  Phase A: {epochs_phase_a} epochs (冻结 CE, 高 LR={lr_a:.0e})")
        for p in ep_model.backbone.parameters():
            p.requires_grad = False
        hist_a = self._pt_fit_ep(
            ep_model, e2e_data, tr, va,
            epochs=epochs_phase_a, batch_size=batch_size,
            lr=lr_a, patience=patience, min_lr=min_lr)

        print(f"\n  Phase B: {epochs_phase_b} epochs (解冻 CE, 全网络联合微调 LR={lr_b:.0e})")
        for p in ep_model.backbone.parameters():
            p.requires_grad = True
        hist_b = self._pt_fit_ep(
            ep_model, e2e_data, tr, va,
            epochs=epochs_phase_b, batch_size=batch_size,
            lr=lr_b, patience=patience + 4, min_lr=1e-7)

        self.ep_model = ep_model
        return ep_model, hist_a, hist_b

    def train_turbo_joint(self,
                          pretrained_ce_state_dict=None,
                          pretrained_detector_state_dict=None,
                          pretrained_oamp_state_dict=None,
                          n_samples=20000,
                          snr_range=(0, 25),
                          dataset_cache_path=None,
                          resume_checkpoint_path=None,
                          epochs_phase_a=30,
                          epochs_phase_b=20,
                          batch_size=32,
                          lr_a=5e-4,
                          lr_b=5e-5,
                          patience=8,
                          min_lr=1e-7,
                          num_outer_iters=3,
                          num_oamp_layers=4,
                          detector_type='oamp',
                          lambda_bce=1.0, lambda_sym=0.2,
                          lambda_ce=0.1,  lambda_obs=0.02):
        """
        Stage-4 deep-unrolled Turbo joint fine-tuning.

        Phase A (freeze CE, train OAMP+Refiner, lr_a=5e-4, 30 epochs):
          OAMP detectors and Channel Refiners learn to cooperate with the
          frozen CE backbone.  Refiner gets 10× higher lr (param groups)
          because it trains from scratch with Kaiming init + alpha-scale.

        Phase B (unfreeze all, joint fine-tune, lr_b=5e-5, 20 epochs):
          Full end-to-end gradient flow through CE backbone, OAMP, and
          Refiner. CE gets 0.1× lr for protection.

        Layer-wise multi-task loss (compute_turbo_loss):
          - BCE on LLR per iteration (BER driver)
          - Symbol MSE (physical anchor)
          - CE MSE (normalised h_2d grid)
          - Measurement consistency (lambda_obs=0.01 Phase B)

        batch_size=32: 3 outer iters × 4 OAMP layers × N×N inv ≈ 10 GB VRAM

        Returns: (turbo_model, hist_a, hist_b)
        """
        print("\n" + "█" * 70)
        print("  JOINT TURBO RECEIVER TRAINING  T={} outer iters".format(num_outer_iters))
        print("█" * 70)

        # ─ Generate or load dataset ──────────────────────────────
        if dataset_cache_path is not None:
            cache_path = Path(dataset_cache_path)
            if cache_path.exists():
                e2e_data = self.load_e2e_dataset_cache(cache_path)
            else:
                e2e_data = self.generate_e2e_training_dataset(
                    n_samples=n_samples, snr_range=snr_range)
                self.save_e2e_dataset_cache(e2e_data, cache_path)
        else:
            e2e_data = self.generate_e2e_training_dataset(
                n_samples=n_samples, snr_range=snr_range)
        data_pos  = e2e_data['data_positions']
        input_dim = e2e_data['X_features'].shape[1]

        n    = len(e2e_data['X_features'])
        perm = np.random.permutation(n)
        split = int(0.8 * n)
        tr, va = perm[:split], perm[split:]

        # ─ Build JointTurboReceiver ───────────────────────────────
        device = self._pt_device()
        turbo_model, _ = self.build_turbo_receiver(
            input_dim, data_pos,
            ce_state_dict   = pretrained_ce_state_dict,
            detector_state_dict = pretrained_detector_state_dict,
            oamp_state_dict = pretrained_oamp_state_dict,
            num_outer_iters = num_outer_iters,
            num_oamp_layers = num_oamp_layers,
            detector_type   = detector_type,
            device          = device,
        )

        empty_hist = {'loss': [], 'val_loss': [], 'val_ber': []}
        resume_payload = None
        phase_hists = {'phase_a': empty_hist.copy(), 'phase_b': empty_hist.copy()}
        if resume_checkpoint_path is not None:
            resume_path = Path(resume_checkpoint_path)
            if resume_path.exists():
                resume_payload = torch.load(str(resume_path), map_location=device)
                if 'model_state' in resume_payload:
                    turbo_model.load_state_dict(resume_payload['model_state'])
                phase_hists.update(resume_payload.get('phase_hists', {}))
                print(f"  Resume checkpoint loaded ← {resume_path}")

        resume_phase = resume_payload.get('phase') if resume_payload else None
        resume_epoch = int(resume_payload.get('epoch', 0)) if resume_payload else 0
        if resume_phase == 'done':
            print("  Resume checkpoint indicates training already finished; "
                  "loading final model and skipping fit.")
            self.turbo_model = turbo_model
            return turbo_model, phase_hists['phase_a'], phase_hists['phase_b']

        loss_kw = dict(lambda_bce=lambda_bce, lambda_sym=lambda_sym,
                       lambda_ce=lambda_ce,   lambda_obs=lambda_obs)

        # ─ Phase A: CE frozen ──────────────────────────────────────
        n_ce = sum(p.numel() for p in turbo_model.backbone.parameters())
        print(f"\n  Phase A: {epochs_phase_a} epochs — CE frozen ({n_ce:,} params), "
              f"lr={lr_a:.0e}, batch={batch_size}")
        for p in turbo_model.backbone.parameters():
            p.requires_grad = False
        self._turbo_phase_name = 'phase_a'
        self._turbo_resume_path = resume_checkpoint_path
        self._turbo_phase_hists = phase_hists
        if resume_phase == 'phase_b' or (resume_phase == 'phase_a' and resume_epoch >= epochs_phase_a):
            hist_a = phase_hists.get('phase_a', empty_hist.copy())
            print("  Phase A already complete in resume checkpoint; skipping.")
        else:
            self._turbo_resume_state = resume_payload if resume_phase == 'phase_a' else None
            hist_a = self._pt_fit_turbo(
                turbo_model, e2e_data, tr, va,
                epochs=epochs_phase_a, batch_size=batch_size,
                lr=lr_a, patience=patience, min_lr=min_lr,
                loss_kw=loss_kw)
            phase_hists['phase_a'] = hist_a

        # ─ Phase B: joint fine-tune ───────────────────────────────
        # Refiner has now learned meaningful delta_H; enable mild loss_obs.
        loss_kw_b = dict(lambda_bce=lambda_bce, lambda_sym=lambda_sym,
                         lambda_ce=lambda_ce,   lambda_obs=max(lambda_obs, 0.2))
        print(f"\n  Phase B: {epochs_phase_b} epochs — joint fine-tune, "
              f"lr={lr_b:.0e}, batch={batch_size}")
        for p in turbo_model.backbone.parameters():
            p.requires_grad = True
        self._turbo_phase_name = 'phase_b'
        self._turbo_phase_hists = phase_hists
        if resume_phase == 'phase_b' and resume_epoch >= epochs_phase_b:
            hist_b = phase_hists.get('phase_b', empty_hist.copy())
            print("  Phase B already complete in resume checkpoint; skipping.")
        else:
            self._turbo_resume_state = resume_payload if resume_phase == 'phase_b' else None
            hist_b = self._pt_fit_turbo(
                turbo_model, e2e_data, tr, va,
                epochs=epochs_phase_b, batch_size=batch_size,
                lr=lr_b, patience=patience + 5, min_lr=1e-8,
                loss_kw=loss_kw_b)
            phase_hists['phase_b'] = hist_b

        if resume_checkpoint_path is not None:
            torch.save({
                'phase': 'done',
                'epoch': epochs_phase_b,
                'model_state': turbo_model.state_dict(),
                'phase_hists': phase_hists,
            }, str(Path(resume_checkpoint_path)))

        self.turbo_model = turbo_model
        return turbo_model, hist_a, hist_b

    def dnn_estimation(self, y_daft, pilot_pos, pilot_syms, guard_pos,
                       pilot_density=None):
        """
        DNN-based SP channel estimation.
        pilot_density is accepted for API compatibility but ignored (SP mode).
        """
        m0 = self._m0
        K_factor, k_max, L_max, W, pad_size = self._get_2d_grid_params()

        features = self.extract_dnn_features(
            y_daft, pilot_pos, pilot_syms, guard_pos, pilot_density)
        features = features.reshape(1, -1)

        if self.dnn_model_full is None:
            raise ValueError("DNN model not trained")

        # Global scalar: same single divisor used at training time
        if self.global_std_X is not None:
            features = features / self.global_std_X

        pred_scaled = self._pt_predict_backbone(self.dnn_model_full, features)[0]

        # Undo global y-scaling to recover physical channel magnitudes
        if self.global_std_y is not None:
            prediction = pred_scaled * self.global_std_y
        else:
            prediction = pred_scaled
        real_2d = prediction[:L_max * W].reshape(L_max, W)
        imag_2d = prediction[L_max * W:].reshape(L_max, W)
        h_2d_pred = real_2d + 1j * imag_2d

        # pass pad_size explicitly — must match the pad_size used during training
        h_tap_pred_dechirped = self.map_2d_grid_to_1d(h_2d_pred, pad_size=pad_size)

        # FIX: rechirp with correct m0-aware cross-term
        h_tap_pred = self._rechirp(h_tap_pred_dechirped, m0=m0)

        H_est = self._reconstruct_H_eff_from_taps_2d(h_tap_pred, m0)
        return H_est

    def run_comparison_test(self, n_test=1000, guard_factor=None):
        """Run comprehensive comparison test for AFDM"""
        print(f"Running AFDM channel estimation comparison with {n_test} samples...")
        
        results = {
            'snr_values': [], 'mse_ls': [], 'mse_mmse': [], 'mse_dnn': [],
            'nmse_ls': [], 'nmse_mmse': [], 'nmse_dnn': [], 'nmse_omp': [],
            'time_ls': [], 'time_mmse': [], 'time_dnn': [], 'time_omp': []
        }
        
        snr_test_values = [5, 10, 15, 20, 25, 30]
        samples_per_snr = max(1, n_test // len(snr_test_values))
        
        training_snr_set = set(range(10, 26))   # training snr_range=(10,25)
        for snr_db in snr_test_values:
            ood_tag = " [OOD]" if snr_db not in training_snr_set else ""
            print(f"Testing at SNR = {snr_db} dB{ood_tag}...")
            
            snr_results = {key: [] for key in results.keys() if key != 'snr_values'}
            
            for _ in range(samples_per_snr):
                max_speed = np.random.uniform(5, self.max_speed_kmh)
                channel_type = np.random.choice(['EPA', 'EVA'])
                # FIX: match training which uses FIXED_PILOT_DENSITY=0.25.
                # Randomizing here would feed out-of-distribution aux feature
                # values to the DNN, degrading test NMSE artificially.
                pilot_density = 0.25
                
                # Generate channel
                H_eff, H_time, ch_params = self.generate_channel_matrix(
                    max_speed, channel_type)

                # SP frame assembly
                _, pilot_pos, pilot_syms, guard_pos, data_pos = \
                    self.generate_pilot_frame()
                N = self.N_total
                qpsk_run      = np.array([1+1j, 1-1j, -1+1j, -1-1j]) / np.sqrt(2)
                x_data_sc_run = np.sqrt(1.0 - self.rho) * qpsk_run[np.random.randint(0,4,N)]
                x_p_only_run  = np.zeros(N, dtype=complex)
                x_p_only_run[pilot_pos] = pilot_syms
                x_full_run    = x_data_sc_run + x_p_only_run

                # Transmission
                s = self.afdm_modulation(x_full_run)
                r_clean = H_time @ s
                r_noisy, sigma_w_2 = self.add_awgn(r_clean, snr_db)
                y_daft = self.afdm_demodulation(r_noisy)

                # LS estimation
                start_time = time.time()
                H_ls = self.improved_ls_estimation(
                    y_daft, pilot_pos, pilot_syms, guard_pos)
                time_ls = time.time() - start_time

                # MMSE estimation
                start_time = time.time()
                H_mmse = self.traditional_mmse_estimation(
                    y_daft, pilot_pos, pilot_syms, guard_pos, sigma_w_2)
                time_mmse = time.time() - start_time

                # DNN estimation
                start_time = time.time()
                try:
                    H_dnn = self.dnn_estimation(
                        y_daft, pilot_pos, pilot_syms, guard_pos)
                except Exception:
                    H_dnn = H_ls
                time_dnn = time.time() - start_time

                # OMP estimation
                start_time = time.time()
                try:
                    H_omp = self.omp_channel_estimate(y_daft)
                except Exception:
                    H_omp = H_ls
                time_omp = time.time() - start_time
                
                # Metrics
                mse_ls = np.mean(np.abs(H_eff - H_ls) ** 2)
                mse_mmse = np.mean(np.abs(H_eff - H_mmse) ** 2)
                mse_dnn = np.mean(np.abs(H_eff - H_dnn) ** 2)
                
                nmse_ls = self.calculate_nmse(H_eff, H_ls)
                nmse_mmse = self.calculate_nmse(H_eff, H_mmse)
                nmse_dnn = self.calculate_nmse(H_eff, H_dnn)
                nmse_omp = self.calculate_nmse(H_eff, H_omp)
                
                snr_results['mse_ls'].append(mse_ls)
                snr_results['mse_mmse'].append(mse_mmse)
                snr_results['mse_dnn'].append(mse_dnn)
                snr_results['nmse_ls'].append(nmse_ls)
                snr_results['nmse_mmse'].append(nmse_mmse)
                snr_results['nmse_dnn'].append(nmse_dnn)
                snr_results['nmse_omp'].append(nmse_omp)
                snr_results['time_ls'].append(time_ls)
                snr_results['time_mmse'].append(time_mmse)
                snr_results['time_dnn'].append(time_dnn)
                snr_results['time_omp'].append(time_omp)
            
            results['snr_values'].append(snr_db)
            for key in snr_results:
                results[key].append(np.mean(snr_results[key]))
        
        return results
    
    
    def visualize_pilot_placement(self, pilot_density=None, guard_factor=None):
        """Visualize AFDM SP pilot frame (data everywhere, pilot at m0)."""
        N = self.N_total
        _, pilot_pos, pilot_syms, guard_pos, data_pos = self.generate_pilot_frame()

        # Build a representative SP frame with random QPSK for amplitude display
        qpsk_vis     = np.array([1+1j, 1-1j, -1+1j, -1-1j]) / np.sqrt(2)
        x_data_sc_v  = np.sqrt(1.0 - self.rho) * qpsk_vis[np.random.randint(0,4,N)]
        x_p_only_v   = np.zeros(N, dtype=complex)
        x_p_only_v[pilot_pos] = pilot_syms
        x_frame      = x_data_sc_v + x_p_only_v

        fig, axes = plt.subplots(2, 1, figsize=(16, 8))

        # --- Plot 1: SP frame magnitude ---
        ax1 = axes[0]
        colors = np.full(N, 'steelblue', dtype=object)   # all = data
        colors[pilot_pos] = 'red'                         # pilot position

        ax1.bar(np.arange(N), np.abs(x_frame), color=colors, width=1.0)
        ax1.set_title(f'AFDM SP Frame (N={N}, rho={self.rho:.2f})\n'
                      f'Full-domain ZC pilot (phase anchor m0={self._m0}),  '
                      f'Data on ALL {len(data_pos)} sub-carriers  '
                      f'(no guard interval)')
        ax1.set_xlabel('DAFT Domain Index')
        ax1.set_ylabel('Symbol Amplitude')
        ax1.legend(handles=[
            plt.Rectangle((0, 0), 1, 1, color='red', label=f'Pilot (power={self.rho*N:.1f}x)'),
            plt.Rectangle((0, 0), 1, 1, color='steelblue', label='Data (all sub-carriers)'),
        ], loc='upper right')
        ax1.grid(True, alpha=0.3)
        
        # --- Plot 2: 2D-like view (reshape for visualization) ---
        ax2 = axes[1]
        if self.N_total == self.N * self.M:
            # Numeric encoding for imshow: 0=data, 1=pilot
            num_colors = np.zeros(N)
            num_colors[pilot_pos] = 1
            grid_2d = num_colors.reshape(self.M, self.N)
            cmap = plt.cm.colors.ListedColormap(['steelblue', 'red'])
            im = ax2.imshow(grid_2d, cmap=cmap, origin='lower',
                           extent=[0, self.N, 0, self.M], aspect='auto')
            ax2.set_title(f'2D View (reshaped {self.M}×{self.N}, SP — no guard zone)')
            ax2.set_xlabel('Column Index')
            ax2.set_ylabel('Row Index')
            plt.colorbar(im, ax=ax2, ticks=[0, 1],
                        label='0=Data (all), 1=Pilot')

        plt.tight_layout()
        plt.savefig(f'afdm_sp_pilot_placement_rho{self.rho:.2f}.png', dpi=300)
        # plt.show()

        print(f"AFDM SP Pilot Information:")
        print(f"  Total subcarriers: {self.N_total}")
        print(f"  rho = {self.rho:.2f}  (pilot power fraction)")
        print(f"  Full-domain ZC pilot: phase anchor m0 = {self._m0}  "
              f"(amplitude sqrt(rho) = {float(np.sqrt(self.rho)):.3f} per ZC subcarrier)")
        print(f"  Data on ALL {self.N_total} sub-carriers  "
              f"(amplitude sqrt(1-rho) = {np.sqrt(1-self.rho):.3f} per QPSK symbol)")
        print(f"  Guard:  NONE  (SP — 100% spectral efficiency)")
        print(f"  c1={self.c1:.8f}, c2={self.c2:.8f}")

        return x_frame
    
    def visualize_channel_estimation_results(self, n_vis=1, guard_factor=None):
        """Visualize AFDM SP channel estimation results."""

        print(f"Visualizing AFDM SP channel estimation results...")
        N = self.N_total

        for vis_idx in range(n_vis):
            max_speed = min(200, self.max_speed_kmh)
            channel_type = 'EVA'
            snr_db = 20

            H_eff, H_time, ch_params = self.generate_channel_matrix(
                max_speed, channel_type)

            # SP frame
            _, pilot_pos, pilot_syms, guard_pos, data_pos = self.generate_pilot_frame()
            qpsk_v       = np.array([1+1j, 1-1j, -1+1j, -1-1j]) / np.sqrt(2)
            x_data_sc_v  = np.sqrt(1.0 - self.rho) * qpsk_v[np.random.randint(0,4,N)]
            x_p_only_v   = np.zeros(N, dtype=complex)
            x_p_only_v[pilot_pos] = pilot_syms
            x_full_v     = x_data_sc_v + x_p_only_v

            s = self.afdm_modulation(x_full_v)
            r_clean = H_time @ s
            r_noisy, sigma_w_2 = self.add_awgn(r_clean, snr_db)
            y_daft = self.afdm_demodulation(r_noisy)

            H_ls = self.improved_ls_estimation(
                y_daft, pilot_pos, pilot_syms, guard_pos)
            H_mmse = self.traditional_mmse_estimation(
                y_daft, pilot_pos, pilot_syms, guard_pos, sigma_w_2)

            try:
                H_dnn = self.dnn_estimation(
                    y_daft, pilot_pos, pilot_syms, guard_pos)
            except Exception:
                H_dnn = H_ls
            
            fig = plt.figure(figsize=(16, 12))
            
            display_size = min(100, self.N_total)
            matrices = {
                'True H_eff': (np.abs(H_eff[:display_size, :display_size]), 'viridis'),
                'LS Estimation': (np.abs(H_ls[:display_size, :display_size]), 'plasma'),
                'MMSE Estimation': (np.abs(H_mmse[:display_size, :display_size]), 'coolwarm'),
                'DNN Blind Estimation': (np.abs(H_dnn[:display_size, :display_size]), 'inferno')
            }
            
            X_mesh, Y_mesh = np.meshgrid(
                np.arange(display_size), np.arange(display_size))
            
            for idx, (title, (H_mag, cmap)) in enumerate(matrices.items()):
                ax = fig.add_subplot(2, 2, idx + 1, projection='3d')
                ax.plot_surface(X_mesh, Y_mesh, H_mag, cmap=cmap, alpha=0.8)
                ax.set_title(f'{title} ({display_size}×{display_size})')
                ax.set_xlabel('Col')
                ax.set_ylabel('Row')
                ax.set_zlabel('|H|')
            
            plt.suptitle(
                f'AFDM Channel Estimation Comparison (Blind DNN)\n'
                f'SNR={snr_db}dB, Speed={max_speed}km/h, {channel_type}, '
                f'c1={self.c1:.6f}, c2={self.c2:.6f}',
                fontsize=14)
            plt.tight_layout()
            plt.savefig(
                f'afdm_channel_estimation_blind_{vis_idx}.png',
                dpi=300, bbox_inches='tight')
            # plt.show()
            
            # Metrics
            mse_ls = np.mean(np.abs(H_eff - H_ls) ** 2)
            mse_mmse = np.mean(np.abs(H_eff - H_mmse) ** 2)
            mse_dnn = np.mean(np.abs(H_eff - H_dnn) ** 2)
            nmse_ls = self.calculate_nmse(H_eff, H_ls)
            nmse_mmse = self.calculate_nmse(H_eff, H_mmse)
            nmse_dnn = self.calculate_nmse(H_eff, H_dnn)
            
            print(f"Sample {vis_idx + 1} Performance (AFDM Blind DNN):")
            print(f"  MSE  - LS: {mse_ls:.2e}, MMSE: {mse_mmse:.2e}, DNN: {mse_dnn:.2e}")
            print(f"  NMSE - LS: {nmse_ls:.2e}, MMSE: {nmse_mmse:.2e}, DNN: {nmse_dnn:.2e}")
            print()
    
    def comprehensive_comparison(self, n_train=20000, n_test=1000, epochs=100,
                                  batch_size=64):
        """Run comprehensive AFDM SP comparison with blind DNN estimation"""
        
        # Diagnose feasibility
        self.diagnose_reconstruction()
        
        # Validate
        validation_results = self.validate_implementation()
        if not all(validation_results.values()):
            print("Warning: AFDM implementation validation failed!")
            for check, passed in validation_results.items():
                print(f"  {check}: {'PASS' if passed else 'FAIL'}")
            print()
        
        # Visualize pilot placement
        print("=== AFDM SP Pilot Placement ===")
        self.visualize_pilot_placement()
        
        print(f"\n=== Using 2D-CNN Fractional Doppler DNN (no SNR/speed info) ===")
        print(f"SP mode: rho={self.rho:.2f}  (pilot power fraction)")
        print(f"Chirp: c1={self.c1:.8f}, c2={self.c2:.8f}")
        K_factor, k_max, L_max, W, _ = self._get_2d_grid_params()
        print(f"DNN input/output: 2D grid ({L_max}x{W}x2 = {L_max*W*2} dim) + 4 aux")
        print(f"  vs old target: 1D h_tap ({self.N_total}*2={self.N_total*2}) "
              f"or full H_eff ({self.N_total**2}*2={self.N_total**2*2} dim)")
        print(f"NMSE: norm-based ||H_est - H_true||^2/||H_true||^2")
        
        # Generate training data with SNR range 10-25 dB
        dataset = self.generate_training_dataset(
            n_samples=n_train,
            snr_range=(10, 25))       # <-- fixed SNR range
        
        # Train DNN
        print("Training AFDM Blind DNN...")
        self.dnn_model_full = self.build_dnn_model_full(dataset['X_data'].shape[1])
        X_train, X_val, y_train, y_val = train_test_split(
            dataset['X_data'], dataset['y_data_full'],
            test_size=0.2, random_state=42)
        
        history = self._pt_fit_ce(
            self.dnn_model_full, X_train, y_train, X_val, y_val,
            epochs=epochs, batch_size=batch_size, patience=15,
            lr=1e-3, min_lr=1e-6)
        
        # Test
        test_results = self.run_comparison_test(n_test)
        
        result = {
            'test_results': test_results,
            'training_history': history,
            'dataset_info': {
                'input_dim': dataset['X_data'].shape[1],
                'output_dim': y_train.shape[1],
                'n_samples': len(dataset['X_data'])
            },
            'validation_results': validation_results,
            'rho': self.rho,
            'c1': self.c1,
            'c2': self.c2
        }
        
        print(f"Visualizing AFDM SP blind channel estimation results...")
        self.visualize_channel_estimation_results(n_vis=2)
        
        return result
    
    def plot_results(self, result):
        """Plot AFDM SP comparison results"""
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        
        test_results = result['test_results']
        history = result['training_history']   # dict with 'loss'/'val_loss' lists
        rho_val = result.get('rho', self.rho)

        # Training history (PyTorch history is a plain dict)
        hist_d = history if isinstance(history, dict) else history.history
        axes[0].plot(hist_d.get('loss', []), label='Training Loss', linewidth=2)
        axes[0].plot(hist_d.get('val_loss', []), label='Validation Loss', linewidth=2)
        axes[0].set_xlabel('Epoch')
        axes[0].set_ylabel('Loss')
        axes[0].set_title(f'AFDM SP Blind DNN Training\n(rho={rho_val:.2f})')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        axes[0].set_yscale('log')
        
        # MSE
        axes[1].semilogy(test_results['snr_values'], test_results['mse_ls'],
                         'o-', label='LS', linewidth=2, markersize=8)
        axes[1].semilogy(test_results['snr_values'], test_results['mse_mmse'],
                         's-', label='MMSE', linewidth=2, markersize=8)
        axes[1].semilogy(test_results['snr_values'], test_results['mse_dnn'],
                         '^-', label='Blind DNN', linewidth=2, markersize=8)
        axes[1].set_xlabel('SNR (dB)')
        axes[1].set_ylabel('MSE')
        axes[1].set_title('AFDM: MSE vs SNR')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        # NMSE
        axes[2].semilogy(test_results['snr_values'], test_results['nmse_ls'],
                         'o-', label='LS', linewidth=2, markersize=8)
        axes[2].semilogy(test_results['snr_values'], test_results['nmse_mmse'],
                         's-', label='MMSE', linewidth=2, markersize=8)
        if 'nmse_omp' in test_results:
            axes[2].semilogy(test_results['snr_values'], test_results['nmse_omp'],
                             'v-', label='OMP', linewidth=2, markersize=8,
                             color='#9467bd')
        axes[2].semilogy(test_results['snr_values'], test_results['nmse_dnn'],
                         '^-', label='Blind DNN', linewidth=2, markersize=8)
        axes[2].set_xlabel('SNR (dB)')
        axes[2].set_ylabel('NMSE')
        axes[2].set_title('AFDM: NMSE vs SNR (Norm-based)')
        axes[2].legend()
        axes[2].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f'afdm_sp_blind_results_rho{rho_val:.2f}.png',
                    dpi=500, bbox_inches='tight')
        # plt.show()
    # ================================================================
    # PyTorch training / inference helpers
    # ================================================================

    def _pt_device(self):
        """Return the best available device."""
        return torch.device('cuda' if torch.cuda.is_available() else
                            'mps'  if torch.backends.mps.is_available() else 'cpu')

    def _pt_fit_ce(self, model, X_tr, y_tr, X_va, y_va,
                   epochs=50, batch_size=128, patience=10,
                   lr=1e-3, min_lr=1e-6):
        """
        Fit a CEBackbone (nn.Module) with MSE loss and early stopping.

        LR schedule: CosineAnnealingLR — decays smoothly from lr → min_lr over
        'epochs' steps every epoch, so the user always sees LR decreasing.
        Early stopping: fires after 'patience' epochs without a new val_loss best.

        Returns a history dict  {'loss': [...], 'val_loss': [...]}.
        """
        device = self._pt_device()
        model  = model.to(device)

        Xt = torch.from_numpy(X_tr).float()
        yt = torch.from_numpy(y_tr).float()
        Xv = torch.from_numpy(X_va).float().to(device)
        yv = torch.from_numpy(y_va).float().to(device)

        loader = DataLoader(TensorDataset(Xt, yt),
                            batch_size=batch_size, shuffle=True,
                            num_workers=0,
                            pin_memory=(device.type == 'cuda'))
        opt   = torch.optim.Adam(model.parameters(), lr=lr)
        # CosineAnnealingLR: lr decays every epoch, always visible to user
        sched = torch.optim.lr_scheduler.CosineAnnealingLR(
            opt, T_max=epochs, eta_min=min_lr)
        mse   = nn.MSELoss()
        scaler = torch.cuda.amp.GradScaler(enabled=(device.type == 'cuda'))

        best_val = float('inf');  pat_cnt = 0
        best_sd  = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        hist     = {'loss': [], 'val_loss': []}
        t0_fit   = time.time()

        for ep in range(epochs):
            t_ep = time.time()
            model.train()
            ep_loss = 0.0
            for xb, yb in loader:
                xb, yb = xb.to(device), yb.to(device)
                opt.zero_grad()
                with torch.cuda.amp.autocast(enabled=(device.type == 'cuda')):
                    loss = mse(model(xb), yb)
                scaler.scale(loss).backward()
                scaler.step(opt);  scaler.update()
                ep_loss += loss.item()
            ep_loss /= len(loader)

            model.eval()
            with torch.no_grad():
                val_loss = mse(model(Xv), yv).item()
            sched.step()   # CosineAnnealing advances every epoch regardless of val

            hist['loss'].append(ep_loss)
            hist['val_loss'].append(val_loss)

            _ep_bar('CE ', ep, epochs, t_ep, t0_fit, ep_loss, val_loss,
                    opt.param_groups[0]['lr'])

            if val_loss < best_val - 1e-4:
                best_val = val_loss;  pat_cnt = 0
                best_sd  = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            else:
                pat_cnt += 1
                if pat_cnt >= patience:
                    print(f"\n  Early stop at epoch {ep+1}  (best val={best_val:.4e})")
                    break
        else:
            print()  # newline after last epoch bar

        model.load_state_dict(best_sd)
        return hist

    def _pt_fit_e2e(self, model, e2e_data, tr_idx, va_idx,
                    epochs, batch_size, lr, patience, min_lr,
                    det_w, sym_w, ce_w):
        """
        Fit an E2EModel with multi-task loss (BCE + sym-MSE + CE-MSE).
        Returns a history dict.
        """
        device = self._pt_device()
        model  = model.to(device)

        def _tensors(idx):
            d = e2e_data
            return (torch.from_numpy(d['X_features'][idx]).float(),
                    torch.from_numpy(d['y_received'][idx]).float(),
                    torch.from_numpy(d['x_pilot_frames'][idx]).float(),
                    torch.from_numpy(d['sigma_w2'][idx]).float(),
                    torch.from_numpy(d['x_data_true'][idx]).float(),
                    torch.from_numpy(d['bits_true'][idx]).float(),
                    torch.from_numpy(d['y_ce_labels'][idx]).float())

        tr_ds = TensorDataset(*_tensors(tr_idx))
        va_ds = TensorDataset(*_tensors(va_idx))
        tr_loader = DataLoader(tr_ds, batch_size=batch_size, shuffle=True,
                               num_workers=0,
                               pin_memory=(device.type == 'cuda'))

        bce = nn.BCEWithLogitsLoss()
        mse = nn.MSELoss()
        opt   = torch.optim.Adam(model.parameters(), lr=lr)
        sched = torch.optim.lr_scheduler.ReduceLROnPlateau(
            opt, factor=0.5, patience=max(2, patience // 2),
            min_lr=min_lr)
        scaler = torch.cuda.amp.GradScaler(enabled=(device.type == 'cuda'))

        best_val = float('inf');  pat_cnt = 0
        best_sd  = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        hist     = {'loss': [], 'val_loss': []}
        t0_fit   = time.time()

        # Chunked val eval — never forward-pass all val samples at once (OOM on small GPU)
        def _val_loss_e2e(chunk=128):
            total = 0.0;  n = 0
            for i in range(0, va_ds.tensors[0].shape[0], chunk):
                Xf,Yr,Xp,Sw,Xd,Bt,Ce = [t[i:i+chunk].to(device) for t in va_ds.tensors]
                with torch.cuda.amp.autocast(enabled=(device.type == 'cuda')):
                    out_v = model(Xf, Yr, Xp, Sw)
                    vl = (det_w * bce(out_v['bits'], Bt)
                        + sym_w * mse(out_v['detection'], Xd)
                        + ce_w  * mse(out_v['channel_est'], Ce))
                bs = Xf.shape[0];  total += vl.item() * bs;  n += bs
            return total / max(n, 1)

        for ep in range(epochs):
            t_ep = time.time()
            model.train();  ep_loss = 0.0
            for Xf, Yr, Xp, Sw, Xd, Bt, Ce in tr_loader:
                Xf,Yr,Xp,Sw,Xd,Bt,Ce = (t.to(device)
                    for t in (Xf,Yr,Xp,Sw,Xd,Bt,Ce))
                opt.zero_grad()
                with torch.cuda.amp.autocast(enabled=(device.type == 'cuda')):
                    out  = model(Xf, Yr, Xp, Sw)
                    loss = (det_w * bce(out['bits'], Bt)
                          + sym_w * mse(out['detection'], Xd)
                          + ce_w  * mse(out['channel_est'], Ce))
                scaler.scale(loss).backward()
                scaler.step(opt);  scaler.update()
                ep_loss += loss.item()
            ep_loss /= len(tr_loader)

            model.eval()
            with torch.no_grad():
                val_loss = _val_loss_e2e()
            sched.step(val_loss)
            hist['loss'].append(ep_loss)
            hist['val_loss'].append(val_loss)
            _ep_bar('E2E', ep, epochs, t_ep, t0_fit, ep_loss, val_loss,
                    opt.param_groups[0]['lr'])
            if val_loss < best_val - 1e-4:
                best_val = val_loss;  pat_cnt = 0
                best_sd  = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            else:
                pat_cnt += 1
                if pat_cnt >= patience:
                    print(f"\n  Early stop at epoch {ep+1}");  break
        else:
            print()  # newline after last epoch bar
        model.load_state_dict(best_sd)
        return hist

    def _pt_fit_oamp(self, model, e2e_data, tr_idx, va_idx,
                     epochs, batch_size, lr, patience, min_lr):
        """
        Fit an E2EOAMPModel with multi-task loss (BCE + sym-MSE + CE-MSE).

        Differences from _pt_fit_e2e():
          - batch_size=64 default (4× N³ matrix inv per layer)
          - Chunked validation with chunk=32 (safety margin)
          - Logs train_loss, val_loss, val_ber_approx per epoch
          - Respects frozen params: only requires_grad=True params in optimizer

        Returns: hist dict with keys 'loss', 'val_loss', 'val_ber'
        """
        device = self._pt_device()
        model  = model.to(device)

        def _tensors(idx):
            d = e2e_data
            return (torch.from_numpy(d['X_features'][idx]).float(),
                    torch.from_numpy(d['y_received'][idx]).float(),
                    torch.from_numpy(d['x_pilot_frames'][idx]).float(),
                    torch.from_numpy(d['sigma_w2'][idx]).float(),
                    torch.from_numpy(d['x_data_true'][idx]).float(),
                    torch.from_numpy(d['bits_true'][idx]).float(),
                    torch.from_numpy(d['y_ce_labels'][idx]).float())

        tr_ds = TensorDataset(*_tensors(tr_idx))
        va_ds = TensorDataset(*_tensors(va_idx))
        tr_loader = DataLoader(tr_ds, batch_size=batch_size, shuffle=True,
                               num_workers=0,
                               pin_memory=(device.type == 'cuda'))

        bce = nn.BCEWithLogitsLoss()
        mse = nn.MSELoss()
        # Only optimize unfrozen parameters
        trainable_params = [p for p in model.parameters() if p.requires_grad]
        opt   = torch.optim.Adam(trainable_params, lr=lr)
        sched = torch.optim.lr_scheduler.ReduceLROnPlateau(
            opt, factor=0.5, patience=max(2, patience // 2),
            min_lr=min_lr)
        # AMP disabled: OAMPLayer uses float32 internally (linalg.inv)
        # Using the scaler anyway for uniformity; autocast enabled=False on OAMP layers
        scaler = torch.cuda.amp.GradScaler(enabled=(device.type == 'cuda'))

        best_val = float('inf');  pat_cnt = 0
        best_sd  = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        hist     = {'loss': [], 'val_loss': [], 'val_ber': []}
        t0_fit   = time.time()

        det_w = 1.0; sym_w = 0.3; ce_w = 0.1

        def _val_loss_oamp(chunk=32):
            total = 0.0;  n = 0;  n_bit_err = 0;  n_bits = 0
            for i in range(0, va_ds.tensors[0].shape[0], chunk):
                Xf, Yr, Xp, Sw, Xd, Bt, Ce = [t[i:i+chunk].to(device)
                                                for t in va_ds.tensors]
                with torch.no_grad():
                    out_v = model(Xf, Yr, Xp, Sw)
                    vl = (det_w * bce(out_v['bits'], Bt)
                        + sym_w * mse(out_v['detection'], Xd)
                        + ce_w  * mse(out_v['channel_est'], Ce))
                    # Approx BER from hard decisions on x_hat
                    N = out_v['detection'].shape[1] // 2
                    xr = out_v['detection'][:, :N].detach().cpu(); xd_r = Xd[:, :N].cpu()
                    n_bit_err += ((xr > 0) != (xd_r > 0)).float().sum().item()
                    n_bits    += xr.numel()
                bs = Xf.shape[0];  total += vl.item() * bs;  n += bs
            ber = n_bit_err / max(n_bits, 1)
            return total / max(n, 1), ber

        det_label = 'EP' if hasattr(model, 'ep') and not hasattr(model, 'oamp') else 'OAMP'

        for ep in range(epochs):
            t_ep = time.time()
            model.train();  ep_loss = 0.0
            for Xf, Yr, Xp, Sw, Xd, Bt, Ce in tr_loader:
                Xf, Yr, Xp, Sw, Xd, Bt, Ce = (t.to(device)
                    for t in (Xf, Yr, Xp, Sw, Xd, Bt, Ce))
                opt.zero_grad()
                # AMP with autocast=False inside OAMP; the outer autocast is a no-op
                with torch.cuda.amp.autocast(enabled=(device.type == 'cuda')):
                    out  = model(Xf, Yr, Xp, Sw)
                    loss = (det_w * bce(out['bits'], Bt)
                          + sym_w * mse(out['detection'], Xd)
                          + ce_w  * mse(out['channel_est'], Ce))
                scaler.scale(loss).backward()
                nn.utils.clip_grad_norm_(trainable_params, max_norm=1.0)
                scaler.step(opt);  scaler.update()
                ep_loss += loss.item()
            ep_loss /= len(tr_loader)

            model.eval()
            with torch.no_grad():
                val_loss, val_ber = _val_loss_oamp()
            sched.step(val_loss)
            hist['loss'].append(ep_loss);  hist['val_loss'].append(val_loss)
            hist['val_ber'].append(val_ber)

            n_tr = sum(1 for p in model.parameters() if p.requires_grad)
            elapsed = time.time() - t_ep
            eta_s   = int(elapsed * (epochs - ep - 1))
            lr_now  = opt.param_groups[0]['lr']
            print(f"  {det_label} [{ep+1:3d}/{epochs}]  "
                  f"loss={ep_loss:.3e}  val={val_loss:.3e}  "
                  f"val_ber={val_ber:.4f}  lr={lr_now:.1e}  "
                  f"{elapsed:.0f}s/ep  ETA {eta_s//60}m{eta_s%60:02d}s",
                  flush=True)

            if val_loss < best_val - 1e-4:
                best_val = val_loss;  pat_cnt = 0
                best_sd  = {k: v.detach().cpu().clone()
                            for k, v in model.state_dict().items()}
            else:
                pat_cnt += 1
                if pat_cnt >= patience:
                    print(f"\n  Early stop at epoch {ep+1}");  break
        else:
            print()
        model.load_state_dict(best_sd)
        return hist

    def _pt_fit_ep(self, model, e2e_data, tr_idx, va_idx,
                   epochs, batch_size, lr, patience, min_lr):
        """
        EP detector training reuses the same E2E loss and output contract as OAMP.
        """
        return self._pt_fit_oamp(
            model, e2e_data, tr_idx, va_idx,
            epochs=epochs, batch_size=batch_size,
            lr=lr, patience=patience, min_lr=min_lr)

    def _pt_fit_turbo(self, model, e2e_data, tr_idx, va_idx,
                      epochs, batch_size, lr, patience, min_lr,
                      loss_kw=None):
        """
        Training loop for JointTurboReceiver with layer-wise multi-task loss.

        Uses the same 7-tensor dataloader as _pt_fit_oamp. batch_size=32
        recommended for T=3 (3×4 OAMP matrix inversions per forward pass).
        Validation is chunked (chunk=16) to avoid OOM.
        """
        _turbo_loss_fn = compute_turbo_loss   # module-level in afdm_trainer.py

        if loss_kw is None:
            loss_kw = {}
        device = self._pt_device()
        model  = model.to(device)

        def _tensors(idx):
            d = e2e_data
            return (torch.from_numpy(d['X_features'][idx]).float(),
                    torch.from_numpy(d['y_received'][idx]).float(),
                    torch.from_numpy(d['x_pilot_frames'][idx]).float(),
                    torch.from_numpy(d['sigma_w2'][idx]).float(),
                    torch.from_numpy(d['x_data_true'][idx]).float(),
                    torch.from_numpy(d['bits_true'][idx]).float(),
                    torch.from_numpy(d['y_ce_labels'][idx]).float())

        tr_ds = TensorDataset(*_tensors(tr_idx))
        va_ds = TensorDataset(*_tensors(va_idx))
        tr_loader = DataLoader(tr_ds, batch_size=batch_size, shuffle=True,
                               pin_memory=False, drop_last=True)
        va_loader = DataLoader(va_ds, batch_size=16, shuffle=False,
                               pin_memory=False)

        # ── Differentiated param groups ────────────────────────────
        # Refiner (680k params, initially untrained) needs higher lr;
        # OAMP (9 scalars, pre-trained) uses base lr;
        # CE backbone (Phase B only) needs protection with lower lr.
        refiner_params = list(model.refiners.parameters()) + \
                         list(model.refine_scales.parameters())
        oamp_params    = list(model.detectors.parameters())
        ce_params      = [p for p in model.backbone.parameters()
                          if p.requires_grad]
        param_groups = []
        if refiner_params:
            param_groups.append({'params': refiner_params, 'lr': lr * 10})
        if oamp_params:
            param_groups.append({'params': oamp_params,    'lr': lr})
        if ce_params:
            param_groups.append({'params': ce_params,      'lr': lr * 0.1})
        if not param_groups:
            param_groups = [{'params': [torch.zeros(1, requires_grad=True,
                                                     device=device)], 'lr': lr}]
        trainable = [p for pg in param_groups for p in pg['params']]
        opt       = torch.optim.Adam(param_groups, eps=1e-7)
        sched     = torch.optim.lr_scheduler.ReduceLROnPlateau(
            opt, mode='min', factor=0.5, patience=max(2, patience // 2),
            min_lr=min_lr)
        scaler    = torch.amp.GradScaler(device='cuda',
                                         enabled=device.type == 'cuda')

        best_val  = float('inf')
        best_sd   = {k: v.detach().cpu().clone()
                     for k, v in model.state_dict().items()}
        pat_cnt   = 0
        hist      = {'loss': [], 'val_loss': [], 'val_ber': []}
        t0_fit    = time.time()

        for ep in range(epochs):
            t_ep = time.time()
            model.train()
            ep_loss = 0.0

            for batch in tr_loader:
                (Xf, Yr, Xp, Sw, Xd, Bt, YCE) = [
                    b.to(device) for b in batch]
                with torch.amp.autocast('cuda', enabled=device.type == 'cuda'):
                    out   = model(Xf, Yr, Xp, Sw)
                    loss  = _turbo_loss_fn(
                        out, Bt, Xd, YCE, Yr, Xp, **loss_kw)
                scaler.scale(loss).backward()
                scaler.unscale_(opt)
                torch.nn.utils.clip_grad_norm_(trainable, max_norm=1.0)
                scaler.step(opt);  scaler.update();  opt.zero_grad()
                ep_loss += loss.item()

            ep_loss /= max(len(tr_loader), 1)
            hist['loss'].append(ep_loss)

            # ── chunked validation ─────────────────────────────────────
            model.eval()
            val_loss = 0.0
            bits_correct = 0;  bits_total = 0
            with torch.no_grad():
                for batch in va_loader:
                    (Xf, Yr, Xp, Sw, Xd, Bt, YCE) = [
                        b.to(device) for b in batch]
                    with torch.amp.autocast('cuda', enabled=device.type == 'cuda'):
                        out  = model(Xf, Yr, Xp, Sw)
                        vloss= _turbo_loss_fn(
                            out, Bt, Xd, YCE, Yr, Xp, **loss_kw)
                    val_loss += vloss.item()
                    # BER from final iteration LLR (hard decision)
                    llr_last = out['final_bits']
                    pred_bits = (llr_last > 0).float()
                    bits_correct += (pred_bits == Bt).sum().item()
                    bits_total   += Bt.numel()

            val_loss /= max(len(va_loader), 1)
            val_ber   = 1.0 - bits_correct / max(bits_total, 1)
            sched.step(val_loss)
            hist['val_loss'].append(val_loss)
            hist['val_ber'].append(val_ber)

            elapsed = time.time() - t_ep
            eta_s   = int(elapsed * (epochs - ep - 1))
            lrs_str = '/'.join(f"{g['lr']:.1e}" for g in opt.param_groups)
            # Print refine_scales if available
            alpha_str = ''
            if hasattr(model, 'refine_scales'):
                alphas = [f"{s.item():.3f}" for s in model.refine_scales]
                alpha_str = f"  α=[{','.join(alphas)}]"
            print(f"  Turbo [{ep+1:3d}/{epochs}]  "
                  f"loss={ep_loss:.3e}  val={val_loss:.3e}  "
                  f"val_ber={val_ber:.4f}  lr={lrs_str}{alpha_str}  "
                  f"{elapsed:.0f}s/ep  ETA {eta_s//60}m{eta_s%60:02d}s",
                  flush=True)

            if val_loss < best_val - 1e-4:
                best_val = val_loss;  pat_cnt = 0
                best_sd  = {k: v.detach().cpu().clone()
                            for k, v in model.state_dict().items()}
            else:
                pat_cnt += 1
                if pat_cnt >= patience:
                    print(f"\n  Early stop at epoch {ep+1}");  break
        else:
            print()
        model.load_state_dict(best_sd)
        return hist

    def _pt_fit_unfolding(self, model, e2e_data, tr_idx, va_idx,
                          epochs, batch_size, lr, patience, min_lr,
                          det_w, sym_w, ce_w,
                          s1_det_w, s1_sym_w, s1_ce_w):
        """Fit UnfoldingModel with 6-output multi-task loss."""
        device = self._pt_device()
        model  = model.to(device)

        def _tensors(idx):
            d = e2e_data
            return (torch.from_numpy(d['X_features'][idx]).float(),
                    torch.from_numpy(d['y_received'][idx]).float(),
                    torch.from_numpy(d['x_pilot_frames'][idx]).float(),
                    torch.from_numpy(d['sigma_w2'][idx]).float(),
                    torch.from_numpy(d['x_data_true'][idx]).float(),
                    torch.from_numpy(d['bits_true'][idx]).float(),
                    torch.from_numpy(d['y_ce_labels'][idx]).float())

        tr_ds = TensorDataset(*_tensors(tr_idx))
        va_ds = TensorDataset(*_tensors(va_idx))
        tr_loader = DataLoader(tr_ds, batch_size=batch_size, shuffle=True,
                               num_workers=0,
                               pin_memory=(device.type == 'cuda'))
        bce = nn.BCEWithLogitsLoss();  mse = nn.MSELoss()
        opt   = torch.optim.Adam(model.parameters(), lr=lr)
        sched = torch.optim.lr_scheduler.ReduceLROnPlateau(
            opt, factor=0.5, patience=max(2, patience // 2),
            min_lr=min_lr)
        scaler = torch.cuda.amp.GradScaler(enabled=(device.type == 'cuda'))

        def _multi_loss(outs, Xd, Bt, Ce, d_w, s_w, c_w, s1d, s1s, s1c):
            b_s1, x_s1, ce_s1, b_s2, x_s2, ce_s2 = outs
            return (d_w  * bce(b_s2, Bt) + s_w  * mse(x_s2, Xd) + c_w  * mse(ce_s2, Ce)
                  + s1d  * bce(b_s1, Bt) + s1s  * mse(x_s1, Xd) + s1c  * mse(ce_s1, Ce))

        # Chunked val eval to avoid OOM on small GPUs
        def _val_loss_unf(chunk=128):
            total = 0.0;  n = 0
            for i in range(0, va_ds.tensors[0].shape[0], chunk):
                Xf,Yr,Xp,Sw,Xd,Bt,Ce = [t[i:i+chunk].to(device) for t in va_ds.tensors]
                with torch.cuda.amp.autocast(enabled=(device.type == 'cuda')):
                    outs_v = model(Xf, Yr, Xp, Sw)
                    vl = _multi_loss(outs_v, Xd, Bt, Ce, det_w, sym_w, ce_w,
                                     s1_det_w, s1_sym_w, s1_ce_w)
                bs = Xf.shape[0];  total += vl.item() * bs;  n += bs
            return total / max(n, 1)

        best_val = float('inf');  pat_cnt = 0
        best_sd  = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        hist     = {'loss': [], 'val_loss': []}
        t0_fit   = time.time()

        for ep in range(epochs):
            t_ep = time.time()
            model.train();  ep_loss = 0.0
            for Xf, Yr, Xp, Sw, Xd, Bt, Ce in tr_loader:
                Xf,Yr,Xp,Sw,Xd,Bt,Ce = (t.to(device)
                    for t in (Xf,Yr,Xp,Sw,Xd,Bt,Ce))
                opt.zero_grad()
                with torch.cuda.amp.autocast(enabled=(device.type == 'cuda')):
                    outs = model(Xf, Yr, Xp, Sw)
                    loss = _multi_loss(outs, Xd, Bt, Ce,
                                       det_w, sym_w, ce_w,
                                       s1_det_w, s1_sym_w, s1_ce_w)
                scaler.scale(loss).backward()
                scaler.step(opt);  scaler.update()
                ep_loss += loss.item()
            ep_loss /= len(tr_loader)

            model.eval()
            with torch.no_grad():
                val_loss = _val_loss_unf()
            sched.step(val_loss)
            hist['loss'].append(ep_loss)
            hist['val_loss'].append(val_loss)
            _ep_bar('Unf', ep, epochs, t_ep, t0_fit, ep_loss, val_loss,
                    opt.param_groups[0]['lr'])
            if val_loss < best_val - 1e-4:
                best_val = val_loss;  pat_cnt = 0
                best_sd  = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            else:
                pat_cnt += 1
                if pat_cnt >= patience:
                    print(f"\n  Early stop at epoch {ep+1}");  break
        else:
            print()  # newline after last epoch bar
        model.load_state_dict(best_sd)
        return hist

    def _pt_fit_refiner(self, model, e2e_data, tr_idx, va_idx,
                        epochs, batch_size, lr, patience, min_lr):
        """
        Fit TurboRefinerModel with pure CE-MSE loss on the normalised 2D grid.

        Tracks and reports NMSE (linear, in physical scale) on the validation
        set each epoch alongside the val_loss.

        Returns history dict {'loss', 'val_loss', 'val_nmse'}.
        """
        device = self._pt_device()
        model  = model.to(device)
        std_y  = float(self.global_std_y) if self.global_std_y is not None else 1.0

        def _tensors(idx):
            d = e2e_data
            return (torch.from_numpy(d['X_features'][idx]).float(),
                    torch.from_numpy(d['y_received'][idx]).float(),
                    torch.from_numpy(d['x_pilot_frames'][idx]).float(),
                    torch.from_numpy(d['sigma_w2'][idx]).float(),
                    torch.from_numpy(d['y_ce_labels'][idx]).float())

        tr_ds = TensorDataset(*_tensors(tr_idx))
        va_ds = TensorDataset(*_tensors(va_idx))
        tr_loader = DataLoader(tr_ds, batch_size=batch_size, shuffle=True,
                               num_workers=0,
                               pin_memory=(device.type == 'cuda'))
        mse    = nn.MSELoss()
        # Only optimize parameters that require grad (refiner + LMMSE noise_floor)
        opt    = torch.optim.Adam(
            filter(lambda p: p.requires_grad, model.parameters()), lr=lr)
        sched  = torch.optim.lr_scheduler.CosineAnnealingLR(
            opt, T_max=epochs, eta_min=min_lr)
        scaler = torch.cuda.amp.GradScaler(enabled=(device.type == 'cuda'))

        best_val = float('inf');  pat_cnt = 0
        best_sd  = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        hist     = {'loss': [], 'val_loss': [], 'val_nmse': []}
        t0_fit   = time.time()

        # Chunked validation: avoids OOM from H_flat (524K floats/sample)
        def _val_loss_refiner(chunk=32):
            total_loss = 0.0;  total_nmse = 0.0;  n = 0
            for i in range(0, va_ds.tensors[0].shape[0], chunk):
                Xf, Yr, Xp, Sw, Ce = [t[i:i+chunk].to(device)
                                      for t in va_ds.tensors]
                with torch.cuda.amp.autocast(enabled=(device.type == 'cuda')):
                    out_v  = model(Xf, Yr, Xp, Sw)
                    vl     = mse(out_v['channel_est_s2'], Ce)
                    # NMSE in physical scale: unnorm pred vs unnorm label
                    pred_p = out_v['channel_est_s2'].detach() * std_y
                    true_p = Ce * std_y
                    diff2  = (pred_p - true_p).pow(2).sum(dim=-1)   # (B,)
                    norm2  = true_p.pow(2).sum(dim=-1).clamp_min(1e-30)
                    total_nmse += (diff2 / norm2).sum().item()
                bs = Xf.shape[0]
                total_loss += vl.item() * bs
                n += bs
            return total_loss / max(n, 1), total_nmse / max(n, 1)

        for ep in range(epochs):
            t_ep = time.time()
            model.train();  ep_loss = 0.0
            for Xf, Yr, Xp, Sw, Ce in tr_loader:
                Xf, Yr, Xp, Sw, Ce = (t.to(device)
                    for t in (Xf, Yr, Xp, Sw, Ce))
                opt.zero_grad()
                with torch.cuda.amp.autocast(enabled=(device.type == 'cuda')):
                    out  = model(Xf, Yr, Xp, Sw)
                    loss = mse(out['channel_est_s2'], Ce)
                scaler.scale(loss).backward()
                scaler.step(opt);  scaler.update()
                ep_loss += loss.item()
            ep_loss /= len(tr_loader)

            model.eval()
            with torch.no_grad():
                val_loss, val_nmse = _val_loss_refiner()
            sched.step()

            hist['loss'].append(ep_loss)
            hist['val_loss'].append(val_loss)
            hist['val_nmse'].append(val_nmse)

            t_ep_s = time.time() - t_ep
            elapsed = time.time() - t0_fit
            eta = elapsed / (ep + 1) * (epochs - ep - 1)
            import sys as _sys
            _sys.stdout.write(
                f"\r  Ref [{ep+1:3d}/{epochs}]  "
                f"loss={ep_loss:.3e}  val={val_loss:.3e}  "
                f"val_nmse={val_nmse:.4f}  "
                f"lr={opt.param_groups[0]['lr']:.1e}  "
                f"{t_ep_s:.0f}s/ep  ETA {int(eta//60)}m{int(eta%60):02d}s")
            _sys.stdout.flush()

            if val_loss < best_val - 1e-5:
                best_val = val_loss;  pat_cnt = 0
                best_sd  = {k: v.detach().cpu().clone()
                            for k, v in model.state_dict().items()}
            else:
                pat_cnt += 1
                if pat_cnt >= patience:
                    print(f"\n  Early stop at epoch {ep+1}  "
                          f"(best val={best_val:.4e}  val_nmse={val_nmse:.4f})")
                    break
        else:
            print()  # newline

        model.load_state_dict(best_sd)
        return hist

    def _pt_infer_e2e(self, model, feats_raw, y_daft, x_p, sw2):
        """
        Single-sample inference for E2EModel.
        Returns dict with float32 numpy arrays: 'detection', 'bits', 'channel_est'.
        """
        device = self._pt_device()
        model.eval()
        N  = self.N_total
        std_x = float(self.global_std_X) if self.global_std_X else 1.0
        feats_n = (feats_raw.reshape(1, -1) / std_x).astype(np.float32)
        yr  = np.concatenate([np.real(y_daft),   np.imag(y_daft)], 0)[None].astype(np.float32)
        xpr = np.concatenate([np.real(x_p),      np.imag(x_p)],   0)[None].astype(np.float32)
        sig = np.array([[sw2]], dtype=np.float32)
        with torch.no_grad():
            out = model(torch.from_numpy(feats_n).to(device),
                        torch.from_numpy(yr).to(device),
                        torch.from_numpy(xpr).to(device),
                        torch.from_numpy(sig).to(device))
        return {k: v[0].cpu().numpy() for k, v in out.items()}

    def _pt_infer_unfolding(self, model, feats_raw, y_daft, x_p, sw2):
        """
        Single-sample inference for UnfoldingModel.
        Returns dict with float32 numpy arrays.
        """
        device = self._pt_device()
        model.eval()
        N  = self.N_total
        std_x = float(self.global_std_X) if self.global_std_X else 1.0
        feats_n = (feats_raw.reshape(1, -1) / std_x).astype(np.float32)
        yr  = np.concatenate([np.real(y_daft),   np.imag(y_daft)], 0)[None].astype(np.float32)
        xpr = np.concatenate([np.real(x_p),      np.imag(x_p)],   0)[None].astype(np.float32)
        sig = np.array([[sw2]], dtype=np.float32)
        with torch.no_grad():
            b_s1, x_s1, ce_s1, b_s2, x_s2, ce_s2 = model(
                torch.from_numpy(feats_n).to(device),
                torch.from_numpy(yr).to(device),
                torch.from_numpy(xpr).to(device),
                torch.from_numpy(sig).to(device))
        return dict(bits_s1=b_s1[0].cpu().numpy(),
                    det_s1=x_s1[0].cpu().numpy(),
                    ce_s1=ce_s1[0].cpu().numpy(),
                    bits_s2=b_s2[0].cpu().numpy(),
                    det_s2=x_s2[0].cpu().numpy(),
                    ce_s2=ce_s2[0].cpu().numpy())

    def _pt_predict_backbone(self, model, features_f32):
        """
        Batch inference on CEBackbone.
        features_f32: (n_samples, input_dim) float32 numpy array (already scaled).
        Returns (n_samples, output_dim) float32 numpy array.
        """
        device = self._pt_device()
        model.to(device)
        model.eval()
        out_list = []
        BS = 128
        with torch.no_grad():
            for i in range(0, len(features_f32), BS):
                xb = torch.from_numpy(
                    features_f32[i:i+BS].astype(np.float32)).to(device)
                out_list.append(model(xb).cpu().numpy())
        return np.concatenate(out_list, axis=0)
