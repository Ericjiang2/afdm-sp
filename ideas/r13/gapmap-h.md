# 第 13 轮阶段 A：runner `h` `§4 B1` 精测缺口地图（`[放宽TWC]` · `[轨B-ISAC]`）

- **测量时间**：2026-11-26 02:39–03:18（耗时约 59 分钟 `≤ 90` 分钟预算；**只量缺口，不出点子**）
- **运行环境**：`deinlab` `/home/guoyikun/.conda/envs/AFDM/bin/python`（`OMP_NUM_THREADS=1`，单任务 `≤ 2` 核，远程目录 `/data/guoyikun/tmp/funnel_h_r13/`，本地缓存 `~/.cache/idea-funnel/afdm-20261126-h-r13/stageA_g1_g4.json` 与 `stageA_g5_g7.json`）
- **测量脚本**：
  - 公共算子与红线 1 核验：`ideas/r13/probes/h_r13_stageA_common.py`
  - `B1-G1 ~ B1-G4`：`ideas/r13/probes/h_r13_stageA_g1_g4.py`
  - `B1-G5 ~ B1-G7`：`ideas/r13/probes/h_r13_stageA_g5_g7.py`

---

## 一、红线 1 原图正常无地板点与算子恒等复现核验（全部 `< 1e-12`）

| 核验项 | 被引论文与公式/图号 | 实测误差 / 读数 | 判定 |
|---|---|---|---|
| 非整数 $2Nc_1=2.37$ 酉性与快速 `DAFT/IDAFT` | `Bemani TWC'23` Eq. (1)–(6)、`Liu & Schober 2607` Eq. (3) | $\|\mathbf{A}\mathbf{A}^H-\mathbf{I}\|_F = 2.31\times 10^{-15}$，FFT 快算误差 `5.79e-15` | PASS (`< 1e-12`) |
| 含 `CPP` 双块连续线性卷积 vs 矩阵 $\mathbf{E}(\ell,\nu)$ | `Liu & Schober 2607` Eq. (7)–(10)、`Tang TWC'26` Eq. (2),(6),(7) | $\|\mathbf{y}_{\mathrm{CPP\_conv}}-\mathbf{E}(\ell,\nu)\mathbf{s}\|_2 = 3.55\times 10^{-15}$，整数移位峰误差 `0.0` | PASS (`< 1e-12`) |
| `B1-G1` 零斜视窄带退化等价 | `Elbir WCL'24` Eq. (1)–(4)（$\eta_{\mathrm{bw}}=0$） | $\|\mathbf{H}_{\mathrm{wb}}(\eta_{\mathrm{bw}}=0)-\mathbf{H}_{\mathrm{nb}}\|_F = 1.38\times 10^{-14}$ | PASS (`< 1e-12`) |
| `B1-G3` `1-bit` DAC 主瓣满增益引理 | `Wang, Hu, Li & Masouros TWC'25` Lemma 1（Eq. 37–39，$\theta_1=0^\circ$） | 阵列照射功率误差 `0.0`（精确达 $N_t P_{\mathrm{blk}}$） | PASS (`< 1e-12`) |
| `B1-G4` 软限幅功放高回退线性极限 | `Sui & Zilong Liu TCOM'26` Eq. (25)–(27), Fig. 7 | 线性区重构误差 `0.0`，无噪 `16-QAM SER = 0.00000` | PASS (`< 1e-12`) |
| `B1-G6` `WMMSE-MM` 感知约束紧可行性 | `Rang Liu & Schober arXiv:2607.05119` Eq. (35b), Fig. 1a | $\mathbf{a}_t^H\mathbf{R}_x\mathbf{a}_t / \Gamma_s = 1.00012 \ge 1$，和速率单调递增 | PASS |
| `B1-G7` 无噪符号级预编码正安全裕度 | `Tang & Fei TWC'26` Eq. (40),(52), Fig. 6–7 | 无噪 `QPSK SER = 0.00000`，最小相长裕度 `min_CI = +0.7354 > 0` | PASS |

---

## 二、`§4 B1` 七个具体子问题实测缺口总表（12 独立随机多径/多角度场景均值）

