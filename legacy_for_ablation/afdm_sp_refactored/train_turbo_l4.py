"""
train_turbo_l4.py — NVIDIA L4 专用 Turbo 训练脚本
=====================================================
在 L4 (22 GB VRAM) 上相比原 train_n512.py --turbo-only：
  · batch_size: 32 → 128
  · DataLoader: num_workers=8, pin_memory=True, persistent_workers=True
  · val_loader: batch_size=64
  · Phase A epochs: 30, lr: 5e-4   (Refiner 10×lr param group)
  · Phase B epochs: 20, lr: 5e-5   (CE 0.1×lr 保护)
  · 估计总时间: ~1.1 h (vs 原始 ~3.3 h)

用法（在服务器上）:
    cd /root/path   (包含 afdm_sp_refactored/ 目录的父目录)
    python -m afdm_sp_refactored.train_turbo_l4

前提:
    outputs_n512/ 中已有 dnn_ce_model.pt + oamp_e2e_model.pt + global_stats.pkl
    (先跑过 main() 和 --oamp-only)
"""
import math, os, sys, warnings, time, pathlib, pickle, shutil
warnings.filterwarnings('ignore')
os.environ.setdefault('PYTORCH_CUDA_ALLOC_CONF', 'max_split_size_mb:512,expandable_segments:True')

print("[init] importing numpy...",      flush=True)
import numpy as np
print("[init] importing matplotlib...", flush=True)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
print("[init] importing torch...",      flush=True)
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader, Subset
print(f"[init] torch {torch.__version__}  cuda={torch.cuda.is_available()}", flush=True)

_HERE   = pathlib.Path(__file__).parent
_PARENT = _HERE.parent
sys.path.insert(0, str(_PARENT))

print("[init] project modules...", flush=True)
from afdm_sp_refactored.run_sp_unfolding import AFDMSystem
from afdm_sp_refactored.afdm_trainer     import compute_turbo_loss
print("[init] all imports done ✓", flush=True)

# ══════════════════════════════════════════════════════════════════════
#  配置区
# ══════════════════════════════════════════════════════════════════════
SAVE_DIR         = os.environ.get(
    'AFDM_TURBO_SAVE_DIR',
    '/home/18736049201eric/afdm_sp_refactored/outputs_n512')
DETECTOR_TYPE    = os.environ.get('AFDM_TURBO_DETECTOR', 'oamp').strip().lower()
if DETECTOR_TYPE not in {'oamp', 'ep'}:
    raise ValueError(f"Unsupported AFDM_TURBO_DETECTOR={DETECTOR_TYPE!r}")
DETECTOR_LABEL   = 'OAMP' if DETECTOR_TYPE == 'oamp' else 'EP'
DETECTOR_CKPT_NAME = f'{DETECTOR_TYPE}_e2e_model.pt'
TURBO_CKPT_NAME = (
    'turbo_receiver_model.pt'
    if DETECTOR_TYPE == 'oamp'
    else f'turbo_receiver_{DETECTOR_TYPE}.pt')
TURBO_CURVE_NAME = (
    'turbo_training_curves_l4.png'
    if DETECTOR_TYPE == 'oamp'
    else f'turbo_training_curves_l4_{DETECTOR_TYPE}.png')
TURBO_BER_NAME = (
    'turbo_ber_l4.png'
    if DETECTOR_TYPE == 'oamp'
    else f'turbo_ber_l4_{DETECTOR_TYPE}.png')
SEED             = 42
N_TRAIN_SAMPLES  = 20000
SNR_TRAIN_RANGE  = (0, 25)
SNR_EVAL_LIST    = [5, 10, 15, 20, 25]
N_TEST_FRAMES    = 200        # L4 快，多测几帧

