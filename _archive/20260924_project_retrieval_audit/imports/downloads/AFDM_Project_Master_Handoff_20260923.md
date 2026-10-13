# AFDM-SP 项目总会话交接文档
## 截止 2026-09-23：TF+CSTATE 主线已闭合到 prospective receiver evidence；CGR 出现真实行为信号但机制未闭合

> 用途：交接当前长会话全部有效状态，供新的 ChatGPT / xHigh / Codex / GPT Pro 会话直接继续。  
> 原则：**不要重新从 whitening / F2-P / list / early I1 / generic DL 等旧路线开始搜索。**  
> 当前 paper 的强 fallback 已经是 **TF+CSTATE**；新的研究探索必须以此为最强现有接收机，而不是以早期 OMP / I0 / TF-only 为基准。

---

# 0. 一句话状态

当前最强 receiver：

> **Native Tensor-Free Joint Coded SP-AFDM + syndrome-triggered CSTATE global structural reopening**

可以理解为两层：

1. **TF：within-model inference**  
   在固定 physical hypothesis set \(\mathcal S\) 内联合更新 data / gain / decoder information。

2. **CSTATE：model-space correction**  
   当 decoder 失败（nonzero syndrome）时，重新开放 physical model space：
   \[
   \mathcal S ightarrow \mathcal S'
   \]
   允许 global path replacement，再 local refinement，随后 TF20 + LDPC50 continuation。

当前论文已经不再只是“PBiGAMP-like inference 在 AFDM 上的 tensor-free 实现”，而是：

> **低状态 joint inference + 条件触发的 physical-model reopening + 完整 reliability/computation evidence。**

---

# 1. 当前论文最准确的贡献定位

## 1.1 TF 的真实 surviving novelty

TF 不是新的 AMP family，也不是新的 Turbo principle。

最准确的定位：

> **AFDM/CPP full-fractional physical-path operator 上，对声明 scalar bilinear joint inference map 的 low-state / tensor-free computational specialization。**

核心结构：

- full fractional physical paths；
- exact AFDM/CPP path action；
- coded finite-alphabet variables 保留在 AF domain；
- observation-unitary equivariance；
- forward / gain-adjoint / data-adjoint / scalar contractions 用 physical path structure 实现；
- inner work 约
  \[
  O(NP+N\log N+P^2)
  \]
  而不构造 dense \(P	imes N	imes N\) path tensor。

必须主动承认 prior art：

- P-BiG-AMP / bilinear AMP；
- AFDM PBiGaBP / JCED；
- fast/matrix-free structured PBiGAMP；
- time-/dual-domain AFDM inference；
- continuous-Doppler PBiGAMP-like methods；
- Turbo coded JCED。

因此 TF 的创新类型是：

> **application-specific structured inference / computational specialization**

而不是 general inference theory。

## 1.2 CSTATE 新增了什么

最初 TF 的一个重要 architecture limitation 是：

> \(\mathcal S\) 一旦由 acquisition / refinement 选定，后续 TF 主要只能更新 \(h,d,\mathrm{LLR}\)，不能有效地重新开放 physical hypothesis set 本身。

A+B+C 生产机制实验发现：

- 多跑 TF（J40R2 / J20R3）只能救少量 selected failures；
- true geometry 能救绝大多数 selected failures；
- full true \(H\) 相比 true geometry 只多救极少；
- 单纯扩大 Doppler local window 没有新增 rescue；
- global model-space freedom 是真实高杠杆。

于是先做了昂贵 classical control **GLOBAL20**：

\[
\mathcal S ightarrow \mathcal S-\{i\}+\{a\}
\]

在整个 finite physical candidate bank 上允许最多两次 global replacement。

GLOBAL20 的作用是**诊断 control**，不是“新方法”。

它证明：

- LOCAL20：10/43 triggered failures 被救回；
- GLOBAL20：31/43 被救回；
- 旧 23 个“加迭代/加轮次也救不回”的困难帧中 GLOBAL 救回 15；
- success controls 无 harm。

但 GLOBAL20 branch 太贵。

### CSTATE

Pro 随后推导了 GLOBAL20 的 exact compact realization。

冻结 decoder APP moments 后，structural objective：

\[
Q(h,\mathcal S)
=
\|y-Bh\|^2+h^H\Gamma h+\lambda\|h\|^2
\]

