# Research: 固定 SCREEN128 与 1024 组独立 cohort 的协议审查

- Query: 根据两帧 pilot 的具体失败，核查扩大 shortlist、独立新 cohort、CP 门及完整计数是否合理；为随后源码准入保留明确合同。
- Scope: internal，当前仅协议/数学/统计审查；无科学代码、仿真、SSH 或新样本。
- Date: 2026-10-07
- Active task: `.trellis/tasks/10-05-method-advantage`
- Files read: 本目录 `SCREEN128_PROTOCOL.md`、`SHORTBURST_RESULT_REVIEW.md`；沿用已核验的 shortburst 模型与 core 合同，不重新加载生命周期。

## Findings

### 最终判定：协议与冻结 P/A 增量源码准入 PASS

修复针对已观察到的 shortlist 损失，模型、code、gain grid、风险阈值均未改变。固定 K=128、单次新 seed、1024 完整组以及保留两个旧 FAIL 的安排合理。新 core/runner/audit 与 dispatch 已完成下述独立增量核查，未发现未关闭缺陷；主线程报告最终 13/13 固定工程合同、Ruff、bash-n 及 CLI import inventory 通过。

准入仅覆盖本文末尾的固定版本、4096 新 vectors 及 P1200s/A300s 开发预算。主线程可继续既有提交/打包/隔离执行流程，本代理未执行这些动作。源码 PASS 不等于新 cohort 的性能 gate 已通过，也不替代两个旧 FAIL。

### 扩大 shortlist 的结构依据成立

在同一第四阶排名、同一 profile likelihood 及全局 hypothesis/gain tie 规则下，稳定 top32 是稳定 top128 的子集。若 FULL 正确且 SCREEN32 正确，true hypothesis 已在 top32 内，并在 FULL 全部候选的总排序中最优；把更多候选加入不能把它换成更优的错误值。因此

`{SCREEN128 wrong, FULL correct} ⊆ {SCREEN32 wrong, FULL correct}`。

这提供了不依赖三次 miss rank 精确位置的修复理由。固定增加到 128 可以作为预定 conservative change；协议明确不扫旧 rank 选择恰好覆盖三例的最小 K。

反之，FULL 错误时，SCREEN32 可能因没看到 FULL 的错误最优项而偶然正确，扩大集合会损失这种偶然获益。因此总体错误率、两码差以及实际速度没有单调保证，仍须新 cohort 实测。新 cohort 不同时运行 SCREEN32，故不能把两次 cohort 间的数值变化单独归因为 K 的边际作用；本次检验的是固定 SCREEN128 完整方案是否满足原要求。

### 单 cell CP 门的整数接受集合正确

每组的坏方向事件是 `SCREEN128 wrong and FULL correct`，独立组在同一冻结 N/T/SNR/prior/code 下 iid；所以 X~Binomial(1024,p)。不能把帧或复坐标当成额外独立重复。

对 x<1024，one-sided95% CP upper 为 `BetaQuantile(.95; x+1,1024−x)`。要求 U≤.02 等价于 `BinomCDF(x;1024,.02)≤.05`。本代理以概率质量递推作无抽样的独立确定性核算：

`b0=.98^1024`，`b_k=b_(k−1)(1025−k)/k·(.02/.98)`。

所得 `CDF(12)=.03009791306826788`、`CDF(13)=.05245190708451013`，与结果审查一致。CDF 对 x 单调，故精确接受集合就是 x≤12。风险阈值和置信度没有放宽，只是 n 从 256 改为 1024；反向 discordance 不能抵消坏方向计数。

**源码边界合同：x=1024 时必须明确 U=1，不能直接调用 beta(a,0) 后存 NaN。** 这只是全失败边界，不改变 x≤12 gate。建议实现与独立 A 同时核对 CP 数值及等价整数门。

### 其余统计门与解释合理

配对差 D=I(quad SCREEN128 wrong)−I(random SCREEN128 wrong)，均值是配对 error reduction，SE=`sqrt(sample_var(D,ddof=1)/1024)`，探索性 normal95% CI 的定义正确。≥.10、CI 下界>0、random 错误数≤256 及 complete speed ratio≥3 均保持。样本增多改善精度，不保证效应达到门槛。

第三轮由前两轮失败触发，不是一次无选择影响的首次确认试验。新数据固定生成、完整保留、不与旧数据合并可以支持此选定方案的独立开发验证；不能把多轮探索整体包装成单个5%全局检验。协议和前轮结果审查已经明确保留两轮 FAIL、禁止改 seed/门槛及隐含重跑，解释边界充分。

两码均使用相同128候选预算、同48 gain grid、同 T/N 及同一组 exogenous variables；这是相同观测和算法预算的比较，不等同于实际两码墙时严格相等。另用 random FULL/SCREEN128 直接验证实际成本门，合理。删去已保留证据的 current/FOURTH 不影响本次修复问题，也没有删除本轮已生成的失败样本。

### 完整计数与资源加法通过

本代理独立核算得到：

