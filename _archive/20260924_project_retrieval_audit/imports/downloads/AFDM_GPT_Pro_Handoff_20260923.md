# GPT Pro 专用科研交接
## 截止 2026-09-23：TF+CSTATE 已是强 frozen fallback；CGR 出现真实 rescue 信号但原机制未闭合

> 供新的 GPT Pro 会话直接继续。  
> 目标不是重走项目历史，而是从最新 mixed CGR result 继续做**机制重导 / method discovery**。  
> 当前主稿并不依赖 CGR；因此没有压力去“救 CGR”。

---

# 1. 当前 strongest receiver

当前 frozen strongest receiver：

> **TF+CSTATE**

结构：

1. native tensor-free coded SP-AFDM TF；
2. decoder syndrome trigger；
3. compact exact global structural reopening（CSTATE）；
4. local refinement；
5. TF20 + LDPC50 continuation。

TF 负责：

\[
(h,d,\mathrm{LLR})\mid\mathcal S
\]

CSTATE 负责：

\[
\mathcal Sightarrow\mathcal S'
\]

因此当前 architecture：

> **within-model inference + conditional model-space correction**

---

# 2. Final fresh evidence

| SNR | TF FER | TF+CSTATE FER | rescues / harms |
|---|---:|---:|---:|
| 6 dB | 206/1024 | 61/1024 | 145 / 0 |
| **6.5 dB primary** | **40/1024** | **6/1024** | **34 / 0** |
| 7 dB | 20/1024 | 5/1024 | 15 / 0 |

6.5 dB：

\[
\Delta FER=-3.32	ext{ pp}
\]

registered one-sided conservative 95% upper bound：

\[
-1.95	ext{ pp}<0.
\]

Mean complete latency：

- TF 328.5 ms
- TF+CSTATE 337.5 ms
- +9.05 ms/frame

0.5 s deadline：

- TF 40 failures
- TF+CSTATE 10

结论：

> TF+CSTATE 已经是强 receiver-level baseline，不是待救方法。

程序性 qualification：原 unattended analyzer 因 receipt schema mismatch 在 truth access 前退出；authorized offline recovery 用原 sealed population 完成，无新 receiver calls，独立 verifier一致。因此 numerical result 强，但不是 unqualified clean one-shot completion。

---

# 3. Novelty boundary

## TF
不是新 AMP。

定位：

> AFDM/CPP full-fractional operator 上 scalar bilinear inference 的 low-state / tensor-free specialization。

## CSTATE
support replacement / Schur / inverse-Gram / add-delete ancestry 都是经典。

定位：

> coded soft moments + full-fractional AFDM structural objective + exact compact global replacement realization。

当前 paper 的创新类型：

> **structured receiver construction + model-space mechanism + computation-adaptive architecture**

不是 fundamental new Bayesian law。

---

# 4. 已杀/降级路线

不要重新提出：

- passive whitening；
- propagated scalar \(v_h\) 主机制；
- extra TF iterations / rounds；
- wider local Doppler window；
- conditional→profile/marginal ranking reversal；
- Hessian negative-curvature escape；
- “fractional Doppler non-Gaussian ⇒ mixture detector”；
- product-bit approximation / BP-response 的简单 code-correlation替代；
- generic JCDD/ADMM + AFDM transplantation；
- generic learned SP receiver；
- support replacement / decoder-aided geometry refinement 作为 general novelty。

---

# 5. Research Discovery Pack

`PRO_PACK.zip`：

- 约 11 MB；
- 3072 fresh frame table；
- 72 post-CSTATE remaining failures；
- rescued/easy controls；
- CSTATE landscape summaries；
- truth diagnostics；
- negative ledger；
- cold archive references。

72 fresh remaining failures：

- 6 dB 61
- 6.5 dB 6
- 7 dB 5

新方法若继续探索，应优先解释这些强 receiver 后的 remaining failures。

---

# 6. 已否决 alternate inference

完整推导过：

> joint code-constrained profiled likelihood + LDPC parity-polytope ADMM/JCDD。

否决原因：

- closest art 已有 bit-level JCDD + channel elimination + polytope + majorized ADMM + deep unfolding；
- JCCD-VALSE 已有 coded soft info + continuous channel/support inference；
- toy relaxed solution不能自动 cheap readout合法 codeword；
- integrality penalty可锁 wrong endpoint。

不要重启此方向，除非有新的 failure-critical operation。

---

# 7. 最新 candidate：CGR

## 7.1 数学对象

CSTATE 可产生：

> same delay + multiple close Doppler paths。

Physical operator Gram：

\[
R_{ij}
=
rac1N\operatorname{tr}(U_i^HU_j)
=
\mathbf1_{l_i=l_j}D_N(
u_j-
u_i).
\]

distinct-delay：

\[
R=I.
\]

close same-delay：

\[
|R_{ij}|
\]

可接近 1。

TF gain reaction：

\[
-lpha Nv_xar h.
\]

CGR：

\[
oxed{
-lpha Nv_xar h
ightarrow
-lpha Nv_xRar h.
}
\]

只改这一项。

其他 TF/CSTATE/decoder 完全不动。

distinct delays：

\[
R=I\Rightarrow CGR=TF
\]

exactly。

额外 cost：

\[
O(P^2).
\]