维护 compact state：

\[
A=B^HB+\Gamma+\lambda I,\qquad
b=B^Hy,\qquad
C=A^{-1},\qquad
h=C b.
\]

用 Schur/inverse-Gram identity 精确计算 all-pair replacement objective，并利用 AFDM/CPP shift-phase structure 批量计算 candidate sufficient statistics。

重要性质：

- 同一个 finite bank；
- 同一个 structural objective；
- 同一个 tie rule；
- CSTATE 与 GLOBAL20 的 replacement / top ranking / final bits **exactly matched within tolerance**；
- CSTATE 不是 heuristic top-K approximation。

生产验证：

- GLOBAL / CSTATE：31/43 rescues 一致；
- old-23：15/23 一致；
- controls：0 harm；
- CSTATE branch mean 0.241 s，GLOBAL 0.665 s；
- CSTATE structural exchange 本身约 26.3 ms。

因此 CSTATE 的真实定位：

> **一个对 high-value global structural reopening 的 exact compact AFDM/CPP-specific realization。**

它的 support-replacement / Schur / inverse-Gram ancestry是经典的，因此不能 claim 新 general support inference。

---

# 2. 最终 fresh prospective TF+CSTATE 结果

## 2.1 Fresh population

最终 frozen TF vs TF+CSTATE prospective campaign：

- 6 / 6.5 / 7 dB；
- 每点 1024 fresh independent observations；
- 总计 3072；
- 两臂 paired；
- 6.5 dB 为 preregistered primary confirmatory cell；
- TF+CSTATE：TF syndrome=0 则直接保留 TF，nonzero syndrome 才触发 frozen CSTATE20。

## 2.2 FER

| SNR | TF FER | TF+CSTATE FER | rescues / harms |
|---|---:|---:|---:|
| 6 dB | 206/1024 = 20.12% | 61/1024 = 5.96% | 145 / 0 |
| **6.5 dB primary** | **40/1024 = 3.91%** | **6/1024 = 0.59%** | **34 / 0** |
| 7 dB | 20/1024 = 1.95% | 5/1024 = 0.49% | 15 / 0 |

6.5 dB：

\[
\Delta FER=-3.32	ext{ percentage points}
\]

preregistered conservative one-sided 95% upper bound：

\[
-1.95	ext{ percentage points}<0.
\]

因此 numerical primary criterion 明确通过。

Fresh sample 中：

- 0 harms；
- 0 numerical fallbacks；
- 0 undetected information-word errors；
- 0 zero-syndrome wrong cases。

这些只能称为 sample observations，不可 universalize。

## 2.3 Latency

6.5 dB：

- TF mean complete latency：328.5 ms；
- TF+CSTATE：337.5 ms；
- population mean extra：9.05 ms/frame；
- trigger count：40/1024；
- triggered extra mean：226.6 ms；
- nontriggered extra：0.21 ms。

0.5 s deadline：

- TF：40 system failures；
- TF+CSTATE：10；
- 34 eventual rescues 中 30 个在 0.5 s 前 ready。

因此当前 receiver 的 computation-adaptive story 已得到真实 population-level支持：

> easy frames 只付 TF 成本；hard frames 才付 structural rescue 成本。

---

# 3. Prospective evidence 的程序性 qualification

必须保留，不能隐去。

原 unattended analyzer 在**打开 truth 之前**因为 preregistered Git-binding receipt 多了一个 descriptive `verification` field 而退出并标记原 pipeline `invalid`。

之后：

- 用户明确授权离线 recovery；
- recovery analyzer 只接受那个确定的第五字段和值；
- 没有新 observation；
- 没有新 receiver call；
- receiver/source/statistical formula 均没改；
- observed seal 已在 truth access 前提交；
- independent verifier 重新计数并完全一致。

因此当前正确措辞：

> numerical primary criterion passes on the original sealed fresh population, **with a procedural qualification**.

不能写：

> clean one-shot prospective completion exactly as preregistered.

---

# 4. Hostile novelty/stop audit

## 4.1 “允许更新初始 \(\mathcal S\)”本身不新

成熟祖先包括：

- CoSaMP / Subspace Pursuit；
- OMPR；
- Stepwise Optimal Subspace Pursuit；
- OLSR/IOLSR；
- sequential add/delete sparse Bayesian methods；
- NOMP；
- JCCD-VALSE；
- decoder-aided / data-aided off-grid channel estimation；
- recent AFDM data-aided dynamic grid methods。

