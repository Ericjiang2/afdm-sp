"""
test_omp_baselines.py — 独立测试 OMP+LMMSE 与 Joint OMP+MP 基线
在分数多普勒 AFDM SP 系统下的 NMSE / BER 性能。

运行方式 (在 OTFS-channel-estimation/ 目录下):
    /opt/anaconda3/envs/CE/bin/python afdm_sp_refactored/test_omp_baselines.py

不需要预训练任何 DNN，纯 NumPy 运行，速度较快。
"""
import numpy as np
import time
import sys
import pathlib

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ── 路径设置 ─────────────────────────────────────────────────────────
_HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(_HERE.parent))

from afdm_sp_refactored.run_sp_unfolding import AFDMSystem

# ================================================================
# 配置
# ================================================================
N_DOPPLER   = 10
M_DELAY     = 10
RHO         = 0.5
SNR_LIST    = [0, 5, 10, 15, 20, 25, 30]
N_SAMPLES   = 500       # 每个 SNR 的测试样本数（增大可得更准确曲线）
N_OUTER_OMP = 5         # Joint 外层迭代次数

# ================================================================
# 初始化系统
# ================================================================
print("=" * 60)
print("  AFDM SP OMP Baseline 独立测试 (MATLAB-UWA 水声信道)")
print("=" * 60)
print(f"  N_total={N_DOPPLER*M_DELAY}, rho={RHO}, SNR={SNR_LIST}")
print(f"  每 SNR 样本数: {N_SAMPLES}, Joint 外迭代: {N_OUTER_OMP}")
print()

sys_obj = AFDMSystem(N=N_DOPPLER, M=M_DELAY, rho=RHO)

# QPSK 星座 & 数据缩放
QPSK      = np.array([1+1j, 1-1j, -1+1j, -1-1j], dtype=complex) / np.sqrt(2)
DATA_CONST = np.sqrt(1.0 - RHO) * QPSK    # PIC 探测器使用的星座点

# ================================================================
# 辅助函数
# ================================================================
def nmse(H_true, H_est):
    return float(np.linalg.norm(H_true - H_est, 'fro')**2 /
                 np.linalg.norm(H_true, 'fro')**2)

def hard_decide(sym_arr, constellation):
    return np.array([constellation[np.argmin(np.abs(s - constellation))]
                     for s in sym_arr], dtype=complex)

def ber_qpsk(x_true, x_det):
    """QPSK BER: 每个符号判 2 bit (I/Q 各 1 bit)。"""
    err_i = float(np.mean((np.real(x_true) > 0) != (np.real(x_det) > 0)))
    err_q = float(np.mean((np.imag(x_true) > 0) != (np.imag(x_det) > 0)))
    return (err_i + err_q) / 2.0

# ================================================================
# 主测试循环
# ================================================================
# 结果存储
metrics = {k: {
    'nmse_ls': [], 'nmse_mmse': [], 'nmse_omp': [], 'nmse_dict_ls': [], 'nmse_joint': [],
    'ber_ls':  [], 'ber_mmse':  [], 'ber_omp':  [], 'ber_joint': [],
    'ber_dict_ls': [],
    'time_omp': [], 'time_joint': [],
} for k in SNR_LIST}

_, pilot_pos, pilot_syms, guard_pos, data_pos = sys_obj.generate_pilot_frame()

