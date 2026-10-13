# MATH-01 / SCORE-01 数学与接线参考

## Target

只读研究分工：为 v2 B3-a 提供独立 SVD-LS 参考的最小契约、白 C 的确定性复数排反反例，以及冻结 prior 的评分装配推导。不修改代码、CSV、任务状态，不担任 checker，不启动接收实验。本记录是源码检查及代数推导，**不代表 MATH-01/SCORE-01 已验收**。

## Status

**COHERENT AS STATED**。GLS 一步下降恒等式成立；现有装配函数可复用。必须明确文中的 `T/q → D/q_perp` 指两个统计量组成的二元组替换，**不是把 `D/q_perp` 这个比值传给 T 槽位**。

## Invariant Object

冻结一次状态的加权最小二乘目标：

\[
J(S)=\min_g\|L^{-1}(y-\Phi_Sg)\|^2,\quad C=LL^H.
\]

候选分数 D 是纯 add 的 J 下降；含 prior 的 logLambda 是另一个评分对象；实际保护、剪枝、扩展后的 F 差是完整动作门控对象。三个对象不互相替代。

## Assumptions

- y、Phi、C、S、有序候选 ID、prior 数值在比较前冻结；C 有限、Hermitian、严格正定。
- 输入复数维度一致；S 中 ID 唯一且在范围内；候选与 active 冲突显式过滤并记数，不补池。
- 精确代数允许秩亏支撑通过 Moore–Penrose 投影解释；v2 的**实际提交契约更严格**，当前系统秩不可靠须 HOLD，候选扩充系统不可靠须拒绝并记原因。
- posterior 解释另需 reduced-space circular complex Gaussian 模型和候选增益先验 CN(0, sh2)。仅做既定评分装配对照并不依赖该概率解释在真实残差中完全成立。

## Notation

A=L^-1 Phi，z=L^-1 y；P=A_S A_S^dagger；r_w=(I-P)z；v_i=(I-P)A_i；q_perp_i=v_i^H v_i；E=max(1,||z||²)。

旧统计量另记为 T_old、q_old，不能用同一变量覆盖后再声称已保存旧统计。q_old=phi_i^H C^-1 phi_i；T_old=|phi_i^H C^-1 r_OLS|²/q_old，r_OLS=y-Phi_S g_OLS。

## Derivation Strategy

从 J 的嵌套子空间最小化推导 D；通过独立重拟合计算参考下降；从 reduced-space Gaussian 积分解释现有 logLambda 的两个输入槽位。以下恒等式直接由给定源码与 B3 定义推导，不以未读外部论文作证据。

## Derivation Map

1. 固定白化将 GLS 化为普通复数 LS。
2. 新候选沿当前支撑正交补中的 v_i 扩张一维。
3. 消去该维增益得到下降 D_i；独立 SVD 重拟合只使用 J 定义。
4. 对同一 reduced-space 候选模型积分 Gaussian 增益，得到既有装配函数，只替换统计二元组。
5. 完整动作还需独立比较最终 refit 的 F，纯 add 公式不证明剪枝后的收益。

## Main Derivation

### 1. 纯 add 的精确恒等式

当 q_perp_i>0 时，在当前子空间正交补中只需最小化

\[
\min_h\|r_w-v_i h\|^2.
\]

复数最优 h=(v_i^H r_w)/q_perp_i，故

\[
J(S+i)=J(S)-\frac{|v_i^H r_w|^2}{q_{\perp i}}.
\]

这是恒等式。注意 r_w 是用**白化后支撑重新拟合**的残差；对于有色 C，一般不等于 W r_OLS。白 C 下两种残差一致，但未投影候选分母仍可改变排序。

q_perp=0 表示候选在支撑张成空间内，精确目标下降为 0；不能计算 0/0，也不能靠 clamp 到 1e-30 将其变成可提交候选。

### 2. 独立 SVD-LS 参考的最小契约

建议测试侧契约（名字仅作接口建议）：

```python
reference_gls_additions(y, Phi, C, support_ids, candidate_ids, *, dtype)
# -> baseline{gain, residual_w, objective, rank_diagnostics},
#    candidates[{id, refit_gain, objective, delta, rank_diagnostics, reason}]
```

独立 oracle 必须逐个调用自己的 SVD fit，不能调用被测 projector、D 计算器、生产 GLS helper，也不能从 D 倒推目标。

参考步骤：

1. 检查 shape、有限性及 C 的 Hermitian 性。必须先检查 Hermitian，不能只依赖 Cholesky（库可能只读取一个三角）。随后独立 Cholesky 并解 L z=y、L A=Phi；不显式求逆、不加 jitter。
2. 独立拟合 `A[:, S]`：对其作 `U,s,Vh = svd(..., full_matrices=False)`，由 `g=Vh.conj().T @ ((U.conj().T @ z)/s)` 求 gain，再**直接**算 residual=z-A_S@g 与 J=vdot(residual,residual).real。满列秩时此式成立。
3. 每个候选独立拟合 `A[:, S+[i]]`；返回直接残差范数之差 `J0-Ji`。不返回 `|v^H r|²/q` 充当参考。
4. 空 S：gain 长度 0、residual=z、J=||z||²，跳过空 SVD。
5. 重复/近共线分支可用独立截断 SVD 记录数学参考及秩诊断，但**不得把其伪逆成功当作生产提交通过**；测试须检查明确拒绝原因。截断阈值必须显式记录，不能依赖库默认 rcond。