因此禁止 claim：

- first support replacement；
- first decoder-aided geometry refinement；
- first data-aided support correction；
- first adaptive delay-Doppler update。

CSTATE 的可防守 delta 是：

> coded full-fractional SP-AFDM 中，用 decoder APP moments 定义 fixed-\(q\) structural objective，并利用 AFDM/CPP operator algebra 将 global all-pair replacement 精确压成 compact low-cost structural state，使 model-space reopening 可以实际嵌入 TF receiver。

这是**structured realization / receiver construction**，不是 fundamental new support-inference principle。

## 4.2 当前 paper 相比 TF-only 明显增强的原因

TF-only 最大风险：

> “generic bilinear inference 的 AFDM-specific implementation。”

现在 paper 至少有：

1. within-model TF inference；
2. model-space CSTATE correction；
3. decoder-triggered conditional computation；
4. production mechanism interventions；
5. fresh FER / latency / deadline evidence。

因此整体更接近：

> **完整 computation-adaptive coded receiver architecture**

而非单一快速 inference kernel。

普通 TCOM/Transactions 级别目前已经进入现实投稿区间，最大的风险是 novelty positioning 过度而不是“没有任何贡献”。

---

# 5. 深度学习位置

当前 TF+CSTATE paper **不建议为了 AI 而加入 DL**。

已经很弱/没必要的 DL 方向：

- learned trigger（syndrome 已很干净）；
- learned CSTATE candidate ranking（解析 objective 已经便宜且有效）；
- trainable damping / step size；
- end-to-end AFDM DNN；
- 学 exact physical operator。

真正可能有后续研究价值的 DL 土壤：

1. **code-correlation-aware structural evidence residual**  
   CSTATE 使用 symbol-level moments \((\mu,V)\)，可能丢掉 LDPC 跨符号 correlation。

2. **model mismatch residual learning**  
   fractional delay / pulse shaping / drift / hardware mismatch 时 analytical physical model 不再 exact。

3. 更复杂 multi-rescue regime 下的 computation-control policy。

原则：

> **只学习解析模型已证实近似不好的部分，不让网络重学 exact AFDM physics。**

---

# 6. Research Discovery Pack 状态

已构建 `PRO_PACK.zip`：

- 约 11 MB；
- 3072 fresh frame table；
- 72 fresh remaining failures；
- rescued / easy-success controls；
- CSTATE landscape summaries；
- truth diagnostics；
- negative-results ledger；
- cold archive索引。

真正重 raw arrays 留在 cold archive，按 hypothesis 定向抽取。

Fresh TF+CSTATE 后 remaining failures：

- 6 dB：61
- 6.5 dB：6
- 7 dB：5

总计：

\[
72
\]

这些是最值得继续研究的 failure population。

---

# 7. Pro 上一轮替代 inference 尝试：已否决

## 7.1 Joint code-constrained profiled likelihood / ADMM JCDD

Pro 推导过：

> **joint code-constrained profiled likelihood + LDPC parity-polytope consensus / ADMM**

核心：

\[
\min_{b\in \mathcal C,h}
\|y-B_	heta(b)h\|^2+h^HRh
\]

消掉小维 gain，再对 relaxed bits 做 majorization / consensus。

否决原因：

- closest art 已有 bit-level JCDD + channel elimination + penalized polytope + majorized ADMM + deep unfolding；
- JCCD-VALSE 已有 coded soft information + continuous channel/support inference；
- toy experiment 显示 continuous relaxation lower objective 并不自动给出 cheap valid codeword；
- integrality penalty 可锁住 wrong endpoint。

因此不要继续这条路线，除非发现新的 failure-critical operation，而不是换 AFDM operator。

---

# 8. 最新研究候选：CGR（Coherence-Complete Gain Reaction）

## 8.1 动机

CSTATE 允许：

> **same delay + multiple close Dopplers**

这在旧 distinct-delay refinement regime 中不常出现。

Physical operator Gram：

\[
R_{ij}
=
rac1N\operatorname{tr}(U_i^HU_j)
=
\mathbf 1_{l_i=l_j}D_N(
u_j-
u_i).
\]

distinct-delay：

\[
R=I.
\]

