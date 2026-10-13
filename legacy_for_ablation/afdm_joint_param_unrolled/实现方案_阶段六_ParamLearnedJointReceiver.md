# 实现方案：阶段六 Param-Learned Joint Receiver

## 1. 阶段目标

在不破坏传统 Joint 框架主骨架的前提下，验证当前性能瓶颈是否主要来自：

- 超参数失配
- 外环闭环校准失配
- detector 到 refit 的反馈信任度失配

阶段六明确收窄为：

- 保留 `OMP init + support expansion + fixed support + DA-LS/DA-LMMSE + MP`
- 不引入 support proposal
- 不引入 hard pruning
- 不引入 add/drop support
- 不引入 CNN 修正器
- 不改 detector 内部结构
- 只学习每轮 3 个量：`lambda_t / alpha_t / beta_t`


## 2. 当前判断

阶段五归档的 pathology slices 结论表明：

- `A_S` 条件数和互相干度在 25 dB 下没有达到“病态爆炸”级别
- 固定 support 的 refit 对微小扰动是稳定的，不是爆炸器
- detector 在固定真信道下并不会天然失效

因此阶段六的核心假设是：

> 当前主瓶颈更像是闭环中的参数与校准失配，而不是单个模块完全不可用。

阶段五的诊断细节保留在备份目录中的：

- `afdm_sp_joint_unrolled_backup_pre_expanded_rollback_20260312_232814/afdm_sp_joint_unrolled/实现方案_阶段五_JointSparseUnrolled.md`


## 3. v1 方法定义

### 3.1 Receiver 主线

每个样本的 forward 固定为：

1. `Iter-1`：解析 `OMP` 初始化 support，并按 `k_leak` 做 cluster expansion
2. 后续迭代：support 固定，不再 add/drop
3. 每轮执行：
   - 用上一轮 detector soft mean 构造 `x_total_refit`
   - 在固定 support 上做 ridge refit
   - 重建 `H`
   - 用冻结的 `SparseMPDetector` 做 data detection
   - 更新 `sigma_eff`

### 3.2 可学习参数

每轮仅学习三个标量：

- `lambda_t`
  - refit 正则强度
- `alpha_t`
  - gain/channel 外环阻尼
- `beta_t`
  - detector 软反馈进入 data-aided refit 的信任门控

物理绑定固定为：

- `lambda_t = sigma_eff * softplus(out_0) + 1e-4`
- `alpha_t = sigmoid(out_1)`
- `beta_t = sigmoid(out_2)`

### 3.3 Strategy Net

共享一个小型 strategy net，不做 per-iter 大网络：

- 输入 5 维：
  - `log(sigma_eff)`
  - `log(residual_energy_prev)`
  - `support_ratio`
  - `mean(v_x)`
  - `iter_frac`
- 输出 3 维残差，叠加到 classical anchor 上

初始化 anchor：

- `lambda_ls_factor = 1e-3`
- `alpha = 0.7`
- `beta ~= 1.0`

当前 ablation 接口：

- `learned_param_set = fixed`
- `learned_param_set = lambda_only`
- `learned_param_set = alpha_beta_only`
- `learned_param_set = lambda_alpha_beta`

接口语义固定为：

- 结构完全不变
- 只控制哪些连续超参数允许偏离 anchor
- 不修改 detector 结构
- 不修改 loss
- 不引入新的 support 管理分支

### 3.4 非学习模块

以下部分在 v1 保持非学习：

- `OMP` 支撑初始化
- support expansion
- fixed-support 机制
- detector 内部结构与其 learnable scalars
- CE backbone / proposal / refiner


## 4. 代码结构

新项目目录：

- `afdm_joint_param_unrolled/`

新增主文件：

- `afdm_joint_param.py`
  - `ParamLearnedJointReceiver`
  - `ParamStrategyNet`
  - `build_param_joint_model`
  - `compute_param_joint_loss`
- `train_joint_param.py`
  - 单阶段 end-to-end supervised 训练
- `verify_joint_param.py`
  - `JointOMPMP` vs `ParamJoint` 对比验证

输出目录统一为：

- `outputs_joint_param/`


## 5. 数据协议

训练只使用 supervised 字段：

- `X_features`
- `y_received`
- `x_pilot_frames`
- `x_data_true`
- `bits_true`
- `sigma_w2`
- `snr_db`

不依赖 trajectory teacher 字段。

默认优先复用旧项目中的 teacher labels / cache：

- `afdm_sp_joint_unrolled/outputs_joint_unrolled/teacher_labels/teacher_all_snr_traj.npz`
- `afdm_sp_joint_unrolled/outputs_joint_unrolled/teacher_sparse_traj_cache.pt`

若历史文件损坏或不可读，可切到在线生成 supervised 样本做 smoke。


## 6. 训练协议

### 6.1 默认工况

- SNR：`[5, 10, 15, 20, 25]`
- 单阶段训练
- 主损失：final BCE on bits
- 辅损失：final symbol MSE
- 当前下一轮主任务：`Ablation First`
  - `fixed`
  - `lambda_only`
  - `alpha_beta_only`
  - `lambda_alpha_beta`

### 6.2 日志要求

每轮至少输出：

- `lambda mean`
- `alpha mean`
- `beta mean`
- `lambda_L/H`
- `alpha_L/H`
- `beta_L/H`

其中：

- Low：`snr <= 10`
- High：`snr >= 20`

每个模式的产物命名包含 `learned_param_set`，避免覆盖：

- `param_joint_fixed.pt`
- `param_joint_lambda_only.pt`
- `param_joint_alpha_beta_only.pt`
- `param_joint_lambda_alpha_beta.pt`


## 7. 验证协议

主对比项：

- `JointOMPMP`
- `ParamJoint`

可选项：

- `OAMP`
- `LMMSE`

主验收观察：

- `20/25 dB` 不明显弱于 `JointOMPMP`
- `15 dB` 是否开始出现稳定改善
- `lambda/alpha/beta` 是否学出工况差异，而不是塌成常数
- 当前下一轮优先回答：
  - `lambda_only ≈ lambda_alpha_beta` 是否成立
  - `alpha_beta_only` 是否几乎无效
  - `fixed -> lambda_only` 的收益是否已覆盖大部分改善


## 8. 风险点

阶段六的潜在风险主要有三类：

- 只学超参数仍不足以突破 classical skeleton 的上限
- ridge refit 的可微实现与 classical CPU micro-kernel 存在数值差异
- detector 冻结后，提升空间可能主要集中在 `alpha / beta`，而不是 `lambda`


## 9. 阶段六验收

### 静态与行为

- `py_compile` 通过
- strategy net 输出有限且范围合法
- support 在 `Iter-1` 后固定
- detector 参数保持冻结

### 训练 smoke

- `frames-per-snr=20`
- `epochs=1`
- 日志必须出现 `lambda / alpha / beta`
- `--learned-param-set` 四种模式都能单独产出 checkpoint

### 验证 smoke

- 表中同时出现 `JointOMPMP` 与 `ParamJoint`
- 结果文件中保存每个 SNR 的参数均值
- `--learned-param-set` 四种模式都能单独选择对应模型


## 10. 当前状态

- 项目脚手架已创建
- 核心 receiver / train / verify 入口已建立
- 研究日志另存于：
  - `研究日志_阶段六_ParamLearnedJointReceiver.md`
