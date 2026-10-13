"""
train_n512.py — 完整 N=512 AFDM SP 训练与评估脚本

系统参数:
    N=512 (16×32), fc=12 kHz, B=4 kHz, fs=8 kHz, rho=0.5
    l_max_cap=50, k_max_cap=2, K_factor=5
    Grid: (51, 13, 2), CNN input_dim=1330

训练流程:
    Phase 1: CNN-CE 预训练 (MSE loss, n_samples 样本)
    Phase 2-A: E2E 稳定期 (BCE + MSE 混合, 较低 LR)
    Phase 2-B: BER 冲刺期 (BCE 主导, 最低 LR)

评估 (BER + NMSE vs SNR, 公平对比):
    1. Joint OMP+BP     — 传统迭代接收机基线 (OMP + n_outer 次外迭代)
    2. DNN-CE + LMMSE   — 预训练 CNN 信道估计 + NumPy LMMSE 均衡
    3. E2E-DNN + LMMSE  — 端对端训练全流程 (TF 前向)

用法:
    cd OTFS-channel-estimation
    /opt/anaconda3/envs/CE/bin/python -m afdm_sp_joint_unrolled.train_n512

调参建议:
    N_TRAIN_SAMPLES : 数据量  (默认 20000, 用 5000 测试流程)
    EPOCHS_PRETRAIN : CE 预训练轮次 (默认 50)
    EPOCHS_E2E      : E2E 微调总轮次 (默认 30)
    N_TEST_FRAMES   : 每SNR测试帧数 (默认 100; 越大越准)
    SAVE_DIR        : checkpoint / 曲线保存目录
"""
import math, os, sys, warnings, time, pathlib
warnings.filterwarnings('ignore')
# Prevent fragmented CUDA allocations (especially important on 6–8 GB GPUs)
os.environ.setdefault('PYTORCH_CUDA_ALLOC_CONF', 'expandable_segments:True')

print("[init] importing numpy...",   flush=True)
import numpy as np
print("[init] importing matplotlib...", flush=True)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
print("[init] importing torch...  (may take 30-120 s on first Windows run)", flush=True)
import torch
print(f"[init] torch {torch.__version__}  cuda={torch.cuda.is_available()}", flush=True)
import pickle

_HERE   = pathlib.Path(__file__).parent
_PARENT = _HERE.parent
sys.path.insert(0, str(_PARENT))

print("[init] importing project modules...", flush=True)
# Each import below now runs independently (lazy __init__.py);
# prints reveal exactly which submodule hangs on this machine.
print("[init]   1/6: scipy probe...", flush=True)
from scipy.linalg import dft as _dft_probe; del _dft_probe
print("[init]   2/6: afdm_layers...", flush=True)
from afdm_sp_joint_unrolled.afdm_layers  import DiffLMMSELayer as _probe; del _probe
print("[init]   3/6: afdm_env...", flush=True)
from afdm_sp_joint_unrolled.afdm_env     import AFDMEnvMixin as _probe; del _probe
print("[init]   4/6: afdm_models...", flush=True)
from afdm_sp_joint_unrolled.afdm_models  import AFDMModelsMixin as _probe; del _probe
print("[init]   5/6: afdm_trainer...", flush=True)
from afdm_sp_joint_unrolled.afdm_trainer import AFDMTrainerMixin as _probe; del _probe
print("[init]   6/6: run_sp_unfolding + baselines...", flush=True)
from afdm_sp_joint_unrolled.run_sp_unfolding import AFDMSystem
from afdm_sp_joint_unrolled.afdm_baselines  import mp_detect_bp
print("[init] all imports done ✓", flush=True)

# ══════════════════════════════════════════════════════════════════════════════
#  配置区：修改这里调参
# ══════════════════════════════════════════════════════════════════════════════
N_TRAIN_SAMPLES  = 20000    # CE/E2E 训练样本数 (建议 ≥ 20000; 最少用 5000 测试流程)
SNR_TRAIN_RANGE  = (0, 25)  # 训练 SNR 均匀采样范围 (dB)
EPOCHS_PRETRAIN  = 50       # Phase 1 CE 预训练最大轮次 (EarlyStopping 会提前停)
EPOCHS_E2E       = 60       # Phase 2 E2E 微调总轮次 (A+B 之和); 提高到 60 让 Phase 2-A 有足够轮次
BATCH_SIZE       = 128
PHASE_A_RATIO    = 0.4      # Phase 2-A 占 E2E 总轮次比例 (0.4×60=24 ep 稳定期, 0.6×60=36 ep 冲刺)

SNR_EVAL_LIST    = [5, 10, 15, 20, 25]   # 评估 SNR 列表 (dB)
N_TEST_FRAMES    = 100      # 每个 SNR 点的测试帧数 (建议 ≥ 100 for statistical confidence)
N_OUTER_JOINT    = 5        # Joint OMP+BP 外迭代次数
NUM_ITER_BP      = 20       # BP 内迭代次数
EVAL_BATCH_SIZE  = 32       # GPU 批量推理大小 (DNN-CE + E2E, 每个 SNR 点一次调用)
                            # 显存充足时可调大至 64/128；CPU-only 时设 1 等同逐帧

SAVE_DIR         = _HERE / 'outputs_n512'   # checkpoint + 曲线输出目录
SEED             = 42

# ══════════════════════════════════════════════════════════════════════════════
#  系统初始化
# ══════════════════════════════════════════════════════════════════════════════
def make_system_n512(rho: float = 0.5) -> AFDMSystem:
    """创建 N=512 (16×32) AFDM SP 系统，设置正确的信道稀疏字典参数."""
    sys_obj = AFDMSystem(N=16, M=32, rho=rho)
    # l_max_cap in DAFT bins: ceil(50_phys_samples * N * delta_f / fs / 5) * 5
    new_lmax = int(math.ceil(50 * 512 * sys_obj.delta_f / sys_obj.fs / 5.0)) * 5
    new_lmax = max(new_lmax, 15)
    sys_obj.l_max_cap     = new_lmax        # 50
    sys_obj.k_max_cap     = 2
    K_factor              = 2 * sys_obj.k_max_cap + 1
    sys_obj.delta_max     = sys_obj.k_max_cap + K_factor * sys_obj.l_max_cap
    sys_obj.max_delay_supported_s = sys_obj.l_max_cap * sys_obj.delay_resolution
    sys_obj.max_delay_idx_bar_supported = (
        int(np.floor(sys_obj.max_delay_supported_s / sys_obj.Ts)) + 1
    )
    # UWA channel: P=5 paths, fractional Doppler
    sys_obj.P_paths             = 5
    sys_obj.use_frac_doppler    = True
    sys_obj.k_leak              = 2
    sys_obj.frac_prune_rel_thres = 0.01

    K, k, L, W, pad = sys_obj._get_2d_grid_params()
    Q = (2 * k + 1) * (sys_obj.l_max_cap + 1)
    print(f"\n  N=512 system: Grid=({L},{W},2)  l_max_cap={new_lmax}  k_max_cap={sys_obj.k_max_cap}")
    print(f"  K_factor={K}  Q={Q}  N/Q={512/Q:.2f}x  delta_max={sys_obj.delta_max}"
          f"  ({'OK' if sys_obj.delta_max<512 else 'FAIL'})")
    print(f"  input_dim = {L*W*2+4}  output_dim = {L*W*2}")
    return sys_obj


# ══════════════════════════════════════════════════════════════════════════════
#  helpers
# ══════════════════════════════════════════════════════════════════════════════
QPSK = np.array([1+1j, 1-1j, -1+1j, -1-1j], dtype=complex) / np.sqrt(2)

def ber_qpsk(x_true, x_hat):
    ei = float(np.mean((np.real(x_true) > 0) != (np.real(x_hat) > 0)))
    eq = float(np.mean((np.imag(x_true) > 0) != (np.imag(x_hat) > 0)))
    return 0.5 * (ei + eq)

def nmse_fro(H_true, H_est):
    return float(np.linalg.norm(H_true - H_est, 'fro')**2 /
                 max(np.linalg.norm(H_true, 'fro')**2, 1e-30))

def hard_qpsk(x_soft, rho):
    const = np.sqrt(1.0 - rho) * QPSK
    return np.array([const[np.argmin(np.abs(v - const))] for v in x_soft])


# ══════════════════════════════════════════════════════════════════════════════
#  启动检查：GPU 信息 + 模型前向预热
# ══════════════════════════════════════════════════════════════════════════════
def _gpu_info():
    """打印显卡信息，并做一次 CUDA 预热（触发驱动初始化，防止首个 batch 异常慢）."""
    print()
    if torch.cuda.is_available():
        n = torch.cuda.device_count()
        for i in range(n):
            p = torch.cuda.get_device_properties(i)
            used = torch.cuda.memory_allocated(i) / 1024**3
            total = p.total_memory / 1024**3
            print(f"  [GPU {i}] {p.name}  "
                  f"{total:.1f} GB VRAM  "
                  f"CUDA {torch.version.cuda}  "
                  f"cuDNN {torch.backends.cudnn.version()}")
        # 预热：强制 CUDA 上下文初始化，防止第一个 epoch 特别慢
        _w = torch.randn(512, 512, device='cuda') @ torch.randn(512, 512, device='cuda')
        torch.cuda.synchronize()
        del _w
        print(f"  CUDA warm-up OK  → 训练将使用 GPU (cuda:0)")
    else:
        print(f"  [CPU only] 未检测到 CUDA GPU，将在 CPU 上训练（速度较慢）")
        print(f"  如需 GPU 加速，请安装 CUDA 版 PyTorch:")
        print(f"    pip install torch --index-url https://download.pytorch.org/whl/cu121")


def _sanity_test(sys_obj: 'AFDMSystem'):
    """在正式训练前跑一次前向传播，确认模型结构和 GPU 均无问题."""
    import torch
    print("  [sanity] 构建模型 + 前向传播测试 ...", end='', flush=True)
    K, k, L, W, pad = sys_obj._get_2d_grid_params()
    input_dim = L * W * 2 + 4
    _, _, _, _, data_pos = sys_obj.generate_pilot_frame()
    N = sys_obj.N_total

    device = sys_obj._pt_device()
    model = sys_obj.build_dnn_model_full(input_dim).to(device)
    model.eval()
    with torch.no_grad():
        dummy = torch.randn(4, input_dim, device=device)
        out   = model(dummy)
    print(f" OK  in={tuple(dummy.shape)} → out={tuple(out.shape)}  device={device}")

    # E2E 前向
    e2e_model, _ = sys_obj.build_e2e_model(input_dim, data_pos, ce_backbone=model)
    e2e_model = e2e_model.to(device).eval()
    with torch.no_grad():
        yr  = torch.randn(4, 2 * N, device=device)
        xpr = torch.randn(4, 2 * N, device=device)
        sw  = torch.rand(4, 1, device=device) * 0.1
        res = e2e_model(dummy, yr, xpr, sw)
    det_shape = tuple(res['detection'].shape)
    print(f"  [sanity] E2E OK  detection={det_shape}")

    del model, e2e_model, dummy, out, yr, xpr, sw, res
    if device.type == 'cuda':
        torch.cuda.empty_cache()