为避免原列尺度干扰 rank，先在独立参考中形成单位范数 `B=A_S / column_norms` 作秩判断。良态拟合可对 B 做 SVD 得到 beta，再恢复原列 gain=beta/column_norms；这仍是同一 full-rank LS 问题。测试应同时验证原列回代 residual 与 returned gain 一致。参考侧不要复用生产 rank helper。

建议每例同时记录绝对误差、误差/E、相对误差、参考下降/E；complex128 的 rtol/normalized-atol 为 1e-8/1e-10，complex64 为 1e-3/1e-5。近零需要绝对分支，不能无条件除以 D_ref；可明确登记接受式 `abs(D-D_ref) <= max(rtol*abs(D_ref), atol*E)`，并分别报告两个误差，避免隐去究竟由哪一分支通过。不要把良态容差推广为任意病态条件下的保证。

### 3. 确定性复数、单位范数、白 C 排反反例

取 N=3、C=I、S={e1}，

\[
y=e_1+(1+i)e_2+e_3,\quad
a=(10e_1+i e_2)/\sqrt{101},\quad b=e_3.
\]

所有原子单位范数，r_OLS=r_w=(1+i)e2+e3，E=4，J(S)=3。

| 量 | 候选 a | 候选 b |
|---|---:|---:|
| q_old | 1 | 1 |
| T_old | 2/101 | 1 |
| q_perp | 1/101 | 1 |
| D | 2 | 1 |
| 独立 refit 后 J | 1 | 2 |

因此旧 T 选 b，GLS 真实下降选 a；差异完全可以发生在白 C 下。候选 a 的精确 refit gain 是 `g_a=sqrt(101)*(1-i)`，原 e1 的 gain 是 `-9+10i`，剩余 residual=e3；候选 b 的 gains 为 (1,1)，剩余 residual=(1+i)e2。这给出了不依赖 D 公式的显式回代参考。

固定两候选 pi=1/2、sh2=1：

- 旧 logLambda(a)=1/101-log(2)，旧 logLambda(b)=1/2-log(2)，仍选 b。
- 新 logLambda(a)=1/51-log(102/101)，新 logLambda(b)=1/2-log(2)，选 a。

这组例子同时检查统计配对装配是否正确，但不能由一个例子推断两种评分一般都排反或新 logLambda 总与 D 同序。

### 4. 冻结 prior 时真实应复用的公式

源码 `decision_bound.py:99`：

```python
b = sh2 * q
logL = log(pi/(1-pi)) + b/(1+b)*T - log(1+b)
```

旧臂严格使用 `(T_old,q_old)`；新臂严格使用 `(D,q_perp)`：

\[
\ell_i^{new}=\log\frac{\pi_i}{1-\pi_i}
+\frac{s_{h,i}^2q_{\perp i}}{1+s_{h,i}^2q_{\perp i}}D_i
-\log(1+s_{h,i}^2q_{\perp i}).
\]

等价相关项是 `sh2*|v^H r_w|²/(1+sh2*q_perp)`。**不能再除一次 q_perp；也不能只换 D 而仍使用 q_old 构造 b。**

概率解释的附加推导：令 Q 是当前支撑正交补的正交基，t=Q^H z、u=Q^H A_i。若 H0: t~CN(0,I)，H1: t=u h+n 且 h~CN(0,sh2)，则 H1 的协方差 I+sh2*u*u^H。矩阵行列式引理给出 log determinant=log(1+sh2*q_perp)，Woodbury 给出二次型增益 `sh2*|u^H t|²/(1+sh2*q_perp)`，再加 prior odds 即上式。复圆对称 Gaussian 的这一约定没有实 Gaussian 的 1/2 因子。

这里应在 Q 坐标解释密度；全空间 r_w 的 covariance=I-P 是奇异矩阵，不能直接假定 full-space covariance 仍是 I 并套普通密度。实际 C 可能为估计、S 自适应、prior 来自经验校准；因此只保证数学装配一致，不宣称真实 posterior 校准或 CFAR。

### 5. prior 冻结的接线边界

已读源码接线：

