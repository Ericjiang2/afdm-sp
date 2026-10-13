# 研究日志：阶段七 Strict Traditional Param-Joint

## 2026-03-19

### 本日目标

在 Stage 6 旁边补一条“严格传统骨架 + learnable 经典超参数”的新分支，用来做更干净的三方对照：

- `JointOMPMP`
- `TradParamJoint`
- `Stage6ParamJoint`

### 本次新增文件

- `afdm_traditional_param.py`
- `train_traditional_param.py`
- `verify_traditional_param.py`
- `compare_joint_families.py`
- `实现方案_阶段七_TraditionalParamJoint.md`
- `研究日志_阶段七_TraditionalParamJoint.md`

### 设计决策

#### 为什么要做阶段七

阶段六已经出现了一个重要信号：

- `Stage6 fixed` 在部分 SNR 上也能优于旧 `JointOMPMP`

这说明：

- Stage 6 的 scaffold 本身可能已经比旧传统 joint 更强

因此需要单独补一条真正贴近旧 `JointOMPMP` 数值流程的 learnable 分支，避免把：

- scaffold 改进
- 参数学习收益

混在一起。

#### 本次固定的约束

- 保留旧传统 joint 的高层数值流程
- 不引入 `beta` 门控
- 只学习旧算法已有的标量：
  - `lambda_ls_factor`
  - `gamma_h`
  - `gamma_x`
  - `pic_damp`
- 训练态允许 straight-through hard QPSK
- 训练和验证都使用固定 outer/inner iter

### 当前实现摘要

- 第一轮 support init 使用旧 baseline 的 numpy OMP 逻辑
- 后续 fixed-support refit 用 torch 可微 ridge solve 复刻
- detector 路线为 classical `PIC`
- channel damping、channel sparsification、symbol damping、adaptive noise update 已接入
- 与阶段六平行组织，不改 Stage 6 已跑通入口

### 计划中的首轮实验

#### 训练 smoke

- `teacher_cache`
- `frames-per-snr = 20`
- `epochs = 1`
- `snr = 5/10/15/20/25`

#### 验证 smoke

- `TradParam fixed`
- `TradParam classical_full`
- `Stage6 lambda_alpha_beta`
- `JointOMPMP`
- `frames = 100`
- `snr = 15/20/25`

### 待补记录

后续需要把以下结果写回本日志：

1. `py_compile` 结果
2. `TradParam fixed` 训练/验证 smoke
3. `TradParam classical_full` 训练/验证 smoke
4. 三方统一对比表
5. 初步判断：
   - `TradParam fixed` 是否贴近 `JointOMPMP`
   - `TradParam classical_full` 是否从传统骨架内拿到收益
   - `Stage6` 的优势是否更多来自 scaffold

### 当日完成：静态检查

- `py_compile` 已通过：
  - `afdm_traditional_param.py`
  - `train_traditional_param.py`
  - `verify_traditional_param.py`
  - `compare_joint_families.py`

### 当日完成：训练 smoke

#### `TradParam fixed`

运行命令：

```bash
conda run -n CE python afdm_joint_param_unrolled/train_traditional_param.py \
  --dataset-source online \
  --frames-per-snr 1 \
  --epochs 1 \
  --batch-size 2 \
  --val-batch-size 2 \
  --snr-list 5 10 15 20 25 \
  --traditional-dir afdm_joint_param_unrolled/outputs_traditional_param_smoke \
  --num-outer-iters 2 \
  --pic-iters 2 \
  --max-active-atoms 10 \
  --k-leak 1 \
  --learned-param-set fixed
```

结果摘要：

- 数据源：`online`
- 总帧数：`5`
- trainable params：`0`
- `Epoch[1/1]`
  - `tr_loss=1.523e+01`
  - `va_loss=1.523e+01`
  - `ber=0.1041 / 0.1041`
  - `lambda=1.103e-04`
  - `gamma_h=0.700`
  - `gamma_x=0.600`
  - `pic_damp=0.500`

结论：

- `fixed` 模式行为正确
- 四个经典参数都稳定固定在 anchor

#### `TradParam classical_full`

运行命令：

```bash
conda run -n CE python afdm_joint_param_unrolled/train_traditional_param.py \
  --dataset-source online \
  --frames-per-snr 1 \
  --epochs 1 \
  --batch-size 2 \
  --val-batch-size 2 \
  --snr-list 5 10 15 20 25 \
  --traditional-dir afdm_joint_param_unrolled/outputs_traditional_param_smoke \
  --num-outer-iters 2 \
  --pic-iters 2 \
  --max-active-atoms 10 \
  --k-leak 1 \
  --learned-param-set classical_full
```

结果摘要：

