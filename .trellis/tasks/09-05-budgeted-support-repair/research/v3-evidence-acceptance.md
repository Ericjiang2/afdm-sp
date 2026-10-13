# v3 EVID-01：原始证据复用验收

执行依据：用户明确要求按照v3 CSV执行直到完成，替代生成时“先不执行”。v3独立预算按原计划上限执行，不追认旧S1增额、不挪用旧S2/S3/S4余额、不打开Dtest或修改论文主张。

验收命令：`python3 .trellis/tasks/09-05-budgeted-support-repair/research/v3_evidence_audit.py --out .mission/20260907_23-36-31-afdm-causal-plan-v3/evidence`。审查与回归由主会话完成；这是原件审计，不是新receiver实验。

| 原始证据 | 新鲜检查 | 复用边界 |
|---|---|---|
| gainpilot+gainrest | 192身份；原sigma、H hash、外生输入、原错误逐帧相等；A2错帧38→2 | 固定最终S与原sigma下，真值投影末端H干预；不可实现，不是sigma-only |
| fit192 | A0/A2与gain参考逐帧身份、错误和H hash一致；A0错帧42/192 | B0=A0无修复，不能把A2的38当B0错误；H只有hash，终端张量需在指定配额补采 |
| mechanism47+首帧 | 48唯一身份；R11 96表、9207候选；69同状态、27支持分化 | 两轮t0修复，不是反馈outer；分化记录保留 |
| feedback48 | 48帧，每帧9个消费者与三目标共同状态 | f_mean轨迹，不能标成B0轨迹；已有目标/解直接复用 |
| 远端feedback原快照 | 48/48存在且SHA256全部匹配，共3,785,060,736 bytes；读/hash用时3.665秒 | 不重跑既有反馈包。需要张量时就地读取，避免无意义回传全部3.8GB |
| 旧壳全池 | 24帧，每帧97动作 | 只回答旧真值容量壳单动作空间，不代签新壳全局上界 |

服务器检查：deinlab可达，4090 24564MiB、使用1MiB、利用率0%；128逻辑核。只读pgrep没有匹配的旧接收实验进程（exit1表示无匹配，不是SSH失联）。SSH配置ServerAliveInterval30、ServerAliveCountMax3。

持久证据：新mission下 `evidence/EVID-01.json`、`feedback-snapshots.json`、`remote-snapshots.json`；含旧包SHA256、当前全部Python源hash和HEAD。旧59行处置映射保留，不改旧CSV状态。旧stage-budget未结束窗口原文件及hash保留，余额不用于v3。

差额清单：B0 fit终端H/初态最多192完整帧；共同B0 t0/3/6轨迹最多48帧，先查原件；特定sigma-only原件在对应任务继续检索。f_mean高置信错误子组应先由现存张量恢复，不能重复计算已有三目标来充当新增证据。

结论：证据身份与复用范围已核验；对应缺字段、补采上限与范围明确。下一步SPEC-01冻结执行协议。所有新科学比较尚未运行。
