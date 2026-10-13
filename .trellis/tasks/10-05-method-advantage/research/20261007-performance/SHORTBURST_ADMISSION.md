# Research: 两帧短突发捕获跟进的独立增量源码准入

- Query: 核对旧码复用、固定 N64/T2/SNR5 单 cell、算法/门槛保持、计数与异常保存、独立 A 审计和 P/A dispatch 的增量一致性。
- Scope: internal；基于已准入 acquisition-performance 版本做 diff 及关键路径审查，无科学运行、SSH、Git 或生命周期重载。
- Date: 2026-10-07
- Active task: `.trellis/tasks/10-05-method-advantage`
- CSV: `.mission/20261007-acquisition-performance/20261007-acquisition-performance.csv`，FOLLOWUP-02。

## Findings

### 最终结论：PASS，限定冻结 P/A 两帧开发 cohort

未发现新数学、计数、基线公平性或源码绑定阻断。主线程已提供统一 10/10 确定性工程合同（config1+failure2+audit7，0.028s）、Ruff、bash-n 和 CLI import inventory PASS 回执。增量源码准入完成，可按既有授权与冻结流程提交、打包及隔离执行；本代理未执行这些动作。

报告仅覆盖本文所列固定哈希版本、1536 新 vectors 和 P600s/A300s 的独立两帧 cohort。旧四 cell pilot 的 FAIL 保持不变，源码准入不代表新性能 gate 已通过。

### 文件与复用边界

- 已读 `SHORTBURST_PROTOCOL.md`。
- 对 `experiments/afdm_acquisition_shortburst_20261007/{study.py,protocol.py,audit.py,test_audit.py,test_failure_records.py}` 与旧同名文件作 diff；读取新增 `test_config.py`、配置、thread binding 和 runtime import inventory。
- 对新 `outputs_acquisition_shortburst_20261007/dispatch/{pack_source.py,bootstrap_remote.py,harvest_remote.py}` 与旧已审版本作 diff，完整核对新增 design reference 复制路径、P/A source inputs、launcher 和 contract。
- core 不存在第二套实现；新 study 直接导入旧 `experiments/afdm_acquisition_performance_20261007/core.py`。独立核对其 SHA 仍为 `68ecf535397c120e06b21f9a36d04794808d1c3e80cb4e80d6bfb82b1c9e777b`，与先前 SOURCE_ADMISSION 完全一致。旧数学合同无需重推。

## 科学方案增量

N=64、s=5、CP=16、L=80 不变；把 T 从 4 改为 2 不改变 `exp(2πiνLt/N)∈C4` 的逐帧论证，也不改变 FFT 坐标、gain gauge、48 点 finite-grid likelihood 和 top32 候选定义。实际噪声仍独立于隐藏 ρ，核心无 truth 输入和完整计时边界保持。

这个 N 仍使所有 Weyl cocycle 相位落在 64 点 full-circle gain-grid 中，未引入 N128 等新维度的网格闭合问题。两帧下四阶均值噪声方差较四帧大，但这只是运行前的敏感性分析，不构成预先成功保证。

根据旧数据 margin 选择低 SNR 短观测场景，是 observation-informed 的下一步研究选择；新 cohort 使用冻结的新 seed、独立数据且不与旧数据合并。因此可评价这个选定场景的新开发结果，但不能把结果解释为预先覆盖所有场景的确认性证据，也不能据后续成功覆盖旧 10pp gate 的失败。协议对这一点的标注充分。

## 固定旧码与设计工作计数

新包已删除 D 入口及设计函数，不再抽码或重搜 quadratic candidate。使用 `design_reference`，不在新 `execution` 目录伪造 D stage。原 N32 code 保留在完整旧 NPZ 内，但不会生成 N32 新观测。

旧 codes.npz 的固定 SHA 是

`9d3a2d5532780b3fc884cc7d97fb7001107f9a94b64d0e9513f9eb2f2ffa0e03`。

bootstrap 在复制前用新冻结 config 的该 SHA 核对旧文件；以独占创建复制原 `codes.npz,design.json,results.json,attempt.json`，记录每个原路径与 SHA/MD5。新 P 同时要求 code hash 匹配旧 receipt 与 config 固定值，A 又用独立常量核对；没有改变旧源或旧结果文件。