for snr_db in SNR_LIST:
    print(f"SNR = {snr_db:3d} dB  ({N_SAMPLES} 样本)...", end='', flush=True)
    t0 = time.time()

    for _ in range(N_SAMPLES):
        # 生成水声信道（MATLAB acousticChannelEnhanced 端口）
        H_eff, H_time, _ = sys_obj.generate_channel_matrix()

        # SP 帧组装
        N = sys_obj.N_total
        data_sym  = QPSK[np.random.randint(0, 4, N)]
        x_data_sc = np.sqrt(1.0 - RHO) * data_sym   # 数据缩放
        x_p_only  = np.zeros(N, dtype=complex)
        x_p_only[pilot_pos] = pilot_syms
        x_full    = x_data_sc + x_p_only             # SP 叠加帧

        # 发送 → AWGN → 接收
        r_noisy, sigma2 = sys_obj.add_awgn(
            H_time @ sys_obj.afdm_modulation(x_full), snr_db)
        y_daft = sys_obj.afdm_demodulation(r_noisy)

        # ── LS 基线（ZC相关）──────────────────────────────────
        H_ls = sys_obj.improved_ls_estimation(
            y_daft, pilot_pos, pilot_syms, guard_pos)
        xh_ls = sys_obj._lmmse_detect_np(H_ls, y_daft, x_p_only, data_pos, sigma2)

        # ── 字典Ridge LS 基线（MATLAB风格）────────────────────
        H_dict_ls = sys_obj.dictionary_ls_estimate(y_daft, sigma2)
        xh_dict_ls = sys_obj._lmmse_detect_np(H_dict_ls, y_daft, x_p_only, data_pos, sigma2)

        # ── MMSE 基线 ────────────────────────────────────────
        H_mm = sys_obj.traditional_mmse_estimation(
            y_daft, pilot_pos, pilot_syms, guard_pos, sigma2)
        xh_mm = sys_obj._lmmse_detect_np(H_mm, y_daft, x_p_only, data_pos, sigma2)

        # ── OMP+LMMSE 基线 ───────────────────────────────────
        t_omp = time.time()
        xh_omp, H_omp = sys_obj.omp_lmmse_detect(
            y_daft, x_p_only, data_pos, sigma2)
        time_omp = time.time() - t_omp

        # ── Joint OMP+MP 基线 ────────────────────────────────
        t_joint = time.time()
        xh_joint, H_joint = sys_obj.joint_iterative_detect(
            y_daft, x_p_only, data_pos, sigma2, n_outer=N_OUTER_OMP)
        time_joint = time.time() - t_joint

        # ── 收集指标 ─────────────────────────────────────────
        # NMSE：针对全 N×N 矩阵
        m = metrics[snr_db]
        m['nmse_ls'].append(nmse(H_eff, H_ls))
        m['nmse_dict_ls'].append(nmse(H_eff, H_dict_ls))
        m['nmse_mmse'].append(nmse(H_eff, H_mm))
        m['nmse_omp'].append(nmse(H_eff, H_omp))
        m['nmse_joint'].append(nmse(H_eff, H_joint))

        # BER：data_pos 子集（SP 模式 data_pos = all N）
        x_ref = x_data_sc[data_pos]
        m['ber_ls'].append(ber_qpsk(x_ref, xh_ls))
        m['ber_dict_ls'].append(ber_qpsk(x_ref, xh_dict_ls))
        m['ber_mmse'].append(ber_qpsk(x_ref, xh_mm))
        m['ber_omp'].append(ber_qpsk(x_ref, xh_omp))
        m['ber_joint'].append(ber_qpsk(x_ref, xh_joint))
        m['time_omp'].append(time_omp)
        m['time_joint'].append(time_joint)

    elapsed = time.time() - t0
    print(f"  done ({elapsed:.1f}s)")

# ================================================================
# 汇总打印
# ================================================================
print()
print("=" * 80)
print("  NMSE 对比 (dB)")
print("=" * 80)
hdr = f"{'SNR':>4} | {'ZC-LS':>9} | {'Dict-LS':>9} | {'MMSE':>9} | {'OMP':>9} | {'Joint':>9}"
print(hdr)
print("-" * len(hdr))
for snr in SNR_LIST:
    m = metrics[snr]
    def db(v): return 10*np.log10(max(np.mean(v), 1e-20))
    print(f"{snr:4d} | {db(m['nmse_ls']):9.2f} | {db(m['nmse_dict_ls']):9.2f} | "
          f"{db(m['nmse_mmse']):9.2f} | {db(m['nmse_omp']):9.2f} | {db(m['nmse_joint']):9.2f}")

