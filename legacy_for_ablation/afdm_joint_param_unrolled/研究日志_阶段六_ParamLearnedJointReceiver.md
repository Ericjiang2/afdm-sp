# 研究日志：阶段六 Param-Learned Joint Receiver

## 2026-03-19

### 本日目标

从 `afdm_sp_joint_unrolled` 分出一个新项目，专门验证：

> 保留传统 Joint 主骨架，只学习少量参数，是否足以解决当前的闭环失配问题。

### 新项目

- 目录：`afdm_joint_param_unrolled`

### 本次新增文件

- `afdm_joint_param.py`
- `train_joint_param.py`
- `verify_joint_param.py`
- `实现方案_阶段六_ParamLearnedJointReceiver.md`
- `研究日志_阶段六_ParamLearnedJointReceiver.md`

### 方法边界

v1 只学习：

- `lambda_t`
- `alpha_t`
- `beta_t`

明确不做：

- support proposal
- hard pruning
- add/drop support
- detector 内部结构改写
- CNN 信道修正

### 与阶段五的关系

阶段五的 pathology slices 已归档，当前不继续沿 expanded OMP / hard pruning 主线推进。

保留引用文档：

- `afdm_sp_joint_unrolled_backup_pre_expanded_rollback_20260312_232814/afdm_sp_joint_unrolled/实现方案_阶段五_JointSparseUnrolled.md`

### 当前实现要点

- `OMP` 初始化 support
- support 固定
- 可微 ridge refit 替代原本更重的 teacher/proposal 驱动逻辑
- detector 复用 `SparseMPDetector`，但其参数冻结
- 共享小 strategy net 输出每轮 `lambda / alpha / beta`

### 本地实现备注

当前本地旧项目里的历史 teacher cache / raw labels 文件存在损坏风险，因此阶段六训练脚本支持三种数据来源：

- `raw_labels`
- `teacher_cache`
- `online`

其中：

- `auto` 会依次尝试 `raw_labels -> teacher_cache -> online`
- `online` 主要服务本地 smoke
- 云端正式训练仍优先建议使用正常的旧 teacher labels

### 待完成验证

1. `py_compile`
2. 小规模训练 smoke
3. 小规模验证 smoke
4. 把首个 smoke 结果写回本日志

### 当日完成：静态检查

- `py_compile` 已通过：
  - `afdm_joint_param.py`
  - `train_joint_param.py`
  - `verify_joint_param.py`

### 当日完成：训练 smoke

运行命令：

```bash
conda run -n CE python afdm_joint_param_unrolled/train_joint_param.py \
  --dataset-source online \
  --frames-per-snr 2 \
  --epochs 1 \
  --batch-size 4 \
  --val-batch-size 4 \
  --snr-list 5 10 15 20 25 \
  --joint-dir afdm_joint_param_unrolled/outputs_joint_param_smoke \
  --num-outer-iters 3 \
  --num-mp-layers 3
```

结果摘要：

- 数据源：`online`
- 总帧数：`10`
- trainable params：`1350`
- trainable parameter groups 仅来自 `strategy_net`
  - `strategy_net.base_raw`
  - `strategy_net.net.*`
- `Epoch[1/1]`
  - `tr_loss=2.815e+00`
  - `va_loss=3.173e+00`
  - `ber=0.4604 / 0.4924`
  - `lambda=3.439e-04 / 3.538e-04`
  - `alpha=0.700 / 0.702`
  - `beta=0.995 / 0.995`
  - `lambda_L/H=4.633e-04 / 2.695e-04 | 4.714e-04 / 2.629e-04`

落盘文件：

- `outputs_joint_param_smoke/param_joint_model.pt`
- `outputs_joint_param_smoke/param_joint_results.pkl`

结论：

- 训练链路已打通
- `lambda / alpha / beta` 日志正常输出
- 参数目前仍贴近 classical anchor，符合 smoke 阶段预期

### 当日完成：验证 smoke

运行命令：