REFERENCE_PROVENANCE.json 与复制的 JSON/NPZ 被新 P/A source lists 纳入 recorder 哈希/snapshot。旧的 96 次 code phase draws 与 163280 geometry probes 在 A 结果中明确标为历史，new_design_phase_draws/new_geometry_probes 均为 0。A 对旧设计仍只检查已有数组/选择和 code 公式，不重新评估设计 ambiguity，符合零新 geometry。

## 单 cell 统计与门槛

新采样固定一个 N64/T2/SNR5 cell 的 256 iid paired groups。生产 `paired_interval` 接收 shape (1,256)，其通用公式严格退化为 `sqrt(sample_var(D,ddof=1)/256)`；独立 A 使用手写单 cell 均值、分母 255 的样本方差及 256 的平均数方差，正确。

在此 iid cell 内，bad-direction discordance 确为 Binomial(256,p)，one-sided95% CP upper 合法；`x≤1` 仍与 upper≤.02 相同。字段名称保留 binomial_reference 不影响数值和解释。反向 discordance 保留。

单 cell random SCREEN usable gate 为错误数≤64，即≤.25；A 不再误用旧每 cell 的≤16 阈值。新 audit fixture 显式检查错误数 65 会失败、T=4 的外来 cohort 会被拒绝，以及不完整组数拒绝。

3×完整时间比、≥.10 的 paired error improvement 与 exploratory normal CI 下界>0、FULL≥SCREEN numerical contract、所有 gate 联合要求均保留。没有通过修改阈值来回溯修复旧结果。独立新 cell 的正结果仍只具有 scoped development 含义。

## 完整计数及异常路径

计数独立复核：

- 256 groups×3 waveforms=768 datasets；每 dataset 两个 64-vectors，所以 1536 新 vectors、98304 complex observations。
- 256×3×3=2304 完整 acquisition calls。
- 每个 waveform 的 FULL 有 1024 hypotheses、SCREEN 有 32，故 `256×3×(1024+32)=811008` likelihood hypotheses，乘 48 为 `38928384` gain-grid evaluations。
- P 的 entered/completed acquisition calls、attempted/completed observation vectors 均保留，并将成功合同改为相应新值；partial raw、partial estimates、failed operation 与已完成 timing 的保存逻辑没有回退。
- 新 seed 是 2026100703，流内顺序、三臂 common exogenous variables 及九种算法/臂顺序轮换不变；没有 warmup 数据或 adaptive sampling。

两项 failure fixtures 复用前轮已验证的固定 mock，仅补 reference hash 字段以通过新的入口合同；新增 config fixture 检查所有新数字、900s 和 private recorder 的 package 隔离。没有将这些确定性 fixtures 记作科学样本。

## 独立 A 的增量

A 全部 dense reconstruction 已从 (4,N) 改为 (2,64)，时钟按两个连续 frame 构造；唯一 cell 顺序约束与 within_cell=group 一致。所有保存 Y、四阶 score、选择/tie/gain、方法一致性、hash、错误及计数仍全量核查。

显式四 Gaussian mixture spot 仍为 groups 0、64、128、192，每组三码、每码两个候选，共 24；它们现在是一个 cell 中的四个预定位置，不冒充四个新 cell，也不伪称全部 likelihood 重新计算。当前 A 无 estimator 调用、无 RNG、新 observation/geometry 均为 0。

独立 summary 与新生产 summary 的统计一致性按上述单 cell 公式比较。任何 source incomplete、hash/shape/count/score 不一致仍显式失败。旧 reference 的 complete 状态与当前 P 的 complete 状态分开验证。

## 源码、dispatch 与资源

study 的固定 config SHA 已独立核对为

`407d1fdabb7b226377ed93a0f004f55332013bb48cbcdc9eabfebfa637f0e959`。

private protocol 仅改隔离模块名称，继续使用新 package 路径绑定旧 recorder；实际 19 个 project runtime 文件清单包含复用旧 core，因此 pack 不会遗漏核心依赖。新源/config/controls 仍从 committed bytes 打包，运行前后绑定和 thread inventory 机制保持。

launcher/harvest 仅要求 P/A 顺序完成，没有 D。trap 在 conda activation 前且退出 receipt 后缀为 .log，整进程成本由 `/usr/bin/time -v` 报告。新 bootstrap 对旧 D 只读复制到新的独占 reference；新 source_v1/control 不覆盖旧 snapshot。

