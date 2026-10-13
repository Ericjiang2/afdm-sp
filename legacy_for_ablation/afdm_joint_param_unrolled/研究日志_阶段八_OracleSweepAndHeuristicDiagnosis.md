# 研究日志：阶段八 Oracle Sweep + Heuristic Breakpoint Diagnosis

## 2026-03-20

### 本轮目标

在不继续新增 learnable module 的前提下，先把“当前传统 heuristic 哪一处真有 oracle gap”这件事做成基础设施和可落盘结果。

本轮不是冲 BER，而是回答：

1. 现有 `fixed` anchor 是否已接近 oracle。
2. 当前最值得学的是 support-side / refit-side / detector-side / outer-loop side 中哪一类。
3. 阶段六/七里“学参数没明显增益”究竟更像 gap 小，还是当前参数化没抓住条件依赖。

### 代码实现

已新增：

- `afdm_joint_param.py`:
  - `ParamLearnedJointReceiver.diagnose(...)`
  - 支持 `k_leak / lambda_ls / alpha / beta / sigma_update_blend / detector_sigma_inflation / seed_mult / expand_mult` 的 inference-time override
- `afdm_traditional_param.py`:
  - `TraditionalParamJointReceiver.diagnose(...)`
  - 支持 `lambda_factor / gamma_h / gamma_x / pic_damp / sigma_update_blend / detector_sigma_inflation / k_leak / tau_h_factor / tau_h_sigma_factor / seed_mult / expand_mult`
- `diagnose_joint_heuristics.py`

设计约束：

- 不修改现有 `train_* / verify_* / compare_*` 语义
- 不保存新 checkpoint
- 不在训练图里使用诊断 override
- `seed vs expanded-only` 分组直接复用现有 `support_stats.seed_mask / support_mask`

### 静态检查

已通过：

```bash
python3 -m py_compile afdm_joint_param_unrolled/afdm_joint_param.py \
  afdm_joint_param_unrolled/afdm_traditional_param.py \
  afdm_joint_param_unrolled/diagnose_joint_heuristics.py
```

### 兼容性检查

已确认：

- `ParamLearnedJointReceiver.diagnose(..., {})` 与当前 `forward()` 同量级、同趋势；在本地当前 artifact 上两者输出一致
- 现有入口不需要新增参数即可继续运行：
  - `verify_joint_param.py`
  - `verify_traditional_param.py`

备注：

- 当前本地 `Stage6 fixed` artifact 在 `verify_joint_param.py` 下给出的 BER 与阶段六冻结文档中的云端结果不一致
- 但 `forward()` 与 `diagnose()` 一致，说明阶段八新增诊断入口本身没有篡改 Stage6 数值流程
- 因此阶段八正式结论必须依据“当前 artifact 内部的 anchor vs oracle gap”，而不能直接引用阶段六云端 BER 作为本地 oracle sweep 的 anchor

### smoke 配置

已完成最小 smoke：

```bash
conda run -n CE python afdm_joint_param_unrolled/diagnose_joint_heuristics.py \
  --frames 10 \
  --snr 15 25 \
  --candidate-families lambda_global k_leak sigma_inflation \
  --out-dir afdm_joint_param_unrolled/outputs_joint_heuristic_diagnosis_smoke
```

### smoke 产物

- `outputs_joint_heuristic_diagnosis_smoke/oracle_sweep_stage6.csv`
- `outputs_joint_heuristic_diagnosis_smoke/oracle_sweep_traditional.csv`
- `outputs_joint_heuristic_diagnosis_smoke/residual_utilization_stage6.csv`
- `outputs_joint_heuristic_diagnosis_smoke/residual_utilization_traditional.csv`
- `outputs_joint_heuristic_diagnosis_smoke/candidate_ranking.json`
- `outputs_joint_heuristic_diagnosis_smoke/diagnostic_summary.md`

### smoke 观察

#### 1. strict traditional 侧

当前 smoke 下，strict traditional anchor 与 oracle sweep 的关系是正常的：

- `sigma_inflation` 在 smoke 上能给出明显改善
- `k_leak` 有一定改善
- `lambda_global` 几乎没有 oracle gap

但按阶段八的 worth-learning 判据：

- `sigma_inflation` 虽然平均改善大，但最优值没有跨条件变化，所以暂不归类为“值得学习”
- `k_leak` 有一定工况差异，但目标区间改善幅度还不够

这说明阶段八脚本已经能把“改善存在”与“值得学习”这两个判断分开。

#### 2. Stage6 侧

当前本地 artifact 上，`Stage6 fixed` 的 anchor BER 明显偏高：

- `15 dB`: `4.6904e-01`
- `25 dB`: `4.4199e-01`

这与阶段六冻结文档中的云端 verify 结果不一致。

当前判断：

- 这是 artifact / 环境侧的一致性问题，不是阶段八诊断入口本身的问题
- 因为在同一批数据上，`forward()` 与 `diagnose()` 的输出一致
- 所以阶段八脚本仍可用于“当前 artifact 内部”的 oracle gap 排序

#### 3. residual utilization

当前 smoke 下，已训 `full` 模型的 residual utilization 统计已可落盘。

从 `ALL/ALL/ALL` 聚合行看：

- Stage6 full：
  - `E|delta_lambda_ls|` 量级约 `1e-6`
  - `E|delta_alpha|` 量级约 `1e-3`
  - `E|delta_beta|` 量级约 `1e-5`
- Traditional full：
  - `E|delta_lambda_factor|` 量级约 `1e-5`
  - `E|delta_gamma_h|` 量级约 `1e-3`
  - `E|delta_gamma_x|` 量级约 `1e-4 ~ 1e-3`
  - `E|delta_pic_damp|` 量级约 `1e-3`

这和前面阶段六/七的判断是相容的：

- 现有 residual 分支在当前训练预算下确实没有大幅偏离 anchor
- 阶段八应先证明 oracle gap，再决定是否继续学习某个局部规则

### 当前阶段性结论

已证实：

1. 阶段八所需的双线 oracle sweep 基础设施已跑通。
2. 两条骨架都支持 inference-time heuristic override。
3. 统一脚本已经能输出：
   - oracle gap 表
   - residual utilization 表
   - candidate ranking
   - 诊断摘要
4. 当前 smoke 证明：
   - `lambda_global` 至少在首轮 smoke 候选里不像是高价值学习目标
   - 候选是否值得学习，不能只看单点 BER 改善，还必须看跨条件最优值是否变化

未证实：

1. 在正式 `15/20/25 dB × 200 frames` 配置下，哪一类候选最终胜出。
2. 当前最值得学的是 support-side / refit-side / detector-side / outer-loop side 中哪一类。
3. `Stage6 fixed` 当前本地 artifact 的高 BER 是 artifact 漂移、环境差异，还是需要另行重导入 checkpoint。

### 下一步

先不改 learnable module。

先做正式诊断：

```bash
conda run -n CE python afdm_joint_param_unrolled/diagnose_joint_heuristics.py \
  --frames 200 \
  --snr 15 20 25 \
  --out-dir afdm_joint_param_unrolled/outputs_joint_heuristic_diagnosis
```

正式诊断完成后，只允许出现一个“下一模块候选”：

- support-side
- refit-side
- detector-side
- outer-loop side

若所有候选 oracle gap 都小，则阶段八结论应明确写成：

- 当前不应继续加 learnable scalar/module
- 应转向结构性建模

## 2026-03-20（阶段八正式诊断结果冻结）

### 说明

这一小节用于在重跑实验前，冻结当前 `outputs_joint_heuristic_diagnosis` 里的正式结果摘要。

对应产物目录：

- `outputs_joint_heuristic_diagnosis`

对应证据文件：

- `outputs_joint_heuristic_diagnosis/diagnostic_summary.md`
- `outputs_joint_heuristic_diagnosis/candidate_ranking.json`
- `outputs_joint_heuristic_diagnosis/oracle_sweep_stage6.csv`
- `outputs_joint_heuristic_diagnosis/oracle_sweep_traditional.csv`

### 配置

- `frames_per_snr = 200`
- `snr = 15 / 20 / 25 dB`
- `seed = 42`
- 候选族：
  - `alpha`
  - `beta`
  - `gamma_h`
  - `gamma_x`
  - `k_leak`
  - `lambda_global`
  - `lambda_group`
  - `pic_damp`
  - `sigma_inflation`
  - `tau_h_factor`
  - `tau_h_sigma_factor`

### 固定基线

#### Stage6 fixed

- `15 dB = 1.9336e-02`
- `20 dB = 5.7617e-03`
- `25 dB = 2.5195e-03`
- `support_mean ≈ 19.8~19.9`
- `seed_mean = 5`

#### Traditional fixed

- `15 dB = 1.7827e-02`
- `20 dB = 6.8604e-03`
- `25 dB = 7.5049e-03`
- `support_mean ≈ 16.6~17.0`
- `seed_mean = 5`

当前共享样本下的骨架对比结论：

- `15 dB`：strict traditional 略优
- `20/25 dB`：Stage6 fixed 明显更强

### 排名结果

#### Stage6 fixed 前三

1. `alpha`
   - 平均改善：`18.051%`
   - 目标区间最大改善：`21.441%`
   - 最优值：
     - `15 dB -> 0.95`
     - `20 dB -> 0.95`
     - `25 dB -> 0.95`
   - `worth_learning = True`
2. `sigma_inflation`
   - 平均改善：`59.733%`
   - 目标区间最大改善：`59.492%`
   - 最优值恒为 `4x`
   - 因最优值不随条件变化，`worth_learning = False`
3. `lambda_global`
   - 改善：`0%`
   - `worth_learning = False`

同时可明确排除：

- `beta` 为负收益
- `k_leak` 近 `0` 改善
- `lambda_group` 近 `0` 改善

#### Traditional fixed 前三

1. `sigma_inflation`
   - 平均改善：`16.482%`
   - 目标区间最大改善：`16.655%`
   - 最优值恒为 `0.25x`
   - `worth_learning = True`
2. `gamma_h`
   - 平均改善：`14.451%`
   - 目标区间最大改善：`17.082%`
   - `worth_learning = True`
3. `gamma_x`
   - 平均改善：`0.696%`
   - `worth_learning = False`

同时可明确排除：

- `lambda_global`
- `lambda_group`
- `pic_damp`
- `k_leak`
- `tau_h_factor`

### 正式诊断结论

这一轮正式诊断给出的最稳结论是：

1. 当前真正还有 leverage 的位置已经缩到：
   - outer-loop trust / damping
   - detector-side uncertainty calibration
2. support-side 与 refit-side 的全局标量当前基本不是主痛点：
   - `lambda_global`
   - `lambda_group`
   - `k_leak`
   都没有形成实质 oracle gap
3. 当前 top candidate 是：
   - `Stage6 fixed / alpha`
4. 当前最值得继续追的下一模块候选是：
   - `outer-loop local trust gate / damping correction`

更细的研究解释是：

- `alpha` 先证明了“当前 fixed anchor 设得不对”
- `sigma_inflation` 先证明了“detector 侧存在固定 calibration gap”
- 但是否需要把 `alpha` 真正交给 DL 学，还要在修正 fixed heuristic 之后再判断

### 结果冻结备注

这一小节的目的就是防止后续重跑把当前目录覆盖后丢失证据。

后续如果重新跑 `outputs_joint_heuristic_diagnosis`，以上结论应继续以本小节为准，除非新结果明确推翻它。

## 2026-03-20（阶段八后续：Heuristic Fix First）

### 本轮目标

在不新增 learned gate 的前提下，先把阶段八正式诊断里最有价值的两个位置做成手工修正验证：

- `Stage6 / alpha`
- `detector sigma_inflation`

目标不是直接证明 local gate 有效，而是先回答：

1. 把 `alpha` anchor 从 `0.70` 改到 oracle 最优附近后，fixed heuristic 是否已经足够。
2. 在 `sigma_inflation` 调准后，`alpha` 的 oracle gap 是否还存在。

### 代码实现

已新增脚本：

- `evaluate_stage8_stage6_heuristics.py`

脚本职责：

1. 评估 4 个固定 profile：
   - `baseline`
   - `alpha95`
   - `sigma4`
   - `alpha95_sigma4`
2. 评估 `alpha x sigma_inflation` 二维网格。
3. 导出 3 个关键 profile 的 outer-loop 轨迹统计。

不修改：

- `train_joint_param.py`
- `verify_joint_param.py`
- `compare_joint_families.py`
- `diagnose_joint_heuristics.py`

### 静态检查

已通过：

