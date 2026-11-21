# 文献的数据不确定度建模逐式核对（Claude，2026-11-18，V 级）

问题（来自 [定位稿 v2](novelty-positioning-20261118.md) 第 0 节）：Mishra、Kanazawa、Zheng 对数据误差的处理，代数上是否等于"数据误差功率 × Σ|h_p|²"，即 `u‖h‖²` 型：一个随正在估计的 h 变化的各向同性坐标惩罚？若是，它们在字面上就属于我们的 A2 类。

## 原文出处
- Mishra et al.，"OTFS Channel Estimation And Data Detection Designs With Superimposed Pilots"，arXiv:2010.15066（IEEE TWC'21）。
  本次经 ar5iv HTML 读取（scratchpad，未入库）。
- Zheng et al.，"Channel Estimation for AFDM With Superimposed Pilots"，arXiv:2404.10232v1。
  本地：`.mission/20261007-sp-fractional-trans/raw/2404.10232v1.clean.txt`。
- Kanazawa et al.，"Superimposed Pilot-Based OTFS: Will it Work?"（arXiv:2501.15935）。
  本地：`.trellis/tasks/09-13-trans-next/research/ce-state-literature-v1/kanazawa-text.txt`。

## 逐篇

| 论文 | 字典几何 | 数据进字典的方式 | 数据误差建模 | 是否 `u‖h‖²` 型 |
|---|---|---|---|---|
| Mishra TWC'21 | **整数** tap：`τ_i = l_i/(MΔf)`，`ν_i = k_i/(NT)`，原文写"the integers l_i and k_i" | SP-NI：字典只含导频（式 15、20、23）。SP-I：硬判决 `argmax`（式 46）填 `Ω̂_d`（式 47–48） | 噪声加干扰为白噪声，`C = ((Σσ²_hi)σ_d² + σ_w²) I`（式 22）；迭代时为 `2(Σσ²_hi)σ_d² I + σ_w² I`（式 51）。由**先验**功率算出，是**常数** | 否 |
| Zheng（arXiv v1） | **整数**格点：`l_t`、`α_t` 由索引 t 取整得到（式 13–14） | 字典只含导频 `Φ_p`；数据通过干扰消除 `y − Ĥ_eff x̂_d` 扣掉（式 24） | `C_ŵ = ((Σσ²_hi)σ_d² + N0) I`（Lemma 2，式 18），先验常数 | 否 |
| Kanazawa | **整数**格点（原文第 160、457 行）；分数 Doppler 列为开放问题（第 587 行） | 不建字典回归：门限检测（式 22），增益靠导频位置平均（式 21） | 初始门限 `3√(N_p(σ² + σ_d²))`（式 24）；之后迭代改为 `3√(N_p σ²)`，去掉数据项（式 25） | 否 |

**补充（已在 11-18 预印本核对中 V 级读过）**：Y. Luo TCOM'26 是**分数**/离格字典，用硬判决重映射，误差设为 `β⁻¹ I_N`，不用软方差。

## 结论
1. 三篇都在整数格点上。按 D1，整数格点上同延迟块为 0，标量处理本来就没有我们指出的那一项误差。它们没有犯这个错，也不可能犯。
2. 三篇的数据误差都是由先验算出的常数白噪声，不随正在估计的 h 变化，**不产生拆分奖励**。
3. 已核实的唯一分数 Doppler SP 工作（Y. Luo）用硬判决，同样不是 `u‖h‖²` 型。
4. 所以 `u‖h‖²`（保留软迹的对角近似）**不是文献中任何一篇的字面做法**。它是"把软信息带进分数 Doppler 支撑获取时最自然的扩展"。在整数格点上，Wang TCOM'22 的期望 Gram 正好退化为这种对角形式，因此照搬过来是自然的。

## 对定位与计划的影响
- 定位稿 v2 第 0 节的判断**得到确认**。贡献按正面方式写："首次在分数 Doppler SP 支撑获取中正确使用译码软不确定度。最自然的对角扩展（在整数格点上精确）会结构性失败；`CODELAY` 是最小的正确形式。相对文献实际采用的硬判决做法，提前 1.3–5.3 dB。"
- **方向 B 取消**：没有文献接收机可以"放入 `CODELAY` 证明其近似有缺陷"。
- 未核：Zheng 的期刊版（TVT'25）是否扩展到了分数 Doppler，本次只读了 arXiv v1；投稿前做 citation audit。