合同为 P600s+A300s=900s、1536 新 vectors、0 geometry、RSS2GiB、output256MiB；冻结配置与控制合同一致。A 对 P source/artifacts 的复制仍是有限一次 snapshot。按 N64 全候选、两帧 raw 估算保存 score 数组规模约 32 MB，raw 约 2.4 MB；加一次 snapshot 与 JSON/source 距 256MiB 有余量。该数字只是静态容量估算，不替代 recorder 的实际 bytes/RSS 检查。

## Validation

本代理未重复运行已关闭核心合同或新科学阶段，仅完成增量源码/测试断言核查与 SHA 读取。主线程最终报告统一 10/10（config1+failure2+audit7，0.028s）通过，并报告新包/dispatch Ruff、bash-n、CLI `--print-imports` 通过。原 core 的 bytes 与旧准入版本相同，因此未机械重跑旧 7 项核心合同。上述统一运行归属主线程，不表述为本代理亲自执行。

## 审阅版本 SHA-256

`PKG`=`experiments/afdm_acquisition_shortburst_20261007/`；`OUT`=`afdm_sp_joint_unrolled/outputs_acquisition_shortburst_20261007/`。

| 文件 | SHA-256 |
| --- | --- |
| PKG/__init__.py | a86eb1b30cc4bf52674262ba7312b2b0cc515b0d967b6da2a9666d2c6acbc7ec |
| PKG/audit.py | cd75df1a7c3781153b2332c03ebba11214fcf3ca3e134bba932e07100f1fd5cd |
| PKG/protocol.py | e0227d6da963fb3ac561e972c1ffb3d9c7880a35be8d89f5b46a8b5fa5476643 |
| PKG/study.py | 7ab36582cbeeb2d04f986728475847995f842a7d23be1c79288db2d4f1e5c564 |
| PKG/test_audit.py | 64c9cfc2961541a18b3514d5eda8e80179369c29fc913b2fb2e9469fc7dbd232 |
| PKG/test_config.py | d9869a6393084b797226b4d8c0ae843c20ed8c45c1ad3b66309a3e8f64aa9d2e |
| PKG/test_failure_records.py | 65c75be070fe9ae3f8a64a6a5e70b9444b370a0a1bd59ce728f421f270a72bab |
| PKG/thread_binding.py | 595aa7384f21e20ac23b965c9e6401a0290baf905207648a0dbfb344059bd13f |
| PKG/STUDY_CONFIG.json | 407d1fdabb7b226377ed93a0f004f55332013bb48cbcdc9eabfebfa637f0e959 |
| OUT/dispatch/bootstrap_remote.py | 8d58c262c0ba2b6ac70f195e895d3ff6325ad917bdfed5b551b5bf98ee7faf82 |
| OUT/dispatch/harvest_remote.py | b68d0eb4bb97d559881670eaf8c955168c2ba7e46f70563477d8cbe0de6a55b8 |
| OUT/dispatch/pack_source.py | 01a104bb31dca315c497d377cd5f9d74852f58cd6c7184df44a3e1919d25cd79 |
| OUT/dispatch/import_paths.json | 29db42d801c9fa097bca009625f48d18c8ff95201a8bb0a9ff3ba4c74c51b781 |
| OUT/launch_v1.sh | 0dce1929a92f1bdf2a7bb51ae8efcb5e86f05f7934b6062944bfc8c547c07554 |
| OUT/run_contract.json | a647c78f32d57b7d36844d7d9d494138815a9a0ee75e4341962078b3c19bba59 |
| SHORTBURST_PROTOCOL.md（本目录） | 1f4902f75b4e55b64e7ea9175b6f66574c3eb168c411c51eff6cf520da6fb32f |

## Caveats / Not Found

- 没有未关闭的增量源码准入缺陷；最终工程回归回执已收到并记录。
- 旧 margin 诊断和旧 pilot 数字来自主线程交接，本轮未重读 raw；本审查没有产生任何新性能结果。
- 这是独立开发 cohort，任何结果都不能与旧 pilot 合并或替代旧 FAIL；经典适配可保留，不据此扩大物理适用域或新颖性声称。
- 本代理唯一新写文件为 SHORTBURST_ADMISSION.md，未修改代码、控制文件、CSV 或旧实验。