```bash
python3 -m py_compile afdm_joint_param_unrolled/evaluate_stage8_stage6_heuristics.py
```

### smoke 配置

已完成最小 smoke：

```bash
conda run -n CE python afdm_joint_param_unrolled/evaluate_stage8_stage6_heuristics.py \
  --frames 20 \
  --snr 15 25 \
  --alpha-grid 0.70 0.90 0.95 \
  --sigma-inflation-grid 1.0 4.0 6.0 \
  --out-dir afdm_joint_param_unrolled/outputs_stage8_stage6_heuristics_smoke
```

### smoke 产物

- `outputs_stage8_stage6_heuristics_smoke/stage6_heuristic_profiles.csv`
- `outputs_stage8_stage6_heuristics_smoke/stage6_heuristic_profiles_summary.md`
- `outputs_stage8_stage6_heuristics_smoke/stage6_alpha_sigma_surface.csv`
- `outputs_stage8_stage6_heuristics_smoke/stage6_alpha_sigma_best_by_snr.json`
- `outputs_stage8_stage6_heuristics_smoke/stage6_alpha_sigma_summary.md`
- `outputs_stage8_stage6_heuristics_smoke/stage6_outerloop_traces.csv`
- `outputs_stage8_stage6_heuristics_smoke/stage6_outerloop_traces_summary.md`

### smoke 观察

#### 1. 固定 profile

当前本地 artifact 下，4 个 profile 的相对关系是：

- `sigma4` 明显优于 `baseline`
- `alpha95` 单独几乎没有帮助
- `alpha95_sigma4` 相对 `baseline` 更好，但未明显优于 `sigma4`

具体数值：

- `15 dB`
  - `baseline = 4.5342e-01`
  - `alpha95 = 4.5371e-01`
  - `sigma4 = 4.4585e-01`
  - `alpha95_sigma4 = 4.4907e-01`
- `25 dB`
  - `baseline = 4.7461e-01`
  - `alpha95 = 4.7529e-01`
  - `sigma4 = 4.6563e-01`
  - `alpha95_sigma4 = 4.6421e-01`

这说明在当前本地 artifact 上，`sigma_inflation` 的 fixed calibration 作用比 `alpha=0.95` 的单独修正更稳定。

#### 2. 二维 alpha × sigma surface

当前 smoke 下的二维最优点：

- `15 dB`: `alpha=0.70`, `sigma=4.0`
- `25 dB`: `alpha=0.90`, `sigma=4.0`

对应诊断摘要：

- `alpha_span = 0.20`
- `sigma_unique_count = 1`
- `alpha95_sigma4_gap_to_best = 0.446%`

按当前阶段八后续判据，这个 smoke 更接近：

- `sigma_inflation` 像 **fixed calibration gap**
- `alpha` 还不能直接定性为“固定值修正就够了”

因为：

- 最优 `sigma` 在 smoke 下不变，始终是 `4.0`
- 最优 `alpha` 已出现跨 SNR 变化
- 但 `alpha95_sigma4` 相对二维最优点的平均 gap 很小，说明“固定 alpha 接近最优”的可能性仍然存在

#### 3. outer-loop traces

当前 smoke 轨迹显示：

- `sigma4` 或 `alpha95_sigma4` 会显著抬高 detector 侧 `v_x`
- 同时伴随更快的 residual energy 下降
- `alpha95_sigma4` 下后几轮 `channel_update_norm` 下降更快，说明 stronger trust / calibration 组合确实在改外环动态

但由于当前本地 artifact 的绝对 BER 仍与此前云端冻结结果不一致，这里只能把这些轨迹当作：

- **当前 artifact 内部的相对动态证据**

而不能直接拿来和阶段六冻结 BER 做绝对数值对照。

### 当前阶段性结论

已证实：

1. `Heuristic Fix First` 所需的 Stage6 专用评估脚本已打通。
2. `sigma_inflation` 作为 fixed calibration gap 的判断，在 smoke 上进一步得到支持。
3. 仅把 `alpha` 固定改到 `0.95`，在当前本地 artifact 上还不足以单独吃掉 gap。
4. `alpha95_sigma4` 已接近二维最优点，说明“先修 fixed heuristic”仍然是合理优先级。

未证实：

1. 在正式 `15/20/25 dB × 500 frames` 配置下，最优 `alpha` 是否仍随 SNR 变化。
2. `alpha95_sigma4` 是否在正式配置下仍能稳定逼近二维最优点。
3. 正式结果最终更支持：
   - 先改 fixed heuristic，不上 gate
   - 还是进入 local alpha gate

### 下一步

先跑正式版：

```bash
conda run -n CE python afdm_joint_param_unrolled/evaluate_stage8_stage6_heuristics.py \
  --frames 500 \
  --snr 15 20 25 \
  --out-dir afdm_joint_param_unrolled/outputs_stage8_stage6_heuristics
```

正式结果只允许得出二选一结论：

- `fixed`：先把 `alpha` 与 `sigma_inflation` 写回 Stage6 fixed heuristic
- `gate`：进入 state-dependent local alpha gate

## 2026-03-20（阶段八后续正式结果：Heuristic Fix First）

### 对应产物

- `outputs_stage8_stage6_heuristics/stage6_heuristic_profiles.csv`
- `outputs_stage8_stage6_heuristics/stage6_heuristic_profiles_summary.md`
- `outputs_stage8_stage6_heuristics/stage6_alpha_sigma_surface.csv`
- `outputs_stage8_stage6_heuristics/stage6_alpha_sigma_best_by_snr.json`
- `outputs_stage8_stage6_heuristics/stage6_alpha_sigma_summary.md`
- `outputs_stage8_stage6_heuristics/stage6_outerloop_traces.csv`
- `outputs_stage8_stage6_heuristics/stage6_outerloop_traces_summary.md`

### 配置

- `frames_per_snr = 500`
- `snr = 15 / 20 / 25 dB`
- `seed = 42`
- 4 个固定 profile：
  - `baseline = (alpha=0.70, sigma=1.0)`
  - `alpha95 = (alpha=0.95, sigma=1.0)`
  - `sigma4 = (alpha=0.70, sigma=4.0)`
  - `alpha95_sigma4 = (alpha=0.95, sigma=4.0)`
- 二维网格：
  - `alpha ∈ {0.70, 0.85, 0.90, 0.95, 0.98}`
  - `sigma_inflation ∈ {1.0, 2.0, 3.0, 4.0, 6.0}`

### 一、固定 profile 结果

#### baseline

- `15 dB = 1.9533e-02`
- `20 dB = 5.9453e-03`
- `25 dB = 3.7520e-03`

#### alpha95

- `15 dB = 1.7111e-02`
- `20 dB = 4.8750e-03`
- `25 dB = 2.9883e-03`

#### sigma4

- `15 dB = 9.4922e-03`
- `20 dB = 2.2266e-03`
- `25 dB = 1.5527e-03`

#### alpha95_sigma4

- `15 dB = 7.4512e-03`
- `20 dB = 1.6465e-03`
- `25 dB = 1.2598e-03`

### 二、固定 profile 的研究解释

这一轮最重要的事实不是“组合最好”，而是：

1. `sigma4` 的收益远大于 `alpha95`
2. `alpha95` 单独也有稳定收益，但量级明显小于 `sigma4`
3. `alpha95_sigma4` 继续显著优于两者单独版本

当前最稳的解释是：

- `detector-side uncertainty calibration` 是第一主痛点
- `outer-loop damping / trust` 是第二主痛点
- 二者是互补关系，不是简单替代关系

也就是说，当前闭环更像是在同时承受：

- detector 置信度过于乐观
- outer-loop 吸收信息过于激进

这比“再学几个全局标量”更接近真实瓶颈。

### 三、二维 alpha × sigma surface

正式二维 sweep 的最优点为：

- `15 dB -> alpha=0.98, sigma=6.0, ber=4.7051e-03`
- `20 dB -> alpha=0.98, sigma=6.0, ber=8.7891e-04`
- `25 dB -> alpha=0.98, sigma=6.0, ber=8.0664e-04`

相对 baseline 的改善分别为：

- `15 dB: 75.912%`
- `20 dB: 85.217%`
- `25 dB: 78.501%`

二维诊断还给出：

- `alpha_span = 0.000`
- `sigma_unique_count = 1`
- `alpha95_sigma4_gap_to_best = 67.291%`

### 四、二维 surface 的研究解释

这里必须明确区分：

- **脚本自动判据给出的 verdict**
- **研究上更稳的解释**

脚本目前会因为 `alpha95_sigma4` 相对二维最优点仍有明显 gap，而给出：

- `move to state-dependent local alpha gate`

但研究解释上，更稳的结论应当是：

1. 当前最佳组合 `alpha=0.98, sigma=6.0` 在三个 SNR 上完全一致。
2. 更关键的是，最优点已经撞到了当前网格的搜索边界：
   - `alpha` 取到当前上界 `0.98`
   - `sigma` 取到当前上界 `6.0`
3. 在最优点撞边界时，最稳的解释不是“必须立刻上 learned gate”，而是：
   - **fixed heuristic 仍明显欠调**
   - **constant-policy 的最优区间尚未被完整探索**

因此，这轮结果更支持：

- 先扩大 fixed 2D sweep
- 再判断是否真的存在 state-dependent gap

而不是直接把结论跳到 local gate。

### 五、outer-loop trace 结果

trace 里最有价值的现象是：

1. `alpha95` 相比 `baseline`，每轮 BER 都更低。
2. `alpha95_sigma4` 比 `alpha95` 进一步明显更低。
3. `alpha95_sigma4` 下：
   - `channel_update_norm` 后期更小
   - detector 侧 `v_x` 更高
   - residual energy 更快下降

当前最稳的解释是：

- 系统正在主动降低 detector 的过度自信
- 从而减少错误 soft information 对信道更新的冲击
- 最终把外环拉回更保守、更收缩的工作区

这说明问题不是“信息不够”，而是：

- **信息太自信**
- **更新太激进**

### 六、当前阶段性结论

和阶段八上一轮相比，这一轮把结论又推进了一步：

1. 当前性能缺口进一步集中在：
   - detector-side uncertainty calibration
   - outer-loop trust / damping
2. `sigma_inflation` 的 fixed calibration 作用非常强，说明 detector 端存在系统性失配。
3. `alpha` 也有稳定协同收益，但当前更像第二主痛点，而不是第一主痛点。
4. support-side 与 refit-side 全局标量仍不是当前主要突破口。
5. 当前最稳的研究解释不是“立刻上 local alpha gate”，而是：
   - **你之前连 fixed alpha / fixed sigma 都还没调到正确工作区**
   - **在这种情况下，任何 learned gate 结论都还为时过早**

### 七、下一步建议（冻结）

下一步优先级固定为：

1. 先扩大 fixed 2D sweep，而不是立刻实现 gate
2. 建议至少扩到：
   - `alpha ∈ {0.98, 0.99, 0.995, 0.999}`
   - `sigma_inflation ∈ {6, 8, 10, 12}`
3. 然后再看：
   - 最优点是否仍继续撞边界
   - 最优常数组合是否已经进入平台区
4. 只有当 best-constant 已被坐实后，才值得继续做：
   - 按 outer-iteration 分层的 oracle sweep
   - 然后决定是否进入 state-dependent local alpha gate

### 八、冻结备注

这一节用于在后续继续覆盖 `outputs_stage8_stage6_heuristics` 目录前，保留当前这轮正式结果与研究解释。

后续若新结果出现，必须明确区分：

- “脚本自动判据”
- “研究解释上的最终结论”

当前冻结版本里，两者并不完全相同：

- 自动判据偏向 `gate`
- 研究解释更稳地偏向 **先继续 fixed retune**

## 2026-03-20（阶段八下一轮评估器已实现：Best-Constant First）

### 目标

在不引入新 learnable module 的前提下，把当前 Stage6 的后续诊断顺序固定为：

1. 先把 `alpha / sigma_inflation` 的 **best-constant** 区域探明
2. 再看 best-constant 在多 seed 下是否稳定
3. 只有在 best-constant 被坐实后，才比较按 outer-iter 分层的 oracle 是否仍有明显 gap

### 代码变更

已扩展：

- `evaluate_stage8_stage6_heuristics.py`

保留原有 3 块产物：

- fixed profiles
- coarse `alpha × sigma` surface
- outer-loop traces

新增 2 块产物：

- `expanded_best_constant`
- `iter_layered_oracle`

新增 CLI：

- `--seeds`
- `--expanded-alpha-grid`
- `--expanded-sigma-inflation-grid`
- `--run-iter-layered`