# ══════════════════════════════════════════════════════════════════════════════
#  Phase 1 + Phase 2 训练  (复用 AFDMTrainerMixin.train_e2e)
# ══════════════════════════════════════════════════════════════════════════════
def train(sys_obj: AFDMSystem, save_dir: pathlib.Path):
    """调用系统内置 train_e2e()，返回训练好的 (e2e_model, dnn_model_full)."""
    save_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "█" * 70)
    print("  PHASE 1 + PHASE 2  TRAINING  (N=512)")
    print("█" * 70)
    e2e_model, hist_pre, (hist_A, hist_B), e2e_data = sys_obj.train_e2e(
        n_samples        = N_TRAIN_SAMPLES,
        snr_range        = SNR_TRAIN_RANGE,
        epochs_pretrain  = EPOCHS_PRETRAIN,
        epochs_e2e       = EPOCHS_E2E,
        batch_size       = BATCH_SIZE,
        phase_a_ratio    = PHASE_A_RATIO,
    )

    # ── 保存 checkpoint ──────────────────────────────────────────────────────
    torch.save(sys_obj.dnn_model_full.state_dict(),
               str(save_dir / 'dnn_ce_model.pt'))
    torch.save(e2e_model.state_dict(),
               str(save_dir / 'e2e_model.pt'))

    with open(save_dir / 'global_stats.pkl', 'wb') as f:
        pickle.dump({'std_X': sys_obj.global_std_X,
                     'std_y': sys_obj.global_std_y,
                     'l_max_cap': sys_obj.l_max_cap,
                     'k_max_cap': sys_obj.k_max_cap,
                     'N': sys_obj.N_total,
                     'rho': sys_obj.rho}, f)

    print(f"\n  Checkpoints saved to {save_dir}")

    # ── 训练曲线 ─────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 3, figsize=(16, 4))
    # Phase 1
    hp = hist_pre if isinstance(hist_pre, dict) else hist_pre.history
    axes[0].plot(hp.get('loss', []), label='train')
    axes[0].plot(hp.get('val_loss', []), label='val')
    axes[0].set_title('Phase 1: CE Pre-train Loss'); axes[0].set_xlabel('Epoch')
    axes[0].set_ylabel('MSE'); axes[0].legend(); axes[0].set_yscale('log')
    # Phase 2-A
    ha = hist_A if isinstance(hist_A, dict) else hist_A.history
    axes[1].plot(ha.get('loss', []), label='train')
    axes[1].plot(ha.get('val_loss', []), label='val')
    axes[1].set_title('Phase 2-A: Stabilisation Loss'); axes[1].set_xlabel('Epoch'); axes[1].legend()
    # Phase 2-B
    hb = hist_B if isinstance(hist_B, dict) else hist_B.history
    axes[2].plot(hb.get('loss', []), label='train')
    axes[2].plot(hb.get('val_loss', []), label='val')
    axes[2].set_title('Phase 2-B: BER Sprint Loss'); axes[2].set_xlabel('Epoch'); axes[2].legend()
    plt.tight_layout()
    fig.savefig(str(save_dir / 'training_curves.png'), dpi=150)
    plt.close(fig)
    print(f"  Training curves → {save_dir/'training_curves.png'}")

    return e2e_model, sys_obj.dnn_model_full


# ══════════════════════════════════════════════════════════════════════════════
#  Unfolding 训练（跳过 Phase 1，复用已有 CE 权重）
# ══════════════════════════════════════════════════════════════════════════════
def train_unfolding(sys_obj: AFDMSystem, save_dir: pathlib.Path):
    """
    载入 Phase 1 CE 权重，只训练 2-Stage 深度展开网络。
    前提：save_dir 中已存在 dnn_ce_model.pt + global_stats.pkl
    （即已经跑过 main() 或 eval_only() 成功过一次）。
    """
    import pickle
    save_dir.mkdir(parents=True, exist_ok=True)

    # ── 载入统计量 ───────────────────────────────────────────────────────────
    stats_path = save_dir / 'global_stats.pkl'
    if not stats_path.exists():
        raise FileNotFoundError(
            f"找不到 {stats_path}\n"
            f"请先运行一次完整训练（python train_n512.py）生成 CE 权重后再用 --unfolding-only。")
    with open(stats_path, 'rb') as f:
        stats = pickle.load(f)
    sys_obj.global_std_X = stats['std_X']
    sys_obj.global_std_y = stats['std_y']
    print(f"  global_std_X={sys_obj.global_std_X:.6f}  "
          f"global_std_y={sys_obj.global_std_y:.6f}")

    # ── 重建 CE 骨干并载入权重 ───────────────────────────────────────────────
    K_factor, k_max, L_max, W, pad_size = sys_obj._get_2d_grid_params()
    input_dim   = L_max * W * 2 + 4
    ce_backbone = sys_obj.build_dnn_model_full(input_dim)
    ckpt_path   = save_dir / 'dnn_ce_model.pt'
    ce_backbone.load_state_dict(
        torch.load(str(ckpt_path), map_location='cpu'))
    print(f"  CE 骨干权重载入自 {ckpt_path}")

    # ── 训练展开网络（Phase 1 跳过） ─────────────────────────────────────────
    print("\n" + "█" * 70)
    print("  UNFOLDING TRAINING  (Phase 1 已跳过 — 复用预训练 CE 权重)")
    print("█" * 70)
    unfolding_model, _, (hist_A, hist_B), _ = sys_obj.train_e2e_unfolding(
        n_samples           = N_TRAIN_SAMPLES,
        snr_range           = SNR_TRAIN_RANGE,
        epochs_pretrain     = EPOCHS_PRETRAIN,
        epochs_e2e          = EPOCHS_E2E,
        batch_size          = BATCH_SIZE,
        phase_a_ratio       = PHASE_A_RATIO,
        pretrained_backbone = ce_backbone,
    )

    # ── 保存 checkpoint ──────────────────────────────────────────────────────
    torch.save(unfolding_model.state_dict(),
               str(save_dir / 'unfolding_model.pt'))
    print(f"\n  Unfolding checkpoint saved → {save_dir / 'unfolding_model.pt'}")

    # ── 训练曲线 ─────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for ax, hist, title in zip(axes,
                               [hist_A, hist_B],
                               ['Unfolding Phase 2-A: Stabilisation',
                                'Unfolding Phase 2-B: BER Sprint']):
        h = hist if isinstance(hist, dict) else hist.history
        ax.plot(h.get('loss', []), label='train')
        ax.plot(h.get('val_loss', []), label='val')
        ax.set_title(title); ax.set_xlabel('Epoch'); ax.legend()
    plt.tight_layout()
    fig.savefig(str(save_dir / 'unfolding_training_curves.png'), dpi=150)
    plt.close(fig)
    print(f"  Training curves → {save_dir / 'unfolding_training_curves.png'}")

    return unfolding_model


def _pt_batch_e2e(model, feat_b, y_b, xp_b, sig_b, device, batch_size=32):
    """
    Batch PyTorch E2E inference.
    Inputs are float32 numpy arrays (F, dim).
    Returns detection numpy array (F, 2N).
    """
    model.eval()
    model = model.to(device)
    n = len(feat_b)
    out_list = []
    with torch.no_grad():
        for i in range(0, n, batch_size):
            sl = slice(i, i + batch_size)
            Xf = torch.from_numpy(feat_b[sl]).to(device)
            Yr = torch.from_numpy(y_b[sl]).to(device)
            Xp = torch.from_numpy(xp_b[sl]).to(device)
            Sw = torch.from_numpy(sig_b[sl]).to(device)
            out = model(Xf, Yr, Xp, Sw)
            out_list.append(out['detection'].cpu().numpy())
    return np.concatenate(out_list, axis=0)


def _pt_batch_unfolding(model, feat_b, y_b, xp_b, sig_b, device, batch_size=32):
    """
    Batch inference for UnfoldingModel. Returns Stage-2 detection (F, 2N).
    UnfoldingModel returns 6-tuple: (bits_s1, det_s1, ce_s1, bits_s2, det_s2, ce_s2).
    """
    model.eval()
    model = model.to(device)
    n = len(feat_b)
    out_list = []
    with torch.no_grad():
        for i in range(0, n, batch_size):
            sl = slice(i, i + batch_size)
            Xf = torch.from_numpy(feat_b[sl]).to(device)
            Yr = torch.from_numpy(y_b[sl]).to(device)
            Xp = torch.from_numpy(xp_b[sl]).to(device)
            Sw = torch.from_numpy(sig_b[sl]).to(device)
            _, _, _, _, det_s2, _ = model(Xf, Yr, Xp, Sw)
            out_list.append(det_s2.cpu().numpy())
    return np.concatenate(out_list, axis=0)


