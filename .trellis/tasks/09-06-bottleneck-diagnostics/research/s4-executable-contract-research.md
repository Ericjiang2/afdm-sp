# S4 最小可执行软反馈契约研究

状态：只读代码研究与实验建议；未实现、未运行 S4。源：parent `implement.md` S4、`design.md` §3.3；当前 `classical_joint_unrolled.py`、`mp_detect_bp_torch.py`；本任务 `soft-feedback-analysis.json`。不能据此宣称 S4 验收完成。

## 1. 现有证据与首个原型边界

GPU 原 A2 192 帧观察器采集与主矩阵 H/x 哈希及错误完全一致。DA-LS 第 1 轮，T=1 符号 NLL 0.77296，离线 T=0.5 为 0.71533；第 9 轮 T=1 为 0.59293，T=2 为 0.53467。后期有限星座预测方差 0.09573，小于实际均方误差 0.16818。它们支持检查反馈失校；**不支持把 T=2 冻结为已校准方法**，因为这是已看的 D_dev，且没有递归反馈。

最小首轮原型：保持现有 A2 支撑/检测/噪声更新，仅在 DA-LS 的外环 QPSK 投影上使用 D_cal 选出的标量温度，返回有限星座均值。同步计算有限星座方差用于诊断。它足以回答“可实现、低成本的反馈均值干预是否影响端到端错误”。方差若只记录，不能命名为“方差反馈”或 J_soft。

该原型只完成 S4 的接口与温度控制，不完成 parent 要求的 G/V 两入口对照。当前 A2 沿用仿真展开抽头容量，因此第一批仍是机制诊断；正式方法、G1/G2 或部署比较前，必须落实 D_cal 固定 K_prop/K_active，扩展后验证实际容量。

## 2. 精确接口与数学语义

| 位置 | 当前行为 | 首轮最小变更建议 |
|---|---|---|
| `classical_joint_unrolled.py:295` `_qpsk_soft_decision` | v_g=sigma²/column_power；logit=-distance²/v_g；均匀先验；只返回均值 | 显式有限星座统计 helper，支持严格正有限 T，给出 p、mu、v；旧调用仍走原算术 |
| 同文件 `forward` DA-LS 分支，约 1715–1747 | 用投影均值组成 A_total；带 previous-gain proximal 项求解 | 只此处选用温度后的 mu；T=1/disabled 保留可回放旧路径 |
| 同文件约 1895–1907 `noise_feedback` | 另一次投影均值影响 sigma² 更新 | 第一批保留原样；以后单独注册 noise-only 或 joint 控制 |
| 同文件约 1861 `mp_detect_bp_torch` | 拿 Gaussian mu_post，忽略 var_post，再做外层均值阻尼 | 第一批不改变此语义；不得将 mu_post 命名为有限星座均值 |
| `mp_detect_bp_torch.py:109` | 逐边有限星座投影分母为 2v，最终节点返回 Gaussian 聚合 | 不是首轮必改位置；改变 BP factor 2 是另一机制，需要独立基线回放与登记 |
| `loop9_cache_features.py:39` `_fast_bp` | 实际 detector 包装绑定 | 只有后续改 BP 返回接口时才需同步转发；外环原型无需改 shim |

工作分布定义：

- `p_T(a) = softmax(logit(a)/T)`，`mu_T = sum_a p_T(a)a`，`v_T = sum_a p_T(a)|a|² - |mu_T|²`。
- 这些是 **Gaussian surrogate 诱导的有限星座工作矩**，不是精确后验；当前阻尼后的 x 不是独立高斯观测，不能补充精确贝叶斯/EM 保证。
- `constellation_data`、mu、x_pilot_scaled 已处于发射功率单位。当前 Pd=1-rho=0.5，QPSK v∈[0,0.5]，均值实虚范围 [-0.5,0.5]。
- T 用实数标量，正且有限。先检查概率/原始矩，再对仅舍入级负方差做容差处理并记录；非法输入不能用方差下限隐藏。
- 首轮不引入额外概率阻尼。若随后注册概率混合 p'=(1-beta)p_old+beta p_new，必须由混合概率重算 mu/v；只混合 mu 再沿用旧 v 不构成一致矩。