默认值固定为：

- `seeds = 42, 123`
- `expanded alpha = {0.95, 0.98, 0.99, 0.995, 0.999}`
- `expanded sigma = {4, 6, 8, 10, 12}`
- `frames = 1000 per SNR`
- `snr = 15 / 20 / 25 dB`

### 诊断规则（冻结）

这轮结束后只允许落入 3 类结论之一：

- `A. 仍撞边界 -> 继续 fixed retune`
- `B. best-constant 坐实 -> 先写回 fixed baseline，不进 gate`
- `C. iter-layered oracle 明显优于 best-constant -> 进入 local alpha/sigma gate 设计`

进入 `C` 的条件固定为：

- iter-layered oracle 相对 best-constant 在 `15/20/25 dB` 平均 BER 再改善 `>10%`
- 且两个 seed 下趋势一致

若不满足该条件，则默认：

- 仍以 fixed heuristic 为主线
- 不进入 learned gate

### 当前研究口径

这一轮实现后的默认研究顺序已明确改成：

- **先把 fixed heuristic 调到头**
- **确认 best-constant 是否进入平台**
- **再判断是否存在真正的时变 / 分层 gap**

也就是说，当前不再接受“直接从阶段八 formal 结果跳到 learned local gate”的解释。

### 静态检查与 smoke

已通过：

```bash
python3 -m py_compile afdm_joint_param_unrolled/afdm_joint_param.py \
  afdm_joint_param_unrolled/evaluate_stage8_stage6_heuristics.py
```

已完成缩小版 smoke，产物目录：

- `outputs_stage8_stage6_heuristics_smoke_v3`

smoke 已确认新产物链路能够落盘：

- `stage6_alpha_sigma_surface_expanded.csv`
- `stage6_alpha_sigma_best_by_snr_expanded.json`
- `stage6_alpha_sigma_summary_expanded.md`
- `stage6_alpha_sigma_seed_compare.json`
- `stage6_alpha_sigma_iterlayer_surface.csv`
- `stage6_alpha_sigma_iterlayer_best.json`
- `stage6_alpha_sigma_iterlayer_summary.md`
- `stage6_outerloop_traces.csv`
- `stage6_outerloop_traces_summary.md`

## 2026-03-20（阶段八继续正式结果：Best-Constant First）

### 对应产物

- `outputs_stage8_stage6_heuristics/stage6_heuristic_profiles.csv`
- `outputs_stage8_stage6_heuristics/stage6_heuristic_profiles_summary.md`
- `outputs_stage8_stage6_heuristics/stage6_alpha_sigma_surface.csv`
- `outputs_stage8_stage6_heuristics/stage6_alpha_sigma_best_by_snr.json`
- `outputs_stage8_stage6_heuristics/stage6_alpha_sigma_summary.md`
- `outputs_stage8_stage6_heuristics/stage6_alpha_sigma_surface_expanded.csv`
- `outputs_stage8_stage6_heuristics/stage6_alpha_sigma_best_by_snr_expanded.json`
- `outputs_stage8_stage6_heuristics/stage6_alpha_sigma_summary_expanded.md`
- `outputs_stage8_stage6_heuristics/stage6_alpha_sigma_seed_compare.json`
- `outputs_stage8_stage6_heuristics/stage6_alpha_sigma_iterlayer_surface.csv`
- `outputs_stage8_stage6_heuristics/stage6_alpha_sigma_iterlayer_best.json`
- `outputs_stage8_stage6_heuristics/stage6_alpha_sigma_iterlayer_summary.md`
- `outputs_stage8_stage6_heuristics/stage6_outerloop_traces.csv`
- `outputs_stage8_stage6_heuristics/stage6_outerloop_traces_summary.md`

### 配置

- `frames_per_snr = 1000`
- `snr = 15 / 20 / 25 dB`
- `seeds = {42, 123}`
- coarse grid：
  - `alpha ∈ {0.70, 0.85, 0.90, 0.95, 0.98}`
  - `sigma_inflation ∈ {1, 2, 3, 4, 6}`
- expanded grid：
  - `alpha ∈ {0.95, 0.98, 0.99, 0.995, 0.999}`
  - `sigma_inflation ∈ {4, 6, 8, 10, 12}`
- iter-layered oracle：
  - `iter1` 一组参数
  - `iter2+` 一组参数
  - 局部网格围绕 expanded best-constant 构造

### 一、coarse profile 结果

#### baseline

- `15 dB = 1.9918e-02`
- `20 dB = 5.9766e-03`
- `25 dB = 4.3359e-03`

#### alpha95

- `15 dB = 1.7354e-02`
- `20 dB = 4.8076e-03`
- `25 dB = 3.4678e-03`

#### sigma4

- `15 dB = 9.6084e-03`
- `20 dB = 2.3467e-03`
- `25 dB = 1.6709e-03`

#### alpha95_sigma4

- `15 dB = 7.6143e-03`
- `20 dB = 1.7061e-03`
- `25 dB = 1.2588e-03`

### 二、coarse profile 的研究解释

当前最稳的事实是：

1. `sigma4` 的收益远大于 `alpha95`
2. `alpha95` 单独也有稳定收益，但量级显著小于 `sigma4`
3. `alpha95_sigma4` 继续显著优于两者单独版本

这说明：

- `detector-side uncertainty calibration` 是第一主痛点
- `outer-loop damping / trust` 是协同痛点
- 二者是互补关系，不是替代关系

也就是说，当前 Stage6 闭环的主缺口首先不在 gate，而在 detector 对 free-run 场景下不确定性的系统性低估。

### 三、expanded best-constant 结果

#### seed = 42

- `15 dB -> alpha=0.999, sigma=12.0, ber=1.9062e-03`
- `20 dB -> alpha=0.980, sigma=12.0, ber=2.4902e-04`
- `25 dB -> alpha=0.990, sigma=12.0, ber=1.0938e-04`

#### seed = 123

- `15 dB -> alpha=0.999, sigma=12.0, ber=1.8643e-03`
- `20 dB -> alpha=0.999, sigma=12.0, ber=1.3672e-04`
- `25 dB -> alpha=0.995, sigma=12.0, ber=8.4961e-05`

#### 聚合结论

- `any_edge_hit = True`
- `consistent_best_region = True`
- expanded summary verdict：
  - `A. 仍撞边界 -> 继续 fixed retune`

### 四、expanded best-constant 的研究解释

这轮最关键的新结论不是“应该学 gate”，而是：

1. 最优区已经稳定落在：
   - 高 `alpha`
   - 高 `sigma_inflation`
2. 但最优点在两个 seed 下依旧全部撞在 expanded grid 边界：
   - `sigma_inflation` 始终顶到 `12`
   - `alpha` 也在 `0.98 ~ 0.999` 的上边界附近
3. 因而当前最稳的解释不是“已经找到了最优常数”，而是：
   - **best-constant 还没有扫到头**
   - **fixed heuristic retune 尚未完成**

也就是说，当前可以确认的是“高保守角区”是正确方向，但还不能确认常数最优已经进入平台。

### 五、iter-layered oracle 结果

best-constant 参考：

- seed `42`: `alpha=0.999, sigma=12.0, mean_ber=7.5488e-04`
- seed `123`: `alpha=0.999, sigma=12.0, mean_ber=6.9564e-04`

iter-layered oracle 的平均提升：

- seed `42`: `0.298%`
- seed `123`: `1.667%`
- `consistent_gate_gain = False`

逐 SNR 看，绝大多数点对 best-constant 的提升为：

- `0%`
- 或极小的个位数百分比

当前 summary verdict：

- iter-layered oracle does not justify a learned gate yet

### 六、iter-layered oracle 的研究解释

这一轮给出的最硬证据之一是：

- `best-constant ≈ simple iter-layered rule`

也就是说，至少在“按 outer-iter 分两层”的级别上，state-dependent rule 还没有展示出足够的额外价值。

因此，当前没有证据支持：

- learned local alpha/sigma gate 是主要缺口

反过来，证据更支持：

- 先把 best-constant 探明
- 再判断是否还存在显著的时变 / 状态依赖 gap

### 七、outer-loop trace 结果

trace 比较对象：

- `baseline = (alpha=0.70, sigma=1.0)`
- `hand_fix = (alpha=0.95, sigma=4.0)`
- `best_constant_expanded = (alpha=0.999, sigma=12.0)`

最关键的现象：

1. `hand_fix` 相对 `baseline` 全程更好
2. `best_constant_expanded` 又显著优于 `hand_fix`
3. `best_constant_expanded` 下：
   - `v_x` 更高
   - BER 在前两轮下降更快
   - `channel_update_norm` 并不单纯更小，很多位置反而更大

### 八、trace 的研究解释

这说明当前系统发生的不是：

- “把更新压小，所以更稳”

而更像是：

- “先把 detector 的过度自信纠正”
- “soft 信息的可信度尺度变对”
- “outer loop 因而能够承受更积极的有效更新而不自毒”

所以当前最核心的问题不是“更新太大”，而是：

- **detector 给出的置信度太假**
- **effective uncertainty 被系统性低估**

这进一步强化了：

- `sigma_inflation` 不是小修正，而是在补 detector-side 的一阶模型失配

### 九、当前阶段性结论

到这一步，阶段八最稳的研究结论可以收敛成 4 条：

1. `Stage6` 当前的首要性能缺口位于 **detector-side uncertainty calibration**，而不是 outer-loop local gate。
2. `alpha` 仍然重要，但更像协同项；它建立在 calibration 被调准之后，而不是独立主导项。
3. 当前 best-constant 仍撞在高 `alpha + sigma` 的边界区，说明 fixed heuristic retune 尚未结束。
4. iter-layered oracle 相对 best-constant 增益极小，当前没有证据支持 state-dependent gate 是主要缺口。

### 十、下一步建议（冻结）

下一步优先级固定为：

1. 继续扩大 constant 2D sweep，而不是进入 learned gate
2. 建议至少扩到：
   - `alpha ∈ {0.98, 0.99, 0.995, 0.999, 0.9995}`
   - `sigma_inflation ∈ {12, 16, 20, 24}`
3. 在新 seed / 更大帧数上继续复核“高 alpha + 高 sigma”的角区是否稳定
4. 在继续 sweep 的同时，新增 detector calibration 诊断：
   - `v_x` vs 真实误差
   - detector used sigma vs empirical residual variance
5. 只有当 best-constant 真正进入平台后，才再比较：
   - best-constant vs iter-layered oracle
   - 决定是否需要 local gate

### 十一、冻结备注

这一节用于在后续继续覆盖 `outputs_stage8_stage6_heuristics` 目录前，保留本轮正式结果与研究解释。

当前冻结结论明确偏向：

- **先继续 fixed retune**
- **暂不进入 learned local gate**

## 2026-03-21（阶段八继续正式结果：Calibration First，sweep 结果先冻结）

本节用于冻结 `outputs_stage8_stage6_heuristics` 这一轮已经完成的 sweep 结果。  
注意：本轮在 `Outer-loop traces` 阶段新增的 calibration 统计路径触发了 shape mismatch，因此：

- **fixed profiles / coarse surface / expanded best-constant / iter-layered oracle 的结果有效**
- **trace + calibration diagnosis 需要在修复 shape bug 后单独补测**

### 一、本轮已完成配置

- 目录：`outputs_stage8_stage6_heuristics`
- 主体：`Stage6 fixed`
- seeds：`42 / 123 / 314`
- 协议：
  - `15 / 20 / 25 dB`
  - `frames = 1500 per SNR`
  - chunked eval 打开
- 网格：
  - coarse：`alpha ∈ {0.70,0.85,0.90,0.95,0.98}`, `sigma ∈ {1,2,3,4,6}`
  - expanded：`alpha ∈ {0.95,0.98,0.99,0.995,0.999}`, `sigma ∈ {4,6,8,10,12}`
  - expanded v2：`alpha ∈ {0.98,0.99,0.995,0.999,0.9995}`, `sigma ∈ {12,16,20,24}`

### 二、fixed profile 结果

- `baseline`
  - `15/20/25 dB = 1.9764e-02 / 6.5085e-03 / 4.0163e-03`
- `alpha95`
  - `15/20/25 dB = 1.7130e-02 / 5.2461e-03 / 3.1973e-03`
- `sigma4`
  - `15/20/25 dB = 9.4518e-03 / 2.5970e-03 / 1.4727e-03`
- `alpha95_sigma4`
  - `15/20/25 dB = 7.4531e-03 / 1.9342e-03 / 1.0716e-03`