# ══════════════════════════════════════════════════════════════════════════════
#  评估：公平对比 (Joint OMP+BP vs DNN-CE+LMMSE vs E2E [vs Unfolding])
# ══════════════════════════════════════════════════════════════════════════════
def evaluate(sys_obj: AFDMSystem, e2e_model, save_dir: pathlib.Path,
             unfolding_model=None):
    """
    对比接收机（3 or 4 路），每个 SNR 点跑 N_TEST_FRAMES 帧。
    若传入 unfolding_model，则增加第 4 路 2-Stage 深度展开对比。

    输出: results 字典，keys 按需包含：
      ['joint_omp_bp', 'dnn_ce_lmmse', 'e2e']  or  [..., 'unfolding']
    """
    save_dir.mkdir(parents=True, exist_ok=True)

    N   = sys_obj.N_total       # 512
    rho = sys_obj.rho

    _, pilot_pos, pilot_syms, guard_pos, data_pos = sys_obj.generate_pilot_frame()
    x_p_only_template = np.zeros(N, dtype=complex)
    x_p_only_template[pilot_pos] = pilot_syms

    # 预取 grid 参数（常量，仅调用一次）
    K_factor, k_max, L_max, W, pad_size = sys_obj._get_2d_grid_params()
    m0 = sys_obj._m0

    _eval_methods = ['joint_omp_bp', 'dnn_ce_lmmse', 'e2e']
    if unfolding_model is not None:
        _eval_methods.append('unfolding')
    results = {m: {snr: {'ber': [], 'nmse': []}
                   for snr in SNR_EVAL_LIST}
               for m in _eval_methods}

    t0 = time.time()

    _method_str = ' / '.join(_eval_methods)
    print("\n" + "█" * 70)
    print(f"  EVALUATION  ({len(SNR_EVAL_LIST)} SNR pts × {N_TEST_FRAMES} frames each)"
          f"  methods: {_method_str}")
    print("█" * 70)

    for snr_db in SNR_EVAL_LIST:
        t_snr = time.time()
        print(f"\n  SNR = {snr_db} dB  [Phase A: 数据生成 + Joint OMP+BP]", flush=True)

        # ── buffers ────────────────────────────────────────────────────────
        feat_buf     : list = []   # (F, input_dim) float32, 已归一化
        y_ri_buf     : list = []   # (F, 2N) float32
        xp_ri_buf    : list = []   # (F, 2N) float32
        sig_buf      : list = []   # (F, 1) float32
        x_ref_buf    : list = []   # (F, |data_pos|) complex
        H_eff_buf    : list = []   # (F, N, N) complex
        y_daft_buf   : list = []   # (F, N) complex
        x_p_only_buf : list = []   # (F, N) complex
        sw2_buf      : list = []   # (F,) float

        ber_joint_list  : list = []
        nmse_joint_list : list = []

        # ── Phase A: 逐帧数据生成 + Joint OMP+BP (CPU串行) ─────────────────
        for iframe in range(N_TEST_FRAMES):
            H_eff, H_time, _ = sys_obj.generate_channel_matrix(30.0, 'EVA')
            data_sym  = QPSK[np.random.randint(0, 4, N)]
            x_data_sc = np.sqrt(1.0 - rho) * data_sym
            x_p_only  = x_p_only_template.copy()
            x_full    = x_data_sc + x_p_only

            s      = sys_obj.afdm_modulation(x_full)
            r, sw2 = sys_obj.add_awgn(H_time @ s, snr_db)
            y_daft = sys_obj.afdm_demodulation(r)
            x_ref  = x_data_sc[data_pos]

            # Joint OMP+BP — CPU迭代，必须串行
            xh_joint, H_joint = sys_obj.joint_iterative_detect(
                y_daft, x_p_only, data_pos, sw2, n_outer=N_OUTER_JOINT)
            xh_joint_hard = hard_qpsk(xh_joint, rho)
            ber_joint_list.append(ber_qpsk(x_ref, xh_joint_hard))
            nmse_joint_list.append(nmse_fro(H_eff, H_joint))

            # 特征提取（纯NumPy，无TF调用）
            feats = sys_obj.extract_dnn_features(
                y_daft, pilot_pos, pilot_syms, guard_pos=guard_pos).reshape(-1)
            if sys_obj.global_std_X is not None:
                feats = feats / sys_obj.global_std_X

            feat_buf.append(feats.astype('float32'))
            y_ri_buf.append(
                np.concatenate([np.real(y_daft), np.imag(y_daft)]).astype('float32'))
            xp_ri_buf.append(
                np.concatenate([np.real(x_p_only), np.imag(x_p_only)]).astype('float32'))
            sig_buf.append(np.float32(sw2))
            x_ref_buf.append(x_ref)
            H_eff_buf.append(H_eff)
            y_daft_buf.append(y_daft)
            x_p_only_buf.append(x_p_only)
            sw2_buf.append(sw2)

            if (iframe + 1) % 20 == 0:
                print(f"    Frame {iframe+1}/{N_TEST_FRAMES}  "
                      f"Joint BER={np.mean(ber_joint_list):.3e}", flush=True)

        # ── Phase B: 批量 DNN-CE 推理 ──────────────────────────────────────
        print(f"  [Phase B: DNN-CE batch predict {N_TEST_FRAMES} frames]", flush=True)
        feat_batch = np.stack(feat_buf)              # (F, input_dim)

        dnn_pred_batch = sys_obj._pt_predict_backbone(
            sys_obj.dnn_model_full, feat_batch)   # (F, L_max*W*2)

        # NumPy后处理（rechirp + H重建 + LMMSE，每帧约1ms，不成瓶颈）
        ber_dnn_list  : list = []
        nmse_dnn_list : list = []
        for iframe in range(N_TEST_FRAMES):
            pred_scaled = dnn_pred_batch[iframe]
            if sys_obj.global_std_y is not None:
                pred_scaled = pred_scaled * sys_obj.global_std_y
            real_2d = pred_scaled[:L_max * W].reshape(L_max, W)
            imag_2d = pred_scaled[L_max * W:].reshape(L_max, W)
            h_2d_pred       = real_2d + 1j * imag_2d
            h_tap_dechirped = sys_obj.map_2d_grid_to_1d(h_2d_pred, pad_size=pad_size)
            h_tap           = sys_obj._rechirp(h_tap_dechirped, m0=m0)
            H_dnn           = sys_obj._reconstruct_H_eff_from_taps_2d(h_tap, m0)

            xh_dnn = sys_obj._lmmse_detect_np(
                H_dnn, y_daft_buf[iframe], x_p_only_buf[iframe], data_pos, sw2_buf[iframe])
            ber_dnn_list.append(ber_qpsk(x_ref_buf[iframe], xh_dnn))
            nmse_dnn_list.append(nmse_fro(H_eff_buf[iframe], H_dnn))

        # ── Phase C: 批量 E2E 推理 ─────────────────────────────────────────
        print(f"  [Phase C: E2E batch predict {N_TEST_FRAMES} frames]", flush=True)
        y_batch   = np.stack(y_ri_buf)                             # (F, 2N)
        xp_batch  = np.stack(xp_ri_buf)                           # (F, 2N)
        sig_batch = np.array(sig_buf, dtype='float32').reshape(-1, 1)  # (F, 1)

        det_batch = _pt_batch_e2e(e2e_model, feat_batch, y_batch,
                                   xp_batch, sig_batch,
                                   sys_obj._pt_device(),
                                   batch_size=EVAL_BATCH_SIZE)    # (F, 2N)
        ber_e2e_list : list = []
        for iframe in range(N_TEST_FRAMES):
            xh_e2e_ri  = det_batch[iframe]
            xh_e2e     = xh_e2e_ri[:N] + 1j * xh_e2e_ri[N:]
            ber_e2e_list.append(ber_qpsk(x_ref_buf[iframe], xh_e2e[data_pos]))

        # ── Phase D: 批量 Unfolding 推理 (可选) ────────────────────────────
        if unfolding_model is not None:
            print(f"  [Phase D: Unfolding batch predict {N_TEST_FRAMES} frames]", flush=True)
            det_unf_batch = _pt_batch_unfolding(
                unfolding_model, feat_batch, y_batch, xp_batch, sig_batch,
                sys_obj._pt_device(), batch_size=EVAL_BATCH_SIZE)
            ber_unf_list = []
            for iframe in range(N_TEST_FRAMES):
                xh_unf_ri = det_unf_batch[iframe]
                xh_unf    = xh_unf_ri[:N] + 1j * xh_unf_ri[N:]
                ber_unf_list.append(ber_qpsk(x_ref_buf[iframe], xh_unf[data_pos]))

        # ── 汇总 ────────────────────────────────────────────────────────────
        results['joint_omp_bp'][snr_db]['ber']  = ber_joint_list
        results['dnn_ce_lmmse'][snr_db]['ber']  = ber_dnn_list
        results['e2e'][snr_db]['ber']            = ber_e2e_list
        results['joint_omp_bp'][snr_db]['nmse'] = nmse_joint_list
        results['dnn_ce_lmmse'][snr_db]['nmse'] = nmse_dnn_list
        results['e2e'][snr_db]['nmse']           = nmse_dnn_list   # 共享 CE backbone
        if unfolding_model is not None:
            results['unfolding'][snr_db]['ber']  = ber_unf_list
            results['unfolding'][snr_db]['nmse'] = nmse_dnn_list   # 共享 CE backbone

        elapsed_snr = time.time() - t_snr
        unf_str = f"  Unf={np.mean(ber_unf_list):.3e}" if unfolding_model is not None else ""
        print(f"  SNR={snr_db}dB  BER: Joint={np.mean(ber_joint_list):.3e}  "
              f"DNN={np.mean(ber_dnn_list):.3e}  E2E={np.mean(ber_e2e_list):.3e}"
              f"{unf_str}  ({elapsed_snr:.0f}s)", flush=True)

    total_elapsed = time.time() - t0
    print(f"\n  评估总耗时 {total_elapsed/60:.1f} min  "
          f"(平均 {total_elapsed/len(SNR_EVAL_LIST):.0f}s/SNR点)")
    return results


# ══════════════════════════════════════════════════════════════════════════════
#  打印 + 绘图
# ══════════════════════════════════════════════════════════════════════════════
def print_results(results):
    _all_m  = ['joint_omp_bp', 'dnn_ce_lmmse', 'e2e', 'unfolding']
    _all_l  = ['Joint OMP+BP',  'DNN-CE+LMMSE', 'E2E DNN+LMMSE', 'Unfolding S2']
    methods = [m for m in _all_m if m in results]
    labels  = [_all_l[_all_m.index(m)] for m in methods]

    # BER table
    print("\n" + "═" * 80)
    print("  BER vs SNR    N=512 UWA AFDM SP系统")
    print("═" * 80)
    hdr = f"{'SNR(dB)':>8}  " + "  ".join(f"{lb:>16}" for lb in labels)
    print(hdr)
    print("─" * len(hdr))
    for snr in SNR_EVAL_LIST:
        row = f"{snr:>8}  "
        for m in methods:
            bers = results[m][snr]['ber']
            row += f"  {np.mean(bers):16.4e}"
        print(row)

    # NMSE table
    print("\n" + "═" * 70)
    print("  NMSE vs SNR   (信道估计质量)")
    print("═" * 70)
    hdr2 = f"{'SNR(dB)':>8}  " + "  ".join(f"{'NMSE_'+m[:8]:>16}" for m in ['joint_omp_bp','dnn_ce_lmmse'])
    print(hdr2); print("─" * len(hdr2))
    for snr in SNR_EVAL_LIST:
        row = f"{snr:>8}"
        for m in ['joint_omp_bp', 'dnn_ce_lmmse']:
            nm = results[m][snr]['nmse']
            if nm:
                row += f"  {np.mean(nm):16.4f}  ({10*np.log10(max(np.mean(nm),1e-20)):+.1f} dB)"
        print(row)

def plot_results(results, save_dir: pathlib.Path):
    _all_m   = ['joint_omp_bp', 'dnn_ce_lmmse', 'e2e', 'unfolding']
    _all_l   = ['Joint OMP+BP (baseline)', 'DNN-CE + LMMSE', 'E2E DNN + LMMSE', 'Unfolding S2']
    _all_mk  = ['o--', 's-', '^-', 'D-']
    _all_col = ['#e06c75', '#61afef', '#98c379', '#e5c07b']
    methods  = [m for m in _all_m if m in results]
    labels   = [_all_l[_all_m.index(m)] for m in methods]
    markers  = [_all_mk[_all_m.index(m)] for m in methods]
    colors   = [_all_col[_all_m.index(m)] for m in methods]

    snrs     = SNR_EVAL_LIST
    bers     = {m: [np.mean(results[m][s]['ber']) for s in snrs] for m in methods}
    nmse_arr = {m: [np.mean(results[m][s]['nmse']) if results[m][s]['nmse'] else None
                     for s in snrs]
                for m in ['joint_omp_bp', 'dnn_ce_lmmse']}

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle('N=512 AFDM SP UWA — Dilated ResNet E2E vs Traditional Baseline',
                 fontsize=12, fontweight='bold')

    # BER
    for m, lb, mk, col in zip(methods, labels, markers, colors):
        ax1.semilogy(snrs, bers[m], mk, color=col, label=lb, linewidth=2, markersize=7)
    ax1.set_xlabel('SNR (dB)'); ax1.set_ylabel('BER')
    ax1.set_title('BER vs SNR   (N=512, P=5 paths, UWA EVA)')
    ax1.legend(); ax1.grid(True, which='both', alpha=0.4)
    ax1.set_xticks(snrs)

    # NMSE
    for m, lb, col in zip(['joint_omp_bp','dnn_ce_lmmse'],
                            ['Joint OMP+BP CE','DNN-CE'],
                            ['#e06c75','#61afef']):
        nm_db = [10*np.log10(max(v,1e-20)) if v else None for v in nmse_arr[m]]
        ax2.plot(snrs, nm_db, 's-' if m=='dnn_ce_lmmse' else 'o--',
                 color=col, label=lb, linewidth=2, markersize=7)
    ax2.set_xlabel('SNR (dB)'); ax2.set_ylabel('NMSE (dB)')
    ax2.set_title('Channel Estimation NMSE vs SNR')
    ax2.legend(); ax2.grid(True, alpha=0.4)
    ax2.set_xticks(snrs)

    plt.tight_layout()
    out = save_dir / 'ber_nmse_comparison.png'
    fig.savefig(str(out), dpi=150)
    plt.close(fig)
    print(f"\n  BER/NMSE 曲线 → {out}")

    # 单独保存高清 BER 图
    fig2, ax = plt.subplots(figsize=(8, 6))
    for m, lb, mk, col in zip(methods, labels, markers, colors):
        ax.semilogy(snrs, bers[m], mk, color=col, label=lb, linewidth=2, markersize=8)
    ax.set_xlabel('SNR (dB)', fontsize=13); ax.set_ylabel('BER', fontsize=13)
    ax.set_title('N=512 AFDM SP — Asymmetric Dilated ResNet E2E\nvs Joint OMP+BP Baseline',
                 fontsize=12)
    ax.legend(fontsize=11); ax.grid(True, which='both', alpha=0.4)
    ax.set_xticks(snrs)
    plt.tight_layout()
    fig2.savefig(str(save_dir / 'ber_comparison_hd.png'), dpi=200)
    plt.close(fig2)


