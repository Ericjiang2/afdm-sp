# AFDM-SP 项目新会话交接文档
## 截止 2026-09-21：Native Tensor-Free Joint Receiver 主线已完成 Part B 主证据

> 用途：将本会话的有效研究状态完整交接给新的 ChatGPT / GPT Pro 会话。  
> 原则：新会话应从“当前论文已经设计完成、主性能证据已闭合”开始，而不是重新从 whitening / V4 / list / physical-refinement 等历史路线重新搜索。

---

## 1. 当前一句话状态

项目当前主线已经冻结为：

> **Tensor-Free Joint Channel Estimation and Decoding for Coded Superimposed-Pilot AFDM with Full Fractional Doppler**

核心思想不是发明新的 AMP，而是：

1. 在完整 fractional-Doppler AFDM 物理路径模型下；
2. 对既有 scalar parametric bilinear inference 做 **AFDM/CPP-specific tensor-free computational specialization**；
3. coded finite-alphabet variables 始终留在 AF 域；
4. 利用 observation-unitary equivariance 和 path-operator contractions，避免显式 `P × N × N` path tensor / observation-specific cavity state；
5. 在 native coded receiver 中直接进行 **data / gain-mean joint adaptation**；
6. 相比强 structured EP，在冻结的 6–7 dB、N=1024、P≈8、LDPC(2048,1024)、rho=0.5 场景中，已通过预注册的 reliability + complete-latency 合同。

当前不再处于“找方向”阶段，而是处于：

> **论文写作 + 最终证据整理 / claim 固化阶段。**

---

## 2. 当前科学 thesis

当前 Paper Design v1 的核心 thesis 可概括为：

> A compact full fractional-path channel permits native joint gain/data adaptation at path-operator cost rather than dense tensor or observation-specific cavity cost. For coded SP-AFDM, an exact computational specialization of a declared scalar-variance bilinear inference map yields a useful measured latency–reliability operating point.

中文理解：

> **少量物理 fractional paths 虽然在 AF 域表现为致密泄漏，但没有必要因此维护致密路径张量或昂贵 observation-wise cavity。利用 AFDM 的精确 path structure，可以把联合 gain/data inference 直接做成 tensor-free 的低状态实现，并在完整接收机层面获得可靠性受控且显著更低的时延。**

---

## 3. 最终建议的论文贡献包

### C1. Exact full-path tensor-free realization

对声明的 scalar bilinear inference map：

- 证明 observation-unitary equivariance；
- 取 observation rotation `V = A^H`；
- 利用
  \[
  U_i = A M_i A^H
  \]
  其中 `M_i` 是包含 CPP 和 fractional Doppler phase 的 weighted cyclic shift；
- 直接构造 predictions、gain adjoint、data adjoint 和 Frobenius/norm 统计；
- inner iteration 复杂度约为
  \[
  O(NP + N\log N + P^2),
  \]
  不显式构造 `P×N×N` tensor。

重要边界：

- 这不是新的 P-BiG-AMP；
- 不是“首次 FFT bilinear inference”；
- 不是 observation rotation 改善 conditioning/convergence；
- two-FFT vs four-FFT 只是 implementation detail，不是 headline。

### C2. Native coded SP-AFDM joint receiver

冻结 primary：`TF_J20_R2`

- 2 coded rounds；
- 每轮 20 joint iterations；
- damping = 0.3；
- full fractional physical path refit；
- LDPC(2048,1024)，decoder cap 50；
- observed-only geometry；
- finite alphabet / code variables 保留在 AF 域；
- LDPC prior / APP / check-extrinsic 信息流合法替换；
- 无 I1 warm-up；
- 无 list；
- 无 sparse AF mask 主阶段；
- 无 learned rescue module。

### C3. Mechanism and operating-envelope analysis

当前可支持的 mechanism wording：

> **性能价值主要与 within-batch gain-mean/data joint adaptation 有关；propagated scalar gain variance 在每轮 startup 可形成大 transient，但 late direct corrections 较小，目前没有独立的 frame-reliability benefit 证据。**

关键证据：

- POINT 保留 gain-mean update、关闭 propagated `v_h`；
- FIXED-inner 同样关闭 propagated `v_h`，但冻结 inner gain mean；
- POINT → FIXED 的差异很大：
  - 6 dB：3/16 → 16/16；
  - 6.5 dB：1/16 → 13/16；
  - 7 dB：0/16 → 6/16；
  - rescues/harm = 13/0, 12/0, 6/0。
- TF → POINT 几乎无明显 frame-level 差异，因此不能把 propagated gain variance 写成主收益来源。

---

## 4. 理论主干已经闭合到什么程度

### Proposition 1 — Observation-unitary equivariance

对于声明的 scalar-variance bilinear map，在：

- isotropic proper complex Gaussian output；
- fixed scalar damping；
- fixed priors；
- matching initial states

条件下，对任意 unitary `V`：

\[
y' = Vy,\qquad U_i' = VU_i
\]