直接结论：

1. `sigma_inflation` 依旧是第一主导项。
2. `alpha` 单独有稳定收益，但量级明显小于 `sigma4`。
3. `alpha + sigma` 组合继续优于两者单独版本，说明 `alpha` 更像 calibration 调准之后的协同项。

### 三、coarse alpha × sigma 结果

coarse best 在三个 SNR 点上完全一致：

- `15 dB`: `alpha=0.98, sigma=6.0, ber=4.6706e-03`
- `20 dB`: `alpha=0.98, sigma=6.0, ber=1.0202e-03`
- `25 dB`: `alpha=0.98, sigma=6.0, ber=5.6315e-04`

这再次说明：

- 系统最优区持续向“高 alpha + 高 sigma”的保守角移动
- 当前问题首先不是 gate 缺失，而是 fixed heuristic 明显欠调

### 四、expanded best-constant 结果

#### expanded v1

三个 seed 的 global best 完全一致：

- `seed=42`: `alpha=0.999, sigma=12.0, mean_ber=7.2591e-04`
- `seed=123`: `alpha=0.999, sigma=12.0, mean_ber=6.7144e-04`
- `seed=314`: `alpha=0.999, sigma=12.0, mean_ber=7.5412e-04`

#### expanded v2

三个 seed 的 global best 再次完全一致，并继续往更保守角推进：

- `seed=42`: `alpha=0.9995, sigma=16.0, mean_ber=7.0269e-04`
- `seed=123`: `alpha=0.9995, sigma=16.0, mean_ber=6.5061e-04`
- `seed=314`: `alpha=0.9995, sigma=16.0, mean_ber=7.2830e-04`

当前最稳解释：

- best-constant 还没有扫到头
- 最优区已经稳定收缩到“极高 alpha + 极高 sigma”的角区
- detector-side calibration 的 fixed gap 远比之前估计得更大

### 五、iter-layered oracle 结果

围绕 expanded best-constant 的按 outer-iter 分层 oracle，三 seed 的平均提升都极小：

- `seed=42`: `0.324%`
- `seed=123`: `0.251%`
- `seed=314`: `0.351%`

这已经形成非常硬的反证：

- `best-constant ≈ simple iter-layered rule`
- 现阶段没有证据支持 state-dependent local gate 是主要缺口

### 六、当前研究结论（更新）

到这一步，阶段八当前最稳的结论可以收敛成 4 条：

1. `Stage6` 当前的首要性能缺口位于 **detector-side uncertainty calibration**，而不是 local gate。
2. `alpha` 仍然重要，但更像 **建立在 calibration 调准之后的协同项**。
3. 当前 best-constant 仍持续向高 `alpha + sigma` 的边界角移动，说明 **fixed heuristic retune 仍未结束**。
4. iter-layered oracle 相对 best-constant 增益极小，因此 **当前没有足够证据进入 learned local alpha/sigma gate**。

### 七、关于本轮 bug 与补测策略

本轮 crash 发生在新增的 calibration 路径：

- 触发点：`trace + calibration diagnosis`
- 原因：`stage["detection"]` 为 detector 的 data-block 表示，而真实符号误差统计直接拿 `x_true_full` 做减法，表示未对齐

因此补测策略明确为：

1. **不重跑 sweep**
2. 先修复 shape bug
3. 只补跑：
   - `stage6_outerloop_traces.csv / summary`
   - `stage6_detector_calibration.csv / summary`
   - `stage6_detector_sigma_residual.csv / summary`

### 八、下一步建议（冻结）

当前优先级继续固定为：

1. 先完成 `trace + calibration diagnosis` 的补测
2. 在补测完成前，不进入 learned gate
3. 后续继续扩大 constant retune 网格，优先确认 best-constant 是否真正进入平台
4. 若 calibration 失配被直接量化坐实，则下一代改进优先转向：
   - detector uncertainty model 修正
   - residual-aware / CSI-aware calibration
   而不是继续学习全局 `lambda / beta`

## 2026-03-21（阶段八继续：Calibration First v3 评估器已实现）

本节记录的是**代码与诊断基础设施已经接好**，不是正式实验结果。

### 一、本轮新增能力

在 `evaluate_stage8_stage6_heuristics.py` 上继续扩展，新增：

1. `expanded_v3` 常数网格
   - `alpha ∈ {0.999, 0.9995, 0.9999}`
   - `sigma_inflation ∈ {16, 20, 24, 32}`
2. `best_constant_expanded_v3` 作为新的 trace / calibration 对照 profile
3. 新的 detector calibration 直观产物：
   - `stage6_detector_calibration_curves.csv`
   - `stage6_detector_calibration_curves_summary.md`
4. 新的 residual proxy 产物：
   - `stage6_detector_residual_proxies.csv`
   - `stage6_detector_residual_proxies_summary.md`
5. `trace-calibration-only` 补测模式继续保留，并支持直接指定：
   - `--trace-best-alpha`
   - `--trace-best-sigma-inflation`

### 二、本轮新增的研究问题

这一轮不再只是问“best-constant 还会不会继续往高保守角走”，还要直接回答：

1. `sym_err / v_x` 是否系统性大于 `1`
2. `empirical_residual_var / detector_sigma` 是否系统性大于 `1`
3. miscalibration 是否主要集中在前两轮
4. `sigma_inflation` 更像在补：
   - channel mismatch
   - SIC residual
   - 或 generic model mismatch

### 三、实现级别结论

当前主线已明确切换为：

- **先做 detector calibration diagnosis**
- **继续做 best-constant plateau 搜索**
- **local gate 不是近期主线**

### 四、smoke 状态

本地 `CE` 环境下已完成：

- `py_compile` 通过
- `trace-calibration-only` smoke 通过
- 新增产物已能成功落盘：
  - `stage6_alpha_sigma_surface_expanded_v3.csv`
  - `stage6_detector_calibration_curves.csv`
  - `stage6_detector_residual_proxies.csv`
  - 对应 `summary.md`

因此，下一步可以直接上云端正式运行 `Calibration First v3`。

## 2026-03-22（阶段八继续正式结果：Detector Calibration Diagnosis v3 结果冻结）

### 一、说明

这一小节用于冻结当前目录：

- `outputs_stage8_stage6_heuristics`

中 `Calibration First v3` 已完成的结果、分析和下一步计划。

本次冻结的重点不是继续比较“哪个参数更重要”，而是把下面四个研究问题收束为当前证据状态：

1. detector 是否系统性低估了真实不确定性。
2. 这种低估主要出现在哪几轮、哪类量上。
3. `sigma_inflation` 更像在补 `CE bias / SIC residual / generic mismatch` 中的哪类缺口。
4. 在 `best-constant` 真到平台前，local gate 是否仍然没有必要。

### 二、本轮已完成的正式结果

对应证据文件：

- `outputs_stage8_stage6_heuristics/stage6_alpha_sigma_summary_expanded_v3.md`
- `outputs_stage8_stage6_heuristics/stage6_alpha_sigma_seed_compare_v3.json`
- `outputs_stage8_stage6_heuristics/stage6_alpha_sigma_iterlayer_summary.md`
- `outputs_stage8_stage6_heuristics/stage6_detector_calibration_curves_summary.md`
- `outputs_stage8_stage6_heuristics/stage6_detector_residual_proxies_summary.md`
- `outputs_stage8_stage6_heuristics/stage6_outerloop_traces_summary.md`

#### 1. fixed profiles 继续确认：`sigma` 是第一主导项，`alpha` 是协同项

| profile | 15 dB | 20 dB | 25 dB |
| --- | --- | --- | --- |
| `baseline = (0.70, 1.0)` | `1.9764e-02` | `6.5085e-03` | `4.0163e-03` |
| `alpha95 = (0.95, 1.0)` | `1.7130e-02` | `5.2461e-03` | `3.1973e-03` |
| `sigma4 = (0.70, 4.0)` | `9.4518e-03` | `2.5970e-03` | `1.4727e-03` |
| `alpha95_sigma4 = (0.95, 4.0)` | `7.4531e-03` | `1.9342e-03` | `1.0716e-03` |

当前最稳判断：

1. `sigma_inflation` 单独调的收益显著大于 `alpha`。
2. `alpha` 仍有稳定收益，但更像 calibration 调准之后的协同项。
3. `alpha + sigma` 组合继续优于单独 `sigma`，说明 outer-loop 不是无关，但主矛盾不在 gate。

#### 2. expanded_v3 best-constant：高 `alpha + sigma` 角区稳定，但仍未封顶

按 seed 聚合的全局最优：

- `seed=42`: `alpha=0.9999`, `sigma=16.0`, `mean_ber=6.9157e-04`
- `seed=123`: `alpha=0.9999`, `sigma=16.0`, `mean_ber=6.4893e-04`
- `seed=314`: `alpha=0.9999`, `sigma=16.0`, `mean_ber=7.1761e-04`

按 `snr` 的最优区域：

- `15 dB`: `alpha≈1.0`, `sigma=16.0`
- `20 dB`: `alpha≈0.999`, `sigma=16.0`
- `25 dB`: `alpha≈0.999`, `sigma=16.0`

同时：

- `any_edge_hit = True`
- `consistent_best_region = True`

这说明：

1. current best-constant 区域已经稳定定位到“极高 `alpha` + 极高 `sigma`”的保守角。
2. 但最优点仍然撞在 v3 搜索边界上，因此 **研究上仍不能宣称 plateau 已被严格坐实**。
3. 对 `alpha` 而言，当前已经足以说明它落在“近似全信”的极限区；继续细扫 `0.9999 -> 1.0` 的研究信息增益很低。
4. 对 `sigma` 而言，仍有必要做一轮**窄的一侧平台确认**，目的不是继续讲参数故事，而是确认 detector 漏项是否已经被常数 `16` 补到平台。

#### 3. iter-layered oracle 基本否定了 local gate

`iter-layered oracle` 相对 current best-constant 的平均增益：

- `seed=42`: `0.545%`
- `seed=123`: `0.427%`
- `seed=314`: `0.640%`

结论：

1. 当前没有证据支持 `alpha gate / sigma gate / learned local gate` 是主要缺口。
2. 在“按 outer-iter 分层”这一粒度上，`state dependence` 不构成主要收益来源。
3. 因此阶段八的主线应继续停留在 **fixed calibration / uncertainty model diagnosis**，而不是转入学习化 gate。

### 三、detector miscalibration 的直接量化结论

#### 1. `sym_err / v_x` 已把“系统性低估真实不确定性”坐实

baseline 下的 `calibration_ratio = sym_err_mean / vx_mean`：

- `15 dB`: `18.661 -> 58.614 -> 89.026 -> 145.306 -> 235.022`
- `20 dB`: `15.282 -> 77.974 -> 151.467 -> 277.797 -> 527.764`
- `25 dB`: `14.042 -> 95.335 -> 209.186 -> 432.558 -> 835.040`

这已经足够支持：

- detector posterior variance `v_x` 长期远小于真实符号误差；
- 而且这种低估不是早期瞬时现象，而是会在后续迭代中继续放大。

best-constant 下，该比值被大幅拉回，甚至后几轮转为明显保守：

- `15 dB`: `3.121 -> 0.251 -> 0.105 -> 0.113 -> 0.367`
- `20 dB`: `9.542 -> 0.190 -> 0.049 -> 0.140 -> 0.600`
- `25 dB`: `13.710 -> 0.167 -> 0.037 -> 0.181 -> 0.768`

当前最稳解释：

1. baseline detector 在 `v_x` 这条线上存在**系统性过度自信**。
2. `sigma_inflation` 不是小修小补，而是在替 detector 漏掉的有效不确定性项做粗粒度补偿。
3. current best-constant 在前几轮修正了过度乐观，但到后几轮又可能转为保守，因此后续真正值得做的是 **uncertainty model 修正**，而不是继续推 `alpha gate`。

#### 2. used sigma vs empirical residual variance：最前面几轮最失真

baseline 的 `sigma_gap_ratio = empirical_residual_var / detector_sigma_mean`：

- `15 dB`: `5.869, 0.613, 0.553, 0.489, 0.512`
- `20 dB`: `16.985, 0.490, 0.433, 0.382, 0.394`
- `25 dB`: `51.181, 0.448, 0.381, 0.331, 0.339`

best-constant 下：

- `15 dB`: `0.273, 0.031, 0.005, 0.011, 0.025`
- `20 dB`: `1.005, 0.028, 0.003, 0.011, 0.022`
- `25 dB`: `3.192, 0.026, 0.003, 0.010, 0.020`

