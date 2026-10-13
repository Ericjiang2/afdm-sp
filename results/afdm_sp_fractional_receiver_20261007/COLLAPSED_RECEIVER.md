# Collapsed 局部接收：有小幅开发差异，未通过性能–成本门

2026-10-08，COLLAPSED-RECEIVER-01。一次冻结四臂实验完成，32/32 calls 全部成功，
独立原件审计 PASS。科学筛选 FAIL：消元法的误比特改善不足，完整成本过高。
保留该经典方法的 AFDM 适配和数学组件；不将它提升为独立确认或 Transactions 贡献。

## 配对结果

同一批原 4 blocks、6/8 dB 共 8 observations；每臂 16384 bits。
N1024、SP 功率 .5/.5、真实连续 CPP，多路径增益保持 G0→G1 原样复用。
所有方法各自完整执行 F1，未跨臂免费复用获取。

| 方法 | 6 dB 错比特 | 8 dB 错比特 | 合计 | 完整中位 wall（秒） |
| --- | ---: | ---: | ---: | ---: |
| F1 + scalar | 1043 | 712 | 1755 | 0.5859166564 |
| 原 point：20 sweeps，全域搜索 | 1045 | 639 | 1684 | 1.6440407335 |
| local point：5 sweeps | 1030 | 642 | 1672 | 0.7517338219 |
| collapsed point：5 sweeps | 1032 | 629 | 1661 | 1.1566770704 |

消元法相对原 point 少 23 个错比特（1.37%），不足预登记 10%；其完整中位 wall
是 scalar 的 1.9741 倍，高于 1.25 倍门。未放宽门槛，也未追加调参重试。

对同为五轮、同一搜索规则的 local point，消元法少 11 个错比特（0.66%），
完整中位 wall 增加 53.87%。123 个硬判发生变化，纠正 67、引入 56；
8 条观测中 5 条改善、3 条变差。6 dB 合计反而多错 2 个，8 dB 少错 13 个。
因此 `matched_control_improvement=true` 只指该开发集合总数严格更少，
不代表统计显著、各场景改善或成本优势。

local point 相对原 point 的运行更快、总错比特略少，但同时改变轮数和搜索。
本实验不能把两者作用单独归因，也不能把它自动升级为新方法通过完整门。
下一诊断使用已保存的完整迭代轨迹，检查优化目标与判决风险的关系。

## 数学作用与边界

固定软数据因子时，Gaussian gain 可解析消去；逐坐标 Schur 评分
J=|t|²/s−log(s) 与完整求解一致，且对 gain–Doppler 的相位参考重参数化不变。
这给出了可复现的 AFDM/SP 实现依据，但经典 Gaussian/Schur/连续频率 evidence
优化已有先例，不声明首创。数理一致性不会自动推出 BER 改善。

每局部坐标窗口 ±.75、与 [-3,3] 相交，bounded 搜索 xatol=1e-4/maxiter=32；
两新臂共 640 次搜索，实际各需 9–13 个评分。3547 次普通局部评分与 3821 次
collapsed 搜索评分均记账；320 次 collapsed 完整 winner 恢复额外计费。
独立审计重算保存候选，最大 J 归一差异约 5.47e-15。完整协方差与原 data-MM
回溯/拒绝工作保留；同搜索上限不等于同实际计算成本。

## 可信度与资源

原 scalar/point 的 16 calls、32 个终态 LLR/hard 数组与上一冻结 ADAPT 实验
逐字节相同，旧基线结果未漂移。全部接收输出先封口再读取 truth 评分。
独立审计覆盖 212 文件、203 个 attempt 绑定、85 source snapshots、全部 32 calls，
逐 LLR 重算硬判、错误数、配对变动、操作计数与完整成本。

- recorder stage wall/CPU：46.682511 / 45.842948 秒，均低于 240 秒。
- 完整进程 wall/CPU：49.65 / 48.83 秒；峰值 RSS：528121856 bytes。
- 212 原件、68802194 bytes；单文件均小于 10 MB，全部回传并核验 SHA/MD5/size。
- 0 新独立 blocks、0 新 observations、0 decoder；不构成 coded 确认。
- source：`62508b84d64be5e3504ad9a2e14ea0e77a4fa60c`；snapshot：`36dc6e527df93fa7494436d1b47a1238fa4b4554`。
- contract SHA：`d3263b137e5b9a7e0895a60610de6993de243d20c31a86bd57402d0619cce9d3`。
- 远端：`/data/guoyikun/afdm_sp_collapsed_receiver_20261007_development_62508b84/artifact`。
- 本地：`.mission/20261007-sp-fractional-trans/evidence-collapsed-receiver-development/artifact`。

同目录 `collapsed_receiver_dev_manifest.json` 列出全部远端路径、MD5、SHA、大小；
scores/contract/launcher/resource 为原件副本，NPZ 不入 Git。
原件审计：`.trellis/tasks/10-05-method-advantage/research/20261007-sp-fractional/COLLAPSED_RECEIVER_DEV_RAW_REVIEW.md`，
SHA-256 `f3bcf528e49a55f7ac84e1f53cd9f2cd0820ac53851e1f38b3f0896013eb7df2`。
原连续边缘化负结果、全部旧 CSV 及论文主张保持原样。完整研究目标仍未满足。