# ── L4 专属超参 ────────────────────────────────────────────────────
BATCH_TRAIN      = int(os.environ.get('AFDM_TURBO_BATCH', '64'))
BATCH_VAL        = int(os.environ.get('AFDM_TURBO_VAL_BATCH', '32'))
NUM_WORKERS      = int(os.environ.get('AFDM_TURBO_NUM_WORKERS', '4'))
EPOCHS_PHASE_A   = 30
EPOCHS_PHASE_B   = 20
LR_A             = 5e-4
LR_B             = 5e-5
PATIENCE         = 10         # 比 3080Ti 版稍宽松，因为每 epoch 更快
MIN_LR           = 1e-7
NUM_OUTER_ITERS  = 3
NUM_OAMP_LAYERS  = 4
DATASET_CACHE    = os.environ.get(
    'AFDM_TURBO_DATASET_CACHE',
    str(pathlib.Path(SAVE_DIR) / 'turbo_train_dataset.pkl'))
RESUME_CHECKPOINT = os.environ.get(
    'AFDM_TURBO_RESUME_CKPT',
    str(pathlib.Path(SAVE_DIR) / (
        'turbo_resume_checkpoint.pt'
        if DETECTOR_TYPE == 'oamp'
        else f'turbo_resume_checkpoint_{DETECTOR_TYPE}.pt')))
RESUME_KEEP = int(os.environ.get('AFDM_TURBO_RESUME_KEEP', '2'))
VAL_EVERY_PHASE_A = max(1, int(os.environ.get('AFDM_TURBO_VAL_EVERY_PHASE_A', '2')))
VAL_EVERY_PHASE_B = max(1, int(os.environ.get('AFDM_TURBO_VAL_EVERY_PHASE_B', '1')))
VAL_SUBSET_SIZE = max(0, int(os.environ.get('AFDM_TURBO_VAL_SUBSET_SIZE', '1024')))
RUN_FINAL_EVAL = os.environ.get('AFDM_TURBO_RUN_FINAL_EVAL', '0').lower() not in {'0', 'false', 'no'}
ENABLE_TF32 = os.environ.get('AFDM_TURBO_ENABLE_TF32', '1').lower() not in {'0', 'false', 'no'}


# ══════════════════════════════════════════════════════════════════════
#  辅助函数
# ══════════════════════════════════════════════════════════════════════
def _gpu_info():
    if not torch.cuda.is_available():
        print("  [WARNING] CUDA 不可用，使用 CPU 训练（很慢）")
        return
    if hasattr(torch.backends.cuda, 'preferred_linalg_library'):
        try:
            torch.backends.cuda.preferred_linalg_library('cusolver')
            print("  CUDA linalg backend → cuSOLVER")
        except Exception as exc:
            print(f"  [WARNING] 无法切到 cuSOLVER: {exc}")
    for i in range(torch.cuda.device_count()):
        p  = torch.cuda.get_device_properties(i)
        mb = p.total_memory // (1024 ** 2)
        print(f"  [GPU {i}] {p.name}  {mb/1024:.1f} GB VRAM  "
              f"CUDA {torch.version.cuda}  cuDNN {torch.backends.cudnn.version()}")
    # 简单 warm-up
    _ = torch.zeros(1, device='cuda')
    print("  CUDA warm-up OK  → 训练将使用 GPU (cuda:0)")


def _configure_runtime():
    if not torch.cuda.is_available():
        return
    if ENABLE_TF32:
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        if hasattr(torch, 'set_float32_matmul_precision'):
            torch.set_float32_matmul_precision('high')
    else:
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        if hasattr(torch, 'set_float32_matmul_precision'):
            torch.set_float32_matmul_precision('highest')


def _make_system(rho=0.5):
    # Keep the exact N=512 geometry from train_n512.py. The raw AFDMSystem
    # constructor alone would leave l_max_cap at the backward-compat default,
    # shrinking the grid to (16,13,2) and breaking checkpoint compatibility.
    sys_obj = AFDMSystem(N=16, M=32, rho=rho)
    new_lmax = int(math.ceil(50 * 512 * sys_obj.delta_f / sys_obj.fs / 5.0)) * 5
    new_lmax = max(new_lmax, 15)
    sys_obj.l_max_cap      = new_lmax
    sys_obj.k_max_cap      = 2
    K_factor               = 2 * sys_obj.k_max_cap + 1
    sys_obj.delta_max      = sys_obj.k_max_cap + K_factor * sys_obj.l_max_cap
    sys_obj.max_delay_supported_s = sys_obj.l_max_cap * sys_obj.delay_resolution
    sys_obj.max_delay_idx_bar_supported = (
        int(np.floor(sys_obj.max_delay_supported_s / sys_obj.Ts)) + 1)
    sys_obj.P_paths              = 5
    sys_obj.use_frac_doppler     = True
    sys_obj.k_leak               = 2
    sys_obj.frac_prune_rel_thres = 0.01
    return sys_obj