same-delay / close Doppler：

\[
|R_{ij}|pprox 1
\]

可发生。

当前 TF gain reaction：

\[
-lpha Nv_xar h.
\]

CGR：

\[
oxed{
-lpha Nv_xar h
ightarrow
-lpha Nv_xRar h
}
\]

只改这一项。

其余 TF/CSTATE/decoder 全不动。

distinct delays：

\[
R=I\Rightarrow CGR=TF
\]

exactly。

复杂度：

\[
O(P^2)
\]

额外 matvec。

---

# 9. CGR reference / synthetic evidence

独立 reference probes 中：

### N=1024 same-delay doublet
- scalar：37/128 errors
- CGR：34/128
- 3 rescues / 0 harm

### same-delay triple
- scalar：42/128
- CGR：38/128
- 4 rescues / 0 harm

### wrong-phase sham
- 47/128
- 0 rescue / 10 harm

说明 aligned orientation 可能重要，但 effect modest。

CGR algebra 本身并不全新：

- P-BiG-AMP pre-scalarization 中有 cross-reaction ancestry；
- 项目旧 coherent/block implementation 已存在类似/更完整 terms。

所以它的潜在科研价值不在“首次写出 \(Rar h\)”，而在：

> CSTATE 改变 physical geometry regime 后，旧 scalar TF closure 是否出现 failure-critical coherence incompatibility，以及 minimal deterministic coherence completion 是否能比 richer block inference 更有效。

---

# 10. 最新 CGR 25×4 production test

固定 25 observations、四臂：

- BASE
- CGR
- SHAM
- BLOCK

结果：

| Arm | correct /25 | target BASE failures rescued | harms |
|---|---:|---:|---:|
| BASE | 14 | 0 | 0 |
| **CGR** | **18** | **4/8** | **0** |
| SHAM | 11 | 0 | 3 |
| BLOCK | 7 | 0 | 7 |

其他重要事实：

- CGR rescues：4/8 target failures；
- 0 harm；
- SHAM 无 target rescue + 3 harms；
- BLOCK 无 target rescue + 7 harms；
- distinct-delay controls：CGR/SHAM 与 BASE detector fields / final bits exact identical；
- CGR branch cost 与 BASE 基本相同；
- terminal CGR physical mismatch 在 4 个 rescues 上均低于 BASE。

---

# 11. 但原 CGR mechanism gate 没通过

原机制故事隐含：

> 被漏掉的 deterministic coherence reaction 应该在 saved 20-step trajectories 中表现为 truth-improving physical direction。

实际：

- 每个 rescued frame 的 one-step signed physical effects 在不同 iterations 中正负都有；
- 累计 signed effect 甚至为负；
- 因此 preregistered / frozen mechanism continuation 5 gates 只过 4 个；
- machine report：
  `candidate_pass=false`.

这不能解释成 CGR“没用”。

但必须解释成：

> **behavioral effect 有强信号；原 one-step physical-descent mechanism 未建立。**

当前禁止：

- 直接 fresh CGR；
- 扩 cohort；
- retune；
- 改 gate；
- 直接宣称 coherence mechanism proven。

---

# 12. 当前对 CGR 的正确解释

CGR **不能**被描述成：

> “已证实 scalar TF 忽略 same-delay coherence，CGR 每一步把 channel 拉向 truth，因此救回 frame。”

该机制没有闭合。

但也不能简单 kill：

- 4/8 rescues；
- 0 harm；
- SHAM 反向伤害；
- BLOCK 更差；
- distinct-delay exact identity；
- cost 几乎不变。

因此最新科研状态：

> **CGR 有真实 behavior-level effect，但最初的 one-step physical-descent mechanism 不成立/未闭合。**

可能需要重新解释其作用，例如：

1. trajectory / basin effect，而非每步 monotonic physical descent；
2. true channel mismatch 不是 TF coupled dynamics 的 Lyapunov function；
3. \(Rar h\) 在校准 approximate pseudo-observation / reaction，而不是做 truth gradient descent；
4. aligned phase consistency 改变 data/gain/decoder trajectory；
5. minimal deterministic reaction correction 比 full BLOCK uncertainty 更匹配当前 damping / scalar information flow。

这些只是候选解释，不能作为已证事实。

---

# 13. 当前下一步（最重要）

## 不要做