这说明：

1. detector 使用的噪声尺度在 **iter0** 尤其偏小，高 SNR 更严重。
2. current best-constant 把这部分缺口强行补上以后，后续轮次又明显转为保守。
3. 因此当前最合理的方向，不是继续把 `sigma` 当神秘最优参数去调，而是把它视作 **漏项的 proxy**，去构造更合理的 detector uncertainty model。

#### 3. “主要补哪类缺口”目前只拿到了代理证据

本轮新增的 `residual proxies` 已支持一个较稳的中间结论：

- 大 `sigma_inflation` 并不是在补一个简单 AWGN 误差常数；
- 它更像在给 `CE bias + SIC residual + generic model mismatch` 的混合项兜底；
- 其中最重的失配很可能前置在外环早期。

但当前仍不能严肃写成：

- “主要就是 CE bias”
- 或 “主要就是 SIC residual”

因为本轮还没有完成严格的来源分解，只拿到了：

- `post_sic_residual_energy`
- `channel_update_norm`
- `sigma_ls_mean`
- `residual_energy_mean`

这些趋势代理量。

因此这一问的当前证据状态应写为：

- **已证实：存在 generic effective uncertainty gap**
- **未完全证实：该 gap 主要由哪一类误差源主导**

### 四、这轮结果对研究方向的重定位

当前最硬的研究结论不是“该再调哪个参数”，而是：

> **Stage6 当前暴露出来的，已经不是普通意义上的 heuristic 欠调，而是 detector 内部的有效不确定性模型存在系统性失配；`sigma_inflation` 一路往大推，并不是偶然，而是在替一个被长期低估的误差源兜底。**

由此带来的重定位是：

1. `alpha` 这条线在研究上基本可以收口：
   - current best-constant 已经落在 `0.999 ~ 1.0` 的极限区；
   - 再继续细扫 `alpha` 的信息增益很低。
2. `sigma` 仍值得做一轮**很窄的一侧平台确认**：
   - 目的不是继续做“参数故事”；
   - 而是给 detector calibration 主线封顶。
3. 阶段八下一步的真正主线应从“要不要 gate”切到：
   - **detector uncertainty model 修正**
   - 或更具体地说：
     - early-iteration-aware sigma rule
     - residual-aware sigma rule
     - posterior variance recalibration

### 五、对四个研究问题的当前回答状态

1. detector 是否系统性低估了真实不确定性  
   - **是，已明确验证。**
2. 这种低估主要出现在哪几轮、哪类量上  
   - **基本验证。**
   - `v_x` 线：全程偏乐观，且后几轮更严重；
   - `used sigma` 线：前两轮最严重，尤其 `iter0`。
3. `sigma_inflation` 到底在补 `CE bias / SIC residual / generic mismatch` 的哪类缺口  
   - **只拿到代理证据，尚未严格分解。**
4. 在 `best-constant` 真到平台前，local gate 是否仍然没有必要  
   - **是，当前证据已经很强。**

### 六、下一步计划（阶段八后续）

当前最合理的下一步，不是继续做大规模 `alpha × sigma` 网格，也不是转向 learned local gate，而是：

1. 固定 `alpha = 0.9999` 或直接 `1.0`；
2. 只对 `sigma` 做一轮很窄的平台确认：
   - `sigma ∈ {16, 20, 24, 32}`
3. 平台确认之后，把主要精力转向 detector uncertainty model 修正：
   - early-iteration-aware sigma model
   - residual-aware sigma model
   - posterior variance recalibration

当前不建议继续推进：

- `alpha gate`
- `sigma gate`
- `lambda / beta / k_leak` 类全局标量学习

因为当前证据已表明，它们不是近期主线。

## 2026-03-22（阶段八下一轮评估器已实现：Sigma-Only Plateau + Uncertainty Model v1）

### 一、本轮实现目标

在保留当前 Stage8 评估器单入口的前提下，把下一轮主线正式切到：

1. `sigma-only` 平台确认
2. 非学习化、可解释的 `sigma schedule v1`

本轮不再继续扩 `alpha`，也不新增任何 learned gate。

### 二、代码实现

继续只扩展：

- `evaluate_stage8_stage6_heuristics.py`

新增 CLI：

- `--run-sigma-only-plateau`
- `--fixed-alpha-for-sigma-only`
- `--sigma-only-grid`
- `--run-sigma-schedule-v1`
- `--sigma-early-grid`
- `--sigma-late-grid`

默认值已固定为：

- `frames = 1000`
- `fixed_alpha_for_sigma_only = 1.0`
- `sigma_only_grid = {16, 20, 24, 32}`
- `sigma_early_grid = {8, 12, 16, 20, 24}`
- `sigma_late_grid = {1, 2, 4, 8, 12}`

### 三、本轮新增输出

已接入新的落盘产物：

- `stage6_sigma_only_plateau.csv`
- `stage6_sigma_only_best_by_snr.json`
- `stage6_sigma_only_summary.md`
- `stage6_sigma_schedule_v1_surface.csv`
- `stage6_sigma_schedule_v1_best.json`
- `stage6_sigma_schedule_v1_summary.md`

同时，现有 calibration / trace 产物继续保留，并把主比较对象切到：

- `baseline = (0.70, 1.0)`
- `hand_fix = (0.95, 4.0)`
- `sigma_only_best = (1.0, sigma_best)`

### 四、设计上的收口决策

这一轮已明确写死：

1. `alpha` 不再作为主研究变量，默认固定到 `1.0` 做平台确认。
2. 本轮正式帧数从上一阶段的 `2000` 减半到 `1000 per SNR`。
3. 当前主线不再是 `alpha × sigma` 大网格，而是：
   - `sigma-only plateau`
   - `sigma schedule v1`
4. `residual-aware sigma formula` 暂不在本轮实现，只作为下一轮分叉候选。
5. learned local gate 继续不是近期主线。

### 五、静态检查

已通过：

```bash
python3 -m py_compile afdm_joint_param_unrolled/evaluate_stage8_stage6_heuristics.py
```

### 六、下一步运行目标

本轮正式实验只需要回答：

1. `sigma=16` 是否已接近平台；
2. detector 是否仍系统性低估真实不确定性；
3. 这种低估是否仍主要集中在前两轮；
4. `sigma schedule v1` 是否比 `sigma-only best` 明显更优；
5. 下一步应写回 fixed sigma baseline，还是进入更细的 uncertainty model 设计。

## 2026-03-22（阶段八继续正式结果：Sigma-Only Plateau + Uncertainty Model v1 结果冻结）

### 一、本轮结果的主结论

这轮结果之后，阶段八的主线已经可以明确收口为：

> **先停止 `gate / 学参数` 这条线，把 Stage6 当成一个“detector uncertainty model 写错了”的系统来修。**

当前最硬的研究判断是：

1. Stage6 的主缺口是 **detector-side uncertainty calibration**，不是 outer-loop local gate。
2. `alpha` 之所以以前显得重要，很大程度上是在给 detector 的过度自信做协同修正。
3. 一旦 `sigma_inflation` 被拉到合适区间，`alpha` 的角色就收缩为协同项，而不是主导项。

### 二、这轮最重要的四个事实

#### 1. `sigma=16` 已足够作为当前 strongest fixed baseline

对应证据：

- `outputs_stage8_stage6_sigmaonly_v1/stage6_sigma_only_summary.md`

当前结果：

- `15 dB`: 最优 `sigma = 16`, `ber = 1.8828e-03`
- `20 dB`: 最优 `sigma = 16`, `ber = 1.0938e-04`
- `25 dB`: 最优 `sigma = 20`, `ber = 1.3281e-04`

按 `sigma` 聚合的平均 BER：

- `sigma = 16 -> 7.1549e-04`
- `sigma = 20 -> 1.1901e-03`
- `sigma = 24 -> 2.4486e-03`
- `sigma = 32 -> 1.0466e-02`

当前判断：

1. `sigma = 16` 已经足够作为 current strongest fixed reference。
2. `20` 只在 `25 dB` 单点略好，研究上不需要再继续围绕“大网格常数搜索”讲故事。
3. 若后续还补实验，也只值得做极窄的 `sigma-only` 收尾，而不是再做 `alpha × sigma` 扩展。

#### 2. `sigma schedule v1` 没有稳定赢过全局常数

对应证据：

- `outputs_stage8_stage6_sigmaonly_v1/stage6_sigma_schedule_v1_summary.md`

当前结果：

- seed `42`: average gain vs sigma-only best = `-5.468%`
- seed `123`: average gain vs sigma-only best = `-40.403%`
- seed `314`: average gain vs sigma-only best = `-5.445%`

这说明：

1. “前几轮大 sigma、后几轮回落”这个方向在机理上不荒谬。
2. 但在 current scaffold 和这版实现下，**时变 sigma schedule 不是主收益源**。
3. 因此此时不应继续往 `schedule / gate` 方向追加复杂度。

#### 3. detector miscalibration 已被直接量化坐实

对应证据：

- `outputs_stage8_stage6_sigmaonly_v1/stage6_detector_calibration_curves_summary.md`

baseline 的 `sym_err / v_x`：

- `15 dB`: `18.6 -> 59.2 -> 91.6 -> 147.6 -> 235.2`
- `20 dB`: `14.9 -> 81.8 -> 158.6 -> 295.7 -> 571.7`
- `25 dB`: `13.8 -> 94.3 -> 225.3 -> 497.7 -> 983.7`

这已经足够支持：

- baseline detector posterior variance `v_x` 不是“略偏乐观”，而是**系统性严重低估真实不确定性**。

而 `sigma_only_best` 下：

- `iter0` 仍然偏乐观；
- 但 `iter1` 之后很多点已经掉到 `< 1`，说明 current constant `sigma=16` 是在用一个粗暴常数把 detector 拉回可信区间，随后又可能变得偏保守。

因此，当前最稳的解释是：

> **`sigma_inflation` 不是在做普通调参，而是在替 detector 漏掉的一整块有效不确定性兜底。**

#### 4. outer-loop 的问题不是“更新太大”，而是“信息太假”

对应证据：

- `outputs_stage8_stage6_sigmaonly_v1/stage6_outerloop_traces_summary.md`

当前现象：

- `sigma_only_best` 下 `v_x` 更高；
- BER 前两轮下降更快；
- `channel_update_norm` 不一定更小，有时反而更大。

这说明真正发生的是：

> **先把 detector 的过度自信修正，outer-loop 才能承受更大的有效更新而不自毒。**

因此 outer-loop 不是当前主矛盾；主矛盾仍然是 detector 的 uncertainty scale。

### 三、这轮之后明确停止的方向

当前不再建议继续投入：

1. `alpha` 细扫  
   - 研究上已经足够说明其 best-constant 落在近似 `1.0` 的极限区。
2. local gate  
   - iter-layered oracle 与 sigma schedule v1 都没有给出足够证据。
3. `lambda / beta / k_leak` 回摆  
   - 这些方向在阶段八前面已经基本排掉。

### 四、下一步计划的正式收口

当前之后的计划不再是“继续调参数”，而是：

1. 把 `Stage6 + alpha = 1.0 + sigma = 16` 立成 current strongest fixed baseline。
2. 如需补实验，只补一个很窄的 `sigma-only` 收尾：
   - `sigma = 16, 20, 24`
3. 之后把主要精力全部转到：
   - early-iteration-aware sigma rule
   - residual-aware sigma model
   - posterior variance recalibration

换句话说：

- `alpha`：停
- `gate`：停
- `constant 大网格`：停
- `sigma = 16`：立成强基线
- 后续主线：**修 detector 的 effective uncertainty model**

## 2026-03-22（阶段九启动：Detector Uncertainty Model 主线切换）

### 一、本轮正式实现内容

阶段九已开始从“gate / 学参数”主线切换到 “detector uncertainty model 修正” 主线。代码层面已新增：

1. `Stage6-fixed-best` 基线导出  
   - 固定 `alpha = 1.0`
   - 固定 `sigma_inflation = 16`
   - 导出：
     - `stage6_fixed_best_summary.md`
     - `stage6_fixed_best_traces.csv`
     - `stage6_fixed_best_calibration.csv`

2. calibration dataset 导出层  
   - 统一导出：
     - `stage6_calibration_dataset.csv`
     - `stage6_calibration_dataset_summary.md`
   - 用于后续 uncertainty model 和 strongest fixed baseline 的统一对比