| 项目 | 数量 |
| --- | ---: |
| independent paired groups | 1024 |
| waveform datasets | 2048 |
| 新 N=64 vectors | 4096 |
| complex observations | 262144 |
| top-level acquisition calls | 4096 |
| likelihood hypotheses | 2359296 |
| 48-point gain-grid evaluations | 113246208 |
| 新 code/geometry | 0 |

其中 likelihood=`1024×2×(1024+128)`，gain evaluations 再乘48。FULL/SCREEN128 的候选数比为8，不应直接报告成已实测8倍 complete speedup。

P1200+A300=1500s 正确；固定2GiB RSS、512MiB output 与新4096观测 reservation 需在新 artifact 根和 recorder 中绑定，不复用旧 stage 名录作为新成功。预算估算可基于已完成同机计时，但不是完成保证。触及 cap 或任何异常均保留已完成前缀，不以预算失败为自动重跑权限。

### 后续源码准入必须核对的增量

- 仅两个 code、两个 method，固定128；不得把旧 SCREEN32 工作量常数或三臂数残留在循环、计数、audit或summary。
- code reference SHA 保持 `9d3a2d5532780b3fc884cc7d97fb7001107f9a94b64d0e9513f9eb2f2ffa0e03`；旧设计成本仍只作 historical reference。
- `n=1024` 的 CP 参数、x=1024 边界、x≤12 等价门、paired SE 以及 usable≤256 同步进入 runner 和独立 audit。
- 全候选/shortlist tie 规则、相同 candidate profile 分数一致性和完整调用计时保持；参考嵌套结论不能依赖不同打分或数值排序规则。
- 所有 raw dense reconstruction、四阶分数与选择/计数/统计仍全量检查；显式 mixture 只检查预定 `4 groups×2 codes×2 candidates=16 spots`，准确标注有限覆盖。
- 每个新调用的 attempted/completed、失败 operation、已完成 score/timing 前缀保存和零审计新样本保持；新源码冻结后再执行。

## External references and related specs

无需新外部文献；上述 CP 判断使用有限二项分布的直接递推，未抽样。科学动机基于已读 SHORTBURST_RESULT_REVIEW 的公开内部结果摘要；本代理此次没有重算其 raw 或重复旧 A。经典 FFT/phase coding 的归属与 AFDM 有用适配定位继续保留。

## Caveats / Not Found

- 本节最初为协议阶段记录；下列源码 follow-up 已完成 runner/audit 准入，不再有待交付项。
- 前两轮结果继续 FAIL，第三轮尚无数据；扩大 K、提高 n 与保留作用域不能被写成已满足性能–成本目标。
- 本代理仅写此 SCREEN128_ADMISSION.md，未修改实现、旧证据或协议。

## Source follow-up: 完整增量准入

2026-10-07 读取新 package 的 core、study、protocol、config、thread binding 和全部测试；其余沿用部分与已准入 shortburst 版本作 diff。audit/test_audit 完成后另作增量审查。没有重新加载生命周期/服务器规则、修改源码、运行科学 stage 或执行 Git/SSH。

### 核心、runner 与统计

新 core 复用旧 `row_chirp/fourth_scores/gain_grid/profile_likelihood/simulate`；只保留 SCREEN128/FULL 的完整入口，稳定 top128 后按全局索引排序。验证、dechirp、FFT、模板/likelihood 与输出均在每次独立调用内部，没有跨调用缓存，也不把 FULL 加上无用四阶预处理来人为减慢基线。

新增固定 core 合同直接比较新 FULL 与旧 FULL 的全部 profile score，要求完全相等，并比较 SCREEN128 与 FULL 相同候选的 scores/gain indices。tie 和拒绝旧 SCREEN32 method 的合同合理。旧 core SHA 仍为 `68ecf535397c120e06b21f9a36d04794808d1c3e80cb4e80d6bfb82b1c9e777b`，未修改数学核。

runner 从 `ARMS=('quadratic','random')`、`METHODS=('SCREEN128','FULL')` 推导实际循环和四种计时顺序，没有残留三臂/九调用。已完成与进入中的 observation/acquisition 计数、partial raw/score/timing/error operation 保存继承上一轮修复。成功总数、reference hash、seed2026100704 和4096 reservation 与协议匹配。

生产 summary 使用一 cell 1024 paired differences，坏方向≤12、usable≤256、≥.10改善与配对正态 SE 均正确。`bad==len(records)` 时返回 CP upper=1，关闭最初要求的全失败边界；不向 beta.ppf 传递零第二参数。

### 独立 audit

audit 的两臂/两方法清单、1024 folder/group 顺序、每组 (2,64) raw reconstruction、all-fourth-score 核验、stable top128、完整 hypothesis/gain/error/count/time 选择与交叉对比均同步。计数复核为4096 calls、2359296 likelihood hypotheses、113246208 gain evaluations。

显式 mixture spot 改为 groups0/256/512/768，每组两个码、两个候选，共16；A 没有调用 estimator、RNG 或生成新观测。旧 reference 的历史成本仍单独标明，没有重新计算设计目标。