# ══════════════════════════════════════════════════════════════════════════════
#  主函数
# ══════════════════════════════════════════════════════════════════════════════
def main():
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    save_dir = pathlib.Path(SAVE_DIR)
    save_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("  AFDM SP N=512 — Asymmetric Dilated ResNet  训练 + 评估")
    print(f"  N_TRAIN_SAMPLES={N_TRAIN_SAMPLES}  EPOCHS_PRE={EPOCHS_PRETRAIN}"
          f"  EPOCHS_E2E={EPOCHS_E2E}")
    print(f"  N_TEST_FRAMES={N_TEST_FRAMES}  SNR_EVAL={SNR_EVAL_LIST}")
    print(f"  SAVE_DIR={save_dir}")
    print("=" * 70)

    # ── 1. 系统初始化 ───────────────────────────────────────────────────────
    sys_obj = make_system_n512(rho=0.5)

    # ── 2. GPU 信息 + 模型预热 ───────────────────────────────────────────────
    _gpu_info()
    _sanity_test(sys_obj)

    # ── 3. 训练 ─────────────────────────────────────────────────────────────
    t_train_start = time.time()
    e2e_model, dnn_model = train(sys_obj, save_dir)
    train_elapsed = time.time() - t_train_start
    print(f"\n  训练完成，耗时 {train_elapsed/60:.1f} min")

    # ── 4. 评估 ─────────────────────────────────────────────────────────────
    t_eval_start = time.time()
    results = evaluate(sys_obj, e2e_model, save_dir)
    eval_elapsed = time.time() - t_eval_start
    print(f"\n  评估完成，耗时 {eval_elapsed/60:.1f} min")

    # ── 5. 打印 + 绘图 ───────────────────────────────────────────────────────
    print_results(results)
    plot_results(results, save_dir)

    # ── 6. 保存数值结果 ─────────────────────────────────────────────────────
    import pickle
    with open(save_dir / 'eval_results.pkl', 'wb') as f:
        pickle.dump(results, f)
    print(f"  数值结果 → {save_dir/'eval_results.pkl'}")
    print("\n  ALL DONE ✓")


# ══════════════════════════════════════════════════════════════════════════════
#  仅评估模式（跳过训练，从 checkpoint 加载）
# ══════════════════════════════════════════════════════════════════════════════
def eval_only():
    """
    从已有 checkpoint 加载，直接评估。
    前提：先运行过 main() 并在 SAVE_DIR 产生了 *.keras 文件。
    """
    import pickle
    save_dir = pathlib.Path(SAVE_DIR)
    np.random.seed(SEED)

    sys_obj = make_system_n512(rho=0.5)

    # 加载统计量
    with open(save_dir / 'global_stats.pkl', 'rb') as f:
        stats = pickle.load(f)
    sys_obj.global_std_X = stats['std_X']
    sys_obj.global_std_y = stats['std_y']

    # 加载模型（PyTorch）
    # Rebuild architecture then load weights
    K_factor, k_max, L_max, W, pad_size = sys_obj._get_2d_grid_params()
    input_dim = L_max * W * 2 + 4
    data_pos  = sys_obj.generate_pilot_frame()[4]
    sys_obj.dnn_model_full = sys_obj.build_dnn_model_full(input_dim)
    sys_obj.dnn_model_full.load_state_dict(
        torch.load(str(save_dir / 'dnn_ce_model.pt'), map_location='cpu'))
    e2e_model, _ = sys_obj.build_e2e_model(input_dim, data_pos,
                                            ce_backbone=sys_obj.dnn_model_full)
    e2e_model.load_state_dict(
        torch.load(str(save_dir / 'e2e_model.pt'), map_location='cpu'))

    print(f"  模型加载自 {save_dir}")

    # 若已有 unfolding_model.pt，自动加载并纳入对比
    unfolding_model = None
    unf_ckpt = save_dir / 'unfolding_model.pt'
    if unf_ckpt.exists():
        # 先读 checkpoint，从 key 推断训练时的 sic_mode，再重建相同架构
        unf_sd = torch.load(str(unf_ckpt), map_location='cpu')
        _sic_mode = 'qpsk_proj' if 'sic.beta_raw' in unf_sd else 'soft'
        print(f"  Unfolding checkpoint sic_mode 自动检测: '{_sic_mode}'")
        unfolding_model, _, _ = sys_obj.build_e2e_unfolding_model(
            input_dim, data_pos, sic_mode=_sic_mode)
        unfolding_model.load_state_dict(unf_sd)
        print(f"  Unfolding 模型加载自 {unf_ckpt}")
    else:
        print(f"  (未找到 {unf_ckpt}，跳过 Unfolding 对比)")

    results = evaluate(sys_obj, e2e_model, save_dir,
                       unfolding_model=unfolding_model)
    print_results(results)
    plot_results(results, save_dir)

    out_pkl = save_dir / ('eval_results_with_unfolding.pkl'
                          if unfolding_model is not None else 'eval_results.pkl')
    with open(out_pkl, 'wb') as f:
        pickle.dump(results, f)
    print(f"  数值结果 → {out_pkl}")


# ══════════════════════════════════════════════════════════════════════════════
#  Unfolding 模式（载入已有 CE/E2E 权重，只训练+评估展开网络）
# ══════════════════════════════════════════════════════════════════════════════
def unfolding_only():
    """
    从已有 dnn_ce_model.pt 载入 CE 骨干，训练 2-Stage 展开网络，
    再与 Joint OMP+BP / DNN-CE / E2E 四路对比评估。
    前提：先跑过 main() 生成 dnn_ce_model.pt + e2e_model.pt + global_stats.pkl。
    """
    import pickle
    save_dir = pathlib.Path(SAVE_DIR)
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    sys_obj = make_system_n512(rho=0.5)
    _gpu_info()

    # ── 训练展开网络 ─────────────────────────────────────────────────────────
    unfolding_model = train_unfolding(sys_obj, save_dir)

    # ── 载入 DNN-CE + E2E 权重（用于公平对比）──────────────────────────────
    K_factor, k_max, L_max, W, pad_size = sys_obj._get_2d_grid_params()
    input_dim = L_max * W * 2 + 4
    data_pos  = sys_obj.generate_pilot_frame()[4]
    sys_obj.dnn_model_full = sys_obj.build_dnn_model_full(input_dim)
    sys_obj.dnn_model_full.load_state_dict(
        torch.load(str(save_dir / 'dnn_ce_model.pt'), map_location='cpu'))
    e2e_model, _ = sys_obj.build_e2e_model(input_dim, data_pos,
                                            ce_backbone=sys_obj.dnn_model_full)
    e2e_ckpt = save_dir / 'e2e_model.pt'
    if e2e_ckpt.exists():
        e2e_model.load_state_dict(torch.load(str(e2e_ckpt), map_location='cpu'))
    print(f"  E2E 模型载入自 {save_dir}")

    # ── 四路对比评估 ─────────────────────────────────────────────────────────
    results = evaluate(sys_obj, e2e_model, save_dir,
                       unfolding_model=unfolding_model)
    print_results(results)
    plot_results(results, save_dir)

    with open(save_dir / 'eval_results_unfolding.pkl', 'wb') as f:
        pickle.dump(results, f)
    print(f"  数值结果 → {save_dir / 'eval_results_unfolding.pkl'}")
    print("\n  UNFOLDING DONE ✓")


# ══════════════════════════════════════════════════════════════════════════════
#  Refiner 模式（载入已有 E2E 权重，训练 Turbo-AI Channel Refiner）
# ══════════════════════════════════════════════════════════════════════════════
def refiner_only():
    """
    从已有 e2e_model.pt 载入 Stage-1 E2E，训练 Stage-2 Channel Refiner，
    并输出 NMSE 与 Stage-1 的对比表格。
    验收标准: val_NMSE < 0.15 (目标突破 Stage-1 的 ~0.20)。
    前提: 先跑过 main() 生成 e2e_model.pt + global_stats.pkl。
    """
    import pickle
    save_dir = pathlib.Path(SAVE_DIR)
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    sys_obj = make_system_n512(rho=0.5)
    _gpu_info()

    # ── 载入统计量 ─────────────────────────────────────────────────────────
    stats_path = save_dir / 'global_stats.pkl'
    if not stats_path.exists():
        raise FileNotFoundError(
            f"找不到 {stats_path}\n"
            f"请先运行 main() 生成完整 checkpoint 后再用 --refiner-only。")
    with open(stats_path, 'rb') as f:
        stats = pickle.load(f)
    sys_obj.global_std_X = stats['std_X']
    sys_obj.global_std_y = stats['std_y']
    print(f"  global_std_X={sys_obj.global_std_X:.6f}  "
          f"global_std_y={sys_obj.global_std_y:.6f}")

    # ── 重建并载入 E2E 模型（Stage-1）──────────────────────────────────────
    K_factor, k_max, L_max, W, pad_size = sys_obj._get_2d_grid_params()
    input_dim = L_max * W * 2 + 4
    data_pos  = sys_obj.generate_pilot_frame()[4]

    ce_backbone = sys_obj.build_dnn_model_full(input_dim)
    ce_backbone.load_state_dict(
        torch.load(str(save_dir / 'dnn_ce_model.pt'), map_location='cpu'))
    e2e_model, _ = sys_obj.build_e2e_model(input_dim, data_pos,
                                            ce_backbone=ce_backbone)
    e2e_model.load_state_dict(
        torch.load(str(save_dir / 'e2e_model.pt'), map_location='cpu'))
    print(f"  Stage-1 E2E 模型载入自 {save_dir}")

    # ── 训练 Channel Refiner ───────────────────────────────────────────────
    print("\n" + "█" * 70)
    print("  TURBO REFINER TRAINING  (Stage-1 frozen)")
    print("█" * 70)
    turbo_model, hist = sys_obj.train_turbo_refiner(
        pretrained_e2e_model = e2e_model,
        n_samples   = N_TRAIN_SAMPLES,
        snr_range   = SNR_TRAIN_RANGE,
        epochs      = 30,
        batch_size  = 64,
        lr          = 5e-4,
        patience    = 8,
        min_lr      = 1e-6,
    )

    # ── 保存 checkpoint ────────────────────────────────────────────────────
    torch.save(turbo_model.state_dict(),
               str(save_dir / 'refiner_model.pt'))
    print(f"\n  Refiner checkpoint saved → {save_dir / 'refiner_model.pt'}")

    # ── 训练曲线 ───────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(13, 4))
    axes[0].plot(hist['loss'], label='train'); axes[0].plot(hist['val_loss'], label='val')
    axes[0].set_title('Refiner MSE Loss'); axes[0].set_xlabel('Epoch')
    axes[0].legend(); axes[0].set_yscale('log')
    axes[1].plot(hist['val_nmse'], color='#e5c07b', label='val NMSE')
    axes[1].axhline(0.15, color='r', linestyle='--', label='threshold 0.15')
    axes[1].set_title('Refiner Validation NMSE'); axes[1].set_xlabel('Epoch')
    axes[1].legend()
    plt.tight_layout()
    fig.savefig(str(save_dir / 'refiner_training_curves.png'), dpi=150)
    plt.close(fig)
    print(f"  Curves → {save_dir / 'refiner_training_curves.png'}")

    # ── NMSE 对比评估 ──────────────────────────────────────────────────────
    N   = sys_obj.N_total
    rho = sys_obj.rho
    _, pilot_pos, pilot_syms, guard_pos, data_pos = sys_obj.generate_pilot_frame()
    x_p_only_template = np.zeros(N, dtype=complex)
    x_p_only_template[pilot_pos] = pilot_syms
    device = sys_obj._pt_device()
    e2e_model   = e2e_model.to(device).eval()
    turbo_model = turbo_model.to(device).eval()

    print("\n" + "═" * 65)
    print("  NMSE Comparison  (Stage-1 E2E vs Stage-2 Turbo Refiner)")
    print("═" * 65)
    print(f"  {'SNR(dB)':>8}  {'NMSE_S1':>12}  {'NMSE_S2':>12}  {'Improv%':>10}")
    print("  " + "─" * 50)

    all_s1, all_s2 = [], []
    for snr_db in SNR_EVAL_LIST:
        nmse_s1_list, nmse_s2_list = [], []
        feat_buf, y_buf, xp_buf, sig_buf, Heff_buf = [], [], [], [], []

        for _ in range(N_TEST_FRAMES):
            H_eff, H_time, _ = sys_obj.generate_channel_matrix(30.0, 'EVA')
            data_sym  = QPSK[np.random.randint(0, 4, N)]
            x_data_sc = np.sqrt(1.0 - rho) * data_sym
            x_p_only  = x_p_only_template.copy()
            x_full    = x_data_sc + x_p_only

            s, sw2    = sys_obj.add_awgn(H_time @ sys_obj.afdm_modulation(x_full), snr_db)
            y_daft    = sys_obj.afdm_demodulation(s)

            feats = sys_obj.extract_dnn_features(
                y_daft, pilot_pos, pilot_syms, guard_pos=guard_pos).reshape(-1)
            if sys_obj.global_std_X is not None:
                feats = feats / sys_obj.global_std_X

            feat_buf.append(feats.astype('float32'))
            y_buf.append(np.concatenate([np.real(y_daft), np.imag(y_daft)]).astype('float32'))
            xp_buf.append(np.concatenate([np.real(x_p_only), np.imag(x_p_only)]).astype('float32'))
            sig_buf.append(np.float32(sw2))
            Heff_buf.append(H_eff)

        feat_t = torch.from_numpy(np.stack(feat_buf)).to(device)
        y_t    = torch.from_numpy(np.stack(y_buf)).to(device)
        xp_t   = torch.from_numpy(np.stack(xp_buf)).to(device)
        sig_t  = torch.from_numpy(np.array(sig_buf, dtype='float32').reshape(-1, 1)).to(device)

        with torch.no_grad():
            out_e2e = e2e_model(feat_t, y_t, xp_t, sig_t)
            out_ref = turbo_model(feat_t, y_t, xp_t, sig_t)

        std_y = sys_obj.global_std_y
        m0    = sys_obj._m0
        K_factor, k_max, L_max, W, pad_size = sys_obj._get_2d_grid_params()

        for iframe in range(N_TEST_FRAMES):
            H_eff = Heff_buf[iframe]

            def _h_flat_to_nmse(h_sc_np):
                h_p = h_sc_np * std_y
                h2d = (h_p[:L_max * W] + 1j * h_p[L_max * W:]).reshape(L_max, W)
                h1d_d = sys_obj.map_2d_grid_to_1d(h2d, pad_size=pad_size)
                h1d   = sys_obj._rechirp(h1d_d, m0=m0)
                H_est = sys_obj._reconstruct_H_eff_from_taps_2d(h1d, m0)
                return nmse_fro(H_eff, H_est)

            nmse_s1_list.append(_h_flat_to_nmse(
                out_e2e['channel_est'][iframe].cpu().numpy()))
            nmse_s2_list.append(_h_flat_to_nmse(
                out_ref['channel_est_s2'][iframe].cpu().numpy()))

        m1 = float(np.mean(nmse_s1_list))
        m2 = float(np.mean(nmse_s2_list))
        imp = (m1 - m2) / max(m1, 1e-12) * 100
        all_s1.append(m1); all_s2.append(m2)
        print(f"  {snr_db:>8}  {m1:12.4f}  {m2:12.4f}  {imp:+10.1f}%")

    print("  " + "─" * 50)
    gm1 = float(np.mean(all_s1)); gm2 = float(np.mean(all_s2))
    print(f"  {'avg':>8}  {gm1:12.4f}  {gm2:12.4f}  "
          f"{(gm1-gm2)/max(gm1,1e-12)*100:+10.1f}%")
    print("═" * 65)

    if gm2 < 0.15:
        print("  ✓ 验收通过：Stage-2 平均 NMSE < 0.15")
    else:
        min_nmse = min(hist['val_nmse'])
        print(f"  ✗ 验收未通过：平均 NMSE={gm2:.4f}  (target < 0.15)")
        print(f"  (训练期间最佳 val_nmse={min_nmse:.4f})")

    with open(save_dir / 'refiner_nmse.pkl', 'wb') as f:
        pickle.dump({'snr': SNR_EVAL_LIST, 'nmse_s1': all_s1, 'nmse_s2': all_s2,
                     'hist': hist}, f)
    print(f"  数值结果 → {save_dir / 'refiner_nmse.pkl'}")
    print("\n  REFINER DONE ✓")