3. uncertainty model v1：`sigma_early_fix`  
   - 规则：`iter0 -> sigma_early`, `iter1+ -> sigma_late`
   - 导出：
     - `stage6_sigma_early_fix_surface.csv`
     - `stage6_sigma_early_fix_best.json`
     - `stage6_sigma_early_fix_summary.md`

4. uncertainty model v2：`residual_aware_sigma_v2`  
   - 规则：
     - `detector_sigma_used = c0 * sigma_w^2 + cr * empirical_residual_var`
   - 当前只走推理/诊断 override 路径，不改训练图
   - 导出：
     - `stage6_residual_aware_sigma_v2_surface.csv`
     - `stage6_residual_aware_sigma_v2_best.json`
     - `stage6_residual_aware_sigma_v2_summary.md`

### 二、阶段九冻结结论

当前阶段九的冻结方向正式写死为：

- `alpha`：停  
  - 研究上已收口到近似 `1.0`
- `gate`：停  
  - 不再作为近期主线
- `constant 大网格`：停  
  - 不再围绕 `alpha × sigma` 扩展扫图
- `sigma = 16`：立为 current strongest fixed baseline
- 后续主线：
  - `sigma early-fix`
  - `residual-aware sigma`
  - `posterior variance recalibration`（下一轮候选，不在本轮直接实现）

### 三、阶段九 smoke 验证结果

已在本地小规模 smoke 跑通，输出目录：

- `outputs_stage9_uncertainty_smoke2/`

当前 smoke 已确认以下阶段九新产物能正常落盘：

- `stage6_fixed_best_summary.md`
- `stage6_fixed_best_traces.csv`
- `stage6_fixed_best_calibration.csv`
- `stage6_calibration_dataset.csv`
- `stage6_calibration_dataset_summary.md`
- `stage6_sigma_early_fix_surface.csv`
- `stage6_sigma_early_fix_best.json`
- `stage6_sigma_early_fix_summary.md`
- `stage6_residual_aware_sigma_v2_surface.csv`
- `stage6_residual_aware_sigma_v2_best.json`
- `stage6_residual_aware_sigma_v2_summary.md`

### 四、下一步正式实验

后续正式实验不再围绕 gate 展开，而是直接回答下面三个问题：

1. `fixed_best = (alpha=1.0, sigma=16)` 是否稳定成立  
2. `sigma_early_fix` 是否稳定超过 `fixed_best`  
3. `residual_aware_sigma_v2` 是否稳定超过 `fixed_best`

如果 v2 在 BER 上没有稳定赢过 `fixed_best`，但 calibration 更合理，则下一轮优先进入：

- posterior variance recalibration

而不是重新回到 gate 主线。

## 2026-03-22（阶段九正式结果：fixed-best 站住，主线转向 posterior uncertainty output calibration）

### 一、本轮最硬的结果

当前阶段九正式结果已经把主线进一步收紧：

> **当前最强的系统不是“会自适应的 Stage6”，而是“内部 detector 用固定强校准 `(alpha=1.0, sigma=16)` 跑起来的 Stage6”。**

对应结果：

- `outputs_stage9_uncertainty/stage6_fixed_best_summary.md`
- `outputs_stage9_uncertainty/stage6_calibration_dataset_summary.md`
- `outputs_stage9_uncertainty/stage6_sigma_early_fix_summary.md`
- `outputs_stage9_uncertainty/stage6_residual_aware_sigma_v2_summary.md`

### 二、固定 strongest baseline 已正式坐实

当前 strongest fixed baseline 可正式冻结为：

- `Stage6-fixed-best = (alpha=1.0, sigma=16)`

对应 BER：

- `15 dB`: `1.9949e-03`
- `20 dB`: `1.6059e-04`
- `25 dB`: `4.1775e-05`

对应 calibration aggregate：

- baseline:
  - `mean_rho = 223.934`
  - `mean_eta = 5.295`
- fixed_best:
  - `mean_rho = 1.939`
  - `mean_eta = 0.310`

这说明：

1. baseline detector 仍是严重乐观失配；
2. `fixed_best` 已经把 detector 拉回了一个“不再自毒”的工作区；
3. 因此后续所有 uncertainty model 实验都应只与 `fixed_best` 比较。

### 三、阶段九 v1/v2 为什么都没有成为主候选

#### 1. `sigma_early_fix` 失败

结果：

- global best `(sigma_early, sigma_late) = (24, 8)`
- `mean_ber = 1.3328e-03`
- 明显劣于 `fixed_best mean_ber = 7.3242e-04`

各 seed 平均 gain 全为大幅负值：

- seed 42: `-208.659%`
- seed 123: `-457.276%`
- seed 314: `-275.331%`

这说明：

> **问题不是“只要知道前面更重、后面更轻，就能用粗粒度时变 sigma 修好 detector”。**

更稳的解释是：

- 当前 detector 失配不是简单的“按 outer iteration 切两段”就能补对；
- 用过粗的 schedule 直接改 detector 内核，会同时改变 detector 的推断轨迹，代价过大。

#### 2. `residual_aware_sigma_v2` 失败

结果：

- global best `(c0, cr) = (8, 4)`
- `mean_ber = 1.6994e-03`
- 同样明显劣于 `fixed_best`

aggregate calibration 也暴露出问题：

- `residual_aware_sigma_v2_best: mean_rho = 68.776`
- 虽然 `mean_eta = 0.192`
- 但 posterior uncertainty 的整体尺度仍非常不合理

这说明：

> **raw residual 不是一个足够干净的 detector internal sigma proxy；直接把 raw residual 塞进 detector 内核 sigma 公式，这种耦合方式当前是错的。**

更具体地说，raw residual 混合了：

- 热噪声
- SIC 残留
- 信道偏差
- detector 自己的错误均值
- 以及有效信号结构本身

因此“直接 residual-aware 改 detector internal sigma”当前不应继续作为主候选。

### 四、本轮最值钱的理论收获

阶段九正式结果把问题拆成了两个层级：

#### 层级 A：detector 内部真正好用的 sigma

当前看起来：

- `sigma = 16`
- 在 detector 内部是**最稳、最好用**的 fixed working point

#### 层级 B：detector 输出给外环的 posterior uncertainty

也就是 `v_x` 这类量。

当前即使在 `fixed_best` 下：

- `mean_rho = 1.939`
- `mean_eta = 0.310`

也说明 detector output uncertainty 仍未完全“物理正确”。

因此当前最重要的结论是：

> **“让 detector 内部好用”和“让 detector 输出给外环的 uncertainty 可校准”不是同一件事。**

### 五、主线正式收口

因此，当前不再建议继续投入：

1. `alpha`
2. local gate
3. 继续改 detector internal sigma 公式作为第一优先级

当前之后的正式主线改为：

1. 固定 detector internal working point：
   - `alpha = 1.0`
   - `sigma = 16`
2. 直接修 detector 输出 uncertainty：
   - posterior variance recalibration
   - per-iteration `v_x` rescale / affine recalibration
   - 之后再考虑更轻量的 uncertainty calibration head

换句话说，下一步最值得做的是：

> **不再先改 detector 内核，而是保留 `fixed_best=(1.0,16)`，转而修 detector 输出给 outer loop 的 uncertainty 本身。**

### 六、冻结结论

当前阶段九可冻结为：

- `alpha`：停
- `gate`：停
- `constant 大网格`：停
- `fixed_best = (1.0, 16)`：继续作为 current strongest fixed baseline
- `sigma_early_fix`：当前失败，不继续作为主候选
- `residual_aware_sigma_v2`：当前失败，不继续作为主候选
- 后续主线：
  - **posterior uncertainty output calibration**
  - 而不是继续修改 detector internal sigma

## 2026-03-22（阶段九继续正式结果：Posterior Uncertainty Output Calibration v1）

### 一、实验设置

本轮正式实验目录：

- `outputs_stage9_vxrecal`

当前主线固定为：

- `fixed_best = (alpha=1.0, sigma=16)`
- 不再继续扩 `alpha`
- 不再继续推进 local gate
- 不再继续修改 detector internal sigma 作为第一优先级

本轮只验证：

1. 固定 `fixed_best` 作为 current strongest fixed baseline；
2. 从 `fixed_best` calibration dataset 自动拟合 per-iteration `v_x` rescale 系数；
3. 仅修改 detector 输出给 outer-loop 的 posterior variance `v_x`；
4. 检查 calibration 是否改善，以及 final BER 是否守住。

### 二、固定基线再次确认

`fixed_best` 结果见 `stage6_fixed_best_summary.md`：

- `15 dB`: `1.9949e-03`
- `20 dB`: `1.6059e-04`
- `25 dB`: `4.1775e-05`

结论不变：

> **`fixed_best = (alpha=1.0, sigma=16)` 已继续站稳，当前仍是 Stage6 uncertainty-model 主线下的 strongest fixed baseline。**

### 三、calibration 现状再次量化

`stage6_calibration_dataset_summary.md` 聚合结果：

- `baseline`: `mean_rho=223.934`, `mean_eta=5.295`
- `fixed_best`: `mean_rho=1.939`, `mean_eta=0.310`

解释：

- `baseline` 仍是严重乐观失配；
- `fixed_best` 已把 detector 拉回可工作区；
- 但 `fixed_best` 下的 posterior variance 仍未完全“物理正确”：
  - `mean_rho` 仍未贴近 `1`
  - `mean_eta` 也明显不在理想平衡区

这进一步支持：

> **detector internal sigma 的“好工作点”和 detector 输出 uncertainty 的“可校准性”不是同一件事。**

### 四、v_x recalibration v1 的拟合结果

`stage6_vx_recalibration_coeffs_summary.md` 给出的 per-iteration scale 为：

- iter `0`: `9.3075`
- iter `1`: `0.2500`
- iter `2`: `0.2500`
- iter `3`: `0.2500`
- iter `4`: `0.6076`

这组系数非常有信息量：

- 第一轮需要大幅放大 `v_x`，说明 `fixed_best` 在 `iter0` 仍明显偏乐观；
- 中间几轮反而需要压低，说明 `fixed_best` 在后续轮次又偏保守；
- 这和前面的 calibration 诊断完全一致。

### 五、v_x recalibration v1 的真实结果

需要特别说明：

`stage6_vx_recalibration_v1_summary.md` 中给出的

- `vx_recalibration_v1 mean_ber = 9.6199e-03`

并不能代表最终 BER，它更像是把所有 outer iterations 的 BER 一起平均了；  
按 `stage6_vx_recalibration_v1_traces.csv` 只看最终轮 `outer_iter=4`，真实 final mean BER 为：

- `fixed_best = 7.3242e-04`
- `fixed_best + vx_recalibration_v1 = 7.3586e-04`

也就是说：

- final BER 只差约 `0.47%`
- 可以视为**几乎持平**
- 并没有出现 summary 文本看起来那种“明显崩掉”

### 六、为什么这轮是正向推进

`stage6_vx_recalibration_v1_calibration.csv` 聚合结果显示：

- `fixed_best`: `mean_rho=1.939`, `mean_eta=0.310`
- `fixed_best+vx_recalibration_v1`: `mean_rho=0.716`, `mean_eta=0.310`

这说明：

1. `v_x` output recalibration 明显改善了 posterior calibration；
2. `eta` 基本不变，这是合理的，因为 detector internal sigma 完全没动；
3. final BER 几乎持平，说明这种 output-side 修正风险很低。

因此，这轮结果的真正价值不是“v1 已经提升 BER”，而是：

> **它第一次证明了：只修 detector 输出 uncertainty 这个接口，就能显著改善 calibration，且几乎不伤性能。**

### 七、对阶段九主线的进一步收紧

当前可以把项目主线进一步收紧为：

- 不该继续优先改的：
  1. `alpha`
  2. local gate
  3. detector internal sigma 大网格或 detector internal sigma 公式
- 当前真正该修的：
  1. detector 输出给 outer-loop 的 posterior uncertainty
  2. 尤其是 `v_x` 的 calibration 与使用方式

更准确地说：

> **当前最强的系统不是“会自适应的 Stage6”，而是“detector internal sigma 固定在好工作点 `(alpha=1.0, sigma=16)`，然后单独修 output uncertainty 接口”的 Stage6。**

### 八、下一步正式建议

后续实验不再回到：

- `best constant` 大网格
- `alpha`
- gate
- detector internal sigma 继续调参

下一步应改为：

1. 保留 `fixed_best=(1.0,16)` 作为唯一正式对照基线；
2. 优先推进 posterior variance recalibration v2：
   - `affine recalibration: v_x' = a_t v_x + b_t`
   - 或 `clipped recalibration`