## 3. D_cal-only 的最小冻结实验

建议 root 在运行前明确写入 child 契约；以下为提案，尚未形成运行授权之外的新研究结论。

1. 先只做 SNR8、原 A2 骨架、coded 模式；三独立 replicate。D_cal-fit 每流64帧，D_cal-validation 每流32帧。固定帧数，失败也保留完整分母。若预算调整，只能在查看该批结果之前改登记。
2. 新 RNG 接口显式 split_id=2。保持既有 D_dev=1 完全不变；pilot/data/channel/noise/order 各自 stream。不要通过给 `replicate` 换一个很大数并仍写 D_dev 来冒充 D_cal。
3. 使用 D_cal 的独立 fit/validation 帧段，例如每流 fit 10000–10063，validation 10100–10131。这些具体 IDs 需检查此前 manifest 未占用。既有校准 cache 使用单一 seed_base 后 legacy 加法，故不仅检查元组，还对生成 channel_seed、H、data/codeword、unit-noise 的哈希及 manifest 做交叉去重。prior cache 可以作为另一 D_cal 子集保留，不能用同一帧既拟合又当 validation。
4. 基线在 fit 帧记录 DA-LS 各轮完整 logits。温度候选预先固定 `{0.25,0.5,1,2,4}`。**首轮只拟合一个跨 DA-LS 轮次共享标量 T**：按帧等权，再按 9 轮等权的符号 NLL 最小。平局优先 T=1，再选 abs(log T) 小者，仍平局选较小 T。SNR/迭代自适应表暂不加；若标量不足，之后另登记小表，不能边看 D_dev 边扩网格。
5. 从相同只读 fit logits 计算 NLL/Brier/可靠性箱。T 选定后，在独立 validation 帧上递归运行 V0 原版、M 温度均值两臂，固定 paired inputs 和随机臂序。不能仅离线重评分后宣称在线分布仍校准：修改早期反馈会改变后续 logits。
6. validation 记录所有轮 p/mu/v、sigma²、support、H/x、最终 raw/info errors、失败和耗时。校准改善只以 validation 的配对逐帧 NLL/Brier/误差-方差读数判断；FER 仅开发描述，报告每流及 paired win/harm。192/96 帧不能替代 S5 功效设计或 G1。
7. 若 M 没有端到端价值，保留失败证据；是否继续 G/V 取决于其不同机制价值和剩余 8 GPUh/8 机器墙钟预算。不可从一个标量失败推断所有软可靠性方法无效。

跨 SNR 的共享信道/码字仍是同一独立簇；一个帧里的 1024 符号、9轮、两stage不是独立样本。后续开发评估可复用既定 D_dev 以定位机制，但明确其已被看过；独立 D_test 保持关闭。

## 4. J_soft 增益入口：区别与最小正确实现契约

固定当前 S、有限星座工作分布 mu/v；令 D_i 为 `reconstruct_H_torch` 的单位增益整数路径算子，H(g)=sum_i g_i D_i；A_i=D_i(x_pilot_scaled+mu)。

`J(g)=||y-A g||² + gᴴ Q g`，其中

`Q_ij = tr(D_iᴴ D_j diag(v)) = sum_n v_n <D_i[:,n], D_j[:,n]>`。

**错误捷径**：把 `D_i sqrt(v)` 当向量相乘再做 Gram，会引入跨符号 n≠m 项，不等于此 trace。

现有 gain 更新含 `lambda||g-g_old||²`，所以若保留其稳定项，实际求解与检查的目标必须明确写成 `J_prox=J+lambda||g-g_old||²`，解为

`g_new=(AᴴA+Q+lambda I)^(-1)(Aᴴy+lambda g_old)`。