- 不要 fresh prospective CGR；
- 不要扩大 target cohort；
- 不要调 \(R\)；
- 不要改 damping；
- 不要 CGR-v2；
- 不要改变 gate；
- 不要直接把 CGR 写成 contribution。

## 应该做

**回 GPT Pro 重新做机制推理。**

建议给 Pro 的核心问题：

> The bounded CGR experiment shows a strong behavioral effect but failed the preregistered physical-direction mechanism gate. Re-derive what the \(Rar h\) reaction is actually doing in the coupled TF/data/decoder dynamics. Explain why aligned CGR rescues while wrong-phase SHAM and richer BLOCK inference hurt, despite non-monotone one-step physical-direction effects. Do not defend the old mechanism automatically. Use existing saved traces first. Only request a new bounded Codex test if you can derive a specific falsifiable revised mechanism.

目标不是“救 CGR”，而是：

\[
oxed{
	ext{behavior}
ightarrow
	ext{new mechanism hypothesis}
ightarrow
	ext{mathematical derivation}
ightarrow
	ext{minimal falsification}
}
\]

如果没有 coherent mechanism，则将 CGR 降级为 empirical patch 并停止。

---

# 14. 项目整体 stop / continue 判断

## 当前 TF+CSTATE paper

已经有足够强的主线，**不需要 CGR 才能投稿**。

当前 paper 的方法搜索可以认为：

> **可停止；TF+CSTATE 是强 fallback / 主稿。**

CGR 是额外 research branch，不应阻塞当前文章。

## 后续研究

仍有潜力。

尤其：

- 72 fresh post-CSTATE remaining failures；
- code correlation；
- frozen-\(q\) structural objective；
- model order / split-merge；
- communication-risk-aware geometry；
- residual model mismatch；
- CGR 暴露的 “structural reopening 改变下游 inference regime” 问题。

---

# 15. 推荐 AI 研究工作流

## 网页 GPT-6 Pro
Research Lead：
- 找问题；
- 第一性原理；
- 新方法；
- novelty adjudication；
- decisive experiment。

## 网页 GPT-6 xHigh
Chief of Staff / Red Team：
- 压缩 evidence；
- 制作 Decision Packet；
- 攻击 Pro 方法；
- 管理 research ledger；
- 决定是否值得调用 Astra。

## Codex Astra
Theory ↔ Code Scientist：
- 高风险新方法的 equation-to-source reconciliation；
- exact teacher；
- production interface；
- 最小 causal test。

## Codex Sol
Research Engineer：
- 实现；
- 实验；
- profiling；
- statistics；
- evidence audit。

## Codex Luna
Research Assistant：
- export；
- hash；
- recount；
- CSV/parquet；
- manifest；
- 独立机械复核。

高智商 token 原则：

> **只花在“研究树往哪长”的节点。**

---

# 16. 下一会话必须记住的红线

1. **TF+CSTATE 已经是强现成 receiver，不得回退到旧 OMP/I0 当新方法基线。**
2. **CSTATE 的 support replacement 思想不是 general novelty。**
3. **CGR behavior 有信号，但 mechanism 未闭合，当前 candidate_pass=false。**
4. **不能因为 CGR 4/8 rescue 就直接做大规模 prospective。**
5. **BLOCK 更丰富却更差，是值得解释的现象，不等于“block inference 永远不好”。**
6. **truth mismatch 不是已证明的局部 Lyapunov function。**
7. **所有新探索必须与当前 strongest TF+CSTATE 比，且优先解释 fresh post-CSTATE failures。**
8. **DL 只能用于已证解析 gap，不要为了 AI 加网络。**
9. **当前 paper 不应被新探索无限拖延。**
10. **如果新方法没有明确 mechanism + closest-art delta + bounded falsification，不进入 production。**

---

# 17. 当前最简决策树

```text
TF+CSTATE 主稿：已成立，可继续写稿 / 做必要 publication hygiene
        |
        +-- CGR research branch
                |
                +-- behavior: YES (4/8 rescue, 0 harm)
                |
                +-- original physical-direction mechanism: NOT ESTABLISHED
                |
                +-- next: Pro re-derive mechanism
                         |
                         +-- coherent revised mechanism survives
                         |       -> one bounded Codex falsification
                         |
                         +-- no coherent mechanism
                                 -> downgrade CGR to empirical patch, STOP
```