# ══════════════════════════════════════════════════════════════════════════════
#  OAMP-Net 共享评估辅助函数
# ══════════════════════════════════════════════════════════════════════════════
def _eval_oamp_ber(sys_obj, oamp_model, lmmse_model, device,
                  snr_list=None, n_frames=None):
    """
    对 OAMP-Net 和 LMMSE E2E（可选）做 BER + v_x 对比评估。
    使用正确的 SP 仿真流程（无需 generate_sample 方法）。

    返回: (results_dict, all_oamp_ber, all_lmmse_ber)
      results_dict : {snr_db: {ber_oamp, ber_lmmse, vx_oamp, vx_lmmse}}
      all_oamp_ber : list[float]
      all_lmmse_ber: list[float]
    """
    import torch
    if snr_list is None:
        snr_list = SNR_EVAL_LIST
    if n_frames is None:
        n_frames = N_TEST_FRAMES

    QPSK = np.array([1+1j, 1-1j, -1+1j, -1-1j], dtype=complex) / np.sqrt(2)
    N    = sys_obj.N_total
    rho  = sys_obj.rho
    _, pilot_pos, pilot_syms, guard_pos, _ = sys_obj.generate_pilot_frame()
    x_p_tpl = np.zeros(N, dtype=complex)
    x_p_tpl[pilot_pos] = pilot_syms

    print("\n" + "═" * 70)
    print("  BER / v_x Comparison  (LMMSE E2E vs OAMP-Net E2E)")
    print("═" * 70)
    hdr = (f"{'SNR(dB)':>8}  {'LMMSE_BER':>12}  {'OAMP_BER':>12}  "
           f"{'LMMSE_vx':>12}  {'OAMP_vx':>12}")
    print(hdr)
    print("─" * len(hdr))

    all_oamp_ber  = []
    all_lmmse_ber = []
    results_dict  = {}

    for snr_db in snr_list:
        sigma_w      = 10 ** (-snr_db / 20.0)
        sigma_w2_val = sigma_w ** 2

        feat_list = []; y_list = []; xp_list = []; x_true_list = []
        for _ in range(n_frames):
            max_speed    = np.random.uniform(5, sys_obj.max_speed_kmh)
            channel_type = np.random.choice(['EPA', 'EVA'])
            _, H_time, _ = sys_obj.generate_channel_matrix(max_speed, channel_type)

            data_sym  = QPSK[np.random.randint(0, 4, N)]
            x_data_sc = np.sqrt(1.0 - rho) * data_sym
            x_full    = x_data_sc + x_p_tpl

            s      = sys_obj.afdm_modulation(x_full)
            r, sw2 = sys_obj.add_awgn(H_time @ s, snr_db)
            y_daft = sys_obj.afdm_demodulation(r)

            feats  = sys_obj.extract_dnn_features(
                y_daft, pilot_pos, pilot_syms, guard_pos)
            feat_list.append((feats / sys_obj.global_std_X).astype(np.float32))
            y_list.append(np.concatenate(
                [y_daft.real, y_daft.imag]).astype(np.float32))
            xp_list.append(np.concatenate(
                [x_p_tpl.real, x_p_tpl.imag]).astype(np.float32))
            x_true_list.append(x_data_sc)   # (N,) complex, what receiver should recover

        Xf = torch.from_numpy(np.stack(feat_list)).to(device)
        Yr = torch.from_numpy(np.stack(y_list)).to(device)
        Xp = torch.from_numpy(np.stack(xp_list)).to(device)
        Sw = torch.full((n_frames, 1), sigma_w2_val,
                        dtype=torch.float32, device=device)

        # ── OAMP inference ─────────────────────────────────────────────────
        with torch.no_grad():
            out_oamp = oamp_model(Xf, Yr, Xp, Sw)
        x_hat_np  = out_oamp['detection'].cpu().numpy()   # (F, 2N)
        oamp_bers = []
        for fi in range(n_frames):
            xh   = x_hat_np[fi]
            xh_c = xh[:N] + 1j * xh[N:]
            oamp_bers.append(ber_qpsk(x_true_list[fi], xh_c))
        mean_oamp_ber = float(np.mean(oamp_bers))
        mean_oamp_vx  = float(out_oamp['v_x'].mean().cpu().item())

        # ── LMMSE baseline ─────────────────────────────────────────────────
        if lmmse_model is not None:
            with torch.no_grad():
                out_lm = lmmse_model(Xf, Yr, Xp, Sw)
            x_hat_lm   = out_lm['detection'].cpu().numpy()
            lmmse_bers = []
            for fi in range(n_frames):
                xh   = x_hat_lm[fi]
                xh_c = xh[:N] + 1j * xh[N:]
                lmmse_bers.append(ber_qpsk(x_true_list[fi], xh_c))
            mean_lmmse_ber = float(np.mean(lmmse_bers))
            mean_lmmse_vx  = float(out_lm['v_x'].mean().cpu().item())
        else:
            mean_lmmse_ber = float('nan')
            mean_lmmse_vx  = float('nan')

        all_oamp_ber.append(mean_oamp_ber)
        all_lmmse_ber.append(mean_lmmse_ber)
        results_dict[snr_db] = {
            'ber_oamp' : mean_oamp_ber,  'ber_lmmse': mean_lmmse_ber,
            'vx_oamp'  : mean_oamp_vx,   'vx_lmmse' : mean_lmmse_vx,
        }
        print(f"  {snr_db:>8}  {mean_lmmse_ber:12.4e}  {mean_oamp_ber:12.4e}  "
              f"{mean_lmmse_vx:12.5f}  {mean_oamp_vx:12.5f}")

    return results_dict, all_oamp_ber, all_lmmse_ber