def _empty_hist():
    return {'loss': [], 'val_loss': [], 'val_ber': [], 'val_epoch': []}


def _history_x(hist, key):
    xs = hist.get('val_epoch')
    ys = hist.get(key, [])
    if key == 'loss':
        return list(range(1, len(hist.get('loss', [])) + 1))
    if xs is None or len(xs) != len(ys):
        return list(range(1, len(ys) + 1))
    return xs


def _save_resume_checkpoint(path, payload):
    if path is None:
        return
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    keep = max(0, RESUME_KEEP)
    if keep > 0 and path.exists():
        oldest = path.with_name(f"{path.stem}.bak{keep}{path.suffix}")
        if oldest.exists():
            oldest.unlink()
        for idx in range(keep - 1, 0, -1):
            src = path.with_name(f"{path.stem}.bak{idx}{path.suffix}")
            dst = path.with_name(f"{path.stem}.bak{idx+1}{path.suffix}")
            if src.exists():
                shutil.move(str(src), str(dst))
        shutil.move(str(path), str(path.with_name(f"{path.stem}.bak1{path.suffix}")))
    torch.save(payload, str(path))


# ══════════════════════════════════════════════════════════════════════
#  L4 专属 _pt_fit_turbo Monkey-Patch
#  —— 替换 DataLoader 为大 batch + 多 worker 版本
# ══════════════════════════════════════════════════════════════════════
def _pt_fit_turbo_l4(self, model, e2e_data, tr_idx, va_idx,
                     epochs, batch_size, lr, patience, min_lr,
                     loss_kw=None):
    """L4 增强版 _pt_fit_turbo：大 batch + 多 worker DataLoader。"""
    _turbo_loss_fn = compute_turbo_loss
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
    val_subset_size = int(getattr(self, '_turbo_val_subset_size', 0) or 0)
    if 0 < val_subset_size < len(va_ds):
        va_ds = Subset(va_ds, list(range(val_subset_size)))

    # ── L4 DataLoader ─────────────────────────────────────────────
    tr_loader_kw = dict(
        batch_size  = batch_size,
        shuffle     = True,
        num_workers = NUM_WORKERS,
        pin_memory  = True,
        drop_last   = True,
    )
    va_loader_kw = dict(
        batch_size  = BATCH_VAL,
        shuffle     = False,
        num_workers = NUM_WORKERS,
        pin_memory  = True,
    )
    if NUM_WORKERS > 0:
        tr_loader_kw.update(persistent_workers=True, prefetch_factor=4)
        va_loader_kw.update(persistent_workers=True, prefetch_factor=2)
    tr_loader = DataLoader(tr_ds, **tr_loader_kw)
    va_loader = DataLoader(va_ds, **va_loader_kw)

    # ── Param groups（和 afdm_trainer.py 保持一致）──────────────
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
        param_groups = [{'params': list(model.parameters()), 'lr': lr}]

    trainable = [p for pg in param_groups for p in pg['params']]
    opt       = torch.optim.Adam(param_groups, eps=1e-7)
    sched     = torch.optim.lr_scheduler.ReduceLROnPlateau(
        opt, mode='min', factor=0.5, patience=max(2, patience // 2),
        min_lr=min_lr)
    scaler    = torch.amp.GradScaler(device='cuda',
                                     enabled=device.type == 'cuda')

    phase_name   = getattr(self, '_turbo_phase_name', 'phase')
    if phase_name == 'phase_a':
        val_every = VAL_EVERY_PHASE_A
    elif phase_name == 'phase_b':
        val_every = VAL_EVERY_PHASE_B
    else:
        val_every = max(1, int(getattr(self, '_turbo_val_every', 1)))
    resume_path  = getattr(self, '_turbo_resume_path', None)
    resume_state = getattr(self, '_turbo_resume_state', None)
    phase_hists  = getattr(self, '_turbo_phase_hists', {})

    start_ep = 0
    best_val = float('inf')
    best_sd  = {k: v.detach().cpu().clone()
                for k, v in model.state_dict().items()}
    pat_cnt  = 0
    hist     = _empty_hist()

    if (resume_state is not None and
            resume_state.get('phase') == phase_name and
            int(resume_state.get('epoch', 0)) < epochs):
        model.load_state_dict(resume_state['model_state'])
        opt.load_state_dict(resume_state['optimizer_state'])
        sched.load_state_dict(resume_state['scheduler_state'])
        scaler_state = resume_state.get('scaler_state')
        if scaler_state:
            scaler.load_state_dict(scaler_state)
        start_ep = int(resume_state.get('epoch', 0))
        best_val = float(resume_state.get('best_val', best_val))
        best_sd  = resume_state.get('best_sd', best_sd)
        pat_cnt  = int(resume_state.get('pat_cnt', 0))
        hist     = resume_state.get('hist', hist)
        hist.setdefault('val_epoch', [])
        print(f"  Resume {phase_name}: epoch {start_ep + 1}/{epochs}", flush=True)

    if start_ep >= epochs:
        model.load_state_dict(best_sd)
        return hist

    for ep in range(start_ep, epochs):
        t0 = time.time()
        model.train()
        ep_loss = 0.0

        for batch in tr_loader:
            Xf, Yr, Xp, Sw, Xd, Bt, YCE = [b.to(device) for b in batch]
            with torch.amp.autocast('cuda', enabled=device.type == 'cuda'):
                out  = model(Xf, Yr, Xp, Sw)
                loss = _turbo_loss_fn(out, Bt, Xd, YCE, Yr, Xp, **loss_kw)
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(trainable, max_norm=1.0)
            scaler.step(opt); scaler.update(); opt.zero_grad()
            ep_loss += loss.item()

        ep_loss /= max(len(tr_loader), 1)
        hist['loss'].append(ep_loss)

        do_val = ((ep + 1) % val_every == 0) or (ep + 1 == epochs)
        val_loss = None
        val_ber = None
        if do_val:
            model.eval()
            val_loss = 0.0
            bc = 0
            bt = 0
            with torch.no_grad():
                for batch in va_loader:
                    Xf, Yr, Xp, Sw, Xd, Bt, YCE = [b.to(device) for b in batch]
                    with torch.amp.autocast('cuda', enabled=device.type == 'cuda'):
                        out   = model(Xf, Yr, Xp, Sw)
                        vloss = _turbo_loss_fn(out, Bt, Xd, YCE, Yr, Xp, **loss_kw)
                    val_loss += vloss.item()
                    pred = (out['final_bits'] > 0).float()
                    bc += (pred == Bt).sum().item()
                    bt += Bt.numel()

            val_loss /= max(len(va_loader), 1)
            val_ber = 1.0 - bc / max(bt, 1)
            sched.step(val_loss)
            hist['val_loss'].append(val_loss)
            hist['val_ber'].append(val_ber)
            hist['val_epoch'].append(ep + 1)

        elapsed = time.time() - t0
        eta_s   = int(elapsed * (epochs - ep - 1))
        lrs_str = '/'.join(f"{g['lr']:.1e}" for g in opt.param_groups)
        alpha_str = ''
        gate_str = ''
        if hasattr(model, 'refine_scales'):
            alphas = [f"{s.item():.3f}" for s in model.refine_scales]
            alpha_str = f"  α=[{','.join(alphas)}]"
        if isinstance(out, dict) and 'history_gate' in out:
            gates = [f"{g.mean().item():.3f}" for g in out['history_gate']]
            gate_str = f"  g=[{','.join(gates)}]"
        if do_val:
            val_msg = f"val={val_loss:.3e}  val_ber={val_ber:.4f}"
        elif hist['val_loss']:
            val_msg = (f"val=skip(last={hist['val_loss'][-1]:.3e})  "
                       f"val_ber=skip(last={hist['val_ber'][-1]:.4f})")
        else:
            val_msg = "val=skip  val_ber=skip"
        print(f"  Turbo [{ep+1:3d}/{epochs}]  "
              f"loss={ep_loss:.3e}  {val_msg}  "
              f"lr={lrs_str}{alpha_str}{gate_str}  "
              f"{elapsed:.0f}s/ep  ETA {eta_s//60}m{eta_s%60:02d}s",
              flush=True)

        stop_now = False
        if do_val:
            if val_loss < best_val - 1e-4:
                best_val = val_loss
                pat_cnt = 0
                best_sd  = {k: v.detach().cpu().clone()
                            for k, v in model.state_dict().items()}
            else:
                pat_cnt += 1
                if pat_cnt >= patience:
                    print(f"\n  Early stop at epoch {ep+1}")
                    stop_now = True

        phase_hists[phase_name] = hist
        _save_resume_checkpoint(resume_path, {
            'phase': phase_name,
            'epoch': ep + 1,
            'model_state': model.state_dict(),
            'optimizer_state': opt.state_dict(),
            'scheduler_state': sched.state_dict(),
            'scaler_state': scaler.state_dict() if device.type == 'cuda' else None,
            'best_val': best_val,
            'best_sd': best_sd,
            'pat_cnt': pat_cnt,
            'hist': hist,
            'phase_hists': phase_hists,
        })
        if stop_now:
            break
    else:
        print()

    phase_hists[phase_name] = hist
    model.load_state_dict(best_sd)
    return hist


def _run_final_eval(sys_obj, save_dir, turbo_model, detector_ckpt, detector_type):
    print("\n" + "─" * 60)
    print(f"  BER 评估: Turbo vs {detector_type.upper()} vs LMMSE")
    print("─" * 60)

    device = sys_obj._pt_device()
    turbo_model.eval()
    turbo_model = turbo_model.to(device)

    K_factor, k_max, L_max, W, pad_size = sys_obj._get_2d_grid_params()
    input_dim = L_max * W * 2 + 4
    data_pos  = sys_obj.generate_pilot_frame()[4]

    det_model_ref = None
    if detector_ckpt.exists():
        ce_bb2 = sys_obj.build_dnn_model_full(input_dim)
        if detector_type == 'ep':
            det_model_ref, _ = sys_obj.build_e2e_ep_model(
                input_dim, data_pos, ce_backbone=ce_bb2,
                num_ep_layers=NUM_OAMP_LAYERS)
        else:
            det_model_ref, _ = sys_obj.build_e2e_oamp_model(
                input_dim, data_pos, ce_backbone=ce_bb2,
                num_oamp_layers=NUM_OAMP_LAYERS)
        det_model_ref.load_state_dict(
            torch.load(str(detector_ckpt), map_location='cpu'))
        det_model_ref.eval()
        det_model_ref = det_model_ref.to(device)

    e2e_ckpt = save_dir / 'e2e_model.pt'
    lmmse_model_ref = None
    if e2e_ckpt.exists():
        ce_bb3 = sys_obj.build_dnn_model_full(input_dim)
        lmmse_model_ref, _ = sys_obj.build_e2e_model(
            input_dim, data_pos, ce_backbone=ce_bb3)
        lmmse_model_ref.load_state_dict(
            torch.load(str(e2e_ckpt), map_location='cpu'))
        lmmse_model_ref.eval()
        lmmse_model_ref = lmmse_model_ref.to(device)

    def _eval_model(model_ref, snr_db, n_frames, out_key):
        if model_ref is None:
            return None
        batch = sys_obj.generate_e2e_training_dataset(
            n_samples=n_frames, snr_range=(snr_db, snr_db))
        with torch.no_grad():
            Xf = torch.from_numpy(batch['X_features']).float().to(device)
            Yr = torch.from_numpy(batch['y_received']).float().to(device)
            Xp = torch.from_numpy(batch['x_pilot_frames']).float().to(device)
            Sw = torch.from_numpy(batch['sigma_w2']).float().to(device)
            out = model_ref(Xf, Yr, Xp, Sw)
        pred = (out[out_key] > 0).float().cpu().numpy()
        return float(np.mean(pred != batch['bits_true']))

    det_label = detector_type.upper()
    print(f"\n  {'SNR':>6}  {'Turbo BER':>12}  {det_label + ' BER':>12}  {'LMMSE BER':>12}")
    print(f"  {'(dB)':>6}  {'----------':>12}  {'--------':>12}  {'---------':>12}")
    ber_turbo = []
    ber_det = []
    for snr in SNR_EVAL_LIST:
        bt = _eval_model(turbo_model, snr, N_TEST_FRAMES, 'final_bits')
        bd = _eval_model(det_model_ref, snr, N_TEST_FRAMES, 'bits')
        bl = _eval_model(lmmse_model_ref, snr, N_TEST_FRAMES, 'bits')
        ber_turbo.append(bt)
        ber_det.append(bd)
        bo_str = f"{bd:.4f}" if bd is not None else "  N/A  "
        bl_str = f"{bl:.4f}" if bl is not None else "  N/A  "
        print(f"  {snr:>6}  {bt:>12.4f}  {bo_str:>12}  {bl_str:>12}", flush=True)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.semilogy(SNR_EVAL_LIST, ber_turbo, 'r-o', label='JointTurbo (Ours)')
    if any(b is not None for b in ber_det):
        ax.semilogy(
            SNR_EVAL_LIST,
            [b if b is not None else float('nan') for b in ber_det],
            'b--s',
            label=f'{det_label}-Net',
        )
    ax.set_xlabel('SNR (dB)')
    ax.set_ylabel('BER')
    ax.set_title('AFDM N=512 — Turbo vs OAMP  (L4 run)')
    ax.legend()
    ax.grid(True, which='both', ls=':')
    ber_path = save_dir / TURBO_BER_NAME
    fig.savefig(str(ber_path), dpi=150)
    plt.close(fig)
    print(f"\n  BER plot → {ber_path}")


# ══════════════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════════════
def main():
    save_dir = pathlib.Path(SAVE_DIR)
    save_dir.mkdir(parents=True, exist_ok=True)

    np.random.seed(SEED)
    torch.manual_seed(SEED)
    _configure_runtime()

    sys_obj = _make_system(rho=0.5)
    _gpu_info()
    print(f"  detector      → {DETECTOR_TYPE}")
    print(f"  TF32 enabled → {ENABLE_TF32}")
    print(f"  val_every     → phase_a={VAL_EVERY_PHASE_A}, phase_b={VAL_EVERY_PHASE_B}")
    print(f"  val_subset    → {VAL_SUBSET_SIZE if VAL_SUBSET_SIZE > 0 else 'full val set'}")
    print(f"  final eval    → {'run' if RUN_FINAL_EVAL else 'skip'}")

    # ── 载入统计量 ──────────────────────────────────────────────
    stats_path = save_dir / 'global_stats.pkl'
    if not stats_path.exists():
        raise FileNotFoundError(
            f"找不到 {stats_path}\n"
            "请先在同一 save_dir 下跑过 main() 生成 global_stats.pkl。")
    with open(stats_path, 'rb') as f:
        stats = pickle.load(f)
    sys_obj.global_std_X = stats['std_X']
    sys_obj.global_std_y = stats['std_y']
    print(f"  global_std_X={sys_obj.global_std_X:.6f}  "
          f"global_std_y={sys_obj.global_std_y:.6f}")

    # ── 载入 checkpoints ────────────────────────────────────────
    ckpt_ce = save_dir / 'dnn_ce_model.pt'
    if not ckpt_ce.exists():
        raise FileNotFoundError(f"找不到 {ckpt_ce}，请先运行 main()。")
    ce_state = torch.load(str(ckpt_ce), map_location='cpu')
    print(f"  CE backbone  ← {ckpt_ce}")

    detector_ckpt  = save_dir / DETECTOR_CKPT_NAME
    detector_state = None
    if detector_ckpt.exists():
        detector_state = torch.load(str(detector_ckpt), map_location='cpu')
        print(f"  {DETECTOR_LABEL}-Net     ← {detector_ckpt}")
    else:
        print(f"  {DETECTOR_LABEL}-Net     : 不存在，随机初始化")

    # ── Monkey-patch DataLoader 为 L4 版本 ──────────────────────
    import types
    sys_obj._pt_fit_turbo = types.MethodType(_pt_fit_turbo_l4, sys_obj)
    sys_obj._turbo_val_every = VAL_EVERY_PHASE_A
    sys_obj._turbo_val_subset_size = VAL_SUBSET_SIZE
    print("  _pt_fit_turbo → L4 patched "
          f"(batch={BATCH_TRAIN}, workers={NUM_WORKERS}) ✓")
    print(f"  resume checkpoint → {RESUME_CHECKPOINT}")
    print(f"  dataset cache     → {DATASET_CACHE}")

    # ── 两阶段训练 ───────────────────────────────────────────────
    print(f"\n  Phase A: {EPOCHS_PHASE_A} ep, lr={LR_A:.0e}, batch={BATCH_TRAIN}")
    print(f"  Phase B: {EPOCHS_PHASE_B} ep, lr={LR_B:.0e}")

    turbo_model, hist_a, hist_b = sys_obj.train_turbo_joint(
        pretrained_ce_state_dict   = ce_state,
        pretrained_detector_state_dict = detector_state,
        n_samples       = N_TRAIN_SAMPLES,
        snr_range       = SNR_TRAIN_RANGE,
        dataset_cache_path = DATASET_CACHE,
        resume_checkpoint_path = RESUME_CHECKPOINT,
        epochs_phase_a  = EPOCHS_PHASE_A,
        epochs_phase_b  = EPOCHS_PHASE_B,
        batch_size      = BATCH_TRAIN,
        lr_a            = LR_A,
        lr_b            = LR_B,
        patience        = PATIENCE,
        min_lr          = MIN_LR,
        num_outer_iters = NUM_OUTER_ITERS,
        num_oamp_layers = NUM_OAMP_LAYERS,
        detector_type   = DETECTOR_TYPE,
    )

    # ── 保存 ────────────────────────────────────────────────────
    ckpt_out = save_dir / TURBO_CKPT_NAME
    torch.save(turbo_model.state_dict(), str(ckpt_out))
    print(f"\n  Turbo checkpoint → {ckpt_out}")

    # ── 训练曲线 ─────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 3, figsize=(18, 4))
    axes[0].plot(_history_x(hist_a, 'loss'), hist_a['loss'], label='train')
    axes[0].plot(_history_x(hist_a, 'val_loss'), hist_a['val_loss'], label='val')
    axes[0].set_title('Phase A: CE-frozen Loss')
    axes[0].set_xlabel('Epoch'); axes[0].legend(); axes[0].set_yscale('log')

    axes[1].plot(_history_x(hist_b, 'loss'), hist_b['loss'], label='train')
    axes[1].plot(_history_x(hist_b, 'val_loss'), hist_b['val_loss'], label='val')
    axes[1].set_title('Phase B: Joint Fine-tune Loss')
    axes[1].set_xlabel('Epoch'); axes[1].legend(); axes[1].set_yscale('log')

    axes[2].plot(_history_x(hist_a, 'val_ber'), hist_a['val_ber'],
                 label='Phase A', color='#e5c07b')
    axes[2].plot(_history_x(hist_b, 'val_ber'), hist_b['val_ber'],
                 label='Phase B', color='#98c379')
    axes[2].set_title('Val BER'); axes[2].set_xlabel('Epoch'); axes[2].legend()
    plt.tight_layout()
    curve_path = save_dir / TURBO_CURVE_NAME
    fig.savefig(str(curve_path), dpi=150); plt.close(fig)
    print(f"  Curves → {curve_path}")

    if RUN_FINAL_EVAL:
        _run_final_eval(
            sys_obj, save_dir, turbo_model, detector_ckpt, DETECTOR_TYPE)
    else:
        print("\n  Final eval skipped (AFDM_TURBO_RUN_FINAL_EVAL=0)")
        print("  如需单独评测，运行: python -m afdm_sp_refactored.verify_turbo")
    print("\n  Done ✓")


if __name__ == '__main__':
    main()