print()
print("=" * 80)
print("  BER 对比")
print("=" * 80)
hdr2 = (f"{'SNR':>4} | {'ZC-LS':>10} | {'Dict-LS':>10} | {'MMSE':>10} | "
        f"{'OMP+LMMSE':>11} | {'Joint':>11}")
print(hdr2)
print("-" * len(hdr2))
for snr in SNR_LIST:
    m = metrics[snr]
    print(f"{snr:4d} | {np.mean(m['ber_ls']):10.4e} | "
          f"{np.mean(m['ber_dict_ls']):10.4e} | "
          f"{np.mean(m['ber_mmse']):10.4e} | "
          f"{np.mean(m['ber_omp']):11.4e} | "
          f"{np.mean(m['ber_joint']):11.4e}")

print()
avg_omp_ms   = 1e3 * np.mean([v for s in SNR_LIST for v in metrics[s]['time_omp']])
avg_joint_ms = 1e3 * np.mean([v for s in SNR_LIST for v in metrics[s]['time_joint']])
print(f"平均运行时间:  OMP+LMMSE={avg_omp_ms:.1f} ms/sample, "
      f"Joint OMP+MP={avg_joint_ms:.1f} ms/sample")

# ================================================================
# 绘图
# ================================================================
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

snrs = SNR_LIST

# --- NMSE ---
ax = axes[0]
def mean_db(lst):
    return [10*np.log10(max(np.mean(metrics[s][lst]), 1e-20)) for s in snrs]

ax.plot(snrs, mean_db('nmse_ls'),      'o-',  label='ZC-LS',       linewidth=2, markersize=7)
ax.plot(snrs, mean_db('nmse_dict_ls'), 'D-',  label='Dict-LS',     linewidth=2, markersize=6,
        color='#2ca02c')
ax.plot(snrs, mean_db('nmse_mmse'),    's-',  label='MMSE',        linewidth=2, markersize=7)
ax.plot(snrs, mean_db('nmse_omp'),     'v--', label='OMP',         linewidth=2, markersize=7,
        color='#9467bd')
ax.plot(snrs, mean_db('nmse_joint'),   '*--', label='Joint OMP+MP', linewidth=2, markersize=9,
        color='#8c564b')
ax.set_xlabel('SNR (dB)', fontsize=12)
ax.set_ylabel('NMSE (dB)', fontsize=12)
ax.set_title(f'NMSE vs SNR (AFDM SP, N={N_DOPPLER*M_DELAY}, ρ={RHO})', fontsize=12)
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)

# --- BER ---
ax = axes[1]
def mean_ber(key):
    return [np.mean(metrics[s][key]) for s in snrs]

ax.semilogy(snrs, mean_ber('ber_ls'),       'o-',  label='ZC-LS+LMMSE',    linewidth=2, markersize=7)
ax.semilogy(snrs, mean_ber('ber_dict_ls'),  'D-',  label='Dict-LS+LMMSE',  linewidth=2, markersize=6,
            color='#2ca02c')
ax.semilogy(snrs, mean_ber('ber_mmse'),     's-',  label='MMSE+LMMSE',     linewidth=2, markersize=7)
ax.semilogy(snrs, mean_ber('ber_omp'),      'v--', label='OMP+LMMSE',      linewidth=2, markersize=7,
            color='#9467bd')
ax.semilogy(snrs, mean_ber('ber_joint'),    '*--', label=f'Joint OMP+MP ({N_OUTER_OMP}-iter)',
            linewidth=2, markersize=9, color='#8c564b')
ax.set_xlabel('SNR (dB)', fontsize=12)
ax.set_ylabel('BER', fontsize=12)
ax.set_title(f'BER vs SNR (AFDM SP, 分数多普勒)', fontsize=12)
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3, which='both')

plt.tight_layout()
out_path = (pathlib.Path(__file__).parent /
            f'omp_baseline_test_N{N_DOPPLER*M_DELAY}_rho{RHO:.2f}.png')
plt.savefig(str(out_path), dpi=300, bbox_inches='tight')
print(f"\n图表已保存: {out_path.name}")
print("测试完成。")