- `decision_gateA.py:92` `_resid_geom` 先普通 LS，同时用该 gain 得到 g_nn；g_nn 决定 fine prior 的 gain bin。因此不能让新臂改为 GLS geometry 再各自 lookup，那会同时改变 pi/sh2。
- `decision_gateA.py:150` `make_genie_lambda` 固定 H 对应的 `(1-rho)HH^H`，每次与 sigma2 I 组成 C；其 residual 来自普通 LS，候选仍是原列。
- `decision_harvest.py:53` `whitened_suffstats` 正是旧 T/q；它含 q.clamp_min(1e-30)，不能直接继承到要求显式秩拒绝的新投影统计路径。
- `budgeted_support_eval.py:102` 虽调用名为 `make_genie_lambda` 的工厂，实际传入 OMP 估计 H0，而不是 simulation Htrue。新部署评分也必须保持这一 observable 边界。
- `classical_joint_unrolled.py:1254` `apply_f2p_refinement` 的 score_override 返回按 cand_cols 对齐的 logits；当前每轮候选由 build_features 重建，且最终 gain 仍为普通 LS。单独替换 scorer 不会完成 B3-b 或 WIRE-05。

最小隔离方案：在共同参考状态按原 geometry 入口一次得到候选 ID 对齐的 `(pi,sh2)`，保存数组并给两个 scorer 共用；用同一个 `assemble_lambda_percand` 各装配一次。保存 shared-state/candidate/prior 标识及 dtype。不能只冻结 lookup 函数而让两个臂用不同 g_nn 调用，然后声称 prior 数值固定。

空支撑数学契约可独立通过，但 `_resid_geom` 的 nearest-active argmin 对空 S 不成立。SCORE 的空 S 必须明确共有 prior 来源或标记不适用，不能在新臂偷偷设置 pi=.5/sh2=1；当前 F2P 本身空 S 直接停止。无 prior OLS 控制应直接返回 D，并独立标注，不能伪装成某个任意 pi/sh2 极限。

## Remarks and Interpretation

### 复数缩放和近零/秩测试

- 候选 a→alpha*a：D/J 不变，q_perp→|alpha|²*q_perp，拟合增益除以 alpha。若还要求完整 logLambda 不变，必须同时 sh2→sh2/|alpha|²；保持 sh2 不变等于改变物理增益先验，不能要求同一 logLambda。
- y→beta*y：J、D 乘 |beta|²，q 不变。C→t*C (t>0)：J、D、q 均除以 t。白 C 测试至少包括 sigma2 !=1，避免漏除噪声功率。
- 近零下降应取非退化候选但 v^H r 接近 0，单独检查 absolute/E 容差；近零 q 则首先触发秩判断，二者不是同一失败原因。
- 按 v2，用白化后单位范数列，阈值 eta_rank=10*max(N,K+1)*eps(real dtype)。可具体登记为 `s_min(B)>eta_rank*s_max(B)` 才判 full-column-rank；当前 S 使用自身尺寸，扩充候选使用 K+1。边界等于阈值拒绝，报告 singular values、ratio、threshold、dtype。
- 测试 `a=e1+epsilon*i*e2` 的 epsilon 在阈值上下两侧；重复列 epsilon=0 应明确拒绝。不要用随机数碰运气产生近共线。
- 对 complex64，N=1024 时 eta_rank 约 0.00122，属于相当保守的 rank 合约；必须记录拒绝率，不能以 double 求解成功覆盖用户规定的原 dtype 秩不确定。
- 对 NaN/Inf、非 Hermitian、负特征值、半正定 C 分别断言显式错误；Cholesky 失败不允许 jitter/retry 假装原模型有效。

## Boundaries and Non-Claims

没有执行 numerical tests、真实 receiver 或训练；本记录的反例数值由精确代数给出。没有变更 CSV 状态。没有引用外部论文中的未验证结论。独立参考仅是测试设计，尚未生成运行证据。

纯 add 的 D 有益不意味着完整事务有益。v2 给出的 `y=e1+epsilon*e2, K=1`、保护 e2 导致剪掉 e1 的反例仍须由实际事务消费者验证；本记录不替代 GATE-01/02 或最终 BP/LDPC 接线验收。

## Open Risks

- MATH/SCORE 实现需要把 rank、近零 score 与 invalid-current-state 的日志原因拆开，避免通用 -inf 掩盖实际失败。
- 新臂高精度统计经 `_to_logits` 转 float32 后可能合并细微差分；数学误差验收应在 conversion 前进行，候选同分的真实选择另测并显式固定。
- 多轮后各臂 S 分叉时，必须说明 prior 对齐是按预存共同参考轨迹进行，还是只保证首轮共同状态；冻结 lookup 参数不等于各轮 prior 数值相同。

源文件：v2 B3（`research/next-execution-plan-20260906-v2.md:90`）；`decision_gateA.py:92,127,150`；`decision_bound.py:99`；`decision_harvest.py:53`；`budgeted_support_eval.py:102`；`classical_joint_unrolled.py:1254`。本分工完成时间：2026-09-06。

## 主会话执行增补

已按上述独立参考实现并运行MATH-01，结果见issues/2026-09-06_13-47-38-afdm-plan-v2/evidence/MATH-01.md。研究记录本体仍为推导；实际验收范围为CPU投影组件，不代表SCORE/GATE/receiver完成。