- trainable params：`1380`
- `Epoch[1/1]`
  - `tr_loss=1.521e+01`
  - `va_loss=1.492e+01`
  - `ber=0.1035 / 0.1043`
  - `lambda=1.102e-04 / 1.100e-04`
  - `gamma_h=0.699 / 0.697`
  - `gamma_x=0.599 / 0.597`
  - `pic_damp=0.499 / 0.497`

结论：

- `classical_full` 模式训练链路已打通
- 参数可以偏离 anchor，说明可学习路径有效

### 当日完成：验证 smoke

运行命令：

```bash
conda run -n CE python afdm_joint_param_unrolled/verify_traditional_param.py \
  --traditional-dir afdm_joint_param_unrolled/outputs_traditional_param_smoke \
  --frames 2 \
  --snr 15 25 \
  --num-outer-iters 2 \
  --pic-iters 2 \
  --max-active-atoms 10 \
  --k-leak 1 \
  --learned-param-set fixed
```

结果摘要：

- `15 dB`
  - `JointOMPMP = 3.6133e-02`
  - `TradParam = 5.2246e-02`
- `25 dB`
  - `JointOMPMP = 2.5391e-02`
  - `TradParam = 9.3750e-02`

补充说明：

- 本次只验证脚手架和结果落盘，不做性能判断
- `OAMP` baseline 在本机 `MPS` 上因 complex solve 不支持被跳过，不影响主对比链路

### 当日完成：三方 compare smoke

为匹配当前本地 Stage 6 `outputs_joint_param_ablation` 的 `outer_iters=5` ckpt，额外补跑了一条传统 `fixed` smoke：

```bash
conda run -n CE python afdm_joint_param_unrolled/train_traditional_param.py \
  --dataset-source online \
  --frames-per-snr 1 \
  --epochs 1 \
  --batch-size 2 \
  --val-batch-size 2 \
  --snr-list 5 10 15 20 25 \
  --traditional-dir afdm_joint_param_unrolled/outputs_traditional_param_compare_smoke \
  --num-outer-iters 5 \
  --pic-iters 2 \
  --max-active-atoms 10 \
  --k-leak 1 \
  --learned-param-set fixed
```

然后运行统一 compare：

```bash
conda run -n CE python afdm_joint_param_unrolled/compare_joint_families.py \
  --stage6-dir afdm_joint_param_unrolled/outputs_joint_param_ablation \
  --traditional-dir afdm_joint_param_unrolled/outputs_traditional_param_compare_smoke \
  --frames 2 \
  --snr 15 25 \
  --num-outer-iters 5 \
  --num-mp-layers 6 \
  --pic-iters 2 \
  --max-active-atoms 10 \
  --k-leak 1 \
  --stage6-param-set fixed \
  --traditional-param-set fixed
```

结果摘要：

- `15 dB`
  - `JointOMPMP = 2.9297e-03`
  - `TradParam = 4.3945e-02`
  - `Stage6 = 4.6680e-01`
- `25 dB`
  - `JointOMPMP = 0.0000e+00`
  - `TradParam = 7.8613e-02`
  - `Stage6 = 4.9463e-01`

补充说明：

- 这仍然是极小样本 smoke，不能拿来判断优劣
- 这轮的意义是确认 `compare_joint_families.py` 能同时加载三条链并统一产表

### 当日继续：云端 strict traditional 结果冻结

本轮统一使用以下协议：

- 训练数据：`teacher_cache`
- 训练预算：`frames-per-snr = 20`，`snr = 5/10/15/20/25`，`epochs = 1`
- 验证协议：`frames = 100`，`snr = 15/20/25`
- 对照基线：`JointOMPMP`

#### 云端训练结果

来自：

- `outputs_traditional_param/logs/train_traditional_fixed.log`
- `outputs_traditional_param/logs/train_traditional_classical_full.log`

`TradParam fixed`

- `trainable_params = 0`
- `tr_loss=3.586e+01`
- `va_loss=3.212e+01`
- `ber=0.0538/0.0591`
- `lam=1.101e-04/1.126e-04`
- `gh=0.700/0.700`
- `gx=0.600/0.600`
- `pd=0.500/0.500`

`TradParam classical_full`

- `trainable_params = 1380`
- `tr_loss=3.572e+01`
- `va_loss=3.175e+01`
- `ber=0.0535/0.0590`
- `lam=1.103e-04/1.134e-04`
- `gh=0.699/0.698`
- `gx=0.601/0.599`
- `pd=0.501/0.503`

训练侧观察：

- `classical_full` 相比 `fixed` 的参数偏移幅度很小
- `gamma_h / gamma_x / pic_damp` 只发生了千分级到百分级微调
- 因此本轮还不能把任何明显增益归因到 classical parameter learning

#### verify 结果

