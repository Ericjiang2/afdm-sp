"""
run_sp_unfolding.py — Entry-point for AFDM SP deep-unfolding experiment.

Usage:
    cd afdm_sp_refactored
    /opt/anaconda3/envs/CE/bin/python run_sp_unfolding.py

AFDMSystem = AFDMEnvMixin + AFDMModelsMixin + AFDMTrainerMixin.
All self.* references resolve through normal Python MRO.
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pickle
import warnings
warnings.filterwarnings('ignore')
import sys, pathlib
# Allow   python run_sp_unfolding.py  from inside the package folder
# as well as   python -m afdm_sp_refactored.run_sp_unfolding  from parent.
_HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(_HERE.parent))   # add OTFS-channel-estimation/ to path

from afdm_sp_refactored.afdm_env       import AFDMEnvMixin
from afdm_sp_refactored.afdm_models    import AFDMModelsMixin
from afdm_sp_refactored.afdm_trainer   import AFDMTrainerMixin
from afdm_sp_refactored.afdm_baselines import AFDMBaselinesMixin


class AFDMSystem(AFDMEnvMixin, AFDMModelsMixin, AFDMTrainerMixin, AFDMBaselinesMixin):
    """
    Monolithic AFDM system assembled from three decoupled mixins.
    Replaces the original AFDMChannelEstimator god-class.
    Usage is identical: AFDMSystem(N=10, M=10, rho=0.3)
    """
    pass


def main():
    """Main function to run AFDM SP blind channel estimation comparison"""
    
    # Configuration
    N_DOPPLER = 10
    M_DELAY = 10
    N_TRAIN_SAMPLES = 50000   # ceil(50000/3)=16667 unique channels × N_AUG=3
    N_TEST_SAMPLES = 8000
    EPOCHS = 60        # patience=15 + more LR drops; SP needs longer to converge
    BATCH_SIZE = 64    # smaller batch → noisier gradients → better generalisation
    RHO = 0.3          # SP pilot power fraction (0 < rho < 1)
    ENABLE_UNFOLDING = True   # set False to skip Phase D (2-stage deep unfolding)
    ENABLE_E2E = False         # set True to run Phase C (E2E CE→LMMSE fine-tuning)
    
    print("=" * 60)
    print("  AFDM Superimposed Pilot (SP) Channel Estimation")
    print("=" * 60)
    print(f"Configuration:")
    print(f"  AFDM subcarriers: N_total = {N_DOPPLER * M_DELAY} (from {N_DOPPLER}x{M_DELAY})")
    print(f"  Training samples: {N_TRAIN_SAMPLES}")
    print(f"  Test samples: {N_TEST_SAMPLES}")
    print(f"  Training epochs: {EPOCHS}")
    print(f"  Batch size: {BATCH_SIZE}")
    print(f"  SP rho: {RHO}  (pilot power fraction; data power = 1-rho={1-RHO:.2f})")
    print(f"  DNN Type: 2D-CNN ResNet hybrid kernels (blind)")
    print(f"  DNN output: h_tap ({N_DOPPLER * M_DELAY}*2 dim) -> Eq.3.39 reconstruct")
    print(f"  NMSE: ||H_est - H_true||^2_F / ||H_true||^2_F")
    print()
    
    # Initialize
    estimator = AFDMSystem(N=N_DOPPLER, M=M_DELAY, rho=RHO)
    
    # Run comparison
    result = estimator.comprehensive_comparison(
        n_train=N_TRAIN_SAMPLES,
        n_test=N_TEST_SAMPLES,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE
    )
    
    # Plot
    estimator.plot_results(result)
    
    # Save
    save_result = {k: v for k, v in result.items() if k != 'training_history'}
    _hist = result['training_history']
    _hd   = _hist if isinstance(_hist, dict) else _hist.history
    save_result['training_history_loss']     = _hd.get('loss', [])
    save_result['training_history_val_loss'] = _hd.get('val_loss', [])
    
    with open(f'afdm_sp_blind_results_rho{RHO:.2f}.pkl', 'wb') as f:
        pickle.dump(save_result, f)
    
    if estimator.dnn_model_full is not None:
        save_path = f'afdm_sp_blind_dnn_rho{RHO:.2f}.pt'
        import torch
        torch.save(estimator.dnn_model_full.state_dict(), save_path)

    # OPT-1: persist scalers so the model can be loaded and used without re-training
    if estimator.global_std_X is not None:
        scaler_path = f'afdm_sp_scalers_rho{RHO:.2f}.pkl'
        with open(scaler_path, 'wb') as f:
            pickle.dump({'global_std_X': estimator.global_std_X,
                         'global_std_y': estimator.global_std_y}, f)
        print(f"  - Scalers: {scaler_path}")

    # ── Phase B: Gate check for differentiable layers ──────────
    print("\n" + "=" * 60)
    print("  Verifying differentiable TF layers before E2E training")
    print("=" * 60)
    layers_ok = estimator.verify_differentiable_layers()

    # ── Phase C: End-to-end CE→LMMSE training (optional) ────────
    if layers_ok and ENABLE_E2E:
        N_E2E_SAMPLES   = 30000   # smaller than CE (E2E gen is slower)
        EPOCHS_PRETRAIN = 35      # CE warm-start inside train_e2e (SP needs more)
        EPOCHS_E2E      = 30      # total E2E fine-tuning epochs (split by phase_a_ratio)
        print("\n" + "=" * 60)
        print("  Phase C: End-to-end training (CE + LMMSE + Demapper/BCE)")
        print("=" * 60)
        e2e_model, hist_pre, (hist_A, hist_B), e2e_data = estimator.train_e2e(
            n_samples          = N_E2E_SAMPLES,
            snr_range          = (10, 25),
            epochs_pretrain    = EPOCHS_PRETRAIN,
            epochs_e2e         = EPOCHS_E2E,
            batch_size         = BATCH_SIZE,
            det_loss_weight    = 1.0,
            ce_loss_weight     = 0.1,
            sym_loss_weight_A  = 0.5,   # Phase 2-A: MSE anchor weight
            sym_loss_weight_B  = 0.05,  # Phase 2-B: nearly released
            phase_a_ratio      = 0.3,   # first 30% epochs = stabilisation
        )

        # ── Evaluate E2E ──────────────────────────────────────────
        print("\nEvaluating E2E model (SER + BER vs SNR)...")
        e2e_results = estimator.evaluate_e2e(n_test=min(N_TEST_SAMPLES, 2000))

        # ── SIC Physics Diagnostic (pure NumPy — no Keras) ────────
        print("\n" + "=" * 64)
        print("  Running SIC Physics Diagnostic...")
        print("=" * 64)
        sic_diag = estimator.diagnose_sic_physics(n_trials=30, snr_db=20.0)

        # ── Plot E2E results ──────────────────────────────────────
        fig, axes = plt.subplots(1, 3, figsize=(20, 5))
        offset = 0
        for h, label in [(hist_pre, 'CE pre-train'),
                         (hist_A,   'E2E Phase-A (anchor)'),
                         (hist_B,   'E2E Phase-B (BCE sprint)')]:
            hd = h if isinstance(h, dict) else h.history
            ep = range(offset, offset + len(hd.get('loss', [])))
            axes[0].semilogy(ep, hd.get('loss', []), label=f'{label} train')
            axes[0].semilogy(ep, hd.get('val_loss', []), '--', label=f'{label} val')
            offset += len(hd.get('loss', []))
        axes[0].set_xlabel('Epoch'); axes[0].set_ylabel('Loss')
        axes[0].set_title('E2E SP Training History')
        axes[0].legend(fontsize=7); axes[0].grid(True, alpha=0.3)
        snrs = sorted(e2e_results.keys())
        for key, lbl, mk in [('ser_ls','LS(Alg5.2.2)+LMMSE','o'),
                              ('ser_ls2d','LS(home_row)+LMMSE','p'),
                              ('ser_mmse','MMSE+LMMSE','s'),
                              ('ser_cednn','DNN-CE+LMMSE','^'),
                              ('ser_e2e','E2E-DNN','D')]:
            axes[1].semilogy(snrs,
                             [np.mean(e2e_results[s][key]) for s in snrs],
                             f'{mk}-', label=lbl, linewidth=2, markersize=7)
        axes[1].set_xlabel('SNR (dB)'); axes[1].set_ylabel('SER')
        axes[1].set_title('SP Symbol Error Rate Comparison')
        axes[1].legend(); axes[1].grid(True, alpha=0.3)
        for key, lbl, mk in [('ber_ls','LS(Alg5.2.2)+LMMSE','o'),
                              ('ber_ls2d','LS(home_row)+LMMSE','p'),
                              ('ber_mmse','MMSE+LMMSE','s'),
                              ('ber_cednn','DNN-CE+LMMSE','^'),
                              ('ber_e2e','E2E-DNN (BCE)','D')]:
            axes[2].semilogy(snrs,
                             [np.mean(e2e_results[s][key]) for s in snrs],
                             f'{mk}-', label=lbl, linewidth=2, markersize=7)
        axes[2].set_xlabel('SNR (dB)'); axes[2].set_ylabel('BER')
        axes[2].set_title('SP Bit Error Rate Comparison')
        axes[2].legend(); axes[2].grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'afdm_sp_e2e_rho{RHO:.2f}.png', dpi=300, bbox_inches='tight')
        torch.save(e2e_model.state_dict(), f'afdm_sp_e2e_lmmse_rho{RHO:.2f}.pt')
        with open(f'afdm_sp_e2e_results_rho{RHO:.2f}.pkl', 'wb') as f:
            pickle.dump(e2e_results, f)
        print(f"\nE2E artefacts saved:")
        print(f"  - afdm_sp_e2e_lmmse_rho{RHO:.2f}.pt")
        print(f"  - afdm_sp_e2e_results_rho{RHO:.2f}.pkl")
        print(f"  - afdm_sp_e2e_rho{RHO:.2f}.png")

    # ── Phase D: 2-Stage Deep Unfolding ───────────────────────────
    if layers_ok and ENABLE_UNFOLDING:
        N_E2E_UNF      = 20000
        EPOCHS_PRE_UNF = 50
        EPOCHS_E2E_UNF = 30
        print("\n" + "=" * 60)
        print("  Phase D: 2-Stage Deep Unfolding training (SP ZC)")
        print("=" * 60)
        unf_model, _hist_pre_u, (_hist_Au, _hist_Bu), _ = \
            estimator.train_e2e_unfolding(
                n_samples       = N_E2E_UNF,
                snr_range       = (10, 25),
                epochs_pretrain = EPOCHS_PRE_UNF,
                epochs_e2e      = EPOCHS_E2E_UNF,
                batch_size      = BATCH_SIZE,
                sic_mode        = 'qpsk_proj',
            )
        print("\nEvaluating Deep Unfolding model (Stage-1 + Stage-2 BER vs SNR)...")
        unf_results = estimator.evaluate_e2e_unfolding(
            n_test=min(N_TEST_SAMPLES, 2000))
        torch.save(unf_model.state_dict(), f'afdm_sp_unfolding_rho{RHO:.2f}.pt')
        with open(f'afdm_sp_unfolding_results_rho{RHO:.2f}.pkl', 'wb') as f:
            pickle.dump(unf_results, f)

        # ── BER plot: traditional + unfolding baselines ─────────────
        snrs_u = sorted(unf_results.keys())
        fig_u, ax_u = plt.subplots(figsize=(9, 6))
        curves = [
            ('ber_ls',     'LS+LMMSE',             'o',  '#1f77b4'),
            ('ber_mmse',   'MMSE+LMMSE',            's',  '#ff7f0e'),
            ('ber_omp',    'OMP+LMMSE',             'v',  '#9467bd'),
            ('ber_joint',  'Joint OMP+MP (5-iter)', '*',  '#8c564b'),
            ('ber_cednn',  'DNN-CE+LMMSE',          '^',  '#2ca02c'),
            ('ber_unf_s1', 'Deep Unfolding S1',     'D',  '#d62728'),
            ('ber_unf_s2', 'Deep Unfolding S2',     'P',  '#e377c2'),
        ]
        for key, lbl, mk, col in curves:
            ber_vals = [np.mean(unf_results[s][key]) for s in snrs_u]
            ax_u.semilogy(snrs_u, ber_vals, f'{mk}-',
                         label=lbl, linewidth=2, markersize=7, color=col)
        ax_u.set_xlabel('SNR (dB)', fontsize=12)
        ax_u.set_ylabel('BER', fontsize=12)
        ax_u.set_title(f'AFDM SP BER Comparison (ρ={RHO:.2f}, ZC pilot)', fontsize=13)
        ax_u.legend(fontsize=9, loc='lower left')
        ax_u.grid(True, alpha=0.3, which='both')
        plt.tight_layout()
        ber_fig_path = f'afdm_sp_ber_comparison_rho{RHO:.2f}.png'
        plt.savefig(ber_fig_path, dpi=300, bbox_inches='tight')
        print(f"\nUnfolding artefacts saved:")
        print(f"  - afdm_sp_unfolding_rho{RHO:.2f}.pt")
        print(f"  - afdm_sp_unfolding_results_rho{RHO:.2f}.pkl")
        print(f"  - {ber_fig_path}")
    elif not layers_ok:
        print("\n  WARNING: layer verification failed — skipping E2E/Unfolding training.")
        print("  Check the error messages above and fix before proceeding.")

    # Summary
    print("\n" + "=" * 60)
    print("  AFDM SP Blind Estimation Performance Summary")
    print("=" * 60)
    test_results = result['test_results']
    
    print(f"\nSNR (dB) | NMSE_LS      | NMSE_MMSE    | NMSE_OMP     | NMSE_DNN")
    print("-" * 70)
    for i, snr in enumerate(test_results['snr_values']):
        omp_val = test_results.get('nmse_omp', [float('nan')] * len(test_results['snr_values']))[i]
        print(f"  {snr:5.0f}  | {test_results['nmse_ls'][i]:.4e} | "
              f"{test_results['nmse_mmse'][i]:.4e} | "
              f"{omp_val:.4e} | "
              f"{test_results['nmse_dnn'][i]:.4e}")
    
    if 20 in test_results['snr_values']:
        idx = test_results['snr_values'].index(20)
        ls_nmse = test_results['nmse_ls'][idx]
        dnn_nmse = test_results['nmse_dnn'][idx]
        improvement_db = 10 * np.log10(ls_nmse / dnn_nmse) if dnn_nmse > 0 else float('inf')
        print(f"\nAt 20dB SNR:")
        print(f"  Blind DNN improvement over LS: {improvement_db:.2f} dB")
    
    print(f"\nResults saved to:")
    print(f"  - Results: afdm_sp_blind_results_rho{RHO:.2f}.pkl")
    print(f"  - Model:   afdm_sp_blind_dnn_rho{RHO:.2f}.pt")


if __name__ == "__main__":
    main()