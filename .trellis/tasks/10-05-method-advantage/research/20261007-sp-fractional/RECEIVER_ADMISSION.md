# RECEIVER 最终字节准入

2026-10-07；IMPL-01 / SSH-DEV。复用核心与 harness 静态审查，仅核对部署字节、
工程输入、合同与启动器；未运行数值、SSH 或提交。**本地字节准入 PASS：工程一次
GO 以主线程最后远端核验为生效条件；development 是下述条件满足后的一次 GO，
当前不立即运行，也无需届时重做本次完整审查。**

## 已核对的绑定

- 原源码 commit：`78c4156934746591dfc1385fc92c811f60a28123`。
- 独立部署 snapshot：`559f41654e15b8103a788f5c003939576dd1da00`。
- tar：`.mission/20261007-sp-fractional-trans/dispatch/receiver-source-78c41569.tar.gz`。
  SHA256：`3947ecf3e123197d8061534feef91a42e31a87db93a9523a5148c217f7e27803`。
- 实际 imports 清单为 58 个项目 Python 文件，集合与 manifest、snapshot Git tree
  完全相等；逐个验证原 commit、snapshot commit、tar、当前源码字节及 SHA 一致。
  snapshot 中 HEAD 正是上述独立 commit，不能把它与原源码 commit 混称。
- tar 共 256 个成员，均为 `source/` 内的普通文件或目录；无绝对/上跳路径、
  重名成员、软硬链接、特殊文件或 setuid/setgid。全部 tar 文件（含 Git 元数据）
  与本地 snapshot 一致；没有额外非 Git 载荷或外部 Git alternates。
- 工程合同 68 个输入 = 58 个源码 + 原 MATH 的 attempt.json 与 N8/N16/N1024
  各 inputs/arrays/checks，共 10 文件；逐字节哈希与本地原证据及 checks 引用一致。
  对应远端目录保持为
  `/data/guoyikun/afdm_sp_fractional_20261007_math01_c639a4b0/artifact/execution/MATH-01/`。
  原 attempt SHA256 未变：
  `329f39b59b0fe48dfdfaa4f3870deb29320d457ede16a95f77d54b673b787e56`。
- 两阶段合同配置与保存的 `--print-config` JSON 精确一致；development 仅绑定
  58 源码，无新引入或复制改写的旧 MATH 输入。两个阶段的 source_manifest 与总表一致。
- 已读取两最终远端根的本地回传 `remote-imports.json` / `remote-config.json`，
  内容及文件 SHA 均与上述冻结 JSON 一致。两份 deployment stdout 均记录 tar 校验
  OK 和正确 snapshot HEAD，stderr 均为空；这只证明部署/导入检查，不是数值运行。

## 合同和启动器

| 阶段 | 内核 wall / CPU | 全进程 timeout | 科学/组件配额 |
|---|---|---|---|
| RECEIVER-ENG-01 | 180 / 180 秒 | 210 秒，TERM 后 10 秒 KILL | 3×7 算子比较、9 数据步、13 组件测试；1 次非法 receive 边界调用，有效 payload/backend、新观测、decoder 均 0 |
| RECEIVER-DEV-01 | 1800 / 1800 秒 | 1830 秒，TERM 后 10 秒 KILL | 4 独立 blocks、6/8 dB 共 8 观测、24 接收调用、decoder 0 |

两者均 1 CPU、CUDA 隐藏、峰值 RSS≤4 GiB、输出≤128 MiB。工程旧矩 Pd=.55
与数据步工作 Pd=.5 明确分开。开发种子 `[20261007,703]`、20×3 更新、三个 arm、
SNR/增益口径与冻结筛选门槛保持一致；不把工程组件当作有效 receiver 或 BER 证据。

两个 launcher 均经 `bash -n`；固定不同 `/data/guoyikun/` 新根，以不带 `-p` 的
`mkdir "$process"` 独占创建过程目录，失败不得覆盖重跑。stdout/PID/start/end/exit
与 `/usr/bin/time -v` 全进程计费保留；内核 180/1800 不冒称全进程上限。首次漏
cao_baseline 子目录的 import-only 失败由主线程报告已保留，补齐后的成功导入也不计
科学样本；本审查未自行运行或复核该旧失败日志。

## 生效条件

1. **工程一次 GO**：主线程在
   `/data/guoyikun/afdm_sp_receiver_20261007_eng01_78c41569` 核实 tar/58 源/合同/
   launcher 及旧远端 10 输入与本报告绑定一致；最终 root 的 import/config 与冻结
   JSON 相同，资源/有效单线程/CUDA 状态满足约束，过程目录和 attempt 尚不存在。
   launcher 必须在已初始化 conda 的同一 shell 中执行，使用 AFDM 环境。
2. **development 条件式一次 GO**：工程原始 attempt 必须 complete、退出 0，
   3 组各 7 项检查全部通过、9 个已接受数据步完整、13 个测试各运行一次并通过；
   源码/输入哈希、资源与 actual_counts 均符合工程合同。测试中事先声明的故障注入
   被正确拒绝属于测试通过，不要求删除其失败 trace。随后主线程在独立新根
   `/data/guoyikun/afdm_sp_receiver_20261007_dev01_78c41569` 再核对本报告同一源码/
   控制字节、该根实际 import/config 和最新资源状态，且无已有过程/attempt 后执行。
3. 任一实际工程失败、预算超限、导入/配置/哈希漂移均不触发自动重试或 development；
   保留首个失败。源码、配置、样本或配额若改变，本准入不自动沿用。开发未过筛选
   门槛也不能删除失败、改门槛或据此关闭 coded/完整性能–成本目标。

## 控制材料 SHA256

路径均相对于 `.mission/20261007-sp-fractional-trans/control-receiver/`。

| 文件 | SHA256 |
|---|---|
| `source_manifest.json`（含两阶段同名副本） | `c6549ea17e47d68a0778088e72ab4106a2014c80fee2cab9d24929cafe751377` |
| `imports.json` | `e12a04791ce7c5c6f4b96e64616ef80ea67147f932d9224fa89ddcef42c6ab4b` |
| `engineering-config.json` | `a3611143e5d91847303a6d52893c71090cf42420a9aeb592c515dbfe18307315` |
| `development-config.json` | `476f9ee0b92790cd38b21c461973c13ee964f00c7afa072498ea0221647f9e6e` |
| `engineering/run_contract.json` | `9b435bbd37a70b2acca4e155fe9cd0caafc3bbe8fc2d9619a9b2bd995042a79a` |
| `engineering/launch.sh` | `45a1c78843ce31e3f42c6760b7e7a4da0515b40fa25ec868a32945cd666cc463` |
| `development/run_contract.json` | `9103c033caf966987a83d686f5a419b8841b21dde7f533e2a732ffa73940a648` |
| `development/launch.sh` | `63bbbedd9b76bab09430c0aba6c95cb4149faa9b059e31c312c00ae5ef30c6a7` |

验证：上述字节/清单/合同检查及启动器静态语法通过；源码 Ruff/AST 复用已完成
记录。本轮未做 TypeCheck、数值 tests 或远端运行；已核对回传部署/导入文件，
剩余远端输入、独占目录与即时资源/环境生效条件由主线程补证。