# ══════════════════════════════════════════════════════════════════════════════
#  OAMP-Net 模式（载入已有 CE 权重，训练 OAMPNetDetector 代替 LMMSE+Demapper）
# ══════════════════════════════════════════════════════════════════════════════
def oamp_only():
    """
    从已有 dnn_ce_model.pt 载入预训练 CE 权重，训练 E2EOAMPModel（OAMP-Net 检测器），
    并输出与原始 E2E (LMMSE) 的 BER + v_x 对比表格。

    两阶段流程:
      Phase A: 冻结 CE，只训练 OAMP 9 个标量参数 (20 epochs, lr=1e-2)
      Phase B: 解冻 CE，全网络联合微调         (15 epochs, lr=1e-5)

    验收标准:
      BER @ 25dB < 0.05  (原 LMMSE: ~0.13)
      mean(v_x) @ 25dB  > 0.05  (原 LMMSE: ~0.00)

    前提: 先跑过 main() 生成 dnn_ce_model.pt + global_stats.pkl。
    """
    import pickle
    save_dir  = pathlib.Path(SAVE_DIR)
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    sys_obj = make_system_n512(rho=0.5)
    _gpu_info()

    # ── 载入统计量 ──────────────────────────────────────────────────────────
    stats_path = save_dir / 'global_stats.pkl'
    if not stats_path.exists():
        raise FileNotFoundError(
            f"找不到 {stats_path}\n"
            f"请先运行 main() 生成完整 checkpoint 后再用 --oamp-only。")
    with open(stats_path, 'rb') as f:
        stats = pickle.load(f)
    sys_obj.global_std_X = stats['std_X']
    sys_obj.global_std_y = stats['std_y']
    print(f"  global_std_X={sys_obj.global_std_X:.6f}  "
          f"global_std_y={sys_obj.global_std_y:.6f}")

    # ── 重建并载入预训练 CE backbone ────────────────────────────────────────
    K_factor, k_max, L_max, W, pad_size = sys_obj._get_2d_grid_params()
    input_dim = L_max * W * 2 + 4
    data_pos  = sys_obj.generate_pilot_frame()[4]

    ce_backbone = sys_obj.build_dnn_model_full(input_dim)
    ckpt_ce = save_dir / 'dnn_ce_model.pt'
    ce_backbone.load_state_dict(
        torch.load(str(ckpt_ce), map_location='cpu'))
    print(f"  CE backbone 载入自 {ckpt_ce}")

    # ── 训练 OAMP-Net E2E 模型 ─────────────────────────────────────────────
    oamp_model, hist_a, hist_b = sys_obj.train_oamp_e2e(
        pretrained_ce_backbone = ce_backbone,
        n_samples     = N_TRAIN_SAMPLES,
        snr_range     = SNR_TRAIN_RANGE,
        epochs_phase_a= 20,
        epochs_phase_b= 15,
        batch_size    = 64,
        lr_a          = 1e-2,
        lr_b          = 1e-5,
        patience      = 8,
        min_lr        = 1e-6,
        num_oamp_layers = 4,
    )

    # ── 保存 checkpoint ────────────────────────────────────────────────────
    torch.save(oamp_model.state_dict(),
               str(save_dir / 'oamp_e2e_model.pt'))
    print(f"\n  OAMP-Net checkpoint → {save_dir / 'oamp_e2e_model.pt'}")

    # ── 训练曲线 ───────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 3, figsize=(16, 4))
    axes[0].plot(hist_a['loss'], label='train'); axes[0].plot(hist_a['val_loss'], label='val')
    axes[0].set_title('Phase A: OAMP-only Loss (CE frozen)')
    axes[0].set_xlabel('Epoch'); axes[0].legend(); axes[0].set_yscale('log')
    axes[1].plot(hist_b['loss'], label='train'); axes[1].plot(hist_b['val_loss'], label='val')
    axes[1].set_title('Phase B: Joint Fine-tune Loss')
    axes[1].set_xlabel('Epoch'); axes[1].legend(); axes[1].set_yscale('log')
    axes[2].plot(hist_a['val_ber'], label='Phase A', color='#e5c07b')
    axes[2].plot(hist_b['val_ber'], label='Phase B', color='#98c379')
    axes[2].set_title('Val BER by Phase'); axes[2].set_xlabel('Epoch')
    axes[2].legend()
    plt.tight_layout()
    fig.savefig(str(save_dir / 'oamp_training_curves.png'), dpi=150)
    plt.close(fig)
    print(f"  Curves → {save_dir / 'oamp_training_curves.png'}")

    # ── BER + v_x 对比评估 ──────────────────────────────────────────────────
    device = sys_obj._pt_device()
    oamp_model.eval();  oamp_model = oamp_model.to(device)

    # 重建 E2E LMMSE 基线供对比
    ce_e2e = sys_obj.build_dnn_model_full(input_dim)
    e2e_ckpt = save_dir / 'e2e_model.pt'
    if e2e_ckpt.exists():
        from afdm_sp_joint_unrolled.afdm_models import E2EModel
        ce_e2e.load_state_dict(torch.load(str(ckpt_ce), map_location='cpu'))
        e2e_lmmse, _ = sys_obj.build_e2e_model(input_dim, data_pos, ce_backbone=ce_e2e)
        e2e_lmmse.load_state_dict(torch.load(str(e2e_ckpt), map_location='cpu'))
        e2e_lmmse.eval();  e2e_lmmse = e2e_lmmse.to(device)
        has_lmmse = True
    else:
        has_lmmse = False
        print("  (e2e_model.pt not found — skipping LMMSE baseline)")

    results_oamp, all_oamp_ber, all_lmmse_ber = _eval_oamp_ber(
        sys_obj, oamp_model,
        e2e_lmmse if has_lmmse else None,
        device)

    print("═" * 70)
    avg_oamp  = float(np.nanmean(all_oamp_ber))
    avg_lmmse = float(np.nanmean(all_lmmse_ber))
    print(f"  {'avg':>8}  {avg_lmmse:12.4e}  {avg_oamp:12.4e}")

    # 验收判断
    ber_25 = results_oamp.get(25, {}).get('ber_oamp', 1.0)
    vx_25  = results_oamp.get(25, {}).get('vx_oamp', 0.0)
    ok_ber = ber_25 < 0.05
    ok_vx  = vx_25  > 0.05
    print()
    print(f"  BER @ 25dB = {ber_25:.4e}  ({'✓' if ok_ber else '✗'} target < 0.05)")
    print(f"  v_x @ 25dB = {vx_25:.5f}   ({'✓' if ok_vx  else '✗'} target > 0.05)")
    if ok_ber and ok_vx:
        print("  ✓ 验收通过：OAMP-Net 成功打破 Error Floor")
    else:
        print("  ✗ 验收未通过，建议增加 OAMP 层数或调整训练参数")

    # 保存数值结果
    with open(save_dir / 'oamp_results.pkl', 'wb') as f:
        pickle.dump({'snr': SNR_EVAL_LIST, 'results': results_oamp,
                     'hist_a': hist_a, 'hist_b': hist_b}, f)
    print(f"  数值结果 → {save_dir / 'oamp_results.pkl'}")
    print("\n  OAMP DONE ✓")


def ep_only():
    """
    从已有 dnn_ce_model.pt 载入预训练 CE 权重，训练 E2EEPModel（EP 检测器），
    并保存 ep_e2e_model.pt。
    """
    import pickle
    save_dir = pathlib.Path(SAVE_DIR)
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    sys_obj = make_system_n512(rho=0.5)
    _gpu_info()

    stats_path = save_dir / 'global_stats.pkl'
    if not stats_path.exists():
        raise FileNotFoundError(
            f"找不到 {stats_path}\n"
            f"请先运行 main() 生成完整 checkpoint 后再用 --ep-only。")
    with open(stats_path, 'rb') as f:
        stats = pickle.load(f)
    sys_obj.global_std_X = stats['std_X']
    sys_obj.global_std_y = stats['std_y']
    print(f"  global_std_X={sys_obj.global_std_X:.6f}  "
          f"global_std_y={sys_obj.global_std_y:.6f}")

    K_factor, k_max, L_max, W, pad_size = sys_obj._get_2d_grid_params()
    input_dim = L_max * W * 2 + 4

    ce_backbone = sys_obj.build_dnn_model_full(input_dim)
    ckpt_ce = save_dir / 'dnn_ce_model.pt'
    if not ckpt_ce.exists():
        raise FileNotFoundError(f"找不到 {ckpt_ce}，请先运行 main()。")
    ce_backbone.load_state_dict(
        torch.load(str(ckpt_ce), map_location='cpu'))
    print(f"  CE backbone 载入自 {ckpt_ce}")

    ep_model, hist_a, hist_b = sys_obj.train_ep_e2e(
        pretrained_ce_backbone=ce_backbone,
        n_samples=N_TRAIN_SAMPLES,
        snr_range=SNR_TRAIN_RANGE,
        epochs_phase_a=20,
        epochs_phase_b=15,
        batch_size=64,
        lr_a=5e-3,
        lr_b=1e-5,
        patience=8,
        min_lr=1e-6,
        num_ep_layers=4,
    )

    torch.save(ep_model.state_dict(), str(save_dir / 'ep_e2e_model.pt'))
    print(f"\n  EP checkpoint → {save_dir / 'ep_e2e_model.pt'}")

    fig, axes = plt.subplots(1, 3, figsize=(16, 4))
    axes[0].plot(hist_a['loss'], label='train')
    axes[0].plot(hist_a['val_loss'], label='val')
    axes[0].set_title('Phase A: EP-only Loss (CE frozen)')
    axes[0].set_xlabel('Epoch')
    axes[0].legend()
    axes[0].set_yscale('log')
    axes[1].plot(hist_b['loss'], label='train')
    axes[1].plot(hist_b['val_loss'], label='val')
    axes[1].set_title('Phase B: Joint Fine-tune Loss')
    axes[1].set_xlabel('Epoch')
    axes[1].legend()
    axes[1].set_yscale('log')
    axes[2].plot(hist_a['val_ber'], label='Phase A', color='#e5c07b')
    axes[2].plot(hist_b['val_ber'], label='Phase B', color='#98c379')
    axes[2].set_title('Val BER by Phase')
    axes[2].set_xlabel('Epoch')
    axes[2].legend()
    plt.tight_layout()
    fig.savefig(str(save_dir / 'ep_training_curves.png'), dpi=150)
    plt.close(fig)
    print(f"  Curves → {save_dir / 'ep_training_curves.png'}")

    with open(save_dir / 'ep_results.pkl', 'wb') as f:
        pickle.dump({'hist_a': hist_a, 'hist_b': hist_b}, f)
    print(f"  数值结果 → {save_dir / 'ep_results.pkl'}")
    print("  运行验证: python -m afdm_sp_joint_unrolled.verify_ep "
          f"--ckpt {save_dir}")
    print("\n  EP DONE ✓")


# ══════════════════════════════════════════════════════════════════════════════
#  --verify-oamp: 只载入已保存权重，跑 BER+v_x 对比表，不重新训练
# ══════════════════════════════════════════════════════════════════════════════
def verify_oamp_only():
    """
    从 outputs_n512/ 载入 oamp_e2e_model.pt（和可选的 e2e_model.pt 基线），
    直接运行 BER + v_x 对比评估，不需要重新训练。

    用法:
        python -m afdm_sp_joint_unrolled.train_n512 --verify-oamp
    """
    import pickle
    save_dir = pathlib.Path(SAVE_DIR)
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    sys_obj = make_system_n512(rho=0.5)
    _gpu_info()

    # ── 载入统计量 ────────────────────────────────────────────────────────
    stats_path = save_dir / 'global_stats.pkl'
    if not stats_path.exists():
        raise FileNotFoundError(f"找不到 {stats_path}，请先运行 main()")
    with open(stats_path, 'rb') as f:
        stats = pickle.load(f)
    sys_obj.global_std_X = stats['std_X']
    sys_obj.global_std_y = stats['std_y']
    print(f"  global_std_X={sys_obj.global_std_X:.6f}  "
          f"global_std_y={sys_obj.global_std_y:.6f}")

    K_factor, k_max, L_max, W, pad_size = sys_obj._get_2d_grid_params()
    input_dim = L_max * W * 2 + 4
    data_pos  = sys_obj.generate_pilot_frame()[4]
    device    = sys_obj._pt_device()

    # ── 载入 OAMP-Net checkpoint ──────────────────────────────────────────
    oamp_ckpt = save_dir / 'oamp_e2e_model.pt'
    if not oamp_ckpt.exists():
        raise FileNotFoundError(
            f"找不到 {oamp_ckpt}\n"
            f"请先运行 --oamp-only 完成训练后再用 --verify-oamp。")
    ce_backbone = sys_obj.build_dnn_model_full(input_dim)
    oamp_model, _ = sys_obj.build_e2e_oamp_model(
        input_dim, data_pos, ce_backbone=ce_backbone, num_oamp_layers=4,
        device=device)
    oamp_model.load_state_dict(
        torch.load(str(oamp_ckpt), map_location=device))
    oamp_model.eval()
    print(f"  OAMP-Net checkpoint 已载入: {oamp_ckpt}")

    # ── 载入 LMMSE E2E 基线（可选）────────────────────────────────────────
    e2e_ckpt = save_dir / 'e2e_model.pt'
    lmmse_model = None
    if e2e_ckpt.exists():
        ce_e2e = sys_obj.build_dnn_model_full(input_dim)
        ckpt_ce = save_dir / 'dnn_ce_model.pt'
        ce_e2e.load_state_dict(
            torch.load(str(ckpt_ce), map_location=device))
        lmmse_model, _ = sys_obj.build_e2e_model(
            input_dim, data_pos, ce_backbone=ce_e2e)
        lmmse_model.load_state_dict(
            torch.load(str(e2e_ckpt), map_location=device))
        lmmse_model.eval()
        lmmse_model = lmmse_model.to(device)
        print(f"  LMMSE E2E 基线已载入:      {e2e_ckpt}")
    else:
        print("  (e2e_model.pt 不存在，跳过 LMMSE 基线对比)")

    # ── 运行评估 ──────────────────────────────────────────────────────────
    results, all_oamp_ber, all_lmmse_ber = _eval_oamp_ber(
        sys_obj, oamp_model, lmmse_model, device)

    print("═" * 70)
    avg_oamp  = float(np.nanmean(all_oamp_ber))
    avg_lmmse = float(np.nanmean(all_lmmse_ber))
    print(f"  {'avg':>8}  {avg_lmmse:12.4e}  {avg_oamp:12.4e}")

    ber_25 = results.get(25, {}).get('ber_oamp', 1.0)
    vx_25  = results.get(25, {}).get('vx_oamp', 0.0)
    ok_ber = ber_25 < 0.05
    ok_vx  = vx_25  > 0.05
    print()
    print(f"  BER @ 25dB = {ber_25:.4e}  ({'✓' if ok_ber else '✗'} target < 0.05)")
    print(f"  v_x @ 25dB = {vx_25:.5f}   ({'✓' if ok_vx  else '✗'} target > 0.05)")
    if ok_ber and ok_vx:
        print("  ✓ 验收通过：OAMP-Net 成功打破 Error Floor")
    else:
        print("  ✗ 验收未通过")

    with open(save_dir / 'oamp_verify_results.pkl', 'wb') as f:
        pickle.dump({'snr': SNR_EVAL_LIST, 'results': results}, f)
    print(f"  数值结果 → {save_dir / 'oamp_verify_results.pkl'}")
    print("\n  VERIFY OAMP DONE ✓")


