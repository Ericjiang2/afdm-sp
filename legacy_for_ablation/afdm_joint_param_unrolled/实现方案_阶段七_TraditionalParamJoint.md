# 实现方案：阶段七 Strict Traditional Param-Joint

## 1. 阶段目标

在 `afdm_joint_param_unrolled` 内新增一条**严格贴近旧 `JointOMPMP` 数值流程**的可学习分支，用来把三类收益拆开：

- 旧传统 `JointOMPMP`
- 严格传统骨架 + learnable 经典标量参数
- 当前 Stage 6 scaffold + learnable 参数

阶段七的核心问题不是“能不能再做一个更强模型”，而是：

> Stage 6 的提升，到底来自参数学习，还是来自 scaffold 本身已经比旧 `JointOMPMP` 更强。


## 2. v1 方法边界

### 2.1 严格保留的传统骨架

新分支主线尽量贴近旧 `joint_omp_mp_iterative()`：

1. `Iter-1`：pilot-only OMP 初始化 support
2. `±k_leak` cluster expansion
3. 后续 outer iter 固定 support
4. Data-aided LS with prior：
   - `(A^H A + λI)^-1 (A^H y + λ g_prev)`
5. `H_hat` damping
6. channel sparsification
7. classical `PIC` detector
8. symbol damping
9. adaptive noise update

### 2.2 为训练做的最小近似

为了可训练，v1 允许以下**最小必要近似**：

- 训练态 hard feedback 使用 straight-through nearest-QPSK
- outer loop / PIC inner loop 固定步数展开
- 训练主路径默认不做 early-stop

验证时仍使用固定 outer/inner iter 协议，与 Stage 6 保持公平可比。


## 3. 可学习参数

### 3.1 只学传统原生标量

v1 不新增 `beta` 等 Stage 6 风格门控，只学习旧传统 joint 已经有的标量：

- `lambda_ls_factor`
- `gamma_h`
- `gamma_x`
- `pic_damp`

### 3.2 参数集消融

固定四种模式：

- `fixed`
- `lambda_only`
- `damping_only`
- `classical_full`

语义固定为：

- 结构完全不变
- 只控制哪些经典标量允许偏离 anchor

默认 anchor：

- `lambda_ls_factor = 1e-3`
- `gamma_h = 0.7`
- `gamma_x = 0.6`
- `pic_damp = 0.5`

### 3.3 Strategy Net 输入

共享一个小 strategy net，输入沿用阶段六的低维工况特征：

- `log(sigma_eff)`
- `log(residual_energy_prev)`
- `support_ratio`
- detector uncertainty proxy
- `iter_frac`


## 4. 代码结构

新增平行文件：

- `afdm_traditional_param.py`
  - `TraditionalParamJointReceiver`
  - `TraditionalStrategyNet`
  - `build_traditional_param_model`
- `train_traditional_param.py`
- `verify_traditional_param.py`
- `compare_joint_families.py`

输出目录：

- `outputs_traditional_param/`

命名约束：

- checkpoint
  - `traditional_param_fixed.pt`
  - `traditional_param_lambda_only.pt`
  - `traditional_param_damping_only.pt`
  - `traditional_param_classical_full.pt`
- verify
  - `traditional_param_fixed_verify_results.pkl`
  - `traditional_param_lambda_only_verify_results.pkl`
  - `traditional_param_damping_only_verify_results.pkl`
  - `traditional_param_classical_full_verify_results.pkl`


## 5. 训练与验证协议

### 5.1 训练

- 数据源优先复用阶段六：
  - `teacher_cache / raw_labels / online`
- 主损失：
  - final bits BCE
- 辅助损失：
  - final symbol MSE
- v1 smoke 默认：
  - `frames-per-snr = 20`
  - `epochs = 1`
  - `snr = 5/10/15/20/25`

### 5.2 验证

默认对比：

- `JointOMPMP`
- `TradParamJoint`
- `OAMP`
- `LMMSE`

统一三方对比脚本 `compare_joint_families.py` 额外输出：

- `Stage6ParamJoint`

v1 验证 smoke 默认：

- `frames = 100`
- `snr = 15/20/25`


## 6. 阶段七验收

### 静态与行为

- `py_compile` 通过
- `fixed` 下四个传统标量保持 anchor 常数
- support 在 `Iter-1` 后固定
- 传统骨架本身不引入额外 learnable detector 权重

### 核心结论

阶段七必须能回答：

1. `TradParam fixed` 是否接近旧 `JointOMPMP`
2. `TradParam classical_full` 是否优于 `TradParam fixed`
3. `Stage6 full` 的优势更多来自 scaffold 还是参数学习


## 7. 当前状态

- 阶段七代码骨架已新增
- Stage 6 原入口保持不变
- 下一步优先做：
  - `py_compile`
  - 小规模训练 smoke
  - 小规模验证 smoke
  - 三方对比首轮结果记录
