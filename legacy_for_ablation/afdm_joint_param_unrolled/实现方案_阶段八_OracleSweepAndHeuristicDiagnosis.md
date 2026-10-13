# 实现方案：阶段八 Oracle Sweep + Heuristic Breakpoint Diagnosis

## 1. 目标

阶段八不直接新增 learnable module，而是先做一轮“双线并行、诊断优先”的研究基础设施，回答下面三个问题：

1. 当前 `Stage6 fixed` 与 `TradParam fixed` 的 anchor 是否已经接近 oracle。
2. 当前真正存在 oracle gap 的 heuristic 属于哪一类：
   - support-side
   - refit-side
   - detector-side
   - outer-loop side
3. 阶段六/七中“学参数增益不明显”的原因，更像是：
   - anchor 已接近 oracle
   - 还是条件依赖存在，但当前全局标量参数化没有抓住。

这轮只做诊断代码和研究记录，不改变现有 `train_* / verify_* / compare_*` 主入口语义。

## 2. 诊断对象

- `Stage6 fixed`
- `TradParam fixed`

已训 `full` checkpoint 不参与 oracle sweep，只用于 residual utilization 统计。

## 3. 代码接口

### 3.1 Stage6 诊断入口

在 `afdm_joint_param.py` 中新增 inference-only 入口：

- `ParamLearnedJointReceiver.diagnose(...)`

该入口不写回 ckpt，不进入训练图，不改变现有 `forward()` 的训练/验证语义。

允许覆盖的诊断量：

- `lambda_ls`
- `lambda_scale`
- `alpha`
- `beta`
- `sigma_update_blend`
- `detector_sigma_inflation`
- `k_leak`
- `seed_mult`
- `expand_mult`

其中 `seed_mult / expand_mult` 通过现有 `support_stats.seed_mask / support_mask` 把 active atoms 分成：

- seed atoms
- expanded-only atoms

然后在 refit 的 ridge 正则里做两组 loading。

### 3.2 Strict traditional 诊断入口

在 `afdm_traditional_param.py` 中新增 inference-only 入口：

- `TraditionalParamJointReceiver.diagnose(...)`

允许覆盖的诊断量：

- `lambda_factor`
- `lambda_factor_scale`
- `gamma_h`
- `gamma_x`
- `pic_damp`
- `sigma_update_blend`
- `detector_sigma_inflation`
- `k_leak`
- `tau_h_factor`
- `tau_h_sigma_factor`
- `seed_mult`
- `expand_mult`

strict traditional 同样复用 `support_stats.seed_mask / support_mask` 做 `seed vs expanded-only` 两组 ridge。

## 4. 统一诊断脚本

新增：

- `diagnose_joint_heuristics.py`

职责：

1. 共享固定 seed 的 verify 风格样本生成。
2. 在同一批样本上同时评估：
   - `Stage6 fixed`
   - `TradParam fixed`
   - 各类 oracle sweep 候选
3. 读取已训 `full` checkpoint，生成 residual utilization 统计。

### 4.1 当前条件轴

第一轮固定：

- `SNR = 15 / 20 / 25 dB`
- `frames = 200 per SNR`
- `channel_type = EPA / EVA`
- `speed bin = low / high`，按当批样本速度中位数二分
- `support_count bin = low / high`，按 `support_count` 中位数二分

当前 verify 体系固定 `P_paths = 5`，阶段八第一轮不新增 path-count sweep。

## 5. 候选家族与 sweep 网格

### 5.1 第一层粗筛

正尺度类：

- `{0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 4.0} × anchor`

阻尼/门控类：

- `{0.10, 0.30, 0.50, 0.70, 0.85, 0.95}`

离散结构类：

- `k_leak ∈ {0,1,2,3,4}`
- `tau_h_factor ∈ {0, 0.0025, 0.005, 0.01, 0.02}`
- `tau_h_sigma_factor ∈ {0, 0.05, 0.1, 0.2}`

两组 ridge loading：

- `seed_mult ∈ {0.5, 1.0, 2.0}`
- `expand_mult ∈ {0.25, 0.5, 1.0, 2.0}`

### 5.2 第一轮必须覆盖的候选族

- support-side：`k_leak`
- refit-side：
  - `lambda_global`
  - `lambda_group(seed vs expanded-only)`
- detector-side：`sigma_inflation`
- outer-loop side：
  - Stage6：`alpha / beta`
  - TradParam：`gamma_h / gamma_x / pic_damp`
- strict traditional 硬阈值：
  - `tau_h_factor`
  - `tau_h_sigma_factor`

### 5.3 第二层精扫

只对每条骨架 coarse ranking 前 2 名候选做局部精扫：

- 连续类围绕 coarse optimum 做更密网格
- 离散类保留最优值与相邻值复核

阶段八代码已预留 coarse ranking 结果输出，正式精扫在完成 200 帧/3 SNR 正式诊断后执行。

## 6. 输出物

脚本输出：

- `oracle_sweep_stage6.csv`
- `oracle_sweep_traditional.csv`
- `residual_utilization_stage6.csv`
- `residual_utilization_traditional.csv`
- `candidate_ranking.json`
- `diagnostic_summary.md`

## 7. “值不值得学”的判据

候选规则只有在同时满足以下三条时，才归类为“值得学习”：

1. 在至少一个目标区间（`15` 或 `20 dB`）相对 anchor 带来 `>10%` 相对 BER 改善。
2. 在 `15/20/25 dB` 平均改善 `>5%`。
3. 最优值跨条件有明显变化：
   - 正尺度类：`max/min > 1.5`
   - 阻尼/门控类：最优值跨度 `>0.05`
   - 离散类：不同条件至少出现 2 个不同最优取值

若不满足，则该候选暂归为“当前不值得学习，只保留为手工调参项”。

## 8. 当前 smoke 验证状态

已完成：

- `afdm_joint_param.py` / `afdm_traditional_param.py` / `diagnose_joint_heuristics.py` 的 `py_compile`
- 最小 smoke：
  - `frames=10`
  - `snr=15,25`
  - `candidate_families=lambda_global,k_leak,sigma_inflation`
- 现有 `verify_joint_param.py` 与 `verify_traditional_param.py` 在不引入新参数的情况下仍可跑通

smoke 输出目录：

- `outputs_joint_heuristic_diagnosis_smoke`

## 9. 当前 smoke 观察

smoke 只用于通路确认，不用于最终研究结论。

当前 smoke 下：

- 两条骨架都能产出 `csv/json/md`
- strict traditional 这条链的 anchor 与 oracle sweep 关系正常
- `Stage6 fixed` 在当前本地 artifact 上出现明显高 BER，说明本地固定 checkpoint 与此前冻结文档中的云端 verify 结果不一致

因此阶段八正式结论必须以“同一批固定样本、同一套当前 artifact 内部的 anchor vs oracle gap”为准，而不能把本地 smoke 与此前云端冻结 BER 直接混合解释。

## 10. 正式运行建议

正式诊断建议命令：

```bash
conda run -n CE python afdm_joint_param_unrolled/diagnose_joint_heuristics.py \
  --frames 200 \
  --snr 15 20 25 \
  --out-dir afdm_joint_param_unrolled/outputs_joint_heuristic_diagnosis
```

如果正式结果显示所有候选 oracle gap 都很小，则下一轮不应继续加 learnable scalar/module，而应转向结构性建模。

如果有单一候选明显胜出，则下一轮只实现该局部规则，不再并行增加多个 learnable knob。
