# 实际终端尾补全（TAIL terminal）：已核验开发裁决

2026-09-16。冻结合同 `tail-terminal-contract-v5.json`（科学字段与 v1 逐字段相同）；四阶段远端作业全部 exit 0，独立进程 raw 审计 PASS；分析器 `tail_terminal_analyze_v2.py` 在本地对下载摘要重算。主会话自审，独立性 weak。

**裁决：`full_feedback_development_GO = false`。** TAIL 对原状 ORIGINAL 通过原冻结 bootstrap 判据，但相对同样补 T 的普通 ridge（RIDGE_T）区间跨零，未通过冻结的双参考 GO 门。全部失败运行与四个历史合同版本原样保留。

## 冻结设计与预算

| 项 | 值 |
|---|---|
| 数据 | N1024 G1，32 物理块 × 7/8 dB，ridge `.1` 已存状态 |
| 臂 | `ORIGINAL` / `TAIL`（冻结有限尾预测器）/ `RIDGE_T`（同 T 普通 ridge） |
| 终端 | 温度 1.0、BP 20 迭代、阈值 1e-4、clip 20、LDPC 50、checkpoint 1/4/7、保留最后 check 外信息、物理方差 |
| 统计 | 32 物理簇配对、20,000 次共同 bootstrap、seed 202609160701、2 比较 Bonferroni `[0.0125, 0.9875]` |
| GO 门 | 两个对比上界均为负 **且** 任一参考下分 SNR FER 不恶化 |
| 调用 | 132T + 132D，0 新 receiver F，0 新物理 A，128 个唯一新方法终端 + 4 个原状恒等回放 |

## 主端点（TAIL − 参考，FER，每物理块）

| 对比 | 均值差 | 同时 95% 区间 | 裁决 |
|---|---:|---|---|
| TAIL − ORIGINAL | **−0.093750** | [−0.171875, −0.031250] | 原冻结 bootstrap 上界 < 0 |
| TAIL − RIDGE_T | −0.046875 | [−0.125000, **+0.031250**] | 跨零，不显著 |

`no_per_snr_worsening = true`（TAIL 在两个 SNR 对两个参考都不恶化）。

## 分 SNR 结果

| SNR | 臂 | 错块/32 | FER | 信息 BER | 完整 H NMSE | 响应 NMSE |
|---|---|---:|---:|---:|---:|---:|
| 7 | ORIGINAL | 13 | 0.4062 | 0.048309 | 0.072261 | 0.070540 |
| 7 | TAIL | **9** | 0.2812 | 0.023468 | 0.048857 | 0.047649 |
| 7 | RIDGE_T | 11 | 0.3438 | 0.033691 | 0.064124 | 0.054954 |
| 8 | ORIGINAL | 2 | 0.0625 | 0.005920 | 0.070976 | 0.069683 |
| 8 | TAIL | **0** | 0.0000 | 0.000000 | 0.045531 | 0.044432 |
| 8 | RIDGE_T | 1 | 0.0312 | 0.003082 | 0.055285 | 0.045751 |

TAIL 相对 ORIGINAL 的逐块方向：7 dB 救回 4、新增 0；8 dB 救回 2、新增 0。相对 RIDGE_T：7 dB 救回 3、新增 1；8 dB 救回 1、新增 0。

## 成本与图规模（开发，插桩前向，非正式部署时延）

| 臂 | 中位前向秒 | 均值 | 平均实际图边 | 预测器求解 | 尾重拟合 |
|---|---:|---:|---:|---:|---:|
| TAIL | 0.399 | 0.396 | 74,000 | 48 | 0 |
| RIDGE_T | 0.781 | 0.793 | 154,912 | 0 | 64 |
| ORIGINAL | — | — | 13,600 | — | — |

TAIL 比同 T 的普通 ridge 便宜约一半，且图边数为其 48%；但相对 ORIGINAL 仍是 5.4 倍图密度。

## 证据、账目与血缘

- 阶段墙钟：工程 run 14.554 秒 / audit 8.637 秒；开发 run 139.651 秒 / audit 54.861 秒；监督器合计 **217.702 秒**（上限 7200）。
- 账目：132T、132 新 BP（2640 内部迭代）、132 生产 LDPC、132D 审计、264 总 LDPC、0 新 receiver F、0 新物理 A、128 唯一新方法终端、4 原状恒等回放。
- 产物 SHA 与合同 SHA 见 `tail-terminal-v5-results-v1.json` 的 `artifact_hashes`；本地镜像 `afdm_sp_joint_unrolled/outputs_tail_terminal_v5_20260916/`，远端 raw 在同名 `outputs_tail_terminal_v5_20260916`。
- 本地新鲜测试 37 项 PASS（v1/v2/v3/v4 语义与 schema 回归）。

## 合同修订史（全部失败保留）

| 版本 | 失败 | 修订（仅绑定/口径） |
|---|---|---|
| v1 | engineering run exit 1，2.972 秒：`KeyError: 'terminal_executed'` | 该字段只存在于上游 stop-runner schema；拆出 `old_binding_ok` 并删除该冗余子句（v2） |
| v2 | engineering run exit 1：`saved ORIGINAL scores disagree: raw_bit_errors` | 生产者用 `supplement_profile.score_errors`（`x_hard` 符号硬判）计分，1 打/221 对 85；改用生产者计分器（v3） |
| v3 | engineering run exit 0（12T）；audit exit 1：`KeyError: 'x_hard'` | 审计回放输出无 `x_hard`，该内部计分恢复 LLR 定义（v4） |
| v4 | 四阶段全 PASS；本地分析 exit 1：`KeyError: 'info_bit_errors'` | 冻结分析器读了被取代计分器的键名；分析器 v2 改读生产者键名（v5），runner 与 v4 逐字节相同 |
| v5 | 四阶段 PASS，分析完成 | 本次裁决 |

科学字段（臂、数据、终端、限额、统计、端点、GO 规则、源绑定、方法文档）在 v1—v5 之间逐字段相同；改动仅限记录/绑定口径。

## 边界

- 全部端点为**已暴露开发**信道，bootstrap 为描述性，不是独立确认、正式 COST 或方法新颖性。
- TAIL 对 ORIGINAL 通过原冻结 bootstrap 判据，但**同支撑同 T 的普通 ridge 已覆盖其中相当部分**；这正是 GO 门设双参考的原因。
- 结论不支持把 TAIL 晋级到完整反馈接收机合同；也不否定尾补全方向本身，仅供设计下一份冻结预测与更省算的对照（如更小图、门控）。
- 下一步需用户决定新的科学范围与预算；CONF/COST/PAPER/总 REVIEW 保持开放。

## 2026-09-17 复核更正

上述 132T/132D/217.702 秒仅为 v5，不能作为跨版本总账。v1—v5 实际执行累计 **276T＋265D＝541 次 LDPC**；成功结果记录为 276T＋264D，另 1 次 v3 D 已完成译码并保存数组，计分时报错。全部监督器合计 458.473 秒。v4→v5 整批重跑已计入，唯一新方法终端仍为 128，不是新增样本。

v5 原始 264 条记录、3036 个数组已于新进程逐项核验通过；统计全量复算与原结果相同。事后精确配对符号检验对 ORIGINAL/ridge 的双侧 p 为 0.03125/0.375，两比较校正后为 0.0625/0.75。它不替代原冻结门，但限制无条件“显著”表述。完整证据与后续 GPU/LLR 诊断见 [接续复核](tail-recheck-results-20260917.md)。
