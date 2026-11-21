# S0：可执行模型与信息边界

日期：2026-09-06。作用域：当前 E1 回放及其后续内部比较；不变更已接受论文结论。

## 变量、单位与接口

| 数学量 | 实际接口 | 单位/条件 |
|---|---|---|
| 未缩放 x | E1 `data_qam = qpsk_map(coded, scale=1)` | 单位平均能量 QPSK；实虚各 ±1/√2 |
| 已缩放 x_d | `const_data=sqrt(1-rho)*QPSK`、`out_g['x_soft']` | 发射数据功率单位；E1 rho=.5，每实分量幅度 .5 |
| p / 已缩放导频 | `sys_obj._zc_seq` / `pilot_scaled=sqrt(rho)*p` | 全域 ZC；不是单个中心叠加脉冲 |
| u | `x_sp=pilot_scaled+sqrt(P_d)*data_qam` | 总发射符号；总功率为统计期望 1，单帧交叉项不保证恰为 0 |
| H | `generate_channel_matrix()[0]` | DAFT 域；非零信道每帧 Frobenius 范数 √N |
| y | `y_daft=H_true@x_sp+sqrt(sigma2)*noise` | 接收功率单位；默认 host complex128 |
| sigma² | E1 `10**(-snr/10)` | E|w|²，实虚各 sigma²/2；不是每实维方差 |
| Phi | `construct_sensing_matrix(N,pilot_scaled,...)` | 第列为对应路径算子作用于已缩放导频；列索引 l(2k_max+1)+(k+k_max) |
| Gaussian mu,v | BP `mu_post,var_post` | 缩放数据单位；全边高斯精度聚合并加入高斯先验，不是有限星座后验矩 |
| 有限星座 mu,v | S4 待新增明确接口 | 应由概率求 E[x]、E|x|²−|E[x]|²；不得重命名旧返回值 |
| LLR | `e1_ldpc.demap_llr(mu,var,amp=.5)` | log P(bit=0)/P(bit=1)，实虚分别 4 amp Re/Im(mu)/v，截断 ±20 |
| FER | 每帧译码信息位错误数 >0 | 与 `decode_ok` 的校验方程成功标志不同；错误有效码字仍算 FER |

源文件：`afdm_env.py`、`e1_ldpc_coded_eval.py`、`mp_detect_bp_torch.py`、`e1_ldpc.py`，哈希见 provenance。

BP 内部星座投影使用 `exp(-distance²/(2*var_ext))`；最终返回仍是高斯精度聚合。该系数和先验语义留给 S4 标量模型验证，S1 不改变历史接收机。

## 物理路径、展开条目与支撑

当前模拟器先对时延取整并裁剪，再将连续多普勒裁剪至设计区间，按 k_leak=2 展开最多五个整数抽头。每路径展开向量先归一化；越界条目和相对峰值功率低于 .01 的条目丢弃；最后整个 H 归一化。它是截断的整数表示，不能把当前 H 称为未经截断的连续多普勒真信道。

- `P_paths`：请求物理路径数；实际物理条目数取返回字典 `taps`。
- `_P_actual` / `P_actual`：展开条目总数；重复 (l,k) 仍重复计数。
- 唯一字典支撑：对相同 (l,k) 的复增益求和后定义；抵消条目不得重复算独立可恢复路径。
- `K_prop`：OMP/F2-P 提名和剪枝后、簇扩展前的唯一列数。
- `K_active`：`expand_cluster_support` 扩展合并后、实际参与 DA-LS 的唯一列数；可大于 K_prop。
- `P_eff`：按 BP 实际 `abs(H)>=1e-4` 边表报告边数/每行度数；不以物理路径数代替。

八个本地实信道样本的 `(请求物理路径数,展开条目数,唯一(l,k)数)`：
`(8,21,21),(8,22,22),(8,29,29),(8,16,11),(8,22,22),(8,21,21),(8,18,18),(8,23,23)`。
证据：`capacity-probe.json`。仅展示三种计数确实不同，不足以选择部署 K_cap。

**纠正原规划容量假设**：旧 E1 将每帧 `_P_actual` 传给 OMP 和 `module.cfg.n_paths`，带有模拟真值容量信息。历史回放保留并标记 `capacity_source=simulator_expanded_tap_count`。新方法/强基线共用 D_cal 选定的固定 K_cap∈{8,16,24,32,40}；不得用测试帧真值选 K。

旧 F2-P：候选 M=96、两轮，每轮最多加 4，簇扩展前临时最多 K_prop+8，最后剪枝并保护 2 个新增列。随后 `expand_cluster_support` 再为每个已选列加入 ±2 多普勒邻居（初始增益零），后续 DA-LS 可激活它们。因此扩展后最多 min(Q,5 K_prop) 列，不能声称 n_paths 就是实际活跃容量。新动作门控必须核对簇扩展后的支撑及目标；S3/S5 分别登记 K_prop 与 K_active 上限，未实现前不宣称旧臂符合新 K_cap。旧顺序加入保留原 OMP 列，可能容量更大；只能作为独立标记的诊断臂，公平适配必须限制共同最终容量。

## 当前评分路径与计时边界

`geom` 以普通 LS 残差定义几何特征，再查校准先验 log odds；`achievable` 在主 forward 外额外运行 OMP 与 LS 建立 Hhat0，然后调用名字为 `make_genie_lambda` 的工厂。该臂传入的是 Hhat0，不是真 H。

该工厂用 CPU complex128 构造 `(1-rho) Hhat0 Hhat0ᴴ`，各调用加入 sigma² I 并 Cholesky 白化残差和候选全部右端项。残差仍由普通 LS 得到；它没有对活跃列和候选进行一致加权残差化。这是 S3 待检验对象，不能直接称现行 scorer 为精确加权 OLS。

真实 BP 绑定以运行记录为准：`loop9_cache_features._fast_bp`。源码注释中的中间 shim 不是最终绑定证据。主 Torch 接收机配置 complex64；BP 包装内部会提升到 complex128；不同臂输入精度必须分别报告。

成本必须包括外部 OMP、闭包创建、全部求解/复制、主 forward、额外末次 BP、LLR 与 LDPC。首版 trace 记录 host y→译码结束的保守总时延（含传输与 finite 检查），排除信道模拟/哈希/落盘。它尚不是分离了输入传输的正式设备就绪计时；预算文件须标明此限制。

## 真值隔离与配对

真 H、真实信息位和噪声仅供模拟、离线诊断与评估。旧 oracle 容量仅用于历史回放；未来部署臂输入清单不含这些字段。achievable 的校准先验可在 D_cal 使用标签，测试在线调用不能使用标签。

历史回放保留旧 master RNG 逐 SNR 消耗顺序；单跑 SNR8 不等于旧多 SNR 运行的 SNR8 前缀。新增臂顺序使用独立 RNG，不消耗输入流。哈希记录原始 y/H/噪声/信息位/码字/导频；同源哈希相等不代表各臂实际 dtype 相同。

后续开发/校准/确认使用 parent 的独立 SeedSequence 分割；本次历史帧不得当独立确认数据。物理位置诊断的一对一匹配须在 S2 运行前固定，不能从误差案例反推容差。