## 7.2 Novelty ceiling

\(Rar h\) algebra 本身不新：

- pre-scalar P-BiG-AMP 有 cross-reaction ancestry；
- 项目旧 coherent/block implementation 已有类似/更丰富 cross terms。

潜在 scientific value 只可能来自：

> CSTATE 造成 previously absent coherent geometry regime，使旧 scalar closure 暴露出 failure-critical incompatibility，而 minimal deterministic coherence correction 可能优于 full block inference。

---

# 8. CGR reference evidence

Synthetic/reference：

### same-delay doublet
- scalar 37/128 errors
- CGR 34/128
- 3 rescues / 0 harm

### same-delay triple
- scalar 42/128
- CGR 38/128
- 4 rescues / 0 harm

### wrong-phase sham
- 47/128
- 0 rescue / 10 harm

effect 有方向，但 modest。

---

# 9. CGR 生产机制实验：最重要的新结果

固定 25 observations × 4 arms：

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

事实：

- CGR 4/8 target rescues；
- CGR 0 harm；
- SHAM 0 target rescue + 3 harms；
- BLOCK 0 target rescue + 7 harms；
- distinct-delay controls：CGR/SHAM 和 BASE detector fields / bits exact identical；
- CGR cost 与 BASE基本相同；
- 4 个 rescue 的 terminal CGR physical mismatch 都低于 BASE。

行为层面信号很强。

---

# 10. 但 original CGR mechanism gate 没通过

原机制隐含：

> CGR 恢复 deterministic coherent reaction 后，应在 saved trajectory 中产生 consistently truth-improving physical direction。

实际：

- 每个 rescued frame 在 20 iterations 中 one-step signed physical effects 正负都有；
- summed signed effects 甚至为负；
- 5 个 fixed continuation gates 仅过 4 个；
- machine report：
  `candidate_pass=false`.

这不能解释成 CGR 无效。

正确状态：

> **behavioral effect supported；original one-step physical-descent explanation not established。**

---

# 11. 下一轮 Pro 的唯一主要任务

请不要继续 broad direction generation，也不要直接要求 fresh CGR experiment。

需要重新推导：

> **为什么 aligned \(Rar h\) CGR 会救 4/8、0 harm，而 wrong-phase SHAM 和 richer BLOCK 明显更差，但 one-step physical-direction diagnostic 又不是单调 truth-improving？**

必须允许推翻原解释。

重点分析 coupled dynamics：

\[
	ext{gain pseudo-observation}
\leftrightarrow
	ext{data pseudo-observation}
\leftrightarrow
	ext{decoder feedback}
\leftrightarrow
	ext{damping}.
\]

可能但未证的解释包括：

- trajectory / basin effect；
- physical mismatch 不是 appropriate Lyapunov function；
- CGR 修的是 approximate pseudo-observation calibration；
- aligned phase consistency 改变 joint trajectory；
- deterministic minimal correction 与 block uncertainty/damping 的相互作用；
- richer BLOCK 为什么显著 harm。

目标：

\[
oxed{
	ext{revised mechanism hypothesis}
ightarrow
	ext{derivation}
ightarrow
	ext{specific falsifiable prediction}
}
\]

优先使用已有 saved traces。

只有在得到一个明确 falsifiable revised mechanism 后，才请求一次 bounded Codex test。

如果无法形成 coherent mechanism：

> **downgrade CGR to an empirical patch and stop.**

---

# 12. 推荐启动 prompt

The bounded CGR experiment produced a mixed but scientifically interesting verdict. Behaviorally, CGR is strong on the fixed diagnostic cohort: it rescued 4/8 designated BASE failures with zero harm; SHAM rescued none and harmed three BASE-correct cases; BLOCK rescued none and harmed seven; distinct-delay controls were exactly identical to BASE; CGR cost was unchanged. However, the original physical-direction mechanism was not established: the saved one-step BASE-state effects of the CGR correction had mixed signs across all rescued trajectories, even though terminal CGR physical mismatch was lower than BASE.

Do not defend the original mechanism automatically and do not propose a larger experiment yet.

Re-derive what the \(Rar h\) correction is actually doing in the coupled TF gain/data/decoder/damping dynamics. Determine whether the failed directional gate falsifies the coherence interpretation itself, only falsifies an inappropriate local diagnostic, or points to a different mechanism. Explain why aligned CGR helps while wrong-phase SHAM and richer BLOCK inference hurt.

Use the existing saved traces and equations first. If a revised mechanism survives, derive it mathematically and state one or more falsifiable predictions that distinguish it from sham explanations. Only then specify one minimal bounded Codex test. If no coherent mechanism survives, explicitly downgrade CGR to an empirical patch and stop.

---

# 13. 红线

- 当前 paper 不依赖 CGR；
- 不需要为了 novelty “救 CGR”；
- 不得把 4/8 outcome-selected diagnostic 当 FER；
- 不得把 `candidate_pass=false` 改写成 pass；
- 不得事后修改 directional gate；
- 不得直接做大规模 prospective；
- BLOCK 更差不等于 block inference universally bad；
- truth mismatch 不是已证明的 local Lyapunov function；
- 新机制必须同时解释 CGR / SHAM / BLOCK / distinct-delay specificity；
- 如果解释不了，就停止。