| Mode | 15 dB | 20 dB | 25 dB | 参数摘要 |
| --- | --- | --- | --- | --- |
| `JointOMPMP` | `1.8291e-02` | `1.0215e-02` | `5.4980e-03` | classical baseline |
| `TradParam fixed` | `1.6377e-02` | `8.8965e-03` | `5.0684e-03` | `lambda=5.922e-05/3.974e-05/3.111e-05`, `gh=0.700`, `gx=0.600`, `pd=0.500` |
| `TradParam classical_full` | `1.6709e-02` | `8.8086e-03` | `5.3516e-03` | `lambda=5.989e-05/4.037e-05/3.170e-05`, `gh≈0.698/0.697/0.697`, `gx≈0.599`, `pd≈0.503/0.504/0.504` |

证据文件：

- `outputs_traditional_param/logs/verify_traditional_fixed.log`
- `outputs_traditional_param/logs/verify_traditional_classical_full.log`

直接结论：

- `TradParam fixed` 相对 `JointOMPMP` 在 `15/20/25 dB` 全部更优
- `TradParam classical_full` 并没有稳定超过 `TradParam fixed`
  - `15 dB`：略差
  - `20 dB`：略好
  - `25 dB`：略差

#### 三方 compare 结果

来自：

- `outputs_traditional_param/logs/compare_fixed.log`
- `outputs_traditional_param/logs/compare_full.log`

`compare_fixed.log`

- `15 dB`
  - `JointOMPMP = 1.8291e-02`
  - `TradParam fixed = 1.6377e-02`
  - `Stage6 fixed = 2.0039e-02`
- `20 dB`
  - `JointOMPMP = 1.0215e-02`
  - `TradParam fixed = 8.8965e-03`
  - `Stage6 fixed = 4.9707e-03`
- `25 dB`
  - `JointOMPMP = 5.4980e-03`
  - `TradParam fixed = 5.0684e-03`
  - `Stage6 fixed = 4.5117e-03`

结论：

- strict traditional scaffold 在 `15 dB` 更稳
- Stage 6 scaffold 在 `20/25 dB` 更强

`compare_full.log`

- `15 dB`
  - `JointOMPMP = 1.8291e-02`
  - `TradParam classical_full = 1.6709e-02`
  - `Stage6 lambda_alpha_beta = 1.9990e-02`
- `20 dB`
  - `JointOMPMP = 1.0215e-02`
  - `TradParam classical_full = 8.8086e-03`
  - `Stage6 lambda_alpha_beta = 4.9707e-03`
- `25 dB`
  - `JointOMPMP = 5.4980e-03`
  - `TradParam classical_full = 5.3516e-03`
  - `Stage6 lambda_alpha_beta = 4.5215e-03`

结论：

- Stage 6 full 在中高 SNR 仍明显优于 strict traditional full
- strict traditional full 仍保持低 SNR 相对更稳的特征

#### 结果文件覆盖风险

需要特别记录：

- `compare_fixed.log` 和 `compare_full.log` 都会把结果写到同一个文件：
  - `outputs_traditional_param/joint_family_compare_results.pkl`
- 因此该 `.pkl` 只能代表**最后一次 compare**，不能单独当作完整证据源
- 当前阶段七正式结论应以：
  - `verify_traditional_fixed.log`
  - `verify_traditional_classical_full.log`
  - `compare_fixed.log`
  - `compare_full.log`
  为准

#### 当前已证实

- 严格传统骨架的 modernized 实现已经被证实有效
- 即使 `fixed` 不学习参数，`TradParam fixed` 也能系统性优于旧 `JointOMPMP`
- 阶段七低 SNR 侧最稳的 scaffold 是 strict traditional
- 阶段七中高 SNR 侧最强的 scaffold 仍是 Stage 6

#### 当前未证实

- 尚未证实 learnable classical params 在 strict traditional scaffold 内能稳定带来额外收益
- 尚未证实 `classical_full` 会在更长训练后显著拉开与 `fixed` 的差距

#### 阶段性结论

阶段七当前最稳的结论是：

- “严格传统骨架 modernized 实现”已经被单独证实有效
- 但 “learnable classical params” 目前还**没有**被单独证实为主要收益来源
- 因此阶段七把问题进一步拆清楚了：旧 `JointOMPMP` 与当前更强实现之间的差距，首先来自 scaffold / 数值实现方式，而不是 learnable classical scalar 已经明显发挥作用

### 当前结论

- 阶段七当前已经不再停留在“只打通链路”的阶段，而是完成了正式结果冻结
- 当前最稳的阶段性结论是：
  - `TradParam fixed` 已在 `15/20/25 dB` 全部优于旧 `JointOMPMP`
  - `TradParam classical_full` 目前没有稳定超过 `TradParam fixed`
  - strict traditional scaffold 在低 SNR 更稳
  - Stage 6 scaffold 在中高 SNR 更强
- 因此，阶段七已经把“传统骨架 modernized 实现收益”和“classical scalar 学习收益”初步拆开：
  - 前者已证实
  - 后者暂未证实