新 `cp_upper` 独立反演二项下尾，不复用生产 beta.ppf：以 lgamma 构造 log combination、log-sum-exp 求 CDF，再对递减的 CDF(p) 作二分，更新方向正确；x=n 返回1。对于本冻结 n1024 的根，64步二分及 log域求和满足所需数值精度。A 显式验证 `(U<=.02)==(x<=12)`，并将自己算出的 U 与保存的生产数值比较。

独立统计使用分母1023的样本方差再除1024，mean/timing/discordance/全部 gate 重新计算。新增 fixtures 覆盖 x0、12、13、1024、非法1025、旧256组拒绝、usable256/257边界，以及128 shortlist tie；不是只检查成功常态。

### 控制、绑定及预算

`STUDY_CONFIG.json` 实际 SHA 与入口常量均为 `1a556ab95e91706858c96c057557cb88c3629d3ce03076a79d6cc8a7c64b581b`。runtime 清单包含20个 project文件，同时含新入口和旧数学core，pack 可从 committed bytes 完整包含复用依赖。private recorder 仅换模块名称，旧冻结模块未改。

dispatch 相对 shortburst 仅换新根/package 路径；design_reference 继续只读复制最初 performance D，SHA固定，非新D。launcher 顺序 P/A、conda前trap、退出.log、/usr/bin/time-v、单线程与CUDA隐藏保持。运行合同 max stage1200、累计1500、4096新vectors、0geometry 与配置一致。

保存的数值 score/hypothesis/gain-index payload 约73.4MB，raw source/Y约7.4MB；A复制一次P证据后加JSON/源码仍有512MiB余量。这只是静态尺寸估算，实际预算必须由recorder测量，失败不产生自动重试权限。

### 工程验证归属

主线程最终报告13/13固定合同通过（core2+config1+failure2+audit8），Ruff、bash-n、CLI `--print-imports` 通过。测试均为小型确定性fixture或故障注入，不是科学pilot。此处记录主线程运行回执，本代理完成源码与断言独立核查，没有机械重跑这些已通过的合同。

## 最终版本 SHA-256

`PKG`=`experiments/afdm_acquisition_screen128_20261007/`；`OUT`=`afdm_sp_joint_unrolled/outputs_acquisition_screen128_20261007/`。以下为本代理通过shasum读取的版本；后续若字节变化须补差异审查。

| 文件 | SHA-256 |
| --- | --- |
| PKG/__init__.py | 86143df951ef42c1ad385704fb83ce0f1855c3c40fb3efc64bf5e2ac3beca88f |
| PKG/audit.py | b5783a5a8896731cbea2270b0a53ccf7dbb0f3dbf4bf757e94d97c9ffca85510 |
| PKG/core.py | 2b912f55370754f92f8021676ada1024f641e86837bdfeba0fb6700434e0bf4a |
| PKG/protocol.py | a64c171638905c869108ad12fd8543bc4fb2241857c85ba0a8770285debfbdd9 |
| PKG/study.py | 195452035493b5867e2fa2016b7bf8ef3fd74838ac873884e037e0aa501c8163 |
| PKG/test_audit.py | 3cfa7e76cf8c28ee6fc83e67262845808fdd5654591adbfde4adbd007ca5916e |
| PKG/test_config.py | 96f0281a55549ddd0b56cba5920c970b3dce17f0e62f38e6b28ecfe3ebc0df83 |
| PKG/test_core.py | bece11c65fd930f56851c79152400ce053b5e92915cb473d2a16f3819ec8e087 |
| PKG/test_failure_records.py | d5a392d07620003dfb63af58795131fec3dabedac7a9303e8a5998e31f50e7a0 |
| PKG/thread_binding.py | 595aa7384f21e20ac23b965c9e6401a0290baf905207648a0dbfb344059bd13f |
| PKG/STUDY_CONFIG.json | 1a556ab95e91706858c96c057557cb88c3629d3ce03076a79d6cc8a7c64b581b |
| OUT/dispatch/bootstrap_remote.py | 9441c3d5f18b9528e6ad349df6a62538d79aee6add17c3df5fd04882e0e0faa4 |
| OUT/dispatch/harvest_remote.py | d5f868f07acc63e3f5b43b47cf9722d005f6830d79ca68a0ab2be8e304f6fcee |
| OUT/dispatch/pack_source.py | 86a07e09a93f52cf6a2b279d4a0e61bd71fa90e34eb32242455cc4a2f154d516 |
| OUT/dispatch/import_paths.json | d0de6e5a13e737fbbef720abc996fafdef3c7683baec6835346ff09bb1c9747b |
| OUT/launch_v1.sh | 7b582b9242998cc9736c9b8bc19a891d47053e797a16347d2908b9296cf5f3d0 |
| OUT/run_contract.json | bff5bb643a1eb3616cfd1319b390e5969a8536bfda5fc17ad7f98818d3d5bdba |
| SCREEN128_PROTOCOL.md（本目录） | d155a2b792da4713934dc902d78382530cc2e67905b1558d69b2450daf322522 |

最终没有未关闭的增量准入缺陷。仅此独立开发cohort可按既有流程继续；不存在本审查产生的新性能结果。