unknown-variable pseudo-observations、scalar variances 和 denoiser outputs 保持一致；observation residual 仅被相同 `V` 旋转。

它是 approximate algorithm 的 exact invariance，不是 posterior theorem。

### Proposition 2 — Tensor-free AFDM contractions

利用 `V=A^H` 后：

\[
[B_T(x)]_{n,i}
=
\chi_{l_i}(n)e^{j2\pi\nu_i n/N}
x_T[(n-l_i)\bmod N].
\]

forward/gain adjoint 为 `O(NP)`；data adjoint 通过一次聚合 path shift/phase + 一次 DAFT 完成。

重复 delay 时必须保留：

\[
R_{ij}
=
\mathbf 1_{l_i=l_j}D_N(\nu_j-\nu_i)
\]

并有：

\[
\|H(h)\|_F^2 = Nh^HRh.
\]

### Proposition 3 — Conditional scale of propagated gain variance

Gaussian gain update满足：

\[
Nv_{h,t}^{post}
=
\frac{1}{\alpha_t a_t+P/N},
\qquad
a_t=\|\bar x_t\|^2/N.
\]

当 `alpha_t a_t` 非退化时，post-transient propagated gain-uncertainty correction 为 `O(P/N)` 量级。

### Startup exception

每个 coded round 起点：

\[
u_0 = 1/P,
\]

所以 startup variance correction 没有 `P/N` 小因子；保存 trace 中初始 output correction 可达约 196%–467%。

因此禁止写“gain variance 始终可忽略”。

### Proposition 4 — Gain-mean update 不受必然 P/N 抑制

实现满足：

\[
h_{t+1}-h_t
=
\frac{
B_T(\bar x_t)^Hs_t
-\alpha_tNv_{x,t}\bar h_t
-Ph_t
}{
P+\alpha_t\|\bar x_t\|^2
}.
\]

即使 scalar variance 收缩到 `O(1/N)`，gain-mean movement 仍可保持一阶量级。

### Limitation / counterexample

scalar AMP 内部 `v_h` shrinkage **不等价于真实 channel posterior 已 identifiable/concentrated**。

因此禁止把算法内部 scalar variance 当作 true posterior theorem。

---

## 5. 最终主性能证据（Part B）

### 实验协议

- 3072 fresh independent radio observations；
- SNR = 6, 6.5, 7 dB；
- 每个 SNR 1024 frames；
- primary methods：
  - TF_J20_R2；
  - EP2_MEAN_R2；
  - EP4_MEAN_R2；
- 9696 attempts；
- 19392 checkpoints；
- source frozen；
- no retuning；
- no missing decisions；
- no numerical failure。

### Unrestricted FER

| SNR | TF | EP2 | EP4 |
|---:|---:|---:|---:|
| 6 dB | 206/1024 | 487/1024 | 309/1024 |
| 6.5 dB | 43/1024 | 140/1024 | 74/1024 |
| 7 dB | 14/1024 | 29/1024 | 20/1024 |

主 claim 不是“FER superiority”，而是：

> **lower complete latency under prospectively controlled reliability.**

对 EP2、EP4 的六个 simultaneous one-sided reliability upper bounds 全部通过预定义 tolerances。

### Complete online latency

TF median：

- 6 dB：0.2882 s
- 6.5 dB：0.2862 s
- 7 dB：0.2842 s

EP2 median：

- 0.5020 / 0.4947 / 0.4916 s

EP4 median：

- 0.7310 / 0.7161 / 0.7132 s

因此：

- TF vs EP2：median latency 约降低 42.1%–42.6%
- TF vs EP4：约降低 60.0%–60.6%
- TF/EP2 median-ratio upper 95% 约 0.58
- p90 ratio 约 0.44–0.45

这不是 borderline pass，而是有明显 margin 的结果。

### Deadline evidence

在固定约 0.5 s deadline：

| SNR | TF | EP2 | EP4 |
|---:|---:|---:|---:|
| 6 dB | 206 | 649 | 897 |
| 6.5 dB | 43 | 336 | 596 |
| 7 dB | 14 | 168 | 358 |

这非常适合作为论文“computation-limited receiver”的系统级主图。

---

## 6. 重要 controls / 限制

### POINT

Part B first 128/SNR：

- TF vs POINT：
  - 6 dB：21 vs 20
  - 6.5 dB：8 vs 9
  - 7 dB：2 vs 3

没有证据支持 propagated gain variance 的一般 reliability benefit。

因此：

- primary 仍保持 TF_J20_R2；
- POINT 是 mechanism ablation；
- 不因开发/control 结果事后换 primary。

### PBiGaBP

Part B first 32/SNR：

- TF：6/2/0
- PBi：21/10/0
- PBi median ≈ 14.36 s
- TF ≈ 0.29 s

只能定位为 expensive richer joint-inference reference；不能写 universal superiority。

### Memory

Part A fresh process：

- TF/EP process peak ≈ 623 MB；
- local PBi adaptation ≈ 1.15 GB。