def verify_ep_only():
    """
    从 outputs_n512/ 载入 ep_e2e_model.pt，直接运行 EP / OAMP / LMMSE 对比。
    """
    from afdm_sp_joint_unrolled import verify_ep as verify_ep_module

    old_argv = list(sys.argv)
    try:
        sys.argv = [
            'verify_ep.py',
            '--ckpt', str(pathlib.Path(SAVE_DIR)),
            '--frames', str(N_TEST_FRAMES),
        ]
        verify_ep_module.main()
    finally:
        sys.argv = old_argv


# ══════════════════════════════════════════════════════════════════════════════
#  JointTurboReceiver evaluation helper
# ══════════════════════════════════════════════════════════════════════════════
def _eval_turbo_ber(sys_obj, turbo_model, oamp_model, lmmse_model, device,
                    snr_list=None, n_frames=None):
    """
    BER + v_x comparison: LMMSE E2E, OAMP-Net, and JointTurboReceiver.
    Uses the correct SP simulation loop (no generate_sample).

    Returns: (results_dict, all_turbo_ber, all_oamp_ber, all_lmmse_ber)
    """
    if snr_list is None:
        snr_list  = SNR_EVAL_LIST
    if n_frames is None:
        n_frames  = N_TEST_FRAMES

    QPSK = np.array([1+1j, 1-1j, -1+1j, -1-1j], dtype=complex) / np.sqrt(2)
    N    = sys_obj.N_total
    rho  = sys_obj.rho
    _, pilot_pos, pilot_syms, guard_pos, _ = sys_obj.generate_pilot_frame()
    x_p_tpl = np.zeros(N, dtype=complex)
    x_p_tpl[pilot_pos] = pilot_syms

    print("\n" + "\u2550" * 70)
    print("  BER / v_x Comparison  (LMMSE / OAMP-Net / TurboReceiver)")
    print("\u2550" * 70)
    hdr = (f"{'SNR(dB)':>8}  {'LMMSE_BER':>12}  {'OAMP_BER':>12}  "
           f"{'Turbo_BER':>12}  {'Turbo_vx':>12}")
    print(hdr)
    print("\u2500" * len(hdr))

    all_turbo_ber = []; all_oamp_ber = []; all_lmmse_ber = []
    results_dict  = {}

    for snr_db in snr_list:
        sigma_w      = 10 ** (-snr_db / 20.0)
        sigma_w2_val = sigma_w ** 2

        feat_list = []; y_list = []; xp_list = []; x_true_list = []
        for _ in range(n_frames):
            max_speed    = np.random.uniform(5, sys_obj.max_speed_kmh)
            channel_type = np.random.choice(['EPA', 'EVA'])
            _, H_time, _ = sys_obj.generate_channel_matrix(max_speed, channel_type)

            data_sym  = QPSK[np.random.randint(0, 4, N)]
            x_data_sc = np.sqrt(1.0 - rho) * data_sym
            x_full    = x_data_sc + x_p_tpl

            s      = sys_obj.afdm_modulation(x_full)
            r, sw2 = sys_obj.add_awgn(H_time @ s, snr_db)
            y_daft = sys_obj.afdm_demodulation(r)

            feats  = sys_obj.extract_dnn_features(
                y_daft, pilot_pos, pilot_syms, guard_pos)
            feat_list.append((feats / sys_obj.global_std_X).astype(np.float32))
            y_list.append(np.concatenate(
                [y_daft.real, y_daft.imag]).astype(np.float32))
            xp_list.append(np.concatenate(
                [x_p_tpl.real, x_p_tpl.imag]).astype(np.float32))
            x_true_list.append(x_data_sc)

        Xf = torch.from_numpy(np.stack(feat_list)).to(device)
        Yr = torch.from_numpy(np.stack(y_list)).to(device)
        Xp = torch.from_numpy(np.stack(xp_list)).to(device)
        Sw = torch.full((n_frames, 1), sigma_w2_val,
                        dtype=torch.float32, device=device)

        # ── Turbo inference ──────────────────────────────────────────
        with torch.no_grad():
            out_turbo = turbo_model(Xf, Yr, Xp, Sw)
        # 'final_bits': (B, 2N) LLR from last iteration
        x_hat_turbo = out_turbo['final_detection'].cpu().numpy()  # (F, 2N)
        vx_turbo    = float(out_turbo['final_vx'].mean().cpu().item())
        turbo_bers  = []
        for fi in range(n_frames):
            xh   = x_hat_turbo[fi]
            xh_c = xh[:N] + 1j * xh[N:]
            turbo_bers.append(ber_qpsk(x_true_list[fi], xh_c))
        mean_turbo_ber = float(np.mean(turbo_bers))

        # ── OAMP baseline ────────────────────────────────────────────
        mean_oamp_ber = float('nan')
        if oamp_model is not None:
            with torch.no_grad():
                out_oamp = oamp_model(Xf, Yr, Xp, Sw)
            x_hat_np = out_oamp['detection'].cpu().numpy()
            oamp_bers = []
            for fi in range(n_frames):
                xh   = x_hat_np[fi]
                xh_c = xh[:N] + 1j * xh[N:]
                oamp_bers.append(ber_qpsk(x_true_list[fi], xh_c))
            mean_oamp_ber = float(np.mean(oamp_bers))

        # ── LMMSE baseline ────────────────────────────────────────
        mean_lmmse_ber = float('nan')
        if lmmse_model is not None:
            with torch.no_grad():
                out_lm = lmmse_model(Xf, Yr, Xp, Sw)
            x_hat_lm   = out_lm['detection'].cpu().numpy()
            lmmse_bers = []
            for fi in range(n_frames):
                xh   = x_hat_lm[fi]
                xh_c = xh[:N] + 1j * xh[N:]
                lmmse_bers.append(ber_qpsk(x_true_list[fi], xh_c))
            mean_lmmse_ber = float(np.mean(lmmse_bers))

        all_turbo_ber.append(mean_turbo_ber)
        all_oamp_ber.append(mean_oamp_ber)
        all_lmmse_ber.append(mean_lmmse_ber)
        results_dict[snr_db] = {
            'ber_turbo' : mean_turbo_ber,
            'ber_oamp'  : mean_oamp_ber,
            'ber_lmmse' : mean_lmmse_ber,
            'vx_turbo'  : vx_turbo,
        }
        print(f"  {snr_db:>8}  {mean_lmmse_ber:12.4e}  {mean_oamp_ber:12.4e}  "
              f"{mean_turbo_ber:12.4e}  {vx_turbo:12.5f}")

    return results_dict, all_turbo_ber, all_oamp_ber, all_lmmse_ber