3. 在此基础上，再研究 outer-loop 如何**真正消费** calibrated `v_x`：
   - uncertainty-aware SIC
   - reliability-aware refit / weighting

### 九、冻结结论

本轮可冻结为：

- `fixed_best=(1.0,16)`：继续作为 strongest fixed baseline
- `sigma_early_fix`：失败，不继续
- `residual_aware_sigma_v2`：失败，不继续
- `vx recalibration v1`：
  - final BER 基本守住
  - calibration 明显改善
  - 已证明 output uncertainty 是正确改动接口
- 下一步主线：
  - **posterior uncertainty recalibration v2**
  - **让 outer-loop 真正使用 calibrated uncertainty**
  - 而不是回到 detector internal sigma 或 local gate

## 2026-03-23（阶段十正式结果：uncertainty-aware SIC 反证成立，停止继续扩这版公式）

### 一、正式结果

基于 `outputs_stage10_unc_sic` 的完整运行结果，这一轮已经可以把阶段十的主结论写硬：

> **把 calibrated `v_x` 通过 `w = 1 / (1 + \kappa v_x)` 直接映射成 SIC 振幅缩放，在当前 Stage6 scaffold 下是错误方向。**

当前 strongest fixed baseline 继续稳定成立：

- `fixed_best = (alpha=1.0, sigma=16)`
- `15 dB`: `2.0464e-03`
- `20 dB`: `1.0742e-04`
- `25 dB`: `1.0308e-04`

`vx recalibration v1` 的方向仍然成立：

- `fixed_best final_mean_ber = 7.5231e-04`
- `fixed_best + vx_recalibration_v1 final_mean_ber = 7.5810e-04`
- `fixed_best: mean_rho = 1.937, mean_eta = 0.308`
- `fixed_best + vx_recalibration_v1: mean_rho = 0.721, mean_eta = 0.308`

也就是说：

- `v_x` output-side recalibration 继续显著改善 posterior calibration
- final BER 仍在可接受误差内
- output uncertainty 接口本身仍然是正确主线

### 二、为什么 uncertainty-aware SIC 这版可以收口

这一轮不再是“没调到位”，而是已经对这条具体假设给出了反证：

- 完整结果中 `best_global (sic_kappa) = 0.0`
- 相对 `fixed_best`：
  - `rel_gain_vs_fixed_best = -0.769%`
- 相对 `fixed_best + vx_recalibration_v1`：
  - `rel_gain_vs_vx_recal_v1 = 0.000%`

更重要的是，`surface.csv` 显示：

- 只要 `kappa > 0`
- BER 在多 seed、多 SNR 下几乎单调恶化
- `kappa` 越大，恶化越明显

这说明：

1. 当前实现路径已经接通，不再是 bug；
2. 最优点退化到 `kappa = 0`，说明这条公式不是“还可微调”，而是方向上就不对；
3. 因此不建议继续扩：
   - 更细的 `kappa` 网格
   - 更大的 `kappa`
   - 或继续在这版 `inv_linear` SIC weighting 上消耗实验预算

### 三、机理解读

当前最合理的解释不是“uncertainty 没用”，而是：

> **uncertainty output 接口修对了，但把 uncertainty 直接映射成 SIC 振幅缩放是错误的消费方式。**

更具体地说：

1. `v_x` 更接近真实 posterior uncertainty，并不等于它适合直接变成 cancellation amplitude 的反比权重；
2. `w < 1` 的结构会系统性压低 `mu_prev`，导致 under-cancellation；
3. 当前 `fixed_best=(1.0,16)` 下 detector internal working point 已经偏保守，再额外压一层 SIC 幅度，会让结构化残差更大；
4. 因此这轮结果更像是在证明：
   - calibrated `v_x` 是对的
   - 但 current outer-loop 不适合用 `1/(1+\kappa v_x)` 这种连续缩幅方式消费它

### 四、阶段十冻结结论

本轮正式冻结为：

- `fixed_best = (1.0,16)`：继续作为唯一 strongest fixed baseline
- `vx recalibration v1`：继续作为当前最稳的 output-side uncertainty calibration
- `uncertainty-aware SIC (inv_linear amplitude weighting)`：
  - 路径已接通
  - 已被完整结果反证
  - 停止继续扩展

### 五、下一步建议

后续不再继续：

- `alpha`
- local gate
- detector internal sigma
- 这版 `uncertainty-aware SIC` amplitude weighting

下一步主线建议收敛到两条更小的线：

1. 继续推进 `v_x recalibration v2`
   - affine recalibration
   - clipped recalibration
2. 若仍要探索 uncertainty 的消费方式
   - 优先尝试更温和、选择型的接口
   - 例如 skip / freeze / threshold 类规则
   - 而不是连续振幅缩放

一句话总结：

> **阶段十的价值不是“又否了一条线”，而是把问题进一步缩窄到了：`v_x` output calibration 是对的，但 current SIC amplitude weighting 是错的。**

## 阶段十一启动：Posterior Uncertainty Recalibration v2 + Skip/Freeze Probe

阶段十结果收口后，项目主线继续固定为：

- `fixed_best = (alpha=1.0, sigma=16)`：唯一 strongest fixed baseline
- `vx recalibration v1`：当前已验证的 output-side uncertainty 修正版本
- `uncertainty-aware SIC (inv_linear amplitude weighting)`：正式停止继续扩展

阶段十一的实现策略改为两步：

1. 重新实现更保守的 `vx recalibration v2`
   - `affine`
   - `clipped`
2. 只在 v2 结果落地后，再做 very-light `skip/freeze` 小试验
   - 不再做连续幅度缩放
   - 只测试 uncertainty 是否更适合被“选择型”消费

本轮实现约束：

- 不再碰：
  - `alpha`
  - local gate
  - detector internal sigma
  - SIC amplitude weighting
  - uncertainty-aware refit weighting
- v2 的目标不是追 BER 大涨，而是：
  - calibration 比 v1 更稳
  - final BER 继续守住

阶段十一新增的具体实现方向：

- `v2_affine`
  - 从普通 least-squares 改成 identity-biased 的保守拟合
  - 显式限制 `a_t` 远离 0
  - 显式限制 `b_t` 不允许主导输出
- `v2_clipped`
  - clip 区间来自更保守的 scaled-`v_x` quantile
  - 强制保留最小区间宽度
  - 禁止退化成 `vmin == vmax` 的逐轮常数替换
- `skip/freeze probe`
  - 默认关闭
  - 只在 `v2` 评估后使用当前更优的 uncertainty source
  - 仅对极高 `v_x'` 的局部符号做 hard skip/freeze
  - 不再做 `1/(1+\kappa v_x)` 这类连续缩幅

## 阶段十一正式结果：`v1` 继续作为当前最优 output-side recalibration

阶段十一完整结果进一步把主线收紧为：

- `fixed_best = (alpha=1.0, sigma=16)`：继续作为唯一 strongest fixed baseline
- `vx recalibration v1`：继续作为当前最实用的 output-side uncertainty calibration
- `v2_affine / v2_clipped`：实现问题已排除，但没有在任务导向的 calibration-performance 折中上超过 `v1`

### 一、结果摘要

本轮关键结果：

- `fixed_best final_mean_ber = 7.5231e-04`
- `fixed_best + vx_recalibration_v1 final_mean_ber = 7.5810e-04`
- `fixed_best + vx_recalibration_v2_affine final_mean_ber = 7.5738e-04`
- `fixed_best + vx_recalibration_v2_clipped final_mean_ber = 7.6136e-04`

aggregate calibration:

- `fixed_best: mean_rho = 1.937`
- `v1: mean_rho = 0.721`
- `affine: mean_rho = 0.478`
- `clipped: mean_rho = 0.646`

但这一轮必须按 `|rho - 1|` 来理解，而不是把 `rho` 越压越小视为越好：

- `fixed_best: |rho-1| = 0.937`
- `v1: |rho-1| = 0.279`
- `affine: |rho-1| = 0.522`
- `clipped: |rho-1| = 0.354`

因此：

> **当前最优点仍然是最简单的 `v1`，不是更复杂的 affine / clipped。**

### 二、这轮最重要的新增认识

阶段十一已经说明：

1. `v2_affine / v2_clipped` 这两条线现在已经不是“实现坏了”：
   - affine 不再塌成 `a≈0`
   - clipped 不再出现 `vmin == vmax`
2. 即便在实现修好之后，更复杂的 family 仍没有超过 `v1`
3. 因此当前面对的不是“再把拟合做对一点就能赢”，而是：

> **在 current Stage6 scaffold 下，posterior calibration 是一个 task-aware calibration 问题，而不是单纯把统计量尽量逼近 `rho=1` 的问题。**

更具体地说：

- affine 在 `iter0` 上修得最漂亮
- 但会把 `iter1..4` 拉得更保守
- clipped 更温和，但仍没有比 `v1` 更平衡

这说明：

> **`v1` 之所以继续最好，不是偶然，而是因为它在“早期 optimism 修正”和“后期不过度保守”之间取得了当前最合适的折中。**

### 三、阶段十一冻结结论

本轮正式冻结为：

- `fixed_best = (1.0, 16)`：继续作为 strongest fixed baseline
- `vx recalibration v1`：继续作为当前最佳 uncertainty 输出校准器
- `v2_affine / v2_clipped`：
  - 已完成工程验证价值
  - 但不再继续作为主 family 扩展

换句话说：

> **阶段十一没有推翻主线，反而把主线收得更紧了：`v_x` output-side recalibration 这条路是对的，但在当前 Stage6 scaffold 下，最实用的版本仍然是最简单的 `v1`。**

### 四、下一步建议

当前最合理的选择有两个层级：

1. 首选收敛方案：
   - 正式立住 `fixed_best`
   - 正式立住 `v1` 为最佳 recalibration
   - 停止继续扩 `affine / clipped`
   - 开始转入结果整理、机理总结和论文叙事收束
2. 若还要再打一枪：
   - 只做一个 `hybrid v3`
   - `iter0` 单独校准
   - `iter1..4` 保持 `v1`

当前明确不建议继续：

- 继续细扫 `affine / clipped`
- 回到 `alpha / gate / detector internal sigma`
- 重新探索连续缩幅型 uncertainty usage

阶段十一之后的当前共识应写成：

> **output-side recalibration 是正确接口；当前最优实现是简单的 per-iteration scalar recalibration (`v1`)；更复杂的 affine / clipped 已证明不带来更好的任务导向折中。**

## 阶段十一后：学习化研究方向排序

当前总判断可以正式收口为：

> **有必要上神经网络，但真正值得开主线的，不再是继续抠 `vx -> vx'` 这类 output scalar recalibration，而是去接管那些“传统先验写不干净、但结构又很强”的子问题。**

在当前冻结共识下，后续若继续推进学习化，研究方向优先级固定为：

### 1. `fractional-Doppler + SP 干扰下的 support / leakage-aware JCED/CE 模块`

这是当前最值得立项的第一方向。

它排第一的原因：

- 当前传统链路的真正结构性痛点，不在 `vx -> vx'` 标量映射，而在：
  - SP 导频下数据干扰强
  - fractional Doppler 会把理想点稀疏 support 打散成 leakage cluster / off-grid spread
  - 传统 OMP/LS 需要在过完备字典里盲搜更多泄漏分量，复杂度和不稳定性都会上升
- 这个子问题天然更像“从受干扰、带局部相关结构的观测里恢复簇状/带状有效信道”：
  - 正是 CNN / UNet / CENet / leakage-aware refinement 更擅长的任务

因此，下一阶段若只开一条真正的 DL 主线，最推荐的是：

> **support / leakage-aware 的 model-driven JCED/CE 网络。**

### 2. `uncertainty-conditioned outer-loop trust controller`

这是第二优先级，但必须明确：它不是 scalar gate，也不是 scalar scale。

它排第二的原因：

- 阶段九到阶段十三已经证明：
  - calibrated uncertainty 本身有价值
  - 但把 uncertainty 直接映射成连续幅度缩放是错的
- 因此如果后续还要让 outer-loop 消费 uncertainty，更合理的问题形式应该是：
  - 该不该信
  - 信哪一部分
  - 用 hard / soft / skip / freeze / refine-only 哪种动作

也就是说，它应该被定义成：

> **按符号 / 按 cluster / 按 frame 的 structured trust decision 问题。**

之所以不排第一，是因为当前证据虽然说明这是“真问题”，但它的设计风险仍高于 leakage-aware JCED/CE。

### 3. `learned soft pseudo-pilot / denoising feedback block`

这是第三优先级。

它排第三的原因：

