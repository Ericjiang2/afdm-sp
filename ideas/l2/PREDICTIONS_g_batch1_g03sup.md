# L2 Runner `g` 第 1 批补测：卡 `I-20261122-g03` 跨家族审计统计加固（2026-11-22 03:16 冻结）

本文件仅装按 `claude-sonnet-4.6` 第 6 步独立推导审计（`ideas/reviews/g-claude-audit-g03-20261122.md`）对卡 `I-20261122-g03` 补充的三项验证（脚本 `ideas/l2/g_l2_g03sup.py`，输出 `ideas/l2/out_g1_g03sup/`）：
1. **将空假设标定帧数从 400 帧扩充 5 倍至 `2000` 帧**（`seeds 50000..51999`），并在 `500` 帧全新空假设检验集（`seeds 52000..52499`）上检验全臂实测虚警率对称性（消除 400 帧标定时 `0.03 vs 0.00` 的分位数抽样波动）。
2. **补充无需估计 $\sigma_0$ 的硬判决副本对消臂 `afdm_hard_sign`**：$e_n = r_n - [\mathrm{sign}(\Re(\hat{g}_0 x_n)) + j\,\mathrm{sign}(\Im(\hat{g}_0 x_n))]$（仅用 Bussgang 相位 $\hat{g}_0 = e^{j\arg\langle \mathbf{x},\mathbf{r}\rangle}$），检验本文新推四级闭式常数定律：
   $$\mathrm{FIM/SNR}_{\text{asymp}}: \quad \text{Bussgang } 1.755 N \;\ll\; \text{Hard-Sign } 1.000\frac{N}{\sigma} \;<\; \text{Cond-Mean } \sqrt{2}\frac{N}{\sigma}\;(+1.505\text{ dB}) \;<\; \text{Probit } 1.4413\frac{N}{\sigma}\;(+1.587\text{ dB}).$$
3. **补充 1 比特稀疏恢复基线 `afdm_biht`**（2 步贪婪二元迭代硬阈值 / 符号投影追踪：先消去强直达径硬符号，再在候选平面匹配恢复弱目标）。

### 跑前判据与预测
- **实现门**：`500` 帧独立空假设集上全部受检臂在 `25 dB` 的虚警率均落在 `[0.002, 0.024]`（围绕 `0.010` 对称）。
- **主判据**：在全新 `300` 帧留出集（`seeds 60000..60299`）与加密 `2 dB` 步长 `WSR in {-18,-20,-22,-24,-26,-28,-30,-32,-34} dB` 上，`afdm_probit` 池化命中率相对 `afdm_bussgang` 与 `afdm_biht` 均高出 $\ge +25\text{ pp}$，且 `MDR_50` 排序满足 `afdm_probit ≈ afdm_cmean < afdm_hard_sign < sc_cphase_probit < afdm_bussgang`（其中 `afdm_probit` 领先 `afdm_hard_sign` 约 `1.2–1.9 dB`，领先 `sc_cphase_probit` 约 `2.1–2.7 dB`）。
- **跑前预测**：`PASS = 0.90, KILL = 0.05, UNDETERMINED = 0.05`。
