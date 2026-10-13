# TAIL 接续核验与可行性收口

## 结论及证据层级

384 个唯一生产比较及四个预定端点，在另一进程逐项重算一致。依据是上一轮成功 SSH 状态检查留下的[工具回执](resume-evidence-v1/tail-verify-captured-tool-evidence-v1.json)；已校验其绑定的旧 summary、rows、reader、runner、contract 与本地文件 SHA-256 一致。它记录 supervisor exit 0、未超时、PID 已退出。此次恢复未重新执行核验。

新进程仍调用原实现，科学审查由主会话完成，独立性 **weak**。本回执是当时读取的 JSON 内容，不能冒充远端原文件的逐字节回传。四份原文件（launch、exit、log、summary）尚待回传及哈希校验：本次操作被自动审批接口 404 拒绝，详见[拦截记录](resume-evidence-v1/tail-readback-approval-block-v1.json)。

旧[结果 JSON](tail-completion-results-v2.json)、raw 和源码保持原样；其中 62.986 秒及同进程自审仅描述原两次作业。本附录补充后来发生的核验，不将重复计算算作新样本。

## 累计计算账本

| 作业 | 唯一生产比较 | 重复核验比较 | 预测矩阵求解 | Supervisor 墙时 |
|---|---:|---:|---:|---:|
| v1 来源守卫失败 | 0 | 0 | 0 | 2.771 秒 |
| v2 生产及同进程核验 | 384 | 384 | 39 + 39 | 60.215 秒 |
| verify-v1 新进程核验 | 0 | 384 | 39 | 31.442 秒 |
| **累计** | **384** | **768** | **117** | **94.428 秒** |

新进程另读 64 个 ridge F、32 个物理 A，重构 128 个保存设计、检查 3072 列和 128 个核心动作；峰值 RSS 733,011,968 字节。累计数学比较 1152，唯一生产比较始终为 384。新增完整接收机 F、CE、BP、LDPC 均为 0。墙时不包含本地开发、测试、汇总或传输；相应活动不得称为零计算。

## 实现与科学范围核验

- [9 项目标测试](resume-evidence-v1/afdm-feasibility-recovery-pytest-v2.json)已通过；两次环境失败保留。冻结源未改，无需重复这组测试。
- 三层各自与相同核心不补尾配对；合法层使用原 S24、实际中心、固定 W5、128 点求积与名义 q=.01。
- 真 H、真数据及路径中心只进入外部评分或明确 oracle 分支；合法层未按真值筛 delay、中心或强度。
- 四区间按 32 个物理簇共同 bootstrap；两 SNR 不是 64 个独立物理样本。
- t9 完整 H/无噪响应均值分别下降 35.19%/35.38%，基线是 `g_solution` 直接重建的未阻尼核心 H。原终端 H 的收益、FER、实际图和成本尚未验证。
- 部分真中心仅替换 14/864 个唯一真路径 delay 状态，不构成严重错中心测试。
- v1 在评分前拒绝，原因与失败开销保留；v2 源映射修复不改变科学判据。

## 交付边界

TAIL 与 CWORD 的结果和主会话范围审查已可落盘；原文件回传和 Git 交付仍待完成，CSV 不提前记为全部闭环。下一阶段按[接续计划](resume-20260915-tail-followup-plan-v1.md)检验实际终端 H 的合法补全。原 G1/COST/CONF/SCENE/CODE/PAPER/REVIEW 七项仍开放。

## 2026-09-17 原文件回传完成

原 launch/exit/log/summary 四文件现已逐字节回传并校验，与本地已存同名文件一致；未重跑 verify 作业。此前 404 为历史阻塞，现已解除。完整路径及 SHA 见 `afdm_sp_joint_unrolled/outputs_tail_recheck_20260917/local/old-verify-harvest.json`。实际终端另已完成，后续以 [接续复核](tail-recheck-results-20260917.md) 为准；旧 raw、结果 JSON 和本文历史账本不改。