- 当前 outer-loop 里的硬判决 generalized pilot 具有天然的错误传播风险
- 真正适合学习接管的，不是末端 scalar recalibration，而是：
  - soft pseudo-pilot 构造
  - confidence mask
  - denoised symbol expectation
- 这类模块本质上是在接管“非高斯、结构化、会闭环自毒”的先验块，比简单学 `v_x` 标量更符合 DL 擅长的区域

它之所以排第三，是因为：

- 它同样是很有希望的结构化方向
- 但目前相较第一名，缺少更直接的复杂度 / leakage 痛点证据钉死

### `output-side posterior uncertainty recalibration` 的新定位

这一方向不再作为“下一阶段需要继续深挖的 DL 主线”，而改为：

- 已完成的主线成果
- 当前 uncertainty interface 的冻结结果
- 其当前最优实现是 `vx recalibration v1`

更具体地说：

- `v1` 已经证明 output-side calibration 这条接口是对的
- affine / clipped / learned 都没有超过它
- 因此这条线现在更适合作为：
  - 后续所有 outer-loop / JCED 学习模块的安全 anchor
  - 而不是继续作为主要立项方向去细抠 scalar family

### 当前明确排除的学习化方向

为了避免后续回摆，当前研究排序中明确不建议重新进入：

- `alpha`
- local gate
- detector internal sigma learning
- continuous uncertainty-aware SIC amplitude weighting
- 围绕 `vx -> vx'` 的 learned scalar recalibration 继续细扫
- 大而黑盒的 end-to-end DNN 替换

也就是说，当前这些方向是“研究方向排序”，不是“下一轮并行开做”的承诺；第 1 名是当前最值得押注的主候选，第 2、3 名是候选储备，而 `output-side recalibration` 已经从“主攻方向”转为“冻结成果与安全 anchor”。

## 阶段十二：Output-Side Posterior Uncertainty Recalibration（Hybrid + Learned）

阶段十二正式沿 `output-side posterior uncertainty recalibration` 主线推进，并把比较线固定为：

- `fixed_best = (alpha=1.0, sigma=16)`
- `fixed_best + vx recalibration v1`
- `fixed_best + vx recalibration v3 hybrid`
- `fixed_best + learned output recalibration`

其中：

- `hybrid_v3`：`iter0` 单独用 affine 校准，`iter1..4` 沿用 `v1`
- learned 版本：只在 `fixed_best` 的输出侧加一个 very-light、identity-biased 的 frame-level scale head，不碰 detector internal sigma，不碰 gate，不碰 refit

### 一、阶段十二核心结果

#### 1. `fixed_best` 继续稳定成立

`outputs_stage12_vxrecal_hybrid_learned/stage6_fixed_best_summary.md` 给出的固定强基线仍然稳定：

- `15 dB = 2.0257e-03`
- `20 dB = 1.0141e-04`
- `25 dB = 4.0064e-05`

这说明当前 strongest fixed working point 没有动摇。

#### 2. `v1` 仍然是当前最实用的 uncertainty calibrator

`outputs_stage12_vxrecal_hybrid_learned/stage6_vx_recalibration_v1_summary.md` 显示：

- `fixed_best final_mean_ber = 7.2241e-04`
- `fixed_best + vx recalibration v1 final_mean_ber = 7.2825e-04`
- `fixed_best: mean_rho = 1.939`
- `v1: mean_rho = 0.720`

因此阶段十二没有改变阶段十一的主结论：

> **`v1` 继续是当前最平衡的 output-side uncertainty calibrator。**

它并不是 BER 最低的版本，但在当前 scaffold 下，它仍然提供了最好的 calibration-performance 折中。

#### 3. `hybrid_v3` 没有超过 `v1`

`outputs_stage12_vxrecal_hybrid_learned/stage12_vx_recalibration_v3_hybrid_summary.md` 显示：

- `fixed_best + vx recalibration v3 hybrid final_mean_ber = 7.2992e-04`
- 相对 `fixed_best`：`-1.040%`
- 相对 `v1`：`-0.229%`

但它也带来了一个重要机理结论：

- `v1 iter0_rho = 0.935`
- `hybrid_v3 iter0_rho = 1.013`
- `hybrid_v3` 的 `iter1..4` 基本与 `v1` 重合

这说明：

> **`iter0` 特化这件事本身是有局部价值的，但单独把 `iter0` 校到统计上更漂亮，并不足以带来更好的 end-to-end tradeoff。**

换句话说，`v1` 在 `iter0` 的轻微 under-confidence，很可能恰恰是当前 scaffold 下更有利的工作点，而不是需要被完全修平的偏差。

#### 4. learned recalibration 学到了非平凡映射，但没形成更好的 task-aware interface

`outputs_stage12_vxrecal_hybrid_learned/stage12_vx_recalibration_learned_summary.md` 显示：

- `fixed_best + learned output recalibration final_mean_ber = 7.2908e-04`
- 相对 `fixed_best`：`-0.924%`
- 相对 `v1`：`-0.115%`

同时 learned head 并不是恒等：

- `mean_learned_scale = 1.898`
- `scale_range = 0.063 ~ 14.159`
- train / val loss 很接近：
  - `train_loss = 0.087720`
  - `val_loss = 0.085747`

这说明：

> **learned head 不是“没学到东西”，而是它学到的统计校准方式，并没有转化成更好的 task-aware uncertainty interface。**

更具体地说，learned 版本把 task-aware score 从 `v1` 的 `0.365` 拉到了 `0.163`，但没有带来 BER 改善。逐轮 `rho` 进一步说明问题：

- `iter0 = 0.733`
- `iter1 = 0.597`
- `iter2 = 0.969`
- `iter3 = 1.705`
- `iter4 = 1.501`

这表示它并不是单纯更优，而是：

- 早期更保守
- 后期从 `v1` 的 over-conservative，转成了明显的 late optimism

也就是说，当前 task-aware 指标虽然成功惩罚了 late over-conservatism，但**没有惩罚 late optimism**，因此它会高估 learned 版本的质量。

### 二、阶段十二最重要的研究判断

阶段十二没有推翻主线，反而把主线收得更紧了：

1. `fixed_best = (1.0, 16)` 继续是 strongest fixed baseline
2. `vx recalibration v1` 继续是当前最佳 uncertainty 输出校准器
3. `hybrid_v3` 证明了：
   - `iter0` 特化有局部价值
   - 但单独修漂亮 `iter0 rho` 不等于更好的系统工作点
4. learned recalibration 证明了：
   - 小型神经网络确实能学到非平凡的 uncertainty mapping
   - 但当前训练目标更像在优化统计校准，而不是 Stage6 真正需要的 task-aware uncertainty interface

因此当前最稳的结论可以写成：

> **Stage12 没有推翻主线，反而把主线进一步钉死：`v_x` output-side recalibration 这条路是对的，但在当前 Stage6 scaffold 下，最实用的版本仍然是最简单的 `v1`；无论是 `iter0` 特化的 hybrid，还是 very-light learned recalibrator，都还没有在 task-aware calibration–performance 折中上超过它。**

### 三、阶段十二冻结建议

本轮建议正式冻结为：

- `fixed_best = (1.0, 16)`：继续作为 strongest fixed baseline
- `vx recalibration v1`：继续作为当前最佳 uncertainty output calibrator
- `hybrid_v3`：
  - 作为“`iter0` 特化有局部价值”的证据保留
  - 但不升级为新主线
- learned output recalibration：
  - 作为“small learned module 能学到非平凡 uncertainty mapping”的证据保留
  - 但当前不升级为新主线

当前因此不建议：

- 继续深挖 `hybrid_v3` family
- 把当前这个 learned objective 再做小修小补后继续细扫
- 回到 `alpha / gate / detector internal sigma`

如果后续还要沿 learning 往前走，阶段十二给出的最硬约束是：

> **下一代 learned module 必须优化真正的 task-aware interface，而不能只优化统计 calibration 本身。**

## 2026-03-24（阶段十三 `v3` smoke：frame-level 风险接通，但 learned 仍未超过 `v1`）

### 一、这轮真正完成了什么

阶段十三前几版最大的残留问题，不是 learned 一定更差，而是：

- `frame_worst_late_optimism` 一直没有真正接通到 audit / summary
- 因此很多关于 late-risk 的判断仍带有“指标是否可信”的不确定性

这轮 `outputs_stage13_anchor_smoke_v3` 的价值首先不在于性能，而在于：

> **它把“测不准”修成了“测得准”。**

具体表现为：

- `stage13_metric_audit_summary.md` 中 4 条 profile 都已有真实 `frame_rows=500`
- `stage13_vx_recalibration_learned_anchor_summary.md` 中已有  
  `frame_row_counts: fixed_best=500, v1=500, variant=500`
- `frame_worst_late_optimism` 不再是 `nan`

因此从这一轮开始，`late optimism` 与 frame-level worst-case risk 的比较终于可以被视为可信证据，而不再只是辅助参考。

### 二、接线修好以后，结论反而更清楚

在真实 frame-level 风险接通之后，当前三条主比较线表现为：

- `fixed_best final_mean_ber = 1.2891e-03`
- `fixed_best + vx recalibration v1 final_mean_ber = 1.3184e-03`
- `fixed_best + anchored learned final_mean_ber = 1.3184e-03`

也就是说：

- learned 已经被拉回到与 `v1` **BER 持平**
- 但仍然没有形成优于 `v1` 的 uncertainty interface

更关键的是风险项现在已经能真实拉开：

- `v1 task_risk_score = 1.077`
- `anchored learned = 1.193`

以及：

- `v1 frame_worst_late_optimism = 0.271`
- `anchored learned = 0.351`

这说明：

> **当 frame-level 风险真正可见后，learned 并没有被“冤枉”；它确实仍然比 `v1` 更危险。**

### 三、`iter4` 的收窄有用，但还不够

这轮另一项关键修改是：

- `iter4 residual bound` 单独从 `log(1.25)` 收窄到 `log(1.10)`

它带来的结果是正向的：

- 前一版 `v2c` 中，learned 的 `iter4_rho ≈ 1.721`
- 本轮 `v3` 中，learned 的 `iter4_rho ≈ 1.515`

因此可以确定：

> **单独收窄最后一轮 residual freedom 是有效的。**

但它仍然没有压回 `v1` 的安全区：

- `v1 iter4_rho ≈ 1.375`
- `learned iter4_rho ≈ 1.515`

所以当前 learned 线的剩余问题已经非常具体，不再是笼统的“目标不对”：

- 它已经不再明显失控
- 但最后一轮仍然比 `v1` 更乐观
- 这部分乐观 overshoot 仍足以让它无法在风险上超过 `v1`

### 四、阶段十三现在可以下一个更硬的判断

阶段十二给出的结论是：

- learned 不是没学到东西
- 问题在于 learned objective 和 outer-loop 真正需要的 task-aware uncertainty interface 没对齐

阶段十三 `v3` 进一步把这个判断钉死成：

> **即使把 frame-level risk 指标真正接通，并对 iter4 加更硬的 anti-optimism 约束，当前 anchored learned scalar recalibration 仍然没有在 BER 持平的前提下，把风险压到不高于 `v1`。**

因此，这轮已经不再只是“继续调一调 loss 看看”，而更像是：

- 证据链已经足够完整
- 现有 learned scalar recalibration family 的收益上限已经基本摸到

### 五、阶段十三冻结建议

本轮建议把结论正式冻结为：

- `fixed_best = (1.0, 16)`：继续作为 strongest fixed baseline
- `vx recalibration v1`：继续作为当前最佳、最实用的 uncertainty output calibrator
- `stage13 anchored learned`：
  - 作为“以 `v1` 为 anchor 的 learned residual 修正可以把 BER 拉回到与 `v1` 持平”的证据保留
  - 作为“frame-level worst late optimism 已真实接通”的方法学进展保留
  - 但不升级为新主线

当前因此进一步不建议：

- 继续沿当前 learned scalar recalibration family 做更多 smoke / 正式版细扫
- 把更多精力投入到继续抠 `iter4` 的 loss 系数和 bound
- 回到 `alpha / gate / detector internal sigma / uncertainty-aware SIC`

如果需要一个当前最稳的冻结句，可以写成：

> **阶段十三 `v3` 表明：在 frame-level late-risk 指标真正接通之后，anchored learned scalar recalibration 仍未在 BER 持平的前提下超过 `vx recalibration v1`。因此，`v1` 继续作为当前最终 uncertainty interface 的最优实现，阶段十三 learned 线以“方法学排障完成、性能未超 incumbent”收口。**