```bash
conda run -n CE python afdm_joint_param_unrolled/verify_joint_param.py \
  --joint-dir afdm_joint_param_unrolled/outputs_joint_param_smoke \
  --frames 2 \
  --snr 15 25 \
  --num-outer-iters 3 \
  --num-mp-layers 3
```

结果摘要：

- `15 dB`
  - `JointOMPMP = 1.8555e-02`
  - `ParamJoint = 4.7168e-01`
  - `LMMSE = 6.2012e-02`
  - `lambda=2.934e-04`
  - `alpha=0.702`
  - `beta=0.995`
- `25 dB`
  - `JointOMPMP = 3.9062e-03`
  - `ParamJoint = 5.1367e-01`
  - `LMMSE = 4.6875e-02`
  - `lambda=2.588e-04`
  - `alpha=0.702`
  - `beta=0.995`

额外备注：

- `OAMP` baseline 在本机 `MPS` 上因 complex solve 不支持而被自动跳过，不影响 `JointOMPMP` 和 `ParamJoint` 主对比
- 当前 smoke 仅用于验证“脚手架、训练、验证、结果落盘”是否全部打通，不用于任何性能判断

### 当前结论

- 阶段六新项目已经完成最小可运行版本
- 本地 legacy teacher cache / raw labels 文件存在损坏风险，因此 smoke 使用 `online` 数据源完成
- 下一步应在云端正常数据资产上运行：
  - `frames-per-snr=20`
  - `epochs=1`
  - `snr=5/10/15/20/25`
- smoke 结果表明：当前模型还只是“结构可跑”，距离有效性能版本还有明显空间，后续重点看参数是否能在正式训练中从 anchor 偏移并改善 `15/20/25 dB`

### 当日完成：云端训练 smoke

运行环境：

- 机器：云端 `cuda`
- 数据源：`teacher_cache`
- 路径：`/home/18736049201eric/afdm_sp_joint_unrolled/outputs_joint_unrolled/teacher_sparse_traj_cache.pt`

运行命令：

```bash
python /home/18736049201eric/afdm_joint_param_unrolled/train_joint_param.py \
  --dataset-source teacher_cache \
  --teacher-cache /home/18736049201eric/afdm_sp_joint_unrolled/outputs_joint_unrolled/teacher_sparse_traj_cache.pt \
  --stats /home/18736049201eric/afdm_sp_joint_unrolled/outputs_n512/global_stats.pkl \
  --joint-dir /home/18736049201eric/afdm_joint_param_unrolled/outputs_joint_param \
  --frames-per-snr 20 \
  --snr-list 5 10 15 20 25 \
  --epochs 1
```

结果摘要：

- 数据源：`teacher_cache`
- 总帧数：`100`
- trainable params：`1350`
- `Epoch[1/1]`
  - `tr_loss=6.328e-01`
  - `va_loss=5.962e-01`
  - `ber=0.0623 / 0.0583`
  - `lambda=2.711e-04 / 2.679e-04`
  - `alpha=0.701 / 0.704`
  - `beta=0.995 / 0.995`
  - `lambda_L/H=3.713e-04 / 1.948e-04 | 3.675e-04 / 1.926e-04`
  - `alpha_L/H=0.701 / 0.701 | 0.703 / 0.704`
  - `beta_L/H=0.995 / 0.995 | 0.995 / 0.995`

阶段性判断：

- 云端正式数据资产上，阶段六训练链路稳定
- `lambda` 已开始学出明显的 low/high SNR 分离
- `alpha` 和 `beta` 仍基本贴近初始 anchor，当前还没有明显学起来

### 当日完成：云端验证 smoke

运行命令：

```bash
python /home/18736049201eric/afdm_joint_param_unrolled/verify_joint_param.py \
  --joint-dir /home/18736049201eric/afdm_joint_param_unrolled/outputs_joint_param \
  --baseline-dir /home/18736049201eric/afdm_sp_joint_unrolled/outputs_n512 \
  --frames 100 \
  --snr 15 20 25 \
  --num-outer-iters 5 \
  --num-mp-layers 6 \
  --max-active-atoms 25 \
  --k-leak 2
```