# ══════════════════════════════════════════════════════════════════════════════
#  --turbo-only: 两阶段联合训练 JointTurboReceiver
# ══════════════════════════════════════════════════════════════════════════════
def turbo_only():
    """
    从已有 dnn_ce_model.pt + oamp_e2e_model.pt 载入预训练权重，
    训练 JointTurboReceiver（T=3 outer iterations，OAMP ⇄ ChannelRefiner），
    并与 OAMP-Net / LMMSE E2E 输出三曲线 BER 对比。

    两阶段流程:
      Phase A: 冻结 CE backbone，训练 T×OAMP + T×Refiner (30 epochs, lr=5e-4)
               Refiner 使用 Kaiming init + alpha-scale 残差；
               param groups: Refiner 10×lr, OAMP 1×lr
      Phase B: 解冻 CE backbone，全网络联合微调          (20 epochs, lr=5e-5)
               CE 使用 0.1×lr 保护；Refiner 仍 10×lr

    验收标准:
      BER @ 25dB < 0.01  (OAMP 基线: ~0.03, LMMSE: ~0.13)

    前提: 先跑过 --oamp-only 生成 oamp_e2e_model.pt。
    """
    import pickle
    save_dir = pathlib.Path(SAVE_DIR)
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    sys_obj = make_system_n512(rho=0.5)
    _gpu_info()

    # ─ 载入统计量 ────────────────────────────────────────────────
    stats_path = save_dir / 'global_stats.pkl'
    if not stats_path.exists():
        raise FileNotFoundError(
            f"找不到 {stats_path}\n请先运行 main() 生成 checkpoint 后再用 --turbo-only。")
    with open(stats_path, 'rb') as f:
        stats = pickle.load(f)
    sys_obj.global_std_X = stats['std_X']
    sys_obj.global_std_y = stats['std_y']
    print(f"  global_std_X={sys_obj.global_std_X:.6f}  "
          f"global_std_y={sys_obj.global_std_y:.6f}")

    K_factor, k_max, L_max, W, pad_size = sys_obj._get_2d_grid_params()
    input_dim = L_max * W * 2 + 4
    data_pos  = sys_obj.generate_pilot_frame()[4]
    device    = sys_obj._pt_device()

    # ─ 载入预训练 CE backbone ──────────────────────────────────────────────
    ckpt_ce = save_dir / 'dnn_ce_model.pt'
    if not ckpt_ce.exists():
        raise FileNotFoundError(f"找不到 {ckpt_ce}，请先运行 main()。")
    ce_state = torch.load(str(ckpt_ce), map_location='cpu')
    print(f"  CE backbone 载入自 {ckpt_ce}")

    # ─ 载入预训练 OAMP-Net checkpoint（可选，不存在则随机初始化）──────────
    oamp_ckpt = save_dir / 'oamp_e2e_model.pt'
    oamp_state = None
    if oamp_ckpt.exists():
        oamp_state = torch.load(str(oamp_ckpt), map_location='cpu')
        print(f"  OAMP-Net checkpoint 载入自 {oamp_ckpt}")
    else:
        print("  (oamp_e2e_model.pt 不存在，OAMP 参数随机初始化)")

    # ─ 训练 JointTurboReceiver ─────────────────────────────────────────────
    turbo_model, hist_a, hist_b = sys_obj.train_turbo_joint(
        pretrained_ce_state_dict   = ce_state,
        pretrained_oamp_state_dict = oamp_state,
        n_samples       = N_TRAIN_SAMPLES,
        snr_range       = SNR_TRAIN_RANGE,
        epochs_phase_a  = 30,
        epochs_phase_b  = 20,
        batch_size      = 32,
        lr_a            = 5e-4,
        lr_b            = 5e-5,
        patience        = 8,
        min_lr          = 1e-7,
        num_outer_iters = 3,
        num_oamp_layers = 4,
    )

    # ─ 保存 checkpoint ──────────────────────────────────────────────────────
    torch.save(turbo_model.state_dict(),
               str(save_dir / 'turbo_receiver_model.pt'))
    print(f"\n  Turbo checkpoint → {save_dir / 'turbo_receiver_model.pt'}")

    # ─ 绘训练曲线 ──────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 3, figsize=(18, 4))
    axes[0].plot(hist_a['loss'], label='train'); axes[0].plot(hist_a['val_loss'], label='val')
    axes[0].set_title('Phase A: CE-frozen Loss'); axes[0].set_xlabel('Epoch')
    axes[0].legend(); axes[0].set_yscale('log')
    axes[1].plot(hist_b['loss'], label='train'); axes[1].plot(hist_b['val_loss'], label='val')
    axes[1].set_title('Phase B: Joint Fine-tune Loss'); axes[1].set_xlabel('Epoch')
    axes[1].legend(); axes[1].set_yscale('log')
    axes[2].plot(hist_a['val_ber'], label='Phase A', color='#e5c07b')
    axes[2].plot(hist_b['val_ber'], label='Phase B', color='#98c379')
    axes[2].set_title('Val BER by Phase'); axes[2].set_xlabel('Epoch'); axes[2].legend()
    plt.tight_layout()
    fig.savefig(str(save_dir / 'turbo_training_curves.png'), dpi=150)
    plt.close(fig)
    print(f"  Curves → {save_dir / 'turbo_training_curves.png'}")

    turbo_model.eval();  turbo_model = turbo_model.to(device)

    # ─ 载入 OAMP 和 LMMSE 基线模型供对比 ────────────────────────────────
    oamp_model_ref  = None
    lmmse_model_ref = None
    if oamp_ckpt.exists():
        ce_backbone2 = sys_obj.build_dnn_model_full(input_dim)
        oamp_model_ref, _ = sys_obj.build_e2e_oamp_model(
            input_dim, data_pos, ce_backbone=ce_backbone2,
            num_oamp_layers=4, device=device)
        oamp_model_ref.load_state_dict(
            torch.load(str(oamp_ckpt), map_location=device))
        oamp_model_ref.eval()
    e2e_ckpt = save_dir / 'e2e_model.pt'
    if e2e_ckpt.exists() and ckpt_ce.exists():
        ce_e2e = sys_obj.build_dnn_model_full(input_dim)
        ce_e2e.load_state_dict(torch.load(str(ckpt_ce), map_location=device))
        lmmse_model_ref, _ = sys_obj.build_e2e_model(
            input_dim, data_pos, ce_backbone=ce_e2e)
        lmmse_model_ref.load_state_dict(
            torch.load(str(e2e_ckpt), map_location=device))
        lmmse_model_ref.eval();  lmmse_model_ref = lmmse_model_ref.to(device)

    # ─ BER + v_x 对比评估 ────────────────────────────────────────────────
    results, all_turbo_ber, all_oamp_ber, all_lmmse_ber = _eval_turbo_ber(
        sys_obj, turbo_model, oamp_model_ref, lmmse_model_ref, device)

    print("\u2550" * 70)
    print(f"  {'avg':>8}  {np.nanmean(all_lmmse_ber):12.4e}  "
          f"{np.nanmean(all_oamp_ber):12.4e}  {np.nanmean(all_turbo_ber):12.4e}")

    ber_25 = results.get(25, {}).get('ber_turbo', 1.0)
    ok_ber = ber_25 < 0.01
    print()
    print(f"  BER @ 25dB = {ber_25:.4e}  ({'✓' if ok_ber else '✗'} target < 0.01)")
    if ok_ber:
        print("  ✓ 验收通过：JointTurboReceiver 达到目标 BER")
    else:
        print("  ✗ 验收未通过，建议检查 lambda_obs / lambda_ce 权重或增加 T")

    with open(save_dir / 'turbo_results.pkl', 'wb') as f:
        pickle.dump({'snr': SNR_EVAL_LIST, 'results': results,
                     'hist_a': hist_a, 'hist_b': hist_b}, f)
    print(f"  数值结果 → {save_dir / 'turbo_results.pkl'}")
    print("\n  TURBO DONE ✓")


# ══════════════════════════════════════════════════════════════════════════════
#  --verify-turbo: 只载入已保存权重，直接跑三模型 BER 对比，不重新训练
# ══════════════════════════════════════════════════════════════════════════════
def verify_turbo_only():
    """
    从 outputs_n512/ 载入 turbo_receiver_model.pt，直接运行
    3-曲线 BER + v_x 对比（LMMSE / OAMP-Net / Turbo），不重新训练。

    用法:
        python -m afdm_sp_joint_unrolled.train_n512 --verify-turbo
    """
    import pickle
    save_dir = pathlib.Path(SAVE_DIR)
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    sys_obj = make_system_n512(rho=0.5)
    _gpu_info()

    stats_path = save_dir / 'global_stats.pkl'
    if not stats_path.exists():
        raise FileNotFoundError(f"找不到 {stats_path}，请先运行 main()")
    with open(stats_path, 'rb') as f:
        stats = pickle.load(f)
    sys_obj.global_std_X = stats['std_X']
    sys_obj.global_std_y = stats['std_y']
    print(f"  global_std_X={sys_obj.global_std_X:.6f}  "
          f"global_std_y={sys_obj.global_std_y:.6f}")

    K_factor, k_max, L_max, W, pad_size = sys_obj._get_2d_grid_params()
    input_dim = L_max * W * 2 + 4
    data_pos  = sys_obj.generate_pilot_frame()[4]
    device    = sys_obj._pt_device()

    # ─ 载入 Turbo checkpoint ──────────────────────────────────────────────
    turbo_ckpt = save_dir / 'turbo_receiver_model.pt'
    if not turbo_ckpt.exists():
        raise FileNotFoundError(
            f"找不到 {turbo_ckpt}\n"
            f"请先运行 --turbo-only 完成训练后再用 --verify-turbo。")
    turbo_model, _ = sys_obj.build_turbo_receiver(
        input_dim, data_pos,
        num_outer_iters=3, num_oamp_layers=4, device=device)
    turbo_model.load_state_dict(
        torch.load(str(turbo_ckpt), map_location=device))
    turbo_model.eval()
    print(f"  Turbo checkpoint 已载入: {turbo_ckpt}")

    # ─ 可选 OAMP-Net 基线 ──────────────────────────────────────────────────
    oamp_model_ref  = None
    oamp_ckpt = save_dir / 'oamp_e2e_model.pt'
    if oamp_ckpt.exists():
        ce_backbone2 = sys_obj.build_dnn_model_full(input_dim)
        oamp_model_ref, _ = sys_obj.build_e2e_oamp_model(
            input_dim, data_pos, ce_backbone=ce_backbone2,
            num_oamp_layers=4, device=device)
        oamp_model_ref.load_state_dict(
            torch.load(str(oamp_ckpt), map_location=device))
        oamp_model_ref.eval()
        print(f"  OAMP-Net 基线已载入: {oamp_ckpt}")

    # ─ 可选 LMMSE E2E 基线 ────────────────────────────────────────────────
    lmmse_model_ref = None
    e2e_ckpt = save_dir / 'e2e_model.pt'
    ckpt_ce  = save_dir / 'dnn_ce_model.pt'
    if e2e_ckpt.exists() and ckpt_ce.exists():
        ce_e2e = sys_obj.build_dnn_model_full(input_dim)
        ce_e2e.load_state_dict(torch.load(str(ckpt_ce), map_location=device))
        lmmse_model_ref, _ = sys_obj.build_e2e_model(
            input_dim, data_pos, ce_backbone=ce_e2e)
        lmmse_model_ref.load_state_dict(
            torch.load(str(e2e_ckpt), map_location=device))
        lmmse_model_ref.eval();  lmmse_model_ref = lmmse_model_ref.to(device)
        print(f"  LMMSE E2E 基线已载入: {e2e_ckpt}")

    # ─ 运行评估 ───────────────────────────────────────────────────────────
    results, all_turbo_ber, all_oamp_ber, all_lmmse_ber = _eval_turbo_ber(
        sys_obj, turbo_model, oamp_model_ref, lmmse_model_ref, device)

    print("\u2550" * 70)
    print(f"  {'avg':>8}  {np.nanmean(all_lmmse_ber):12.4e}  "
          f"{np.nanmean(all_oamp_ber):12.4e}  {np.nanmean(all_turbo_ber):12.4e}")

    ber_25 = results.get(25, {}).get('ber_turbo', 1.0)
    ok_ber = ber_25 < 0.01
    print()
    print(f"  BER @ 25dB = {ber_25:.4e}  ({'✓' if ok_ber else '✗'} target < 0.01)")
    if ok_ber:
        print("  ✓ 验收通过：JointTurboReceiver 达到目标 BER")
    else:
        print("  ✗ 验收未通过")

    with open(save_dir / 'turbo_verify_results.pkl', 'wb') as f:
        pickle.dump({'snr': SNR_EVAL_LIST, 'results': results}, f)
    print(f"  数值结果 → {save_dir / 'turbo_verify_results.pkl'}")
    print("\n  VERIFY TURBO DONE ✓")


if __name__ == '__main__':
    # Windows spawn guard: prevents DataLoader workers from re-launching the
    # whole script and entering an infinite fork loop.
    import torch
    torch.multiprocessing.freeze_support()

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--eval-only', action='store_true',
                        help='从 checkpoint 加载模型，跳过训练')
    parser.add_argument('--unfolding-only', action='store_true',
                        help='载入已有 CE 权重，只训练+评估 2-Stage 展开网络')
    parser.add_argument('--refiner-only', action='store_true',
                        help='载入已有 E2E 权重，训练 Turbo-AI Channel Refiner')
    parser.add_argument('--oamp-only', action='store_true',
                        help='载入已有 CE 权重，训练 OAMP-Net 检测器替换 LMMSE')
    parser.add_argument('--verify-oamp', action='store_true',
                        help='载入已保存的 oamp_e2e_model.pt，直接运行 BER+v_x 验证，不重新训练')
    parser.add_argument('--ep-only', action='store_true',
                        help='载入已有 CE 权重，训练 EP-Net 检测器替换 LMMSE')
    parser.add_argument('--verify-ep', action='store_true',
                        help='载入已保存的 ep_e2e_model.pt，直接运行 EP/OAMP/LMMSE 验证')
    parser.add_argument('--turbo-only', action='store_true',
                        help='载入已有 CE+OAMP 权重，训练 JointTurboReceiver (T=3 outer iters)')
    parser.add_argument('--verify-turbo', action='store_true',
                        help='载入已保存的 turbo_receiver_model.pt，直接运行三曲线 BER 验证，不重新训练')
    args = parser.parse_args()

    if args.eval_only:
        eval_only()
    elif args.unfolding_only:
        unfolding_only()
    elif args.refiner_only:
        refiner_only()
    elif args.oamp_only:
        oamp_only()
    elif args.verify_oamp:
        verify_oamp_only()
    elif args.ep_only:
        ep_only()
    elif args.verify_ep:
        verify_ep_only()
    elif args.turbo_only:
        turbo_only()
    elif args.verify_turbo:
        verify_turbo_only()
    else:
        main()
