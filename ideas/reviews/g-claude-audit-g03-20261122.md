# Step 6 Independent Derivation & L2 Audit — `I-20261122-g03` (`claude-sonnet-4.6`, 2026-11-22)

- Scope: Independent cross-family verification of asymptotic Fisher/SNR constants and L2 readout for `I-20261122-g03` (run via `claude -p --no-session-persistence --model sonnet` per `round-agy.md` §6 while Codex quota resets at 06:23).

---

**结论**：三组常数的渐近推导方向都对，但 (a) 的数值应为 1.4413 而非 1.4464，对应 (b) 的差距是 0.082 dB 而非 0.098 dB；(c) 的 2.486 dB 精确成立。L2 的 PASS 结论成立，但卡面有四处需要在放行前改正。

## 1. 独立重推

**共同起点**：每个实维度的比特满足 $P(s=+1)=\Phi(u+a\theta/\sigma_0)$，其中 $\theta$ 是弱径幅度，$a$ 是弱径模板系数，$u=\Re(g_0x)/\sigma_0$。单样本 Fisher 信息为 $(a/\sigma_0)^2\,\phi^2(u)/[\Phi(1-\Phi)]$。该因子在 $|u|\lesssim 2$ 之外指数衰减，所以只有过零窄层有贡献，总信息 $\approx$ (模板能量 $A$)·$p_U(0)\,\sigma_0\cdot I_0/\sigma_0^2$。这里 $I_0=\int\phi^2/[\Phi(1-\Phi)]\,dt$，$p_U(0)$ 是未归一化实分量 $\Re(g_0x)$ 在 0 处的密度。

**(a) 逆 Mills 比 Probit，$C_0$**

- 高斯多载波的 $p_U(0)=1/\sqrt\pi$，所以信息 $=A\theta^2 I_0/(\sqrt\pi\,\sigma_0)$。用 $\sigma=\sqrt2\sigma_0$ 换算后，与卡的 $C_0=\sqrt{2/\pi}\,I_0$ 同构，公式本身正确。
- 数值积分得 $I_0=1.8064$，所以 $C_0=1.4413$，卡里的 1.4464 偏高 0.35%。
- $\int\Phi(1-\Phi)\,dt=1/\sqrt\pi$ 已验证。

**(b) 未加权条件均值对消**

- 对 $e=s-(2\Phi(u)-1)$：均值偏移是 $2\phi(u)a\theta/\sigma_0$，条件方差是 $4\Phi(1-\Phi)$。
- 做平均得 $E[2\phi]=2\sigma_0/\sqrt\pi$ 和 $E[4\Phi(1-\Phi)]=4\sigma_0/\pi$，代入得效用 $=A\theta^2/\sigma_0$，换算成 $\sigma$ 为 $\sqrt2/\sigma$。"效用常数 $\sqrt2$"成立。
- 与 Probit 的比是 $1.0191$，即 **0.082 dB**。卡里的 0.098 dB 是 1.4464 带来的，应改。
- 与 L2 对照：MDR_50 的实测差是 0.057、0.19、0.006、0.033、0.055 dB（15/20/25/30/35 dB），平均约 0.07 dB，方向和量级一致。
- 池化命中率差 0.70 pp（CI [0.15, 1.22]）与理论预期 0.5–0.9 pp 吻合，这才是最干净的一致性证据。
- 稳妥表述：**"二者在统计上近乎等价，渐近差约 0.08 dB，实测与之相容"**。

**(c) 连续均匀相位恒模，反正弦分布**

- $p_U(0)=1/\pi$，信息比 $=\pi/\sqrt\pi=\sqrt\pi$，即 **2.486 dB**，精确成立。
- 实测 MDR_50 的 `sc_cphase` 与 `afdm_probit` 差为 2.39、**3.07**、2.22、2.33、2.07 dB，均值 2.42 dB。
- 反正弦的过零饥饿线更早：$N=1024$ 时约 33.3 dB，而高斯约 38.2 dB。35 dB 一档的 cphase 已进入饥饿区，所以 35 dB 处 2.07 dB 偏小是预期方向。

## 2. 需要在放行前收紧或修正的地方

1. **机制归因**：0 dB PAPR 的连续相位恒模（`sc_cphase`）在 CNR ≥ 20 dB 时 MDR_50 比 AFDM+Bussgang 好约 3–6 dB，比 Probit 只差 2.4 dB。因此失明来自**离散 QPSK 星座导致的零点距离**，与包络是否恒定无关。核心控制量应改写为**门限过零密度 $p_U(0)$ 与奇次谐波的条件零化**，删除"严禁选用恒模单载波"。
2. **"指数失明"在帧平均下不成立**：随机载波相位 $\phi_0$ 下部分帧偶发贴近零点，帧平均命中率呈代数衰减（实测 14%），应改为"固定非轴向相位下指数失明、随机相位下帧平均代数退化"。
3. **区分主旁瓣信噪比斜率（$+5\text{ dB/decade}$）与检测门限 `MDR_50` 斜率（受过零饥饿弯折影响实测约 $3.9\text{ dB/decade}$）**。
4. **正文过零饥饿上界公式统一更正为 $N^2/(50\pi)$（$N=1024$ 约 $38.2\text{ dB}$，$N=4096$ 约 $50.3\text{ dB}$）**。

## 3. 建议补充对照（已纳入 `g03_sup` 补跑）

- 将空假设标定帧数提升至 $\ge 2000$ 帧以压低 1% 分位门限抽样方差；
- 补充无需估计 $\sigma_0$ 的**硬判决副本对消** $e_n = s_n - \mathrm{sign}(\hat{u}_n)$（理论渐近效用 $1.000\,N/\sigma$，比条件均值 $\sqrt{2}\,N/\sigma$ 低 $1.505\text{ dB}$）及 1 比特稀疏恢复 `BIHT` 对照臂。
