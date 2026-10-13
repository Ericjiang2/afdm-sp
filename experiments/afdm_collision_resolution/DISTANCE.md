# 有界 bridge 距离诊断与有限重复关系

## Target

从冻结的 `oracle_identifiability_v1` 全部 112 个 same-nuisance null/alt/R
评价 LLR 对，计算两组等权的 TV 与未除以 2 的 Hellinger 平方 bridge。
给出预登记有限样本区间、完整分母/逐组值及单帧到重复的条件关系；不再运行原检测。

## Status

**COHERENT AS STATED**。真密度恒等式与实际数值似然的代理期望分别保留。
实际先验没有全局似然误差证书，因而本 reader 不认证其真实距离或最优功效。

## Invariant Object

固定一组 null/alt 分布后，始终分析
`theta_g=(E_P0 g(L)+E_P1 g(L))/2`。使用真 L 时它等于指定距离；使用保存的
代理 `L_tilde` 时，分析对象是同一真实抽样分布下的 `theta_g_tilde`，不会悄然
把抽样分布改成代理密度或把代理期望命名为真距离。

## Assumptions

- P0、P1 相对于共同支配测度有归一化密度 p0、p1；本项目正 Gaussian 噪声使密度
  严格正。令 L=log(p1/p0)。理论允许一般共同支配分布；有限保存 LLR 是计算输入。
- 每行有 n0 个独立 P0 评价组和 n1 个独立 P1 评价组，两组彼此独立。每个 R 组
  是原注册的互不重叠帧组及固定前缀。不同备择复用同一 null、不同 R 复用帧，
  因而不假定不同行相互独立。
- bridge、置信错误预算和 R 传播网格在读取结果前固定；没有校准样本选择、拟合
  或调阈值。实际近似似然是冻结的确定性函数。
- IID 重复定理要求相同单帧 P0/P1 的独立乘积分布；它不是任意代理函数的恒等式。

## Notation

- M=(P0+P1)/2，密度 m=(p0+p1)/2。
- TV(P0,P1)=(1/2)∫|p1−p0|。
- H²(P0,P1)=∫(sqrt(p1)−sqrt(p0))²∈[0,2]；本文不采用除以 2 的另一惯例。
- `g_TV(l)=|tanh(l/2)|∈[0,1]`，`g_H(l)=2(1−sech(l/2))∈[0,2]`。
- b 是相应 bridge 的上界（1 或 2）；δ 为一次区间失败概率；全家族 δ_F=.05。
- α 是检验的真实总体 size 上限，与区间失败概率 δ 区分。

## Derivation Strategy

从真距离定义代入 m 和 L，得到有界混合期望；再对两组独立样本的带权和直接应用
Hoeffding，最后用不需要行间独立的 union bound。重复关系从 affinity 的乘积
分解推导。代理误差只在另有全局证书时通过 Lipschitz 界转移。

## Derivation Map

1. **恒等式**：距离定义 → 关于 M 的 bridge 期望；需要真 p0、p1。
2. **命题**：固定有界 bridge → 两组等权 Hoeffding；只需要独立抽样和函数范围，
   所以同样适用于实际代理期望。
3. **命题**：224 个边际浓缩界 → Bonferroni 同时覆盖；不需要跨 pair/R 独立。
4. **恒等式**：真单帧 affinity → IID 重复 H²；代理期望代入仅是代数外推。
5. **有条件命题**：若存在 uniform log-ratio error ε，则桥期望偏差≤ε/2。
   本轮未取得该证书，因此不做真实距离区间扩张或认证。

## Main Derivation

### 1. 距离到有界期望：恒等式

由 p1/p0=exp(L)，

`(p1−p0)/(p1+p0)=tanh(L/2)`，
`2 sqrt(p0 p1)/(p0+p1)=sech(L/2)`。

因此

`TV=∫m |(p1−p0)/(p1+p0)|=E_M g_TV(L)`，

`H²=∫(p0+p1−2sqrt(p0p1))=E_M g_H(L)`。

计算中令 x=|L|/2、z=exp(−x)，`sech(x)=2z/(1+z²)`；直接减去接近 1 的
sech 会损失小 L 精度，因此实现使用等价式

`g_H(L)=2[-expm1(−x)]²/(1+exp(−x)²)`。

它既避免 cosh 溢出，也保留 `g_H(L)~L²/4` 的小 L 行为。极端有限 L 时
g_TV→1、g_H→2，无需要裁剪未界定数值的静默补救。

### 2. 两组等权估计与浓缩：命题

记 X_i=g(L(Y0_i))、Z_j=g(L(Y1_j))，均在 [0,b]。使用

`hat_theta=(mean(X)+mean(Z))/2`，

即使 n0≠n1，两个分布仍各占 1/2，不能按组样本数直接合并成另一混合权重。
保存两组各自样本方差 s0²、s1²，并报告诊断 SE：

`SE=(1/2)sqrt(s0²/n0+s1²/n1)`。

此 SE 不是本轮浓缩区间的依据。带权各项范围长度为 b/(2n0)、b/(2n1)，平方和
为 `b²(1/n0+1/n1)/4`，Hoeffding 给出

`Pr(|hat_theta−theta|≥t) ≤ 2 exp(−8t²/[b²(1/n0+1/n1)])`。

令

`r_delta=b sqrt((1/n0+1/n1)log(2/delta)/8)`，

则 `[max(0,hat_theta−r_delta), min(b,hat_theta+r_delta)]` 至少有 1−δ 覆盖。
范围截断来自已知真参数的 [0,b] 支撑，不是忽略失效观测。

