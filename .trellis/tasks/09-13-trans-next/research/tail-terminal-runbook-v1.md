# 实际终端尾补全：运行入口 v1

科学来源：[冻结合同](tail-terminal-contract-v1.md)。精确文件、SHA、参数和顺序：[作业包](tail-terminal-bundle-v1.json)。本入口不替代CSV状态；当前包尚未上传、目标G1新调用为0。

## 先恢复已有证据

TAIL verify-v1 已成功退出，不得再次启动。先从
`/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_ce_state_20260915/`
回收以下原文件到本地同名目录，按远端SHA校验；已有文件只接受相同字节：

- `evidence/tail-completion-verify-v1-launch.json`
- `evidence/tail-completion-verify-v1-exit.json`
- `logs/tail-completion-verify-v1.log`
- `runs/tail-completion-verify-v1/summary.json`

上一轮成功读取的JSON内容已存于[工具回执](resume-evidence-v1/tail-verify-captured-tool-evidence-v1.json)，不要把它重序列化后冒充原文件。2026-09-16的实际回传被自动审批服务404拒绝，需恢复审批通道后再执行。

## 新实验部署

1. 通过 `ssh deinlab` 只读检查CPU、内存、GPU故障状态和本任务同名进程/目录。当前是显式CPU任务；不安装或修复GPU驱动。
2. 创建作业包声明的新 `outputs_tail_terminal_20260916` 目录及 `analysis-source-v1/jobs/evidence/logs`。只上传包中9个源/合同文件和4个job JSON，校验每项SHA。文件存在则核相同字节，不覆盖。
3. 复用原CE `source-v4`、原ridge与原G1结果；不要同步 `.trellis/`、STATE、vault目录或大NPZ。快照代码、旧失败、raw保持原样。
4. 对实际AFDM环境执行source/导入检查；本地缺少matplotlib导致计时runner未作运行验证，不能把本地CLI的validate结果当成远端集成通过。远端既有环境若缺依赖，先保留错误、停止该工程入口。
5. 依下表逐个启动。各job已包含完整命令、root和timeout；用包中同SHA的 `run-light-job.py JOB_PATH JOB_SHA256` 放入指定tmux。只有前一作业的exit0、未超时、summary和对应准入已验证，才进入下一项。

| 顺序 | 作业 | tmux | 计算上限 |
|---|---|---|---|
| 1 | engineering-run | `g_tt_eng_run_v1` | 12T / 600秒 |
| 2 | engineering-audit | `g_tt_eng_audit_v1` | 12D / 600秒 |
| 3 | development-run | `g_tt_dev_run_v1` | 120T / 4800秒 |
| 4 | development-audit | `g_tt_dev_audit_v1` | 120D / 1200秒 |

工程先对块0/20×7/8四个ORIGINAL逐数组精确回放，随后才评分8个新方法终端。工程audit的报价必须GO；后续保留工程结果，只做余30块。任何失败、超时、字节或来源不一致都停在本次尝试，不能覆盖失败或盲目重发。

监督器将缓存、Matplotlib、Torch及临时目录放到新campaign的cache下，并固定单线程/禁CUDA。所有远端写入仍位于 `/data/guoyikun/`。不用远端共享临时目录，不push或发送外部通知。

## 回收与分析

四个作业的launch/exit/log、producer/audit summary及environment回传同名本地输出目录。为小文件加精确Git白名单；大NPZ留远端，保存完整路径、大小和SHA/MD5清单。

使用 `tail_terminal_analyze_v1.py --root CAMPAIGN --contract CONTRACT --output NEW_RESULT_JSON`。分析器要求两阶段producer和audit匹配、132T/132D齐全、四个exit成功、32物理簇配对与7200秒预算。输出文件不得已存在。

根据冻结两个FER比较及分SNR无恶化规则裁决；若不GO，先研究已有原始图和误差分解，不能将旧TAIL风险阳性移植为终端性能主张。新完整反馈合同、独立确认和原七项后置验证分别维护。
