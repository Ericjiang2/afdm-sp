# 实际终端复核与 GPU 资格抽样

2026-09-17。接续会话 `01a0a5a0-7304-7313-a4d9-460abc86d922` 的三个未完成行。结论：**保存仿真结果与原始数组一致；TAIL 未通过普通 ridge 参考门，仍不晋级。** 主会话实现与自审，独立性 weak；文件检索子代理不构成独立结果审查。

## 原始证据与统计

- 在 deinlab 原目录读取 v5 的 264 条生产/审计记录、3036 个数组，验证 JSON/NPZ SHA、MD5、dtype/shape/内容、预约身份、物理源、先验及冻结源码；生产与已存审计译码输出完全相同。重新计算逐块硬错误、H/响应误差及审计 NLL，与保存分数精确相同。此次只读审计 **0 新 F/T/D/A**，未重建候选或重跑译码。
- 本地全量分析器输出与旧 `tail-terminal-v5-results-v1.json` 精确相同。32 个物理簇，两 SNR 共享簇；128 个唯一新方法终端，加 4 个原状回放。
- 原冻结区间：TAIL−ORIGINAL −0.09375，区间 [−0.171875, −0.03125]；TAIL−RIDGE_T −0.046875，区间 [−0.125, 0.03125]。双参考 GO=false 保持。
- 事后双侧精确簇符号检验 p=0.03125/0.375，Bonferroni 后 0.0625/0.75；该敏感性分析依赖配对符号可交换性，不替代预登记 bootstrap。避免将开发 bootstrap 阳性写成独立统计确认。
- 旧 TAIL verify 的四份原文件已回传，相同字节核验通过；404 回传阻塞已解除，未重跑。

## 跨版本计算更正

| 版本 | T 执行 | D 执行 | 成功 D 记录 | 说明 |
|---|---:|---:|---:|---|
| v1 | 0 | 0 | 0 | 读取字段失败 |
| v2 | 0 | 0 | 0 | 旧分数定义绑定失败 |
| v3 | 12 | 1 | 0 | D 已译码并保存 3 数组，后续计分缺 x_hard；数组与生产逐项相同 |
| v4 | 132 | 132 | 132 | 四阶段成功；分析器字段失败 |
| v5 | 132 | 132 | 132 | 整批重复运行；必须计入 |
| **历史总计** | **276** | **265** | **264** | **541 次 LDPC，458.473 秒监督器墙时** |

当前 GPU 资格另加 6T/6LDPC。两者累计为 282T＋265D＝547 次 LDPC；新 F/A 均为 0。本次 raw 审计 58.305 秒，GPU job 9.486 秒；并行且插桩，不能作为正式部署成本。上述不含本地开发、传输和历史其他研究阶段。

## CPU/CUDA 抽样

固定三例 `(0,7,ORIGINAL)`、`(14,7,TAIL)`、`(14,7,RIDGE_T)`。每例仅 CPU/CUDA 各一次，共 6T；保存 H/z/prior 输入不变。GPU 为 RTX 4090，实际 CUDA 可用。

三例 CPU 的 mu/var/raw_llr/llr/decoded/info_hat/x_hard/decode_ok 全部精确复现保存值。CUDA 的全部硬判与 CPU 相同，图 H hash 相同；四个软字段均通过预冻结 atol=1e-9、rtol=1e-7，最大绝对差 1.7764e-14。**仅为三个已暴露终端样本资格；不证明 CE、完整旧接收机或跨场景等价。** LDPC 仍使用公共 CPU 实现，CUDA 作用于 BP。

GPU 作业约 9.486 秒，终端首次 CUDA 调用含初始化。后两例虽更快，不能据此报告完整接收机加速比；未启动正式 COST。

## LLR 与 H 误差

以下为同一批已暴露信道的事后描述。NLL 基于送入 LDPC 的 channel-extrinsic LLR，0 比特为正号；错误符号位位置与 |LLR| 另存，不与 x_hard 的 raw_bit_errors 混用。

| SNR | 臂 | 错块/32 | 平均 H NMSE | 平均 bit NLL | LLR 符号错误总位数 |
|---|---|---:|---:|---:|---:|
| 7 | ORIGINAL | 13 | 0.072261 | 0.281306 | 7582 |
| 7 | TAIL | 9 | 0.048857 | 0.252422 | 6879 |
| 7 | RIDGE_T | 11 | 0.064124 | 0.225757 | 5962 |
| 8 | ORIGINAL | 2 | 0.070976 | 0.192046 | 4871 |
| 8 | TAIL | 0 | 0.045531 | 0.158950 | 4063 |
| 8 | RIDGE_T | 1 | 0.055285 | 0.118197 | 2939 |

TAIL 对 ORIGINAL 在两个 SNR 的所有块均改善 NLL；对 RIDGE_T 仅 8/32、1/32 块改善。平均 H NMSE 更低，却不意味着检测 LLR 平均质量更高，也不能单凭平均 NLL 排定 FER。

7 dB 对 ORIGINAL 救回 2/9/17/26，无新增失败；对 ridge 救回 2/17/26，但丢失块 14。TAIL 剩余失败为 4/11/14/15/18/22/25/27/31。8 dB 对 ORIGINAL 救回 15/25，对 ridge 救回 15，无新增失败。

块 14（7 dB）：TAIL 的 H NMSE=0.061595，小于 ridge 的 0.067681；但响应 NMSE=0.060702 大于 0.057271，NLL=0.315415 大于 0.284317。TAIL/ridge 的 LLR 符号错误为 270/232，错误位平均 |LLR|=1.5171/1.6109，最大值 7.2323/6.6915；最终信息位错误为 49/0。这否定“H 更准必然译码更好”的单指标推断；不能用这个事后案例证明具体因果路径或按真值选择方法。

## 复现、验证和剩余门

实现冻结提交 `f70f0229`。本地及远端各 4 项数值边界测试 PASS，Python AST PASS；项目未配置独立 lint/type-check/build。真实远端两作业均 exit0，全部 29 个回收文件逐字节 SHA 匹配。GPU 六份状态在保存时逐数组回读通过。没有改动旧 source/raw/失败文件。

证据根：`afdm_sp_joint_unrolled/outputs_tail_recheck_20260917/`。远端前缀 `/data/guoyikun/00inbox/AFDM-channel-estimation/`；大 NPZ 留远端，路径、大小、SHA/MD5 在 raw inventory 及 GPU result JSON。关键证据：

- `raw/raw-audit.json`：264 记录/3036 数组及绑定清单。
- `raw/historical-accounting.json`、`local/v3-orphan-audit.json`：版本账目与失败 D 实际执行证据。
- `gpu/summary.json`、`gpu/*-result.json`：CPU/CUDA 数值门及状态。
- `raw/mechanism.json`、`local/mechanism-summary-v2.json`：逐端点描述与汇总。
- `local/analysis.json`、`local/summary-recheck.json`：冻结统计与敏感性检验。
- `evidence/*-exit.json`、`harvest-sha256.json`：真实退出及传输核验。

重新汇总：`python3 tail_recheck_summarize_20260917.py --root <证据根> --output <新文件>`。原始 runner 位于研究目录及远端 source 快照；不要为读取已完成结果重新运行 gpu 模式。

剩余 G1/COST/CONF/SCENE/CODE/PAPER/REVIEW 七行仍开放：当前没有通过双参考门的候选，新候选与独立验证的科学范围/预算需明确后才能启动。GPU 恢复与三例资格不解除这些科学门；不自动扩展方向或将阶段核验算作 Trans 总目标闭合。