结果摘要：

- `15 dB`
  - `JointOMPMP = 1.8291e-02`
  - `ParamJoint = 1.9971e-02`
  - `OAMP = 7.8506e-02`
  - `LMMSE = 1.1757e-01`
  - `lambda=2.199e-04`
  - `alpha=0.704`
  - `beta=0.995`
- `20 dB`
  - `JointOMPMP = 1.0215e-02`
  - `ParamJoint = 4.9805e-03`
  - `OAMP = 7.4268e-02`
  - `LMMSE = 1.1729e-01`
  - `lambda=1.982e-04`
  - `alpha=0.704`
  - `beta=0.995`
- `25 dB`
  - `JointOMPMP = 5.4980e-03`
  - `ParamJoint = 4.5117e-03`
  - `OAMP = 6.7617e-02`
  - `LMMSE = 1.1509e-01`
  - `lambda=1.917e-04`
  - `alpha=0.704`
  - `beta=0.995`

相对 `JointOMPMP` 的对比：

- `15 dB`：`ParamJoint` 略弱于 baseline
- `20 dB`：`ParamJoint` 明显优于 baseline
- `25 dB`：`ParamJoint` 小幅优于 baseline

阶段性结论：

- 阶段六路线已被初步验证有效
- “保留传统 Joint 骨架，只学习少量参数”已经能在 `20/25 dB` 超过 classical `JointOMPMP`
- 当前主要学出来的是 `lambda` 自适应，而不是 `alpha/beta`
- 低 SNR (`15 dB`) 仍未改善，说明仅靠 `lambda/alpha/beta` 这 3 个量，还不足以完全解决低 SNR 闭环问题
- 当前版本已经具备继续做消融的价值，下一步最值得验证的是：
  - `learn lambda only`
  - `learn lambda + alpha + beta`
  以判断当前增益是否几乎全部来自 learned `lambda`

### 当日继续：Ablation First 接口落地

本轮代码层新增统一消融接口：

- `--learned-param-set {fixed, lambda_only, alpha_beta_only, lambda_alpha_beta}`

行为约束：

- `fixed`
  - `lambda/alpha/beta` 全固定为 anchor
- `lambda_only`
  - 只允许 `lambda` 偏离 anchor
- `alpha_beta_only`
  - 只允许 `alpha/beta` 偏离 anchor
- `lambda_alpha_beta`
  - 完整 Stage 6 版本

命名约束：

- checkpoint:
  - `param_joint_fixed.pt`
  - `param_joint_lambda_only.pt`
  - `param_joint_alpha_beta_only.pt`
  - `param_joint_lambda_alpha_beta.pt`
- verify:
  - `param_joint_fixed_verify_results.pkl`
  - `param_joint_lambda_only_verify_results.pkl`
  - `param_joint_alpha_beta_only_verify_results.pkl`
  - `param_joint_lambda_alpha_beta_verify_results.pkl`

本轮 4 组实验表：

| Mode | 训练 | 验证 | 目标 |
| --- | --- | --- | --- |
| `fixed` | 待跑 | 待跑 | 固定 anchor 参考线 |
| `lambda_only` | 待跑 | 待跑 | 检验收益是否主要来自 `lambda` |
| `alpha_beta_only` | 待跑 | 待跑 | 检验闭环参数单独是否有效 |
| `lambda_alpha_beta` | 待跑 | 待跑 | 与当前完整版本对照 |

本轮仍然不做：

- 大帧数稳定性确认
- 15 dB 轨迹病理切片
- 新结构扩展

### 当日继续：Ablation First 正式结果冻结

本轮统一使用以下协议：