其下降保证只属于冻结分布/支持的 J_prox。不能报告 J 本身必下降；若要求纯 J，需去掉 proximal 项，另有可能奇异的最小范数解契约。

对于当前 N=1024、l∈[0,102]、k∈[-2,2]，各唯一原子的 displacement `5*l+k mod N` 不重复；每列是单位相位的单点，因此 **Q=sum(v) I**。这使首轮 G 入口只比原小规模 solve 多一个有物理单位的 ridge，且不是经验任意增大 lambda。实现必须检查 displacement 唯一；一般配置出现同位移时，Q 的交叉项是加权相位和，不可继续盲用对角公式。用真实 D_i 的小 N dense trace 对照证明算子公式。

G 对照最少 M 与 G：二者用同一冻结 D_cal 温度及 mu，G 额外使用 v 的 Q；噪声更新保持原样，支撑与检测保持同规则。点质量 v=0 时退化为同 mu 下原 proximal DA-LS（若 lambda=0 才是纯已知数据 LS）。

## 5. 残余协方差入口：独立目标与成本

缩放后的工作量必须使用 `C = H diag(v) Hᴴ + sigma² I`，**不再乘 (1-rho)**。它在固定 H、v≥0、sigma²>0 时 HPD。point mass v=0 退化为 sigma²I；这与 gain 入口不同。

仅把残差 trace/N 加到现有 sigma² 更新，是“标量不确定性噪声控制”，不是完整 H V Hᴴ 协方差入口。完整 V 入口需明确使用位置，例如固定 H/mu/v 构造局部 whitening/score；若把 C 引入 gain GLS，要明确是在最小化 frozen-C 加权残差，不能同时再机械加入 Q 并声称一个既定目标。当前主干 detector 接口只接受 scalar sigma²，不能直接塞 N×N C。

因此 M/G 是最小连续实现序列；V 应先固定调用契约，确认冻结 C 的接收接口/稀疏性与成本，再实现。dense Cholesky 或算子求逆均需计入完整 receiver；已有 pilot-only achievable scorer 的临时残余协方差不能直接等同此每轮数据反馈模型。

## 6. 有区分力的工程验收

- 均匀分布：mu=0、v=Pd；点质量：mu=a、v=0；非均匀二点分布使用解析均值方差。不能仅通过重复实现公式的测试。
- 复高斯标量 QPSK：四状态精确枚举验证 logits 温度和有限矩；明确噪声采用 E|w|²，总复数方差分母不额外带2。
- 全局功率缩放 c>0：x/constellation 乘 sqrt(c)，sigma²乘 c，p 不变，mu乘 sqrt(c)，v乘 c；C/Gram 的预期单位一致。
- disabled/T=1 对既定 CUDA 工程帧验证完整 H/x/sigma/errors 一致；原 observer-only baseline 回放保留。CPU lstsq 现存微小不确定性不能用放宽 GPU gate 掩盖。
- 校准字段零温度/NaN/错长度、split 哈希碰撞、空 fit/val、非法概率/显著负方差：显式失败，非默认退回 T=1。
- G：小 N dense trace 与结构 Q 对照，包含 displacement collision 反例；固定 mu/v/S 的复数扰动与旧 g 对照 J_prox 不增；v=0 reduction；Hermitian/PSD 容差。
- V：v非负时 C Hermitian 且 Cholesky 成功；point mass reduction；矩阵实现和 `H @ (v*(Hᴴ@z))+sigma²*z` 一致。
- 真值仅在校准/观测闭包和评估中；部署配置只加载已冻结 T/容量/参数。artifact 必须存 source/checkpoint/LDPC/calibration 哈希、fit/validation IDs、选择规则、T、功率/dtype/运行环境。

结论：先做 DA-LS-only 温度均值原型有明确价值与边界；其有限 v 只是可验证统计量。下一层 G 可以借当前整数位移结构成为极小、目标清楚的方差入口。完整 V 需要另一个明确消费协方差的接口，不能通过改 sigma² 名称补齐。