同时保存 pointwise δ=.05 和 simultaneous δ=.05/224。224=112 行×2 个距离。
Union bound 给出全部区间同时覆盖概率至少 .95，即使不同 null/alt/R 之间相关。
不把 112 行合成一个总体，也不把被复用的组重复计为独立新观测。

### 3. 数值密度近似的范围：有条件命题

`g_TV` 是 1/2-Lipschitz。`g_H'(l)=sech(l/2)tanh(l/2)`，其绝对值最大为 1/2。
如果能证明在真实 P0/P1 支撑上 `|L_tilde−L|≤epsilon`，则两种桥期望的偏差
均≤epsilon/2（还可与已知函数范围取最小值）。若每个 log-density 分别有全局
误差界 epsilon0、epsilon1，则可取 epsilon=epsilon0+epsilon1。

原实际参考只保存有限观测上的加密比较，没有这个 uniform 证书。输出的证书字段
明确为 null。实际同时区间只覆盖真实抽样分布下的代理函数期望，不覆盖真 TV/H²。
控制参考在解析模型层面给出真 likelihood；浮点实现的全局舍入误差也未另行认证，
其数学距离解释以准确 likelihood 算术为前提。

特别地，P0=P1 时若近似 L 被错误地置为常数 1，真实距离仍为零而两个代理均
严格为正。再多样本只能收紧代理期望区间，不能修复这个对象偏差。

### 4. 理想功效与重复关系：带明确前提的定理

对任意检验函数 φ∈[0,1]，
`E_P1 φ−E_P0 φ≤TV(P0,P1)`，所以若真实 size `E_P0φ≤alpha`，则
`power≤min(1,alpha+TV)`。这是准确分布距离与总体 size 的结论；经验 proxy
或一次有限校准后的样本虚警率不能替代前提。

令 affinity `A=∫sqrt(p0p1)=1−H1²/2`。IID product 下 Tonelli 分解给出
`A_R=A^R`，因此

`H_R²=2−2(1−H1²/2)^R`。

该函数对 H1² 单调。在真距离区间事件上，对上下界作同一单调变换即可同时控制
任何预定 R，不另需跨 R 独立或新的 Bonferroni 次数。实现用 log1p/expm1 保留
小距离精度，并显式处理 H1²=2。

预登记 R=(1,4,8,16,64,256)，共 56 个单帧 pair×6=336 行代数传播；不是新
实验。实际将代理 H1²代入后不再享有真距离或重复代理期望的覆盖保证。原控制 R8、
实际 R4 的直接 bridge 估计另列比较，保留共享数据/前缀的依赖，不能把差异当独立
复现实验或再据此调传播关系。

### 5. KL 辅助量：诊断而非浓缩认证

真 likelihood 下 `E_P0[-L]=KL(P0||P1)`、`E_P1[L]=KL(P1||P0)`。
LLR 无界，本轮只保留各组 mean、sample variance、SE，允许有限样本负估计，
不裁零、不套用有界 Hoeffding，也不从 sample SE 认证 KL 或信息上界。

## Remarks and Interpretation

- 输入固定为旧补充阶段的 `oracle_control.npz`、`oracle_actual.npz` 中的
  **evaluation** LLR、pair IDs、R 与候选；不读取 calibration 数组参与统计。
- 输出 `bridge_{family}.npz` 保存派生逐组 g_TV/g_H 值、pair/R/候选索引，不复制
  原 LLR、完整原 NPZ 或大 raw。`distance_cases.json` 保存所有分母、均值、方差、
  SE、两类浓缩区间和解释；`repetition_projection.json` 保存全部传播和已有 R
  的直接对照。全部 112 行保留，不能只报告分离明显的条件。
- `DISTANCE_CONFIG.json` 在 GO 前绑定 source registration/attempt/消费工件和
  新 protected manifest 哈希。运行前后复用独立哈希读取器校验完整旧补充 stage、
  绑定源码/快照/原提交及新封存 baseline。自己的 attempt 成本另列，不重复累计
  输入阶段费用。
- 新 `protocol.py` 只私有加载冻结 efficient-information admission implementation，
  替换任务路径并调用原 run；没有复制另一套登记器、没有修改旧模块 globals。
  注册沿用原 recorder schema，任务身份由新路径/合同给出。源码须匹配 HEAD，
  失败保留 raw/预约，执行锁、总预算、单线程预加载规则继承。

## Boundaries and Non-Claims

本 reader 新观测/节点/积分规则均为 0，预约 120 秒，不重新运行检测，不接收或
译码，不外推完整八径生产。实际 proxy CI 不是最优功效、真实TV或真实H²认证；
理论重复关系不提供已校准检测器。本轮没有新增确认流，所有复用关系逐行保留。

正式入口仅在主会话提交源码并 GO 后运行：

```sh
/tmp/afdm-shared-channel-env/bin/python -m experiments.afdm_collision_resolution.distance_reader --stage distance_v1
```

NumPy/SciPy/audit 依赖在顶层预加载，不调用物理生成器或 PyTorch。使用统一单线程
环境和新合同：8192 总新观测、2400 总预约秒、单 stage≤600 秒、250000000 输出字节。

## Open Risks

- 同时界可能宽；不能通过删除条件、事后改 family 或放大独立样本数收紧。
- 实际密度代理的 uniform 误差证书尚缺；原样本加密通过不填补该缺口。
- 浮点误差无全局证书；解析恒等式与有限精度计算的证据等级分列。
- 微型测试涵盖同分布、两点分布、极端 L、小 L、分母不等、有限 Bernoulli 精确
  枚举、tensor product、代理反例以及保存阶段/篡改读取。它们不是正式研究结果；
  保存阶段测试仅 mock 大型历史哈希遍历，其消费文件/记录哈希仍实际校验。