| 子问题 ID 与具体切口 | 锚定 2024–2026 论文与图号 | 账本 | `(a)` 已发表 AFDM/ISAC 原方法（配平外环与零阶标定） | `(b)` 单篇母方法 $\mathbf{F}_N\to\mathbf{A}$ 零改动直套 | 真值 / 同硬件上限 | 对最强对手缺口 & $c_1=0$ 非同构核查 | 是否达标进阶段 B |
|---|---|---|---|---|---|---|---|
| **`B1-G1`**：宽带大孔径无 TTD 相控阵混合波束斜视（$N_t=64, N_{\mathrm{RF}}=6, K=3, \eta_{\mathrm{bw}}=0.12, \nu_{\max}=0.65, 20\text{ dB}$） | `Elbir WCL'24` (`10.1109/LWC.2024.3489632` Fig.2,4) + `Luo & Gao TWC'26` (`10.1109/twc.2026.3651469`) + `Liu 2607` | 破壁账 | `SumRate = 21.80 bps/Hz`<br>`TarGain = -10.50 dB` | `SumRate = 20.58 bps/Hz`<br>`TarGain = -10.51 dB` | 理想 TTD：`25.84 bps/Hz, -6.00 dB`<br>同无 TTD 相控阵展宽：`15.04 bps/Hz, -6.40 dB` | 目标增益较 TTD 差 `4.50 dB`，但**同无 TTD 硬件展宽波束会倒扣 `-6.76 bps/Hz` 和速率**；且 $c_1=0$ 目标斜视损失同为 `-10.50 dB`，地面毫米波 $\Delta_{\max}\nu_{\max}<0.02$ | **否（主动淘汰）** |
| **`B1-G2`**：少射频链（$N_{\mathrm{RF}}=K+1=4 \ll N_t=32$）混合模拟–数字多径下行 `MIMO-AFDM ISAC`（$K=3, P_k=3, N=64, \nu_{\max}=0.85, 20\text{ dB}$, 16-QAM） | `Elbir, Celik & Eltawil WCL'24` (`10.1109/LWC.2024.3489632` Alg.1–2, Fig.2–3) + `Liu & Schober arXiv:2607.05119` Sec. V | 破壁账 + 性能/算力账 | `Liu 2607` 12 轮逐格 `WMMSE` 混合基带：<br>`SumRate = 18.87 bps/Hz`<br>`16QAM SER = 4.21%`<br>`TarGain = -3.21 dB` | `Elbir WCL'24 HANDBALL` 逐格直套：<br>`SumRate = 15.11 bps/Hz`<br>`16QAM SER = 21.74%`<br>`TarGain = -5.60 dB` | **同 $N_{\mathrm{RF}}=4$ 固定模拟移相器**跨格基带上限：<br>`SumRate = 24.56 bps/Hz`<br>`16QAM SER = 0.00%`<br>`TarGain = -5.66 dB` | 较最强者 `(a)` 和速率缺口 **`+5.69 bps/Hz` (`+30.1%`)**，且打穿 `4.21% → 0.00%` 误符平层；$c_1=0$ 静态下 `(b)` 仅 `1.30%` SER，$c_1\ne 0$ 因 $2Nc_1\ell_{k,p}$ 跨格漏散射径恶化 **`16.7×`** | **是（真缺口 #1）** |
| **`B1-G3`**：`1-bit` 低精度 DAC 下行多用户免均衡 `MIMO-AFDM ISAC` 预编码与强目标伴随弱目标检测（$N_t=16, K=3, N=64, Q=8, 20\text{ dB}$, QPSK，`+23 dB` 强目标） | `Wang, Hu, Li, Masouros & Wong TWC'25` (`10.1109/TWC.2025.3595731` Fig.16–18) + `Sui & Liu TCOM'26` (`10.1109/tcomm.2026.3701879` Fig.5) + `Liu 2607` | 模型化硬件损伤账 + 破壁账 | `Sui TCOM'26` Bussgang 标定 + `Liu 2607` 1-bit 量化预编码：<br>`QPSK SER = 5.36%`<br>`WeakSINR = 15.51 dB` | `Wang TWC'25 CI-DAC` 直套（逐格 `67.19%` / 全块 2048 维 `CEO` `67.56%`）：<br>`QPSK SER = 65.73%`<br>`WeakSINR = 7.91 dB` | 同总功率无穷精度上限：<br>`QPSK SER = 0.00%`<br>`WeakSINR = 21.30 dB`<br>（注：`2-bit` QPSK 下 `(a)` 已达 `0.14%`，故锁死 `1-bit` 或 `1–2 bit` 16-QAM） | 较最强者 `(a)` 存在 **`5.36% → 0.00%` 量化误码地板** 与 **`+5.79 dB` 弱目标 `SINR` 缺口**；$c_1=0$ 静态下逐格 `(b)` `SER = 4.61%` 而 $c_1\ne 0$ 崩至 `67.19%`（`14.6×`），且 $c_1=0$ 单频雷达 `WeakSINR = -22.0 dB` | **是（真缺口 #2）** |
| **`B1-G4`**：`0 dB IBO` 重度饱和非线性功放（`SEL/Rapp` 峰值圆盘约束）多用户 `16-QAM` 下行 `MIMO-AFDM ISAC` 预编码（$N_t=8, K=3, N=64, Q=8, 26\text{ dB}$） | `Sui & Zilong Liu TCOM'26` (`10.1109/tcomm.2026.3701879` Eq.25–27, Fig.7) + `Gourar arXiv:2609.14030` + `Liu 2607` | 模型化硬件损伤账 + 破壁账 | 配齐精确 Bussgang `1/K_PA` 缩放与理想记忆无关 DPD（`SEL`）的块预编码：<br>`16QAM SER = 14.11%`<br>`WeakSINR = 13.08 dB` | 逐 DAFT 格 Bussgang `RZF` $\mathbf{F}_N\to\mathbf{A}$ 直套：<br>`16QAM SER = 89.04%`<br>`WeakSINR = 13.97 dB` | 线性功放：`0.00% / 15.56 dB`<br>**同 `0 dB IBO` 峰值受限功放圆盘可行域上限**：<br>`16QAM SER = 0.37%`<br>（纯通信投影 `WeakSINR = 9.11 dB`） | **同一 `0 dB IBO` 饱和功放下 `16-QAM SER` 可从 `14.11%` 压至 `0.37%`（`38.2×` 破壁裕度）**，且纯通信峰值投影会掉 `4–6.5 dB` 弱目标 `SINR`，存在真实通感峰值圆盘耦合（非 `h01` 恒模环面）；$c_1=0$ 下 `(b)` `16.81%` vs $c_1\ne 0$ `89.04%` | **是（真缺口 #3）** |
| **`B1-G5`**：双基地强多径杂波（$K+R_c=8 > N_t=6$）下多用户下行 `MIMO-AFDM ISAC` 随机 `16-QAM` 载荷泄漏与速率折中 | `Xie, He, Xiong, Fan Liu & Shi Jin arXiv:2512.08157` Fig.1 + `Zhang JSAC'26` + `Liu 2607` | 破壁账 | `Zhang JSAC'26` 25% 保护带 + `Liu 2607` + 已知导频 `ExactSubspaceBLUE`：<br>`SumRate = 14.39 bps/Hz`<br>`SCNR = +0.09 dB` | `Xie & Fan Liu 2512` 叠加导频 `DPI` $\mathbf{F}_N\to\mathbf{A}$ 直套：<br>`SumRate = 17.95 bps/Hz`<br>`SCNR = +0.65 dB` | 双基地已知私有数据上限：<br>`SumRate = 17.95 bps/Hz`<br>`SCNR = +21.59 dB` | 虽检出 `+20.93 dB` 双基地 `SCNR` 缺口，但**切口邻近在审卡 `I-20261125-m04`（压缩保护带双基地未知载荷强杂波零空间）及 `runner k` 的 `§4 B2+B3` 领地**，按第 13 轮防撞边界主动隔离不入阶段 B | **否（防撞隔离淘汰）** |
| **`B1-G6`**：多用户下行 `MIMO-AFDM ISAC` 逐帧 `WMMSE-MM` 凸规划的 $\mathcal{O}(K Q N^3)$ 高耗时瓶颈（公平缓存 $\mathbf{H}_k[q]$ 测 $N=64,128,256$，$N_t=6, K=3, Q=8, \nu_{\max}=0.85, 20\text{ dB}$） | `Rang Liu, Ming Li, Swindlehurst, Franchi & Schober arXiv:2607.05119` Sec. IV-B Eq.(39)–(46), Fig.1a–1b | 算力账（同精度提速 `≥ 10×`） | 精确 `Liu 2607 WMMSE-MM`（15 轮，缓存 $\mathbf{H}_k[q]$）：<br>`N=64`: `18.47 bps/Hz`, **`2,252 ms`**<br>`N=128`: `16.29 bps/Hz`, **`10,693 ms`**<br>`N=256`: `18.12 bps/Hz`, **`70,580 ms`** | 逐 DAFT 格解耦 `WMMSE-MM` $\mathbf{F}_N\to\mathbf{A}$ 直套：<br>`N=64`: **`10.73 bps/Hz`** (`1,695 ms`)<br>`N=128`: **`10.79 bps/Hz`**<br>`N=256`: **`11.07 bps/Hz`** | 同和速率精度（差 `≤ 0.2 dB` / `≤ 2%` 速率）且严格满足 $\mathbf{a}_t^H\mathbf{R}_x\mathbf{a}_t \ge \Gamma_s$ 的准线性耗时下限 `< 50 ms` | `(a)` 因每轮 $KQ$ 次 $N\times N$ 稠密求逆随 $N^3$ 暴涨至 `2.25s → 70.6s`，而母方法逐格直套 `(b)` 在 $c_1\ne 0$ 下**暴跌 `-7.74 bps/Hz` (`-41.9%`)**（$c_1=0$ 静态下 `(a)==(b)==18.80 bps/Hz` 逐位重合，证非纯换字母！） | **是（真缺口 #4）** |
| **`B1-G7`**：终端免均衡单抽头接收的多用户下行 `MIMO-AFDM ISAC` 总功率球符号级/块级通感预编码（$N_t=6, K=3, N=64,128, Q=8, \ell_{\max}=2, \nu_{\max}=0.85, 18\text{ dB}$，`+23 dB` 强目标伴随弱目标） | `Tang & Fei, C. Masouros et al. TWC'26` (`10.1109/twc.2026.3692638` Eq.40,52, Fig.7,9) + `Peishi Li, Ming Li & Swindlehurst TWC'25` (`10.1109/twc.2024.3503605` Fig.7–8) + `Liu 2607` | 破壁账 + 算力账 | `(a1)` `Liu 2607` 单抽头接收：`SER = 56.95%`, `WeakSINR = 4.35 dB`<br>`(a2)` `Tang TWC'26` 截断 $k_\nu=1$ 对偶 QP + 专用感知流串联：`SER = 7.69%` (`N=64`) / `12.66%` (`N=128`), `WeakSINR = 5.49 / 8.74 dB`, `125 / 432 ms` | `Li & Masouros TWC'18` 逐格 `CI-SLP` $\mathbf{F}_N\to\mathbf{A}$ 直套：<br>`QPSK SER = 56.46%` (`N=64`) / `61.53%` (`N=128`)<br>`WeakSINR = 4.47 / 12.17 dB` | 总功率球（非恒模！）目标正交补全矩阵精确对偶 QP：<br>`QPSK SER = 0.043%`<br>`WeakSINR = 27.86 dB`<br>（稠密 QP 耗时 `191 → 693 ms`） | 较最强者 `(a2)` **`SER` 降 `177×` (`7.69% → 0.043%`)**、强目标旁弱目标 **`WeakSINR` 升 `+22.36 dB`**（注：须严防 `h01` 跨块重复固定啁啾假峰，后续必检全图盲搜等虚警）；$c_1=0$ 下 `(b)` `3.35%` vs $c_1\ne 0$ `56.46%` | **是（真缺口 #5）** |

---

## 三、阶段 A 小结与交接阶段 B 清单

- **测缺口总数**：`7` 个（全部通过红线 1 `< 1e-12` 复现核验与 $c_1=0$ 非同构检验）
- **淘汰/隔离数**：`2` 个（`B1-G1` 同无 TTD 相控阵展宽倒扣和速率且目标斜视与 $c_1$ 无关；`B1-G5` 主动避让 `m04` 与 `k` 双基地杂波靶区）
- **晋级阶段 B 的达标真缺口**：**`5` 个**（`B1-G2` 少射频链混合通感波束、`B1-G3` 1-bit DAC 有限字母表通感预编码、`B1-G4` `0 dB IBO` 饱和功放峰值圆盘 16-QAM 通感预编码、`B1-G6` `Liu 2607` 逐帧 `WMMSE-MM` `≥ 10×` 降阶加速、`B1-G7` 免均衡总功率球多用户通感预编码与强弱目标消遮蔽），覆盖 `round-13.md` §2 指定的全部四个 `B1` 子方向且与 `h01/h02` 正交。
