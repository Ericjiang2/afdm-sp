# Results — afdm_joint_param_unrolled

## 格式说明

```markdown
## R[ID] 实验名称

**实验时间**: YYYY-MM-DD
**实验阶段**: Stage X
**状态**: 进行中 / 已完成 / 已分析

### 实验配置
- SNR: ...
- 帧数: ...
- 信道类型: ...
- 关键参数: ...

### 结果摘要
| 方法 | 15dB | 20dB | 25dB |
|------|------|------|------|
| ...  | ...  | ...  | ...  |

### 关键发现
...

### 输出文件位置
- `outputs_xxx/result.csv`
- `outputs_xxx/result.pkl`

### 相关分析
[[链接到分析文档]]
```

---

## 现有结果汇总

### 阶段八 Oracle Sweep（进行中）
**输出目录**: `outputs_joint_heuristic_diagnosis/`

#### Smoke 测试（已完成）
- **配置**: 10 帧, SNR=[15, 25], candidate_families=lambda_global,k_leak,sigma_inflation
- **观察**:
  - strict traditional 侧 anchor 与 oracle sweep 关系正常
  - sigma_inflation 有改善但跨条件变化不明显
  - k_leak 有工况差异但改善幅度不够
- **结论**: 阶段八脚本能区分 "改善存在" 与 "值得学习"

#### 正式诊断（待运行）
- **建议配置**: 200 帧, SNR=[15, 20, 25]
- **命令**:
```bash
conda run -n CE python afdm_joint_param_unrolled/diagnose_joint_heuristics.py \
  --frames 200 \
  --snr 15 20 25 \
  --out-dir afdm_joint_param_unrolled/outputs_joint_heuristic_diagnosis
```

### 阶段六/七历史结果
参见原有研究日志:
- `研究日志_阶段六_ParamLearnedJointReceiver.md`
- `研究日志_阶段七_TraditionalParamJoint.md`