- 训练数据：`teacher_cache`
- 训练预算：`frames-per-snr = 20`，`snr = 5/10/15/20/25`，`epochs = 1`
- 验证协议：`frames = 100`，`snr = 15/20/25`
- 对照基线：`JointOMPMP`

#### 四组 verify 结果

| Mode | 15 dB | 20 dB | 25 dB | 参数摘要 |
| --- | --- | --- | --- | --- |
| `JointOMPMP` | `1.8291e-02` | `1.0215e-02` | `5.4980e-03` | classical baseline |
| `fixed` | `2.0039e-02` | `4.9707e-03` | `4.5117e-03` | `lambda≈2.205e-04/1.988e-04/1.923e-04`, `alpha=0.700`, `beta=0.995` |
| `lambda_only` | `2.0039e-02` | `4.9707e-03` | `4.5117e-03` | `lambda≈2.202e-04/1.985e-04/1.920e-04`, `alpha=0.700`, `beta=0.995` |
| `alpha_beta_only` | `1.9990e-02` | `4.9707e-03` | `4.5215e-03` | `lambda≈2.205e-04/1.987e-04/1.922e-04`, `alpha≈0.703/0.703/0.704`, `beta=0.995` |
| `lambda_alpha_beta` | `1.9990e-02` | `4.9707e-03` | `4.5215e-03` | `lambda≈2.201e-04/1.984e-04/1.919e-04`, `alpha≈0.703/0.703/0.704`, `beta=0.995` |

证据文件：

- `outputs_joint_param_ablation/logs/verify_fixed.log`
- `outputs_joint_param_ablation/logs/verify_lambda_only.log`
- `outputs_joint_param_ablation/logs/verify_alpha_beta_only.log`
- `outputs_joint_param_ablation/logs/verify_lambda_alpha_beta.log`

#### 训练日志侧观察

来自 `outputs_joint_param_ablation/logs/train_*.log`：

- `fixed`
  - `trainable_params = 0`
  - `lam=2.713e-04/2.687e-04`
  - `alpha=0.700/0.700`
  - `beta=0.995/0.995`
- `lambda_only`
  - `trainable_params = 1347`
  - 训练后结果与 `fixed` 几乎完全重合
- `alpha_beta_only`
  - `alpha` 仅从 `0.700` 偏到 `0.701~0.703`
  - `beta` 仍保持 `0.995`
- `lambda_alpha_beta`
  - 与 `alpha_beta_only` 在本轮预算下几乎不可区分

这说明本轮真正被使用到的 residual 自由度非常弱，尤其 `alpha/beta` 基本没有离开安全常数附近。

#### 当前已证实

- `Stage6 fixed` 已经能够在 `20/25 dB` 明显优于 `JointOMPMP`
- 四组 Stage 6 ablation 在 `20/25 dB` 都优于 `JointOMPMP`
- `fixed` 与 `lambda_only` 在当前预算下几乎完全重合
- `alpha_beta_only` 与 `lambda_alpha_beta` 也几乎完全重合
- 当前 Stage 6 的主收益首先来自 **Stage 6 scaffold 本身**，而不是 residual 参数学习

#### 当前未证实

- 尚未证实 `learned lambda` 在当前强 anchor 之上带来了稳定额外收益
- 尚未证实 `alpha/beta` 的闭环调度在当前训练预算下被真正利用
- 尚未证实 Stage 6 的 learnable residual 能在 `15 dB` 弥补低 SNR gap

#### 阶段性结论

阶段六当前最稳的说法不是“学习少量参数已经全面超过传统 Joint”，而是：

- 保留传统 Joint 高层骨架、换成 Stage 6 这一套更现代的实现 scaffold 后，中高 SNR 已经能稳定超过旧 `JointOMPMP`
- 但在当前 `1 epoch + 100 frame verify` 设置下，额外的 `lambda/alpha/beta` residual 学习尚未被单独证实是主要收益来源
- 因此，阶段六当前更像是在证明 **scaffold modernization 有效**，而不是“全局小标量 residual 学习已经解决了主要瓶颈”