不要声称 TF 对 EP 有巨大完整进程 memory 优势。

---

## 7. 当前 novelty boundary

必须主动承认以下 prior art：

- P-BiG-AMP scalar bilinear inference；
- coded FFT PBiGAMP；
- AFDM parametric bilinear inference / PBiGaBP；
- dual-domain structured EP；
- coded SP feedback；
- data-aided off-grid SBL/GAMP；
- bilinear/unitary AMP；
- other multicarrier parametric bilinear receivers。

论文不能 claim：

- 新 general AMP；
- 新 Turbo；
- first bilinear AFDM；
- first coded FFT bilinear inference；
- observation rotation improves conditioning；
- universal Bayes optimality / convergence；
- universal superiority over EP/PBiGaBP。

真正 novelty case 是：

> **exact full-fractional AFDM/CPP computational specialization + native coded SP receiver + mechanism-qualified complete cost/reliability operating benefit.**

当前最大的论文风险已经从“性能不够”转变为：

> **审稿人是否认为这只是 generic P-BiG-AMP 的 straightforward AFDM implementation。**

因此 manuscript 中 equation-level prior-art positioning 必须做得非常认真。

---

## 8. 论文当前成熟度

### 已闭合

- 问题定义；
- 方法；
- primary numerical configuration；
- 信息接口；
- theory backbone；
- main mechanism；
- primary comparison；
- Part A qualification；
- Part B main performance；
- latency/reliability claim；
- major nonclaims。

### 尚可补，但不影响当前写作

- 最终 related-work / novelty audit；
- bounded scope illustrations：
  - second code/interleaver；
  - rho=.25；
  - unresolved/missed-delay adverse case。
- 这些不是再次验证主方向，而是论文 scope/boundary 扩展。
- 是否补应在稿件成型后根据 reviewer-facing gap 决定。

---

## 9. 当前推荐论文结构

1. Introduction and closest-art positioning
2. Signal model and inference contract
3. Native scalar joint coded receiver
4. Tensor-free fractional-path realization
5. Mechanism, startup and limitations
6. Numerical evaluation
   - exactness/scaling
   - primary FER/reliability
   - complete latency
   - deadline tradeoff
   - POINT/FIXED/PBi controls
7. Discussion and conclusion
8. Appendices / supplement
   - detailed CPP contractions
   - proof details
   - code-equation map
   - numerical guards
   - baseline adaptations
   - provenance / seeds / statistical contract

---

## 10. 当前推荐 figures

1. Receiver variable-domain + information-flow schematic
2. FER vs SNR（TF / EP2 / EP4）
3. Complete latency + deadline error tradeoff
4. Core complexity / measured resource scaling
5. Mechanism trajectories（两个 coded round 的 startup / late behavior）

---

## 11. 当前推荐 claim wording

可写：

> In the declared N=1024 coded full-fractional SP-AFDM regime, the frozen tensor-free joint receiver satisfies prospectively defined practical reliability constraints against the structured EP controls while reducing measured complete online median latency by approximately 42% relative to EP2 and 60% relative to EP4.

不可写：

- universal superiority；
- statistical equivalence；
- all hardware；
- all channel regimes；
- FER floor；
- Bayesian optimality；
- gain variance causes the performance；
- FFT-count reduction causes the complete speed gain。

---

## 12. 当前下一步

### 不要再做

- 新 receiver search；
- 新模块；
- 新 hyperparameter sweep；
- 再找 V4/list/whitening；
- 再调 POINT；
- 再做“小样本方向验证”。

### 现在做

1. 写完整 manuscript 初稿；
2. 写项目 Technical Master Document；
3. 固化 claims/evidence map；
4. 做最终 related-work / novelty audit；
5. 根据写稿后暴露出的 reviewer-facing scope gap，再决定是否做 1–3 个很小的 bounded scope experiment。

---

## 13. 新会话启动建议

新会话应优先读取：

1. `SP_AFDM_Paper_Design_v1(1).md`
2. `RESULTS(8).md`（Part B final evidence）
3. `RESULTS(7).md`（Part A qualification / attribution）
4. `TABLES.md`（mechanism traces）
5. `SP_AFDM_Native_Joint_Research_Verdict_20260921(1).md`
6. 最新 theory chapter

不要重新从早期 V4/list/whitening 文档开始，除非需要查某个历史 derivation。

新会话当前主要任务：

> **把 Paper Design v1 和最终 Part B evidence 写成完整 Transactions-style manuscript + technical master reference，并做最后 novelty/claim 审核。**

---

## 14. 当前最终判断

- 当前路线：**保留，不再换方向**
- 方法：**冻结**
- 理论：**基本闭合**
- 机制：**基本闭合**
- 主性能：**Part B prospectively supported**
- 普通 IEEE Transactions 潜力：**现实且值得正式投稿**
- 最大剩余风险：**novelty perception / closest-art positioning，而非主性能**
- Codex：**不再需要主性能实验；只在写稿后发现明确 scope/qualification gap 时补小实验**
